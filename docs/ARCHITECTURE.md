# KisanDrishti AI — Architecture, Optimization & Hardware Utilization

## 1. End-to-End Methodology

KisanDrishti AI combines three defensive layers to eliminate field false positives and dosage hallucinations while operating completely offline on Arm edge hardware:

1. **Gate A — Pre-Inference Clinical Input Filter (`src/diagnose.py`):**
   - Computes Laplacian variance to reject motion-blurred captures (`< 20.0`).
   - Evaluates HSV green/yellow/brown foliage ratio (`< 0.08`) to block non-plant objects.
   - Cross-checks top-1 crop class prefix against the farmer's selected crop (`Potato`, `Tomato`, `Rice`, `Corn`), attaining **99.94% crop-level gating accuracy** (`models/evaluation_report_20classes.json`).
2. **Dual Vision Classification & Severity Quantification:**
   - **Mode 1 (`mobilenetv3_4crops_standalone.onnx`, 6.12 MB):** 20-class `MobileNetV3-Small` at `224x224` achieving **99.79% accuracy** and **0.9975 macro-F1** over 4,855 held-out leaf images (`1.50 ms` mean ONNX latency).
   - **HSV Severity Analyzer (`src/vision/severity_analyzer.py`):** Vectorized OpenCV thresholding partitions isolated leaf pixels into healthy green tissue vs. chlorotic/necrotic lesions (`S%`), generating an annotated diagnostic overlay.
   - **Mode 3 (`pest_mobilenetv3.onnx`, 5.83 MB):** Dedicated 6-class IP102 insect classifier (`Aphid`, `Brown_Planthopper`, `Corn_Borer`, `Leafminer`, `Rice_Leaf_Roller`, `Whitefly`; **71.33% val accuracy**).
3. **Gate B + Grounded ExecuTorch Reasoning (`src/advisory/agronomist_engine.py`, `src/reasoning/icar_db.py`):**
   - **Gate B Check:** Suppresses chemical spray advice if confidence `< 75%` (`< 50%` rejected outright) or regional validation fails.
   - **Static Regulatory Prescriptions:** Chemical formulations, dosages (`g/L`), Pre-Harvest Intervals (PHI), and pollinator warnings are queried strictly from SQLite (`data/icar_agronomic_kb.sqlite`).
   - **ExecuTorch SLM (`llama3_2_1b_instruct_8da4w_xnnpack.pte`, 765.32 MB):** Meta Llama 3.2 1B-Instruct acts solely as an empathetic cultural explainer and trilingual follow-up assistant (EN / TA / HI), preventing fabricated pesticide recommendations.

---

## 2. Optimization Techniques for Arm Edge

| Component | Optimization Applied | Footprint / Benefit |
|---|---|---|
| **LLM Reasoning** | Meta Llama 3.2 1B-Instruct exported to ExecuTorch `.pte` with **8-bit dynamic activations, 4-bit weights (`8da4w`)** targeting **XNNPACK** Arm64 kernels | Runs inside ~765 MB `.pte` footprint directly on Raspberry Pi 5 Cortex-A76 CPU |
| **Leaf & Pest Vision** | `MobileNetV3-Small` single-file embedded **ONNX Runtime** graphs (`mobilenetv3_4crops_standalone.onnx`, `pest_mobilenetv3.onnx`) | `~6 MB` per model; zero external weight shard files; `1.50 ms` mean / `1.71 ms` P95 ONNX latency |
| **Speech Recognition (STT)** | Sherpa-ONNX **Whisper-Base INT8** quantized encoder (`27.77 MB`) + decoder (`124.62 MB`) | Fully offline multilingual speech transcription without cloud APIs |
| **Neural Voice Output (TTS)** | Sherpa-ONNX Piper VITS (`en`, `hi`) + MMS Tamil VITS + pre-warmed disk cache (`precache_voices.py`) | Zero-latency replay for frequent crop/severity advisories |
| **Hailo NPU Separation** | Optional **HailoRT** `.hef` offload (`src/vision/hailo_runner.py`, `deploy/HAILO_NPU.md`) | Keeps vision NPU pipeline strictly decoupled from ExecuTorch Llama CPU execution |
| **Android Mobile App** | Native Jetpack Compose + ONNX Runtime Mobile (`onnxruntime-android:1.21.0`) + bundled SQLite KB & sample assets | Standalone offline execution in `KisanDrishti-AI.apk` with optional Pi 5 Wi-Fi offload |

---

## 3. Hardware Utilization & Telemetry Monitoring

`src/telemetry/pi_monitor.py` exposes live edge telemetry at `/api/telemetry` and in the top-right status badge of both the Pi 5 Web Dashboard and Android app:
- Active platform & Arm backend (`CPUExecutionProvider` / `HailoRT` + `ExecuTorch XNNPACK`)
- Process RSS memory footprint (`MB`), CPU clock (`MHz`), and SoC thermal sensor (`°C`)
- Stage-by-stage breakdown: Vision latency (`ms`), HSV severity latency (`ms`), ExecuTorch tokens/s, STT/TTS latency (`ms`).
