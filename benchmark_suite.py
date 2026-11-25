"""
Benchmark & Clinical Validation Runner for KisanDrishti AI.
Generates real measured tables (never synthetic estimates) across the 4 crops
and prints system hardware telemetry for the current platform (Windows or Raspberry Pi 5).
"""
import os
import sys
import statistics
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.diagnose import KisanDrishtiDiagnosticEngine


def run_benchmark(iterations: int = 10):
    engine = KisanDrishtiDiagnosticEngine(model_version="4crops", enable_audio=False, enable_llm=True)

    cases = [
        ("Potato", "potato_late_blight.jpg"),
        ("Potato", "potato_healthy.jpg"),
        ("Tomato", "tomato_early_blight.jpg"),
        ("Rice", "rice_bacterial_blight.jpg"),
        ("Rice", "rice_brown_spot.jpg"),
        ("Corn", "corn_leaf_blight.jpg"),
    ]

    print("\n=== 4-CROP CLINICAL VALIDATION RESULTS (MEASURED) ===")
    print(f"{'Crop':<8} | {'Condition':<24} | {'Pathogen':<24} | {'Conf':<7} | {'Vision':<8} | {'Severity':<16} | {'Prescription'}")
    print("-" * 135)

    vision_times = []
    sev_times = []
    total_times = []

    for crop, fname in cases:
        fpath = os.path.join(BASE_DIR, "data", "sample_leaves", fname)
        if not os.path.exists(fpath):
            continue
        # Warmup
        engine.diagnose(fpath, selected_crop=crop, lang="en")
        res = None
        for _ in range(iterations):
            res = engine.diagnose(fpath, selected_crop=crop, lang="en")
            vision_times.append(res["vision_latency_ms"])
            sev_times.append(res["severity_latency_ms"])
            total_times.append(res["total_latency_ms"])

        chem_sec = next((s for s in res["prescription_card"]["sections"] if s["type"] == "chemical"), None)
        rx = f"{chem_sec['chemical_name']} @ {chem_sec['dosage']}" if chem_sec else "Cultural/Organic Only"
        print(
            f"{res['crop']:<8} | {res['disease']:<24} | {res['pathogen_scientific']:<24} | "
            f"{res['confidence']*100:5.1f}% | {res['vision_latency_ms']:5.2f} ms | "
            f"{res['severity_pct']:5.1f}% ({res['severity_stage']:<4}) | {rx}"
        )

    telem = engine.telemetry.snapshot()
    print("\n=== MEASURED SYSTEM METRICS ===")
    print(f"Platform:               {telem['platform']}")
    print(f"Vision Backend:         {engine.backend}")
    print(f"LLM Backend:            {engine.agronomist.backend_name}")
    print(f"Mean Vision Latency:    {statistics.mean(vision_times):.2f} ms")
    print(f"Mean Severity Latency:  {statistics.mean(sev_times):.2f} ms")
    print(f"Mean End-to-End (noTTS):{statistics.mean(total_times):.2f} ms")
    print(f"Process RSS RAM:        {telem['process_rss_mb']} MB")
    print(f"CPU Freq / SoC Temp:    {telem['cpu_freq_mhz']} MHz / {telem['soc_temp_c']} C")


if __name__ == "__main__":
    run_benchmark()
