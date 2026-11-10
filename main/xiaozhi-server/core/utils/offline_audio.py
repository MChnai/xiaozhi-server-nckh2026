"""Authenticated private TTS sidecar; accept valid nonempty PCM16 mono WAV."""
import io
import os
import wave
import httpx
async def synthesize_local(endpoint,text,voice,timeout=120):
    if not isinstance(text,str) or not 1<=len(text)<=2000:raise ValueError('Nội dung TTS phải có từ 1–2000 ký tự')
    secret=os.environ.get('NCKH_SERVER_SECRET','')
    if not secret:raise ValueError('Chưa cấu hình NCKH_SERVER_SECRET')
    async with httpx.AsyncClient(timeout=timeout,trust_env=False) as client:
        response=await client.post(endpoint.rstrip('/')+'/synthesize',headers={'Authorization':'Bearer '+secret},json={'text':text,'voice':voice});response.raise_for_status()
    audio=response.content
    if not 44<len(audio)<=12_000_000:raise ValueError('TTS offline trả âm thanh rỗng hoặc quá lớn')
    with wave.open(io.BytesIO(audio),'rb') as wav:
        if wav.getnframes()==0 or wav.getnchannels()!=1 or wav.getsampwidth()!=2:raise ValueError('TTS offline phải trả WAV PCM16 mono')
    return audio
