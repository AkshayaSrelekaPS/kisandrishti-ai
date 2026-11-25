#!/bin/bash
# ==============================================================================
# KisanDrishti AI: One-Command Raspberry Pi 5 End-to-End Hardware Verification
# ==============================================================================
set -e
cd "$(dirname "$0")/.."
source .venv/bin/activate

export OMP_NUM_THREADS=4

echo "=================================================================="
echo "  1/4 Validating Mode 1 (4-Crop ONNX) + Gate A/B + ExecuTorch"
echo "=================================================================="
python -u test_pipeline.py

echo "=================================================================="
echo "  2/4 Validating Mode 3 (6-Pest ONNX) + Offline Neural TTS"
echo "=================================================================="
python -u test_mode3_pest.py

echo "=================================================================="
echo "  3/4 Validating Offline Whisper STT -> ExecuTorch -> Sherpa TTS"
echo "=================================================================="
python -u test_voice_assistant.py

echo "=================================================================="
echo "  4/4 Measuring Real Arm Cortex-A76 Latency, RAM & SoC Thermal"
echo "=================================================================="
python -u benchmark_suite.py

echo "ALL RASPBERRY PI 5 VERIFICATION CHECKS COMPLETED!"
