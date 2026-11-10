"""Private CPU TTS service. Models are cached in Docker volumes. No public port."""
import hmac
import io
import json
import os
os.environ.setdefault("ORT_DISABLE_TELEMETRY", "1")
import subprocess
import sys
import tempfile
import threading
import wave
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
class Engine:
    def __init__(self):
        self.kind=os.environ.get('TTS_ENGINE','piper');self.lock=threading.Lock()
        self.secret=os.environ.get('NCKH_SERVER_SECRET','')
        import onnxruntime
        onnxruntime.disable_telemetry_events()
        if not self.secret:raise RuntimeError('Thiếu NCKH_SERVER_SECRET')
        if self.kind=='piper':
            print('[TTS] Đang kiểm tra/tải Piper; lần đầu cần Internet.',flush=True)
            from piper import PiperVoice
            self.default='vi_VN-vais1000-medium'
            folder=Path(os.environ.get('PIPER_MODEL_DIR','/models/piper'));folder.mkdir(parents=True,exist_ok=True)
            model=folder/(self.default+'.onnx')
            if not model.is_file() or not Path(str(model)+'.json').is_file():
                if os.environ.get('HF_HUB_OFFLINE')=='1':raise RuntimeError('Chưa có model Piper trong cache')
                subprocess.run([sys.executable,'-m','piper.download_voices',self.default,'--data-dir',str(folder)],check=True,timeout=900)
            self.model=PiperVoice.load(str(model));self.voices=[('VAIS 1000',self.default)]
        elif self.kind=='vieneu':
            print('[TTS] Đang nạp VieNeu; lần đầu tải mô hình có thể mất nhiều phút.',flush=True)
            from vieneu import Vieneu
            self.default='Hải Đăng';self.model=Vieneu(backend='onnx',precision=os.environ.get('VIENEU_PRECISION','int8'))
            self.voices=self.model.list_preset_voices()
        else:raise ValueError('Engine không được hỗ trợ')
    def synthesize(self,text,voice):
        if not isinstance(text,str) or not 1<=len(text)<=2000:raise ValueError('Nội dung từ 1–2000 ký tự')
        if not isinstance(voice,str):raise ValueError('Giọng không hợp lệ')
        if not self.lock.acquire(timeout=15):raise TimeoutError('TTS đang bận')
        try:
            if self.kind=='piper':
                if voice and voice!=self.default:raise ValueError('Giọng Piper không tồn tại')
                output=io.BytesIO()
                with wave.open(output,'wb') as wav:self.model.synthesize_wav(text,wav)
                return output.getvalue()
            with tempfile.TemporaryDirectory() as folder:
                target=Path(folder)/'speech.wav';audio=self.model.infer(text,voice=voice or self.default)
                self.model.save(audio,str(target));return target.read_bytes()
        finally:self.lock.release()
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def respond(self,status,data,mime='application/json; charset=utf-8'):
        raw=json.dumps(data,ensure_ascii=False).encode() if isinstance(data,dict) else data
        self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        if self.path=='/healthz':self.respond(200,{'ready':True,'engine':self.server.engine.kind,'voices':self.server.engine.voices})
        else:self.respond(404,{'error':'Không có đường dẫn'})
    def do_POST(self):
        if self.path!='/synthesize':return self.respond(404,{'error':'Không có đường dẫn'})
        if not hmac.compare_digest(self.headers.get('Authorization',''),'Bearer '+self.server.engine.secret):return self.respond(401,{'error':'Không được phép'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=20000:return self.respond(413,{'error':'Dữ liệu quá lớn'})
            data=json.loads(self.rfile.read(length));audio=self.server.engine.synthesize(data.get('text'),data.get('voice',''))
            if not 44<len(audio)<=12_000_000:raise ValueError('Âm thanh không hợp lệ')
            self.respond(200,audio,'audio/wav')
        except (ValueError,TypeError):self.respond(400,{'error':'Nội dung hoặc giọng không hợp lệ'})
        except TimeoutError:self.respond(503,{'error':'TTS đang bận'})
        except Exception:self.respond(503,{'error':'Tổng hợp giọng nói thất bại; kiểm tra model/cache'})
if __name__=='__main__':
    engine=Engine();server=ThreadingHTTPServer(('0.0.0.0',5100),Handler);server.engine=engine
    print('TTS offline sẵn sàng:',engine.kind,flush=True);server.serve_forever()
