"""
Parser for Deye/Solarman register definitions.
Handles rules 1-6 as defined in the YAML parameter files.
"""
import struct


def _to_signed16(val: int) -> int:
    return val - 65536 if val > 32767 else val


def _to_signed32(val: int) -> int:
    return val - 4294967296 if val > 2147483647 else val


def parse_registers(item: dict, register_map: dict[int, int]) -> float | str | None:
    """
    Given a parameter item definition and a flat {register_addr: raw_value} map,
    return the decoded value or None if any register is missing.
    """
    regs = item.get("registers", [])
    rule = item.get("rule", 1)
    scale = item.get("scale", 1)
    offset = item.get("offset", 0)
    lookup = item.get("lookup")

    # Fetch raw register values
    raw_vals = []
    for r in regs:
        if r not in register_map:
            return None
        raw_vals.append(register_map[r])

    if not raw_vals:
        return None

    try:
        if rule == 1:
            # Unsigned 16-bit
            value = raw_vals[0]
            if offset:
                value = (value - offset) * scale
            else:
                value = value * scale

        elif rule == 2:
            # Signed 16-bit
            value = _to_signed16(raw_vals[0])
            if offset:
                value = (value - offset) * scale
            else:
                value = value * scale

        elif rule == 3:
            # Unsigned 32-bit: high word first
            value = ((raw_vals[0] << 16) | raw_vals[1]) * scale

        elif rule == 4:
            # Unsigned 32-bit: low word first
            value = ((raw_vals[1] << 16) | raw_vals[0]) * scale

        elif rule == 5:
            # ASCII string from registers (2 chars per 16-bit word)
            chars = []
            for w in raw_vals:
                hi = (w >> 8) & 0xFF
                lo = w & 0xFF
                if hi:
                    chars.append(chr(hi))
                if lo:
                    chars.append(chr(lo))
            return "".join(chars).strip()

        elif rule == 6:
            # Alert bitfield — return hex representation
            parts = [f"{v:04X}" for v in raw_vals]
            return " ".join(parts)

        else:
            value = raw_vals[0] * scale

    except Exception:
        return None

    # Apply lookup table for string values
    if lookup and item.get("isstr"):
        key = int(value)
        for entry in lookup:
            if entry["key"] == key:
                return entry["value"]
        return str(key)

    # Round to avoid float noise
    if isinstance(value, float):
        decimals = len(str(scale).rstrip("0").split(".")[-1]) if "." in str(scale) else 0
        value = round(value, max(decimals, 2))

    return value


def parse_all(parameter_definition: dict, register_map: dict[int, int]) -> dict:
    """
    Parse all parameters from the YAML definition against the register map.
    Returns {group: {name: value, ...}, ...}
    """
    result = {}
    for group_def in parameter_definition.get("parameters", []):
        group_name = group_def["group"]
        group_data = {}
        for item in group_def.get("items", []):
            name = item["name"]
            value = parse_registers(item, register_map)
            if value is not None:
                group_data[name] = {
                    "value": value,
                    "uom": item.get("uom", ""),
                    "class": item.get("class", ""),
                }
        result[group_name] = group_data
    return result
