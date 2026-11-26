"""Đọc VietQR bằng chính logic của skill `vietqr` (`.claude/skills/vietqr/scripts/vietqr.py`).

Nạp file skill theo đường dẫn để chỉ có MỘT nguồn logic (không sao chép → không lệch).
Docker/deploy phải kèm file này (hoặc đặt VIETQR_SCRIPT_PATH).
"""
import importlib.util
import sys
from dataclasses import asdict
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=4)
def _load_vietqr(path: str):
    spec = importlib.util.spec_from_file_location("tkc_vietqr_skill", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Không nạp được vietqr từ {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclass cần module có trong sys.modules khi exec
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(spec.name, None)
        raise
    return module


def parse_vietqr(payload: str, script_path: Path) -> dict:
    """Trả dict các trường của VietQR. Ném ValueError (tiếng Việt) nếu chuỗi không phải TLV hợp lệ."""
    return asdict(_load_vietqr(str(script_path)).parse(payload))
