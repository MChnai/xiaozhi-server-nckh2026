"""PhoWhisper CT2: shared CPU int8 model, input is decoded PCM16 mono 16 kHz."""
import asyncio
import os
os.environ.setdefault("ORT_DISABLE_TELEMETRY", "1")
import threading
import numpy as np
from .base import ASRProviderBase
from .dto.dto import InterfaceType


class ASRProvider(ASRProviderBase):
    _models = {}
    _cache_lock = threading.Lock()

    def __init__(self, config, delete_audio_file=True):
        super().__init__()
        self.interface_type = InterfaceType.LOCAL
        self.delete_audio_file = delete_audio_file
        self.output_dir = config.get("output_dir", "tmp/")
        os.makedirs(self.output_dir, exist_ok=True)
        self.language = config.get("language", "vi")
        path = os.environ.get("PHOWHISPER_MODEL_PATH") or config.get("model_path", "models/phowhisper-small-ct2")
        if not os.path.isfile(os.path.join(path, "model.bin")):
            raise FileNotFoundError("Chưa có PhoWhisper CT2. Chạy lệnh chuẩn bị model trong HUONG_DAN_VI.md.")
        key = (os.path.abspath(path), int(config.get("cpu_threads", 4)))
        with self._cache_lock:
            if key not in self._models:
                import onnxruntime
                onnxruntime.disable_telemetry_events()
                from faster_whisper import WhisperModel
                self._models[key] = (WhisperModel(path, device="cpu", compute_type="int8",
                                                 cpu_threads=key[1], local_files_only=True), threading.Lock())
            self.model, self._inference_lock = self._models[key]

    def _transcribe(self, pcm):
        if len(pcm) % 2:
            raise ValueError("PCM16 phải có số byte chẵn")
        audio = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0
        if audio.size < 1600 or float(np.max(np.abs(audio))) < 0.001:
            return ""
        # The segment iterator performs inference lazily; consume under the lock.
        with self._inference_lock:
            segments, _ = self.model.transcribe(audio, language=self.language, beam_size=3,
                condition_on_previous_text=False, no_speech_threshold=0.6, vad_filter=False)
            return " ".join(s.text.strip() for s in segments if s.no_speech_prob < 0.6).strip()

    async def speech_to_text(self, opus_data, session_id, artifacts=None):
        if artifacts is None or not artifacts.pcm_bytes:
            return "", None
        text = await asyncio.to_thread(self._transcribe, artifacts.pcm_bytes)
        return text, artifacts.file_path
