"""Real Piper → WAV → PhoWhisper roundtrip. No paid API; no physical device needed."""
import json
import os
os.environ.setdefault("ORT_DISABLE_TELEMETRY", "1")
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

def inside():
    import wave
    import onnxruntime
    onnxruntime.disable_telemetry_events()
    from faster_whisper import WhisperModel
    sentence = "Xin chào, đây là máy chủ robot tiếng Việt."
    request = urllib.request.Request(os.environ.get("PIPER_URL","http://piper:5100")+"/synthesize",
        data=json.dumps({"text":sentence,"voice":"vi_VN-vais1000-medium"}).encode(),
        headers={"Content-Type":"application/json", "Authorization":"Bearer "+os.environ['NCKH_SERVER_SECRET']})
    with urllib.request.urlopen(request, timeout=150) as response:
        audio = response.read(4_000_000)
    if len(audio) <= 44 or audio[:4] != b'RIFF':
        raise RuntimeError("Piper không tạo được WAV")
    print("[ĐẠT] Piper TTS:", len(audio), "byte WAV", flush=True)
    with tempfile.TemporaryDirectory() as folder:
        source, target = Path(folder)/'tts.wav', Path(folder)/'asr.wav'
        source.write_bytes(audio)
        subprocess.run(['ffmpeg','-nostdin','-y','-i',str(source),'-ar','16000','-ac','1',str(target)],
                       check=True, timeout=30, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        model = WhisperModel(os.environ.get('PHOWHISPER_MODEL_PATH','/model-store/phowhisper-small-ct2'),
                             device='cpu',compute_type='int8',cpu_threads=4,local_files_only=True)
        import numpy as np
        with wave.open(str(target),'rb') as wav:
            pcm=np.frombuffer(wav.readframes(wav.getnframes()),dtype='<i2').astype(np.float32)/32768.0
        segments, _ = model.transcribe(pcm,language='vi',beam_size=3,condition_on_previous_text=False)
        text = ' '.join(segment.text.strip() for segment in segments).strip()
        if not text:
            raise RuntimeError('PhoWhisper chưa nhận dạng được lời nói')
        print('[ĐẠT] PhoWhisper ASR:', text, flush=True)
    print('Đã thử vòng âm thanh TTS → ASR. Tiếp tục thử WebSocket/MCP và lời nhắc trong trang Kiểm thử server.', flush=True)

def main():
    if os.environ.get('NCKH_PROFILE') == 'nckh':
        inside()
        return 0
    from project import ROOT, load_env, compose_command, process_env
    load_env()
    return subprocess.run(compose_command()+['exec','-T','voice','python','/opt/selftest.py'],cwd=ROOT,env=process_env()).returncode
if __name__ == '__main__':
    raise SystemExit(main())
