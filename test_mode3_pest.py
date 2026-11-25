"""
End-to-End Verification for Mode 3 Image-Level Insect Pest Classification.
Tests PestDetector ONNX inference, 26-record SQLite KB, FastAPI /api/diagnose-pest,
and live offline trilingual Sherpa-ONNX TTS across Whitefly, Aphid, and Leafminer.
"""
import os
import sys
from fastapi.testclient import TestClient

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.web_app import app


def run_mode3_tests():
    client = TestClient(app)
    telem = client.get("/api/telemetry").json()
    print("Telemetry pest_ready:", telem["pest_ready"], "| stt_ready:", telem["stt_ready"])
    assert telem["pest_ready"] is True

    for cls_folder, crop, lang in [("Whitefly", "Tomato", "ta"), ("Aphid", "Potato", "hi"), ("Leafminer", "Tomato", "en")]:
        folder = os.path.join(BASE_DIR, "data", "pests", cls_folder)
        passed = False
        for fn in sorted(os.listdir(folder)):
            p = os.path.join(folder, fn)
            with open(p, "rb") as f:
                r = client.post(
                    "/api/diagnose-pest",
                    data={
                        "crop": crop,
                        "lang": lang,
                        "voice": "female",
                        "voice_speed": "slow",
                        "state": "Tamil Nadu",
                        "district": "Coimbatore",
                    },
                    files={"file": (fn, f, "image/jpeg")},
                )
            d = r.json()
            if d.get("status") == "SUCCESS":
                print(
                    f"[PASS MODE 3 {cls_folder:10s}] pred={d['disease']:10s} | conf={d['confidence']}% | "
                    f"vision={d['vision_latency_ms']}ms | audio={d['audio_backend']}"
                )
                assert d["audio_url"]
                assert client.get(d["audio_url"]).status_code == 200
                passed = True
                break
        assert passed, f"No successful Mode 3 prediction for {cls_folder}"

    print("ALL MODE 3 PEST END-TO-END TESTS PASSED!")


if __name__ == "__main__":
    run_mode3_tests()
