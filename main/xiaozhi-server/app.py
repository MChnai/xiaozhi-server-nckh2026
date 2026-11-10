"""Vietnamese Robot server. Fatal initialization/service failures exit with code 1."""
import asyncio
import os
os.environ.setdefault("ORT_DISABLE_TELEMETRY", "1")
import signal
import sys

async def wait_for_exit():
    event = asyncio.Event()
    loop = asyncio.get_running_loop()
    if sys.platform != "win32":
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, event.set)
    await event.wait()

async def main():
    from config.settings import load_config
    config = await load_config()
    from config.logger import setup_logging
    logger = setup_logging(config).bind(tag="startup")
    from core.utils.util import check_ffmpeg_installed
    check_ffmpeg_installed()
    logger.info("Bước 1/3: đã đọc cấu hình API; đang nạp VAD và PhoWhisper CPU...")
    from core.websocket_server import WebSocketServer
    from core.http_server import SimpleHttpServer
    from core.service_supervisor import run_services
    from core.utils.gc_manager import get_gc_manager
    # Model initialization finishes before the listeners can report ready.
    ws = WebSocketServer(config)
    http = SimpleHttpServer(config, ws)
    logger.info("Bước 2/3: đã nạp mô hình; đang mở cổng WebSocket và HTTP...")
    gc = get_gc_manager(interval_seconds=300)
    await gc.start()
    def ready():
        logger.info("Bước 3/3: voice SẴN SÀNG — WebSocket và HTTP đã mở; VAD/ASR đã nạp.")
    async def reminders():
        await ws.reminder_service.run()
    # The scheduler has no listening socket, but its task is still supervised.
    reminder_ready = asyncio.Event()
    reminder_ready.set()
    try:
        services = [("WebSocket", ws.start, ws.ready), ("HTTP", http.start, http.ready)]
        if ws.reminder_service.enabled:
            services.append(("Nhắc nhở", reminders, reminder_ready))
        await run_services(services, wait_for_exit, startup_timeout=120, on_ready=ready)
    finally:
        await gc.stop()
        logger.info("Máy chủ đã dừng.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Đã dừng theo yêu cầu.", flush=True)
    except Exception as error:
        # Include the original exception type/message, never a full config/token.
        cause = error.__cause__ or error
        print(f"[LỖI KHỞI ĐỘNG] {type(error).__name__}: {error}. Nguyên nhân: {type(cause).__name__}: {cause}", file=sys.stderr, flush=True)
        raise SystemExit(1)
