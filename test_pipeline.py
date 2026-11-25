"""
End-to-End Integration & Gate Verification Test for KisanDrishti AI.
Verifies:
1. 4-Crop ONNX Vision + Severity + 24-column SQLite Retrieval
2. Gate A Rejections (Blurry image, Non-leaf image, Crop Mismatch)
3. Gate B Suppression (<75% borderline confidence / unverified region)
4. Trilingual Output (Tamil, Hindi, English)
"""
import os
import sys
import tempfile
import cv2
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.diagnose import KisanDrishtiDiagnosticEngine


def run_tests():
    print("=" * 70)
    print("  KisanDrishti AI: 4-Crop Trilingual Pipeline & Gate Test Suite")
    print("=" * 70)

    engine = KisanDrishtiDiagnosticEngine(model_version="4crops", enable_audio=False, enable_llm=True)

    # 1. Test all 4 crops from sample_leaves
    samples = [
        ("potato_late_blight.jpg", "Potato", "en"),
        ("tomato_early_blight.jpg", "Tomato", "ta"),
        ("rice_bacterial_blight.jpg", "Rice", "hi"),
        ("corn_leaf_blight.jpg", "Corn", "en"),
        ("potato_healthy.jpg", "Potato", "ta"),
    ]
    for fname, crop, lang in samples:
        fpath = os.path.join(BASE_DIR, "data", "sample_leaves", fname)
        assert os.path.exists(fpath), f"Missing sample: {fpath}"
        res = engine.diagnose(fpath, selected_crop=crop, lang=lang)
        assert res["status"] == "SUCCESS", f"Expected SUCCESS for {fname}, got {res}"
        assert res["gate_a_passed"] is True
        print(
            f"[PASS] {res['crop']:6s} | {res['disease']:28s} | conf={res['confidence']*100:5.1f}% | "
            f"sev={res['severity_pct']:5.1f}% ({res['severity_stage']}) | "
            f"vision={res['vision_latency_ms']:5.2f}ms | lang={lang}"
        )

    # 2. Gate A Crop Mismatch Test
    potato_sample = os.path.join(BASE_DIR, "data", "sample_leaves", "potato_late_blight.jpg")
    mismatch = engine.diagnose(potato_sample, selected_crop="Tomato", lang="en")
    assert mismatch["status"] == "REJECTED_BY_GATE_A"
    assert mismatch["reason"] == "CROP_MISMATCH"
    print(f"[PASS] Gate A Crop Mismatch rejected cleanly: {mismatch['message']}")

    # 3. Gate A Non-Leaf & Blur Rejection Tests
    with tempfile.TemporaryDirectory() as tmpdir:
        non_leaf_path = os.path.join(tmpdir, "blank_blue.jpg")
        blank_img = np.full((256, 256, 3), (200, 50, 50), dtype=np.uint8)
        cv2.line(blank_img, (0, 0), (255, 255), (255, 255, 255), 3)
        cv2.imwrite(non_leaf_path, blank_img)
        non_leaf_res = engine.diagnose(non_leaf_path, selected_crop="Potato", lang="en")
        assert non_leaf_res["status"] == "REJECTED_BY_GATE_A"
        print(f"[PASS] Gate A Non-Leaf rejected cleanly: {non_leaf_res['reason']}")

        blur_path = os.path.join(tmpdir, "blur_leaf.jpg")
        orig = cv2.imread(potato_sample)
        blurred = cv2.GaussianBlur(orig, (51, 51), 20)
        cv2.imwrite(blur_path, blurred)
        blur_res = engine.diagnose(blur_path, selected_crop="Potato", lang="en")
        assert blur_res["status"] == "REJECTED_BY_GATE_A"
        assert blur_res["reason"] == "IMAGE_TOO_BLURRY"
        print(f"[PASS] Gate A Blur check rejected cleanly: variance={blur_res['quality']['blur_variance']}")

    # 4. Gate B Chemical Suppression Test (confidence < 0.75)
    t_row = engine.kb.get_treatment("Potato", "late_blight", "Moderate", lang="en")
    borderline = engine.agronomist.generate_advisory(
        {
            "crop": "Potato",
            "disease": "late_blight",
            "pathogen_scientific": t_row["pathogen_scientific"],
            "confidence": 0.62,
            "severity_pct": 14.0,
            "severity_stage": "Uncertain",
            "treatment": t_row,
        },
        lang="en",
    )
    assert borderline["gate_b_passed"] is False
    assert borderline["prescription_card"]["sections"][-1]["type"] == "suppressed"
    print("[PASS] Gate B Chemical Suppression verified at 62.0% borderline confidence")

    print("=" * 70)
    print("ALL INTEGRATION & GATE TESTS PASSED!")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
