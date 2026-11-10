# Kết quả kiểm thử Server Robot AI tiếng Việt v2

Ngày kiểm tra: **06/11/2026**. Kết quả dưới đây thuộc bản nguồn bàn giao; các bài kiểm thử đã được chạy lại sau khi khôi phục phiên làm việc. Không quy đổi số bài test thành phần trăm hoàn thành yêu cầu.

## Kết quả đã chạy

| Nhóm | Kết quả | Phạm vi |
|---|---:|---|
| Python | 58 đạt | Plugin/đơn vị dữ liệu, lịch nhắc, timezone, reconnect/hủy, Edge retry, TTS client, API kiểm thử nội bộ, MCP state/future, HMAC |
| Web contract | 10 đạt | Hợp đồng UI/API kế thừa |
| Web unit | 85 đạt | 70 bài kế thừa + 15 bài giao thức thiết bị ảo/WAV và HTTP của trang kiểm thử |
| Java | 32 đạt, 0 bỏ qua | 7 lớp test liên quan config, phân quyền, thiết bị, OTA quyết định cập nhật và thời gian |
| Tổng bài tự động | **185 đạt, 0 thất bại** | Không bao gồm kiểm thử tải hoặc nghiệm thu phần cứng |
| Vue production build | Thành công | Build từ nguồn, bundle có trang Kiểm thử server |
| Java compile/package | Thành công | JDK 21; JAR kiểm tra có AdminApplication, đúng Start-Class và CRC hợp lệ |
| Package Java lặp lại | Thành công | Kiểm tra lại lỗi repackage sau khi đã tạo executable JAR |
| Python compileall | Thành công | Tệp mới/chỉnh sửa; có SyntaxWarning ở chuỗi escape upstream không thuộc phần sửa |
| SQL | Parse 80 câu lệnh | V1 so byte giữ nguyên; **chưa chạy migration trên MySQL thật tại đây** |

Java chạy nhóm: NckhLabControllerTest, DeviceEnrollmentPermissionTest, ConfigServiceImplTest, DeviceServiceImplTest, DeviceAutoUpdateTest, DeviceTimeSerializationTest, ShiroConfigTest. Không ghi nhận đây là toàn bộ test suite upstream.

## Âm thanh thật đã kiểm tra

- Engine **Piper 1.8.0**, model **vi_VN-vais1000-medium**, tổng hợp câu: “Xin chào, đây là bài kiểm tra máy chủ Robot AI tiếng Việt.”
- Có WAV thật: **135,724 byte**, mono PCM16 **22,050 Hz**, dài khoảng **3.077 giây**.
- Khởi tạo và tổng hợp ở môi trường này khoảng **1.541 giây**; đây là một mẫu kiểm tra, không phải benchmark hay cam kết cho laptop của bạn.
- HTTP sidecar thật: health đạt, thiếu secret trả 401, có secret trả WAV không rỗng.
- Mã hóa đầu vào bằng ffmpeg/libopus và giải mã Python: **52 frame**, 49,920 mẫu, 3.12 giây ở 16 kHz.
- Bộ giải mã **Opus WASM dùng trên web** giải mã cùng số mẫu, **0 lỗi**. Phép thử chạy SDK/WASM trong Node; chưa kiểm tra trực quan bằng trình duyệt tại đây.

Kết quả máy đọc được: `deploy/nckh/verification/results.json`. Âm thanh và model tải để kiểm tra không đóng gói vào nguồn.

## Ma trận chức năng và mức kiểm chứng

| Chức năng | Mã nguồn | Điều đã kiểm tra | Cần nghiệm thu tiếp |
|---|---|---|---|
| Web/Java/DB/Redis/Docker | Có | Build web/Java, cấu hình Compose | Build và khởi động toàn bộ stack trên Docker của bạn |
| ASR PhoWhisper CPU | Có, giữ cache dùng chung | Unit PCM16, cache, tham số chống hallucination | Suy luận model thật, câu thu âm và độ chính xác |
| LLM demo / DeepSeek | Có | Demo không khởi tạo client cloud, thiếu khóa được báo rõ | Khóa/số dư thật, hội thoại và chọn tool bằng ngôn ngữ |
| EdgeTTS Việt | Có | Retry, bỏ dữ liệu dở, giữ tiếng Việt, cancellation | Tính sẵn sàng của Edge qua mạng thực tế |
| Piper offline | Có | Suy luận + HTTP + codec thật | Profile Docker trên máy bạn và chất lượng giọng nghe |
| VieNeu offline | Có | Client/contract dùng chung, cấu hình SDK/container | Tải model và suy luận VieNeu thật |
| Tin / thời tiết / vàng | Có | Parser, đơn vị, thiếu khóa, xử lý dữ liệu lỗi | API/RSS thực tế, quota và trạng thái nguồn |
| Âm lịch Việt | Có | Tết 1968, 2024–2027, tháng nhuận 2023, ngày sai/phạm vi | Bộ dữ liệu lịch rộng hơn nếu dùng ngoài demo nghiên cứu |
| Dịch Việt–Anh / IPA | Có | Contract JSON, giới hạn đầu vào, thiếu khóa | Chất lượng dịch/IPA bằng API thật |
| Nhạc local | Có | Tên có dấu, match, tránh tìm đường dẫn ngoài thư mục | Bài nhạc của bạn qua loa/thiết bị |
| Lịch nhắc/lặp/nhắc bù/hủy | Có | State/claim, UTC+7, offline, hủy, lỗi TTS, frame gửi | MySQL + WS + thời gian thật, restart/crash của toàn stack |
| MCP 5 tool | Có | Tên thật/sanitized, id tương quan, giới hạn, timeout/cancel cleanup | Firmware công bố tool và điều khiển vật lý đúng |
| Phân quyền | Có | Chặn thiết bị/lịch/trợ lý người khác, SQL tham số, che credential | E2E với nhiều tài khoản đang chạy trong stack |
| Backup/restore | Có | Mã và guard thao tác khôi phục | Dump/restore trên DB thử nghiệm trước khi dùng dữ liệu quan trọng |

## Giới hạn thực nghiệm

Môi trường này không có Docker engine để chạy Compose. JVM không truy cập DNS trực tiếp nên dependency được nạp vào cache qua HTTPS và Maven chạy offline; build/test vẫn dùng mã thật. Build Vue dùng shim nhận diện card mạng dành riêng môi trường kiểm tra; shim không nằm trong ZIP và Dockerfile của bạn dùng Node 22 bình thường.

Các unit dùng mock/stub được nêu rõ; chúng không chứng minh ASR chính xác, API bên ngoài luôn sẵn sàng hoặc robot đã thực thi. Chưa có khóa DeepSeek/OpenWeather của bạn, chưa nhận firmware/robot thật và chưa kiểm thử tải đồng thời. Không phát sinh lời gọi API DeepSeek tính phí trong lần kiểm tra này.

Trạng thái `queued` của lời nhắc là đã gửi audio qua WS, không phải ACK loa đã phát. Cơ chế khôi phục có thể gửi lại nếu server chết sau phát trước commit DB; chưa có exactly-once phần cứng.

## Các bài cần chạy trên máy bạn trước khi nghiệm thu

1. Chạy nâng cấp theo HUONG_DAN_V2.md, đủ dịch vụ healthy và 4 kiểm tra kết nối đạt.
2. Thử từng tab Kiểm thử server, nghe âm thanh và nhận dạng một đoạn thu âm thật.
3. Chạy robot_client.py với WAV để thử Opus → ASR → LLM → Opus. Lưu JSON report, không chỉ chụp health check.
4. Tạo, hủy, chờ lịch đến giờ; thử offline/reconnect, lặp ngày/tuần và restart dịch vụ để kiểm tra lưu bền.
5. Nếu dùng DeepSeek: gọi API thật rồi yêu cầu chọn các plugin/MCP bằng hội thoại. Đối chiếu dữ liệu nguồn và kết quả công cụ.
6. Ghép firmware thật, thử cảm biến/LED rồi servo/motor ngắn; kiểm tra mic/loa và mất mạng/nguồn.
7. Thử backup/restore trên DB thử nghiệm và ghi nhận cấu hình/máy chạy khi đo hiệu năng.

**Kết luận:** đã triển khai các phần server cốt lõi và có bằng chứng build/unit/component ở trên. Chưa có đủ bằng chứng để xác nhận hệ thống đã nghiệm thu 100% trên Docker, API và phần cứng thực tế. Gmail OAuth, VPS/GPU và các module mở rộng upstream không được ghi là đã hoàn thành trong phạm vi này.
