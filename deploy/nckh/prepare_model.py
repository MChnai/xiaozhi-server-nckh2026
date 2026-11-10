"""Prepare official VinAI PhoWhisper on CPU; conversion is outside the voice image."""
import gc
import os
import shutil
import threading
import time
from pathlib import Path
from model_cache import validate_model, write_manifest, promote

def main():
    output = Path(os.environ.get("MODEL_OUTPUT", "/model-store/phowhisper-small-ct2"))
    output.parent.mkdir(parents=True, exist_ok=True)
    revision = os.environ.get("PHOWHISPER_REVISION", "main")
    try:
        validate_model(output)
        import json
        cached=json.loads((output/'nckh-model.json').read_text())
        if cached.get('revision') != revision:
            raise ValueError('Revision cache khác cấu hình')
        print("[ĐẠT] Cache PhoWhisper int8 đầy đủ và đúng SHA-256; không chuyển lại.", flush=True)
        return
    except (ValueError, OSError):
        print("Chuẩn bị PhoWhisper-small: cần Internet lần đầu (model gốc khoảng 1 GB).", flush=True)
    start = time.monotonic()
    stop = threading.Event()
    def progress():
        while not stop.wait(15):
            print(f"[MÔ HÌNH] đang tải/chuyển đổi; đã qua {int(time.monotonic()-start)} giây...", flush=True)
    thread = threading.Thread(target=progress, daemon=True)
    thread.start()
    staging = output.with_name(output.name+".building")
    try:
        if staging.exists():
            shutil.rmtree(staging)
        from ctranslate2.converters import TransformersConverter
        converter = TransformersConverter("vinai/PhoWhisper-small", revision=revision,
                    copy_files=["tokenizer.json", "preprocessor_config.json"])
        converter.convert(str(staging), quantization="int8")
        del converter
        gc.collect()
        validate_model(staging, require_manifest=False)
        # Load actual CT2 weights before accepting the cache as ready.
        from ctranslate2.models import Whisper
        model = Whisper(str(staging), device="cpu", compute_type="int8", intra_threads=2)
        del model
        write_manifest(staging, revision)
        promote(staging, output)
        print("[ĐẠT] PhoWhisper CT2 int8 đã chuyển, nạp thử và kiểm tra SHA-256.", flush=True)
    finally:
        stop.set()
        thread.join(timeout=1)
if __name__ == "__main__":
    main()
