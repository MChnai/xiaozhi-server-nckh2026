"""Vietnam calendar context; no Chinese calendar package or external service."""
from datetime import datetime
from zoneinfo import ZoneInfo
from core.utils.lunar_vn import solar_to_lunar
VN = ZoneInfo("Asia/Ho_Chi_Minh")
WEEKDAYS = ("Thứ hai", "Thứ ba", "Thứ tư", "Thứ năm", "Thứ sáu", "Thứ bảy", "Chủ nhật")
def get_current_time(): return datetime.now(VN).strftime("%H:%M")
def get_current_date(): return datetime.now(VN).strftime("%Y-%m-%d")
def get_current_weekday(): return WEEKDAYS[datetime.now(VN).weekday()]
def get_current_lunar_date():
    lunar = solar_to_lunar(datetime.now(VN).date())
    return f"{lunar['day']}/{lunar['month']}{' nhuận' if lunar['leap_month'] else ''}, năm {lunar['year_name']}"
def get_current_time_info():
    return get_current_time(), get_current_date(), get_current_weekday(), get_current_lunar_date()
