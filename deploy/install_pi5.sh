#!/bin/bash
# ==============================================================================
# KisanDrishti AI: Automated Setup Script for Raspberry Pi 5 (64-bit Arm)
# 4 Crops (20 Classes) • Trilingual (Tamil / Hindi / English)
# Runtime: ONNX Runtime (Vision) + OpenCV + SQLite + ExecuTorch (.pte, XNNPACK 8da4w) + Offline TTS
# ==============================================================================
set -e

echo "=================================================================="
echo "  KisanDrishti AI: Starting Raspberry Pi 5 Edge Environment Setup"
echo "=================================================================="

echo "[Step 1/6] Installing Arm64 system packages & build tools..."
sudo apt update
sudo apt install -y python3-pip python3-opencv sqlite3 espeak-ng libatlas-base-dev \
    python3-venv cmake build-essential git

echo "[Step 2/6] Creating virtual environment and installing runtime packages (incl. ExecuTorch)..."
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "[Step 3/6] Verifying ExecuTorch (.pte) and optional llama.cpp fallback..."
python -c "import executorch.runtime as et, pytorch_tokenizers; print('  -> ExecuTorch runtime verified:', et.__file__)" || echo "Warning: ExecuTorch runtime check failed."
CMAKE_ARGS="-DGGML_NATIVE=ON" pip install llama-cpp-python || echo "Optional llama.cpp fallback skipped (ExecuTorch is primary)."

echo "[Step 4/6] Rebuilding ICAR/TNAU SQLite KB & fetching offline voice models..."
python -m src.reasoning.icar_db
python setup_offline_voice_models.py || echo "Warning: offline voice model download skipped."

echo "[Step 5/6] Verifying ONNX MobileNetV3 4-Crop Vision Model..."
python -c "
import onnxruntime as ort, numpy as np
session = ort.InferenceSession('models/mobilenetv3_4crops_standalone.onnx', providers=['CPUExecutionProvider'])
inp = np.random.randn(1, 3, 224, 224).astype(np.float32)
out = session.run(None, {session.get_inputs()[0].name: inp})
print('  -> ONNX model verified! Output shape:', out[0].shape)
"

echo "[Step 6/6] Configuring systemd autostart service..."
CURRENT_DIR=$(pwd)
CURRENT_USER=$(whoami)

cat <<EOF | sudo tee /etc/systemd/system/kisandrishti.service
[Unit]
Description=KisanDrishti AI Offline Web Kiosk Service
After=network.target

[Service]
Type=simple
User=${CURRENT_USER}
WorkingDirectory=${CURRENT_DIR}
ExecStart=${CURRENT_DIR}/.venv/bin/python -m uvicorn src.web_app:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable kisandrishti.service

echo "=================================================================="
echo "  Setup Completed!"
echo "  Ensure models/llama3_2_1b_instruct_8da4w_xnnpack.pte and"
echo "  models/tokenizer.model are present in models/"
echo "  Start Kiosk: sudo systemctl start kisandrishti.service"
echo "=================================================================="
