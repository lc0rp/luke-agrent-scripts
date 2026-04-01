from __future__ import annotations

import copy
import re
from typing import Any


_DELTA_RE = re.compile(r"^[+-](?:\d+(?:\.\d+)?|\.\d+)$")
_NUMBER_RE = re.compile(r"^-?(?:\d+(?:\.\d+)?|\.\d+)$")
_BBOX_INDEX = {
    "x0": 0,
    "left": 0,
    "y0": 1,
    "top": 1,
    "x1": 2,
    "right": 2,
    "y1": 3,
    "bottom": 3,
}


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def parse_delta(value: Any) -> float | None:
    if is_number(value):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if _DELTA_RE.match(stripped):
            return float(stripped)
    return None


def parse_number(value: Any) -> float | None:
    if is_number(value):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if _NUMBER_RE.match(stripped):
            return float(stripped)
    return None


def apply_numeric_override(current: Any, override: Any) -> Any:
    if not is_number(current):
        return copy.deepcopy(override)
    delta = parse_delta(override)
    if delta is not None:
        resolved = float(current) + delta
    else:
        number = parse_number(override)
        if number is None:
            return copy.deepcopy(override)
        resolved = number
    if isinstance(current, int) and float(resolved).is_integer():
        return int(resolved)
    return float(resolved)


def apply_bbox_override(bbox: list[Any], override: Any) -> list[float]:
    resolved = [float(value) for value in bbox[:4]]
    if isinstance(override, list):
        for index, value in enumerate(override[:4]):
            resolved[index] = float(apply_numeric_override(resolved[index], value))
        return resolved
    if not isinstance(override, dict):
        return resolved
    for key, value in override.items():
        if key in _BBOX_INDEX:
            resolved[_BBOX_INDEX[key]] = float(apply_numeric_override(resolved[_BBOX_INDEX[key]], value))
            continue
        if key in {"x", "dx"}:
            delta = parse_delta(value)
            if delta is not None:
                resolved[0] += delta
                resolved[2] += delta
            continue
        if key in {"y", "dy"}:
            delta = parse_delta(value)
            if delta is not None:
                resolved[1] += delta
                resolved[3] += delta
            continue
        if key in {"w", "width", "dw"}:
            delta = parse_delta(value)
            if delta is not None:
                resolved[2] += delta
                continue
            number = parse_number(value)
            if number is not None:
                resolved[2] = resolved[0] + number
            continue
        if key in {"h", "height", "dh"}:
            delta = parse_delta(value)
            if delta is not None:
                resolved[3] += delta
                continue
            number = parse_number(value)
            if number is not None:
                resolved[3] = resolved[1] + number
    return [round(value, 2) for value in resolved]


def apply_override_value(current: Any, override: Any) -> Any:
    if isinstance(current, dict) and isinstance(override, dict):
        resolved = copy.deepcopy(current)
        for key, value in override.items():
            if key == "bbox" and isinstance(resolved.get("bbox"), list):
                resolved["bbox"] = apply_bbox_override(resolved["bbox"], value)
                continue
            resolved[key] = apply_override_value(resolved.get(key), value)
        return resolved
    if isinstance(current, list):
        if len(current) == 4 and all(is_number(value) for value in current):
            return apply_bbox_override(list(current), override)
        if isinstance(override, list):
            resolved = copy.deepcopy(current)
            for index, value in enumerate(override):
                if index < len(resolved):
                    resolved[index] = apply_override_value(resolved[index], value)
                else:
                    resolved.append(copy.deepcopy(value))
            return resolved
        return copy.deepcopy(override)
    if is_number(current):
        return apply_numeric_override(current, override)
    return copy.deepcopy(override)


def apply_custom_override_to_block(block: dict) -> dict:
    override = block.get("custom_override")
    if not isinstance(override, dict) or not override:
        return copy.deepcopy(block)
    resolved = copy.deepcopy(block)
    for key, value in override.items():
        if key == "bbox" and isinstance(resolved.get("bbox"), list):
            resolved["bbox"] = apply_bbox_override(resolved["bbox"], value)
            continue
        resolved[key] = apply_override_value(resolved.get(key), value)
    return resolved


def apply_custom_overrides_to_payload(payload: dict) -> dict:
    resolved = copy.deepcopy(payload)
    resolved["blocks"] = [apply_custom_override_to_block(block) for block in payload.get("blocks", [])]
    return resolved
