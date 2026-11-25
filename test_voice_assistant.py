"""
End-to-End 100% Offline Two-Way Voice Assistant Test:
1. Live offline neural TTS (English, Hindi, Tamil) on uncached text via Sherpa-ONNX
2. Live offline STT (Whisper-Base INT8) -> ExecuTorch Llama 3.2 -> Live offline TTS via /api/voice-qa
3. Measures real STT, LLM, TTS latency and Process RSS memory impact.
"""
import json
import os
import sys
import time
from fastapi.testclient import TestClient

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.audio.voice_assistant import FarmerVoiceAssistant
from src.web_app import app


def run_voice_tests():
    print("=" * 70)
    print("  KisanDrishti AI: 100% Offline Two-Way Voice Assistant Test")
    print("=" * 70)

    va = FarmerVoiceAssistant(allow_online=False, speed="slow")
    samples = [
        ("en", "Custom field scan: thirty seven percent moderate blight detected."),
        ("hi", "नमस्ते किसान भाइयों, आपकी फसल में सैंतीस प्रतिशत संक्रमण पाया गया है।"),
        ("ta", "வணக்கம் விவசாயிகளே உங்கள் பயிரில் முப்பத்தி ஏழு சதவீதம் பாதிப்பு உள்ளது"),
    ]
    for lang, txt in samples:
        t0 = time.perf_counter()
        wav = va.speak(txt, lang=lang)
        ms = round((time.perf_counter() - t0) * 1000.0, 1)
        size = os.path.getsize(wav) if wav and os.path.exists(wav) else 0
        print(f"[PASS TTS {lang.upper()}] {va.last_backend} | {ms} ms | {size:,} bytes")
        assert "sherpa-onnx neural" in va.last_backend and size > 5000

    q_wav = va.speak("What organic spray should I use for potato late blight?", lang="en", speed="fast")
    client = TestClient(app)
    telem = client.get("/api/telemetry").json()
    print(f"STT Ready: {telem['stt_ready']} | Baseline RSS: {telem['telemetry']['process_rss_mb']} MB")
    assert telem["stt_ready"] is True

    ctx = json.dumps({
        "crop": "Potato",
        "disease": "late_blight",
        "severity_pct": 19.9,
        "severity_stage": "Moderate",
        "gate_b_passed": True,
        "cultural_action": "Halt overhead sprinkler irrigation immediately.",
        "organic_remedy": "Spray 5% Neem Seed Kernel Extract during early morning hours.",
        "chemical_name": "Cymoxanil 8% + Mancozeb 64% WP",
        "chemical_dosage": "2.0-2.5 g/L water",
        "phi_display": "7 days",
    })

    with open(q_wav, "rb") as f:
        r = client.post(
            "/api/voice-qa",
            data={"lang": "en", "voice": "female", "voice_speed": "slow", "context_json": ctx},
            files={"audio_file": ("question.wav", f, "audio/wav")},
        )
    d = r.json()
    print(f"[PASS VOICE Q&A] Status: {d['status']}")
    print(f"  STT Transcript ({d['stt_latency_ms']} ms): {d['transcript']!r}")
    print(f"  LLM Reply ({d['llm_metrics'].get('tokens_per_sec')} tok/s): {d['answer'][:180]!r}")
    print(f"  TTS Reply ({d['tts_latency_ms']} ms): {d['audio_backend']} -> {d['audio_url']}")
    print(f"  Total Q&A Latency: {d['total_latency_ms']} ms | RSS After STT+TTS: {d['telemetry']['process_rss_mb']} MB")

    assert d["status"] == "SUCCESS"
    assert d["transcript"]
    assert d["audio_url"]
    assert client.get(d["audio_url"]).status_code == 200
    print("=" * 70)
    print("ALL TWO-WAY OFFLINE VOICE ASSISTANT TESTS PASSED!")
    print("=" * 70)


if __name__ == "__main__":
    run_voice_tests()
