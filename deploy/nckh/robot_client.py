"""Firmware-compatible virtual device. Use the voice container for libopus/ffmpeg.
The JSON report contains no bearer token. Simulated hardware cannot prove GPIO behavior.
"""
import argparse
import asyncio
import json
import re
import subprocess
import uuid
import wave
from pathlib import Path
from urllib.request import Request,urlopen
import websockets
CHOICES={
 'self.led.set_mode':{'led':['left','right','both'],'mode':['off','on','blink_slow','blink_fast','breathe']},
 'self.robot.move':{'direction':['forward','backward','left','right','stop'],'duration_ms':(0,2000)},
 'self.robot.set_servo':{'part':['neck','arm_left','arm_right'],'angle':(0,180)},
 'self.robot.get_distance':{},'self.robot.wave_hand':{'which':['left','right','both'],'times':(1,10)}}
def tools():
    result=[]
    for name,fields in CHOICES.items():
        props={k:({'type':'integer','minimum':v[0],'maximum':v[1]} if isinstance(v,tuple) else {'type':'string','enum':v}) for k,v in fields.items()}
        result.append({'name':name,'description':'[MÔ PHỎNG] '+name,'inputSchema':{'type':'object','properties':props,'required':list(props),'additionalProperties':False}})
    return result

def mcp_reply(payload,distance=100):
    if 'id' not in payload:return None
    try:
        method=payload.get('method')
        if method=='initialize':result={'protocolVersion':'2024-11-05','capabilities':{'tools':{}},'serverInfo':{'name':'RobotVietCLI','version':'3.0.0'}}
        elif method=='tools/list':result={'tools':tools()}
        elif method=='tools/call':
            params=payload['params'];name=params['name'];args=params.get('arguments',{});fields=CHOICES[name]
            if not isinstance(args,dict) or set(args)!=set(fields):raise ValueError('Thiếu hoặc thừa tham số')
            for key,spec in fields.items():
                value=args[key]
                if isinstance(spec,tuple):
                    if type(value)!=int or not spec[0]<=value<=spec[1]:raise ValueError('Giá trị ngoài giới hạn')
                elif value not in spec:raise ValueError('Giá trị không hợp lệ')
            data={'simulated':True,'tool':name,'arguments':args};data.update({'distance_cm':distance} if name=='self.robot.get_distance' else {'success':True})
            result={'content':[{'type':'text','text':json.dumps(data,ensure_ascii=False)}],'isError':False}
        else:return {'jsonrpc':'2.0','id':payload['id'],'error':{'code':-32601,'message':'Phương thức không được hỗ trợ'}}
        return {'jsonrpc':'2.0','id':payload['id'],'result':result}
    except (KeyError,ValueError,TypeError):return {'jsonrpc':'2.0','id':payload['id'],'error':{'code':-32602,'message':'Công cụ hoặc tham số không hợp lệ'}}

def ota(url,device,client):
    body={'version':2,'application':{'name':'nckh-simulator','version':'3.0.0'},'board':{'type':'nckh-simulator','name':'Robot Việt giả lập'}}
    request=Request(url,data=json.dumps(body).encode(),headers={'Content-Type':'application/json','Device-Id':device,'Client-Id':client},method='POST')
    with urlopen(request,timeout=15) as response:return json.load(response)

def encode_wav(filename):
    import opuslib_next
    raw=subprocess.run(['ffmpeg','-nostdin','-v','error','-i',filename,'-t','30','-f','s16le','-ar','16000','-ac','1','pipe:1'],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=35).stdout
    if len(raw)<3200:raise ValueError('Tệp quá ngắn để thử ASR')
    encoder=opuslib_next.Encoder(16000,1,opuslib_next.APPLICATION_AUDIO)
    return [encoder.encode(raw[i:i+1920].ljust(1920,b'\0'),960) for i in range(0,len(raw),1920)]

def save_audio(frames,filename):
    import opuslib_next
    decoder=opuslib_next.Decoder(16000,1);target=Path(filename);target.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(target),'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000)
        for frame in frames:f.writeframes(decoder.decode(frame,960))

async def exercise(args):
    client=uuid.uuid4().hex
    cfg=await asyncio.to_thread(ota,args.ota_url or 'http://'+args.host+':8002/nckhsv/ota/',args.device_id,client)
    if cfg.get('activation'):raise ValueError('Thiết bị chưa liên kết. Trong web chọn trợ lý > Thiết bị > Thêm, nhập mã '+str(cfg['activation'].get('code',''))+', rồi chạy lại.')
    ws_cfg=cfg.get('websocket',{});endpoint=args.ws_url or ws_cfg.get('url')
    if not endpoint:raise ValueError('OTA chưa trả địa chỉ WebSocket')
    headers={'Device-Id':args.device_id,'Client-Id':client,'Authorization':'Bearer '+ws_cfg.get('token','')}
    hello=asyncio.Event();ready=asyncio.Event();done=asyncio.Event();frames=[]
    report={'simulated_hardware':True,'device_id':args.device_id,'ota':True,'hello':False,'mcp_ready':False,'mcp_calls':[],'stt':[],'reply':[],'input_audio_frames':0}
    async with websockets.connect(endpoint,additional_headers=headers,max_size=4*1024*1024,open_timeout=15) as ws:
        async def receive():
            async for raw in ws:
                if isinstance(raw,bytes):frames.append(raw);continue
                message=json.loads(raw);kind=message.get('type')
                if kind=='hello':report['hello']=True;hello.set()
                elif kind=='mcp':
                    payload=message['payload'];reply=mcp_reply(payload,args.distance)
                    if reply:
                        await ws.send(json.dumps({'type':'mcp','payload':reply},ensure_ascii=False))
                        if payload.get('method')=='tools/list':report['mcp_ready']=True;ready.set()
                        if payload.get('method')=='tools/call':report['mcp_calls'].append({'name':payload.get('params',{}).get('name'),'ok':'error' not in reply})
                elif kind=='stt':report['stt'].append(message.get('text',''))
                elif kind=='tts':
                    if message.get('text'):report['reply'].append(message['text'])
                    if message.get('state')=='stop':done.set()
        task=asyncio.create_task(receive())
        try:
            await ws.send(json.dumps({'type':'hello','version':1,'transport':'websocket','features':{'mcp':True},'audio_params':{'format':'opus','sample_rate':16000,'channels':1,'frame_duration':60}}))
            await asyncio.wait_for(hello.wait(),args.timeout);await asyncio.wait_for(ready.wait(),args.timeout);await asyncio.sleep(2)
            if args.wav:
                encoded=await asyncio.to_thread(encode_wav,args.wav)
                await ws.send(json.dumps({'type':'listen','state':'start','mode':'manual'}))
                for frame in encoded:await ws.send(frame);await asyncio.sleep(.06)
                await asyncio.sleep(.2);await ws.send(json.dumps({'type':'listen','state':'stop'}));report['input_audio_frames']=len(encoded)
            elif args.text:await ws.send(json.dumps({'type':'listen','state':'detect','text':args.text},ensure_ascii=False))
            if args.wav or args.text:
                await asyncio.wait_for(done.wait(),args.timeout)
                if not frames:raise ValueError('Đã nhận tts/stop nhưng không có âm thanh trả về')
                if args.wav and not any(report['stt']):raise ValueError('ASR không nhận dạng được lời nói')
            if args.stay_seconds:await asyncio.sleep(args.stay_seconds)
            if args.output and frames:await asyncio.to_thread(save_audio,frames,args.output)
            report['output_audio_frames']=len(frames);report['passed']=True
            report['scope']='OTA + hello + MCP'+(' + ASR/LLM/TTS' if args.wav else ' + text/LLM/TTS' if args.text else '')
            return report
        finally:
            task.cancel()
            try:await task
            except asyncio.CancelledError:pass

def main():
    p=argparse.ArgumentParser(description='Thiết bị robot giả lập để kiểm thử server')
    p.add_argument('--host',default='127.0.0.1');p.add_argument('--device-id',default='02:00:00:00:00:01');p.add_argument('--ota-url');p.add_argument('--ws-url');p.add_argument('--timeout',type=int,default=150)
    group=p.add_mutually_exclusive_group();group.add_argument('--text');group.add_argument('--wav')
    p.add_argument('--distance',type=int,default=100);p.add_argument('--stay-seconds',type=int,default=0);p.add_argument('--output',help='WAV trả lời; cần libopus, nên chạy trong container voice');p.add_argument('--report',default='robot-test-report.json');args=p.parse_args()
    if not re.fullmatch(r'(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}',args.device_id):p.error('MAC không hợp lệ')
    if not 0<=args.distance<=500 or not 0<=args.stay_seconds<=3600:p.error('Khoảng cách 0–500, thời gian giữ kết nối 0–3600 giây')
    try:report=asyncio.run(asyncio.wait_for(exercise(args),timeout=args.timeout*3+args.stay_seconds))
    except Exception as exc:report={'passed':False,'error':str(exc) if isinstance(exc,ValueError) else type(exc).__name__,'simulated_hardware':True}
    Path(args.report).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2));return 0 if report['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
