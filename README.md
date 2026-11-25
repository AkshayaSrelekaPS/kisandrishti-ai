# KisanDrishti AI (உழவர் பார்வை / किसान दृष्टि)
**Offline 4-Crop Disease Detection, Severity Quantification & Trilingual Agronomic Advisory on Arm Edge**

* **Target Hardware:** Raspberry Pi 5 (64-bit Arm Cortex-A76 @ 2.4 GHz, 8GB RAM)
* **Supported Crops (20 Classes):** Potato, Tomato, Rice (Paddy), Corn (Maize)
* **Languages:** Tamil (தமிழ்), Hindi (हिन्दी), English
* **Edge Stack:**
  * **Vision:** MobileNetV3-Small via ONNX Runtime (Arm NEON; Hailo-8/8L NPU ready via HailoRT)
  * **Severity:** Vectorized OpenCV HSV lesion segmentation ($S\%$)
  * **Guardrails:** Gate A (Blur / Foliage / Crop Mismatch) & Gate B (Confidence $\ge 75\%$ + SQLite Regulatory Lookup)
  * **Local SLM (Reference Runtime):** Meta Llama 3.2 1B-Instruct (`8da4w` XNNPACK `.pte`) deployed on-device via **ExecuTorch** (primary, with `llama.cpp` GGUF fallback; strictly constrained to cultural explanation & translation while chemical dosages are rendered statically from SQLite)
  * **Offline Voice:** Sherpa-ONNX Piper VITS (`en`/`hi`/`ta`) + Whisper-Base INT8 STT

## Quick Start

```bash
pip install -r requirements.txt
python -m src.reasoning.icar_db
python test_pipeline.py
python -m uvicorn src.web_app:app --host 0.0.0.0 --port 8000
```

## Raspberry Pi 5 Deployment

```bash
chmod +x deploy/install_pi5.sh
./deploy/install_pi5.sh
```
