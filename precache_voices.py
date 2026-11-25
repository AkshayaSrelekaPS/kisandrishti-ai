"""
Pre-caches crystal-clear native speaker advisories (Tamil, Hindi, English) into data/audio_cache/
by running the real diagnostic pipeline on all preloaded sample leaves across both voice personas
so offline Raspberry Pi 5 runs play studio-quality native speech with zero network access.
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.diagnose import KisanDrishtiDiagnosticEngine

SAMPLES = [
    ("potato_late_blight.jpg", "Potato"),
    ("potato_healthy.jpg", "Potato"),
    ("rice_bacterial_blight.jpg", "Rice"),
    ("rice_brown_spot.jpg", "Rice"),
    ("tomato_early_blight.jpg", "Tomato"),
    ("corn_leaf_blight.jpg", "Corn"),
]


def precache_all_samples(speed: str = "slow"):
    engine = KisanDrishtiDiagnosticEngine(model_version="4crops", enable_audio=True, enable_llm=False)
    engine.voice_assistant.allow_online = True

    total = 0
    for fname, crop in SAMPLES:
        fpath = os.path.join(BASE_DIR, "data", "sample_leaves", fname)
        if not os.path.exists(fpath):
            continue
        for lang in ["ta", "hi", "en"]:
            for voice in ["female", "male"]:
                res = engine.diagnose(
                    fpath,
                    selected_crop=crop,
                    lang=lang,
                    voice=voice,
                    voice_speed=speed,
                )
                backend = engine.voice_assistant.last_backend
                audio_p = res.get("audio_path") or ""
                size_kb = os.path.getsize(audio_p) / 1024.0 if audio_p and os.path.exists(audio_p) else 0.0
                print(f"[{lang.upper()} | {voice:6s} | {speed}] {fname:26s} -> {backend} ({size_kb:.1f} KB)")
                total += 1
    print(f"\nPre-cached {total} native audio advisories into data/audio_cache/")


if __name__ == "__main__":
    precache_all_samples(speed="slow")
