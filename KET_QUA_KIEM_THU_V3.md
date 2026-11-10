# Kết quả kiểm thử Server Robot Việt v3

Ngày 06/11/2026. Phạm vi: bản nguồn 3.0.0. Đã triển khai các chức năng trong `DOI_CHIEU_YEU_CAU_V3.md`; các bằng chứng bên dưới không thay cho nghiệm thu trên máy và robot thật.

## Kiểm thử và build đã thực hiện

| Hạng mục | Kết quả |
|---|---|
| Python: plugin, provider, lời nhắc, xác thực, bộ cài, model cache, lỗi khởi động và hàng đợi audio | 84 đạt |
| Web contract | 10 đạt |
| Web component/unit | 85 đạt |
| Java: 8 lớp kiểm thử liên quan cấu hình, phân quyền/thiết bị, thời gian và online WebSocket | 35 đạt |
| Tổng các kiểm thử tự động trên | **214 đạt, 0 thất bại** |
| Vue production build | Đạt |
| Java 21 compile/package, kiểm tra cấu trúc JAR | Đạt; 1012 mục trong JAR |
| Docker Compose 2.39.4 đọc cấu hình/profile setup | Đạt |
| Giải dependency cho Python 3.11 Linux amd64 | Đạt; 77 dependency khóa phiên bản |
| Cài môi trường runtime sạch + `pip check` | Đạt trên Python 3.12, dùng cùng phiên bản package trong lock |
| Lịch sử Liquibase v1/v2 | Giữ nguyên từng byte |
| SQL migration v3 | Phân tích cú pháp MySQL được 11 câu; chưa chạy trên DB thật ở đây |

Các cảnh báo deprecation của môi trường pytest/Python không làm kiểm thử thất bại. JDK dùng phiên bản 21 thật. Maven được cấp cache dependency qua HTTPS rồi build offline do DNS của JVM trong môi trường kiểm tra. Build Vue dùng shim nhận diện card mạng dành riêng môi trường kiểm thử; shim này không nằm trong gói và Dockerfile dùng Node 22 bình thường.

## Thử thành phần voice bằng mô hình và âm thanh thật

Đây là tiến trình voice cục bộ với cấu hình fixture. **Không chạy Java/MySQL/Docker trong bài thử này.** Dùng cùng phiên bản package runtime đã khóa: NumPy 1.26.4, CTranslate2 4.6.2, ONNX Runtime 1.23.2, faster-whisper 1.2.1; Piper 1.8.0. Python kiểm tra là 3.12.14, còn image voice đích dùng Python 3.11.

- Tải mô hình VinAI chính thức, chuyển PhoWhisper-small CT2 int8 và nạp được trọng số CPU. Revision nguồn: `a86b604c346caf7148c37512eafe783a16420adb`.
- Kiểm tra đủ model.bin, config, tokenizer, preprocessor và vocabulary; xác minh SHA-256, chạy lại với cache và không chuyển lại.
- Nạp VAD Silero ONNX thật. Readiness trả `ready`, `websocket`, `http`, `asr_loaded`, `vad_loaded` đều true.
- Kết nối WebSocket với token HMAC, hello và tools/list thật giữa server với client mô phỏng.
- Gọi và nhận kết quả cả năm MCP tool: LED, move, servo, distance, wave_hand. Kết quả có dấu **mô phỏng**, không có tác động GPIO thật.
- Gửi văn bản và nhận 109 gói Opus TTS thật từ Piper.
- Gửi âm thanh qua WebSocket: 37 gói Opus đầu vào, nhận STT và 111 gói âm thanh trả lời qua demo LLM + Piper.
- Thử `play_music` với WAV tự tạo và nhận 56 gói âm thanh.
- Toàn bài thử voice kết thúc với `VOICE_PROTOCOL_PASS`, đóng kết nối và dọn tài nguyên.

Câu âm thanh nguồn: “Xin chào, đây là máy chủ robot tiếng Việt.”

Kết quả qua WebSocket: **xin chào đây là máy chủ dò tiếng việt**.

Mô hình vẫn nhận sai “robot”; dữ liệu này chứng minh pipeline truyền/nhận và suy luận đã chạy, không chứng minh đạt độ chính xác nhận dạng 100%. Cần tập bản thu nhiều người nói để đo WER và nhiễu thực tế. Các số gói/thời gian trong một lượt thử không phải benchmark tải hoặc SLA.

Kiểm tra này phát hiện và đã sửa hai lỗi: bỏ phần đầu bản thu thủ công sau lượt văn bản, và flush ASR trước khi xử lý hết các khung trong hàng đợi. Có kiểm thử hồi quy cho cả hai. Telemetry ONNX được tắt **trước khi thư viện khởi tạo** bằng `ORT_DISABLE_TELEMETRY=1`, cùng API tắt telemetry; mô hình suy luận dùng cache local.

## Chưa có bằng chứng chạy thật trong môi trường này

- Không có Docker engine để build/khởi động toàn bộ Compose; mới xác minh Compose CLI đọc cấu hình, build Java/Vue và chạy thành phần voice riêng.
- Chưa chạy migration, backup/restore và lưu lời nhắc trên MySQL thật ở đây. Các ca scheduler/ownership dùng kiểm thử có kiểm soát; cần thử bền vững trên stack của bạn.
- Không có khóa DeepSeek/OpenWeather của bạn; chưa gọi API trả phí hoặc chứng minh LLM tự chọn tool đúng trên dịch vụ thật.
- Chưa nghiệm thu trực tiếp độ sẵn sàng RSS/giá vàng/EdgeTTS, mô hình VieNeu hoặc chất lượng ba giọng trên người dùng thật.
- Chưa có firmware/phần cứng để kiểm tra mic/loa, cảm biến, LED, servo/motor và ngắt mạng/nguồn thực tế.
- Chưa chạy kiểm thử trình duyệt trực quan, nhiều trình duyệt, nhiều robot đồng thời hoặc đo WER có bộ dữ liệu.

## Cách tiếp tục trên máy bạn

Chạy `python deploy/nckh/install.py --host 192.168.1.2 --stop-previous`, sau đó `check_server.py` và `selftest.py`. Đăng nhập web, tạo trợ lý và thực hiện danh sách nghiệm thu trong `HUONG_DAN_V3.md`. Khi có khóa, chạy `check_deepseek.py --chat` rồi thử function calling; khi firmware sẵn sàng, ghép và kiểm tra thiết bị thật.

Kết quả máy đọc được: `deploy/nckh/verification/results.json`. Log chọn lọc đã ẩn thông tin môi trường nằm trong `deploy/nckh/verification/v3/`. Không ghi nhận các hạng mục chưa chạy là “đã nghiệm thu 100%”.
