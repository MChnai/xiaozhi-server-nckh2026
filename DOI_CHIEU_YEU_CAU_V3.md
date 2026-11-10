# Đối chiếu yêu cầu server v3

Đọc cùng `HUONG_DAN_V3.md` và `KET_QUA_KIEM_THU_V3.md`. “Đã triển khai” mô tả mã nguồn; trạng thái chạy thật có bằng chứng riêng, không suy ra từ tên file hoặc container healthy.

| Yêu cầu trong tài liệu | Nơi triển khai chính | Điều kiện nghiệm thu trên máy đích |
|---|---|---|
| Docker hóa server/API/web/DB/Redis | `compose.nckh.yaml`, `deploy/nckh/Dockerfile-*` | Bộ cài hoàn tất, toàn bộ dịch vụ healthy |
| Cài lại từ đầu, tự chuẩn bị cấu hình/model | `install.py`, `project.py`, `prepare_model.py`, `model_cache.py` | Tạo `.env`, chuyển model, chạy lại an toàn, báo lỗi hữu hạn |
| PhoWhisper CPU int8, chống nạp lại/hallucination | `core/providers/asr/pho_whisper_ct2.py` | Tệp thu âm Việt, nhiều lượt kết nối, đo WER/độ trễ |
| VAD Silero ONNX | `core/providers/vad/silero.py` | Thu âm tự động và dừng câu trong điều kiện tiếng ồn thực tế |
| DeepSeek/function_call | `core/providers/llm/nckh`, `openai`, `core/providers/tools` | Khóa có số dư; LLM tự chọn đúng plugin và nhận kết quả |
| Demo không API | Provider `nckh`, `.env` | Văn bản/âm thanh phản hồi cố định; không nhầm với suy luận AI |
| EdgeTTS tiếng Việt | `core/providers/tts/edge.py`, model `TTS_NCKH` | Có mạng; thử Hoài My và Nam Minh |
| Piper/VieNeu cục bộ | `piper_local.py`, `vieneu_local.py`, `offline_tts_server.py` | Cache model; Piper mặc định, VieNeu profile tùy chọn |
| Thời tiết OpenWeather | `plugins_func/functions/get_weather_vn.py` | `OPENWEATHER_API_KEY`, dữ liệu đúng địa phương/đơn vị |
| VnExpress RSS | `get_news_from_vnexpress.py` | Nguồn truy cập được, thời điểm và liên kết bài đúng |
| Âm lịch Việt Nam | `get_lunar.py`, `core/utils/lunar_vn.py`, `current_time.py` | UTC+7, ngày Tết và tháng nhuận; khoảng năm hỗ trợ 1900–2099 |
| Giá vàng | `get_gold_price.py` | Nguồn vang.today, đúng loại và đơn vị VND/lượng hoặc USD/oz |
| Dịch Việt–Anh/IPA | `translate_text.py` | DeepSeek thật; kiểm tra nghĩa, IPA và chiều dịch |
| Nhạc local | `play_music.py`, `music/nhac_mau.wav` | Chọn đúng tệp, gửi được audio, không báo phát nếu không có tệp |
| Nhắc thêm/xem/hủy | `add/list/delete_reminder.py`, `core/reminder_scheduler.py`, `NckhLabController` | DB bền vững; chỉ truy cập thiết bị của tài khoản |
| Tự phát, lặp daily/weekly, nhắc bù | Scheduler claim/lease, queue TTS, bảng `ai_reminder_nckh` | Online/rảnh, restart, quá giờ, ngắt giữa chừng và hủy |
| Web tiếng Việt, mẫu mặc định | `manager-web/src/i18n/vi.js`, Vue, migration `nckh-v3-20261106.sql` | Tạo trợ lý mới, đủ model/giọng/plugin |
| Thử không có firmware | `ServerLab.vue`, `robotSimulator.mjs`, `robot_client.py`, `selftest.py` | Hello, MCP giả lập, Opus, file/micro, hội thoại, lời nhắc |
| OTA 8002, WebSocket 8000, ghép thiết bị/token | Java OTA/device, `core/auth.py`, `websocket_server.py`, nginx | Firmware gọi OTA thật, ghép, nhận token, kết nối lại |
| Năm công cụ phần cứng | `core/providers/tools/device_mcp` | Công bố tools/list, gọi và quan sát LED/motor/servo/cảm biến thật |
| Giữ kết nối và trạng thái online | Thời hạn 86400, registry WS, API online riêng có xác thực | Mất Wi-Fi/reconnect, đóng tab, reboot thiết bị |
| Sao lưu/khôi phục/chẩn đoán | `backup_db.py`, `restore_db.py`, `doctor.py` | Dump SQL, restore vào môi trường thử, kiểm tra dữ liệu |

## Thay đổi v3 giải quyết lỗi triển khai

- Runtime voice không còn cài toàn bộ FunASR/Torch/model SDK không thuộc pipeline. Torch chỉ nằm trong công cụ chuyển model; VieNeu ở image riêng.
- Không nuốt lỗi tác vụ HTTP/WebSocket: ready chỉ sau khi mở cổng; tác vụ lỗi làm tiến trình dừng có mã lỗi.
- Không bind mount thư mục PhoWhisper rỗng trên Windows. Model dùng volume, manifest SHA-256, staging và promote khi hợp lệ.
- Bộ cài tuần tự, chờ có giới hạn, phát hiện restarting/exited/unhealthy, tạo log đã ẩn khóa.
- Nginx dùng DNS Docker khi chuyển tiếp; healthcheck dùng IPv4 loopback rõ ràng.
- Piper mặc định hoạt động cục bộ, vẫn giữ Edge/VieNeu. Đã tắt telemetry ONNX trước khi tạo session.
- Mẫu nhân vật và ngữ cảnh ngày/âm lịch dùng tiếng Việt; không bị plugin âm lịch Trung Quốc kế thừa ghi đè.
- Trạng thái thiết bị đọc registry WebSocket, không phụ thuộc MQTT chưa được cấu hình.
- Thương lượng âm thanh thống nhất Opus 16 kHz; nhận dạng và TTS dùng cùng quy ước giao thức.

## Phần cần hạ tầng hoặc firmware riêng

Gmail OAuth, domain/VPS/HTTPS, GPU, ASR tiếng Anh chuyên dụng và thử tải nhiều robot là công việc triển khai/thực nghiệm bổ sung, không phải tệp có sẵn của giảng viên có thể sao chép để chứng nhận hoàn tất. Firmware và tác động vật lý của năm MCP tool phải do nhóm firmware cùng kiểm tra trên thiết bị.
