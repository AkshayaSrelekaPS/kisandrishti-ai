# Optional Hailo-8 / Hailo-8L NPU Vision Pipeline (Raspberry Pi AI HAT+)

KisanDrishti AI cleanly separates **Vision Inference** from **Language Advisory Inference**:

| Workload | CPU-Only Pi 5 Mode (Default) | Pi 5 + AI HAT+ (Hailo NPU Mode) |
|---|---|---|
| **Mode 1 Leaf Disease (20 classes)** | ONNX Runtime (`models/mobilenetv3_4crops_standalone.onnx`) on Arm Cortex-A76 | HailoRT (`models/mobilenetv3_4crops.hef`) on Hailo-8/8L NPU |
| **Mode 3 Insect Pest (6 classes)** | ONNX Runtime (`models/pest_mobilenetv3.onnx`) on Arm Cortex-A76 | HailoRT (`models/pest_mobilenetv3.hef`) on Hailo-8/8L NPU |
| **HSV Lesion Severity (`S%`)** | OpenCV vectorized HSV on Arm CPU | OpenCV vectorized HSV on Arm CPU |
| **Meta Llama 3.2 1B Advisory & Q&A** | **ExecuTorch** (`models/llama3_2_1b_instruct_8da4w_xnnpack.pte`) on Arm CPU | **ExecuTorch** (`models/llama3_2_1b_instruct_8da4w_xnnpack.pte`) on Arm CPU |
| **Offline Speech (STT & TTS)** | Sherpa-ONNX Whisper-Base INT8 + Piper VITS on Arm CPU | Sherpa-ONNX Whisper-Base INT8 + Piper VITS on Arm CPU |

## Enabling Hailo NPU Vision on Raspberry Pi 5

1. Install HailoRT system packages on Raspberry Pi OS:
   ```bash
   sudo apt update && sudo apt install -y hailo-all
   ```
   Ensure `hailo_platform` is importable in the Python environment (use `--system-site-packages` if creating `.venv` against system HailoRT Python bindings).

2. On an x86_64 host with **Hailo Dataflow Compiler**, compile the ONNX vision models into `.hef` targeting your accelerator (`hailo8l` for 13 TOPS AI HAT+ or `hailo8` for 26 TOPS):
   ```bash
   hailomz compile --ckpt models/mobilenetv3_4crops_standalone.onnx \
     --hw-arch hailo8l --calib-path data/sample_leaves/ --classes 20
   # Rename/place output at: models/mobilenetv3_4crops.hef

   hailomz compile --ckpt models/pest_mobilenetv3.onnx \
     --hw-arch hailo8l --calib-path data/pests/ --classes 6
   # Rename/place output at: models/pest_mobilenetv3.hef
   ```

3. Copy `models/mobilenetv3_4crops.hef` and `models/pest_mobilenetv3.hef` to the Pi.
   `KisanDrishtiDiagnosticEngine` (`src/diagnose.py`) and `PestDetector` (`src/vision/pest_detector.py`) automatically use `HailoVisionRunner` (`src/vision/hailo_runner.py`) when `hailo_platform` and the `.hef` files are present, while Llama 3.2 continues executing separately on ExecuTorch CPU.
