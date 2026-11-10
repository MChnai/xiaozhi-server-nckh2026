"""Synchronous file validation must never run a nested asyncio event loop."""
from config.config_loader import read_config, get_project_dir, load_config
from pathlib import Path
config_file_valid = False

def check_config_file():
    global config_file_valid
    if config_file_valid:
        return
    path = Path(get_project_dir())/"data/.config.yaml"
    if not path.is_file():
        raise FileNotFoundError("Thiếu data/.config.yaml. Chạy bộ cài v3 hoặc voice-entrypoint.")
    custom = read_config(path)
    if not isinstance(custom, dict):
        raise ValueError("data/.config.yaml phải là cấu hình YAML dạng object")
    if custom.get("manager-api", {}).get("url") and custom.get("selected_module") is not None:
        raise ValueError("Không trộn selected_module cục bộ với manager-api. Chọn mô hình trên web.")
    config_file_valid = True
