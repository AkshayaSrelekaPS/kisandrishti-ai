"""
KisanDrishti AI: 100% Offline Edge Agronomic Clinical Diagnostic Kiosk
FastAPI Web Application for Bharat AI-SoC Challenge 2026-27.
Zero external CDN/font dependencies; supports 4 crops (20 diseases), Mode 3 Pests (6 classes),
ExecuTorch Llama 3.2 advisory, 2-way offline Voice Q&A, and full trilingual UI (EN/TA/HI).
"""
import json
import os
import shutil
import sys
import time
import uuid
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.diagnose import KisanDrishtiDiagnosticEngine
from src.reasoning.icar_db import VERIFIED_REGIONS
from src.audio.voice_qa import OfflineVoiceQAEngine

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
SAMPLES_DIR = os.path.join(DATA_DIR, "sample_leaves")
AUDIO_DIR = os.path.join(DATA_DIR, "audio_outputs")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
VIS_DIR = os.path.join(DATA_DIR, "visualizations")

for d in [SAMPLES_DIR, AUDIO_DIR, UPLOADS_DIR, VIS_DIR]:
    os.makedirs(d, exist_ok=True)

print("Initializing KisanDrishti 4-Crop Trilingual Diagnostic Engine...")
engine = KisanDrishtiDiagnosticEngine(model_version="4crops")
voice_qa = OfflineVoiceQAEngine(engine.agronomist, engine.voice_assistant, engine.telemetry)
print("Engine ready.")

app = FastAPI(title="KisanDrishti AI Offline Kiosk")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static/samples", StaticFiles(directory=SAMPLES_DIR), name="samples")
app.mount("/static/audio", StaticFiles(directory=AUDIO_DIR), name="audio")
app.mount("/static/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
app.mount("/static/vis", StaticFiles(directory=VIS_DIR), name="vis")

SAMPLE_METADATA = [
    {
        "id": "potato_late_blight.jpg",
        "crop": "Potato",
        "title": "Potato Late Blight (Active Lesion)",
        "file": "potato_late_blight.jpg",
        "markers": "Expanding water-soaked dark brown marginal lesions with pale chlorotic borders.",
        "expected": "Potato___Late_blight • Phytophthora infestans",
    },
    {
        "id": "potato_healthy.jpg",
        "crop": "Potato",
        "title": "Potato Healthy Leaf",
        "file": "potato_healthy.jpg",
        "markers": "Uniform dark green lamina without necrotic rings or water-soaked margins.",
        "expected": "Potato___healthy • Cultural Baseline",
    },
    {
        "id": "tomato_early_blight.jpg",
        "crop": "Tomato",
        "title": "Tomato Early Blight",
        "file": "tomato_early_blight.jpg",
        "markers": "Dark brown concentric target-board rings surrounded by yellow chlorotic halos.",
        "expected": "Tomato___Early_blight • Alternaria solani",
    },
    {
        "id": "rice_bacterial_blight.jpg",
        "crop": "Rice",
        "title": "Rice Bacterial Leaf Blight",
        "file": "rice_bacterial_blight.jpg",
        "markers": "Water-soaked straw-yellow wavy stripes advancing down from leaf tips.",
        "expected": "Rice___Bacterial_leaf_blight • Xanthomonas oryzae",
    },
    {
        "id": "rice_brown_spot.jpg",
        "crop": "Rice",
        "title": "Rice Brown Spot",
        "file": "rice_brown_spot.jpg",
        "markers": "Oval sesame-shaped dark brown spots with gray centers across rice blade.",
        "expected": "Rice___Brown_spot • Bipolaris oryzae",
    },
    {
        "id": "corn_leaf_blight.jpg",
        "crop": "Corn",
        "title": "Corn Northern Leaf Blight",
        "file": "corn_leaf_blight.jpg",
        "markers": "Long cigar-shaped gray-green necrotic streaks running parallel to leaf veins.",
        "expected": "Corn___Northern_Leaf_Blight • Exserohilum turcicum",
    },
]


@app.get("/api/samples")
def get_samples():
    return SAMPLE_METADATA


@app.get("/api/regions")
def get_regions():
    return VERIFIED_REGIONS


@app.get("/api/library")
def get_library(lang: str = "en"):
    return engine.kb.list_all_guidelines(lang=lang)


@app.get("/api/telemetry")
def get_telemetry():
    return {
        "vision_backend": engine.backend,
        "pest_ready": engine.pest_detector.is_ready(),
        "llm_backend": engine.agronomist.backend_name,
        "stt_ready": voice_qa.is_stt_ready(),
        "telemetry": engine.telemetry.snapshot(),
    }


@app.post("/api/diagnose-pest")
def run_pest_diagnosis(
    crop: str = Form("Tomato"),
    lang: str = Form("ta"),
    voice: str = Form("female"),
    voice_speed: str = Form("slow"),
    state: str = Form("National (ICAR Baseline)"),
    district: str = Form("All Districts"),
    file: UploadFile = File(...),
):
    t0 = time.perf_counter()
    img_filename = f"pest_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}.jpg"
    img_path = os.path.join(UPLOADS_DIR, img_filename)
    with open(img_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    original_img_url = f"/static/uploads/{img_filename}"

    diag_res = engine.diagnose_pest(
        img_path,
        selected_crop=crop,
        lang=lang,
        voice=voice,
        voice_speed=voice_speed,
        state=state,
        district=district,
    )
    if diag_res.get("status") != "SUCCESS":
        return {
            "status": "GATE_A_REJECTED",
            "gate_a_passed": False,
            "reason": diag_res.get("reason"),
            "message": diag_res.get("message"),
            "original_image_url": original_img_url,
            "telemetry": diag_res.get("telemetry"),
            "total_latency_ms": round((time.perf_counter() - t0) * 1000, 1),
        }

    audio_url = ""
    if diag_res.get("audio_path") and os.path.exists(diag_res["audio_path"]):
        audio_url = f"/static/audio/{os.path.basename(diag_res['audio_path'])}"

    return {
        "status": "SUCCESS",
        "mode": diag_res["mode"],
        "crop": diag_res["crop"],
        "disease": diag_res["disease"],
        "pathogen_scientific": diag_res.get("pathogen_scientific", ""),
        "confidence": round(diag_res["confidence"] * 100, 1),
        "severity_pct": 0.0,
        "severity_stage": diag_res["severity_stage"],
        "state": diag_res.get("state"),
        "district": diag_res.get("district"),
        "pest_status": diag_res.get("pest_status"),
        "top_candidates": diag_res.get("top_candidates", []),
        "pathology_metrics": {
            "leaf_isolation_pct": 0.0,
            "healthy_pct": 0.0,
            "chlorosis_pct": 0.0,
            "necrosis_pct": 0.0,
        },
        "treatment_summary": diag_res.get("treatment_summary", {}),
        "gate_a_passed": True,
        "gate_b_passed": diag_res["gate_b_passed"],
        "is_borderline": diag_res.get("is_borderline", False),
        "symptom_checklist": diag_res.get("symptom_checklist", []),
        "prescription_card": diag_res["prescription_card"],
        "llama_explanation": diag_res.get("llama_explanation", ""),
        "llm_metrics": diag_res.get("llm_metrics", {}),
        "spoken_script": diag_res["spoken_script"],
        "audio_url": audio_url,
        "audio_backend": engine.voice_assistant.last_backend,
        "original_image_url": original_img_url,
        "annotated_image_url": original_img_url,
        "vision_backend": diag_res.get("vision_backend"),
        "vision_latency_ms": diag_res.get("vision_latency_ms"),
        "severity_latency_ms": 0.0,
        "telemetry": diag_res.get("telemetry"),
        "total_latency_ms": round((time.perf_counter() - t0) * 1000, 1),
    }


@app.post("/api/voice-qa")
def run_voice_qa(
    lang: str = Form("ta"),
    voice: str = Form("female"),
    voice_speed: str = Form("slow"),
    question_text: str = Form(""),
    context_json: str = Form("{}"),
    audio_file: UploadFile = File(None),
):
    try:
        ctx = json.loads(context_json or "{}")
    except Exception:
        ctx = {}

    wav_path = None
    if audio_file and audio_file.filename:
        wav_name = f"qa_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}.wav"
        wav_path = os.path.join(UPLOADS_DIR, wav_name)
        with open(wav_path, "wb") as f:
            shutil.copyfileobj(audio_file.file, f)

    res = voice_qa.answer_question(
        question_text=question_text,
        wav_path=wav_path,
        context=ctx,
        lang=lang,
        voice=voice,
        voice_speed=voice_speed,
    )
    if res.get("audio_path") and os.path.exists(res["audio_path"]):
        res["audio_url"] = f"/static/audio/{os.path.basename(res['audio_path'])}"
    else:
        res["audio_url"] = ""
    return res


@app.post("/api/diagnose")
def run_diagnosis(
    crop: str = Form(...),
    lang: str = Form("ta"),
    voice: str = Form("female"),
    voice_speed: str = Form("slow"),
    state: str = Form("National (ICAR Baseline)"),
    district: str = Form("All Districts"),
    sample_name: str = Form(None),
    file: UploadFile = File(None),
):
    t0 = time.perf_counter()
    img_filename = f"query_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}.jpg"
    img_path = os.path.join(UPLOADS_DIR, img_filename)

    if file and file.filename:
        with open(img_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        original_img_url = f"/static/uploads/{img_filename}"
    elif sample_name:
        sample_path = os.path.join(SAMPLES_DIR, sample_name)
        if not os.path.exists(sample_path):
            return JSONResponse(status_code=400, content={"error": f"Sample {sample_name} not found"})
        shutil.copyfile(sample_path, img_path)
        original_img_url = f"/static/samples/{sample_name}"
    else:
        return JSONResponse(status_code=400, content={"error": "No image uploaded or sample selected"})

    diag_res = engine.diagnose(
        img_path,
        selected_crop=crop,
        lang=lang,
        voice=voice,
        voice_speed=voice_speed,
        state=state,
        district=district,
    )

    if diag_res.get("status") == "REJECTED_BY_GATE_A":
        return {
            "status": "GATE_A_REJECTED",
            "gate_a_passed": False,
            "reason": diag_res.get("reason"),
            "selected_crop": diag_res.get("selected_crop"),
            "diagnosed_crop": diag_res.get("diagnosed_crop"),
            "message": diag_res.get("message"),
            "quality": diag_res.get("quality", {}),
            "original_image_url": original_img_url,
            "telemetry": diag_res.get("telemetry"),
            "total_latency_ms": round((time.perf_counter() - t0) * 1000, 1),
        }

    vis_filename = f"vis_{img_filename}"
    vis_dest = os.path.join(VIS_DIR, vis_filename)
    if os.path.exists(diag_res["visualization_path"]):
        shutil.copyfile(diag_res["visualization_path"], vis_dest)

    audio_url = ""
    if diag_res.get("audio_path") and os.path.exists(diag_res["audio_path"]):
        audio_url = f"/static/audio/{os.path.basename(diag_res['audio_path'])}"

    return {
        "status": "SUCCESS",
        "mode": "Mode 1: Leaf Disease & Severity Diagnostics",
        "crop": diag_res["crop"],
        "disease": diag_res["disease"],
        "pathogen_scientific": diag_res.get("pathogen_scientific", ""),
        "confidence": round(diag_res["confidence"] * 100, 1),
        "severity_pct": diag_res["severity_pct"],
        "severity_stage": diag_res["severity_stage"],
        "state": diag_res.get("state"),
        "district": diag_res.get("district"),
        "pest_status": diag_res.get("pest_status"),
        "quality": diag_res.get("quality", {}),
        "pathology_metrics": diag_res.get("pathology_metrics", {}),
        "top_candidates": diag_res.get("top_candidates", []),
        "treatment_summary": diag_res.get("treatment_summary", {}),
        "gate_a_passed": True,
        "gate_b_passed": diag_res["gate_b_passed"],
        "is_borderline": diag_res.get("is_borderline", False),
        "symptom_checklist": diag_res.get("symptom_checklist", []),
        "prescription_card": diag_res["prescription_card"],
        "llama_explanation": diag_res.get("llama_explanation", ""),
        "llm_metrics": diag_res.get("llm_metrics", {}),
        "spoken_script": diag_res["spoken_script"],
        "audio_url": audio_url,
        "audio_backend": engine.voice_assistant.last_backend,
        "original_image_url": original_img_url,
        "annotated_image_url": f"/static/vis/{vis_filename}",
        "vision_backend": diag_res.get("vision_backend"),
        "vision_latency_ms": diag_res.get("vision_latency_ms"),
        "severity_latency_ms": diag_res.get("severity_latency_ms"),
        "telemetry": diag_res.get("telemetry"),
        "total_latency_ms": round((time.perf_counter() - t0) * 1000, 1),
    }


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>KisanDrishti AI | Offline Arm Edge Clinical Kiosk</title>
  <style>
    :root {
      --bg-root: #02110b;
      --bg-header: #051c13;
      --bg-card: #062116;
      --bg-card-deep: #041810;
      --bg-card-inner: #0a2d1f;
      --border-emerald: #134e35;
      --border-glow: #10b981;
      --accent-emerald: #10b981;
      --accent-cyan: #22d3ee;
      --accent-teal: #14b8a6;
      --accent-amber: #f59e0b;
      --accent-red: #f87171;
      --text-main: #ecfdf5;
      --text-soft: #a7f3d0;
      --text-muted: #6ee7b7aa;
      --font-sans: system-ui, -apple-system, 'Segoe UI', Roboto, 'Noto Sans Tamil', 'Noto Sans Devanagari', sans-serif;
      --font-mono: ui-monospace, 'Cascadia Code', Consolas, monospace;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: radial-gradient(circle at top center, #062a1c 0%, var(--bg-root) 60%);
      color: var(--text-main);
      font-family: var(--font-sans);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }
    .telemetry-strip {
      background: #020d09;
      border-bottom: 1px solid #0e3b28;
      padding: 0.42rem 1.25rem;
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 0.6rem;
      font-family: var(--font-mono);
      font-size: 0.72rem;
      color: #86efac;
    }
    .hw-left { display: flex; align-items: center; gap: 0.55rem; flex-wrap: wrap; }
    .live-dot {
      width: 8px; height: 8px; border-radius: 50%; background: #10b981;
      box-shadow: 0 0 8px #10b981;
    }
    .hw-pills { display: flex; flex-wrap: wrap; gap: 0.45rem; }
    .hw-pill {
      background: #052318;
      border: 1px solid #166534;
      color: #6ee7b7;
      padding: 0.18rem 0.55rem;
      border-radius: 999px;
      font-size: 0.7rem;
    }
    .hw-pill.cyan { border-color: #0e7490; color: #67e8f9; background: #04242b; }

    header {
      background: rgba(5, 28, 19, 0.94);
      border-bottom: 1px solid var(--border-emerald);
      padding: 0.75rem 1.25rem;
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 0.85rem;
      position: sticky;
      top: 0;
      z-index: 30;
      backdrop-filter: blur(8px);
    }
    .brand-group { display: flex; align-items: center; gap: 0.75rem; }
    .brand-icon {
      width: 38px; height: 38px; border-radius: 10px;
      background: linear-gradient(135deg, #059669, #14b8a6);
      display: flex; align-items: center; justify-content: center;
      font-size: 1.25rem; box-shadow: 0 0 14px rgba(16, 185, 129, 0.35);
    }
    .brand-title { display: flex; align-items: center; gap: 0.5rem; font-weight: 800; font-size: 1.15rem; color: #fff; }
    .pro-badge {
      background: #064e3b; color: #34d399; border: 1px solid #10b98155;
      font-size: 0.68rem; padding: 0.14rem 0.48rem; border-radius: 6px; font-weight: 700;
    }
    .brand-sub { font-size: 0.74rem; color: var(--text-muted); margin-top: 0.1rem; }

    .nav-tabs { display: flex; flex-wrap: wrap; gap: 0.4rem; }
    .nav-tab {
      background: #041911;
      border: 1px solid var(--border-emerald);
      color: #a7f3d0;
      padding: 0.45rem 0.85rem;
      border-radius: 8px;
      font-size: 0.8rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s;
    }
    .nav-tab:hover { border-color: var(--accent-emerald); color: #fff; }
    .nav-tab.active {
      background: linear-gradient(135deg, #059669, #0d9488);
      border-color: #34d399;
      color: #fff;
      box-shadow: 0 0 12px rgba(16, 185, 129, 0.28);
    }

    .top-controls { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem; }
    .acc-pill {
      background: rgba(6, 78, 59, 0.65);
      border: 1px solid rgba(52, 211, 153, 0.4);
      color: #34d399;
      padding: 0.36rem 0.7rem;
      border-radius: 8px;
      font-size: 0.74rem;
      font-weight: 700;
    }
    .ctrl-select {
      background: #041911;
      border: 1px solid var(--border-emerald);
      color: #ecfdf5;
      padding: 0.38rem 0.65rem;
      border-radius: 8px;
      font-size: 0.78rem;
      cursor: pointer;
    }

    .container {
      width: 100%;
      max-width: 1380px;
      margin: 1rem auto 2rem auto;
      padding: 0 1.15rem;
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }
    .view-panel { display: none; flex-direction: column; gap: 1rem; }
    .view-panel.active { display: flex; }

    .emerald-card {
      background: linear-gradient(180deg, rgba(8, 38, 26, 0.96) 0%, rgba(5, 26, 18, 0.98) 100%);
      border: 1px solid var(--border-emerald);
      border-radius: 14px;
      padding: 1rem 1.2rem;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
    }

    /* Dataset Testing Suite Bar */
    .suite-top {
      display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 0.75rem;
      margin-bottom: 0.75rem;
    }
    .suite-title { font-size: 0.96rem; font-weight: 700; color: #ecfdf5; display: flex; align-items: center; gap: 0.5rem; }
    .chip-green {
      background: #064e3b; border: 1px solid #10b98155; color: #34d399;
      font-size: 0.68rem; padding: 0.16rem 0.55rem; border-radius: 999px; font-weight: 700;
    }
    .suite-actions { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; }
    .btn {
      border: 1px solid var(--border-emerald);
      background: #0a2d1f;
      color: #d1fae5;
      padding: 0.48rem 0.85rem;
      border-radius: 8px;
      font-size: 0.8rem;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex; align-items: center; gap: 0.4rem;
      transition: all 0.15s;
    }
    .btn:hover { border-color: #34d399; color: #fff; }
    .btn-cta {
      background: linear-gradient(135deg, #059669, #0891b2);
      border-color: #2dd4bf;
      color: #fff;
      font-weight: 700;
      padding: 0.52rem 1.05rem;
    }
    .btn-cta:hover { filter: brightness(1.08); }
    .btn-amber { background: #451a03; border-color: #f59e0b66; color: #fcd34d; }

    .filter-row {
      display: flex; flex-wrap: wrap; gap: 0.45rem; align-items: center; margin-bottom: 0.75rem;
    }
    .filter-pill {
      background: #041911; border: 1px solid #14532d; color: #a7f3d0;
      padding: 0.3rem 0.7rem; border-radius: 999px; font-size: 0.74rem; font-weight: 600; cursor: pointer;
    }
    .filter-pill.active { background: #059669; color: #fff; border-color: #34d399; }

    .suite-selector-grid {
      display: grid; grid-template-columns: 1.5fr 0.8fr 0.9fr 0.9fr; gap: 0.6rem;
      margin-bottom: 0.7rem;
    }
    @media (max-width: 960px) { .suite-selector-grid { grid-template-columns: 1fr 1fr; } }
    @media (max-width: 600px) { .suite-selector-grid { grid-template-columns: 1fr; } }

    .field-box label {
      display: block; font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.04em;
      color: var(--text-muted); margin-bottom: 0.25rem; font-weight: 700;
    }
    .field-box select, .field-box input[type="text"] {
      width: 100%; background: #03150e; border: 1px solid #14532d; color: #ecfdf5;
      padding: 0.48rem 0.65rem; border-radius: 8px; font-size: 0.82rem;
    }

    .markers-strip {
      display: grid; grid-template-columns: 1.2fr 1fr; gap: 0.75rem;
      background: #03160f; border: 1px solid #0f3f2c; border-radius: 10px; padding: 0.65rem 0.9rem;
      font-size: 0.78rem;
    }
    @media (max-width: 780px) { .markers-strip { grid-template-columns: 1fr; } }
    .markers-label { font-size: 0.66rem; color: var(--accent-emerald); text-transform: uppercase; font-weight: 700; margin-bottom: 0.2rem; }
    .markers-val { color: #d1fae5; line-height: 1.35; }

    .samples-drawer {
      display: none; grid-template-columns: repeat(auto-fill, minmax(175px, 1fr)); gap: 0.6rem;
      margin-top: 0.75rem;
    }
    .samples-drawer.open { display: grid; }
    .sample-mini-card {
      background: #041911; border: 1px solid #14532d; border-radius: 10px; padding: 0.45rem;
      cursor: pointer; transition: border-color 0.15s;
    }
    .sample-mini-card:hover, .sample-mini-card.active { border-color: var(--accent-cyan); }
    .sample-mini-card img { width: 100%; height: 82px; object-fit: cover; border-radius: 6px; margin-bottom: 0.35rem; }
    .sample-mini-title { font-size: 0.74rem; font-weight: 700; color: #ecfdf5; }

    /* Hero Diagnostic Card */
    .hero-grid { display: grid; grid-template-columns: 330px 1fr; gap: 1.25rem; align-items: start; }
    @media (max-width: 960px) { .hero-grid { grid-template-columns: 1fr; } }
    .leaf-frame {
      background: #03130d; border: 1px solid var(--border-emerald); border-radius: 12px;
      padding: 0.65rem; position: relative;
    }
    .leaf-top-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.45rem; font-size: 0.72rem; }
    .conf-badge {
      background: #059669; color: #fff; font-weight: 700; padding: 0.2rem 0.55rem; border-radius: 999px; font-size: 0.72rem;
    }
    .leaf-frame img {
      width: 100%; max-height: 270px; object-fit: contain; border-radius: 8px; background: #020c08; display: block;
    }
    .leaf-toggle-row { display: flex; gap: 0.4rem; margin-top: 0.5rem; }
    .mini-toggle {
      flex: 1; background: #07261a; border: 1px solid #14532d; color: #a7f3d0;
      font-size: 0.72rem; padding: 0.32rem; border-radius: 6px; cursor: pointer; font-weight: 600;
    }
    .mini-toggle.active { background: #065f46; border-color: #34d399; color: #fff; }
    .leaf-caption { font-size: 0.7rem; color: var(--text-muted); margin-top: 0.45rem; text-align: center; }

    .hero-badges { display: flex; flex-wrap: wrap; gap: 0.45rem; margin-bottom: 0.45rem; }
    .pill-sev {
      background: rgba(120, 53, 15, 0.55); border: 1px solid rgba(251, 191, 36, 0.45); color: #fde68a;
      font-size: 0.74rem; padding: 0.22rem 0.65rem; border-radius: 999px; font-weight: 700;
    }
    .pill-sev.healthy { background: rgba(6, 78, 59, 0.6); border-color: #34d39966; color: #6ee7b7; }
    .pill-sev.severe { background: rgba(127, 29, 29, 0.6); border-color: #f8717166; color: #fecaca; }
    .hero-title { font-size: 1.75rem; font-weight: 800; color: #fff; line-height: 1.2; margin-bottom: 0.2rem; }
    .hero-sci { font-size: 0.9rem; font-style: italic; color: #34d399; margin-bottom: 0.6rem; }
    .hero-desc { font-size: 0.88rem; color: #d1fae5; line-height: 1.5; margin-bottom: 0.85rem; }

    .kpi-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.65rem; margin-bottom: 0.85rem; }
    @media (max-width: 720px) { .kpi-3 { grid-template-columns: 1fr; } }
    .kpi-box {
      background: #03150e; border: 1px solid #134e35; border-radius: 10px; padding: 0.65rem 0.8rem;
    }
    .kpi-lbl { font-size: 0.66rem; text-transform: uppercase; color: var(--text-muted); font-weight: 700; margin-bottom: 0.25rem; }
    .kpi-val { font-size: 1.25rem; font-weight: 800; color: #34d399; }
    .kpi-val.amber { color: #fbbf24; }
    .kpi-val.cyan { color: #38bdf8; font-size: 1.02rem; }

    .hero-btn-row { display: flex; flex-wrap: wrap; gap: 0.55rem; margin-bottom: 0.75rem; }
    .audio-strip {
      background: #031a12; border: 1px solid #14532d; border-radius: 10px; padding: 0.6rem 0.85rem;
      display: flex; flex-direction: column; gap: 0.45rem;
    }
    .audio-strip-head { display: flex; justify-content: space-between; align-items: center; font-size: 0.78rem; color: #6ee7b7; font-weight: 700; }
    audio { width: 100%; height: 34px; }

    /* Certified Solution Card */
    .solution-head {
      display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 0.6rem;
      margin-bottom: 0.8rem;
    }
    .chem-banner {
      background: #041911; border: 1px solid #0e7490; border-radius: 12px; padding: 0.9rem 1rem;
      display: grid; grid-template-columns: 1.4fr repeat(3, 0.85fr); gap: 0.75rem; align-items: center;
      margin-bottom: 0.8rem;
    }
    @media (max-width: 900px) { .chem-banner { grid-template-columns: 1fr 1fr; } }
    @media (max-width: 550px) { .chem-banner { grid-template-columns: 1fr; } }
    .chem-sub-box {
      background: #03120d; border: 1px solid #134e35; border-radius: 8px; padding: 0.55rem 0.7rem;
    }
    .chem-sub-box .kpi-val { font-size: 0.92rem; color: #38bdf8; }

    .prognosis-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
    @media (max-width: 780px) { .prognosis-grid { grid-template-columns: 1fr; } }
    .info-box {
      background: #041911; border: 1px solid #134e35; border-radius: 10px; padding: 0.8rem;
    }
    .warn-box {
      background: rgba(69, 26, 3, 0.45); border: 1px solid rgba(245, 158, 11, 0.5); border-radius: 10px; padding: 0.8rem;
    }
    .danger-box {
      background: rgba(127, 29, 29, 0.45); border: 1px solid rgba(248, 113, 113, 0.55); border-radius: 12px; padding: 1rem;
    }

    /* Two-column Differential + Pathology Metrics */
    .analytics-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
    @media (max-width: 900px) { .analytics-2 { grid-template-columns: 1fr; } }
    .rank-row { margin-bottom: 0.6rem; }
    .rank-top { display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 0.25rem; }
    .rank-bar-bg { height: 7px; border-radius: 999px; background: #03130d; overflow: hidden; border: 1px solid #134e35; }
    .rank-bar-fill { height: 100%; background: linear-gradient(90deg, #10b981, #22d3ee); border-radius: 999px; }

    .metric-4 { display: grid; grid-template-columns: 1fr 1fr; gap: 0.6rem; }
    .metric-tile { background: #041911; border: 1px solid #134e35; border-radius: 10px; padding: 0.65rem 0.75rem; }
    .metric-num { font-size: 1.35rem; font-weight: 800; margin: 0.15rem 0; }

    /* Bottom 5-Tab Clinical Strip */
    .subtab-strip { display: flex; flex-wrap: wrap; gap: 0.45rem; border-bottom: 1px solid #134e35; padding-bottom: 0.7rem; margin-bottom: 0.85rem; }
    .subtab-btn {
      background: #041911; border: 1px solid #134e35; color: #a7f3d0;
      padding: 0.42rem 0.8rem; border-radius: 8px; font-size: 0.78rem; font-weight: 600; cursor: pointer;
    }
    .subtab-btn.active { background: #065f46; border-color: #34d399; color: #fff; }
    .subtab-pane { display: none; font-size: 0.86rem; line-height: 1.55; color: #d1fae5; }
    .subtab-pane.active { display: block; }
    .step-3 { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 0.75rem; }
    .step-box { background: #041911; border: 1px solid #134e35; border-radius: 10px; padding: 0.75rem; }

    /* Library, Agronomist Chat & Scan Log */
    .lib-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(290px, 1fr)); gap: 0.85rem; }
    .lib-card {
      background: #041911; border: 1px solid #134e35; border-radius: 12px; padding: 0.9rem;
      display: flex; flex-direction: column; gap: 0.45rem;
    }
    .chat-box {
      background: #03130d; border: 1px solid #134e35; border-radius: 12px; padding: 0.9rem;
      min-height: 220px; max-height: 420px; overflow-y: auto; display: flex; flex-direction: column; gap: 0.65rem;
    }
    .chat-msg { padding: 0.65rem 0.85rem; border-radius: 10px; font-size: 0.86rem; line-height: 1.5; max-width: 88%; }
    .chat-user { align-self: flex-end; background: #065f46; border: 1px solid #10b98166; color: #ecfdf5; }
    .chat-bot { align-self: flex-start; background: #08271b; border: 1px solid #14532d; color: #d1fae5; }
    .log-item {
      background: #041911; border: 1px solid #134e35; border-radius: 10px; padding: 0.7rem 0.9rem;
      display: flex; justify-content: space-between; align-items: center; gap: 0.75rem; cursor: pointer;
    }
    .log-item:hover { border-color: #34d399; }

    @media print {
      .telemetry-strip, header, .suite-card, .subtab-strip, .hero-btn-row { display: none !important; }
      body { background: #fff; color: #000; }
      .emerald-card { background: #fff; color: #000; border: 1px solid #ccc; }
    }
  </style>
</head>
<body>
  <!-- Hardware Telemetry Ribbon -->
  <div class="telemetry-strip">
    <div class="hw-left">
      <span class="live-dot"></span>
      <span id="hwStatusLine">CONNECTED TO ARM EDGE | Vision: Loading... | LLM: ExecuTorch</span>
    </div>
    <div class="hw-pills">
      <span class="hw-pill" id="hwClock">Clock: -- MHz</span>
      <span class="hw-pill cyan" id="hwPipe">Pipeline: -- ms</span>
      <span class="hw-pill" id="hwRam">RAM RSS: -- MB</span>
      <span class="hw-pill" id="hwTemp">SoC Temp: --</span>
    </div>
  </div>

  <!-- Header & Top Navigation -->
  <header>
    <div class="brand-group">
      <div class="brand-icon">🌿</div>
      <div>
        <div class="brand-title">
          <span id="uiBrandName">KisanDrishti AI</span>
          <span class="pro-badge">ExecuTorch + ONNX</span>
        </div>
        <div class="brand-sub" id="uiBrandSub">உழவர் பார்வை • किसान दृष्टि — Offline Clinical Agronomic Kiosk</div>
      </div>
    </div>

    <div class="nav-tabs">
      <button class="nav-tab active" onclick="switchView('analysis')" id="tabBtnAnalysis">🔬 AI Analysis</button>
      <button class="nav-tab" onclick="switchView('library')" id="tabBtnLibrary">📚 Disease Library (26)</button>
      <button class="nav-tab" onclick="switchView('agronomist')" id="tabBtnAgronomist">🦙 Agronomist AI</button>
      <button class="nav-tab" onclick="switchView('history')" id="tabBtnHistory">📋 Scan Log</button>
    </div>

    <div class="top-controls">
      <span class="acc-pill" id="uiAccPill">✔ 99.79% Vision Accuracy</span>
      <select class="ctrl-select" id="langSelect" onchange="onLanguageChange()">
        <option value="en" selected>English (ICAR Standard)</option>
        <option value="ta">தமிழ் (Tamil)</option>
        <option value="hi">हिन्दी (Hindi)</option>
      </select>
      <select class="ctrl-select" id="voicePresetSelect" onchange="onVoicePresetChange()">
        <option value="female|slow" selected>Neerja (Female • Slow)</option>
        <option value="female|normal">Neerja (Female • Normal)</option>
        <option value="male|slow">Prabhat (Male • Slow)</option>
        <option value="male|normal">Prabhat (Male • Normal)</option>
      </select>
    </div>
  </header>

  <div class="container">
    <!-- ==================== VIEW 1: AI ANALYSIS ==================== -->
    <div id="view-analysis" class="view-panel active">
      <!-- Dataset Testing Suite Card -->
      <div class="emerald-card suite-card">
        <div class="suite-top">
          <div class="suite-title">
            <span>🧪</span>
            <span id="uiSuiteTitle">Dataset Testing & Field Capture Suite</span>
            <span class="chip-green" id="uiModeBadge">Mode 1: Leaf + Mode 3: Pests</span>
          </div>
          <div class="suite-actions">
            <button class="btn" onclick="toggleSampleDrawer()" id="btnBrowseSamples">▦ Browse Sample Cards</button>
            <button class="btn" onclick="document.getElementById('leafFileInput').click()" id="btnUploadLeaf">📷 Upload Leaf Image</button>
            <button class="btn btn-amber" onclick="document.getElementById('pestFileInput').click()" id="btnUploadPest">🐛 Mode 3: Scan Insect Pest</button>
            <button class="btn btn-cta" onclick="runDiagnosis()" id="btnScanRun">🔬 Scan &amp; Run Diagnosis</button>
            <input type="file" id="leafFileInput" accept="image/*" style="display:none;" onchange="onCustomFileSelected(event, 'leaf')">
            <input type="file" id="pestFileInput" accept="image/*" style="display:none;" onchange="onCustomFileSelected(event, 'pest')">
          </div>
        </div>

        <div class="filter-row" id="cropFilterChips">
          <button class="filter-pill active" onclick="filterSamplesByCrop('All', this)">All Crops (6)</button>
          <button class="filter-pill" onclick="filterSamplesByCrop('Potato', this)">Potato</button>
          <button class="filter-pill" onclick="filterSamplesByCrop('Tomato', this)">Tomato</button>
          <button class="filter-pill" onclick="filterSamplesByCrop('Rice', this)">Rice</button>
          <button class="filter-pill" onclick="filterSamplesByCrop('Corn', this)">Corn</button>
        </div>

        <div class="suite-selector-grid">
          <div class="field-box">
            <label id="lblSampleSelect">Select Testing Sample or Upload Image</label>
            <select id="sampleSelect" onchange="onSampleSelected()"></select>
          </div>
          <div class="field-box">
            <label id="lblCropGuard">Gate A Selected Crop</label>
            <select id="cropSelect">
              <option value="Potato">Potato</option>
              <option value="Tomato">Tomato</option>
              <option value="Rice">Rice</option>
              <option value="Corn">Corn</option>
            </select>
          </div>
          <div class="field-box">
            <label id="lblStateGuard">State / Region (Gate B)</label>
            <select id="stateSelect" onchange="populateDistricts()"></select>
          </div>
          <div class="field-box">
            <label id="lblDistrictGuard">District Verification</label>
            <select id="districtSelect"></select>
          </div>
        </div>

        <div class="markers-strip">
          <div>
            <div class="markers-label" id="lblMarkersHead">Clinical Field Markers</div>
            <div class="markers-val" id="selectedMarkersText">Select a sample or upload a photo to analyze crop disease or insect pests offline.</div>
          </div>
          <div>
            <div class="markers-label" id="lblExpectedHead">Expected Class / Selected File</div>
            <div class="markers-val" id="selectedExpectedText">-</div>
          </div>
        </div>

        <div class="samples-drawer" id="samplesDrawer"></div>
      </div>

      <!-- Loading / Gate A Alert Box -->
      <div id="statusAlertBox" style="display:none;"></div>

      <!-- Hero Clinical Diagnostic Split Card -->
      <div class="emerald-card" id="heroDiagnosticCard" style="display:none;">
        <div class="hero-grid">
          <div class="leaf-frame">
            <div class="leaf-top-row">
              <span style="font-weight:700; color:#a7f3d0;" id="lblScannedImg">Scanned Specimen</span>
              <span class="conf-badge" id="heroConfBadge">100.0% Confidence</span>
            </div>
            <img id="heroPreviewImg" src="" alt="Specimen">
            <div class="leaf-toggle-row">
              <button class="mini-toggle active" id="btnShowAnnotated" onclick="toggleLeafView('annotated')">Severity Overlay</button>
              <button class="mini-toggle" id="btnShowOriginal" onclick="toggleLeafView('original')">Original Photo</button>
            </div>
            <div class="leaf-caption" id="heroVisionCaption">ONNXRuntime • 0.0 ms</div>
          </div>

          <div>
            <div class="hero-badges">
              <span class="chip-green" id="heroModePill">Mode 1: Leaf Disease</span>
              <span class="pill-sev" id="heroSeverityPill">Severity: Moderate</span>
              <span class="chip-green" id="heroGateBPill">ICAR / TNAU Verified</span>
            </div>
            <h1 class="hero-title" id="heroTitle">-</h1>
            <div class="hero-sci" id="heroSci">-</div>
            <p class="hero-desc" id="heroDesc">-</p>

            <div class="kpi-3">
              <div class="kpi-box">
                <div class="kpi-lbl" id="lblKpiConf">AI Confidence Score</div>
                <div class="kpi-val" id="kpiConfVal">0%</div>
              </div>
              <div class="kpi-box">
                <div class="kpi-lbl" id="lblKpiSev">Affected Surface Area (S%)</div>
                <div class="kpi-val amber" id="kpiSevVal">0.0%</div>
              </div>
              <div class="kpi-box">
                <div class="kpi-lbl" id="lblKpiTaxon">Pathogen / Pest Taxon</div>
                <div class="kpi-val cyan" id="kpiTaxonVal">-</div>
              </div>
            </div>

            <div class="hero-btn-row">
              <button class="btn btn-cta" onclick="openAgronomistWithContext()" id="btnAskAgronomist">🦙 Ask AI Agronomist About Treatment</button>
              <button class="btn" onclick="window.print()" id="btnPrintReport">🖨 Print Diagnostic Report</button>
            </div>

            <div class="audio-strip">
              <div class="audio-strip-head">
                <span id="audioStripLabel">🔊 Spoken Neural Advisory (Offline Sherpa-ONNX)</span>
                <span id="audioBackendBadge" style="font-size:0.7rem; color:#6ee7b7aa;">-</span>
              </div>
              <audio id="audioPlayer" controls></audio>
            </div>
          </div>
        </div>
      </div>

      <!-- Certified Clinical Solution Card -->
      <div class="emerald-card" id="clinicalSolutionCard" style="display:none;">
        <div class="solution-head">
          <div>
            <h2 style="font-size:1.08rem; color:#fff;" id="lblSolutionTitle">Certified Clinical Solution &amp; Gate B Prognosis</h2>
            <div style="font-size:0.76rem; color:var(--text-muted);" id="lblSolutionSub">Deterministic ICAR / TNAU / CIBRC static SQLite dosage — zero LLM dosage hallucination</div>
          </div>
          <div style="display:flex; gap:0.45rem; flex-wrap:wrap;">
            <span class="pill-sev" id="phiPillBadge">PHI: --</span>
            <span class="chip-green" id="sourcePillBadge">Source: ICAR/TNAU</span>
          </div>
        </div>

        <div id="chemicalSectionContainer"></div>

        <div class="prognosis-grid">
          <div class="info-box">
            <div class="markers-label" id="lblCulturalBox">1. Immediate Cultural Action (Zero-Cost Physical Step)</div>
            <div class="markers-val" id="culturalTextBox">-</div>
          </div>
          <div class="warn-box" id="organicWarnBox">
            <div class="markers-label" style="color:#fbbf24;" id="lblOrganicBox">2. Low-Cost Organic Remedy &amp; Field Note</div>
            <div class="markers-val" id="organicTextBox">-</div>
          </div>
        </div>
      </div>

      <!-- Differential Ranking + Pathology Metrics Split -->
      <div class="analytics-2" id="analyticsSplitRow" style="display:none;">
        <div class="emerald-card">
          <h3 style="font-size:0.96rem; margin-bottom:0.75rem; color:#fff;" id="lblDiffTitle">Multi-Class Differential Diagnosis Ranking</h3>
          <div id="diffBarsContainer"></div>
        </div>
        <div class="emerald-card">
          <h3 style="font-size:0.96rem; margin-bottom:0.75rem; color:#fff;" id="lblPathMetricsTitle">Vision Pathology Metrics (OpenCV Arm NEON HSV)</h3>
          <div class="metric-4" id="pathologyMetricsGrid"></div>
        </div>
      </div>

      <!-- 5-Tab Bottom Detail Strip -->
      <div class="emerald-card" id="bottomDetailTabs" style="display:none;">
        <div class="subtab-strip">
          <button class="subtab-btn active" onclick="switchSubTab('llama', this)" id="stLlama">🦙 Meta Llama 3.2 (ExecuTorch) Advisory</button>
          <button class="subtab-btn" onclick="switchSubTab('action', this)" id="stAction">🛡 Action Plan &amp; Steps</button>
          <button class="subtab-btn" onclick="switchSubTab('checklist', this)" id="stChecklist">🔍 Symptoms Checklist</button>
          <button class="subtab-btn" onclick="switchSubTab('script', this)" id="stScript">🔊 Spoken Audio Transcript</button>
          <button class="subtab-btn" onclick="switchSubTab('audit', this)" id="stAudit">⚙ Gate A/B &amp; Hardware Audit</button>
        </div>
        <div id="subtab-llama" class="subtab-pane active"></div>
        <div id="subtab-action" class="subtab-pane"></div>
        <div id="subtab-checklist" class="subtab-pane"></div>
        <div id="subtab-script" class="subtab-pane"></div>
        <div id="subtab-audit" class="subtab-pane"></div>
      </div>
    </div>

    <!-- ==================== VIEW 2: DISEASE LIBRARY ==================== -->
    <div id="view-library" class="view-panel">
      <div class="emerald-card">
        <div class="suite-top">
          <div class="suite-title">📚 <span id="lblLibTitle">ICAR / TNAU / CIBRC Verified Disease &amp; Pest Library (26 Records)</span></div>
          <input type="text" id="libSearchInput" placeholder="Search crop, disease, pathogen, or chemical..." oninput="renderLibraryGrid()"
                 style="background:#03150e; border:1px solid #14532d; color:#fff; padding:0.45rem 0.75rem; border-radius:8px; width:280px;">
        </div>
        <div class="filter-row" id="libCropFilterRow">
          <button class="filter-pill active" onclick="setLibFilter('All', this)">All (26)</button>
          <button class="filter-pill" onclick="setLibFilter('Potato', this)">Potato</button>
          <button class="filter-pill" onclick="setLibFilter('Tomato', this)">Tomato</button>
          <button class="filter-pill" onclick="setLibFilter('Rice', this)">Rice</button>
          <button class="filter-pill" onclick="setLibFilter('Corn', this)">Corn</button>
          <button class="filter-pill" onclick="setLibFilter('Pest', this)">Insect Pests (6)</button>
        </div>
        <div class="lib-grid" id="libGridContainer"></div>
      </div>
    </div>

    <!-- ==================== VIEW 3: AGRONOMIST AI (VOICE & TEXT Q&A) ==================== -->
    <div id="view-agronomist" class="view-panel">
      <div class="emerald-card">
        <div class="suite-top">
          <div>
            <div class="suite-title">🦙 <span id="lblAgroTabTitle">Meta Llama 3.2 (ExecuTorch) Agronomist &amp; Live Voice Q&amp;A</span></div>
            <div style="font-size:0.78rem; color:var(--text-muted); margin-top:0.2rem;" id="qaContextBanner">
              Active Context: Run or load a leaf/pest scan first, or ask a general question offline.
            </div>
          </div>
          <span class="hw-pill cyan" id="qaStatusBadge">Whisper-Base INT8 + ExecuTorch</span>
        </div>

        <div class="filter-row" style="margin-top:0.4rem;">
          <button class="filter-pill" onclick="askPresetQA('What organic spray should I use for this condition?')">Organic Remedy?</button>
          <button class="filter-pill" onclick="askPresetQA('What immediate physical step should I do today in my field?')">Immediate Action?</button>
          <button class="filter-pill" onclick="askPresetQA('What is the Pre-Harvest Safety Interval (PHI) before harvesting?')">Safety Interval (PHI)?</button>
          <button class="filter-pill" onclick="askPresetQA('How does this affect beneficial insects and bees?')">Pollinator Safety?</button>
        </div>

        <div class="chat-box" id="qaChatHistory">
          <div class="chat-msg chat-bot">
            Hello! I am KisanDrishti AI running Meta Llama 3.2 1B-Instruct via <b>ExecuTorch</b> offline. Speak using the microphone or type any follow-up question about the diagnosed crop condition.
          </div>
        </div>

        <div style="display:flex; gap:0.55rem; flex-wrap:wrap; margin-top:0.8rem;">
          <button id="btnMic" class="btn btn-cta" style="background:#047857;" onclick="toggleMicRecording()">🎤 Speak Question</button>
          <input id="qaTextInput" type="text" placeholder="Type follow-up question in English, Tamil, or Hindi..."
                 onkeydown="if(event.key==='Enter') submitTextQA()"
                 style="flex:1; min-width:240px; background:#03150e; border:1px solid #14532d; color:#fff; padding:0.55rem 0.8rem; border-radius:8px;">
          <button class="btn btn-cta" onclick="submitTextQA()" id="btnSendQA">Send</button>
        </div>

        <div id="qaAudioWrap" style="display:none; margin-top:0.75rem;" class="audio-strip">
          <div class="audio-strip-head"><span>🔊 Spoken Agronomist Reply</span><span id="qaAudioMeta"></span></div>
          <audio id="qaAudioPlayer" controls></audio>
        </div>
      </div>
    </div>

    <!-- ==================== VIEW 4: SCAN LOG ==================== -->
    <div id="view-history" class="view-panel">
      <div class="emerald-card">
        <div class="suite-top">
          <div class="suite-title">📋 <span>On-Device Persistent Scan Diagnostic Log</span></div>
          <button class="btn" onclick="clearScanLog()">🗑 Clear Log</button>
        </div>
        <div id="scanLogList" style="display:flex; flex-direction:column; gap:0.6rem;"></div>
      </div>
    </div>
  </div>

  <script>
    const I18N = {
      en: {
        tabAnalysis: "🔬 AI Analysis",
        tabLibrary: "📚 Disease Library (26)",
        tabAgronomist: "🦙 Agronomist AI",
        tabHistory: "📋 Scan Log",
        suiteTitle: "Dataset Testing & Field Capture Suite",
        uploadLeaf: "📷 Upload Leaf Image",
        uploadPest: "🐛 Mode 3: Scan Insect Pest",
        scanRun: "🔬 Scan & Run Diagnosis",
        browse: "▦ Browse Sample Cards",
        kpiConf: "AI Confidence Score",
        kpiSev: "Affected Surface Area (S%)",
        kpiTaxon: "Pathogen / Pest Taxon",
        askAgro: "🦙 Ask AI Agronomist About Treatment",
        printBtn: "🖨 Print Diagnostic Report",
        solutionTitle: "Certified Clinical Solution & Gate B Prognosis",
        diffTitle: "Multi-Class Differential Diagnosis Ranking",
        pathTitle: "Vision Pathology Metrics (OpenCV Arm NEON HSV)",
        culturalBox: "1. Immediate Cultural Action (Zero-Cost Physical Step)",
        organicBox: "2. Low-Cost Organic Remedy & Field Note"
      },
      ta: {
        tabAnalysis: "🔬 AI நோய் ஆய்வு",
        tabLibrary: "📚 நோய் அறிவு நூலகம் (26)",
        tabAgronomist: "🦙 வேளாண் AI ஆலோசகர்",
        tabHistory: "📋 ஆய்வுப் பதிவுகள்",
        suiteTitle: "மாதிரி இலை & களப் பட ஆய்வுத் தொகுப்பு",
        uploadLeaf: "📷 இலைப் படம் பதிவேற்று",
        uploadPest: "🐛 பூச்சி ஆய்வு (Mode 3)",
        scanRun: "🔬 ஆய்வு செய்து பரிந்துரை பெறுக",
        browse: "▦ மாதிரி இலைகளைக் காண்க",
        kpiConf: "AI கண்டறிதல் துல்லியம்",
        kpiSev: "பாதிக்கப்பட்ட இலைப் பரப்பு (S%)",
        kpiTaxon: "நோய்க்காரணி / பூச்சி இனம்",
        askAgro: "🦙 சிகிச்சை குறித்து AI-யிடம் கேட்க",
        printBtn: "🖨 மருத்துவ அறிக்கை அச்சிடு",
        solutionTitle: "சான்றளிக்கப்பட்ட வேளாண் தீர்வு (ICAR / TNAU / CIBRC)",
        diffTitle: "பல்வகை நோய் ஒப்பீட்டுத் தரவரிசை",
        pathTitle: "இலை பாதிப்பு அளவீடுகள் (OpenCV Arm NEON HSV)",
        culturalBox: "1. உடனடி வேளாண் பராமரிப்பு (செலவில்லாத நேரடி நடவடிக்கை)",
        organicBox: "2. இயற்கை மற்றும் உயிரியல் கட்டுப்பாடு"
      },
      hi: {
        tabAnalysis: "🔬 AI रोग विश्लेषण",
        tabLibrary: "📚 रोग ज्ञान पुस्तकालय (26)",
        tabAgronomist: "🦙 कृषि AI सलाहकार",
        tabHistory: "📋 जांच लॉग",
        suiteTitle: "डेटासेट परीक्षण और खेत छवि विश्लेषण",
        uploadLeaf: "📷 पत्ती की फोटो अपलोड करें",
        uploadPest: "🐛 कीट जांच (Mode 3)",
        scanRun: "🔬 स्कैन और निदान चलाएं",
        browse: "▦ नमूना पत्तियां देखें",
        kpiConf: "AI पहचान सटीकता",
        kpiSev: "प्रभावित पत्ती क्षेत्र (S%)",
        kpiTaxon: "रोगजनक / कीट वैज्ञानिक नाम",
        askAgro: "🦙 उपचार के बारे में AI से पूछें",
        printBtn: "🖨 निदान रिपोर्ट प्रिंट करें",
        solutionTitle: "प्रमाणित कृषि उपचार एवं सुरक्षा जांच (Gate B)",
        diffTitle: "बहु-वर्ग तुलनात्मक निदान रैंकिंग",
        pathTitle: "पत्ती संक्रमण मीट्रिक्स (OpenCV Arm NEON HSV)",
        culturalBox: "1. तत्काल कृषि कार्य (शून्य-लागत भौतिक उपाय)",
        organicBox: "2. जैविक एवं प्राकृतिक उपचार"
      }
    };

    let allSamples = [];
    let filteredCrop = "All";
    let regionsMap = {};
    let uploadedFile = null;
    let uploadedMode = "leaf";
    let lastResult = null;
    let leafViewMode = "annotated";
    let libraryItems = [];
    let libFilter = "All";
    let scanHistory = [];
    try { scanHistory = JSON.parse(localStorage.getItem("kisandrishti_logs_v2") || "[]"); } catch (e) { scanHistory = []; }

    let micRecording = false, mediaStream = null, audioCtx = null, scriptNode = null, pcmChunks = [];

    function getVoiceSettings() {
      const [voice, speed] = (document.getElementById("voicePresetSelect").value || "female|slow").split("|");
      return { voice, speed };
    }

    async function initDashboard() {
      try {
        const [sampRes, regRes, telRes] = await Promise.all([
          fetch("/api/samples"), fetch("/api/regions"), fetch("/api/telemetry")
        ]);
        allSamples = await sampRes.json();
        regionsMap = await regRes.json();
        const tel = await telRes.json();
        updateTelemetryBar(tel);

        const stateSel = document.getElementById("stateSelect");
        Object.keys(regionsMap).forEach(st => {
          const opt = document.createElement("option");
          opt.value = st; opt.textContent = st;
          stateSel.appendChild(opt);
        });
        populateDistricts();
        renderSamplesUI();
        renderScanLog();
        await loadLibrary();
        // Run initial sample scan cleanly on open so dashboard immediately displays real telemetry & inference
        await runDiagnosis();
      } catch (e) {
        console.error("Init error:", e);
      }
    }

    function updateTelemetryBar(tel) {
      if (!tel) return;
      const t = tel.telemetry || tel;
      const vision = tel.vision_backend || "ONNXRuntime";
      const llm = tel.llm_backend || "ExecuTorch";
      document.getElementById("hwStatusLine").textContent =
        `CONNECTED TO ${t.platform || "ARM EDGE"} | Vision: ${vision} | LLM: ${llm}`;
      document.getElementById("hwClock").textContent =
        `Clock: ${t.cpu_freq_mhz ? t.cpu_freq_mhz + " MHz" : "Arm Edge"}`;
      document.getElementById("hwRam").textContent =
        `RAM RSS: ${t.process_rss_mb || "--"} MB`;
      document.getElementById("hwTemp").textContent =
        `SoC Temp: ${t.soc_temp_c !== null && t.soc_temp_c !== undefined ? t.soc_temp_c + " °C" : "N/A"}`;
    }

    function populateDistricts() {
      const st = document.getElementById("stateSelect").value;
      const distSel = document.getElementById("districtSelect");
      distSel.innerHTML = "";
      (regionsMap[st] || ["All Districts"]).forEach(d => {
        const opt = document.createElement("option");
        opt.value = d; opt.textContent = d;
        distSel.appendChild(opt);
      });
    }

    function filterSamplesByCrop(crop, btn) {
      filteredCrop = crop;
      document.querySelectorAll("#cropFilterChips .filter-pill").forEach(b => b.classList.remove("active"));
      if (btn) btn.classList.add("active");
      renderSamplesUI();
    }

    function renderSamplesUI() {
      const sel = document.getElementById("sampleSelect");
      const drawer = document.getElementById("samplesDrawer");
      const list = filteredCrop === "All" ? allSamples : allSamples.filter(s => s.crop === filteredCrop);
      sel.innerHTML = "";
      drawer.innerHTML = "";

      list.forEach(s => {
        const opt = document.createElement("option");
        opt.value = s.id; opt.textContent = `${s.crop} — ${s.title}`;
        sel.appendChild(opt);

        const card = document.createElement("div");
        card.className = "sample-mini-card";
        card.innerHTML = `<img src="/static/samples/${s.file}" alt="${s.title}"><div class="sample-mini-title">${s.title}</div>`;
        card.onclick = () => {
          uploadedFile = null;
          sel.value = s.id;
          onSampleSelected();
          toggleSampleDrawer(false);
          runDiagnosis();
        };
        drawer.appendChild(card);
      });
      onSampleSelected();
    }

    function onSampleSelected() {
      uploadedFile = null;
      uploadedMode = "leaf";
      const id = document.getElementById("sampleSelect").value;
      const s = allSamples.find(x => x.id === id) || allSamples[0];
      if (!s) return;
      document.getElementById("cropSelect").value = s.crop;
      document.getElementById("selectedMarkersText").textContent = s.markers;
      document.getElementById("selectedExpectedText").textContent = s.expected;
    }

    function onCustomFileSelected(evt, mode) {
      const f = evt.target.files[0];
      if (!f) return;
      uploadedFile = f;
      uploadedMode = mode;
      document.getElementById("selectedMarkersText").textContent =
        mode === "pest"
          ? `Mode 3 Insect Close-Up selected (${f.name}). Ready for pest MobileNetV3 screening + ExecuTorch advisory.`
          : `Custom field image selected (${f.name}). Gate A blur, foliage & crop check will execute on scan.`;
      document.getElementById("selectedExpectedText").textContent = `Uploaded File: ${f.name}`;
      if (mode === "pest") runDiagnosis();
    }

    function toggleSampleDrawer(forceVal) {
      const el = document.getElementById("samplesDrawer");
      if (typeof forceVal === "boolean") el.classList.toggle("open", forceVal);
      else el.classList.toggle("open");
    }

    function applyUILanguage() {
      const lang = document.getElementById("langSelect").value;
      const t = I18N[lang] || I18N.en;
      document.getElementById("tabBtnAnalysis").textContent = t.tabAnalysis;
      document.getElementById("tabBtnLibrary").textContent = t.tabLibrary;
      document.getElementById("tabBtnAgronomist").textContent = t.tabAgronomist;
      document.getElementById("tabBtnHistory").textContent = t.tabHistory;
      document.getElementById("uiSuiteTitle").textContent = t.suiteTitle;
      document.getElementById("btnUploadLeaf").textContent = t.uploadLeaf;
      document.getElementById("btnUploadPest").textContent = t.uploadPest;
      document.getElementById("btnScanRun").textContent = t.scanRun;
      document.getElementById("btnBrowseSamples").textContent = t.browse;
      document.getElementById("lblKpiConf").textContent = t.kpiConf;
      document.getElementById("lblKpiSev").textContent = t.kpiSev;
      document.getElementById("lblKpiTaxon").textContent = t.kpiTaxon;
      document.getElementById("btnAskAgronomist").textContent = t.askAgro;
      document.getElementById("btnPrintReport").textContent = t.printBtn;
      document.getElementById("lblSolutionTitle").textContent = t.solutionTitle;
      document.getElementById("lblDiffTitle").textContent = t.diffTitle;
      document.getElementById("lblPathMetricsTitle").textContent = t.pathTitle;
      document.getElementById("lblCulturalBox").textContent = t.culturalBox;
      document.getElementById("lblOrganicBox").textContent = t.organicBox;
    }

    async function onLanguageChange() {
      applyUILanguage();
      await loadLibrary();
      await runDiagnosis();
    }

    async function onVoicePresetChange() {
      await runDiagnosis();
    }

    async function runDiagnosis() {
      const alertBox = document.getElementById("statusAlertBox");
      alertBox.style.display = "block";
      alertBox.className = "emerald-card";
      alertBox.innerHTML = "⏳ Running ONNX / ExecuTorch offline pipeline on edge processor...";

      const { voice, speed } = getVoiceSettings();
      const fd = new FormData();
      fd.append("crop", document.getElementById("cropSelect").value);
      fd.append("lang", document.getElementById("langSelect").value);
      fd.append("voice", voice);
      fd.append("voice_speed", speed);
      fd.append("state", document.getElementById("stateSelect").value);
      fd.append("district", document.getElementById("districtSelect").value);

      let endpoint = "/api/diagnose";
      if (uploadedFile) {
        fd.append("file", uploadedFile);
        if (uploadedMode === "pest") endpoint = "/api/diagnose-pest";
      } else {
        fd.append("sample_name", document.getElementById("sampleSelect").value);
      }

      try {
        const res = await fetch(endpoint, { method: "POST", body: fd });
        const data = await res.json();
        if (data.status === "GATE_A_REJECTED" || data.error) {
          showGateARejection(data);
          return;
        }
        alertBox.style.display = "none";
        lastResult = data;
        saveToScanLog(data);
        renderDiagnosisResult(data);
      } catch (e) {
        alertBox.className = "danger-box";
        alertBox.innerHTML = `<b>Error:</b> ${e.message}`;
      }
    }

    function showGateARejection(data) {
      const alertBox = document.getElementById("statusAlertBox");
      alertBox.style.display = "block";
      alertBox.className = "danger-box";
      alertBox.innerHTML = `
        <h3 style="color:#fecaca; margin-bottom:0.35rem;">⚠ Gate A Pre-Screening Halt (${data.reason || "REJECTED"})</h3>
        <p style="font-size:0.88rem; color:#fee2e2; margin-bottom:0.5rem;">${data.message || data.error}</p>
        ${data.selected_crop ? `<div style="font-size:0.78rem; color:#fca5a5;">Selected: <b>${data.selected_crop}</b> | Detected: <b>${data.diagnosed_crop}</b></div>` : ""}
      `;
      ["heroDiagnosticCard", "clinicalSolutionCard", "analyticsSplitRow", "bottomDetailTabs"].forEach(id => {
        document.getElementById(id).style.display = "none";
      });
    }

    function toggleLeafView(mode) {
      leafViewMode = mode;
      document.getElementById("btnShowAnnotated").classList.toggle("active", mode === "annotated");
      document.getElementById("btnShowOriginal").classList.toggle("active", mode === "original");
      if (!lastResult) return;
      document.getElementById("heroPreviewImg").src =
        mode === "annotated" ? lastResult.annotated_image_url : lastResult.original_image_url;
    }

    function renderDiagnosisResult(d) {
      document.getElementById("heroDiagnosticCard").style.display = "block";
      document.getElementById("clinicalSolutionCard").style.display = "block";
      document.getElementById("analyticsSplitRow").style.display = "grid";
      document.getElementById("bottomDetailTabs").style.display = "block";

      if (d.telemetry) {
        document.getElementById("hwPipe").textContent = `Pipeline: ${d.total_latency_ms} ms`;
        document.getElementById("hwRam").textContent = `RAM RSS: ${d.telemetry.process_rss_mb} MB`;
        document.getElementById("hwTemp").textContent =
          `SoC Temp: ${d.telemetry.soc_temp_c !== null && d.telemetry.soc_temp_c !== undefined ? d.telemetry.soc_temp_c + " °C" : "N/A"}`;
      }

      document.getElementById("heroConfBadge").textContent = `${d.confidence}% Confidence`;
      leafViewMode = "annotated";
      toggleLeafView("annotated");
      document.getElementById("heroVisionCaption").textContent =
        `${d.vision_backend || "ONNXRuntime"} • ${d.vision_latency_ms || 0} ms`;

      document.getElementById("heroModePill").textContent = d.mode || "Mode 1: Leaf Diagnostics";
      const sevPill = document.getElementById("heroSeverityPill");
      sevPill.textContent = d.prescription_card?.severity_display || `${d.severity_pct}% (${d.severity_stage})`;
      sevPill.className = "pill-sev " + (d.severity_stage === "Healthy" ? "healthy" : (d.severity_stage === "Severe" ? "severe" : ""));
      document.getElementById("heroGateBPill").textContent = d.gate_b_passed ? "✔ Gate B Authorized" : "⚠ Gate B Suppressed";

      const cleanTitle = `${d.crop === "Pest" ? "Pest" : d.crop}: ${String(d.disease || "").replace(/_/g, " ")}`;
      document.getElementById("heroTitle").textContent = cleanTitle;
      document.getElementById("heroSci").textContent = d.pathogen_scientific ? `Scientific Name: ${d.pathogen_scientific}` : "";
      document.getElementById("heroDesc").textContent = d.llama_explanation || "";

      document.getElementById("kpiConfVal").textContent = `${d.confidence}%`;
      document.getElementById("kpiSevVal").textContent = `${d.severity_pct}%`;
      document.getElementById("kpiTaxonVal").textContent = d.pathogen_scientific || d.disease.replace(/_/g, " ");

      const audioEl = document.getElementById("audioPlayer");
      if (d.audio_url) {
        audioEl.style.display = "block";
        audioEl.src = d.audio_url;
      } else {
        audioEl.style.display = "none";
      }
      document.getElementById("audioBackendBadge").textContent = d.audio_backend || "offline";

      // Clinical Solution Card
      const card = d.prescription_card || { sections: [] };
      const chemSec = card.sections.find(s => s.type === "chemical");
      const suppSec = card.sections.find(s => s.type === "suppressed");
      const cultSec = card.sections.find(s => s.type === "cultural");
      const orgSec = card.sections.find(s => s.type === "organic");

      document.getElementById("culturalTextBox").textContent = cultSec ? cultSec.content : "-";
      document.getElementById("organicTextBox").textContent = orgSec ? orgSec.content : "-";

      const chemContainer = document.getElementById("chemicalSectionContainer");
      if (chemSec) {
        document.getElementById("phiPillBadge").textContent = `PHI: ${chemSec.phi}`;
        document.getElementById("sourcePillBadge").textContent = chemSec.source_citation;
        chemContainer.innerHTML = `
          <div class="chem-banner">
            <div>
              <div class="markers-label" style="color:#38bdf8;">Prescribed Regulatory Compound (SQLite)</div>
              <div style="font-size:1.1rem; font-weight:800; color:#fff; margin-bottom:0.2rem;">${chemSec.chemical_name}</div>
              <div style="font-size:0.78rem; color:#bae6fd;">${chemSec.bio_compatibility_note || ""}</div>
            </div>
            <div class="chem-sub-box">
              <div class="kpi-lbl">Exact Dilution &amp; Dosage</div>
              <div class="kpi-val">${chemSec.dosage}</div>
            </div>
            <div class="chem-sub-box">
              <div class="kpi-lbl">Pre-Harvest Interval (PHI)</div>
              <div class="kpi-val">${chemSec.phi}</div>
            </div>
            <div class="chem-sub-box">
              <div class="kpi-lbl">Regulatory Source</div>
              <div class="kpi-val">${chemSec.source_citation}</div>
            </div>
          </div>
        `;
      } else {
        document.getElementById("phiPillBadge").textContent = "PHI: N/A";
        document.getElementById("sourcePillBadge").textContent = d.gate_b_passed ? "Organic Only" : "Gate B Halted";
        chemContainer.innerHTML = `
          <div class="warn-box" style="margin-bottom:0.8rem;">
            <b style="color:#fde68a;">Gate B Status:</b> ${suppSec ? suppSec.content : "Cultural and biological control sufficient."}
          </div>
        `;
      }

      // Differential Ranking Bars
      const diffEl = document.getElementById("diffBarsContainer");
      const cands = d.top_candidates || [];
      diffEl.innerHTML = cands.length
        ? cands.map((c, idx) => `
            <div class="rank-row">
              <div class="rank-top">
                <span style="color:${idx === 0 ? "#fff" : "#a7f3d0"}; font-weight:${idx === 0 ? "700" : "500"};">${c.label}</span>
                <span style="color:#34d399; font-weight:700;">${c.probability_pct}%</span>
              </div>
              <div class="rank-bar-bg"><div class="rank-bar-fill" style="width:${c.probability_pct}%;"></div></div>
            </div>
          `).join("")
        : `<div style="font-size:0.82rem; color:var(--text-muted);">Top prediction: ${cleanTitle} (${d.confidence}%)</div>`;

      // Vision Pathology Metrics
      const pm = d.pathology_metrics || {};
      document.getElementById("pathologyMetricsGrid").innerHTML = `
        <div class="metric-tile">
          <div class="kpi-lbl">Leaf Isolation Mask</div>
          <div class="metric-num" style="color:#38bdf8;">${pm.leaf_isolation_pct ?? 0}%</div>
          <div style="font-size:0.72rem; color:var(--text-muted);">Segmented blade</div>
        </div>
        <div class="metric-tile">
          <div class="kpi-lbl">Healthy Chlorophyll</div>
          <div class="metric-num" style="color:#34d399;">${pm.healthy_pct ?? 0}%</div>
          <div style="font-size:0.72rem; color:var(--text-muted);">Intact green tissue</div>
        </div>
        <div class="metric-tile">
          <div class="kpi-lbl">Chlorosis Yellowing</div>
          <div class="metric-num" style="color:#fbbf24;">${pm.chlorosis_pct ?? 0}%</div>
          <div style="font-size:0.72rem; color:var(--text-muted);">Early stress halo</div>
        </div>
        <div class="metric-tile">
          <div class="kpi-lbl">Necrotic Lesion Area</div>
          <div class="metric-num" style="color:#f87171;">${pm.necrosis_pct ?? 0}%</div>
          <div style="font-size:0.72rem; color:var(--text-muted);">HSV severity S=${d.severity_pct}%</div>
        </div>
      `;

      // Bottom 5 Detail Tabs
      const lm = d.llm_metrics || {};
      document.getElementById("subtab-llama").innerHTML = `
        <div style="display:flex; flex-wrap:wrap; gap:0.45rem; margin-bottom:0.6rem;">
          <span class="chip-green">Runtime: ${lm.backend || "ExecuTorch"}</span>
          <span class="hw-pill cyan">TTFT: ${lm.ttft_ms ?? "--"} ms</span>
          <span class="hw-pill">Speed: ${lm.tokens_per_sec ?? "--"} tok/s</span>
          <span class="hw-pill">Tokens: ${lm.tokens_generated ?? 0}</span>
        </div>
        <p style="font-size:0.92rem; color:#fff; background:#03150e; border:1px solid #134e35; border-radius:10px; padding:0.85rem;">${d.llama_explanation || "-"}</p>
      `;

      document.getElementById("subtab-action").innerHTML = `
        <div class="step-3">
          <div class="step-box"><b style="color:#34d399;">Step 1 — Cultural Sanitation</b><p style="margin-top:0.35rem;">${cultSec ? cultSec.content : "-"}</p></div>
          <div class="step-box"><b style="color:#fbbf24;">Step 2 — Organic Bio-Control</b><p style="margin-top:0.35rem;">${orgSec ? orgSec.content : "-"}</p></div>
          <div class="step-box"><b style="color:#38bdf8;">Step 3 — Regulatory Protocol</b><p style="margin-top:0.35rem;">${chemSec ? `${chemSec.chemical_name} @ ${chemSec.dosage} (PHI: ${chemSec.phi})` : (suppSec ? suppSec.content : "Not required")}</p></div>
        </div>
      `;

      const checklist = d.symptom_checklist || [];
      document.getElementById("subtab-checklist").innerHTML = checklist.length
        ? checklist.map(c => `<div style="padding:0.4rem 0; border-bottom:1px solid #0e3b28;">✔ ${c}</div>`).join("")
        : "<p>High confidence diagnosis verified. Standard field hygiene applies.</p>";

      document.getElementById("subtab-script").innerHTML = `
        <div style="background:#03150e; border:1px solid #134e35; border-radius:10px; padding:0.8rem;">
          <div class="markers-label">Normalized Offline TTS Script (${d.audio_backend || "-"})</div>
          <p style="margin-top:0.35rem; color:#ecfdf5;">${d.spoken_script || "-"}</p>
        </div>
      `;

      const q = d.quality || {};
      document.getElementById("subtab-audit").innerHTML = `
        <div class="step-3">
          <div class="step-box"><b>Gate A Quality Check</b><p style="margin-top:0.35rem;">Blur Var: ${q.blur_variance ?? "N/A"} | Foliage: ${q.foliage_ratio !== undefined ? (q.foliage_ratio*100).toFixed(1)+"%" : "N/A"} | Crop Match: Passed</p></div>
          <div class="step-box"><b>Gate B Safety Verdict</b><p style="margin-top:0.35rem;">Authorized: <b>${d.gate_b_passed}</b> | State: ${d.state} | District: ${d.district}</p></div>
          <div class="step-box"><b>Measured Edge Timings</b><p style="margin-top:0.35rem;">Vision: ${d.vision_latency_ms} ms | Severity: ${d.severity_latency_ms} ms | LLM: ${lm.total_llm_ms ?? "--"} ms | Total: ${d.total_latency_ms} ms</p></div>
        </div>
      `;

      document.getElementById("qaContextBanner").textContent =
        `Active Context: ${cleanTitle} (${d.confidence}% confidence, ${d.severity_pct}% ${d.severity_stage}) — Ready for offline follow-up questions.`;
    }

    function switchView(name) {
      document.querySelectorAll(".view-panel").forEach(p => p.classList.remove("active"));
      document.getElementById("view-" + name).classList.add("active");
      document.getElementById("tabBtnAnalysis").classList.toggle("active", name === "analysis");
      document.getElementById("tabBtnLibrary").classList.toggle("active", name === "library");
      document.getElementById("tabBtnAgronomist").classList.toggle("active", name === "agronomist");
      document.getElementById("tabBtnHistory").classList.toggle("active", name === "history");
    }

    function switchSubTab(name, btn) {
      document.querySelectorAll(".subtab-btn").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".subtab-pane").forEach(p => p.classList.remove("active"));
      if (btn) btn.classList.add("active");
      document.getElementById("subtab-" + name).classList.add("active");
    }

    function openAgronomistWithContext() {
      switchView("agronomist");
    }

    async function loadLibrary() {
      const lang = document.getElementById("langSelect").value;
      const res = await fetch(`/api/library?lang=${encodeURIComponent(lang)}`);
      libraryItems = await res.json();
      renderLibraryGrid();
    }

    function setLibFilter(crop, btn) {
      libFilter = crop;
      document.querySelectorAll("#libCropFilterRow .filter-pill").forEach(b => b.classList.remove("active"));
      if (btn) btn.classList.add("active");
      renderLibraryGrid();
    }

    function renderLibraryGrid() {
      const q = (document.getElementById("libSearchInput").value || "").toLowerCase().trim();
      const filtered = libraryItems.filter(it => {
        if (libFilter !== "All" && it.crop !== libFilter) return false;
        if (!q) return true;
        return (it.title + " " + it.pathogen_scientific + " " + it.chemical_name + " " + it.cultural_action).toLowerCase().includes(q);
      });
      document.getElementById("libGridContainer").innerHTML = filtered.map(it => `
        <div class="lib-card">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <span class="chip-green">${it.crop}</span>
            <span style="font-size:0.7rem; color:var(--text-muted);">${it.source_citation}</span>
          </div>
          <div style="font-size:0.96rem; font-weight:800; color:#fff;">${it.title}</div>
          <div style="font-size:0.76rem; font-style:italic; color:#34d399;">${it.pathogen_scientific}</div>
          <div style="font-size:0.78rem; color:#d1fae5; line-height:1.4;">${it.cultural_action}</div>
          <div style="font-size:0.74rem; color:#38bdf8; margin-top:auto; padding-top:0.35rem; border-top:1px solid #0e3b28;">
            Rx: ${it.chemical_name} ${it.chemical_dosage && it.chemical_dosage !== "N/A" ? "@ " + it.chemical_dosage : ""}
          </div>
        </div>
      `).join("");
    }

    function saveToScanLog(d) {
      const entry = {
        time: new Date().toLocaleString(),
        crop: d.crop,
        disease: String(d.disease || "").replace(/_/g, " "),
        confidence: d.confidence,
        severity_pct: d.severity_pct,
        stage: d.severity_stage,
        total_ms: d.total_latency_ms,
        result: d
      };
      scanHistory.unshift(entry);
      scanHistory = scanHistory.slice(0, 20);
      try { localStorage.setItem("kisandrishti_logs_v2", JSON.stringify(scanHistory)); } catch (e) {}
      renderScanLog();
    }

    function renderScanLog() {
      const el = document.getElementById("scanLogList");
      if (!scanHistory.length) {
        el.innerHTML = `<div style="color:var(--text-muted); font-size:0.86rem;">No diagnostic scans recorded yet.</div>`;
        return;
      }
      el.innerHTML = scanHistory.map((item, idx) => `
        <div class="log-item" onclick="loadScanFromHistory(${idx})">
          <div>
            <b style="color:#fff;">${item.crop}: ${item.disease}</b>
            <div style="font-size:0.74rem; color:var(--text-muted);">${item.time} • Total: ${item.total_ms} ms</div>
          </div>
          <div style="display:flex; gap:0.5rem; align-items:center;">
            <span class="chip-green">${item.confidence}% Conf</span>
            <span class="pill-sev">${item.severity_pct}% (${item.stage})</span>
          </div>
        </div>
      `).join("");
    }

    function loadScanFromHistory(idx) {
      const item = scanHistory[idx];
      if (!item || !item.result) return;
      lastResult = item.result;
      renderDiagnosisResult(item.result);
      switchView("analysis");
    }

    function clearScanLog() {
      scanHistory = [];
      try { localStorage.removeItem("kisandrishti_logs_v2"); } catch (e) {}
      renderScanLog();
    }

    function encodeWav16k(chunks, sampleRate) {
      let totalLen = chunks.reduce((acc, c) => acc + c.length, 0);
      const merged = new Float32Array(totalLen);
      let off = 0;
      for (const c of chunks) { merged.set(c, off); off += c.length; }
      const targetSr = 16000;
      const ratio = sampleRate / targetSr;
      const outLen = Math.max(1, Math.floor(merged.length / ratio));
      const buffer = new ArrayBuffer(44 + outLen * 2);
      const view = new DataView(buffer);
      const writeStr = (p, s) => { for (let i = 0; i < s.length; i++) view.setUint8(p + i, s.charCodeAt(i)); };
      writeStr(0, 'RIFF'); view.setUint32(4, 36 + outLen * 2, true); writeStr(8, 'WAVE');
      writeStr(12, 'fmt '); view.setUint32(16, 16, true); view.setUint16(20, 1, true);
      view.setUint16(22, 1, true); view.setUint32(24, targetSr, true);
      view.setUint32(28, targetSr * 2, true); view.setUint16(32, 2, true);
      view.setUint16(34, 16, true); writeStr(36, 'data'); view.setUint32(40, outLen * 2, true);
      for (let i = 0; i < outLen; i++) {
        const idx = Math.min(merged.length - 1, Math.floor(i * ratio));
        const s = Math.max(-1, Math.min(1, merged[idx]));
        view.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
      }
      return new Blob([buffer], { type: 'audio/wav' });
    }

    async function toggleMicRecording() {
      const btn = document.getElementById("btnMic");
      const badge = document.getElementById("qaStatusBadge");
      if (!micRecording) {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          badge.textContent = window.isSecureContext
            ? "Mic API unavailable; please type question below."
            : "Mic blocked over HTTP LAN IP. Open http://localhost:8000 on Pi or https://<pi-ip>:8443.";
          return;
        }
        try {
          mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
          audioCtx = new (window.AudioContext || window.webkitAudioContext)();
          const source = audioCtx.createMediaStreamSource(mediaStream);
          scriptNode = audioCtx.createScriptProcessor(4096, 1, 1);
          pcmChunks = [];
          scriptNode.onaudioprocess = (e) => pcmChunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
          source.connect(scriptNode);
          scriptNode.connect(audioCtx.destination);
          micRecording = true;
          btn.textContent = "⏹ Stop & Ask";
          btn.style.background = "#dc2626";
          badge.textContent = "Listening (16 kHz PCM)...";
        } catch (err) {
          badge.textContent = "Mic error: " + err.message;
        }
      } else {
        micRecording = false;
        btn.textContent = "🎤 Speak Question";
        btn.style.background = "#047857";
        badge.textContent = "Transcribing & Reasoning (ExecuTorch)...";
        const sr = audioCtx ? audioCtx.sampleRate : 16000;
        if (scriptNode) scriptNode.disconnect();
        if (audioCtx) await audioCtx.close();
        if (mediaStream) mediaStream.getTracks().forEach(t => t.stop());
        const wavBlob = encodeWav16k(pcmChunks, sr);
        await sendVoiceQA({ audioBlob: wavBlob });
      }
    }

    function askPresetQA(q) {
      document.getElementById("qaTextInput").value = q;
      submitTextQA();
    }

    async function submitTextQA() {
      const q = document.getElementById("qaTextInput").value.trim();
      if (!q) return;
      document.getElementById("qaTextInput").value = "";
      await sendVoiceQA({ questionText: q });
    }

    async function sendVoiceQA({ audioBlob = null, questionText = "" }) {
      const badge = document.getElementById("qaStatusBadge");
      const chat = document.getElementById("qaChatHistory");
      badge.textContent = "Running Whisper STT -> ExecuTorch Llama 3.2 -> Sherpa TTS...";

      const ctxPayload = lastResult ? {
        crop: lastResult.crop,
        disease: lastResult.disease,
        severity_pct: lastResult.severity_pct,
        severity_stage: lastResult.severity_stage,
        gate_b_passed: lastResult.gate_b_passed,
        cultural_action: (lastResult.treatment_summary || {}).cultural_action || "",
        organic_remedy: (lastResult.treatment_summary || {}).organic_remedy || "",
        chemical_name: (lastResult.treatment_summary || {}).chemical_name || "Withheld",
        chemical_dosage: (lastResult.treatment_summary || {}).chemical_dosage || "N/A",
        phi_display: (lastResult.treatment_summary || {}).phi_display || "N/A"
      } : {};

      const { voice, speed } = getVoiceSettings();
      const fd = new FormData();
      fd.append("lang", document.getElementById("langSelect").value);
      fd.append("voice", voice);
      fd.append("voice_speed", speed);
      fd.append("context_json", JSON.stringify(ctxPayload));
      if (questionText) fd.append("question_text", questionText);
      if (audioBlob) fd.append("audio_file", audioBlob, "question.wav");

      try {
        const res = await fetch("/api/voice-qa", { method: "POST", body: fd });
        const d = await res.json();
        const uDiv = document.createElement("div");
        uDiv.className = "chat-msg chat-user";
        uDiv.textContent = d.transcript || questionText || "(audio)";
        chat.appendChild(uDiv);

        const bDiv = document.createElement("div");
        bDiv.className = "chat-msg chat-bot";
        const lm = d.llm_metrics || {};
        bDiv.innerHTML = `${d.answer || ""}<div style="font-size:0.7rem; color:#6ee7b7aa; margin-top:0.35rem;">ExecuTorch: ${lm.tokens_per_sec || 0} tok/s | STT: ${d.stt_latency_ms || 0} ms | TTS: ${d.tts_latency_ms || 0} ms</div>`;
        chat.appendChild(bDiv);
        chat.scrollTop = chat.scrollHeight;

        const wrap = document.getElementById("qaAudioWrap");
        const qaAudio = document.getElementById("qaAudioPlayer");
        if (d.audio_url) {
          wrap.style.display = "flex";
          qaAudio.src = d.audio_url;
          qaAudio.play().catch(() => {});
          document.getElementById("qaAudioMeta").textContent = d.audio_backend || "";
        }
        badge.textContent = `ExecuTorch ${lm.tokens_per_sec || 0} tok/s | TTS ${d.tts_latency_ms || 0} ms`;
      } catch (err) {
        badge.textContent = "Q&A Error: " + err.message;
      }
    }

    initDashboard();
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(content=HTML_TEMPLATE)


if __name__ == "__main__":
    import uvicorn
    print("Starting KisanDrishti AI Offline Kiosk on http://0.0.0.0:8000")
    uvicorn.run("src.web_app:app", host="0.0.0.0", port=8000, reload=False)
