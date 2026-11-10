import os
import json
import httpx
from plugins_func.register import register_function, ToolType, ActionResponse, Action

DESC = {"type":"function","function":{"name":"get_weather_vn","description":"Tra thời tiết hiện tại tại một thành phố; đơn vị Celsius, trả tiếng Việt.","parameters":{"type":"object","properties":{"city":{"type":"string","description":"Tên thành phố, ví dụ Da Lat,VN"}},"required":["city"]}}}

@register_function("get_weather_vn", DESC, ToolType.WAIT)
async def get_weather_vn(city):
    key = os.environ.get("OPENWEATHER_API_KEY")
    if not key:
        return ActionResponse(Action.REQLLM, "Chưa cấu hình OPENWEATHER_API_KEY cho thời tiết; đây là khóa riêng với DeepSeek.")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get("https://api.openweathermap.org/data/2.5/weather",
                params={"q":city[:100],"appid":key,"units":"metric","lang":"vi"})
            response.raise_for_status()
        d = response.json()
        return ActionResponse(Action.REQLLM, json.dumps({"source":"OpenWeather", "city":d.get("name"),
            "temperature_c":d["main"]["temp"], "humidity_percent":d["main"]["humidity"],
            "description":d["weather"][0]["description"], "observed_at_unix":d["dt"]}, ensure_ascii=False))
    except Exception:
        return ActionResponse(Action.REQLLM, "Không lấy được thời tiết. Kiểm tra tên thành phố, khóa và kết nối mạng.")
