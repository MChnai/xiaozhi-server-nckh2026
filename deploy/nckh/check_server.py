import argparse
import json
import urllib.request
import sys

def check(host):
    checks = [(8002,"/healthz","Web"), (8002,"/nckhsv/ota/","OTA tương thích firmware"),
              (8002,"/xiaozhi/ota/","OTA gốc"), (8000,"/","Cổng WebSocket"),
              (8002,"/voice/healthz","Voice: ASR/VAD + HTTP + WebSocket")]
    failures = 0
    for port, path, label in checks:
        try:
            with urllib.request.urlopen(f"http://{host}:{port}{path}", timeout=8) as response:
                body = response.read(4096).decode("utf-8")
                if path.endswith('/ota/') and "bình thường" not in body:
                    raise ValueError("OTA không trả về trạng thái mong đợi")
                if path == '/voice/healthz':
                    health = json.loads(body)
                    if not all(health.get(key) for key in ('ready','asr_loaded','vad_loaded','websocket','http')):
                        raise ValueError("Voice chưa nạp xong các thành phần")
                print(f"[ĐẠT] {label}: HTTP {response.status} — {body.strip()}")
        except Exception as exc:
            failures += 1
            print(f"[LỖI] {label}: {exc}")
    return 1 if failures else 0
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Kiểm tra trạng thái sẵn sàng Robot Việt v3")
    parser.add_argument('--host', default='127.0.0.1')
    raise SystemExit(check(parser.parse_args().host))
