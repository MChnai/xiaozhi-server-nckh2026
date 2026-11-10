"""Private workbench API. Java verifies user/agent ownership before forwarding."""
import asyncio
import os
import base64
import hmac
import json
import tempfile
import subprocess
import wave
from pathlib import Path
from types import SimpleNamespace
from aiohttp import web
from config.config_loader import merge_configs
class NckhHandler:
    def __init__(self,config,ws_server):
        self.config=config;self.ws_server=ws_server;self.limit=asyncio.Semaphore(2)
    async def online(self,request):
        secret=self.config.get('manager-api',{}).get('secret') or self.config['server'].get('auth_key','')
        if not secret or not hmac.compare_digest(request.headers.get('Authorization',''),'Bearer '+secret):
            return web.json_response({'error':'Không được phép'},status=401)
        try:
            from core.reminder_scheduler import device_key
            data=await request.json()
            if not isinstance(data,dict):raise ValueError('Object bắt buộc')
            ids=data.get('device_ids')
            if not isinstance(ids,list) or len(ids)>1000 or any(not isinstance(x,str) or len(x)>80 for x in ids):
                raise ValueError('Danh sách thiết bị không hợp lệ')
            result={}
            for value in ids:
                key=device_key(value);conn=self.ws_server.reminder_service.connections.get(key)
                result[key]={'exists':True,'isAlive':bool(conn and not conn.need_bind and conn.bind_completed_event.is_set() and not conn.stop_event.is_set()),'transport':'websocket'}
            return web.json_response(result)
        except (ValueError,TypeError):
            return web.json_response({'error':'Dữ liệu không hợp lệ'},status=400)
    async def probe(self,request):
        secret=self.config.get('manager-api',{}).get('secret') or self.config['server'].get('auth_key','')
        if not secret or not hmac.compare_digest(request.headers.get('Authorization',''),'Bearer '+secret):return web.json_response({'ok':False,'error':'Không được phép'},status=401)
        async with self.limit:
            try:
                data=await request.json();cfg=merge_configs(self.config,data.get('config',{}));cfg['reminders']=self.config.get('reminders',{})
                cfg['plugins']={k:json.loads(v) if isinstance(v,str) else v for k,v in cfg.get('plugins',{}).items()}
                kind=data.get('kind');text=data.get('text','')
                if kind=='status':
                    mode=os.environ.get('NCKH_LLM_MODE','demo')
                    llm=cfg.get('LLM',{}).get(cfg.get('selected_module',{}).get('LLM'),{})
                    conn=self.ws_server.reminder_service.connections.get(data.get('device_id'))
                    tools=list(conn.mcp_client.name_mapping.values()) if conn and conn.mcp_client else []
                    return web.json_response({'ok':True,'version':'3.0.0','mode':mode,
                        'deepseek_configured':bool(os.environ.get('DEEPSEEK_API_KEY') or llm.get('api_key')),
                        'deepseek_model':os.environ.get('DEEPSEEK_MODEL','deepseek-flash'),
                        'weather_configured':bool(os.environ.get('OPENWEATHER_API_KEY')),
                        'ready':self.ws_server.ready.is_set(),
                        'selected_module':cfg.get('selected_module',{}),
                        'simulator_online':bool(conn and not conn.stop_event.is_set()),
                        'hardware_tools':tools})
                if kind=='tts':
                    if not isinstance(text,str) or not 1<=len(text)<=2000:raise ValueError('Nội dung từ 1–2000 ký tự')
                    from core.utils.modules_initialize import initialize_tts
                    provider=await asyncio.to_thread(initialize_tts,cfg);audio=await provider.text_to_speak(text,None)
                    if not audio or len(audio)>12_000_000:raise ValueError('Không tạo được âm thanh hợp lệ')
                    return web.json_response({'ok':True,'audio_base64':base64.b64encode(audio).decode(),'mime':'audio/wav' if audio[:4]==b'RIFF' else 'audio/mpeg','bytes':len(audio)})
                if kind=='asr':
                    raw=base64.b64decode(data.get('audio_base64',''),validate=True)
                    if not raw or len(raw)>8_000_000:raise ValueError('Tệp âm thanh phải nhỏ hơn 8 MB')
                    with tempfile.TemporaryDirectory() as folder:
                        source=Path(folder)/'input.audio';target=Path(folder)/'input.wav';source.write_bytes(raw)
                        await asyncio.to_thread(subprocess.run,['ffmpeg','-nostdin','-y','-protocol_whitelist','file,pipe','-format_whitelist','wav,mp3,ogg,flac,mov,matroska,aac','-i',str(source),'-vn','-sn','-dn','-t','30','-ar','16000','-ac','1',str(target)],check=True,timeout=35,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
                        with wave.open(str(target),'rb') as f:pcm=f.readframes(f.getnframes())
                        from core.utils.modules_initialize import initialize_asr
                        provider=await asyncio.to_thread(initialize_asr,cfg);result,_=await provider.speech_to_text([],'lab',SimpleNamespace(pcm_bytes=pcm,file_path=str(target)))
                        return web.json_response({'ok':True,'text':result or '','max_seconds':30})
                if kind=='plugin':
                    from plugins_func.register import all_function_registry
                    allowed={'get_weather_vn','get_news_from_vnexpress','get_gold_price','get_lunar','translate_text','add_reminder','list_reminders','delete_reminder','play_music'}
                    name=data.get('name');args=data.get('arguments',{})
                    if name not in allowed or not isinstance(args,dict):raise ValueError('Công cụ hoặc tham số không hợp lệ')
                    item=all_function_registry.get(name)
                    if not item:raise ValueError('Plugin chưa được nạp')
                    conn=self.ws_server.reminder_service.connections.get(data.get('device_id'))
                    if item.type and item.type.code in (3,4,5):
                        if not conn or conn.need_bind:raise ValueError('Kết nối thiết bị ảo trước khi thử công cụ này')
                        values=(conn,)
                    else:values=()
                    if asyncio.iscoroutinefunction(item.func):result=await asyncio.wait_for(item.func(*values,**args),timeout=50)
                    else:result=await asyncio.wait_for(asyncio.to_thread(item.func,*values,**args),timeout=50)
                    return web.json_response({'ok':True,'result':result.result,'response':result.response,'action':result.action.name})
                if kind=='mcp':
                    conn=self.ws_server.reminder_service.connections.get(data.get('device_id'))
                    if not conn or not conn.mcp_client or not await conn.mcp_client.is_ready():raise ValueError('Thiết bị ảo chưa sẵn sàng MCP')
                    from core.providers.tools.device_mcp import call_mcp_tool
                    name=data.get('name','');args=data.get('arguments',{})
                    if not isinstance(args,dict):raise ValueError('Tham số phải là JSON object')
                    if name not in conn.mcp_client.name_mapping.values():raise ValueError('Thiết bị không công bố công cụ này')
                    sanitized=next(k for k,v in conn.mcp_client.name_mapping.items() if v==name)
                    result=await asyncio.wait_for(call_mcp_tool(conn,conn.mcp_client,sanitized,json.dumps(args),timeout=18),timeout=20)
                    return web.json_response({'ok':True,'result':result})
                raise ValueError('Phép thử không được hỗ trợ')
            except asyncio.CancelledError:raise
            except Exception as exc:
                message=str(exc) if isinstance(exc,ValueError) else 'Kiểm thử chưa thành công ('+type(exc).__name__+'). Kiểm tra cấu hình, mạng hoặc log voice.'
                return web.json_response({'ok':False,'error':message})
