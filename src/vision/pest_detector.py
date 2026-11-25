"""
KisanDrishti AI: Mode 3 Image-Level Insect Pest Classifier
Runs MobileNetV3-Small via ONNX Runtime on insect close-ups (data/pests/ classes).
Strictly designated as Image-Level Pest Classification (no bounding-box claims).
"""
import json
import os
import time
import cv2
import numpy as np

try:
    import onnxruntime as ort
except ImportError:
    ort = None

from src.vision.hailo_runner import HailoVisionRunner, HAILO_AVAILABLE

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODELS_DIR = os.path.join(BASE_DIR, "models")


class PestDetector:
    MIN_LAPLACIAN_BLUR_VAR = 20.0
    REJECT_CONFIDENCE_THRESHOLD = 0.50
    ACCEPT_CONFIDENCE_THRESHOLD = 0.75

    def __init__(self, onnx_path: str = None, classes_path: str = None, hef_path: str = None):
        self.onnx_path = onnx_path or os.path.join(MODELS_DIR, "pest_mobilenetv3.onnx")
        self.hef_path = hef_path or os.path.join(MODELS_DIR, "pest_mobilenetv3.hef")
        self.classes_path = classes_path or os.path.join(MODELS_DIR, "pest_classes.json")
        self.hailo_runner = None
        self.session = None
        self.input_name = None
        self.backend_name = "unavailable"
        self.class_names = []
        self.mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        self.std = np.array([0.229, 0.224, 0.225], dtype=np.float32)

        if os.path.exists(self.classes_path):
            with open(self.classes_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            self.class_names = meta.get("classes", [])
            self.mean = np.array(meta.get("mean", [0.485, 0.456, 0.406]), dtype=np.float32)
            self.std = np.array(meta.get("std", [0.229, 0.224, 0.225]), dtype=np.float32)

        if HAILO_AVAILABLE and os.path.exists(self.hef_path):
            runner = HailoVisionRunner(self.hef_path)
            if runner.ready:
                self.hailo_runner = runner
                self.backend_name = f"HailoRT NPU ({os.path.basename(self.hef_path)})"

        if self.hailo_runner is None and ort is not None and os.path.exists(self.onnx_path):
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = 4
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            self.session = ort.InferenceSession(
                self.onnx_path, sess_options=opts, providers=["CPUExecutionProvider"]
            )
            self.input_name = self.session.get_inputs()[0].name
            self.backend_name = f"ONNXRuntime ({os.path.basename(self.onnx_path)})"

    def is_ready(self) -> bool:
        return (self.hailo_runner is not None or self.session is not None) and len(self.class_names) > 0

    def _preprocess(self, img_bgr: np.ndarray) -> np.ndarray:
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(img_rgb, (256, 256), interpolation=cv2.INTER_LINEAR)
        start = (256 - 224) // 2
        cropped = resized[start:start + 224, start:start + 224]
        arr = cropped.astype(np.float32) / 255.0
        arr = (arr - self.mean) / self.std
        return np.expand_dims(np.transpose(arr, (2, 0, 1)), axis=0).astype(np.float32)

    @staticmethod
    def _softmax(logits: np.ndarray) -> np.ndarray:
        shifted = logits - np.max(logits)
        exps = np.exp(shifted)
        return exps / np.sum(exps)

    def detect(self, image_path: str, skip_quality_check: bool = False) -> dict:
        if not self.is_ready():
            return {"status": "UNAVAILABLE", "message": "Mode 3 pest model not initialized."}
        if not os.path.exists(image_path):
            return {"status": "ERROR", "message": f"Pest image not found: {image_path}"}

        img_bgr = cv2.imread(image_path)
        if img_bgr is None or img_bgr.size == 0:
            return {"status": "REJECTED_BY_GATE_A", "reason": "INVALID_IMAGE", "message": "Could not decode insect image."}

        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        raw_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        res_var = float(cv2.Laplacian(cv2.resize(gray, (256, 256)), cv2.CV_64F).var())
        blur_var = max(raw_var, res_var)
        if not skip_quality_check and blur_var < self.MIN_LAPLACIAN_BLUR_VAR:
            return {
                "status": "REJECTED_BY_GATE_A",
                "reason": "IMAGE_TOO_BLURRY",
                "blur_variance": round(blur_var, 2),
                "message": f"Gate A Halt (Mode 3): Insect photo is too blurry (variance={blur_var:.1f} < {self.MIN_LAPLACIAN_BLUR_VAR}).",
            }

        t0 = time.perf_counter()
        inp = self._preprocess(img_bgr)
        if self.hailo_runner is not None and self.hailo_runner.ready:
            logits = self.hailo_runner.infer_logits(inp)
        else:
            logits = self.session.run(None, {self.input_name: inp})[0][0]
        probs = self._softmax(logits)
        pred_idx = int(np.argmax(probs))
        conf = float(probs[pred_idx])
        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        pest_class = self.class_names[pred_idx]

        if conf < self.REJECT_CONFIDENCE_THRESHOLD:
            return {
                "status": "REJECTED_BY_GATE_A",
                "reason": "LOW_CONFIDENCE_UNKNOWN",
                "confidence": conf,
                "pest_latency_ms": latency_ms,
                "message": f"Gate A Halt (Mode 3): Insect confidence ({conf*100:.1f}%) is below 50%. Capture a closer, sharper insect photo.",
            }

        top_indices = np.argsort(probs)[::-1][:4]
        top_candidates = [
            {
                "crop": "Pest",
                "disease": self.class_names[int(i)],
                "label": self.class_names[int(i)].replace("_", " "),
                "probability_pct": round(float(probs[int(i)]) * 100.0, 1),
            }
            for i in top_indices
        ]

        return {
            "status": "SUCCESS",
            "mode": "Mode 3: Image-Level Insect Pest Classification",
            "pest_class": pest_class,
            "confidence": conf,
            "is_borderline": conf < self.ACCEPT_CONFIDENCE_THRESHOLD,
            "pest_latency_ms": latency_ms,
            "blur_variance": round(blur_var, 2),
            "top_candidates": top_candidates,
        }
