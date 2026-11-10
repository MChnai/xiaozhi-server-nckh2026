"""Create or safely update LAN settings. Never regenerate existing credentials."""
import argparse
from project import ensure_env

def main():
    parser = argparse.ArgumentParser(description="Tạo cấu hình Robot Việt v3")
    parser.add_argument("--host", required=True)
    args = parser.parse_args()
    try:
        settings = ensure_env(args.host)
    except ValueError as exc:
        parser.error(str(exc))
    print("Đã kiểm tra .env; giữ nguyên các mật khẩu đã có. Chế độ:", settings.get("NCKH_LLM_MODE", "demo"))
if __name__ == "__main__":
    main()
