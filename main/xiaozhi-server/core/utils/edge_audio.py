"""Bounded retry; discard partial audio and keep Vietnamese fallback voices."""
import asyncio
async def synthesize_edge(text,voice,rate='+0%',volume='+0%',pitch='+0Hz',attempts=2,timeout=12):
    import edge_tts
    voices=[voice]
    if voice in ('vi-VN-HoaiMyNeural','vi-VN-NamMinhNeural'):voices.append('vi-VN-NamMinhNeural' if voice=='vi-VN-HoaiMyNeural' else 'vi-VN-HoaiMyNeural')
    error=None
    async def collect(chosen):
        data=bytearray()
        async for chunk in edge_tts.Communicate(text,voice=chosen,rate=rate,volume=volume,pitch=pitch).stream():
            if chunk['type']=='audio':data.extend(chunk['data'])
            if len(data)>12_000_000:raise ValueError('Âm thanh quá lớn')
        if not data:raise RuntimeError('EdgeTTS không trả âm thanh')
        return bytes(data)
    for index in range(max(1,min(attempts,3))):
        for chosen in voices:
            try:return await asyncio.wait_for(collect(chosen),timeout=timeout)
            except asyncio.CancelledError:raise
            except Exception as exc:error=exc
        if index+1<attempts:await asyncio.sleep(index+1)
    raise RuntimeError('EdgeTTS tạm không khả dụng; thử lại hoặc chọn TTS offline.') from error
