# ROBOT AI TIẾNG VIỆT — TÀI LIỆU TOÀN DIỆN

Tài liệu kiến trúc & vận hành đầy đủ: Firmware ESP32, Server Python, Docker, Web, Database, Protocol.

---

# PHẦN I — TỔNG QUAN KIẾN TRÚC

## Luồng hoạt động end-to-end
```
[Người nói] 
   ↓ (âm thanh)
[ESP32-S3 ziczac-ai-robot] — thu âm qua mic I2S, phát hiện wake word , Web hoặc Finger
   ↓ OTA lấy config (HTTP 8002) + kết nối WebSocket (8000)
[Server Python native — Windows or Ubuntu]
   ├─ ASR: PhoWhisper (CPU) → text tiếng Việt
   ├─ LLM: DeepSeek V4 Flash → hiểu + gọi tool
   ├─ Plugin: thời tiết, tin tức, giá vàng, dịch, nhắc nhở, điều khiển robot,...
   ├─ TTS: EdgeTTS (online) / VieNeu (offline đẹp) / Piper (offline nhẹ)
   └─ Lấy cấu hình từ manager-api
        ↓
[manager-api (Docker) — Spring Boot + Vue + MySQL + Redis]
   quản lý agent/user/thiết bị/model/plugin qua web console 8002
   ↓ (âm thanh TTS)
[ESP32-S3] — phát loa I2S + cử động (motor, servo, LED mắt)
```

## Ba khối phần mềm
1. **Firmware ESP32** (C/C++, ESP-IDF) — chạy trên robot, thu/phát âm thanh, điều khiển phần cứng.
2. **Server Python** (Server Robot) — bộ não AI, chạy native trên Windows hoặc Ubuntu.
3. **manager-api** (Docker) — quản trị đa người dùng, web console.

---

# PHẦN II — FIRMWARE ESP32 (MÃ nguồn mở https://github.com/78/xiaozhi-esp32/tree/main --> tự build thành board ziczac-ai-robot)

## Phần cứng
- **Chip:** ESP32-S3, flash 16MB, PSRAM OCT (SPIRAM).
- **Ngôn ngữ:** tiếng Việt (CONFIG_LANGUAGE_VI_VN), có wake word detection (AFE).
- **Nhà sản xuất:** "Zic Zac Robot AI", target esp32s3.

## Sơ đồ chân (GPIO) — từ config.h (Có thể chủ động thay đỗi lại)
| Bộ phận | Chân GPIO |
|---|---|
| Mic I2S | WS=4, SCK=5, DIN=6 |
| Loa I2S | DOUT=17, BCLK=16, LRCK=15 |
| LED trạng thái | 18 (builtin) |
| LED mắt trái/phải | trái=3, phải=21 |
| OLED (mắt hiển thị) | SDA=41, SCL=42 |
| Nút BOOT | 0 |
| Cảm ứng TTP223 | 7 |
| Màn hình SPI | MOSI=11, CLK=12, DC=10, RST=14, CS=13 |
| Motor trái (L298N) | IN1=38, IN2=39 |
| Motor phải (L298N) | IN3=40, IN4=45 |
| Servo cổ | 46 |
| Servo tay trái/phải | trái=1, phải=47 |

## Các thành phần điều khiển
- **2 motor DC** (L298N) — di chuyển bánh xe (tiến/lùi/trái/phải).
- **3 servo** — cổ (neck), tay trái (arm_left), tay phải (arm_right).
- **2 LED mắt** — hiệu ứng (on/off/blink/breathe).
- **OLED** — hiển thị mắt robot (oled_eyes.cc).
- **TFT2.8** — hiển thị thông tin nội dung trò chuyện.
- **Cảm biến siêu âm** — đo khoảng cách vật cản (vl6180x / ultrasonic).
- **Cảm ứng chạm** TTP223.

## 5 MCP Tool phần cứng (khai báo trong kst_ai_robot_board.cc)
Các tool này ESP32 gửi lên server khi kết nối (giao thức MCP). Đã Việt hóa mô tả sẵn trong firmware:

| Tool | Tham số | Chức năng |
|---|---|---|
| `self.led.set_mode` | led (left/right/both), mode (off/on/blink_slow/blink_fast/breathe) | Đèn LED mắt |
| `self.robot.move` | direction (forward/backward/left/right/stop), duration_ms | Di chuyển bánh xe |
| `self.robot.set_servo` | part (neck/arm_left/arm_right), angle (0-180) | Cử động cổ/tay |
| `self.robot.get_distance` | (không) | Đọc khoảng cách siêu âm (cm) |
| `self.robot.wave_hand` | which (left/right/both), times (1-10) | Vẫy tay (tự lặp) |

## Cơ chế kết nối & timeout (application.cc)
- **KHÔNG có timer tự ngắt khi idle** — firmware chỉ đóng kết nối khi: mất mạng, reboot, hoặc lỗi.
- **CanEnterSleepMode()** chỉ cho ngủ khi kênh audio ĐÃ ĐÓNG. Server giữ kênh mở → ESP32 không ngủ → online liên tục.
- **SetPowerSaveLevel(LOW_POWER)** chỉ giảm xung nhịp CPU nhẹ, KHÔNG cắt wifi.
- **HỆ QUẢ:** timeout do SERVER quyết định (close_connection_no_voice_time), không phải firmware. Đặt server = 86400s → robot online 24/7 (khi cắm điện).

## Build & nạp firmware
- Công cụ: ESP-IDF (không phải Arduino). Build một lần trên máy dev, nạp qua USB.
- **KHÔNG đóng Docker** (Docker khó truy cập USB, và build là tác vụ một lần).
- Khi bê server sang máy mới (IP đổi): chỉ cần build lại firmware trỏ IP mới, nạp qua USB. Firmware độc lập với "cục server".

---

# PHẦN III — SERVER PYTHON (Mã nguồn mở xiaozhi-server: https://github.com/xinnan-tech/xiaozhi-esp32-server/tree/main) --> build thành của mình

## Vị trí & cách chạy
- Đường dẫn: `...\main\nckhsv-server`
- Chạy: `python app.py` (native Windows, KHÔNG trong Docker)
- Phần cứng máy chủ: Windows, GTX 1050 2GB (chạy AI trên CPU), RAM 16GB, IP 192.168.1.19 (đang chạy trong local --> Lên VPS sẽ congif lại)

## Pipeline AI

### ASR — PhoWhisper
- Model: PhoWhisper-small chuyển CT2 int8, chạy CPU (~3-5s/câu).
- Provider tự viết: `core/providers/asr/pho_whisper_ct2.py`
- Cache model class-level (chống hết RAM `mkl_malloc failed`).
- Chống hallucination: `condition_on_previous_text=False`, `no_speech_threshold=0.6`.
- Cấu hình `language=vi` → chỉ nghe tiếng Việt (hạn chế: không nghe tiếng Anh).

### LLM — DeepSeek V4 Flash
- Model: `deepseek-v4-flash`, base_url `https://api.deepseek.com`
- Chế độ Intent: `function_call` (LLM tự gọi tool) — BẮT BUỘC để plugin hoạt động.
- max_tokens=120 (giảm ngắt quãng, câu ngắn).

### TTS — 3 lựa chọn (đánh đổi cố hữu)
| TTS | Chất lượng | Offline | Tốc độ | Ghi chú |
|---|---|---|---|---|
| EdgeTTS | Đẹp, tự nhiên | KHÔNG (cần mạng) | Nhanh | Giọng vi-VN-HoaiMy/NamMinh |
| VieNeu | Đẹp 48kHz | CÓ | Chậm ~4s/câu | 20 giọng, file provider `vieneu_local.py` |
| Piper | Ngọng | CÓ | Nhanh, nhẹ | Dự phòng, file `piper_local.py` |

**Không có TTS nào đủ cả 3: nhanh + đẹp + offline.** Muốn cả ba cần GPU (Nấc 2 VPS).

## Plugin (đã có và có thể nâng cấp mở rộng)
| Plugin | provider_code | ToolType | Nguồn dữ liệu |
|---|---|---|---|
| Thời tiết | get_weather | (cần conn) | OpenWeatherMap |
| Tin tức | get_news_from_vnexpress | | RSS VnExpress (tự viết) |
| Âm lịch | get_lunar | WAIT | cnlunar (đã ép gọi tool) |
| Phát nhạc | play_music | | file local |
| Giá vàng | get_gold_price | WAIT (KHÔNG conn) | API vang.today |
| Dịch Việt-Anh | translate_text | WAIT (KHÔNG conn) | LLM (kèm IPA) |
| Nhắc nhở | add_reminder, list_reminders, delete_reminder | SYSTEM_CTL (CÓ conn) | MySQL ai_reminder |

**Quy tắc ToolType quan trọng:**
- `ToolType.WAIT` → hàm KHÔNG có tham số `conn`.
- `ToolType.SYSTEM_CTL` → hàm CÓ `conn` (dùng lấy device_id).
- Sai → lỗi "missing/unexpected conn".

## Hệ thống nhắc nhở (3 bước)
- **Bước A** (nhớ + quản lý): bảng `ai_reminder` (11 cột), 3 plugin add/list/delete. Kết nối MySQL từ Python native qua `127.0.0.1:3306` (Docker map cổng).
- **Bước B** (tự kêu): `core/reminder_scheduler.py` — registry active_connections theo device_id, quét MySQL mỗi 30s, push qua `chat()`, mở kênh loa bằng `send_tts_message(conn, "start")` trước audio. Đã chạy: robot tự kêu đúng giờ khi online.
- **Bước C** (nhắc lặp daily/weekly): bảng có sẵn repeat_type, cần bổ sung logic tái tạo lần nhắc kế tiếp .

## Điều khiển robot (nhảy/biểu cảm)
- Tool phần cứng ở FIRMWARE (MCP), không viết plugin server được.
- Cách làm: dạy LLM qua prompt agent — ánh xạ "nhảy/vẫy tay/gật đầu" → self.robot.* tools.
- "Nhảy" của ziczac = đèn nhấp nháy + vẫy tay + lắc lư bánh xe + lắc cổ (robot bánh xe, không phải 2 chân).

---

# PHẦN IV — DOCKER & HẠ TẦNG

## 3 container (docker-compose_manager.yml)
| Container | Image | Cổng | Vai trò |
|---|---|---|---|
| -esp32-server-web | ghcr.io/.../-esp32-server:web_latest | 8002 | manager-api (Spring Boot) + web (nginx) |
| -esp32-server-db | mysql:latest | 3306 | Database |
| -esp32-server-redis | redis:8.0 | 6379 | Cache |

## Điểm quan trọng về Docker
- Web = Spring Boot (API, cổng nội bộ 8003) + nginx (tĩnh, 8002 ngoài). 502 = backend chưa sẵn sàng hoặc không nối được MySQL.
- **Thứ tự khởi động:** web phụ thuộc MySQL healthy. Nếu MySQL lên chậm, web lỗi "Connection refused" → cần restart web sau khi MySQL healthy.
- Server Python native gọi MySQL qua `127.0.0.1:3306` (cổng map ra host).
- Redis cache tham số: đổi sys_params bằng SQL phải `FLUSHALL` Redis + restart web mới có hiệu lực.

## Mount web tùy biến 
- Web tĩnh gốc nằm trong image tại `/usr/share/nginx/html`.
- Để sửa giao diện: mount `./manager-web-dist:/usr/share/nginx/html` trong compose (service web, phần volumes).
- `docker compose up -d` (KHÔNG phải restart) để áp dụng mount mới.

## Lệnh Docker hay dùng
```powershell
# Vào MySQL
docker exec -it -esp32-server-db mysql -uroot -p123456 _esp32_server

# Chạy file SQL (PowerShell không hỗ trợ <)
docker cp "x.sql" -esp32-server-db:/tmp/x.sql
docker exec -esp32-server-db sh -c "mysql -uroot -p123456 --default-character-set=utf8mb4 _esp32_server < /tmp/x.sql"

# Restart + clear cache
docker restart -esp32-server-web
docker exec -it -esp32-server-redis redis-cli FLUSHALL
docker logs --tail 20 -esp32-server-web   # chờ "Started AdminApplication"

# Backup database (LÀM ĐỊNH KỲ)
docker exec -esp32-server-db mysqldump -uroot -p123456 --default-character-set=utf8mb4 _esp32_server > backup_YYYYMMDD.sql
```

---

# PHẦN V — WEB (manager-web, Vue)

## Source & build
- Source Vue: `main/manager-web/src/` (views, components, router, apis, i18n, store, styles).
- Build: `npm install` (lần đầu) → `npm run build` → tạo `dist/`.
- Công cụ: Node.js (v22 đã có).

## Quy trình sửa giao diện (đã thông)
1. Sửa file trong `manager-web/src/` (ví dụ `i18n/vi.js` để Việt hóa).
2. `npm run build`.
3. Xóa sạch + copy dist vào `manager-web-dist` (dùng `\*`, xóa trước để không sót file cũ).
4. Hard refresh web (đã mount, không cần up -d lại).

## Bẫy thường gặp
- **Service worker cache:** web giữ bản cũ. Xóa: F12 → Application → Service Workers → Unregister, hoặc mở ẩn danh.
- **findstr KHÔNG đọc được tiếng Việt (UTF-8):** đừng tin findstr cho text tiếng Việt. Kiểm tra bằng tên file app.*.js (ASCII) hoặc mắt nhìn web.
- **Tên file js đổi hash mỗi build** — dùng để xác nhận bản mới đã vào container.

## Backend (manager-api, Java Spring Boot)
- Source: `main/manager-api/` (pom.xml + src).
- Build: `mvn clean package -Dmaven.test.skip=true` → tạo .jar.
- **YÊU CẦU Java 21** (không phải 17 — lỗi "release version 21 not supported").
- Lần đầu build tải nhiều dependency (lâu, tùy mạng).

---

# PHẦN VI — DATABASE (MySQL)

## Bảng chính
| Bảng | Vai trò |
|---|---|
| ai_agent | Agent (prompt, model, intent...) |
| ai_agent_template | Template tạo agent (5 nhân vật Việt) |
| ai_agent_plugin_mapping | Plugin nào bật cho agent (agent_id, plugin_id, param_info) |
| ai_model_provider | Định nghĩa provider (ASR/LLM/TTS/Plugin) — provider_code khớp tên file .py |
| ai_model_config | Instance cấu hình model (config_json chứa type) |
| ai_tts_voice | Danh sách giọng TTS |
| ai_reminder | Nhắc nhở (11 cột) |
| sys_params | Tham số hệ thống (server.*, register...) |
| sys_user | Người dùng |

## Nguyên tắc vàng
**`provider_code`/`type` trong database PHẢI khớp tên file .py của provider.**
Ví dụ: type `vieneu_local` → file `vieneu_local.py`. type `piper_local` → `piper_local.py`. Sai → "Loại TTS không được hỗ trợ" / provider không nạp.

## Cơ chế nạp function
- **Function hệ thống** (get_lunar, handle_exit_intent) — tự nạp, KHÔNG cần đăng ký.
- **Plugin thường** (weather, news, reminder, gold, translate) — PHẢI đăng ký `ai_model_provider` (model_type='Plugin') + thêm `ai_agent_plugin_mapping` mới nạp.
- Mỗi function 1 provider (reminder 3 function = 3 provider).

## Tham số quan trọng (sys_params) (IP có thể thay đổi nhưng nạp lại firmware cho robot
- `server.websocket` = ws://192.168.1.19:8000/nckh/v1/
- `server.ota` = http://192.168.1.19:8002/nckhsv/ota/ (CỔNG 8002!)
- `server.fronted_url` = http://192.168.1.19:8002
- `server.allow_user_register` = true (đăng ký username/password)
- `close_connection_no_voice_time` = 86400 (giữ kết nối 24h cho robot tự kêu)

---

# PHẦN VII — GIAO THỨC (Protocol)

## OTA (HTTP, cổng 8002)
- ESP32 khởi động → gọi OTA lấy config (websocket url, token...).
- Test: `curl http://127.0.0.1:8002/nckhsv/ota/` → "Giao diện OTA đang hoạt động bình thường.".
- Ghép thiết bị: ESP32 hiện mã 6 số → web nhập mã → gán device vào agent.

## WebSocket (cổng 8000)
- Kênh chính truyền âm thanh 2 chiều (audio opus 16kHz) + tin nhắn JSON.
- ESP32 gửi: hello (khai báo khả năng + MCP tools), listen (bắt đầu nghe), audio.
- Server gửi: TTS audio, tin nhắn điều khiển.

## MCP (Model Context Protocol)
- ESP32 khai báo tool phần cứng qua hello message ("công cụ được thiết bị khách hỗ trợ").
- Server nạp các tool này, LLM gọi được → điều khiển robot.
- 5 tool ziczac: led.set_mode, robot.move, robot.set_servo, robot.get_distance, robot.wave_hand.

## manager-api (đọc config)
- Server Python đọc config từ manager-api qua HTTP (secret xác thực).
- `read_config_from_api: true` → server ngừng đọc YAML, lấy hết từ database.

---

# PHẦN VIII — BẢNG TRA LỖI

| Lỗi | Nguyên nhân | Cách sửa |
|---|---|---|
| ASR ra chữ Trung/rác | FunASR không nhận tiếng Việt | Đổi PhoWhisper |
| `No audio received` | edge-tts cũ | `pip install --upgrade edge-tts` |
| Robot nói tiếng Trung | prompt_manager default 中文 | Sửa "Tiếng Việt" + prompt ép |
| OTA 404 | chưa điền server.ota / sai cổng | server.ota=8002 |
| `mkl_malloc failed` | model nạp lại mỗi kết nối | cache model class-level |
| Robot không gọi tool | prompt hẹp / intent sai | prompt đa năng + Intent_function_call |
| `Loại TTS không được hỗ trợ: X` | tên file .py ≠ type | đổi tên file khớp type |
| "Không cho phép đăng ký" | Redis cache | FLUSHALL + restart web |
| `missing conn` (plugin) | ToolType.WAIT nhưng có conn | bỏ conn (WAIT) hoặc dùng SYSTEM_CTL |
| 502 Bad Gateway | web lên trước MySQL / MySQL chưa sẵn | restart web sau khi MySQL healthy |
| findstr không thấy tiếng Việt | findstr không đọc UTF-8 | dùng tên file / mắt nhìn |
| PowerShell `<` lỗi | không hỗ trợ redirect | docker cp + sh -c "... < ..." |
| Java build "release 21" | JDK 17, source cần 21 | cài JDK 21 |
| Web sửa không đổi | mount chưa áp dụng / service worker | up -d + unregister SW |

---

# PHẦN IX — KHÓ KHĂN KHI TRIỂN KHAI

## Phần cứng
- **Máy có GPU càng tốt** chạy bằng CPU  — quá yếu cho AI GPU, mọi thứ chạy CPU → chậm. PhoWhisper ~3-5s, VieNeu ~4s/câu.
- **CPU gánh cả ASR + TTS** — nhiều người dùng đồng thời sẽ nghẽn.

## Phần mềm / tính năng
- **ASR chỉ tiếng Việt** — không nghe được tiếng Anh (chế độ dịch 2 chiều).
- **TTS đánh đổi** — không có bản nhanh+đẹp+offline (cần GPU).
- **Nhắc lặp (Bước C)**  — daily/weekly chưa tự tái tạo.
- **Nhắc offline (B1)**  — robot tắt/pin bỏ lỡ nhắc, chưa nhắc bù.
- **Gmail OAuth**  — cần build backend Java + domain HTTPS.
- **Tự kêu chỉ khi online** — robot chạy pin ngắt kết nối thì không tự kêu đúng giờ.

## Hạ tầng
- **Chạy LAN** — chỉ dùng trong nhà. Ra internet cần VPS + domain + SSL (Nấc 2).
- **IP cứng 192.168.1.19** — router đổi IP là hỏng cấu hình. Cần IP tĩnh.
- **Server Python chưa Docker hóa** —  "bê nguyên cục" .
- **Thứ tự khởi động Docker** — web hay lỗi 502 khi MySQL lên chậm.
