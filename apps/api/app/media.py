import subprocess
from contextlib import contextmanager
from threading import BoundedSemaphore

from .analyzer.contract import AnalyzerError
from .config import ROOT

MEDIA_WORKER = ROOT / "apps" / "api" / "tools" / "media" / "worker.cjs"
WORKERS = BoundedSemaphore(3)


@contextmanager
def media_slot():
    if not WORKERS.acquire(blocking=False):
        raise AnalyzerError(429, "Đang có nhiều ảnh được xử lý. Hãy thử lại sau vài giây.")
    try:
        yield
    finally:
        WORKERS.release()


def read_media(mode, data, settings, *args, timeout):
    result = subprocess.run(
        [settings.node_command, str(MEDIA_WORKER), mode, *args],
        input=data, capture_output=True, check=True, timeout=timeout,
    )
    return result.stdout.decode("utf-8", errors="replace")
