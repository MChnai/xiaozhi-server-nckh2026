# Robot AI tiếng Việt — Server v3

Mã nguồn server cho đề tài Robot AI tiếng Việt: Python voice, Spring Boot API, Vue, MySQL, Redis và Docker. Firmware ESP32 do nhóm firmware triển khai riêng.

## Cài mới trên Windows

Cài Python 3.10 trở lên, mở Docker Desktop dùng Linux containers. Giải nén vào thư mục mới, mở PowerShell **tại nơi có `compose.nckh.yaml`** và chạy:

```powershell
python deploy/nckh/install.py --host 192.168.1.2 --stop-previous
if ($LASTEXITCODE -ne 0) { throw "Cài đặt chưa hoàn tất; xem diagnostics" }
```

Thay `192.168.1.2` bằng IPv4 LAN hiện tại của máy bạn. `--stop-previous` dừng các container project v1/v2 `robot-ai-viet`, giữ nguyên dữ liệu cũ. Nếu đây là máy cài lần đầu thì cờ này không làm gì.

Bộ cài tự tạo `.env`, build lần lượt các image, tải/chuyển PhoWhisper, nạp Piper và chờ từng dịch vụ healthy. Mỗi bước có thời hạn và nhật ký đã ẩn khóa. Chạy lại cùng lệnh để tiếp tục nếu mạng hoặc build bị gián đoạn. Không cần cài Java, Node, PyTorch hay MySQL trên Windows.

Mở [web trên máy chủ](http://localhost:8002), đăng ký tài khoản đầu tiên, tạo trợ lý bằng mẫu **Trợ lý Robot Việt**, rồi chọn **Kiểm thử server** trên thanh đầu trang. Mặc định là **demo + Piper**, chưa cần mua API.

```powershell
python deploy/nckh/check_server.py --host 127.0.0.1
python deploy/nckh/selftest.py
```

Lệnh thứ hai phát sinh giọng Piper và nhận dạng bằng PhoWhisper thật. Các phép thử WebSocket/MCP, hội thoại, nhạc và lời nhắc nằm trên trang kiểm thử.

## Chức năng trong gói

- PhoWhisper-small CT2 int8 trên CPU, Silero VAD và âm thanh Opus 16 kHz.
- Demo không API; DeepSeek cho hội thoại AI và tự gọi công cụ.
- Ba TTS: Piper cục bộ mặc định, EdgeTTS Hoài My/Nam Minh, VieNeu tùy chọn.
- Thời tiết, RSS VnExpress, âm lịch Việt Nam UTC+7, giá vàng, dịch Việt–Anh kèm IPA, nhạc local.
- Lời nhắc MySQL: thêm/xem/hủy, một lần/hằng ngày/hằng tuần, nhắc bù khi thiết bị online trở lại.
- OTA tương thích firmware, ghép thiết bị, token WebSocket và năm công cụ MCP phần cứng.
- Web tiếng Việt, thiết bị ảo, ghi/tải âm thanh, trạng thái online WebSocket, sao lưu/khôi phục và chẩn đoán.

Hướng dẫn đầy đủ: [HUONG_DAN_V3.md](HUONG_DAN_V3.md). Đối chiếu từng yêu cầu: [DOI_CHIEU_YEU_CAU_V3.md](DOI_CHIEU_YEU_CAU_V3.md). Kết quả đã chạy và phần chưa nghiệm thu: [KET_QUA_KIEM_THU_V3.md](KET_QUA_KIEM_THU_V3.md).

V3 dùng project Docker riêng `robot-ai-viet-v3`. Các hướng dẫn v1/v2 còn trong cây nguồn là tài liệu lịch sử; dùng hướng dẫn v3 khi cài gói này. Không chép `.env` v2 vào v3: bộ cài tạo mật khẩu cho DB v3 riêng. Luôn giữ `.env` v3 để dùng lại với dữ liệu v3.

Dựa trên [xiaozhi-esp32-server](https://github.com/xinnan-tech/xiaozhi-esp32-server). Giữ giấy phép và ghi nhận tác giả gốc trong mã nguồn; mô hình và thư viện bên thứ ba giữ giấy phép riêng. Gói này chứa mã nguồn và VAD, mô hình PhoWhisper/Piper được tải từ nguồn chính thức khi cài.
