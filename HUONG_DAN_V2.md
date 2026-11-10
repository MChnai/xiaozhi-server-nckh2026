> Tài liệu lịch sử. Với gói v3, dùng [HUONG_DAN_V3.md](HUONG_DAN_V3.md) và bộ cài `install.py`; không chạy quy trình cũ bên dưới.

# Hướng dẫn Server Robot AI tiếng Việt v2

Ngày: 06/11/2026. Phạm vi: server Python, API Java, Vue, dữ liệu và Docker. Firmware không nằm trong gói này. Container healthy chỉ chứng minh dịch vụ đang lắng nghe, chưa chứng minh toàn bộ AI/phần cứng đã nghiệm thu.

## 1. Nâng cấp bản đang chạy

Dùng lại thư mục dự án để giữ Docker project `robot-ai-viet`. Chép mã mới vào đó, giữ `.env`, `models/`, `music/`, tệp upload và các Docker volumes. Không dùng `down -v` hoặc xóa volume để nâng cấp.

```powershell
powershell -ExecutionPolicy Bypass -File deploy/nckh/upgrade.ps1
```

Script dừng ngay khi sao lưu, build hoặc tải model lỗi. Có thể chạy thủ công:

```powershell
python deploy/nckh/backup_db.py
if ($LASTEXITCODE -ne 0) { throw "Sao lưu thất bại" }
docker compose -f compose.nckh.yaml build api voice web
if ($LASTEXITCODE -ne 0) { throw "Build thất bại" }
docker compose -f compose.nckh.yaml up -d --wait --wait-timeout 300
if ($LASTEXITCODE -ne 0) { throw "Dịch vụ chưa healthy" }
python deploy/nckh/check_server.py --host 127.0.0.1
```

Không chạy lại model-setup nếu đã có `models/phowhisper-small-ct2/model.bin`. Liquibase thêm changeset v2; migration v1 giữ nguyên checksum. Không đổi mật khẩu, khóa riêng hoặc prompt người dùng tự viết. Thêm ba plugin mới cho các trợ lý đang dùng `LLM_NCKH`; làm mới cache model khi API khởi động.

Nhấn Ctrl+F5 trên web. Nếu còn giao diện cũ, xóa cache/service worker của riêng trang. IP `172.x` trong log là nội bộ; URL trả từ OTA mới là URL firmware cần dùng.

## 2. Cài lần đầu

Cần Docker Desktop ở chế độ Linux containers và Python 3 trên Windows. Lần đầu cần Internet để tải image, dependency và model. API Java/MySQL/Redis không public cổng ra LAN. Cho phép TCP 8000 và 8002 trên firewall mạng riêng.

```powershell
python deploy/nckh/setup.py --host 192.168.1.2
if ($LASTEXITCODE -ne 0) { throw "Không tạo được cấu hình" }
powershell -ExecutionPolicy Bypass -File deploy/nckh/upgrade.ps1
```

Thay bằng IPv4 LAN thật của máy. Không dùng IP container, `0.0.0.0` hay `127.0.0.1` cho robot ở máy khác. `setup.py` không ghi đè `.env`. Nếu IP đổi, sửa `NCKH_PUBLIC_HOST`, chạy `docker compose -f compose.nckh.yaml up -d` và kiểm tra `server.websocket`, `server.ota`, `server.fronted_url`. Nên cố định IP qua DHCP reservation.

Mở `http://192.168.1.2:8002`, tạo tài khoản đầu tiên, đăng nhập và tạo trợ lý. Tài khoản quản trị dùng **Mô hình** để sửa provider/config dùng chung, **Vai trò** để gán model theo trợ lý, **Quản lý tham số** để sửa thiết lập hệ thống.

## 3. Model của Trợ lý Robot Việt

| Trường | Mã / lựa chọn |
|---|---|
| ASR | `ASR_NCKH` — PhoWhisper-small tiếng Việt |
| VAD | `VAD_SileroVAD` |
| LLM chính / nhỏ | `LLM_NCKH` — Robot AI: Demo / DeepSeek |
| Nhận dạng ý định | `Intent_NCKH`, kiểu function_call |
| Bộ nhớ | `Memory_nomem` — Không lưu bộ nhớ dài hạn |
| Văn bản thành giọng nói | `TTS_NCKH` — EdgeTTS Hoài My/Nam Minh |
| Ngôn ngữ / giọng | Tiếng Việt / Hoài My hoặc Nam Minh |

ASR/VAD được hiển thị trực tiếp ở Vai trò trong v2. Nhấn Lưu cấu hình rồi kết nối lại thiết bị để nạp phiên mới. Với trợ lý cũ, mở Chỉnh sửa chức năng và kiểm tra các plugin NCKH; tạo trợ lý mới theo mẫu mặc định đã có đầy đủ.

`server-base` chỉ có ASR/VAD là đúng cơ chế nạp cấu hình chung. LLM/TTS/Intent/Memory được lấy theo trợ lý sau khi thiết bị được định danh.

## 4. Kiểm thử ngay trên web, không cần firmware

Mở **Kiểm thử server** trên menu hoặc `http://localhost:8002/#/server-lab`.

1. Chọn trợ lý và Kết nối thiết bị ảo. Web lưu thiết bị `nckh-simulator` thuộc tài khoản/trợ lý hiện tại, nhận token riêng và kết nối WS. MAC được hiển thị, không gửi server secret hay DeepSeek key cho trình duyệt.
2. Hội thoại: gửi “Xin chào robot”. Demo trả lời cố định. Phải nhận được gói âm thanh và nghe được bằng trình phát; trình duyệt chặn tự phát thì nhấn Play.
3. ASR/TTS: tạo giọng nói, sau đó tải WAV/MP3/M4A có giọng bạn. Tối đa 8 MB, nhận dạng 30 giây đầu. Hai phép thử không gọi DeepSeek và dùng đúng cấu hình trợ lý.
4. Plugin: thử `get_lunar` với `{"date":"2026-02-17"}`, kỳ vọng 1/1 năm Bính Ngọ. Thử tin, vàng, thời tiết. Đọc nội dung lỗi nguồn; HTTP 200 không có nghĩa dữ liệu đã lấy thành công.
5. MCP mô phỏng: thử đủ 5 nút. Khoảng cách là số bạn đặt; JSON ghi `simulated:true`. Luồng đi qua Java → voice → WS → thiết bị ảo → phản hồi MCP; không có GPIO thật.
6. Nhắc nhở: chọn MAC, nhập nội dung, Đặt sau 1 phút rồi Lưu. Giữ trang online để nghe. Thử hủy, lặp ngày/tuần, offline qua giờ hẹn rồi reconnect để nhắc bù.

Không mở đồng thời hai trang dùng cùng MAC ảo. Mỗi thiết bị đại diện cho một kết nối. Chỉ hội thoại ở mode deepseek mới chứng minh LLM tự chọn công cụ; các nút trực tiếp giúp tách lỗi từng thành phần.

### Thử Opus vào → ASR → LLM → Opus ra

CLI đã có trong image voice, dùng libopus và ffmpeg cài sẵn. Dùng MAC ảo vừa tạo, ngắt web trước khi dùng CLI; thay MAC ví dụ:

```powershell
docker compose -f compose.nckh.yaml exec -T voice python /opt/robot_client.py --host web --ws-url ws://voice:8000/xiaozhi/v1/ --device-id 02:AA:BB:CC:DD:EE --text "Xin chào robot" --output /tmp/robot-reply.wav --report /tmp/robot-report.json

docker compose -f compose.nckh.yaml cp .\thu-am.wav voice:/tmp/thu-am.wav
docker compose -f compose.nckh.yaml exec -T voice python /opt/robot_client.py --host web --ws-url ws://voice:8000/xiaozhi/v1/ --device-id 02:AA:BB:CC:DD:EE --wav /tmp/thu-am.wav --output /tmp/robot-reply.wav --report /tmp/robot-report.json
docker compose -f compose.nckh.yaml cp voice:/tmp/robot-reply.wav .\robot-reply.wav
docker compose -f compose.nckh.yaml cp voice:/tmp/robot-report.json .\robot-report.json
```

CLI yêu cầu nhận audio, không coi riêng `tts/stop` là đạt. Với WAV còn cần ASR trả văn bản. `--stay-seconds 120` giữ online để thử lịch. Báo cáo có OTA, hello, MCP, frame và văn bản; không ghi token. Nếu chưa ghép, CLI trả mã để nhập trên web rồi chạy lại.

Lệnh trên dùng DNS nội bộ Docker để kiểm tra pipeline. Để kiểm tra LAN, chạy client từ máy khác với `--host IP_LAN`, không ghi đè `--ws-url`. Chạy CLI ngoài Docker cần `websockets==14.2`; chức năng mã hóa/ghi WAV cần ffmpeg, opuslib_next và libopus.

## 5. DeepSeek: khi nào trả phí, cách bật

| Việc thử | Cần DeepSeek? |
|---|---|
| Web, tài khoản, DB, OTA, WebSocket | Không |
| ASR, TTS, lời nhắc theo lịch, MCP trực tiếp | Không; EdgeTTS cần Internet |
| Âm lịch, tin, vàng, nhạc local | Không |
| OpenWeather | Khóa OpenWeather riêng |
| Hội thoại thông minh / LLM chọn công cụ | Có khi dùng DeepSeek |
| Plugin dịch và IPA | Có, cả khi hội thoại đang ở demo |

Vào [DeepSeek Platform](https://platform.deepseek.com/), đăng nhập, nạp số dư ở mục thanh toán theo phương thức đang được hỗ trợ, rồi tạo khóa tại API keys. Tín dụng API dùng cho chương trình theo lượng token; không phải gói ChatGPT Pro. Không đặt khóa trong firmware, Vue hoặc Git.

```dotenv
NCKH_LLM_MODE=deepseek
DEEPSEEK_API_KEY=KHOA_THAT_CUA_BAN
DEEPSEEK_MODEL=deepseek-flash
```

```powershell
docker compose -f compose.nckh.yaml up -d --force-recreate voice
python deploy/nckh/check_deepseek.py
python deploy/nckh/check_deepseek.py --chat
```

`--chat` gọi thật và có thể tính phí. Sau khi đổi mode/model, reconnect thiết bị. Xem model và giá hiện hành tại [DeepSeek docs](https://api-docs.deepseek.com/quick_start/pricing/); không dùng giá cũ để cam kết chi phí. 401 thường do khóa, 402 số dư, 429 giới hạn dịch vụ. Plugin dịch trả translation/english_ipa/explanation_vi; IPA do LLM sinh nên cần đối chiếu khi dùng để dạy phát âm.

## 6. TTS offline

Chỉ bật engine cần dùng. Lần đầu vẫn cần Internet để tải package/model. Offline là suy luận sau khi cache đầy đủ, không phải cài mới hoàn toàn không mạng.

```powershell
# Piper
docker compose -f compose.nckh.yaml --profile piper up -d --build piper
docker compose -f compose.nckh.yaml --profile piper logs -f --tail 30 piper

# Hoặc VieNeu
docker compose -f compose.nckh.yaml --profile vieneu up -d --build vieneu
docker compose -f compose.nckh.yaml --profile vieneu logs -f --tail 30 vieneu
```

Chờ `TTS offline sẵn sàng` rồi chọn trong Vai trò:

| Engine | Model | Giọng | Endpoint nội bộ |
|---|---|---|---|
| Piper | TTS_PIPER_NCKH | VAIS 1000 | http://piper:5100 |
| VieNeu CPU/ONNX | TTS_VIENEU_NCKH | Hải Đăng | http://vieneu:5100 |

Lưu rồi reconnect. Không đổi endpoint thành localhost. VieNeu có `VIENEU_PRECISION=int8` phù hợp i7-13620H; `fp32` cho CPU cũ. Hai engine dùng container và cache riêng, không nâng PyTorch trong voice.

Sau khi tải thành công, thêm `NCKH_TTS_OFFLINE=1` và recreate engine để cấm tải model. Xóa volume sẽ mất cache. Không public cổng TTS ra LAN; endpoint cần server secret từ môi trường Docker.

EdgeTTS NoAudioReceived có thể do dịch vụ hoặc mạng. V2 thử lại có giới hạn, đổi giữa hai giọng Việt và bỏ dữ liệu dở. Không bảo đảm Edge luôn sẵn sàng; có thể chủ động chuyển model offline.

## 7. Plugin và lịch nhắc

- Nhạc: chép MP3/WAV/OGG/FLAC có quyền sử dụng vào `music/`, tên có nghĩa và có thể có dấu. Không tìm thấy sẽ báo rõ. Compose mount chỉ đọc.
- Thời tiết: đặt `OPENWEATHER_API_KEY`, recreate voice, thử `{"city":"Da Lat,VN"}`.
- Tin: moi-nhat, thoi-su, the-gioi, khoa-hoc, kinh-doanh, giao-duc; giới hạn 1–5 tin từ RSS cho phép.
- Vàng: ví dụ `SJL1L10` trong nước; `XAUUSD` là USD/oz. Kết quả giữ nguồn, thời gian và đơn vị. Nguồn đổi/bị chặn thì báo lỗi, không suy đoán giá.
- Âm lịch: UTC+7, ngày dương 1900–2099, có tháng nhuận.

Lịch lưu UTC; giờ không có offset được hiểu UTC+7. Hỗ trợ none/daily/weekly. Chỉ phát khi thiết bị đã ghép, online và rảnh. Offline qua giờ hẹn sẽ nhắc bù khi reconnect. Lịch lặp nhắc bù một lần rồi đưa kỳ tiếp theo đến tương lai, không đọc liên tục mọi kỳ đã lỡ.

| Trạng thái | Ý nghĩa |
|---|---|
| pending | Chờ thời gian/thiết bị rảnh |
| sending | Đang tạo/gửi âm thanh |
| queued | Đã gửi audio qua WS; chưa có ACK loa vật lý |
| cancelled | Đã hủy |

Hủy khi đang gửi được scheduler phát hiện ở lần quét kế tiếp, thường trong 10 giây khi DB/server hoạt động. Audio đã tới loa không thể thu hồi; Ngắt lời dừng phiên hiện tại. Lỗi TTS, ngắt lời/mất kết nối không được ghi là gửi xong. Server chết đúng lúc sau phát trước cập nhật DB có thể gửi lại; chưa có ACK phần cứng để bảo đảm exactly-once.

## 8. Bàn giao cho bạn firmware

```text
Web:       http://192.168.1.2:8002
OTA:       http://192.168.1.2:8002/nckhsv/ota/
WebSocket: ws://192.168.1.2:8000/xiaozhi/v1/
```

Thay IP đúng `.env`; alias WS `/nckh/v1/` được hỗ trợ. Ưu tiên URL trả từ OTA. Cùng LAN, tránh Wi-Fi guest cô lập thiết bị, mở firewall TCP 8000/8002 mạng riêng.

Firmware POST OTA với Device-Id (MAC), Client-Id, application và board.type. Ghép mã sáu số trên web vào đúng trợ lý. Lấy token OTA rồi gửi `Authorization: Bearer ...` khi mở WS; không gửi server secret hoặc DeepSeek key cho firmware. Gửi hello với features.mcp=true, Opus mono 16 kHz, frame 60 ms, công bố tools/list.

| Tool | Tham số server chấp nhận |
|---|---|
| self.led.set_mode | led left/right/both; mode off/on/blink_slow/blink_fast/breathe |
| self.robot.move | direction forward/backward/left/right/stop; duration_ms 0–2000 |
| self.robot.set_servo | part neck/arm_left/arm_right; angle 0–180 |
| self.robot.get_distance | Không tham số |
| self.robot.wave_hand | which left/right/both; times 1–10 |

Thống nhất với firmware giới hạn 2 giây/lệnh di chuyển, ý nghĩa góc servo, đơn vị khoảng cách và cấu trúc lỗi. Nghiệm thu: OTA/ghép → hello/MCP → cảm biến → LED → servo → motor ngắn → giọng nói → lịch và reconnect. Lỗi/timeout không được xác nhận robot đã thực thi.

Mô phỏng không xác nhận chất lượng mic/loa, nguồn, cơ khí, cảm biến hay chế độ ngủ. Cấu hình này hướng tới LAN. OTA kế thừa nhận diện theo MAC và cấp token; MAC không phải bí mật đủ mạnh cho dịch vụ public. Khi ra Internet cần HTTPS/WSS, provisioning khóa thiết bị cùng phía firmware và kiểm thử bảo mật riêng.

## 9. Sao lưu và chẩn đoán

```powershell
python deploy/nckh/backup_db.py
docker compose -f compose.nckh.yaml ps
docker compose -f compose.nckh.yaml logs --tail 100 api voice
```

SQL ở backups/. Sao lưu riêng `.env`, model, nhạc và upload cần giữ; DB dump không gồm các tệp này. Chỉ restore SQL tin cậy sau khi có bản sao hiện tại và dừng thao tác người dùng:

```powershell
python deploy/nckh/restore_db.py --file .\backups\TEN_BAN_SAO.sql --confirm-restore
```

Thao tác thay thế dữ liệu hiện tại. Script restart API/voice để nạp dữ liệu/migration. Không restore tự động khi nâng cấp.

## 10. Kiểm thử mã nguồn

```text
python -m pip install pytest PyYAML numpy httpx loguru aiohttp openai websockets
python -m pytest deploy/nckh/tests -q
cd main/manager-web
npm ci
npm test
npm run build
cd ../manager-api
mvn "-Dtest=NckhLabControllerTest,DeviceEnrollmentPermissionTest,ConfigServiceImplTest,DeviceServiceImplTest,DeviceAutoUpdateTest,DeviceTimeSerializationTest,ShiroConfigTest" test
mvn package -DskipTests
```

Java cần JDK 21. Các unit dùng mock/stub không gọi API tính phí. Xem KET_QUA_KIEM_THU_V2.md để biết phần đã chạy và các bài cần Docker/robot/khóa thật. Không suy từ unit test sang độ chính xác ASR hay hiệu năng trên laptop.

## Phạm vi và nguồn

Gmail OAuth, VPS/GPU, vision/RAG/voiceprint và mở rộng MQTT/UDP là hướng mở rộng được nhắc ở tài liệu gốc; không được ghi là đã nghiệm thu trong bản này. Tính năng server cốt lõi của đề tài gồm pipeline giọng Việt, các plugin, lịch nhắc, quản trị và giao thức firmware.

[Xiaozhi server](https://github.com/xinnan-tech/xiaozhi-esp32-server), [PhoWhisper](https://huggingface.co/vinai/PhoWhisper-small), [DeepSeek](https://api-docs.deepseek.com/), [VieNeu SDK](https://github.com/pnnbao97/VieNeu-TTS/blob/main/README_PYPI.md), [Piper API](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/API_PYTHON.md), [giọng VAIS1000](https://huggingface.co/rhasspy/piper-voices/tree/main/vi/vi_VN/vais1000/medium), [vang.today](https://www.vang.today/vi/api), [âm lịch Hồ Ngọc Đức](https://www.informatik.uni-leipzig.de/~duc/amlich/calrules.html).

Giữ bản quyền upstream. Piper engine thuộc dự án GPL; engine và trọng số/giọng có giấy phép riêng. Kiểm tra giấy phép trước khi phân phối sản phẩm. ZIP giữ tài nguyên VAD upstream; không kèm trọng số PhoWhisper/VieNeu/Piper tải thêm.
