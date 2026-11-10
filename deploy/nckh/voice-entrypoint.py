"""Validate local prerequisites before starting the supervised server."""
import os
os.environ.setdefault("ORT_DISABLE_TELEMETRY", "1")
import sys
from pathlib import Path
import yaml

secret = os.environ.get("NCKH_SERVER_SECRET", "")
if len(secret) < 32:
    raise SystemExit("NCKH_SERVER_SECRET cần ít nhất 32 ký tự. Chạy install.py.")
mode = os.environ.get("NCKH_LLM_MODE", "demo").strip().lower()
if mode not in ("demo", "deepseek"):
    raise SystemExit("NCKH_LLM_MODE phải là demo hoặc deepseek")
if mode == "deepseek" and not os.environ.get("DEEPSEEK_API_KEY", "").strip():
    raise SystemExit("Đã chọn deepseek nhưng thiếu DEEPSEEK_API_KEY. Dùng demo để thử không cần API.")
model = Path(os.environ.get("PHOWHISPER_MODEL_PATH", "/model-store/phowhisper-small-ct2"))
required = ("model.bin", "config.json", "tokenizer.json", "preprocessor_config.json", "vocabulary.json")
missing = [name for name in required if not (model/name).is_file() or not (model/name).stat().st_size]
if missing:
    raise SystemExit("PhoWhisper chưa hoàn chỉnh: " + ", ".join(missing) + ". Chạy python deploy/nckh/install.py --host <IP LAN>.")
print("[KHỞI ĐỘNG] Đã kiểm tra cấu hình và tệp PhoWhisper. Đang đọc API...", flush=True)
config = {
    "server": {"ip": "0.0.0.0", "port": 8000, "http_port": 8003,
        "auth_key": secret, "timezone_offset": 7,
        "vision_explain": "http://" + os.environ["NCKH_PUBLIC_HOST"] + ":8002/mcp/vision/explain"},
    "manager-api": {"url": "http://api:8003/xiaozhi", "secret": secret},
    "reminders": {"enabled": True}, "prompt_template": "agent-base-prompt-vi.txt"}
Path("data").mkdir(exist_ok=True)
Path("data/.config.yaml").write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
os.execv(sys.executable, [sys.executable, "-u", "app.py"])
