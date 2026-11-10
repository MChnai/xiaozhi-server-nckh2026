from pathlib import Path
from core.providers.tts.base import TTSProviderBase
from core.utils.offline_audio import synthesize_local
class TTSProvider(TTSProviderBase):
    def __init__(self,config,delete_audio_file):
        super().__init__(config,delete_audio_file)
        self.endpoint=config.get('endpoint','http://vieneu:5100')
        self.voice=config.get('private_voice') or config.get('voice','Hải Đăng')
        self.audio_file_type='wav'
        self.tts_timeout=float(config.get('tts_timeout',150))
        self.retry_attempts=1
    async def text_to_speak(self,text,output_file):
        audio=await synthesize_local(self.endpoint,text,self.voice,timeout=min(self.tts_timeout,120))
        if output_file:
            Path(output_file).parent.mkdir(parents=True,exist_ok=True);Path(output_file).write_bytes(audio)
        else:return audio
