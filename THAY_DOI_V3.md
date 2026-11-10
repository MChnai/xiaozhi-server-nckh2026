# Thay đổi Server Robot Việt v3

V3 là gói cài mới vào project Docker `robot-ai-viet-v3`; dữ liệu v2 được giữ nguyên. Giữ lịch sử Liquibase v1/v2, thêm changeset riêng cho cấu hình v3.

- Thêm bộ cài `install.py`, dùng `.env` rõ ràng, giữ mật khẩu, kiểm tra cổng, chờ từng dịch vụ có thời hạn, log đã ẩn khóa và công cụ doctor.
- Thêm giám sát tác vụ và readiness thật; lỗi bind/import/model không còn để tiến trình tiếp tục báo đã khởi động.
- Tách runtime voice CPU khỏi Torch/FunASR và SDK cũ; ghim các phiên bản ASR/PyAV tương thích.
- Tải/chuyển PhoWhisper theo revision VinAI cố định, kiểm tra đủ trọng số/tokenizer/vocabulary/config và SHA-256, thay model theo staging.
- Piper là TTS mặc định được bộ cài chuẩn bị; giữ Edge và profile VieNeu. Tắt telemetry ONNX trước khi nạp session.
- Thêm `selftest.py` thử TTS→ASR thật, micro trong web, trạng thái chế độ/API, thời hạn kết nối WebSocket và nhãn lời nhắc tiếng Việt.
- Thêm trạng thái online qua WebSocket có xác thực và lọc thiết bị theo tài khoản; không dùng trạng thái MQTT cho stack LAN này.
- Sửa ngữ cảnh lịch Việt, tránh plugin lịch cũ ghi đè; thêm nhạc WAV tự tạo, giữ chín plugin yêu cầu và năm MCP tool.
- Chuẩn hóa Opus 16 kHz, retry TTS và kết nối TTS nội bộ không qua proxy môi trường.
- Sửa chế độ thu thủ công: không bỏ hai giây đầu sau lượt văn bản; xử lý dấu kết thúc qua cùng hàng đợi FIFO để không bỏ khung âm thanh chưa được xử lý.
- Giữ phân quyền, lời nhắc lặp/nhắc bù, OTA và công cụ mô phỏng từ v2; mở rộng kiểm thử lỗi khởi động và trạng thái thiết bị.

Xem kết quả kiểm thử thực tế và giới hạn trong `KET_QUA_KIEM_THU_V3.md`.
