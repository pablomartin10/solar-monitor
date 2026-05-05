"""
Solar Monitor API
─────────────────
FastAPI backend that manages inverter configuration, polls Deye inverters
via PySolarmanV5, stores readings in InfluxDB, and exposes a REST API
consumed by the dashboard.
"""
import json
import logging
import os
import re
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator

from influx import InfluxWriter
from poller import InverterPoller

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger(__name__)

CONFIG_PATH  = Path("/app/data/inverters.json")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "60"))
MAX_POLL_INTERVAL = 3600  # Max 1 hour
MIN_POLL_INTERVAL = 10    # Min 10 seconds

# Validate and constrain POLL_INTERVAL
if POLL_INTERVAL < MIN_POLL_INTERVAL or POLL_INTERVAL > MAX_POLL_INTERVAL:
    POLL_INTERVAL = max(MIN_POLL_INTERVAL, min(POLL_INTERVAL, MAX_POLL_INTERVAL))
    log.warning(f"POLL_INTERVAL adjusted to {POLL_INTERVAL}s (valid range: {MIN_POLL_INTERVAL}-{MAX_POLL_INTERVAL}s)")

SUPPORTED_INVERTER_TYPES = {"hybrid", "4mppt", "micro", "sg04_sg02"}
POLL_STATS = {"total": 0, "success": 0, "failure": 0, "last_poll": None}

# ── In-memory state ───────────────────────────────────────────────────────────

inverters: dict[str, dict]   = {}   # id → config + runtime state
pollers:   dict[str, InverterPoller] = {}
influx:    InfluxWriter | None = None


# ── Persistence ───────────────────────────────────────────────────────────────

def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            data = json.load(f)
        for inv in data:
            inv.setdefault("status", "unknown")
            inv.setdefault("last_data", None)
            inv.setdefault("last_update", None)
            inverters[inv["id"]] = inv
        log.info(f"Loaded {len(inverters)} inverter(s) from config")


def save_config():
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    serialisable = [
        {k: v for k, v in inv.items() if k not in ("last_data",)}
        for inv in inverters.values()
    ]
    with open(CONFIG_PATH, "w") as f:
        json.dump(serialisable, f, indent=2)


# ── Polling ───────────────────────────────────────────────────────────────────

def _get_or_create_poller(inv: dict) -> InverterPoller:
    inv_id = inv["id"]
    if inv_id not in pollers:
        pollers[inv_id] = InverterPoller(
            inv_id=inv_id,
            name=inv["name"],
            host=inv["host"],
            port=inv["port"],
            serial=int(inv["serial"]) if inv.get("serial") else 0,
            slave_id=inv.get("slave", 1),
            inv_type=inv["type"],
        )
    return pollers[inv_id]


def _remove_poller(inv_id: str):
    if inv_id in pollers:
        pollers[inv_id].close()
        del pollers[inv_id]


def poll_inverter(inv_id: str):
    inv = inverters.get(inv_id)
    if not inv:
        return
    POLL_STATS["total"] += 1
    POLL_STATS["last_poll"] = datetime.now(tz=timezone.utc).isoformat()
    
    log.info(f"Polling [{inv['name']}] at {inv['host']}:{inv['port']}")
    poller = _get_or_create_poller(inv)
    try:
        data = poller.poll()
        inv["status"]      = "online"
        inv["last_data"]   = data
        inv["last_update"] = datetime.now(tz=timezone.utc).isoformat()
        inv["poll_count"]  = inv.get("poll_count", 0) + 1
        if influx:
            influx.write_reading(inv_id, inv["name"], inv["type"], data)
        log.info(f"[{inv['name']}] Poll OK (#{inv['poll_count']})")
        POLL_STATS["success"] += 1
    except Exception as e:
        inv["status"]    = "offline"
        inv["last_data"] = None
        inv["poll_errors"] = inv.get("poll_errors", 0) + 1
        log.warning(f"[{inv['name']}] Poll FAILED (error #{inv['poll_errors']}): {e}")
        POLL_STATS["failure"] += 1


def poll_all():
    for inv_id in list(inverters.keys()):
        try:
            poll_inverter(inv_id)
        except Exception as e:
            log.error(f"Unexpected error polling {inv_id}: {e}")


# ── App lifecycle ─────────────────────────────────────────────────────────────

scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global influx
    load_config()
    influx = InfluxWriter()
    scheduler.add_job(poll_all, "interval", seconds=POLL_INTERVAL, id="poll_all",
                      max_instances=1, coalesce=True)
    scheduler.start()
    # Initial poll on startup
    if inverters:
        poll_all()
    yield
    scheduler.shutdown(wait=False)
    for p in pollers.values():
        p.close()
    if influx:
        influx.close()


app = FastAPI(title="Solar Monitor API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ───────────────────────────────────────────────────────────────────

def validate_ip(v: str) -> str:
    """Validate IPv4 or hostname."""
    # Allow hostnames and IPv4 addresses
    ip_pattern = r'^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$|^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
    if not re.match(ip_pattern, v):
        raise ValueError(f"Invalid IP or hostname: {v}")
    return v

def validate_port(v: int) -> int:
    """Validate port number."""
    if not 1 <= v <= 65535:
        raise ValueError(f"Port must be between 1 and 65535, got {v}")
    return v

def validate_slave_id(v: int) -> int:
    """Validate Modbus slave ID."""
    if not 0 <= v <= 255:
        raise ValueError(f"Slave ID must be between 0 and 255, got {v}")
    return v

class InverterCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    host: str = Field(..., description="IP address or hostname of data logger")
    port: int = Field(default=8899, ge=1, le=65535)
    serial: str = Field(default="", max_length=20)
    type: str = Field(default="hybrid", description="Inverter type: hybrid or 4mppt")
    slave: int = Field(default=1, ge=0, le=255)

    @validator('host')
    def validate_host(cls, v):
        return validate_ip(v)

    @validator('port')
    def validate_port_field(cls, v):
        return validate_port(v)

    @validator('slave')
    def validate_slave_field(cls, v):
        return validate_slave_id(v)

    @validator('type')
    def validate_type(cls, v):
        if v not in SUPPORTED_INVERTER_TYPES:
            raise ValueError(f"Unsupported inverter type: {v}. Supported: {', '.join(SUPPORTED_INVERTER_TYPES)}")
        return v

class InverterUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    host: str | None = Field(None, description="IP address or hostname")
    port: int | None = Field(None, ge=1, le=65535)
    serial: str | None = Field(None, max_length=20)
    type: str | None = Field(None, description="Inverter type")
    slave: int | None = Field(None, ge=0, le=255)

    @validator('host')
    def validate_host(cls, v):
        if v is not None:
            return validate_ip(v)
        return v

    @validator('type')
    def validate_type(cls, v):
        if v is not None and v not in SUPPORTED_INVERTER_TYPES:
            raise ValueError(f"Unsupported inverter type: {v}. Supported: {', '.join(SUPPORTED_INVERTER_TYPES)}")
        return v

class ErrorResponse(BaseModel):
    detail: str
    timestamp: str
    request_id: str | None = None


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/api/inverters", tags=["Inverters"])
def list_inverters():
    """List all configured inverters with current status."""
    return [_public(inv) for inv in inverters.values()]


@app.post("/api/inverters", status_code=201, tags=["Inverters"])
def add_inverter(body: InverterCreate):
    """Add a new inverter for monitoring."""
    # Check for duplicates
    for inv in inverters.values():
        if inv["host"] == body.host and inv["port"] == body.port and inv["serial"] == body.serial:
            raise HTTPException(409, "Inverter with same host/port/serial already exists")
    
    inv_id = str(uuid.uuid4())
    inv = {
        "id":          inv_id,
        "name":        body.name,
        "host":        body.host,
        "port":        body.port,
        "serial":      body.serial,
        "type":        body.type,
        "slave":       body.slave,
        "status":      "unknown",
        "last_data":   None,
        "last_update": None,
        "created_at":  datetime.now(tz=timezone.utc).isoformat(),
        "poll_count":  0,
        "poll_errors": 0,
    }
    inverters[inv_id] = inv
    save_config()
    log.info(f"Added inverter: {body.name} ({body.host}:{body.port})")
    # Kick off first poll in background
    import threading
    threading.Thread(target=poll_inverter, args=(inv_id,), daemon=True).start()
    return _public(inv)


@app.get("/api/inverters/{inv_id}", tags=["Inverters"])
def get_inverter(inv_id: str):
    """Get details of a specific inverter."""
    inv = _require(inv_id)
    return _public(inv)


@app.put("/api/inverters/{inv_id}", tags=["Inverters"])
def update_inverter(inv_id: str, body: InverterUpdate):
    """Update inverter configuration."""
    inv = _require(inv_id)
    changed = False
    for field in ("name", "host", "port", "serial", "type", "slave"):
        val = getattr(body, field)
        if val is not None and inv.get(field) != val:
            inv[field] = val
            changed = True
    if changed:
        # Re-create poller with new settings
        _remove_poller(inv_id)
        inv["status"] = "unknown"  # Reset status when config changes
        inv["last_data"] = None
        save_config()
        log.info(f"Updated inverter: {inv['name']}")
        import threading
        threading.Thread(target=poll_inverter, args=(inv_id,), daemon=True).start()
    return _public(inv)


@app.delete("/api/inverters/{inv_id}", status_code=204, tags=["Inverters"])
def delete_inverter(inv_id: str):
    """Delete an inverter."""
    inv = _require(inv_id)
    _remove_poller(inv_id)
    del inverters[inv_id]
    save_config()
    log.info(f"Deleted inverter: {inv['name']}")


@app.post("/api/inverters/{inv_id}/refresh", tags=["Inverters"])
def refresh_inverter(inv_id: str):
    """Trigger immediate poll of inverter."""
    _require(inv_id)
    import threading
    threading.Thread(target=poll_inverter, args=(inv_id,), daemon=True).start()
    return {"status": "queued"}


@app.get("/api/inverters/{inv_id}/history", tags=["Data"])
def get_history(inv_id: str, metric: str, hours: int = Query(24, ge=1, le=720)):
    """Get historical data for a metric (max 30 days)."""
    _require(inv_id)
    if not influx:
        raise HTTPException(503, "InfluxDB not available")
    data = influx.query_history(inv_id, metric, hours)
    return data


@app.get("/api/inverters/{inv_id}/metrics", tags=["Data"])
def get_available_metrics(inv_id: str):
    """Get list of available metrics for inverter."""
    _require(inv_id)
    if not influx:
        return []
    return influx.query_available_metrics(inv_id)


@app.get("/api/health", tags=["System"])
def health():
    """Get system health and statistics."""
    online = sum(1 for inv in inverters.values() if inv["status"] == "online")
    offline = sum(1 for inv in inverters.values() if inv["status"] == "offline")
    return {
        "status": "ok",
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "inverters": {
            "total": len(inverters),
            "online": online,
            "offline": offline,
            "unknown": len(inverters) - online - offline,
        },
        "polling": {
            "interval_seconds": POLL_INTERVAL,
            "total_polls": POLL_STATS["total"],
            "successful": POLL_STATS["success"],
            "failed": POLL_STATS["failure"],
            "last_poll": POLL_STATS["last_poll"],
        },
        "influxdb": {
            "connected": influx is not None,
        },
        "supported_types": list(SUPPORTED_INVERTER_TYPES),
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _require(inv_id: str) -> dict:
    inv = inverters.get(inv_id)
    if not inv:
        raise HTTPException(404, f"Inverter {inv_id} not found")
    return inv


def _public(inv: dict) -> dict:
    return {
        "id":          inv["id"],
        "name":        inv["name"],
        "host":        inv["host"],
        "port":        inv["port"],
        "serial":      inv.get("serial", ""),
        "type":        inv["type"],
        "slave":       inv.get("slave", 1),
        "status":      inv.get("status", "unknown"),
        "last_update": inv.get("last_update"),
        "data":        inv.get("last_data"),
        "created_at":  inv.get("created_at"),
        "poll_count":  inv.get("poll_count", 0),
        "poll_errors": inv.get("poll_errors", 0),
    }
