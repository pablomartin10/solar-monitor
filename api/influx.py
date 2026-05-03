"""
InfluxDB 2.x writer and query helper.
"""
import logging
import os
from datetime import datetime, timezone
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

log = logging.getLogger(__name__)

INFLUX_URL    = os.getenv("INFLUXDB_URL",    "http://influxdb:8086")
INFLUX_TOKEN  = os.getenv("INFLUXDB_TOKEN",  "")
INFLUX_ORG    = os.getenv("INFLUXDB_ORG",    "solar")
INFLUX_BUCKET = os.getenv("INFLUXDB_BUCKET", "inverters")


class InfluxWriter:
    def __init__(self):
        self._client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        self._write_api  = self._client.write_api(write_options=SYNCHRONOUS)
        self._query_api  = self._client.query_api()

    def write_reading(self, inv_id: str, inv_name: str, inv_type: str, groups: dict):
        """Write all numeric readings from a poll result as InfluxDB points."""
        now = datetime.now(tz=timezone.utc)
        points = []
        for group_name, items in groups.items():
            for metric_name, meta in items.items():
                value = meta["value"]
                if not isinstance(value, (int, float)):
                    continue
                p = (
                    Point("inverter_metric")
                    .tag("inverter_id",   inv_id)
                    .tag("inverter_name", inv_name)
                    .tag("inverter_type", inv_type)
                    .tag("group",         group_name)
                    .tag("metric",        metric_name)
                    .field("value",       float(value))
                    .time(now, WritePrecision.SECONDS)
                )
                points.append(p)
        try:
            self._write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=points)
            log.debug(f"[{inv_name}] Wrote {len(points)} points to InfluxDB")
        except Exception as e:
            log.error(f"[{inv_name}] InfluxDB write error: {e}")

    def query_history(self, inv_id: str, metric: str, hours: int = 24) -> list[dict]:
        """Return time-series data for a specific metric."""
        flux = f'''
from(bucket: "{INFLUX_BUCKET}")
  |> range(start: -{hours}h)
  |> filter(fn: (r) => r._measurement == "inverter_metric")
  |> filter(fn: (r) => r.inverter_id == "{inv_id}")
  |> filter(fn: (r) => r.metric == "{metric}")
  |> filter(fn: (r) => r._field == "value")
  |> sort(columns: ["_time"])
'''
        try:
            result = self._query_api.query(flux, org=INFLUX_ORG)
            rows = []
            for table in result:
                for record in table.records:
                    rows.append({
                        "time":  record.get_time().isoformat(),
                        "value": record.get_value(),
                    })
            return rows
        except Exception as e:
            log.error(f"InfluxDB query error: {e}")
            return []

    def query_available_metrics(self, inv_id: str) -> list[str]:
        """Return distinct metric names stored for this inverter."""
        flux = f'''
import "influxdata/influxdb/schema"
schema.tagValues(
  bucket: "{INFLUX_BUCKET}",
  tag: "metric",
  predicate: (r) => r.inverter_id == "{inv_id}",
  start: -30d
)
'''
        try:
            result = self._query_api.query(flux, org=INFLUX_ORG)
            return [r.get_value() for table in result for r in table.records]
        except Exception:
            return []

    def close(self):
        self._client.close()
