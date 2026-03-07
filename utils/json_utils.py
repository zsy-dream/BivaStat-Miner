from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd
from flask.json.provider import DefaultJSONProvider


def to_json_compatible(value: Any) -> Any:
    """递归将 numpy / pandas 等对象转换为 JSON 可序列化的原生类型。"""
    if isinstance(value, dict):
        return {str(k): to_json_compatible(v) for k, v in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [to_json_compatible(item) for item in value]

    if isinstance(value, np.ndarray):
        return [to_json_compatible(item) for item in value.tolist()]

    if isinstance(value, (np.integer, np.signedinteger, np.unsignedinteger)):
        return int(value)

    if isinstance(value, (np.floating, Decimal)):
        return float(value)

    if isinstance(value, (np.bool_,)):
        return bool(value)

    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()

    if isinstance(value, pd.Timedelta):
        return str(value)

    if isinstance(value, pd.Series):
        return {str(k): to_json_compatible(v) for k, v in value.to_dict().items()}

    if isinstance(value, pd.Index):
        return [to_json_compatible(item) for item in value.tolist()]

    if isinstance(value, pd.DataFrame):
        return [to_json_compatible(row) for row in value.to_dict(orient='records')]

    if hasattr(value, 'item') and callable(getattr(value, 'item')):
        try:
            return to_json_compatible(value.item())
        except Exception:
            pass

    return value


class AppJSONProvider(DefaultJSONProvider):
    """Flask JSON provider with numpy / pandas compatibility."""

    def default(self, obj: Any) -> Any:
        converted = to_json_compatible(obj)
        if isinstance(converted, (dict, list, str, int, float, bool)) or converted is None:
            return converted
        return super().default(obj)
