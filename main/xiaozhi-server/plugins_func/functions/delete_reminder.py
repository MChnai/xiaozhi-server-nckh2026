import asyncio
from core.reminder_scheduler import ReminderStore
from plugins_func.register import register_function, ToolType, ActionResponse, Action

DESC = {"type":"function","function":{"name":"delete_reminder","description":"Hủy lời nhắc của thiết bị này theo ID; dùng list_reminders để tìm ID trước.","parameters":{"type":"object","properties":{"reminder_id":{"type":"string"}},"required":["reminder_id"]}}}

@register_function("delete_reminder", DESC, ToolType.SYSTEM_CTL)
async def delete_reminder(conn, reminder_id):
    try:
        changed = await asyncio.to_thread(ReminderStore().cancel, conn.device_id, reminder_id)
        return ActionResponse(Action.REQLLM, "Đã hủy lời nhắc." if changed else "Không tìm thấy lời nhắc đang chờ trên thiết bị này.")
    except Exception:
        return ActionResponse(Action.REQLLM, "Không hủy được lời nhắc. Kiểm tra MySQL.")
