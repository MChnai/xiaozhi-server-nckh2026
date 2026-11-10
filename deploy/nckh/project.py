"""Shared stdlib-only project/env handling for all host-side commands."""
import ipaddress
import json
import os
import re
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_NAMES = {"NCKH_PUBLIC_HOST", "MYSQL_ROOT_PASSWORD", "MYSQL_PASSWORD", "NCKH_SERVER_SECRET",
             "NCKH_LLM_MODE", "DEEPSEEK_API_KEY", "DEEPSEEK_MODEL", "OPENWEATHER_API_KEY",
             "PHOWHISPER_REVISION", "NCKH_TTS_OFFLINE", "VIENEU_PRECISION", "COMPOSE_PROJECT_NAME"}
SECRET_NAMES = ("MYSQL_ROOT_PASSWORD", "MYSQL_PASSWORD", "NCKH_SERVER_SECRET", "DEEPSEEK_API_KEY", "OPENWEATHER_API_KEY")

def parse_env(path):
    values = {}
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)", line)
        if not match:
            raise ValueError(f".env dòng {number} không đúng dạng TEN=gia_tri")
        key, value = match.groups()
        if key in values:
            raise ValueError(f".env có tham số trùng: {key}")
        value = value.strip()
        if value.startswith("'"):
            end = value.rfind("'")
            if end < 1 or (value[end+1:].strip() and not value[end+1:].strip().startswith('#')):
                raise ValueError(f".env dòng {number} thiếu dấu nháy")
            value = value[1:end]
        elif value.startswith('"'):
            try:
                decoded, end = json.JSONDecoder().raw_decode(value)
                if value[end:].strip() and not value[end:].strip().startswith("#"):
                    raise ValueError(f".env dòng {number} có dữ liệu thừa")
                value = decoded
            except json.JSONDecodeError as exc:
                raise ValueError(f".env dòng {number} có dấu nháy không hợp lệ") from exc
            if not isinstance(value, str):
                raise ValueError(f".env dòng {number} phải là chuỗi")
        else:
            value = re.split(r"\s+#", value, 1)[0].strip()
        if "${" in value:
            raise ValueError(f"Dùng giá trị trực tiếp cho {key}, không dùng biến lồng nhau")
        values[key] = value
    return values

def valid_host(host):
    ip = ipaddress.IPv4Address(host)
    if ip.is_loopback or ip.is_unspecified or ip.is_multicast or ip.is_link_local:
        raise ValueError("--host phải là IPv4 LAN của máy chạy Docker, không phải localhost")
    return str(ip)

def validate_env(values):
    valid_host(values.get("NCKH_PUBLIC_HOST", ""))
    for key in ("MYSQL_ROOT_PASSWORD", "MYSQL_PASSWORD", "NCKH_SERVER_SECRET"):
        value = values.get(key, "")
        if len(value) < 32 or re.fullmatch(r"[A-Za-z0-9_-]+", value) is None:
            raise ValueError(f"{key} thiếu hoặc không hợp lệ. Cần ít nhất 32 ký tự chữ/số/_/-. Không tự đổi mật khẩu khi DB đã có dữ liệu.")
    mode = values.get("NCKH_LLM_MODE", "demo")
    if mode not in ("demo", "deepseek"):
        raise ValueError("NCKH_LLM_MODE phải là demo hoặc deepseek")
    if mode == "deepseek" and not values.get("DEEPSEEK_API_KEY", "").strip():
        raise ValueError("Thiếu DEEPSEEK_API_KEY; dùng NCKH_LLM_MODE=demo để thử miễn phí")
    if values.get("COMPOSE_PROJECT_NAME", "robot-ai-viet-v3") != "robot-ai-viet-v3":
        raise ValueError("Bản v3 dùng project robot-ai-viet-v3 để tách DB khỏi bản cũ")
    return values

def ensure_env(host, root=ROOT):
    host = valid_host(host)
    path = root/".env"
    if path.exists():
        values = parse_env(path)
        # Changing the LAN address is safe; preserve all existing credentials.
        text = path.read_text(encoding="utf-8-sig")
        text, count = re.subn(r"(?m)^NCKH_PUBLIC_HOST\s*=.*$", "NCKH_PUBLIC_HOST="+host, text)
        if not count:
            text += "\nNCKH_PUBLIC_HOST="+host+"\n"
        prospective = dict(values, NCKH_PUBLIC_HOST=host)
        validate_env(prospective)
        path.write_text(text, encoding="utf-8")
    else:
        text = (root/"deploy/nckh/.env.example").read_text(encoding="utf-8")
        text = re.sub(r"(?m)^NCKH_PUBLIC_HOST=.*$", "NCKH_PUBLIC_HOST="+host, text)
        for key in ("MYSQL_ROOT_PASSWORD", "MYSQL_PASSWORD", "NCKH_SERVER_SECRET"):
            text = text.replace(key+"=\n", key+"="+secrets.token_hex(24)+"\n")
        path.write_text(text, encoding="utf-8")
        path.chmod(0o600)
    (root/"music").mkdir(exist_ok=True)
    return validate_env(parse_env(path))

def load_env(root=ROOT):
    if not (root/".env").is_file():
        raise ValueError("Chưa có .env. Chạy python deploy/nckh/install.py --host <IP LAN> trước.")
    return validate_env(parse_env(root/".env"))

def compose_command(root=ROOT):
    return ["docker", "compose", "--project-directory", str(root), "--env-file", str(root/".env"),
            "-p", "robot-ai-viet-v3", "-f", str(root/"compose.nckh.yaml")]

def process_env():
    # Giữ .env của dự án làm nguồn cấu hình chính.
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in ENV_NAMES
    }

    # Các tiến trình Python con xuất tiếng Việt bằng UTF-8.
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    return env

def redact(text, values):
    for key in SECRET_NAMES:
        value = values.get(key)
        if value:
            text = text.replace(value, "[ĐÃ ẨN]")
    return re.sub(r"(?i)(Bearer\s+)[A-Za-z0-9._~+/-]+", r"\1[ĐÃ ẨN]", text)
