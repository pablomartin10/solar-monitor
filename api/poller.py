"""
Inverter polling via PySolarmanV5 + YAML register definitions.
"""
import logging
import threading
import yaml
from pathlib import Path
from pysolarmanv5 import PySolarmanV5
from parser import parse_all

log = logging.getLogger(__name__)

CONFIG_DIR = Path("/app/config")
YAML_MAP = {
    "hybrid": "deye_hybrid.yaml",
    "4mppt":  "deye_4mppt.yaml",
    "micro": "deye_micro.yaml",
    "sg04_sg02": "deye_sg04_sg02.yaml",
}
RETRY_ATTEMPTS = 2


def _load_definition(inv_type: str) -> dict:
    filename = YAML_MAP.get(inv_type, "deye_hybrid.yaml")
    with open(CONFIG_DIR / filename) as f:
        return yaml.full_load(f)


def _build_register_map(modbus: PySolarmanV5, requests: list) -> dict[int, int]:
    """Read all requested register ranges and return a flat addr→value dict."""
    register_map = {}
    for req in requests:
        start = req["start"]
        end = req["end"]
        mb_fc = req.get("mb_functioncode", 3)
        length = end - start + 1

        for attempt in range(RETRY_ATTEMPTS):
            try:
                if mb_fc == 4:
                    values = modbus.read_input_registers(register_addr=start, quantity=length)
                else:
                    values = modbus.read_holding_registers(register_addr=start, quantity=length)
                for i, v in enumerate(values):
                    register_map[start + i] = v
                break
            except Exception as e:
                if attempt == RETRY_ATTEMPTS - 1:
                    raise
                log.warning(f"Register range {start:#06x}-{end:#06x}: attempt {attempt+1} failed: {e}")
    return register_map


class InverterPoller:
    """Thread-safe inverter poller. One instance per inverter."""

    def __init__(self, inv_id: str, name: str, host: str, port: int,
                 serial: int, slave_id: int, inv_type: str):
        self.id = inv_id
        self.name = name
        self.host = host
        self.port = port
        self.serial = serial
        self.slave_id = slave_id
        self.inv_type = inv_type
        self._modbus: PySolarmanV5 | None = None
        self._lock = threading.Lock()
        self._definition = _load_definition(inv_type)

    def _connect(self):
        if self._modbus is None:
            log.info(f"[{self.name}] Connecting to {self.host}:{self.port}")
            self._modbus = PySolarmanV5(
                self.host, self.serial,
                port=self.port,
                mb_slave_id=self.slave_id,
                logger=None,
                auto_reconnect=True,
                socket_timeout=15,
            )

    def _disconnect(self):
        if self._modbus:
            try:
                self._modbus.disconnect()
            except Exception:
                pass
            finally:
                self._modbus = None

    def poll(self) -> dict:
        """
        Connect, read all registers, parse and return structured data.
        Raises on failure.
        """
        with self._lock:
            try:
                self._connect()
                requests = self._definition["requests"]
                register_map = _build_register_map(self._modbus, requests)
                data = parse_all(self._definition, register_map)
                return data
            except Exception as e:
                log.error(f"[{self.name}] Poll failed: {e}")
                self._disconnect()
                raise

    def close(self):
        with self._lock:
            self._disconnect()
