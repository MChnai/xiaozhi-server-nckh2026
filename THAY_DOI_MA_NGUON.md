> Tài liệu v1. Dùng HUONG_DAN_V2.md, THAY_DOI_V2.md và KET_QUA_KIEM_THU_V2.md cho bản hiện tại.

# Thay đổi mã nguồn Robot AI tiếng Việt

Đối chiếu trực tiếp với `xiaozhi-esp32-server-main(2).zip` được cung cấp, ngày 04/11/2026.

## Kết quả chính

- Tạo cấu hình Docker riêng cho đề tài: web Vue, API Java 21, voice Python, MySQL 8.4, Redis 8.0; image build từ nguồn đã sửa.
- Việt hóa mặc định web/API, prompt, lời chào, hướng dẫn ghép thiết bị, lỗi phổ biến và lời kết thúc. Không thay định danh giao thức.
- Thêm PhoWhisper-small CT2 int8 trên CPU, cache model giữa các thiết bị và khóa inference; model tải riêng từ VinAI.
- Thêm demo không gọi DeepSeek và cấu hình DeepSeek qua môi trường, tên model mặc định `deepseek-flash` theo tài liệu chính thức đã đối chiếu.
- Thêm RSS VnExpress, thời tiết OpenWeather, nhắc nhở theo thiết bị với MySQL; dùng MCP của firmware cho phần cứng.
- Thêm lịch một lần/ngày/tuần, nhắc bù sau offline, claim/retry, lọc thiết bị online và gửi tts/start trước audio.
- Thêm alias OTA `/nckhsv/ota/`, giữ route gốc; WebSocket chấp nhận đường dẫn firmware mô tả.
- Không sửa firmware, không giả định các provider riêng mà tài liệu giảng viên đề cập đã tồn tại trong ZIP.

## Cách dùng

Đọc `HUONG_DAN_VI.md`, bắt đầu bằng `python deploy/nckh/setup.py --host IP_LAN`, sau đó build và chạy `compose.nckh.yaml`.
Mặc định demo không cần trả phí DeepSeek. Chuyển `NCKH_LLM_MODE=deepseek` và đặt API key khi cần hội thoại/gọi công cụ tự nhiên.

## Giới hạn còn lại

Đã build frontend, chạy 93 test frontend và 23 test NCKH, kiểm tra cú pháp Python/SQL. Chưa build JAR Java 21, build/chạy toàn stack Docker, chạy migration thật, suy luận model thật hoặc kiểm thử với robot thật. Xem `KET_QUA_KIEM_THU.md`.

EdgeTTS vẫn cần Internet. Chưa đưa VieNeu/Piper, giá vàng, dịch có IPA, Gmail OAuth hay âm lịch Việt Nam vào cấu hình đã hỗ trợ. Nhắc nhở đánh dấu đã xếp hàng TTS, chưa có ACK từ loa; chưa đảm bảo phát đúng một lần. Cấu hình này chạy một replica voice, trong LAN HTTP/WS.

Các module và dữ liệu mẫu upstream khác được giữ để tra cứu; có thể còn tên provider/log/chú thích tiếng Trung. Trợ lý đã tồn tại không tự đổi model/plugin. Dùng database mới trong lần triển khai đầu; sao lưu trước nếu áp dụng vào dữ liệu đang dùng.

## Danh sách tệp thay đổi

| Loại | Đường dẫn | Nội dung |
|---|---|---|
| Sửa | `.dockerignore` | Loại dependency, build cache, dữ liệu chạy và model tải về khỏi build context; giữ model Silero gốc. |
| Sửa | `.gitignore` | Bỏ qua secret, model tải về và backup. |
| Sửa | `README.md` | Đặt hướng dẫn NCKH ở đầu, giữ nội dung upstream. |
| Sửa | `main/manager-api/src/main/java/xiaozhi/modules/agent/service/impl/AgentServiceImpl.java` | Gán bộ plugin NCKH cho trợ lý mới dùng LLM_NCKH. |
| Sửa | `main/manager-api/src/main/java/xiaozhi/modules/device/controller/OTAController.java` | Health OTA tiếng Việt; cấu hình WebSocket không bắt buộc MQTT. |
| Sửa | `main/manager-api/src/main/java/xiaozhi/modules/security/config/WebMvcConfig.java` | API mặc định tiếng Việt khi không có ngôn ngữ phù hợp. |
| Sửa | `main/manager-web/.env` | Thông tin tiêu đề/miêu tả sản phẩm tiếng Việt khi phát triển. |
| Sửa | `main/manager-web/.env.production` | Tiêu đề/miêu tả tiếng Việt khi build Docker. |
| Sửa | `main/manager-web/public/index.html` | Khai báo lang=vi. |
| Sửa | `main/manager-web/src/i18n/index.js` | Mặc định/fallback tiếng Việt, vẫn giữ lựa chọn ngôn ngữ hợp lệ đã lưu. |
| Sửa | `main/manager-web/src/i18n/vi.js` | Tên sản phẩm Robot AI tiếng Việt. |
| Sửa | `main/manager-web/src/registerServiceWorker.js` | Việt hóa thông báo cập nhật giao diện. |
| Sửa | `main/xiaozhi-server/app.py` | Chạy/dừng scheduler, xử lý stdin EOF trong Docker và log khởi động tiếng Việt. |
| Sửa | `main/xiaozhi-server/config/config_loader.py` | Gộp cấu hình server thay vì làm mất auth/đường dẫn; giữ cấu hình reminders local khi đọc API. |
| Sửa | `main/xiaozhi-server/core/connection.py` | Đăng ký/hủy kết nối theo thiết bị; TTS Việt cả khi chờ ghép, Việt hóa ví dụ và không log toàn bộ headers. |
| Sửa | `main/xiaozhi-server/core/handle/helloHandle.py` | Câu chào Việt; không dùng file wakeup tiếng Trung khi cache thiếu. |
| Sửa | `main/xiaozhi-server/core/handle/receiveAudioHandle.py` | Hướng dẫn ghép và giới hạn sử dụng bằng TTS Việt, bỏ phát asset tiếng Trung trong các luồng này. |
| Sửa | `main/xiaozhi-server/core/providers/llm/openai/openai.py` | Đọc API key từ biến môi trường cấu hình, ưu tiên hơn khóa trong DB. |
| Sửa | `main/xiaozhi-server/core/providers/tools/server_plugins/plugin_executor.py` | Không tự gắn công cụ âm lịch Trung Quốc vào trợ lý NCKH. |
| Sửa | `main/xiaozhi-server/core/utils/dialogue.py` | Thời điểm động có cả ngày và giờ, hỗ trợ phiên kéo dài khi hẹn lịch. |
| Sửa | `main/xiaozhi-server/core/utils/prompt_manager.py` | Ngôn ngữ fallback là Tiếng Việt. |
| Sửa | `main/xiaozhi-server/core/utils/util.py` | Lời báo lỗi mặc định tiếng Việt. |
| Sửa | `main/xiaozhi-server/core/websocket_server.py` | Tạo ReminderService, Việt hóa thông báo kết nối/xác thực. |
| Sửa | `main/xiaozhi-server/plugins_func/functions/handle_exit_intent.py` | Mô tả/câu chào kết thúc tiếng Việt. |
| Thêm | `HUONG_DAN_VI.md` | Tài liệu triển khai, chi phí, phần cứng và giới hạn kiểm thử. |
| Thêm | `KET_QUA_KIEM_THU.md` | Tài liệu triển khai, chi phí, phần cứng và giới hạn kiểm thử. |
| Thêm | `compose.nckh.yaml` | Stack source-build, healthchecks, named volumes, DB/Redis không public. |
| Thêm | `deploy/nckh/.env.example` | Sinh secret, cấu hình IP và chọn demo/DeepSeek. |
| Thêm | `deploy/nckh/Dockerfile-api` | Build Java 21 nhiều giai đoạn, API tách container. |
| Thêm | `deploy/nckh/Dockerfile-model` | Image riêng tải/chuyển PhoWhisper với PyTorch phù hợp. |
| Thêm | `deploy/nckh/Dockerfile-voice` | Đóng gói server Python, thư viện CPU/audio và provider mới. |
| Thêm | `deploy/nckh/Dockerfile-web` | Build Vue từ nguồn local, phục vụ bằng nginx. |
| Thêm | `deploy/nckh/backup_db.py` | Sao lưu MySQL theo luồng byte tương thích PowerShell. |
| Thêm | `deploy/nckh/check_deepseek.py` | Kiểm tra model/key; chỉ gửi chat thật khi thêm --chat. |
| Thêm | `deploy/nckh/check_server.py` | Kiểm tra HTTP web/OTA/cổng voice, không điều khiển thiết bị. |
| Thêm | `deploy/nckh/nginx.conf` | Proxy API, alias OTA /nckhsv/ và endpoint vision. |
| Thêm | `deploy/nckh/prepare_model.py` | Tải VinAI và chuyển CT2 int8, không thay model đã có khi lỗi. |
| Thêm | `deploy/nckh/setup.py` | Sinh secret, cấu hình IP và chọn demo/DeepSeek. |
| Thêm | `deploy/nckh/tests/conftest.py` | Kiểm thử NCKH với cloud/model/DB giả; không thay thế nghiệm thu thiết bị. |
| Thêm | `deploy/nckh/tests/test_deployment.py` | Kiểm thử NCKH với cloud/model/DB giả; không thay thế nghiệm thu thiết bị. |
| Thêm | `deploy/nckh/tests/test_providers_plugins.py` | Kiểm thử NCKH với cloud/model/DB giả; không thay thế nghiệm thu thiết bị. |
| Thêm | `deploy/nckh/tests/test_reminders.py` | Kiểm thử NCKH với cloud/model/DB giả; không thay thế nghiệm thu thiết bị. |
| Thêm | `deploy/nckh/voice-entrypoint.py` | Tạo cấu hình runtime kết nối manager-api, không nhúng khóa vào image. |
| Thêm | `main/manager-api/src/main/java/xiaozhi/modules/config/init/NckhBootstrap.java` | Đồng bộ URL/secret từ môi trường qua API service và cache theo khóa. |
| Thêm | `main/manager-api/src/main/resources/db/changelog/db.changelog-nckh.yaml` | Migration NCKH riêng, include lịch sử gốc không sửa checksum cũ. |
| Thêm | `main/manager-api/src/main/resources/db/changelog/nckh-20261104.sql` | Tạo bảng nhắc nhở, provider/model/giọng/template và tham số Việt. |
| Thêm | `main/xiaozhi-server/agent-base-prompt-vi.txt` | Prompt Việt, công cụ thật, thời gian và MCP. |
| Thêm | `main/xiaozhi-server/core/providers/asr/pho_whisper_ct2.py` | ASR tiếng Việt, model CPU int8 dùng chung, khóa inference, nhận PCM16. |
| Thêm | `main/xiaozhi-server/core/providers/llm/nckh/__init__.py` | Khai báo gói provider. |
| Thêm | `main/xiaozhi-server/core/providers/llm/nckh/nckh.py` | Demo không gọi cloud hoặc ủy quyền OpenAI-compatible client cho DeepSeek. |
| Thêm | `main/xiaozhi-server/core/reminder_scheduler.py` | Lịch nhắc MySQL theo thiết bị; UTC+7, lặp, offline, claim/retry, mở TTS trước audio. |
| Thêm | `main/xiaozhi-server/plugins_func/functions/add_reminder.py` | Plugin Việt đăng ký đúng ToolType và hợp đồng tham số conn. |
| Thêm | `main/xiaozhi-server/plugins_func/functions/delete_reminder.py` | Plugin Việt đăng ký đúng ToolType và hợp đồng tham số conn. |
| Thêm | `main/xiaozhi-server/plugins_func/functions/get_news_from_vnexpress.py` | Plugin Việt đăng ký đúng ToolType và hợp đồng tham số conn. |
| Thêm | `main/xiaozhi-server/plugins_func/functions/get_weather_vn.py` | Plugin Việt đăng ký đúng ToolType và hợp đồng tham số conn. |
| Thêm | `main/xiaozhi-server/plugins_func/functions/list_reminders.py` | Plugin Việt đăng ký đúng ToolType và hợp đồng tham số conn. |
| Thêm | `main/xiaozhi-server/requirements-nckh.txt` | Dependency bổ sung ASR tiếng Việt và MySQL. |

Có 24 tệp gốc được sửa và 33 tệp mới trong danh sách trên. Tài liệu thay đổi này và `NCKH_CHANGES.patch` được thêm khi đóng gói. Không đưa node_modules, dist, cache build hoặc secret runtime vào ZIP.
