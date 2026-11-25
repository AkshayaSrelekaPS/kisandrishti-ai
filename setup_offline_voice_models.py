#!/usr/bin/env python3
"""
Downloads 100% offline neural speech models for KisanDrishti AI:
- TTS (English): vits-piper-en_US-lessac-medium-int8 (Sherpa-ONNX) -> models/tts/en/
- TTS (Hindi):   vits-piper-hi_IN-priyamvada-medium-int8 (Sherpa-ONNX) -> models/tts/hi/
- TTS (Tamil):   codebucketsolutions/bolo-mms-tts-tamil (MMS VITS ONNX) -> models/tts/ta/
- STT (Ta/Hi/En): csukuangfj/sherpa-onnx-whisper-base (INT8 ONNX) -> models/stt/whisper-base/
"""
import os
import shutil
import sys
import tarfile
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TTS_DIR = os.path.join(BASE_DIR, "models", "tts")
STT_DIR = os.path.join(BASE_DIR, "models", "stt", "whisper-base")
TEMP_DIR = os.path.join(BASE_DIR, "temp_download")


def download_file(url: str, dst: str):
    if os.path.exists(dst) and os.path.getsize(dst) > 0:
        print(f"  [SKIP] {os.path.basename(dst)} already exists")
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    tmp = dst + ".part"
    print(f"  [GET]  {url}")
    with requests.get(url, stream=True, timeout=180) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
    os.replace(tmp, dst)


def install_piper_tar_bz2(archive_name: str, target_lang_dir: str):
    out_dir = os.path.join(TTS_DIR, target_lang_dir)
    if os.path.isdir(out_dir) and any(f.endswith(".onnx") for f in os.listdir(out_dir)):
        print(f"[SKIP] TTS ({target_lang_dir}) already installed at {out_dir}")
        return

    os.makedirs(TEMP_DIR, exist_ok=True)
    url = f"https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/{archive_name}"
    arc_path = os.path.join(TEMP_DIR, archive_name)
    download_file(url, arc_path)

    print(f"  [EXTRACT] {archive_name} -> {out_dir}")
    with tarfile.open(arc_path, "r:bz2") as tar:
        tar.extractall(TEMP_DIR)

    extracted_folder = os.path.join(TEMP_DIR, archive_name.replace(".tar.bz2", ""))
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    shutil.move(extracted_folder, out_dir)
    os.remove(arc_path)


def install_tamil_mms_tts():
    out_dir = os.path.join(TTS_DIR, "ta")
    model_dst = os.path.join(out_dir, "model.onnx")
    tokens_dst = os.path.join(out_dir, "tokens.txt")
    if os.path.exists(model_dst) and os.path.exists(tokens_dst):
        print(f"[SKIP] TTS (ta) already installed at {out_dir}")
        return

    os.makedirs(out_dir, exist_ok=True)
    base_url = "https://huggingface.co/codebucketsolutions/bolo-mms-tts-tamil/resolve/main"
    for fname in ["model.onnx", "tokens.txt", "voice.json"]:
        download_file(f"{base_url}/{fname}", os.path.join(out_dir, fname))


def install_whisper_base_int8():
    os.makedirs(STT_DIR, exist_ok=True)
    base_url = "https://huggingface.co/csukuangfj/sherpa-onnx-whisper-base/resolve/main"
    for fname in ["base-encoder.int8.onnx", "base-decoder.int8.onnx", "base-tokens.txt"]:
        download_file(f"{base_url}/{fname}", os.path.join(STT_DIR, fname))


if __name__ == "__main__":
    print("=== 1. Installing Offline Neural TTS Models (en, hi, ta) ===")
    install_piper_tar_bz2("vits-piper-en_US-lessac-medium-int8.tar.bz2", "en")
    install_piper_tar_bz2("vits-piper-hi_IN-priyamvada-medium-int8.tar.bz2", "hi")
    install_tamil_mms_tts()

    print("\n=== 2. Installing Offline Multilingual Whisper-Base INT8 STT ===")
    install_whisper_base_int8()

    shutil.rmtree(TEMP_DIR, ignore_errors=True)
    print("\nALL OFFLINE VOICE MODELS INSTALLED!")
