import asyncio
from aiohttp import web
from config.logger import setup_logging
from core.api.ota_handler import OTAHandler
from core.api.vision_handler import VisionHandler

TAG = __name__


class SimpleHttpServer:
    def __init__(self, config: dict, ws_server=None):
        self.config = config
        self.ready = asyncio.Event()
        self.runner = None
        self.ws_server = ws_server
        self.logger = setup_logging()
        self.ota_handler = OTAHandler(config)
        self.vision_handler = VisionHandler(config)

    def _get_websocket_url(self, local_ip: str, port: int) -> str:
        """获取websocket地址

        Args:
            local_ip: 本地IP地址
            port: 端口号

        Returns:
            str: websocket地址
        """
        server_config = self.config["server"]
        websocket_config = server_config.get("websocket")

        if websocket_config and "你" not in websocket_config:
            return websocket_config
        else:
            return f"ws://{local_ip}:{port}/xiaozhi/v1/"

    async def start(self):
        try:
            server_config = self.config["server"]
            read_config_from_api = self.config.get("read_config_from_api", False)
            host = server_config.get("ip", "0.0.0.0")
            port = int(server_config.get("http_port", 8003))

            if port:
                app = web.Application(client_max_size=12 * 1024 * 1024)
                async def health(request):
                    ready = self.ready.is_set() and bool(self.ws_server and self.ws_server.ready.is_set())
                    return web.json_response({"ready": ready, "version": "3.0.0",
                        "websocket": bool(self.ws_server and self.ws_server.ready.is_set()),
                        "http": self.ready.is_set(), "asr_loaded": bool(self.ws_server and self.ws_server._asr),
                        "vad_loaded": bool(self.ws_server and self.ws_server._vad)}, status=200 if ready else 503)
                app.router.add_get('/healthz', health)
                if self.ws_server:
                    from core.api.nckh_handler import NckhHandler
                    handler=NckhHandler(self.config,self.ws_server)
                    app.router.add_post('/_nckh/probe',handler.probe)
                    app.router.add_post('/_nckh/online',handler.online)

                if not read_config_from_api:
                    # 如果没有开启智控台，只是单模块运行，就需要再添加简单OTA接口，用于下发websocket接口
                    app.add_routes(
                        [
                            web.get("/xiaozhi/ota/", self.ota_handler.handle_get),
                            web.post("/xiaozhi/ota/", self.ota_handler.handle_post),
                            web.options(
                                "/xiaozhi/ota/", self.ota_handler.handle_options
                            ),
                            # 下载接口，仅提供 data/bin/*.bin 下载
                            web.get(
                                "/xiaozhi/ota/download/{filename}",
                                self.ota_handler.handle_download,
                            ),
                            web.options(
                                "/xiaozhi/ota/download/{filename}",
                                self.ota_handler.handle_options,
                            ),
                        ]
                    )
                # 添加路由
                app.add_routes(
                    [
                        web.get("/mcp/vision/explain", self.vision_handler.handle_get),
                        web.post(
                            "/mcp/vision/explain", self.vision_handler.handle_post
                        ),
                        web.options(
                            "/mcp/vision/explain", self.vision_handler.handle_options
                        ),
                    ]
                )

                # 运行服务
                runner = web.AppRunner(app)
                self.runner = runner
                await runner.setup()
                site = web.TCPSite(runner, host, port)
                await site.start()
                self.ready.set()

                # 保持服务运行
                while True:
                    await asyncio.sleep(3600)
            else:
                raise ValueError("Cổng HTTP phải khác 0 để kiểm tra trạng thái")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"HTTP服务器启动失败: {e}")
            import traceback

            self.logger.bind(tag=TAG).error(f"错误堆栈: {traceback.format_exc()}")
            raise
        finally:
            self.ready.clear()
            if self.runner:
                await self.runner.cleanup()
