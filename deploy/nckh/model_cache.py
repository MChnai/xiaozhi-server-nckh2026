"""Portable validation/atomic promotion of a converted PhoWhisper model."""
import hashlib
import json
import shutil
from pathlib import Path

REQUIRED = ("model.bin", "config.json", "tokenizer.json", "preprocessor_config.json", "vocabulary.json")

def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024*1024), b""):
            value.update(block)
    return value.hexdigest()

def validate_model(folder, require_manifest=True):
    folder = Path(folder)
    for name in REQUIRED:
        path = folder/name
        if not path.is_file() or path.stat().st_size <= 0:
            raise ValueError("Thiếu tệp mô hình: "+name)
        if name.endswith('.json'):
            json.loads(path.read_text(encoding="utf-8"))
    if (folder/"model.bin").stat().st_size < 1_000_000:
        raise ValueError("model.bin quá nhỏ, có thể tải chưa hoàn tất")
    if require_manifest:
        manifest = json.loads((folder/"nckh-model.json").read_text(encoding="utf-8"))
        for name in REQUIRED:
            expected = manifest.get("sha256", {}).get(name)
            if not expected or digest(folder/name) != expected:
                raise ValueError("Tệp mô hình hỏng hoặc đã thay đổi: "+name)
    return True

def write_manifest(folder, revision):
    manifest = {"source": "vinai/PhoWhisper-small", "revision": revision,
                "quantization": "int8", "sha256": {name: digest(folder/name) for name in REQUIRED}}
    (folder/"nckh-model.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

def promote(staging, destination):
    staging, destination = Path(staging), Path(destination)
    validate_model(staging)
    backup = destination.with_name(destination.name+".previous")
    if backup.exists():
        shutil.rmtree(backup)
    if destination.exists():
        destination.rename(backup)
    try:
        staging.rename(destination)
    except BaseException:
        if backup.exists() and not destination.exists():
            backup.rename(destination)
        raise
    if backup.exists():
        shutil.rmtree(backup)
