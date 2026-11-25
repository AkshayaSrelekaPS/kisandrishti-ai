"""
KisanDrishti AI: Complete 4-Crop End-to-End Trilingual Diagnostic Pipeline
Integrates:
- Gate A: Quality Pre-Check (Null, Laplacian Blur, Foliage Ratio) + 4-Crop Identity Check
- Perception: MobileNetV3-Small via ONNX Runtime (or optional HailoRT NPU .hef on AI HAT+)
- Calibration: <50% Rejection | 50-75% Borderline Checklist | >=75% High-Confidence Acceptance
- Severity: OpenCV Vectorized HSV Lesion Surface Area Quantification (S %)
- Knowledge: Deterministic SQLite ICAR/TNAU/CIBRC Regulatory Database
- Gate B: 4-Point Advisory Safety Validation Gate
- Reasoning: Meta Llama 3.2 1B-Instruct via ExecuTorch (.pte primary, llama.cpp fallback) - cultural explanation only
- Output: Structured Agronomic Prescription Card, Annotated Leaf, Offline Audio, & Arm Telemetry
"""
import os
import sys
import json
import time
import cv2
import numpy as np

try:
    import onnxruntime as ort
except ImportError:
    ort = None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "models")
DATA_DIR = os.path.join(BASE_DIR, "data")
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.vision.severity_analyzer import SeverityAnalyzer
from src.vision.pest_detector import PestDetector
from src.vision.hailo_runner import HailoVisionRunner, HAILO_AVAILABLE
from src.reasoning.icar_db import ICARKnowledgeBase
from src.advisory.agronomist_engine import MultilingualAgronomistEngine
from src.audio.voice_assistant import FarmerVoiceAssistant
from src.telemetry.pi_monitor import ArmTelemetryMonitor


class KisanDrishtiDiagnosticEngine:
    # Heuristic Gate A / Confidence thresholds (subject to empirical calibration)
    MIN_LAPLACIAN_BLUR_VAR = 20.0
    MIN_FOLIAGE_RATIO = 0.08
    REJECT_CONFIDENCE_THRESHOLD = 0.50
    ACCEPT_CONFIDENCE_THRESHOLD = 0.75

    def __init__(self, model_version: str = "4crops", enable_audio: bool = True, enable_llm: bool = True):
        self.enable_audio = enable_audio
        self.enable_llm = enable_llm

        if model_version == "4crops" and os.path.exists(os.path.join(MODELS_DIR, "classes_4crops.json")):
            self.classes_path = os.path.join(MODELS_DIR, "classes_4crops.json")
            self.onnx_candidates = [
                os.path.join(MODELS_DIR, "mobilenetv3_4crops_standalone.onnx"),
                os.path.join(MODELS_DIR, "mobilenetv3_4crops.onnx"),
            ]
            self.pt_weights_path = os.path.join(MODELS_DIR, "best_mobilenetv3_4crops.pt")
        else:
            self.classes_path = os.path.join(MODELS_DIR, "classes.json")
            self.onnx_candidates = [
                os.path.join(MODELS_DIR, "mobilenetv3_tomato_potato.onnx"),
            ]
            self.pt_weights_path = os.path.join(MODELS_DIR, "best_mobilenetv3_tomato_potato.pt")

        with open(self.classes_path, "r", encoding="utf-8") as f:
            self.metadata = json.load(f)

        self.class_names = self.metadata["classes"]
        self.num_classes = len(self.class_names)
        self.supported_crops = self.metadata.get("supported_crops", ["Potato", "Tomato", "Corn", "Rice"])
        self.mean = np.array(self.metadata.get("mean", [0.485, 0.456, 0.406]), dtype=np.float32)
        self.std = np.array(self.metadata.get("std", [0.229, 0.224, 0.225]), dtype=np.float32)

        self.backend = None
        self.hailo_runner = None
        self.ort_session = None
        self.ort_input_name = None
        self.torch_model = None

        self._init_vision_backend()

        self.severity_analyzer = SeverityAnalyzer()
        self.pest_detector = PestDetector()
        self.kb = ICARKnowledgeBase()
        self.agronomist = MultilingualAgronomistEngine(enable_llm=enable_llm)
        self.voice_assistant = FarmerVoiceAssistant()
        self.telemetry = ArmTelemetryMonitor()
        print(f"KisanDrishti Engine ready ({self.num_classes} classes, Vision backend: {self.backend}, LLM backend: {self.agronomist.backend_name})")

    def _init_vision_backend(self):
        """Use HailoRT NPU (.hef) when AI HAT+ is present, else lightweight ONNX Runtime on Arm CPU."""
        hef_path = os.path.join(MODELS_DIR, "mobilenetv3_4crops.hef")
        if HAILO_AVAILABLE and os.path.exists(hef_path):
            runner = HailoVisionRunner(hef_path)
            if runner.ready:
                self.hailo_runner = runner
                self.backend = f"HailoRT NPU ({os.path.basename(hef_path)})"
                return

        if ort is not None:
            for onnx_path in self.onnx_candidates:
                if os.path.exists(onnx_path):
                    sess_opts = ort.SessionOptions()
                    sess_opts.intra_op_num_threads = 4
                    sess_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                    self.ort_session = ort.InferenceSession(
                        onnx_path, sess_options=sess_opts, providers=["CPUExecutionProvider"]
                    )
                    self.ort_input_name = self.ort_session.get_inputs()[0].name
                    self.backend = f"ONNXRuntime ({os.path.basename(onnx_path)})"
                    return

        # Fallback only if onnxruntime is missing or ONNX file is unavailable
        import torch
        import torch.nn as nn
        from torchvision.models import mobilenet_v3_small

        model = mobilenet_v3_small(weights=None)
        in_features = model.classifier[3].in_features
        model.classifier[3] = nn.Linear(in_features, self.num_classes)
        model.load_state_dict(torch.load(self.pt_weights_path, map_location="cpu"))
        model.eval()
        self.torch_model = model
        self.backend = f"PyTorch-Fallback ({os.path.basename(self.pt_weights_path)})"

    def _preprocess(self, img_bgr: np.ndarray) -> np.ndarray:
        """Resize(256x256) -> CenterCrop(224x224) -> RGB float32 Normalize -> NCHW."""
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(img_rgb, (256, 256), interpolation=cv2.INTER_LINEAR)
        start = (256 - 224) // 2
        cropped = resized[start:start + 224, start:start + 224]
        arr = cropped.astype(np.float32) / 255.0
        arr = (arr - self.mean) / self.std
        chw = np.transpose(arr, (2, 0, 1))
        return np.expand_dims(chw, axis=0).astype(np.float32)

    def _predict_logits(self, input_tensor: np.ndarray) -> np.ndarray:
        if self.hailo_runner is not None and self.hailo_runner.ready:
            return self.hailo_runner.infer_logits(input_tensor)
        if self.ort_session is not None:
            outputs = self.ort_session.run(None, {self.ort_input_name: input_tensor})
            return outputs[0][0]
        import torch
        with torch.no_grad():
            t = torch.from_numpy(input_tensor)
            return self.torch_model(t).numpy()[0]

    @staticmethod
    def _softmax(logits: np.ndarray) -> np.ndarray:
        shifted = logits - np.max(logits)
        exps = np.exp(shifted)
        return exps / np.sum(exps)

    def _normalize_crop(self, raw_str: str) -> str:
        s = raw_str.lower().strip()
        if "corn" in s or "maize" in s:
            return "Corn"
        if "potato" in s:
            return "Potato"
        if "tomato" in s:
            return "Tomato"
        if "rice" in s or "paddy" in s:
            return "Rice"
        return raw_str.capitalize()

    def _check_image_quality(self, img_bgr: np.ndarray) -> dict:
        """Gate A pre-check: scale-normalized Laplacian blur variance and foliage ratio."""
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        raw_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        gray_256 = cv2.resize(gray, (256, 256), interpolation=cv2.INTER_AREA)
        res_var = float(cv2.Laplacian(gray_256, cv2.CV_64F).var())
        blur_var = max(raw_var, res_var)
        foliage_ratio = self.severity_analyzer.compute_foliage_ratio(img_bgr)
        return {
            "blur_variance": round(blur_var, 2),
            "foliage_ratio": round(foliage_ratio, 4),
            "blur_ok": blur_var >= self.MIN_LAPLACIAN_BLUR_VAR,
            "foliage_ok": foliage_ratio >= self.MIN_FOLIAGE_RATIO,
        }

    def diagnose_pest(
        self,
        pest_image_path: str,
        selected_crop: str = "Tomato",
        lang: str = "en",
        voice: str = "female",
        voice_speed: str = "slow",
        state: str = "National (ICAR Baseline)",
        district: str = "All Districts",
    ) -> dict:
        """Mode 3: Image-level insect pest classification + ICAR/TNAU advisory."""
        t_start = time.perf_counter()
        self.voice_assistant.set_voice_persona(voice)
        pest_res = self.pest_detector.detect(pest_image_path)
        if pest_res.get("status") != "SUCCESS":
            return {
                "status": pest_res.get("status", "REJECTED_BY_GATE_A"),
                "gate_a_passed": False,
                "reason": pest_res.get("reason", "PEST_REJECTED"),
                "message": pest_res.get("message", "Mode 3 pest screening could not classify image."),
                "telemetry": self.telemetry.snapshot(),
                "total_latency_ms": round((time.perf_counter() - t_start) * 1000, 2),
            }

        pest_cls = pest_res["pest_class"]
        conf_val = pest_res["confidence"]
        is_borderline = pest_res["is_borderline"]
        treatment = self.kb.get_treatment("Pest", pest_cls, "Moderate", lang=lang, state=state)

        diagnostic_payload = {
            "crop": selected_crop,
            "disease": pest_cls,
            "pathogen_scientific": (treatment or {}).get("pathogen_scientific", ""),
            "confidence": conf_val,
            "severity_pct": 0.0,
            "severity_stage": "Uncertain" if is_borderline else "Moderate",
            "state": state,
            "district": district,
            "treatment": treatment,
            "pest_status": f"Mode 3 Verified: {pest_cls} ({conf_val*100:.1f}%)",
        }

        advisory_result = self.agronomist.generate_advisory(diagnostic_payload, lang=lang)
        spoken_script = self.voice_assistant.build_spoken_script(diagnostic_payload, lang=lang)
        audio_path = (
            self.voice_assistant.speak(spoken_script, lang=lang, speed=voice_speed)
            if self.enable_audio
            else None
        )

        return {
            "status": "SUCCESS",
            "mode": "Mode 3: Insect Pest Classification",
            "crop": selected_crop,
            "disease": pest_cls,
            "pathogen_scientific": diagnostic_payload["pathogen_scientific"],
            "confidence": conf_val,
            "severity_pct": 0.0,
            "severity_stage": diagnostic_payload["severity_stage"],
            "state": state,
            "district": district,
            "pest_status": diagnostic_payload["pest_status"],
            "prescription_card": advisory_result["prescription_card"],
            "llama_prompt": advisory_result["llama_prompt"],
            "llama_explanation": advisory_result["llama_explanation"],
            "llm_metrics": advisory_result["llm_metrics"],
            "spoken_script": spoken_script,
            "audio_path": audio_path,
            "gate_a_passed": True,
            "gate_b_passed": advisory_result["gate_b_passed"],
            "is_borderline": is_borderline,
            "symptom_checklist": (treatment or {}).get("symptom_checklist", []) if is_borderline else [],
            "vision_backend": f"ONNXRuntime ({os.path.basename(self.pest_detector.onnx_path)})",
            "vision_latency_ms": pest_res["pest_latency_ms"],
            "severity_latency_ms": 0.0,
            "total_latency_ms": round((time.perf_counter() - t_start) * 1000, 2),
            "telemetry": self.telemetry.snapshot(),
            "visualization_path": pest_image_path,
        }

    def diagnose(
        self,
        image_path: str,
        selected_crop: str = "Potato",
        lang: str = "en",
        voice: str = "female",
        voice_speed: str = "slow",
        state: str = "National (ICAR Baseline)",
        district: str = "All Districts",
        skip_quality_check: bool = False,
        pest_image_path: str = None,
    ) -> dict:
        t_start = time.perf_counter()

        self.voice_assistant.set_voice_persona(voice)

        if not os.path.exists(image_path):
            return {"status": "ERROR", "error": f"Image file not found: {image_path}"}

        img_bgr = cv2.imread(image_path)
        if img_bgr is None or img_bgr.size == 0:
            return {
                "status": "REJECTED_BY_GATE_A",
                "gate_a_passed": False,
                "reason": "INVALID_IMAGE",
                "message": "Gate A Halt: Could not decode image file. Please capture or upload a valid JPG/PNG leaf photograph.",
            }

        # 1. Gate A Quality Pre-Check (Blur & Foliage Ratio)
        quality = self._check_image_quality(img_bgr)
        if not skip_quality_check:
            if not quality["blur_ok"]:
                return {
                    "status": "REJECTED_BY_GATE_A",
                    "gate_a_passed": False,
                    "reason": "IMAGE_TOO_BLURRY",
                    "quality": quality,
                    "message": f"Gate A Halt: Image is too blurry (Laplacian variance={quality['blur_variance']} < {self.MIN_LAPLACIAN_BLUR_VAR}). Please hold camera steady and retake.",
                    "telemetry": self.telemetry.snapshot(),
                    "total_latency_ms": round((time.perf_counter() - t_start) * 1000, 2),
                }
            if not quality["foliage_ok"]:
                return {
                    "status": "REJECTED_BY_GATE_A",
                    "gate_a_passed": False,
                    "reason": "NON_LEAF_IMAGE",
                    "quality": quality,
                    "message": f"Gate A Halt: Insufficient plant foliage detected ({quality['foliage_ratio']*100:.1f}% leaf area). Capture a close-up of the leaf blade.",
                    "telemetry": self.telemetry.snapshot(),
                    "total_latency_ms": round((time.perf_counter() - t_start) * 1000, 2),
                }

        # 2. Perception Engine (MobileNetV3 ONNX)
        t0 = time.perf_counter()
        input_tensor = self._preprocess(img_bgr)
        logits = self._predict_logits(input_tensor)
        probs = self._softmax(logits)
        pred_idx = int(np.argmax(probs))
        conf_val = float(probs[pred_idx])
        cls_latency_ms = (time.perf_counter() - t0) * 1000

        predicted_class = self.class_names[pred_idx]
        raw_crop, diagnosed_disease = predicted_class.split("___")
        diagnosed_crop = self._normalize_crop(raw_crop)
        norm_selected = self._normalize_crop(selected_crop)

        # 3. Gate A: Confidence Floor (<50%) & Crop Identity Validation
        if conf_val < self.REJECT_CONFIDENCE_THRESHOLD:
            return {
                "status": "REJECTED_BY_GATE_A",
                "gate_a_passed": False,
                "reason": "LOW_CONFIDENCE_UNKNOWN",
                "confidence": conf_val,
                "selected_crop": norm_selected,
                "diagnosed_crop": diagnosed_crop,
                "quality": quality,
                "vision_latency_ms": round(cls_latency_ms, 2),
                "message": f"Gate A Halt: Prediction confidence ({conf_val*100:.1f}%) is below the 50% reliability floor. Capture a clearer close-up of a single leaf.",
                "telemetry": self.telemetry.snapshot(),
                "total_latency_ms": round((time.perf_counter() - t_start) * 1000, 2),
            }

        if norm_selected != diagnosed_crop:
            return {
                "status": "REJECTED_BY_GATE_A",
                "gate_a_passed": False,
                "reason": "CROP_MISMATCH",
                "confidence": conf_val,
                "selected_crop": norm_selected,
                "diagnosed_crop": diagnosed_crop,
                "quality": quality,
                "vision_latency_ms": round(cls_latency_ms, 2),
                "message": f"Crop Mismatch Alert: You selected {norm_selected}, but the leaf matches {diagnosed_crop} ({conf_val*100:.1f}%). Analysis halted to prevent incorrect treatment.",
                "telemetry": self.telemetry.snapshot(),
                "total_latency_ms": round((time.perf_counter() - t_start) * 1000, 2),
            }

        # 4. Leaf-Level Severity Quantification
        t1 = time.perf_counter()
        is_borderline = conf_val < self.ACCEPT_CONFIDENCE_THRESHOLD
        severity_pct, severity_stage, annotated_img = self.severity_analyzer.analyze(
            img_bgr, uncertain=is_borderline
        )
        sev_latency_ms = (time.perf_counter() - t1) * 1000

        # 5. Deterministic SQLite Retrieval
        treatment = self.kb.get_treatment(
            diagnosed_crop, diagnosed_disease, severity_stage, lang=lang, state=state
        )

        # Optional Mode 3 Insect Close-Up screening alongside Mode 1 Leaf Diagnosis
        pest_status = "Pest assessment not performed (Mode 3 insect close-up not provided)"
        pest_detection = None
        if pest_image_path and os.path.exists(pest_image_path):
            p_res = self.pest_detector.detect(pest_image_path)
            if p_res.get("status") == "SUCCESS":
                pest_detection = p_res
                pest_status = f"Mode 3 Detected: {p_res['pest_class']} ({p_res['confidence']*100:.1f}%)"
                p_treat = self.kb.get_treatment("Pest", p_res["pest_class"], "Moderate", lang=lang, state=state)
                if p_treat:
                    pest_detection["treatment"] = p_treat
            else:
                pest_status = p_res.get("message", "Mode 3 screening rejected")

        diagnostic_payload = {
            "crop": diagnosed_crop,
            "disease": diagnosed_disease,
            "pathogen_scientific": (treatment or {}).get("pathogen_scientific", ""),
            "confidence": conf_val,
            "severity_pct": severity_pct,
            "severity_stage": severity_stage,
            "state": state,
            "district": district,
            "treatment": treatment,
            "pest_status": pest_status,
        }

        # 6. Gate B & llama.cpp Context-Constrained Reasoning
        advisory_result = self.agronomist.generate_advisory(diagnostic_payload, lang=lang)
        card = advisory_result["prescription_card"]
        gate_b_passed = advisory_result["gate_b_passed"]

        # 7. Native Spoken Voice Synthesis
        spoken_script = self.voice_assistant.build_spoken_script(diagnostic_payload, lang=lang)
        audio_path = (
            self.voice_assistant.speak(spoken_script, lang=lang, speed=voice_speed)
            if self.enable_audio
            else None
        )

        out_vis_path = os.path.join(BASE_DIR, "output_diagnostic_card.jpg")
        cv2.imwrite(out_vis_path, annotated_img)

        total_time_ms = (time.perf_counter() - t_start) * 1000
        telem = self.telemetry.snapshot()

        return {
            "status": "SUCCESS",
            "crop": diagnosed_crop,
            "disease": diagnosed_disease,
            "pathogen_scientific": diagnostic_payload["pathogen_scientific"],
            "confidence": conf_val,
            "severity_pct": severity_pct,
            "severity_stage": severity_stage,
            "state": state,
            "district": district,
            "pest_status": diagnostic_payload["pest_status"],
            "pest_detection": pest_detection,
            "quality": quality,
            "prescription_card": card,
            "llama_prompt": advisory_result["llama_prompt"],
            "llama_explanation": advisory_result["llama_explanation"],
            "llm_metrics": advisory_result["llm_metrics"],
            "spoken_script": spoken_script,
            "audio_path": audio_path,
            "gate_a_passed": True,
            "gate_b_passed": gate_b_passed,
            "is_borderline": is_borderline,
            "symptom_checklist": (treatment or {}).get("symptom_checklist", []) if is_borderline else [],
            "vision_backend": self.backend,
            "vision_latency_ms": round(cls_latency_ms, 2),
            "severity_latency_ms": round(sev_latency_ms, 2),
            "total_latency_ms": round(total_time_ms, 2),
            "telemetry": telem,
            "visualization_path": out_vis_path,
        }


if __name__ == "__main__":
    engine = KisanDrishtiDiagnosticEngine(model_version="4crops", enable_audio=False, enable_llm=False)
    for sample, crop in [
        ("potato_late_blight.jpg", "Potato"),
        ("rice_bacterial_blight.jpg", "Rice"),
        ("tomato_early_blight.jpg", "Tomato"),
        ("corn_leaf_blight.jpg", "Corn"),
    ]:
        p = os.path.join(DATA_DIR, "sample_leaves", sample)
        if os.path.exists(p):
            res = engine.diagnose(p, selected_crop=crop, lang="ta")
            print(
                f"{res.get('crop')} | {res.get('disease')} | conf={res.get('confidence', 0)*100:.1f}% | "
                f"sev={res.get('severity_pct')}% ({res.get('severity_stage')}) | "
                f"vision={res.get('vision_latency_ms')}ms | total={res.get('total_latency_ms')}ms"
            )
