from plugins_func.register import register_function, ToolType, ActionResponse, Action
from config.logger import setup_logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

handle_exit_intent_function_desc = {
    "type": "function",
    "function": {
        "name": "handle_exit_intent",
        "description": "Dùng khi người dùng muốn kết thúc cuộc trò chuyện.",
        "parameters": {
            "type": "object",
            "properties": {
                "say_goodbye": {
                    "type": "string",
                    "description": "Lời chào kết thúc bằng tiếng Việt",
                }
            },
            "required": ["say_goodbye"],
        },
    },
}


@register_function(
    "handle_exit_intent", handle_exit_intent_function_desc, ToolType.SYSTEM_CTL
)
def handle_exit_intent(conn: "ConnectionHandler", say_goodbye: str | None = None):
    # 处理退出意图
    try:
        if say_goodbye is None:
            say_goodbye = "Tạm biệt, chúc bạn một ngày vui!"
        if not conn.close_after_chat:
            conn.close_after_chat = True
        logger.bind(tag=TAG).info(f"Đã kết thúc cuộc trò chuyện:{say_goodbye}")
        return ActionResponse(
            action=Action.RESPONSE, result="Đã kết thúc cuộc trò chuyện", response=say_goodbye
        )
    except Exception as e:
        logger.bind(tag=TAG).error(f"处理退出意图错误: {e}")
        return ActionResponse(
            action=Action.NONE, result="Chưa kết thúc được cuộc trò chuyện", response=""
        )
