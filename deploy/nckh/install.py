"""Fresh install/resume with finite staged health waits. Python standard library only."""
import argparse
import datetime
import json
import queue
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from project import ROOT, compose_command, ensure_env, process_env, redact

class InstallError(RuntimeError):
    pass

def decode_rows(output):
    text = output.strip()
    if not text:
        return []
    if text.startswith("["):
        return json.loads(text)
    return [json.loads(line) for line in text.splitlines() if line.strip()]

def evaluate_health(rows, service):
    relevant = [r for r in rows if r.get("Service") == service]
    if not relevant:
        return "waiting", "chưa có container"
    row = relevant[0]
    state = row.get("State", "").lower()
    health = (row.get("Health") or "").lower()
    if state in ("exited", "dead", "restarting", "removing") or health == "unhealthy":
        return "failed", f"state={state}, health={health or 'chưa có'}"
    if state == "running" and health == "healthy":
        return "ready", "healthy"
    return "waiting", f"state={state or 'đang tạo'}, health={health or 'starting'}"

class Installer:
    def __init__(self, settings, args):
        self.settings, self.args = settings, args
        self.command = compose_command()
        self.env = process_env()
        folder = ROOT/"diagnostics"
        folder.mkdir(exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.log = folder/("install-"+stamp+".log")
    def print(self, message):
        message = redact(str(message), self.settings)
        print(message, flush=True)
        with self.log.open("a", encoding="utf-8") as file:
            file.write(message+"\n")
    def capture(self, command, timeout=30):
        return subprocess.run(command, cwd=ROOT, env=self.env, text=True, encoding="utf-8",
                              errors="replace", stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    def run(self, parts, timeout=600, compose=True):
        command = (self.command if compose else []) + parts
        process = subprocess.Popen(command, cwd=ROOT, env=self.env, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", bufsize=1)
        output = queue.Queue()
        def read():
            try:
                for line in process.stdout:
                    output.put(line.rstrip())
            finally:
                output.put(None)
        thread = threading.Thread(target=read, daemon=True)
        thread.start()
        start = tick = time.monotonic()
        try:
            while True:
                if time.monotonic()-start > timeout:
                    raise InstallError("Hết thời gian thực hiện: "+" ".join(parts[:4]))
                try:
                    line = output.get(timeout=1)
                    if line is None:
                        break
                    self.print(line)
                except queue.Empty:
                    if time.monotonic()-tick >= 20:
                        self.print(f"... đang thực hiện, đã qua {int(time.monotonic()-start)} giây")
                        tick = time.monotonic()
            result = process.wait(timeout=10)
            if result:
                raise InstallError(f"Lệnh thất bại (mã {result}): "+" ".join(parts[:4]))
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            process.stdout.close()
    def wait(self, service):
        start = time.monotonic()
        tick = 0
        while time.monotonic()-start < self.args.wait_timeout:
            result = self.capture(self.command+["ps", "-a", "--format", "json", service], timeout=20)
            if result.returncode:
                raise InstallError("Không đọc được trạng thái Docker: "+redact(result.stderr, self.settings))
            state, detail = evaluate_health(decode_rows(result.stdout), service)
            if state == "ready":
                self.print(f"[ĐẠT] {service}: healthy")
                return
            if state == "failed":
                raise InstallError(f"{service} thất bại: {detail}")
            if time.monotonic()-tick >= 15:
                self.print(f"[CHỜ] {service}: {detail}; {int(time.monotonic()-start)}/{self.args.wait_timeout} giây")
                tick = time.monotonic()
            threading.Event().wait(3)
        raise InstallError(f"{service} chưa healthy sau {self.args.wait_timeout} giây. Đã dừng chờ.")
    def diagnostics(self):
        for command in (["ps", "-a"], ["logs", "--no-color", "--tail", "100", "api", "voice", "web", "piper"]):
            try:
                result = self.capture(self.command+command)
                self.print(result.stdout or result.stderr)
            except Exception as exc:
                self.print("Không lấy được chẩn đoán: "+type(exc).__name__)
    def free_ports(self):
        # Only stop an old project when explicitly requested; keep every old volume.
        if self.args.stop_previous:
            old = self.capture(["docker", "ps", "-q", "--filter", "label=com.docker.compose.project=robot-ai-viet"])
            if old.returncode:
                raise InstallError("Không đọc được project cũ")
            ids = old.stdout.split()
            if ids:
                self.print("Dừng container project v1/v2 robot-ai-viet; giữ nguyên dữ liệu cũ.")
                self.run(["docker", "stop", *ids], timeout=90, compose=False)
        for port in (8000, 8002):
            probe = socket.socket()
            try:
                probe.bind(("0.0.0.0", port))
            except OSError:
                # An existing healthy v3 installation may own its own ports.
                result = self.capture(["docker", "ps", "--format", "json", "--filter", "label=com.docker.compose.project=robot-ai-viet-v3"])
                rows = decode_rows(result.stdout) if result.returncode == 0 else []
                if not any(f":{port}->" in r.get("Ports", "") for r in rows):
                    raise InstallError(f"Cổng {port} đang bị chiếm. Dừng dịch vụ đó hoặc dùng --stop-previous nếu là bản v1/v2.")
            finally:
                probe.close()
    def install(self):
        self.print("Robot Việt v3 — cài mới hoặc tiếp tục cài đặt đang dở.")
        info = self.capture(["docker", "info", "--format", "{{.OSType}}"])
        if info.returncode or info.stdout.strip() != "linux":
            raise InstallError("Mở Docker Desktop và chuyển sang Linux containers, rồi chạy lại lệnh.")
        self.run(["config", "--quiet"], timeout=30)
        self.free_ports()
        if not self.args.skip_build:
            # Sequential builds reduce memory pressure on a 16 GB laptop.
            for name in ("api", "voice", "web", "piper", "model-setup"):
                self.print("[BUILD] "+name)
                self.run(["--profile", "setup", "--progress", "plain", "build", name], timeout=self.args.build_timeout)
        self.print("[MÔ HÌNH] Tải/chuyển PhoWhisper một lần; lần sau kiểm tra cache.")
        self.run(["--profile", "setup", "run", "--rm", "--no-deps", "model-setup"], timeout=self.args.model_timeout)
        for group in (("db", "redis"), ("api",), ("piper",), ("voice",), ("web",)):
            self.print("[KHỞI ĐỘNG] "+", ".join(group))
            self.run(["up", "-d", "--no-deps", *group], timeout=180)
            for name in group:
                self.wait(name)
        self.run([sys.executable, "deploy/nckh/check_server.py", "--host", "127.0.0.1"], timeout=90, compose=False)
        self.print("[HOÀN TẤT] Mở http://"+self.settings["NCKH_PUBLIC_HOST"]+":8002 rồi đăng ký tài khoản và tạo trợ lý.")
        self.print("Vào Khác → Kiểm thử server để thử ASR/TTS, hội thoại, plugin và MCP mô phỏng.")

def main():
    parser = argparse.ArgumentParser(description="Cài server Robot Việt v3 từ đầu, không cần Python packages trên Windows")
    parser.add_argument("--host", required=True, help="IPv4 LAN của máy chạy Docker")
    parser.add_argument("--stop-previous", action="store_true", help="Dừng project v1/v2 robot-ai-viet, giữ mọi volume")
    parser.add_argument("--skip-build", action="store_true", help="Chỉ dùng khi image v3 đã build thành công")
    parser.add_argument("--wait-timeout", type=int, default=300, help="Số giây chờ healthy cho từng dịch vụ")
    parser.add_argument("--build-timeout", type=int, default=2400)
    parser.add_argument("--model-timeout", type=int, default=2400)
    args = parser.parse_args()
    if min(args.wait_timeout, args.build_timeout, args.model_timeout) <= 0:
        parser.error("Thời gian chờ phải lớn hơn 0")
    if not shutil.which("docker"):
        parser.error("Chưa tìm thấy Docker. Cài/mở Docker Desktop rồi mở lại PowerShell.")
    installer = None
    try:
        if not (ROOT/".env").is_file():
            existing=subprocess.run(["docker","volume","inspect","robot-ai-viet-v3_mysql-data"],
                cwd=ROOT,env=process_env(),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=20)
            if existing.returncode==0:
                raise InstallError("Đã có DB v3 nhưng thiếu .env. Chép lại .env từ thư mục v3 trước đó để giữ đúng mật khẩu; không tạo mật khẩu mới cho DB cũ.")
        settings = ensure_env(args.host)
        installer = Installer(settings, args)
        installer.install()
    except (InstallError, ValueError, OSError, subprocess.SubprocessError, KeyboardInterrupt) as exc:
        if installer:
            installer.print("[DỪNG] "+(str(exc) or type(exc).__name__))
            installer.diagnostics()
            installer.print("Nhật ký đã ẩn khóa: "+str(installer.log))
        else:
            print("[LỖI]", exc, file=sys.stderr)
        return 1
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
