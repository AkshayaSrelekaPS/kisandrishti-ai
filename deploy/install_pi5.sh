#!/bin/bash
# ==============================================================================
# KisanDrishti AI: Automated Setup Script for Raspberry Pi 5 (64-bit Arm)
# 4 Crops (20 Classes) + Mode 3 Pests (6 Classes) • Trilingual (TA / HI / EN)
# Vision: ONNX Runtime CPU (or HailoRT NPU .hef) + OpenCV HSV
# Reasoning: Meta Llama 3.2 1B-Instruct via ExecuTorch (.pte, XNNPACK 8da4w)
# ==============================================================================
set -e

echo "=================================================================="
echo "  KisanDrishti AI: Starting Raspberry Pi 5 Edge Environment Setup"
echo "=================================================================="

echo "[Step 1/7] Checking Python >= 3.11 & installing Arm64 system packages..."
python3 - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit(
        f"ERROR: Python >= 3.11 required for ExecuTorch aarch64 wheels (found {sys.version.split()[0]}). "
        "Use Raspberry Pi OS Bookworm/Trixie (Python 3.11+)."
    )
print("  -> Python version OK:", sys.version.split()[0])
PY

sudo apt update
sudo apt install -y python3-pip python3-opencv sqlite3 espeak-ng \
    libatlas-base-dev libopenblas-dev libgomp1 openssl \
    python3-venv cmake build-essential git

echo "[Step 2/7] Creating virtual environment and installing runtime packages..."
# --system-site-packages lets optional HailoRT Python bindings (`hailo-all`) work cleanly inside .venv
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "[Step 3/7] Downloading ExecuTorch Llama 3.2 (.pte) if not already staged..."
python setup_llm_model.py || echo "Warning: .pte download skipped; copy models/llama3_2_1b_instruct_8da4w_xnnpack.pte manually for air-gapped Pi."

echo "[Step 4/7] Optional llama.cpp fallback (ExecuTorch is primary)..."
CMAKE_ARGS="-DGGML_NATIVE=ON" pip install llama-cpp-python || echo "Optional llama.cpp skipped."

echo "[Step 5/7] Rebuilding SQLite KB, offline STT/TTS models & audio cache..."
python -m src.reasoning.icar_db
python setup_offline_voice_models.py || echo "Warning: offline voice download skipped; copy models/tts & models/stt manually."
python precache_voices.py || echo "Warning: audio cache warmup skipped."

echo "[Step 6/7] Verifying ONNX vision + ExecuTorch .pte + Sherpa STT/TTS..."
python -c "
import onnxruntime as ort, numpy as np
s = ort.InferenceSession('models/mobilenetv3_4crops_standalone.onnx', providers=['CPUExecutionProvider'])
out = s.run(None, {s.get_inputs()[0].name: np.random.randn(1, 3, 224, 224).astype(np.float32)})
print('  -> ONNX 4-crop vision verified! Shape:', out[0].shape)
"
python -c "
from src.advisory.agronomist_engine import MultilingualAgronomistEngine
eng = MultilingualAgronomistEngine(enable_llm=True)
print('  -> LLM backend initialized:', eng.backend_name)
"

echo "[Step 7/7] Generating self-signed TLS cert (LAN mic access) & systemd service..."
chmod +x deploy/run_kiosk.sh deploy/verify_pi5.sh
mkdir -p deploy/certs
if [ ! -f deploy/certs/cert.pem ] || [ ! -f deploy/certs/key.pem ]; then
    openssl req -x509 -newkey rsa:2048 -nodes -days 3650 \
        -keyout deploy/certs/key.pem -out deploy/certs/cert.pem \
        -subj "/CN=kisandrishti.local"
fi

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
Environment=OMP_NUM_THREADS=4
Environment=OPENBLAS_NUM_THREADS=4
ExecStart=${CURRENT_DIR}/deploy/run_kiosk.sh
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable kisandrishti.service

echo "=================================================================="
echo "  Raspberry Pi 5 Setup Completed!"
echo "  Verify hardware:  ./deploy/verify_pi5.sh"
echo "  Start HTTP kiosk: sudo systemctl start kisandrishti.service"
echo "  Start LAN HTTPS:  ./deploy/run_kiosk.sh --https"
echo "=================================================================="
