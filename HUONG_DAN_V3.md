# Hướng dẫn cài mới và nghiệm thu Server Robot Việt v3

Phiên bản 3.0.0, ngày 06/11/2026. Phạm vi: phần server của đề tài; firmware, nạp ESP32 và đấu nối GPIO thuộc nhóm firmware. Các số liệu đã thử được tách riêng trong `KET_QUA_KIEM_THU_V3.md`.

## 1. Chuẩn bị

- Windows x64, Docker Desktop dùng Linux containers/WSL2, Python 3.10 trở lên.
- Máy 16 GB RAM: nên cấp Docker khoảng 6–8 GB RAM và còn ít nhất 12–15 GB đĩa trống cho image, cache và model. Đây là mức khuyến nghị, không phải kết quả thử tải đa người dùng.
- Internet cho lần build/tải mô hình đầu tiên. Không cần GPU hoặc tài khoản DeepSeek để thử demo.
- Xác định IPv4 LAN bằng `ipconfig`; ví dụ hiện tại của bạn là `192.168.1.2`. Nên đặt DHCP reservation trên router.

Giải nén ZIP vào thư mục mới. Chỉ chạy lệnh khi thư mục hiện hành có `compose.nckh.yaml` và thư mục `main`.

## 2. Chạy bộ cài một lệnh

```powershell
python deploy/nckh/install.py --host 10.10.66.210 --stop-previous
if ($LASTEXITCODE -ne 0) { throw "Cài đặt chưa hoàn tất; đọc lỗi cuối và thư mục diagnostics" }
```

Bộ cài làm lần lượt:

1. Kiểm tra Docker và tạo `.env` với mật khẩu ngẫu nhiên nếu chưa có. Chạy lại sẽ giữ mật khẩu và chỉ cập nhật IP LAN.
2. Với `--stop-previous`, dừng project `robot-ai-viet` của v1/v2, giữ mọi volume. Không dừng ứng dụng khác đang chiếm cổng.
3. Build từng image API, voice, web, Piper và công cụ chuyển mô hình để giảm đỉnh RAM.
4. Tải PhoWhisper-small từ VinAI theo revision cố định, chuyển CT2 int8, nạp thử trọng số, ghi và kiểm tra SHA-256. Dữ liệu đặt trong volume, không phụ thuộc một thư mục model rỗng trên Windows.
5. Khởi động DB/Redis → API → Piper → voice → web. Chờ tối đa 300 giây cho từng dịch vụ; dừng sớm nếu container exited/restarting/unhealthy.
6. Kiểm tra web, OTA và readiness thật của voice.

Build và tải model lần đầu có thể mất nhiều phút. Bộ cài hiển thị bước hiện tại và thời gian đã qua. Mặc định mỗi build/model có giới hạn 2400 giây. Nếu mạng rất chậm, có thể tăng riêng:

```powershell
python deploy/nckh/install.py --host 192.168.1.2 --stop-previous --build-timeout 3600 --model-timeout 3600
```

Nếu bị gián đoạn, sửa nguyên nhân rồi chạy lại **cùng lệnh**, không xóa volume. Nếu image đã build xong, dùng `--skip-build` để bỏ qua bước build.

V3 dùng project `robot-ai-viet-v3`, DB và cache riêng với v2. Nếu đã có dữ liệu v3 nhưng thiếu `.env`, bộ cài sẽ dừng để tránh sinh mật khẩu khác với DB cũ. Lấy lại `.env` từ thư mục v3 đã cài trước đó. Không dùng `down -v` để chữa lỗi mật khẩu hoặc healthy.

## 3. Tài khoản và trợ lý

Mở [http://localhost:8002](http://localhost:8002) trên máy chạy Docker hoặc `http://192.168.1.2:8002` từ máy cùng LAN. Tài khoản đăng ký đầu tiên được cấp quyền quản trị theo cơ chế của dự án gốc.

Chọn **Thêm tác nhân**, đặt tên rồi vào **Vai trò**, chọn mẫu **Trợ lý Robot Việt** và lưu. Mặc định v3:

| Thành phần | Mã | Giá trị hiển thị |
|---|---|---|
| ASR toàn server | `ASR_NCKH` | PhoWhisper-small tiếng Việt |
| VAD toàn server | `VAD_SileroVAD` | Silero ONNX CPU |
| LLM | `LLM_NCKH` | Robot AI: Demo / DeepSeek |
| TTS mặc định v3 | `TTS_PIPER_NCKH` | Piper tiếng Việt, VAIS 1000 |
| Intent | `Intent_NCKH` | Gọi công cụ của Robot AI, `function_call` |
| Memory | `Memory_nomem` | Không lưu bộ nhớ dài hạn |

ASR/VAD được chọn trong **Mô hình** với quyền quản trị, không phải mọi trường đều xuất hiện trong trang Vai trò. Tên hiển thị khác mã kỹ thuật; không cần tìm chữ `LLM_NCKH` trong nhãn giao diện. TTS, LLM, Intent và Memory được chọn trong Vai trò. Mẫu tạo trợ lý mới tự có đủ chín plugin của đề tài.

Các mẫu nhân vật kế thừa cũng dùng pipeline tiếng Việt. Không cần nhập khóa DeepSeek vào web khi đã cấu hình qua `.env`.

## 4. Nghiệm thu khi chưa có firmware

Chạy:

```powershell
python deploy/nckh/check_server.py --host 10.10.66.210
python deploy/nckh/selftest.py
```

`check_server.py` kiểm tra readiness/cổng. `selftest.py` gọi Piper nội bộ, chuyển WAV và nhận dạng bằng PhoWhisper CPU; có lời nhận dạng không đồng nghĩa đạt độ chính xác ASR cho mọi người nói.

Mở **Kiểm thử server** trên thanh điều hướng, chọn trợ lý:

1. Nhấn **Kiểm tra cấu hình**. Xem chế độ demo/DeepSeek, readiness và trạng thái có/thiếu khóa; trang không trả khóa bí mật.
2. **Kết nối thiết bị ảo**. Nhật ký phải có hello và MCP. MAC bắt đầu `02:` thuộc trợ lý/tài khoản hiện tại; có thể xóa thiết bị ảo ở Quản lý thiết bị.
3. Tab **Hội thoại**: gửi “Xin chào robot”. Demo trả câu cố định nhưng phải nhận được gói Opus và có thể nghe âm thanh. Nhấn **Ngắt lời** để thử hủy.
4. Tab **ASR / TTS**: tạo giọng nói; tải WAV/MP3/M4A hoặc thu micro rồi nhận dạng. Tệp tối đa 8 MB, nhận dạng 30 giây đầu. Micro yêu cầu mở qua `localhost` hoặc HTTPS; HTTP bằng IP LAN vẫn dùng được chức năng tải tệp.
5. Tab **Plugin**: thử Âm lịch với `2026-02-17` → mùng 1 tháng 1 năm Bính Ngọ; tin VnExpress; giá vàng; thời tiết khi đã có khóa. Dịch yêu cầu DeepSeek thật. Phát nhạc với `song_name` là `nhạc mẫu`; gói có thang âm WAV tự tạo để thử.
6. Tab **MCP mô phỏng**: thử cả năm nút LED, di chuyển, servo, khoảng cách, vẫy tay. Những kết quả này chứng minh giao thức với thiết bị ảo, chưa chứng minh motor/servo thật.
7. Tab **Nhắc nhở**: chọn thiết bị ảo, đặt sau 1 phút, giữ trang online để nghe. Thử hằng ngày/hằng tuần; hủy một lời nhắc. Tạo lời nhắc, ngắt thiết bị qua thời điểm đến hạn rồi kết nối lại để thử nhắc bù.
8. Restart dịch vụ rồi tải lại danh sách lời nhắc để kiểm tra tính bền vững MySQL. Có thể theo dõi online/offline thật của WebSocket trong Quản lý thiết bị.

Âm thanh nhận được được lưu trong trình phát để nghe/tải xuống. Quyền tự phát của trình duyệt có thể yêu cầu nhấn nút phát.

`queued` nghĩa là server đã gửi gói âm thanh qua WebSocket. Firmware hiện chưa có xác nhận loa đã phát, nên không coi trạng thái này là bảo đảm người dùng đã nghe hoặc bảo đảm “đúng một lần” khi mất mạng đúng lúc.

## 5. Bật DeepSeek và gọi thử API thật

Chưa cần mua API để build, chạy web, OTA, thử PhoWhisper/Piper, MCP mô phỏng hoặc quản lý lời nhắc. Demo không hiểu và tự chọn công cụ bằng ngôn ngữ tự nhiên; muốn thử phần đó cần DeepSeek hoặc tự triển khai thêm LLM khác.

Đăng ký/đăng nhập [DeepSeek Platform](https://platform.deepseek.com/), vào Billing/Top up để nạp số dư theo phương thức tài khoản hỗ trợ, rồi tạo khóa trong API keys. Mức giá và model xem trên [tài liệu chính thức](https://api-docs.deepseek.com/quick_start/pricing). Khóa và số dư API là dịch vụ lập trình riêng; không cấp gói ChatGPT Pro hay một gói giao diện chat tương đương. Có thể dùng API cho công cụ hỗ trợ code tương thích, chi phí tính theo API.

Sửa **`.env` ở cạnh compose.nckh.yaml**:

```dotenv
NCKH_LLM_MODE=deepseek
DEEPSEEK_API_KEY=dan_khoa_cua_ban_o_day
DEEPSEEK_MODEL=deepseek-flash
```

`deepseek-flash` là tên gọi theo tài liệu DeepSeek tại thời điểm phát hành v3; có thể sửa khi nhà cung cấp đổi model. Không ghi khóa vào Git hoặc gửi ảnh chụp khóa.

```powershell
python deploy/nckh/check_deepseek.py
python deploy/nckh/check_deepseek.py --chat
docker compose -p robot-ai-viet-v3 -f compose.nckh.yaml up -d --force-recreate voice
```

Lệnh đầu đọc danh sách model, lệnh `--chat` gửi một yêu cầu hội thoại thật và có thể tính phí token. Mã 401: khóa sai; 402: thiếu số dư; 429: giới hạn tần suất. Đổi `.env` cần recreate container, chỉ `restart` sẽ không nạp biến môi trường mới.

Sau đó kết nối lại thiết bị ảo và thử “Hôm nay âm lịch ngày mấy?”, “Vẫy cả hai tay hai lần”, “Nhắc tôi uống nước lúc …”. Kiểm tra nhật ký gọi công cụ và kết quả, không chỉ dựa vào câu nói của LLM. Function calling dùng chế độ không suy luận theo [hướng dẫn Tool Calls](https://api-docs.deepseek.com/guides/tool_calls/).

Thời tiết dùng `OPENWEATHER_API_KEY` riêng của [OpenWeather](https://openweathermap.org/api). Không cần mua API DeepSeek để gọi trực tiếp plugin thời tiết. RSS/giá vàng phụ thuộc nguồn công khai và có thể bị giới hạn; server trả lỗi khi nguồn không cung cấp dữ liệu, không tạo dữ liệu giả.

## 6. Chọn ba giọng TTS

| TTS | Cách dùng | Internet |
|---|---|---|
| Piper | Có sẵn mặc định trong Vai trò, giọng VAIS 1000 | Tải lần đầu; suy luận cục bộ |
| EdgeTTS | Vai trò → Văn bản thành giọng nói → Giọng Việt: Hoài My / Nam Minh | Cần Internet khi tạo giọng |
| VieNeu | Bật dịch vụ tùy chọn dưới đây, rồi chọn VieNeu và giọng Hải Đăng | Tải lần đầu; chạy cục bộ sau khi có cache |

```powershell
docker compose -p robot-ai-viet-v3 -f compose.nckh.yaml --profile vieneu build vieneu
docker compose -p robot-ai-viet-v3 -f compose.nckh.yaml --profile vieneu up -d vieneu
docker compose -p robot-ai-viet-v3 -f compose.nckh.yaml logs -f vieneu
```

Chờ “TTS offline sẵn sàng: vieneu” rồi chọn giọng. Nếu tải bị lỗi, xem log và giữ nguyên cache. Bản v3 tách SDK VieNeu/PyTorch khỏi image voice. Piper nhẹ nhưng giọng kém tự nhiên hơn Edge/VieNeu; lựa chọn mặc định giúp thử hệ thống không phụ thuộc EdgeTTS online. Edge gặp `NoAudioReceived` sau các lần thử hữu hạn thì chọn Piper để tiếp tục kiểm tra.

PhoWhisper mặc định nhận tiếng Việt. Dịch hai chiều hỗ trợ **văn bản** Việt–Anh; không cam kết PhoWhisper sẽ nhận tiếng Anh tốt. Chức năng này cần thêm ASR đa ngôn ngữ và bộ dữ liệu kiểm thử nếu muốn nghiệm thu hội thoại tiếng Anh bằng micro.

## 7. Kết nối robot thật khi firmware sẵn sàng

Gửi cho bạn firmware các thông tin:

| Mục | Giá trị ví dụ |
|---|---|
| IP máy server | `192.168.1.2` |
| OTA | `http://192.168.1.2:8002/nckhsv/ota/` |
| WebSocket do OTA cấp | `ws://192.168.1.2:8000/nckh/v1/` |
| Âm thanh | Opus mono 16 kHz; vào 20/40/60 ms, ra 60 ms |
| MCP | Thiết bị công bố `tools/list`; server gọi đúng tên đã nhận |

Robot và server phải truy cập được nhau trong LAN. Không dùng IP bridge `172.x` của container trong firmware. Không hardcode khóa nội bộ server vào firmware; dùng token do OTA cấp.

Bật robot, xem mã kích hoạt sáu số trên màn hình/log UART, vào **Thiết bị** của đúng trợ lý để ghép bằng mã. Khi đã ghép, reboot/kết nối lại robot để nhận cấu hình/token mới. Nếu firmware không hiện màn hình, lấy MAC và log OTA từ bạn firmware để xác định bước đang lỗi.

Windows Firewall cần cho phép cổng TCP 8000 và 8002 trong mạng Private nếu thiết bị LAN chưa vào được. Có thể chạy PowerShell quản trị:

```powershell
New-NetFirewallRule -DisplayName "Robot Viet v3 LAN" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000,8002 -Profile Private -RemoteAddress LocalSubnet
```

Không phải mọi kết nối lỗi đều do firewall: thử mở web bằng IP từ điện thoại cùng Wi-Fi và xem log trước.

Nghiệm thu năm công cụ:

| Công cụ | Tham số cần kiểm tra |
|---|---|
| `self.led.set_mode` | led left/right/both; mode off/on/blink_slow/blink_fast/breathe |
| `self.robot.move` | direction forward/backward/left/right/stop; duration_ms 0–2000 |
| `self.robot.set_servo` | part neck/arm_left/arm_right; angle 0–180 |
| `self.robot.get_distance` | Không có tham số; kiểm tra giá trị cm thực tế |
| `self.robot.wave_hand` | which left/right/both; times 1–10 |

Tên/kiểu phải đúng `tools/list` thực tế. Nếu firmware dùng tên khác, cần phối hợp chỉnh giao thức; server không thể chứng nhận chuyển động chỉ từ mô phỏng. Thử LED/khoảng cách trước, rồi servo/motor với thời lượng ngắn và quan sát thực tế. Lưu kết quả firmware/thiết bị thật vào biên bản nghiệm thu riêng.

Công cụ CLI `deploy/nckh/robot_client.py` hỗ trợ OTA, hello, Opus và MCP để thử thay firmware. Ví dụ sau khi ghép MAC ảo `02:00:00:00:00:01` bằng mã OTA:

```powershell
docker compose -p robot-ai-viet-v3 -f compose.nckh.yaml exec -T voice python /opt/robot_client.py --host 192.168.1.2 --device-id 02:00:00:00:00:01 --text "Xin chào robot" --output /opt/xiaozhi-esp32-server/data/tra_loi.wav --report /opt/xiaozhi-esp32-server/data/robot-test-report.json
```

Lần đầu CLI có thể trả mã chưa ghép; nhập mã trên web rồi chạy lại. Tùy chọn `--wav` gửi một tệp âm thanh qua WebSocket thay cho `--text`; dùng đường dẫn tồn tại trong container và đúng thời lượng ngắn để kiểm tra.

## 8. Sao lưu, khôi phục, chẩn đoán và đổi IP

```powershell
python deploy/nckh/backup_db.py
python deploy/nckh/doctor.py
```

Tệp SQL nằm trong `backups/`. `.env` cần lưu riêng tại nơi an toàn để mở lại DB; backup SQL không chứa đủ cấu hình môi trường.

Khôi phục vào v3 đang chạy, sau khi đã sao lưu dữ liệu hiện tại:

```powershell
python deploy/nckh/restore_db.py --file backups/ten_ban_sao_luu.sql --confirm-restore
```

Lệnh khôi phục thay dữ liệu hiện tại bằng tệp đã chọn, xóa cache Redis riêng của project v3 rồi khởi động lại API/voice. Không dùng dump v2 để nhập tùy tiện vào v3 đã có dữ liệu; nên thử một môi trường riêng và kiểm tra migration/config trước.

Đổi IP: chạy lại bộ cài với `--host IP_MOI` (có thể thêm `--skip-build` khi image còn nguyên), sau đó cập nhật URL OTA ở cấu hình firmware theo cơ chế bạn firmware hỗ trợ. Chỉ cần build lại firmware nếu firmware đã hardcode IP mà không có cách thay cấu hình.

| Hiện tượng | Việc cần làm |
|---|---|
| Thiếu `NCKH_PUBLIC_HOST` | Chạy `install.py --host IP_LAN`, không chạy backup trước lần cài đầu |
| DB access denied | Kiểm tra `.env` đúng với project v3/volume hiện có; không sinh lại mật khẩu |
| Voice restarting/unhealthy | `doctor.py`; kiểm tra tệp model, lỗi import, RAM và API nội bộ |
| Web 502 | Kiểm tra API/voice sẵn sàng và log; nginx v3 tự làm mới DNS Docker |
| Cổng 8000/8002 bị chiếm | Dừng project cũ bằng cờ `--stop-previous` hoặc xác định ứng dụng đang dùng |
| Tải model chậm | Giữ cache; xem tiến độ; tăng `--model-timeout` nếu cần |
| Model hỏng | Bộ chuẩn bị model kiểm tra SHA-256, dựng bản mới trước khi thay cache |
| Micro không hoạt động qua IP | Mở `localhost:8002` trên máy server, dùng HTTPS hoặc tải tệp |
| Demo không tự gọi tool | Bật DeepSeek để thử khả năng LLM; dùng tab Plugin/MCP để kiểm tra trực tiếp |

Nhật ký cài đặt: `diagnostics/install-*.log`, có ẩn các khóa trong `.env`. Không chia sẻ `.env` hoặc đầu ra `docker compose config` đầy đủ vì có thể chứa mật khẩu.

## 9. Giới hạn nghiệm thu

Mã nguồn có các chức năng server trong bảng đối chiếu. Việc nghiệm thu toàn hệ thống cần chạy Docker trên máy đích, API thật và robot thật. Gmail OAuth, VPS/domain/HTTPS và tăng tốc GPU xuất hiện trong phần định hướng/khó khăn của tài liệu; chúng không tự được cung cấp chỉ bằng gói server LAN này. V3 không tự triển khai hạ tầng hoặc tạo tài khoản/khóa trả phí thay bạn.

Mỗi dịch vụ voice chạy một scheduler, dùng claim/lease trong MySQL cho lời nhắc. Chưa cấu hình triển khai nhiều replica hoặc bảo đảm exactly-once trên loa. Chưa có kết quả tải nhiều robot đồng thời. Cần thêm đo WER tiếng Việt, độ trễ đầu âm thanh và kiểm tra firmware trước khi kết luận nghiệm thu 100%.
