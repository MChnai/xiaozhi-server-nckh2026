import sys
import types
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "main/xiaozhi-server"))

@pytest.fixture
def lightweight_logger(monkeypatch):
    # Unit tests avoid booting unrelated ASR/cloud providers through the logger.
    from loguru import logger
    module = types.ModuleType("config.logger")
    module.setup_logging = lambda *a, **kw: logger
    monkeypatch.setitem(sys.modules, "config.logger", module)
    return logger
