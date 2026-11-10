"""Public vang.today API; preserve source, units and observation time."""
import json
import math
import httpx
from plugins_func.register import register_function,ToolType,ActionResponse,Action
CODES={'SJL1L10','SJ9999','DOHNL','DOHCML','DOJINHTV','BTSJC','BT9999NTT','PQHNVM','PQHN24NTT','VNGSJC','VIETTINMSJC','XAUUSD'}
DESC={'type':'function','function':{'name':'get_gold_price','description':'Lấy giá vàng từ vang.today. Trong nước VND/lượng, XAUUSD USD/oz; nêu thời điểm cập nhật.','parameters':{'type':'object','properties':{'type_code':{'type':'string','enum':sorted(CODES)}},'required':['type_code']}}}

def parse_prices(payload,code):
    if payload.get('success') is not True or not isinstance(payload.get('data'),list):raise ValueError('Nguồn giá vàng trả dữ liệu không hợp lệ')
    rows=[]
    for row in payload['data']:
        if row.get('type_code')!=code:continue
        item={key:row.get(key) for key in ('type_code','buy','sell','update_time')}
        if any(isinstance(item[k],bool) or not isinstance(item[k],(int,float)) or not math.isfinite(item[k]) or item[k]<=0 for k in ('buy','sell')):raise ValueError('Nguồn chưa cung cấp giá mua/bán hợp lệ')
        item['unit']='USD/oz' if code=='XAUUSD' else 'VND/lượng';rows.append(item)
    if not rows:raise ValueError('Không có dữ liệu cho loại vàng này')
    return {'source':'https://www.vang.today/api/prices','source_time':payload.get('current_time'),'prices':rows}

@register_function('get_gold_price',DESC,ToolType.WAIT)
async def get_gold_price(type_code='SJL1L10'):
    if type_code not in CODES:return ActionResponse(Action.REQLLM,'Mã loại vàng không được hỗ trợ.')
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r=await client.get('https://www.vang.today/api/prices',params={'type':type_code});r.raise_for_status()
        if len(r.content)>2_000_000:raise ValueError('Phản hồi quá lớn')
        return ActionResponse(Action.REQLLM,json.dumps(parse_prices(r.json(),type_code),ensure_ascii=False))
    except Exception:return ActionResponse(Action.REQLLM,'Chưa lấy được giá vàng đáng tin cậy. Không suy đoán giá; thử lại sau.')
