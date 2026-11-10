from datetime import datetime
from zoneinfo import ZoneInfo
import json
from core.utils.lunar_vn import solar_to_lunar
from plugins_func.register import register_function,ToolType,ActionResponse,Action
DESC={'type':'function','function':{'name':'get_lunar','description':'Đổi ngày dương lịch sang âm lịch Việt Nam UTC+7, có tháng nhuận.','parameters':{'type':'object','properties':{'date':{'type':'string','description':'YYYY-MM-DD; bỏ trống để lấy hôm nay ở Việt Nam'}}}}}
@register_function('get_lunar',DESC,ToolType.WAIT)
def get_lunar(date=None):
    try:return ActionResponse(Action.REQLLM,json.dumps(solar_to_lunar(date or datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).date()),ensure_ascii=False))
    except (ValueError,TypeError) as exc:return ActionResponse(Action.REQLLM,str(exc))
