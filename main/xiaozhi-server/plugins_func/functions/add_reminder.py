import asyncio
from core.reminder_scheduler import ReminderStore, parse_due
from plugins_func.register import register_function, ToolType, ActionResponse, Action

DESC = {"type":"function","function":{"name":"add_reminder",
    "description":"Tạo lời nhắc cho thiết bị này. Hỏi lại nếu chưa rõ ngày giờ; giờ mặc định Việt Nam.",
    "parameters":{"type":"object","properties":{
        "content":{"type":"string","description":"Nội dung cần nhắc"},
        "due_at":{"type":"string","description":"ISO 8601, ví dụ 2026-11-05T07:30:00+07:00"},
        "repeat_type":{"type":"string","enum":["none","daily","weekly"]}},"required":["content","due_at"]}}}

@register_function("add_reminder", DESC, ToolType.SYSTEM_CTL)
async def add_reminder(conn, content, due_at, repeat_type="none"):
    if not conn.config.get("reminders", {}).get("enabled", False):
        return ActionResponse(Action.REQLLM, "Chức năng nhắc nhở chưa được bật.")
    try:
        due = parse_due(due_at)
        rid = await asyncio.to_thread(ReminderStore().add, conn.device_id, content, due, repeat_type)
        return ActionResponse(Action.REQLLM, f"Đã lưu lời nhắc {rid}, lúc {due_at}, lặp {repeat_type}. Robot cần online; khi offline sẽ nhắc bù sau kết nối.")
    except ValueError as e:
        return ActionResponse(Action.REQLLM, str(e))
    except Exception:
        return ActionResponse(Action.REQLLM, "Không lưu được lời nhắc. Kiểm tra MySQL và cấu hình bộ nhắc nhở.")
