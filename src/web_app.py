"""
KisanDrishti AI: 100% Offline Edge Agronomic Clinical Diagnostic Kiosk
FastAPI Web Application for Bharat AI-SoC Challenge 2026-27.
Zero external CDN/font dependencies; supports 4 crops & 3 languages (Tamil, Hindi, English).
"""
import os
import sys
import shutil
import time
import uuid
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

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
    {"id": "potato_late_blight.jpg", "crop": "Potato", "title": "Potato Late Blight", "file": "potato_late_blight.jpg"},
    {"id": "potato_healthy.jpg", "crop": "Potato", "title": "Potato Healthy", "file": "potato_healthy.jpg"},
    {"id": "rice_bacterial_blight.jpg", "crop": "Rice", "title": "Rice Bacterial Blight", "file": "rice_bacterial_blight.jpg"},
    {"id": "rice_brown_spot.jpg", "crop": "Rice", "title": "Rice Brown Spot", "file": "rice_brown_spot.jpg"},
    {"id": "tomato_early_blight.jpg", "crop": "Tomato", "title": "Tomato Early Blight", "file": "tomato_early_blight.jpg"},
    {"id": "corn_leaf_blight.jpg", "crop": "Corn", "title": "Corn Leaf Blight", "file": "corn_leaf_blight.jpg"},
]


@app.get("/api/samples")
def get_samples():
    return SAMPLE_METADATA


@app.get("/api/regions")
def get_regions():
    return VERIFIED_REGIONS


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
    import json
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
        "crop": diag_res["crop"],
        "disease": diag_res["disease"],
        "pathogen_scientific": diag_res.get("pathogen_scientific", ""),
        "confidence": round(diag_res["confidence"] * 100, 1),
        "severity_pct": diag_res["severity_pct"],
        "severity_stage": diag_res["severity_stage"],
        "state": diag_res.get("state"),
        "district": diag_res.get("district"),
        "pest_status": diag_res.get("pest_status"),
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
  <title>KisanDrishti AI | Offline Edge Agronomic Kiosk</title>
  <style>
    :root {
      --bg: #090d16;
      --card-bg: #111827;
      --card-border: #1f293d;
      --accent-green: #10b981;
      --accent-amber: #f59e0b;
      --accent-red: #ef4444;
      --accent-blue: #3b82f6;
      --text-main: #f9fafb;
      --text-muted: #9ca3af;
      --font-sans: system-ui, -apple-system, 'Segoe UI', Roboto, 'Noto Sans Tamil', 'Noto Sans Devanagari', sans-serif;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg);
      color: var(--text-main);
      font-family: var(--font-sans);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      padding: 1.25rem;
    }
    header {
      max-width: 1320px;
      margin: 0 auto 1.25rem auto;
      width: 100%;
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 1rem;
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 1rem;
    }
    .brand-title { display: flex; align-items: center; gap: 0.75rem; }
    .brand-badge {
      background: linear-gradient(135deg, #059669, #10b981);
      color: white;
      padding: 0.45rem 0.8rem;
      border-radius: 8px;
      font-weight: 800;
      font-size: 1rem;
    }
    h1 { font-size: 1.4rem; font-weight: 800; color: #fff; }
    .brand-subtitle { font-size: 0.82rem; color: var(--text-muted); margin-top: 0.15rem; }
    .badges-strip { display: flex; flex-wrap: wrap; gap: 0.5rem; }
    .status-pill {
      font-size: 0.75rem;
      font-weight: 600;
      padding: 0.3rem 0.65rem;
      border-radius: 20px;
      border: 1px solid var(--card-border);
      background: rgba(17, 24, 39, 0.7);
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
    }
    .pill-green { color: #34d399; border-color: rgba(52, 211, 153, 0.3); background: rgba(6, 78, 59, 0.4); }
    .pill-blue { color: #60a5fa; border-color: rgba(96, 165, 250, 0.3); background: rgba(30, 58, 138, 0.4); }
    .pill-purple { color: #c084fc; border-color: rgba(192, 132, 252, 0.3); background: rgba(88, 28, 135, 0.4); }
    .pill-amber { color: #fbbf24; border-color: rgba(251, 191, 36, 0.3); background: rgba(120, 53, 15, 0.4); }

    main {
      max-width: 1320px;
      margin: 0 auto;
      width: 100%;
      display: grid;
      grid-template-columns: 410px 1fr;
      gap: 1.25rem;
      flex: 1;
    }
    @media (max-width: 1024px) { main { grid-template-columns: 1fr; } }

    .card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 1.25rem;
      box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    .card-title {
      font-size: 1.05rem;
      font-weight: 700;
      margin-bottom: 1rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.5rem;
    }
    .form-group { margin-bottom: 0.9rem; }
    .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 0.65rem; }
    label { display: block; font-size: 0.8rem; font-weight: 600; color: #d1d5db; margin-bottom: 0.35rem; }
    select {
      width: 100%;
      padding: 0.6rem 0.75rem;
      background: #1e293b;
      border: 1px solid #334155;
      color: #fff;
      border-radius: 8px;
      font-size: 0.88rem;
      outline: none;
    }
    select:focus { border-color: var(--accent-green); }

    .sample-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.5rem; margin-bottom: 0.9rem; }
    .sample-item {
      background: #1a2234;
      border: 1px solid #2d3748;
      border-radius: 8px;
      padding: 0.4rem;
      cursor: pointer;
      text-align: center;
      transition: all 0.15s;
    }
    .sample-item:hover, .sample-item.active {
      border-color: var(--accent-green);
      background: rgba(16, 185, 129, 0.15);
    }
    .sample-item img { width: 100%; height: 56px; object-fit: cover; border-radius: 6px; margin-bottom: 0.25rem; }
    .sample-item span { font-size: 0.7rem; font-weight: 600; display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #e2e8f0; }

    .dropzone {
      border: 2px dashed #374151;
      border-radius: 10px;
      padding: 1rem;
      text-align: center;
      cursor: pointer;
      background: rgba(30, 41, 59, 0.4);
      margin-bottom: 0.9rem;
    }
    .dropzone:hover { border-color: var(--accent-green); }
    .dropzone p { font-size: 0.78rem; color: var(--text-muted); margin-top: 0.25rem; }

    .btn-submit {
      width: 100%;
      padding: 0.8rem;
      background: linear-gradient(135deg, #059669, #10b981);
      color: #fff;
      font-size: 0.95rem;
      font-weight: 700;
      border: none;
      border-radius: 8px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
    }
    .btn-submit:disabled { opacity: 0.5; cursor: not-allowed; }

    .metrics-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.75rem; margin-bottom: 1rem; }
    @media (max-width: 640px) { .metrics-row { grid-template-columns: repeat(2, 1fr); } }
    .metric-card { background: #172033; border: 1px solid var(--card-border); border-radius: 10px; padding: 0.7rem; text-align: center; }
    .metric-val { font-size: 1.15rem; font-weight: 800; color: #fff; }
    .metric-label { font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; margin-top: 0.2rem; }

    .vis-container { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem; }
    @media (max-width: 768px) { .vis-container { grid-template-columns: 1fr; } }
    .img-box { background: #0f172a; border-radius: 10px; border: 1px solid var(--card-border); overflow: hidden; text-align: center; }
    .img-box img { width: 100%; height: 210px; object-fit: contain; background: #000; display: block; }
    .img-caption { padding: 0.4rem; font-size: 0.75rem; font-weight: 600; color: var(--text-muted); background: #1e293b; }

    .hud-strip {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      margin-bottom: 1rem;
      padding: 0.65rem 0.85rem;
      border-radius: 10px;
      background: #0f172a;
      border: 1px solid #1e293b;
      font-size: 0.78rem;
      color: #cbd5e1;
    }

    .checklist-box {
      background: rgba(245, 158, 11, 0.12);
      border: 1px solid var(--accent-amber);
      border-radius: 10px;
      padding: 0.9rem;
      margin-bottom: 1rem;
      display: none;
    }
    .checklist-box h4 { color: #fbbf24; margin-bottom: 0.5rem; font-size: 0.9rem; }
    .checklist-box label { display: flex; gap: 0.5rem; align-items: flex-start; font-weight: 500; margin-bottom: 0.35rem; cursor: pointer; }

    .rx-box { background: #141e30; border-left: 4px solid var(--accent-green); border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }
    .rx-section-title { font-size: 0.85rem; font-weight: 700; color: #34d399; margin-bottom: 0.35rem; }
    .rx-content { font-size: 0.92rem; line-height: 1.5; color: #e2e8f0; margin-bottom: 0.6rem; }

    .audio-card {
      background: linear-gradient(135deg, #1e1b4b, #1e293b);
      border: 1px solid #3730a3;
      border-radius: 12px;
      padding: 0.9rem;
      display: flex;
      flex-direction: column;
      gap: 0.65rem;
    }
    audio { width: 100%; height: 38px; outline: none; border-radius: 20px; }
    details { background: rgba(15, 23, 42, 0.6); border: 1px solid var(--card-border); border-radius: 8px; padding: 0.55rem 0.8rem; font-size: 0.84rem; }
    summary { cursor: pointer; font-weight: 600; color: #93c5fd; }
    .transcript-text { margin-top: 0.5rem; line-height: 1.5; color: #cbd5e1; }
    .alert-banner { background: rgba(239, 68, 68, 0.15); border: 1px solid var(--accent-red); color: #fca5a5; padding: 0.9rem; border-radius: 8px; font-weight: 600; display: none; margin-bottom: 1rem; }
    .placeholder-state { text-align: center; padding: 3.5rem 1rem; color: var(--text-muted); }
    .spinner { border: 3px solid rgba(255,255,255,0.2); border-top-color: #fff; border-radius: 50%; width: 16px; height: 16px; animation: spin 0.8s linear infinite; display: inline-block; }
    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>
  <header>
    <div class="brand-title">
      <div class="brand-badge">உழவர் பார்வை • किसान दृष्टि</div>
      <div>
        <h1>KisanDrishti AI Offline Edge Clinical Kiosk</h1>
        <div class="brand-subtitle">4 Crops (20 Classes) • ONNX Vision + OpenCV Severity + SQLite Safety + ExecuTorch Llama 3.2</div>
      </div>
    </div>
    <div class="badges-strip">
      <div class="status-pill pill-green">Gate A: Quality + Crop Check</div>
      <div class="status-pill pill-blue">Gate B: Static SQLite Dosages</div>
      <div class="status-pill pill-purple">100% Offline Ready</div>
    </div>
  </header>

  <main>
    <div class="card">
      <div class="card-title">
        <span>Field Input Settings</span>
        <span style="font-size: 0.75rem; color: var(--text-muted);">Local Edge Inference</span>
      </div>

      <div class="form-group">
        <label>1. Primary Crop (4 Supported)</label>
        <select id="cropSelect">
          <option value="Potato">Potato (உருளைக்கிழங்கு / आलू)</option>
          <option value="Rice">Rice / Paddy (நெல் / धान)</option>
          <option value="Tomato">Tomato (தக்காளி / टमाटर)</option>
          <option value="Corn">Corn / Maize (மக்காச்சோளம் / मक्का)</option>
        </select>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label>2. State / Agro-Zone</label>
          <select id="stateSelect" onchange="updateDistricts()"></select>
        </div>
        <div class="form-group">
          <label>District</label>
          <select id="districtSelect"></select>
        </div>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label>3. Advisory Language</label>
          <select id="langSelect">
            <option value="ta" selected>தமிழ் (Tamil - TNAU)</option>
            <option value="hi">हिन्दी (Hindi - ICAR)</option>
            <option value="en">English (ICAR/CIBRC)</option>
          </select>
        </div>
        <div class="form-group">
          <label>Native Speaker Voice</label>
          <select id="voiceSelect">
            <option value="female" selected>Female (Pallavi / Swara / Neerja)</option>
            <option value="male">Male (Valluvar / Madhur / Prabhat)</option>
          </select>
        </div>
      </div>

      <div class="form-group">
        <label>Voice Speaking Speed</label>
        <select id="speedSelect">
          <option value="slow" selected>Slow &amp; Clear (-18% Recommended for Farmers)</option>
          <option value="normal">Normal Extension Pace (-10%)</option>
          <option value="fast">Standard Speed (0%)</option>
        </select>
      </div>

      <label>4. Select Preloaded Leaf Sample</label>
      <div class="sample-grid" id="sampleGrid"></div>

      <label>Or Upload Custom Leaf Photo (Mode 1)</label>
      <div class="dropzone" onclick="document.getElementById('fileInput').click()">
        <div style="font-weight: 600; font-size: 0.85rem;" id="dropzoneText">Click to Upload Leaf Image</div>
        <p>JPG / PNG (Mode 1: Leaf Close-Up)</p>
        <input type="file" id="fileInput" accept="image/*" style="display: none;" onchange="handleFileSelect(event)">
      </div>

      <label>Mode 3: Insect Close-Up (Optional Pest Screening)</label>
      <div class="dropzone" style="border-color: #475569; padding: 0.75rem;" onclick="document.getElementById('pestInput').click()">
        <div style="font-weight: 600; font-size: 0.82rem;" id="pestDropText">Click to Upload Insect Photo (Whitefly / Aphid / Leafminer...)</div>
        <input type="file" id="pestInput" accept="image/*" style="display: none;" onchange="handlePestSelect(event)">
      </div>

      <button class="btn-submit" id="btnSubmit" onclick="runAnalysis()">
        <span id="btnIcon">▶</span>
        <span id="btnText">Execute Offline Diagnosis</span>
      </button>
      <button class="btn-submit" id="btnPestSubmit" style="margin-top: 0.5rem; background: linear-gradient(135deg, #b45309, #d97706); display: none;" onclick="runPestAnalysis()">
        <span>🐛</span>
        <span>Execute Mode 3 Insect Pest Diagnosis</span>
      </button>
    </div>

    <div class="card">
      <div class="card-title">
        <span>Diagnostic Results &amp; Advisory</span>
        <span id="telemetryBadge" class="status-pill pill-blue">Awaiting Input</span>
      </div>

      <div class="alert-banner" id="alertBanner"></div>

      <div id="placeholderState" class="placeholder-state">
        <h3>Select a crop, region, and leaf image to run offline diagnosis.</h3>
        <p style="margin-top: 0.5rem; font-size: 0.84rem;">Runs locally with zero cloud API calls.</p>
      </div>

      <div id="resultsContent" style="display: none;">
        <div class="metrics-row">
          <div class="metric-card">
            <div class="metric-val" id="metricDisease" style="color: #60a5fa;">-</div>
            <div class="metric-label" id="metricPathogen">Vision Diagnosis</div>
          </div>
          <div class="metric-card">
            <div class="metric-val" id="metricConfidence" style="color: #34d399;">-</div>
            <div class="metric-label">Confidence</div>
          </div>
          <div class="metric-card">
            <div class="metric-val" id="metricSeverity" style="color: #f59e0b;">-</div>
            <div class="metric-label">Leaf Severity (S%)</div>
          </div>
          <div class="metric-card">
            <div class="metric-val" id="metricLatency" style="color: #a78bfa;">-</div>
            <div class="metric-label">Total Latency</div>
          </div>
        </div>

        <div class="hud-strip" id="hudStrip"></div>

        <div class="checklist-box" id="checklistBox">
          <h4>Borderline Confidence (50%–75%): Verify 3-Point Field Symptom Checklist</h4>
          <div id="checklistItems"></div>
        </div>

        <div class="vis-container">
          <div class="img-box">
            <img id="imgOriginal" src="" alt="Original Leaf">
            <div class="img-caption">Field Leaf Input</div>
          </div>
          <div class="img-box">
            <img id="imgAnnotated" src="" alt="Lesion Mask">
            <div class="img-caption">Experimental OpenCV Lesion Mask (S%)</div>
          </div>
        </div>

        <div class="audio-card">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 0.88rem; font-weight: 700; color: #a5b4fc;">Offline Spoken Advisory</span>
            <span id="voiceBadge" class="status-pill pill-green" style="font-size: 0.68rem;">Offline Audio</span>
          </div>
          <audio id="audioPlayer" controls></audio>
          <details>
            <summary>View Spoken Script &amp; ExecuTorch Llama 3.2 Explanation</summary>
            <div class="transcript-text" id="transcriptText"></div>
          </details>
        </div>

        <div id="prescriptionCard" style="margin-top: 1rem;"></div>

        <!-- Two-Way Offline Live Voice Q&A -->
        <div class="audio-card" style="margin-top: 1rem; border-color: #065f46; background: linear-gradient(135deg, #064e3b33, #111827);">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 0.9rem; font-weight: 700; color: #34d399;">🎙️ Ask Follow-Up Question (100% Offline Voice Q&amp;A)</span>
            <span id="qaStatusBadge" class="status-pill pill-blue" style="font-size: 0.68rem;">Whisper-Base INT8 + ExecuTorch</span>
          </div>
          <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
            <button id="btnMic" class="btn-submit" style="width: auto; padding: 0.55rem 0.9rem; background: #047857;" onclick="toggleMicRecording()">🎤 Speak Question</button>
            <input id="qaTextInput" type="text" placeholder="Or type a follow-up question in Tamil / Hindi / English..." style="flex: 1; min-width: 220px; padding: 0.55rem 0.75rem; background: #1e293b; border: 1px solid #334155; color: #fff; border-radius: 8px; font-size: 0.85rem;">
            <button class="btn-submit" style="width: auto; padding: 0.55rem 0.9rem; background: #2563eb;" onclick="submitTextQA()">Ask</button>
          </div>
          <div id="qaResultBox" style="display: none; font-size: 0.86rem; line-height: 1.5; color: #e2e8f0;">
            <div id="qaTranscript" style="color: #93c5fd; margin-bottom: 0.35rem;"></div>
            <div id="qaAnswer" style="margin-bottom: 0.5rem;"></div>
            <audio id="qaAudioPlayer" controls style="display: none;"></audio>
          </div>
        </div>
      </div>
    </div>
  </main>

  <script>
    let selectedSample = null;
    let selectedFile = null;
    let selectedPestFile = null;
    let regionsMap = {};
    let lastDiagnosisContext = {};
    let micRecording = false;
    let audioCtx = null;
    let mediaStream = null;
    let pcmChunks = [];
    let scriptNode = null;

    async function init() {
      const [sRes, rRes] = await Promise.all([fetch('/api/samples'), fetch('/api/regions')]);
      const samples = await sRes.json();
      regionsMap = await rRes.json();

      const stateSel = document.getElementById('stateSelect');
      Object.keys(regionsMap).forEach(st => {
        const opt = document.createElement('option');
        opt.value = st;
        opt.textContent = st;
        stateSel.appendChild(opt);
      });
      updateDistricts();

      const grid = document.getElementById('sampleGrid');
      samples.forEach((s, idx) => {
        const div = document.createElement('div');
        div.className = 'sample-item' + (idx === 0 ? ' active' : '');
        if (idx === 0) {
          selectedSample = s.id;
          document.getElementById('cropSelect').value = s.crop;
        }
        div.onclick = () => selectSample(s, div);
        div.innerHTML = `<img src="/static/samples/${s.file}" alt="${s.title}"><span>${s.title}</span>`;
        grid.appendChild(div);
      });
    }

    function updateDistricts() {
      const st = document.getElementById('stateSelect').value;
      const distSel = document.getElementById('districtSelect');
      distSel.innerHTML = '';
      (regionsMap[st] || ['All Districts']).forEach(d => {
        const opt = document.createElement('option');
        opt.value = d;
        opt.textContent = d;
        distSel.appendChild(opt);
      });
    }

    function selectSample(sample, el) {
      document.querySelectorAll('.sample-item').forEach(x => x.classList.remove('active'));
      el.classList.add('active');
      selectedSample = sample.id;
      selectedFile = null;
      document.getElementById('cropSelect').value = sample.crop;
      document.getElementById('dropzoneText').textContent = 'Click to Upload Leaf Image';
    }

    function handleFileSelect(e) {
      const file = e.target.files[0];
      if (file) {
        selectedFile = file;
        selectedSample = null;
        document.querySelectorAll('.sample-item').forEach(x => x.classList.remove('active'));
        document.getElementById('dropzoneText').textContent = `Selected: ${file.name}`;
      }
    }

    function handlePestSelect(e) {
      const file = e.target.files[0];
      if (file) {
        selectedPestFile = file;
        document.getElementById('pestDropText').textContent = `Insect Selected: ${file.name}`;
        document.getElementById('btnPestSubmit').style.display = 'flex';
      }
    }

    async function runPestAnalysis() {
      if (!selectedPestFile) return;
      const btn = document.getElementById('btnPestSubmit');
      const alertBanner = document.getElementById('alertBanner');
      alertBanner.style.display = 'none';
      btn.disabled = true;
      const fd = new FormData();
      fd.append('crop', document.getElementById('cropSelect').value);
      fd.append('lang', document.getElementById('langSelect').value);
      fd.append('voice', document.getElementById('voiceSelect').value);
      fd.append('voice_speed', document.getElementById('speedSelect').value);
      fd.append('state', document.getElementById('stateSelect').value);
      fd.append('district', document.getElementById('districtSelect').value);
      fd.append('file', selectedPestFile);
      try {
        const res = await fetch('/api/diagnose-pest', { method: 'POST', body: fd });
        const data = await res.json();
        if (data.status === 'GATE_A_REJECTED') {
          alertBanner.innerHTML = `⚠️ <b>Gate A Halt (Mode 3):</b> ${data.message}`;
          alertBanner.style.display = 'block';
          return;
        }
        renderResults(data);
      } catch (err) {
        alertBanner.textContent = 'Pest Diagnostic Error: ' + err.message;
        alertBanner.style.display = 'block';
      } finally {
        btn.disabled = false;
      }
    }

    async function runAnalysis() {
      const btn = document.getElementById('btnSubmit');
      const icon = document.getElementById('btnIcon');
      const text = document.getElementById('btnText');
      const alertBanner = document.getElementById('alertBanner');

      alertBanner.style.display = 'none';
      btn.disabled = true;
      icon.innerHTML = '<span class="spinner"></span>';
      text.textContent = 'Running Edge Inference...';

      const formData = new FormData();
      formData.append('crop', document.getElementById('cropSelect').value);
      formData.append('lang', document.getElementById('langSelect').value);
      formData.append('voice', document.getElementById('voiceSelect').value);
      formData.append('voice_speed', document.getElementById('speedSelect').value);
      formData.append('state', document.getElementById('stateSelect').value);
      formData.append('district', document.getElementById('districtSelect').value);

      if (selectedFile) formData.append('file', selectedFile);
      else if (selectedSample) formData.append('sample_name', selectedSample);

      try {
        const res = await fetch('/api/diagnose', { method: 'POST', body: formData });
        const data = await res.json();

        if (data.status === 'GATE_A_REJECTED') {
          alertBanner.innerHTML = `⚠️ <b>Gate A Halt:</b> ${data.message}`;
          alertBanner.style.display = 'block';
          document.getElementById('placeholderState').style.display = 'block';
          document.getElementById('resultsContent').style.display = 'none';
          document.getElementById('telemetryBadge').textContent = 'Gate A Rejection';
          document.getElementById('telemetryBadge').className = 'status-pill pill-amber';
          return;
        }
        renderResults(data);
      } catch (err) {
        alertBanner.textContent = 'Diagnostic Error: ' + err.message;
        alertBanner.style.display = 'block';
      } finally {
        btn.disabled = false;
        icon.textContent = '▶';
        text.textContent = 'Execute Offline Diagnosis';
      }
    }

    function renderResults(d) {
      document.getElementById('placeholderState').style.display = 'none';
      document.getElementById('resultsContent').style.display = 'block';

      document.getElementById('metricDisease').textContent = d.disease.replace(/_/g, ' ');
      document.getElementById('metricPathogen').textContent = d.pathogen_scientific || 'Vision Diagnosis';
      document.getElementById('metricConfidence').textContent = d.confidence + '%';
      document.getElementById('metricSeverity').textContent = `${d.severity_pct}% (${d.severity_stage})`;
      document.getElementById('metricLatency').textContent = d.total_latency_ms + ' ms';
      document.getElementById('telemetryBadge').textContent = `Vision: ${d.vision_latency_ms} ms | Total: ${d.total_latency_ms} ms`;
      document.getElementById('telemetryBadge').className = 'status-pill pill-green';

      const t = d.telemetry || {};
      const llm = d.llm_metrics || {};
      const tempTxt = t.soc_temp_c != null ? `Temp: ${t.soc_temp_c}°C` : 'Temp: N/A';
      const freqTxt = t.cpu_freq_mhz != null ? `Clock: ${t.cpu_freq_mhz} MHz` : '';
      const llmTxt = llm.executed ? `LLM: ${llm.tokens_per_sec} tok/s (TTFT ${llm.ttft_ms} ms)` : `LLM: ${llm.backend || 'Fallback'}`;
      document.getElementById('hudStrip').innerHTML = `
        <span><b>Vision:</b> ${d.vision_backend} (${d.vision_latency_ms} ms)</span>
        <span>• <b>Severity:</b> ${d.severity_latency_ms} ms</span>
        <span>• <b>RAM RSS:</b> ${t.process_rss_mb || '-'} MB</span>
        <span>• <b>${tempTxt}</b> ${freqTxt}</span>
        <span>• <b>${llmTxt}</b></span>
        <span>• <b>Pest Mode 3:</b> ${d.pest_status}</span>
      `;

      const clBox = document.getElementById('checklistBox');
      if (d.is_borderline && d.symptom_checklist && d.symptom_checklist.length > 0) {
        clBox.style.display = 'block';
        document.getElementById('checklistItems').innerHTML = d.symptom_checklist
          .map(item => `<label><input type="checkbox"> <span>${item}</span></label>`)
          .join('');
      } else {
        clBox.style.display = 'none';
      }

      document.getElementById('imgOriginal').src = d.original_image_url;
      document.getElementById('imgAnnotated').src = d.annotated_image_url;

      const audio = document.getElementById('audioPlayer');
      document.getElementById('voiceBadge').textContent = d.audio_backend || 'Offline';
      if (d.audio_url) {
        audio.style.display = 'block';
        audio.src = d.audio_url;
        audio.play().catch(() => {});
      } else {
        audio.style.display = 'none';
      }
      document.getElementById('transcriptText').innerHTML = `
        <p><b>Spoken Script:</b> ${d.spoken_script}</p>
        <p style="margin-top:0.5rem;"><b>SLM Cultural Explanation:</b> ${d.llama_explanation}</p>
      `;

      const rxContainer = document.getElementById('prescriptionCard');
      const card = d.prescription_card;
      const lbl = card.labels || {};
      let rxHtml = `
        <div class="rx-box">
          <div style="font-weight: 800; font-size: 1.05rem; color: #fff; margin-bottom: 0.4rem;">${card.title}</div>
          <div style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 0.9rem;">
            <b>${card.crop}</b> • ${card.disease} (<i>${card.pathogen_scientific || ''}</i>) • ${card.severity_display} • Confidence: ${card.confidence_display} • Region: ${d.state} / ${d.district}
          </div>
      `;

      card.sections.forEach(sec => {
        if (sec.type === 'chemical') {
          rxHtml += `
            <div style="margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid #1f293d;">
              <div class="rx-section-title" style="color: #60a5fa;">${sec.title}</div>
              <div class="rx-content" style="color: #93c5fd;">
                <b>${lbl.chem_label || 'Compound'}:</b> ${sec.chemical_name}<br>
                <b>${lbl.dosage_label || 'Dosage'}:</b> ${sec.dosage}<br>
                <b>${lbl.phi_label || 'PHI'}:</b> ${sec.phi}<br>
                <b>${lbl.source_label || 'Source'}:</b> ${sec.source_citation}<br>
                <span style="font-size:0.8rem;color:#94a3b8;"><b>${lbl.compat_label || 'Note'}:</b> ${sec.bio_compatibility_note}</span>
              </div>
            </div>
          `;
        } else {
          rxHtml += `
            <div style="margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid #1f293d;">
              <div class="rx-section-title">${sec.title}</div>
              <div class="rx-content">${sec.content}</div>
            </div>
          `;
        }
      });

      rxHtml += '</div>';
      rxContainer.innerHTML = rxHtml;

      const secCultural = (card.sections || []).find(s => s.type === 'cultural');
      const secOrganic = (card.sections || []).find(s => s.type === 'organic');
      const secChem = (card.sections || []).find(s => s.type === 'chemical');
      lastDiagnosisContext = {
        crop: d.crop,
        disease: d.disease,
        severity_pct: d.severity_pct,
        severity_stage: d.severity_stage,
        gate_b_passed: d.gate_b_passed,
        cultural_action: secCultural ? secCultural.content : '',
        organic_remedy: secOrganic ? secOrganic.content : '',
        chemical_name: secChem ? secChem.chemical_name : 'Withheld',
        chemical_dosage: secChem ? secChem.dosage : 'N/A',
        phi_display: secChem ? secChem.phi : 'N/A'
      };
      document.getElementById('qaResultBox').style.display = 'none';
    }

    function encodeWav16k(chunks, inputSampleRate) {
      let totalLen = chunks.reduce((a, c) => a + c.length, 0);
      let merged = new Float32Array(totalLen);
      let offset = 0;
      for (const c of chunks) { merged.set(c, offset); offset += c.length; }
      const targetRate = 16000;
      const ratio = inputSampleRate / targetRate;
      const outLen = Math.max(1, Math.floor(merged.length / ratio));
      const buffer = new ArrayBuffer(44 + outLen * 2);
      const view = new DataView(buffer);
      const writeStr = (pos, str) => { for (let i = 0; i < str.length; i++) view.setUint8(pos + i, str.charCodeAt(i)); };
      writeStr(0, 'RIFF'); view.setUint32(4, 36 + outLen * 2, true); writeStr(8, 'WAVE');
      writeStr(12, 'fmt '); view.setUint32(16, 16, true); view.setUint16(20, 1, true);
      view.setUint16(22, 1, true); view.setUint32(24, targetRate, true);
      view.setUint32(28, targetRate * 2, true); view.setUint16(32, 2, true);
      view.setUint16(34, 16, true); writeStr(36, 'data'); view.setUint32(40, outLen * 2, true);
      for (let i = 0; i < outLen; i++) {
        const idx = Math.min(merged.length - 1, Math.floor(i * ratio));
        const s = Math.max(-1, Math.min(1, merged[idx]));
        view.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
      }
      return new Blob([buffer], { type: 'audio/wav' });
    }

    async function toggleMicRecording() {
      const btn = document.getElementById('btnMic');
      const badge = document.getElementById('qaStatusBadge');
      if (!micRecording) {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          badge.textContent = window.isSecureContext
            ? 'Mic API unavailable in this browser; please type your question.'
            : 'Mic blocked on HTTP LAN IP. Open http://localhost:8000 on Pi or https://<pi-ip>:8443, or type below.';
          return;
        }
        try {
          mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
          audioCtx = new (window.AudioContext || window.webkitAudioContext)();
          const source = audioCtx.createMediaStreamSource(mediaStream);
          scriptNode = audioCtx.createScriptProcessor(4096, 1, 1);
          pcmChunks = [];
          scriptNode.onaudioprocess = (e) => { pcmChunks.push(new Float32Array(e.inputBuffer.getChannelData(0))); };
          source.connect(scriptNode);
          scriptNode.connect(audioCtx.destination);
          micRecording = true;
          btn.textContent = '⏹ Stop & Ask';
          btn.style.background = '#dc2626';
          badge.textContent = 'Listening...';
        } catch (err) {
          badge.textContent = 'Mic error: ' + err.message;
        }
      } else {
        micRecording = false;
        btn.textContent = '🎤 Speak Question';
        btn.style.background = '#047857';
        badge.textContent = 'Transcribing & Answering...';
        const sr = audioCtx ? audioCtx.sampleRate : 16000;
        if (scriptNode) scriptNode.disconnect();
        if (audioCtx) await audioCtx.close();
        if (mediaStream) mediaStream.getTracks().forEach(t => t.stop());
        const wavBlob = encodeWav16k(pcmChunks, sr);
        await sendVoiceQA({ audioBlob: wavBlob });
      }
    }

    async function submitTextQA() {
      const q = document.getElementById('qaTextInput').value.trim();
      if (!q) return;
      await sendVoiceQA({ questionText: q });
    }

    async function sendVoiceQA({ audioBlob = null, questionText = '' }) {
      const badge = document.getElementById('qaStatusBadge');
      badge.textContent = 'Running Offline Voice Q&A...';
      const fd = new FormData();
      fd.append('lang', document.getElementById('langSelect').value);
      fd.append('voice', document.getElementById('voiceSelect').value);
      fd.append('voice_speed', document.getElementById('speedSelect').value);
      fd.append('context_json', JSON.stringify(lastDiagnosisContext));
      if (questionText) fd.append('question_text', questionText);
      if (audioBlob) fd.append('audio_file', audioBlob, 'question.wav');

      try {
        const res = await fetch('/api/voice-qa', { method: 'POST', body: fd });
        const d = await res.json();
        document.getElementById('qaResultBox').style.display = 'block';
        document.getElementById('qaTranscript').textContent = 'Farmer Asked: ' + (d.transcript || '(no speech detected)');
        document.getElementById('qaAnswer').textContent = 'Agronomist Reply: ' + (d.answer || '');
        const qaAudio = document.getElementById('qaAudioPlayer');
        if (d.audio_url) {
          qaAudio.style.display = 'block';
          qaAudio.src = d.audio_url;
          qaAudio.play().catch(() => {});
        } else {
          qaAudio.style.display = 'none';
        }
        badge.textContent = `STT ${d.stt_latency_ms || 0}ms | TTS ${d.tts_latency_ms || 0}ms | ${d.audio_backend || ''}`;
      } catch (err) {
        badge.textContent = 'Q&A Error: ' + err.message;
      }
    }

    init();
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
