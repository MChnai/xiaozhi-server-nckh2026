import asyncio
from datetime import timezone
from core.reminder_scheduler import ReminderStore, VN
from plugins_func.register import register_function, ToolType, ActionResponse, Action

DESC = {"type":"function","function":{"name":"list_reminders","description":"Liệt kê các lời nhắc đang chờ của thiết bị hiện tại.","parameters":{"type":"object","properties":{}}}}

@register_function("list_reminders", DESC, ToolType.SYSTEM_CTL)
async def list_reminders(conn):
    try:
        rows = await asyncio.to_thread(ReminderStore().list, conn.device_id)
        text = "\n".join(f"{r['id']}: {r['content']} — {r['due_at'].replace(tzinfo=timezone.utc).astimezone(VN).isoformat()} ({r['repeat_type']})" for r in rows)
        return ActionResponse(Action.REQLLM, text or "Không có lời nhắc đang chờ.")
    except Exception:
        return ActionResponse(Action.REQLLM, "Không đọc được lời nhắc. Kiểm tra kết nối MySQL.")
