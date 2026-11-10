> Tài liệu lịch sử. Với gói v3, dùng [HUONG_DAN_V3.md](HUONG_DAN_V3.md) và bộ cài `install.py`; không chạy quy trình cũ bên dưới.

> Tài liệu v1. Dùng HUONG_DAN_V2.md, THAY_DOI_V2.md và KET_QUA_KIEM_THU_V2.md cho bản hiện tại.

# Hướng dẫn triển khai Robot AI tiếng Việt

Ngày đối chiếu: 04/11/2026. Phạm vi: server Python, web Vue, API Java và hạ tầng Docker. Không sửa, build hoặc nạp firmware trong gói này.

## 1. Kết quả chỉnh sửa và phạm vi sử dụng

Bộ mã nguồn gốc đã có giao thức âm thanh, MCP, quản trị thiết bị/người dùng và tệp dịch giao diện tiếng Việt. Tuy nhiên, cấu hình mặc định dùng ASR/nhân vật tiếng Trung. ZIP không chứa các bản nâng cấp riêng mà giảng viên mô tả như `pho_whisper_ct2.py`, `vieneu_local.py`, `piper_local.py`, bảng nhắc nhở và scheduler.

Gói này bổ sung một cấu hình triển khai NCKH, xây dựng image trực tiếp từ mã nguồn đã sửa. Cấu hình gốc, tài liệu upstream và giấy phép MIT vẫn được giữ để tra cứu. Dùng `compose.nckh.yaml` cho đề tài; các compose cũ là tài liệu tham khảo upstream.

| Thành phần | Cấu hình đề tài |
|---|---|
| Web | Vue, mặc định tiếng Việt; Element UI và thông báo API có bản Việt |
| API quản trị | Spring Boot, Java 21; MySQL và Redis nội bộ |
| ASR | PhoWhisper-small của VinAI, chuyển CTranslate2 int8, CPU, ngôn ngữ `vi` |
| LLM | Chế độ `demo` để thử kết nối; `deepseek` cho hội thoại và gọi công cụ thật |
| TTS | EdgeTTS Hoài My / Nam Minh, cần Internet |
| Công cụ server | Tin VnExpress, thời tiết OpenWeather, tạo/liệt kê/hủy lời nhắc, nhạc upstream |
| Phần cứng | Dùng MCP mà firmware gửi lên; không viết lại driver GPIO trên server |
| Nhắc nhở | MySQL, một lần/hằng ngày/hằng tuần; chờ thiết bị online để nhắc bù |

Không đưa vào cấu hình mặc định: digital-human, ứng dụng mobile, clone giọng, RAG, Gmail OAuth, các dịch vụ Trung Quốc. Mã upstream liên quan vẫn được giữ. VieNeu/Piper, giá vàng và dịch có IPA chưa được bổ sung vì thiếu provider/đặc tả API tương ứng trong ZIP. Công cụ âm lịch `cnlunar` gốc không được tự bật cho cấu hình NCKH: chưa có xác nhận lịch âm Việt Nam theo UTC+7.

Việt hóa tập trung vào giao diện chính và luồng Robot Việt. Chú thích, log kỹ thuật, tên model/provider cũ và tài liệu upstream vẫn có thể còn tiếng Trung. Không thay định danh giao thức bằng tiếng Việt.

## 2. Kiến trúc và cổng

| Dịch vụ Docker | Cổng máy tính | Vai trò |
|---|---|---|
| `web` | 8002 | Giao diện, proxy API/OTA, proxy vision |
| `api` | Không mở trực tiếp | Spring Boot tại cổng nội bộ 8003 |
| `voice` | 8000 | WebSocket hai chiều; HTTP vision tại 8003 nội bộ |
| `db` | Không mở trực tiếp | MySQL 8.4, lưu bền |
| `redis` | Không mở trực tiếp | Redis 8.0, lưu bền |
| `model-setup` | Không | Chạy một lần để tải/chuyển model ASR |

Web và Python cùng cần cổng 8003 bên trong hai container khác nhau, nên không xung đột. Khởi động có kiểm tra sức khỏe MySQL/Redis/API. API, web và voice đều build từ nguồn local, không dùng image upstream dựng sẵn để rồi mất các chỉnh sửa.

Công việc tải/chuyển PhoWhisper được tách khỏi voice: công cụ chuyển model dùng PyTorch mới; voice giữ dependency upstream. Việc này tránh ép thay phiên bản PyTorch của toàn dự án chỉ để chuyển một model.

## 3. Chuẩn bị máy Windows hoặc Linux

1. Cài Docker Desktop với Linux containers (Windows dùng WSL2), hoặc Docker Engine + Compose v2 trên Linux.
2. Cài Python 3.10 trở lên để chạy các script cấu hình/kiểm tra. Không cần cài Java/Node trên máy nếu build bằng Docker.
3. Giải nén gói vào thư mục riêng, mở terminal tại thư mục chứa `compose.nckh.yaml`.
4. Dùng `ipconfig` (Windows) hoặc `ip addr` (Linux) để lấy IPv4 của card đang nối cùng mạng robot. Ví dụ `192.168.1.19`; đây là ví dụ, không phải IP bắt buộc.
5. Nên đặt DHCP reservation cho máy chủ. Bản đầu chạy CPU; không cần GPU NVIDIA để khởi động cấu hình này. Máy 16 GB RAM cần cấp đủ tài nguyên cho Docker và tránh chạy đồng thời nhiều phần mềm nặng. Chưa có benchmark để cam kết số robot đồng thời.

## 4. Chạy lần đầu, chưa cần mua DeepSeek

Thay IP ví dụ bằng IP thật:

```powershell
python deploy/nckh/setup.py --host 192.168.1.19
docker compose -f compose.nckh.yaml --profile setup build
docker compose -f compose.nckh.yaml --profile setup run --rm --no-deps model-setup
docker compose -f compose.nckh.yaml up -d
docker compose -f compose.nckh.yaml ps
python deploy/nckh/check_server.py --host 127.0.0.1
```

Lần build/tải đầu cần Internet và có thể lâu: tải dependency Python, npm, Maven, image hệ thống và model. Script chuyển model tải `vinai/PhoWhisper-small`, rồi tạo `models/phowhisper-small-ct2/model.bin`. Gói ZIP không kèm trọng số model. Không chép trực tiếp `pytorch_model.bin` vào thư mục CT2 để thay `model.bin`.

`setup.py` tạo `.env` có mật khẩu MySQL và secret ngẫu nhiên. Nó từ chối ghi đè tệp đã tồn tại. Giữ `.env` để các lần chạy sau dùng cùng mật khẩu; không commit hoặc gửi kèm khóa cho bạn lập trình firmware. Nếu muốn tái lập chính xác model, đặt `PHOWHISPER_REVISION` bằng commit của VinAI trước khi tải.

Mở `http://IP_MAY_CHU:8002`. Chọn tiếng Việt nếu trình duyệt đã lưu một lựa chọn ngôn ngữ trước đó. Tài khoản đăng ký đầu tiên là quản trị viên theo logic upstream. Không có mật khẩu admin cố định được thêm vào bản này. Đăng ký và đặt mật khẩu riêng trước khi cho người khác truy cập mạng thử nghiệm.

Tạo trợ lý. Mẫu mặc định mới là **Trợ lý Robot Việt**, gồm:

| Trường | Giá trị |
|---|---|
| ASR | `ASR_NCKH` |
| LLM | `LLM_NCKH` |
| TTS | `TTS_NCKH` |
| Giọng | Hoài My (`vi-VN-HoaiMyNeural`) hoặc Nam Minh |
| Intent | `Intent_NCKH`, kiểu `function_call` |
| Memory | `Memory_nomem` |

Trợ lý tạo mới theo `LLM_NCKH` được gán các plugin NCKH mặc định. Trợ lý cũ không tự đổi cấu hình hay plugin. Nếu dùng dữ liệu cũ, cần chọn các model và plugin này trong trang chỉnh trợ lý.

Trong chế độ `demo`, robot vẫn cần model ASR và mạng cho EdgeTTS. Nó trả lời một câu xác nhận cố định để thử mic → ASR → server → loa. Đây không phải chatbot hoàn chỉnh và không tự chọn công cụ/MCP. Không có lời gọi DeepSeek trong chế độ này.

## 5. Khi nào cần trả tiền DeepSeek?

| Việc thử | Cần DeepSeek trả phí? |
|---|---|
| Build Docker, mở web, đăng ký, tạo trợ lý | Không |
| OTA, ghép robot, bắt tay WebSocket | Không |
| Nhận dạng tiếng Việt bằng PhoWhisper local | Không |
| Nghe câu phản hồi cố định của chế độ demo | Không; EdgeTTS vẫn cần mạng |
| Hội thoại tự nhiên bằng DeepSeek | Có lời gọi API, cần khóa hợp lệ và số dư được cấp hoặc đã nạp |
| Yêu cầu LLM chọn plugin/MCP bằng lời nói | Có khi dùng cấu hình DeepSeek |
| Bộ hẹn giờ phát một lời nhắc đã lưu | Không gọi DeepSeek lúc đến giờ; dùng TTS trực tiếp |
| Dữ liệu thời tiết | Khóa OpenWeather riêng, không dùng khóa DeepSeek |

DeepSeek chỉ đảm nhận phần xử lý ngôn ngữ. Nạp tiền DeepSeek không cung cấp ASR, TTS, dữ liệu thời tiết hay kết nối phần cứng.

### Đăng ký và nạp tiền

1. Vào trang chính thức https://platform.deepseek.com, đăng ký/đăng nhập.
2. Vào **API keys**, tạo khóa cho dự án và lưu riêng. Đây là khóa server; không đặt trong Vue, firmware hoặc Git.
3. Vào **Top up** và nạp theo nhu cầu. Phương thức thanh toán, số tiền tối thiểu và khả năng thanh toán tại Việt Nam phải xem trực tiếp trên tài khoản của bạn; tài liệu công khai được kiểm tra không đủ để đảm bảo mọi thẻ/ngân hàng đều dùng được. Không cần mua tài khoản bán lại.
4. Xem bảng giá tại https://api-docs.deepseek.com/quick_start/pricing/ và mức sử dụng trong trang quản trị. Chi phí tính theo token đầu vào/đầu ra, trừ vào số dư được cấp/nạp. Không giả định có số dư miễn phí cho mọi tài khoản.
5. Trong `.env` ở thư mục gốc, đổi:

```dotenv
NCKH_LLM_MODE=deepseek
DEEPSEEK_API_KEY=DIEN_KHOA_CUA_BAN_TAI_DAY
DEEPSEEK_MODEL=deepseek-flash
```

Không dùng dòng placeholder làm khóa thật. `deepseek-flash` là tên model được tài liệu chính thức hướng dẫn tại ngày đối chiếu; không khóa cứng tên `deepseek-v4-flash` cũ trong mô tả đề tài.

Kiểm tra và áp dụng:

```powershell
python deploy/nckh/check_deepseek.py
python deploy/nckh/check_deepseek.py --chat
docker compose -f compose.nckh.yaml up -d --force-recreate voice
```

Lệnh đầu đọc danh sách model. Lệnh có `--chat` gửi một câu chào thật, có thể tính phí token. Script không in khóa. Khởi động lại robot để bắt đầu phiên mới sau khi đổi model/cấu hình.

Các giá trị LLM mới: base URL `https://api.deepseek.com`, `max_tokens=512`, tắt chế độ suy nghĩ để phù hợp tương tác giọng nói. Có thể đổi hạn mức trong model, không nên đặt chỉ 120 nếu cần chuỗi tool-call dài. Trả lời ngắn được điều khiển thêm bằng prompt. API key trong biến môi trường được ưu tiên hơn trường khóa trong model.

HTTP 401 thường là khóa không hợp lệ; 402 là thiếu số dư; 429 là giới hạn dịch vụ. Giá, model và phương thức thanh toán có thể thay đổi, xem trang chính thức trước khi nạp.

## 6. Kết nối phần cứng đã hoàn thành firmware

### Thông tin chuyển cho bạn phụ trách firmware

| Nội dung | Ví dụ với máy chủ `192.168.1.19` |
|---|---|
| Mạng | ESP32 và máy chủ cùng LAN, ESP32 dùng Wi-Fi phù hợp board |
| OTA cấu hình | `http://192.168.1.19:8002/nckhsv/ota/` |
| OTA tương đương theo upstream | `http://192.168.1.19:8002/xiaozhi/ota/` |
| WebSocket được OTA trả về | `ws://192.168.1.19:8000/nckh/v1/` |
| Trang ghép thiết bị | `http://192.168.1.19:8002` |
| Định danh | `Device-Id` là MAC/ID của robot; `Client-Id` theo firmware |
| Xác thực WebSocket | Token lấy từ phản hồi OTA; server không cấp khóa DeepSeek cho robot |
| Âm thanh vào | Opus, mono; server giải mã về PCM16 16 kHz cho ASR |
| MCP | `hello.features.mcp=true`, rồi JSON-RPC initialize/tools/list |

Giao thức WebSocket gốc không ràng buộc duy nhất đường dẫn `/xiaozhi/v1/`, nên chấp nhận `/nckh/v1/`. Nginx thêm alias `/nckhsv/` cho firmware trong mô tả. Không đổi trường JSON `hello`, `listen`, `mcp`, `audio_params` sang tiếng Việt.

### Trình tự thực hiện

1. Chạy server theo mục 4; chạy script kiểm tra từ máy khác cùng LAN bằng `--host IP_MAY_CHU` để xác nhận truy cập qua mạng.
2. Cho robot vào chế độ cấu hình Wi-Fi của firmware và nối cùng mạng. Chỉ cần cáp USB nếu cần nạp/cấu hình hoặc xem log; luồng hoạt động thường ngày đi qua Wi-Fi.
3. Kiểm tra URL OTA hiện tại của firmware. Nếu firmware cho đổi URL OTA trong giao diện cấu hình/NVS, thay ở đó. Nếu URL được đóng cứng khi build, nhờ bạn firmware đổi hằng cấu hình và nạp lại. Việc firmware “đã hoàn tất” không có nghĩa đã trỏ đúng máy chủ mới. Không thể sửa một URL đóng cứng chỉ bằng web server.
4. Khởi động robot, xem log serial: có IP → OTA POST thành công → nhận URL/token WebSocket. Không dùng `localhost`, `127.0.0.1`, tên container `api` hoặc `voice` làm địa chỉ máy chủ trên robot.
5. Robot chưa được gán trợ lý sẽ nhận/hiển thị mã kích hoạt. Vào trợ lý trên web → quản lý thiết bị → thêm/ghép thiết bị → nhập mã đang còn hiệu lực. Sau khi ghép, khởi động lại robot để nó lấy lại OTA và cấu hình.
6. Kiểm tra log `voice` có kết nối và bắt tay `hello`. Trong `demo`, nói một câu tiếng Việt và kiểm tra có câu xác nhận từ loa. Nếu nhận chữ đúng nhưng không có tiếng, kiểm tra Internet cho EdgeTTS và phần phát loa của firmware.
7. Bật DeepSeek theo mục 5. Thử hội thoại trước, sau đó thử “đọc khoảng cách” hoặc “bật đèn mắt” qua MCP. Cuối cùng mới thử servo/motor với thời lượng nhỏ.

Trên Windows, cho phép TCP 8000 và 8002 trong Windows Defender Firewall cho mạng Private. Kiểm tra Wi-Fi không bật AP/client isolation. Không cần mở cổng MySQL/Redis ra LAN. Không nối chân GPIO vào máy server: mic, loa, LED, servo và motor vẫn do firmware điều khiển.

### MCP và trách nhiệm hai phía

Server gửi `initialize` và `tools/list` sau `hello`. Firmware cần trả kết quả JSON-RPC theo ID yêu cầu; tool phần cứng không được “nhét toàn bộ trong hello”. Sau đó LLM mới nhìn thấy danh sách công cụ và server chuyển `tools/call` xuống robot.

Danh sách trong mô tả là kỳ vọng:

| Tool | Tham số mô tả |
|---|---|
| `self.led.set_mode` | `led`, `mode` |
| `self.robot.move` | `direction`, `duration_ms` |
| `self.robot.set_servo` | `part`, `angle` |
| `self.robot.get_distance` | Không có |
| `self.robot.wave_hand` | `which`, `times` |

`tools/list` thực tế là nguồn xác định tên, kiểu và giới hạn. Gói tải lên không chứa firmware nên chưa xác minh được chính xác schema tool, thứ tự bắt tay của bản firmware bạn đang có, hay giới hạn servo/motor. Bạn firmware cần đưa log `hello` + `tools/list` để đối chiếu khi tích hợp. Không tạo plugin server giả với các tên này để thay thế phần cứng.

## 7. Plugin và nhắc nhở

OpenWeather: lấy khóa riêng ở https://openweathermap.org, đặt `OPENWEATHER_API_KEY` trong `.env`, tạo lại container `voice`. Plugin gọi Current Weather với `lang=vi`, `units=metric`. Tin VnExpress dùng RSS danh mục cố định, không cần khóa DeepSeek riêng cho nguồn tin; LLM vẫn gọi để quyết định và diễn đạt câu trả lời trong chế độ thật.

Ví dụ lời nói sau khi bật DeepSeek:

- “Thời tiết Đà Lạt hiện tại thế nào?”
- “Đọc cho mình ba tin mới nhất.”
- “Ngày mai lúc 7 giờ sáng nhắc mình uống nước.”
- “Nhắc uống nước hằng ngày lúc 7 giờ sáng.”
- “Liệt kê lời nhắc của mình”, rồi “hủy lời nhắc …”.

Bảng mới là `ai_reminder_nckh`; không giả định bảng `ai_reminder` của giảng viên tồn tại. Mỗi lời nhắc gắn với `device_id`. API/plugin hủy và liệt kê lọc theo đúng ID thiết bị. Thời gian lưu UTC; đầu vào không có múi giờ được hiểu là giờ Việt Nam. Hằng ngày/hằng tuần giữ chu kỳ; nếu bỏ lỡ nhiều lần, nhắc bù một lần rồi tính lần kế tiếp trong tương lai.

Scheduler quét mỗi 10 giây. Thiết bị offline hoặc đang nói/nghe thì giữ trạng thái chờ, chưa chiếm lời nhắc. Khi online và rảnh, gửi `tts/start` mở kênh loa trước, rồi đưa chuỗi FIRST → TEXT → LAST vào TTS; không cần gọi LLM thêm vào lúc hẹn. Chỉ chạy **một replica `voice`** trong cấu hình này vì registry kết nối nằm trong bộ nhớ tiến trình.

Trạng thái `queued` có nghĩa đã đưa vào hàng đợi TTS, không phải xác nhận loa đã phát. Lỗi TTS/mất điện sau khi xếp hàng có thể khiến robot không nghe được; lỗi/crash giữa enqueue và cập nhật DB có thể dẫn đến lặp thông báo khi thử lại. Chưa có cơ chế ACK từ firmware để bảo đảm phát đúng một lần. Đây là lời nhắc hỗ trợ, không dùng cho báo động bắt buộc tin cậy.

`close_connection_no_voice_time=86400` chỉ nới thời gian im lặng phía server. Nó không đảm bảo robot online 24/7, không ngăn mất Wi-Fi/hết pin và không thay chính sách sleep của bản firmware thực tế. Lệnh kết thúc hội thoại vẫn có thể đóng kết nối.

## 8. Vận hành và sửa lỗi

```powershell
docker compose -f compose.nckh.yaml logs --tail 100 api voice web
python deploy/nckh/backup_db.py
docker compose -f compose.nckh.yaml down
docker compose -f compose.nckh.yaml up -d
```

`down` giữ named volumes. Không dùng `down -v` nếu muốn giữ tài khoản, thiết bị, lời nhắc và cấu hình. Sao lưu SQL cùng `.env` và thư mục model; bản sao lưu không tự bao gồm toàn bộ file upload. Upload nằm trong volume `uploads` và cần sao lưu riêng nếu đã sử dụng. Script backup dùng luồng byte, tránh lỗi UTF-16 do redirect PowerShell đời cũ.

| Hiện tượng | Kiểm tra |
|---|---|
| Chưa có `model.bin` | Chạy `model-setup`, xem log tải Hugging Face |
| Web 502 | `docker compose ... ps`, log API, MySQL healthy; không chỉ restart web liên tục |
| OTA báo thiếu websocket/ota | `.env` có IP đúng, log `NckhBootstrap`, API khởi động thành công |
| Thiết bị không thấy server | Cùng LAN, firewall 8000/8002, AP isolation, URL OTA thật của firmware |
| WebSocket xác thực lỗi | Lấy lại OTA/token sau restart; không chép token cũ hoặc nhập secret vào firmware |
| Robot chỉ nói câu xác nhận | Đang `NCKH_LLM_MODE=demo`; bật DeepSeek và tạo lại `voice` |
| ASR đúng, TTS im lặng | EdgeTTS cần Internet, kiểm tra giọng, loa, sample rate, log |
| Không có MCP tool | Firmware báo `features.mcp`, trả initialize/tools/list; Intent `function_call` |
| Nhắc không kêu | Thiết bị online/rảnh, plugin bật, MySQL hoạt động; kiểm tra trạng thái pending/queued |
| Sửa `.env` chưa hiệu lực | Dùng `up -d --force-recreate voice`, không chỉ `restart` |
| Đổi IP máy chủ | Sửa `NCKH_PUBLIC_HOST` trong `.env`, tạo lại `api voice`, cập nhật OTA firmware nếu cần |
| Giao diện vẫn ngôn ngữ cũ | Chọn Tiếng Việt và tải lại; gỡ service worker cũ nếu dùng cùng origin trước đây |

Nên đổi tham số qua giao diện quản trị để đồng bộ cache. Không dùng `FLUSHALL` như thao tác thường xuyên. Bootstrap của cấu hình Docker cập nhật URL/secret qua service của API và xóa riêng cache cấu hình server.

Bản này là cấu hình LAN HTTP/WS. Đưa lên VPS cần tên miền, HTTPS/WSS, reverse proxy và xác minh firmware hỗ trợ TLS. Không chỉ đổi IP LAN thành IP public rồi xem như triển khai production hoàn chỉnh.

## 9. Kiểm thử và nghiệm thu còn lại

Đã thực hiện trong môi trường bàn giao:

- Build production giao diện Vue thành công; có workaround chỉ trong môi trường kiểm thử vì không được liệt kê card mạng. Workaround không nằm trong gói source.
- 6 tệp i18n, mỗi tệp 1546 khóa, kiểm tra đồng bộ đạt.
- 10 contract tests, 13 snapshot tests và 70 unit tests giao diện đạt.
- 23 kiểm thử NCKH đạt: thời gian UTC+7/lặp, truy vấn theo thiết bị, nhắc khi offline/busy, chuỗi TTS, reconnect, demo không gọi cloud, khóa thiếu, RSS/thời tiết và hợp đồng plugin, cache/PCM provider ASR, cấu hình triển khai/setup.
- Python compile check đạt; SQL NCKH được phân tích cú pháp theo MySQL (26 câu lệnh). Đây chưa phải thực thi migration trên MySQL.

Chưa thực hiện: build JAR với Java 21, build/chạy toàn bộ container, chạy migration thật, tải/chuyển và suy luận model thật, gọi DeepSeek/EdgeTTS/OpenWeather/VnExpress trực tiếp, kết nối ESP32 và điều khiển MCP thật. Các kiểm thử provider dùng backend giả, không chứng minh độ chính xác ASR hay độ trễ thực tế. Không có Docker daemon/Java 21 và phần cứng tại môi trường bàn giao.

Checklist trên máy có robot:

1. `docker compose ... --profile setup build` thành công và chuyển model xong.
2. `db`, `redis`, `api`, `voice`, `web` khỏe; script kiểm tra đạt từ máy chủ và máy khác cùng LAN.
3. Đăng ký, đăng nhập, tạo trợ lý, ghép đúng robot; người khác không thấy thiết bị của tài khoản này.
4. Demo: mic → ASR tiếng Việt → câu trả lời TTS; ghi nhận transcript, thời gian và lỗi nếu có.
5. DeepSeek: hội thoại nhiều lượt, ngắt lời và phản hồi lỗi mạng/khóa/số dư.
6. MCP: so khớp tools/list; thử lần lượt LED, khoảng cách, tay/cổ và di chuyển có kiểm soát.
7. Nhắc một lần, lặp ngày/tuần, hủy, offline rồi kết nối lại; đối chiếu UTC+7 và trạng thái queued.
8. Khởi động lại Docker/máy và xác nhận dữ liệu còn; thử backup và phục hồi trên bản dữ liệu thử.

Chưa thể gọi bản này là đã nghiệm thu end-to-end chỉ dựa trên các unit test.

Chạy lại bộ kiểm thử NCKH (không gọi cloud, không cần phần cứng):

```powershell
python -m pip install pytest PyYAML httpx loguru numpy
python -m pytest deploy/nckh/tests -q
```

## 10. Nguồn chính thức đã đối chiếu

- DeepSeek Quick Start: https://api-docs.deepseek.com/
- DeepSeek Models & Pricing: https://api-docs.deepseek.com/quick_start/pricing/
- DeepSeek Error Codes: https://api-docs.deepseek.com/quick_start/error_codes
- DeepSeek Platform: https://platform.deepseek.com
- VinAI PhoWhisper-small: https://huggingface.co/vinai/PhoWhisper-small
- CTranslate2 Transformers conversion: https://opennmt.net/CTranslate2/guides/transformers
- OpenWeather Current Weather: https://openweathermap.org/current
- VnExpress RSS: https://vnexpress.net/rss

Khi viết báo cáo nghiên cứu, trích dẫn PhoWhisper của Le, Nguyen và Nguyen (ICLR 2024 Tiny Papers) theo model card của VinAI. Giữ LICENSE upstream khi phân phối mã nguồn.
