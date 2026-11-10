> Tài liệu v1. Dùng HUONG_DAN_V2.md, THAY_DOI_V2.md và KET_QUA_KIEM_THU_V2.md cho bản hiện tại.

# Kết quả kiểm thử bàn giao — 04/11/2026

| Kiểm tra | Kết quả | Giới hạn |
|---|---|---|
| Vue production build | Đạt | Workaround card mạng chỉ trong môi trường kiểm thử, không đưa vào source |
| Đồng bộ i18n | Đạt, 1546 khóa × 6 ngôn ngữ | Không xác nhận mọi nhãn dữ liệu upstream đã được dịch |
| Frontend contract | 10/10 đạt | Bộ test sẵn có |
| Frontend snapshot | 13/13 đạt | Bộ test sẵn có |
| Frontend unit | 70/70 đạt | Bộ test sẵn có |
| NCKH Python unit/contracts | 23/23 đạt | Mock cloud, model inference và MySQL |
| Python compileall | Đạt | Không thay thế kiểm thử runtime toàn pipeline |
| SQL NCKH parse MySQL | Đạt, 26 câu lệnh | Chưa thực thi trên MySQL |
| Dependency metadata trực tiếp | Tìm được các phiên bản yêu cầu | Không thay thế build image hoặc resolver đầy đủ theo Python 3.10 |
| Build JAR Java 21 | Chưa chạy | Môi trường chỉ có Java 17 |
| Build/chạy Docker toàn bộ | Chưa chạy | Không có Docker daemon |
| PhoWhisper model thật | Chưa chạy | Không tải model; unit test kiểm tra cache, PCM, tham số và loại bỏ segment no-speech |
| DeepSeek, EdgeTTS, OpenWeather, RSS live | Chưa chạy | Không gọi dịch vụ thật trong bộ test |
| ESP32/MCP thật | Chưa chạy | Không có firmware và robot để xác minh |

Các ca NCKH bao gồm: giờ Việt Nam và UTC, từ chối lịch quá khứ, lặp daily/weekly và nhắc bù, SQL tham số theo thiết bị, validation đầu vào, offline/busy, reconnect, phát tts/start trước hàng đợi FIRST/TEXT/LAST, thử lại khi queue lỗi, trì hoãn khi người dùng nói trong lúc truy cập DB, demo không tạo cloud client, thiếu API key, RSS UTF-8, schema plugin có/không có conn, thời tiết dạng chuỗi hợp lệ cho tool history, model ASR dùng chung và PCM16, compose, đường dẫn migration và setup không ghi đè cấu hình.

Lệnh chạy lại:

```powershell
python -m pip install pytest PyYAML httpx loguru numpy
python -m pytest deploy/nckh/tests -q
```

Tại `main/manager-web` sau khi cài Node/npm dependencies:

```powershell
npm ci
npm run check:i18n
npm run test:contract
npm run test:snapshot
npm run test:unit
npm run build
```

Các ca cần thực hiện trên máy thật nằm trong mục 9 của HUONG_DAN_VI.md. Không kết luận đã nghiệm thu end-to-end từ kết quả kiểm thử này.
