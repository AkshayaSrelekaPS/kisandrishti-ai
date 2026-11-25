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
python setup_llm_model.py
python -m src.reasoning.icar_db
python setup_offline_voice_models.py
python test_pipeline.py
python -m uvicorn src.web_app:app --host 0.0.0.0 --port 8000
```

## Raspberry Pi 5 Deployment

```bash
chmod +x deploy/install_pi5.sh deploy/run_kiosk.sh deploy/verify_pi5.sh
./deploy/install_pi5.sh
./deploy/verify_pi5.sh
```

* **Local Touchscreen Kiosk (HTTP + Mic allowed on localhost):** `sudo systemctl start kisandrishti.service` → `http://localhost:8000`
* **Remote Phone / Tablet over LAN (HTTPS for browser microphone):** `./deploy/run_kiosk.sh --https` → `https://<pi-ip>:8443`
* **Optional Hailo-8 / Hailo-8L AI HAT+ NPU Vision:** See [deploy/HAILO_NPU.md](deploy/HAILO_NPU.md) (vision runs on HailoRT NPU while Meta Llama 3.2 runs separately on ExecuTorch CPU).
* **Air-Gapped USB Model Transfer:** Run `powershell -ExecutionPolicy Bypass -File deploy\prepare_pi_usb_bundle.ps1 -TargetDir E:\kisandrishti_models` on Windows.
