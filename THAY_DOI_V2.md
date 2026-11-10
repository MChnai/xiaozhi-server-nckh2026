# Thay đổi mã nguồn Server Robot AI v2

Ngày 06/11/2026. Đối chiếu trực tiếp ZIP được cung cấp và mô tả đề tài; không sửa firmware.

| Nhóm | Kết quả triển khai |
|---|---|
| Docker | Sửa PyPI/PyTorch CPU index và tách COPY khỏi RUN; công cụ chuyển model riêng; thêm Piper/VieNeu profile, cache bền vững, nhạc read-only, tăng timeout proxy |
| Web tiếng Việt | Trang Kiểm thử server: hội thoại WS, ASR tệp, TTS, plugin, MCP ảo, lịch nhắc; hiện ASR/VAD trong Vai trò; Việt hóa trợ giúp tham số và nhãn mặc định |
| Plugin | Bổ sung vàng, dịch/IPA và âm lịch Việt UTC+7; nâng nhạc local, tên có dấu và báo lỗi trung thực |
| Lời nhắc | Lặp ngày/tuần, nhắc bù, claim nguyên tử; chỉ hoàn tất khi có frame audio gửi qua WS; retry khi lỗi/ngắt/mất kết nối, theo dõi hủy khi đang gửi |
| MCP | Kiểm tra 5 tool và giới hạn tham số, ánh xạ tên đúng firmware, cleanup future khi timeout/cancel, không báo thực thi thành công khi không có phản hồi |
| Phân quyền | Chỉ tạo thiết bị/đọc lịch của tài khoản và trợ lý được phép; SQL có tham số; không gửi server secret/model key cho browser; bearer riêng cho nội bộ voice/TTS |
| Dữ liệu | Changeset mới, giữ nguyên v1; thêm mapping cho trợ lý dùng LLM_NCKH, giữ cấu hình riêng; làm mới cache liên quan |
| Vận hành | Script nâng cấp có backup và dừng khi lỗi; restore có cờ xác nhận; CLI OTA/hello/MCP/Opus và JSON report không chứa token |
| Build Java | Maven Central, JDK 21, main class rõ ràng và tạo lại JAR khi package để tránh lỗi repackage lặp |

Mã mới nằm chủ yếu ở deploy/nckh, core/api/nckh_handler.py, core/utils, core/reminder_scheduler.py, các provider TTS/plugin Việt, NckhLabController.java và ServerLab.vue. README upstream và giấy phép được giữ. Tên provider, trường JSON và MCP không dịch để giữ tương thích.

Chi tiết sử dụng trong HUONG_DAN_V2.md; tình trạng kiểm chứng trong KET_QUA_KIEM_THU_V2.md. Triển khai chức năng và nghiệm thu thực tế là hai mốc riêng; không coi mô phỏng/health check là 100% nghiệm thu robot.
