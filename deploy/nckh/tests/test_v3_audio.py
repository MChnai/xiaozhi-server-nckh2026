import asyncio
import importlib
import queue
import threading
from types import SimpleNamespace
from unittest.mock import AsyncMock

def test_manual_audio_does_not_discard_first_two_seconds(lightweight_logger,monkeypatch):
    module=importlib.import_module('core.handle.receiveAudioHandle')
    monkeypatch.setattr(module,'no_voice_close_connect',AsyncMock())
    receive=AsyncMock()
    conn=SimpleNamespace(vad=SimpleNamespace(is_vad=lambda c,pcm:True),asr=SimpleNamespace(receive_audio=receive),
        just_woken_up=True,client_listen_mode='manual',client_aec=False)
    asyncio.run(module.handleAudioMessage(conn,b'first-words'))
    receive.assert_awaited_once_with(conn,b'first-words',True)

def test_stop_waits_for_all_preceding_pcm_frames(lightweight_logger,monkeypatch):
    base=importlib.import_module('core.providers.asr.base')
    async def scenario():
        complete=asyncio.Event();captured=[]
        class Provider(base.ASRProviderBase):
            async def speech_to_text(self,*args,**kwargs):return '',None
            async def handle_voice_stop(self,conn,audio):
                captured.extend(audio);conn.stop_event.set();complete.set()
        provider=Provider()
        conn=SimpleNamespace(loop=asyncio.get_running_loop(),stop_event=threading.Event(),asr_audio_queue=queue.Queue(),asr_audio=[])
        conn.reset_audio_states=lambda:conn.asr_audio.clear()
        async def delayed_receive(c,frame):
            await asyncio.sleep(.005);c.asr_audio.append(frame)
        monkeypatch.setattr(base,'handleAudioMessage',delayed_receive)
        worker=threading.Thread(target=provider.asr_text_priority_thread,args=(conn,),daemon=True)
        worker.start()
        expected=[bytes([i])*100 for i in range(10)]
        for frame in expected:conn.asr_audio_queue.put(frame)
        conn.asr_audio_queue.put(base.MANUAL_AUDIO_STOP)
        await asyncio.wait_for(complete.wait(),2)
        await asyncio.to_thread(worker.join,1)
        assert captured==expected and not worker.is_alive()
    asyncio.run(scenario())
