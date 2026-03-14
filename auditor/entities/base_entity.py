from __future__ import annotations

from typing import Any


def to_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)
