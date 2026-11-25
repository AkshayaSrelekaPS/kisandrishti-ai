"""
KisanDrishti AI: 100% Offline Two-Way Voice Q&A Engine
Pipeline:
  Microphone 16kHz WAV -> Whisper-Base INT8 (sherpa-onnx) ->
  Context-Constrained Llama 3.2 1B (ExecuTorch) ->
  Live Offline Neural TTS (sherpa-onnx VITS)
"""
import gc
import os
import sys
import time
import wave
import numpy as np

try:
    import sherpa_onnx
except ImportError:
    sherpa_onnx = None

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

STT_DIR = os.path.join(PROJECT_ROOT, "models", "stt", "whisper-base")


def read_wav_float32(wav_path: str, target_sr: int = 16000) -> tuple[np.ndarray, int]:
    """Reads PCM WAV (any channel count / sample rate) and returns mono float32 @ target_sr."""
    with wave.open(wav_path, "rb") as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        orig_sr = wf.getframerate()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    if sampwidth == 2:
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif sampwidth == 4:
        samples = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        samples = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0

    if n_channels > 1:
        samples = samples.reshape(-1, n_channels).mean(axis=1)

    if orig_sr != target_sr and len(samples) > 1:
        duration = len(samples) / float(orig_sr)
        new_len = max(int(round(duration * target_sr)), 1)
        x_old = np.linspace(0.0, 1.0, len(samples), endpoint=False)
        x_new = np.linspace(0.0, 1.0, new_len, endpoint=False)
        samples = np.interp(x_new, x_old, samples).astype(np.float32)
        return samples, target_sr

    return samples.astype(np.float32), orig_sr


class OfflineVoiceQAEngine:
    def __init__(self, agronomist_engine, voice_assistant, telemetry_monitor):
        self.agronomist = agronomist_engine
        self.voice_assistant = voice_assistant
        self.telemetry = telemetry_monitor
        self._recognizer = None
        self._recognizer_lang = None

    def is_stt_ready(self) -> bool:
        return (
            sherpa_onnx is not None
            and os.path.exists(os.path.join(STT_DIR, "base-encoder.int8.onnx"))
            and os.path.exists(os.path.join(STT_DIR, "base-decoder.int8.onnx"))
            and os.path.exists(os.path.join(STT_DIR, "base-tokens.txt"))
        )

    def _get_recognizer(self, lang: str):
        if not self.is_stt_ready():
            return None
        lang = lang if lang in ["en", "hi", "ta"] else "en"
        if self._recognizer is not None and self._recognizer_lang == lang:
            return self._recognizer

        # Keep only one active Whisper recognizer instance in memory
        if self._recognizer is not None:
            self._recognizer = None
            gc.collect()

        self._recognizer = sherpa_onnx.OfflineRecognizer.from_whisper(
            encoder=os.path.join(STT_DIR, "base-encoder.int8.onnx"),
            decoder=os.path.join(STT_DIR, "base-decoder.int8.onnx"),
            tokens=os.path.join(STT_DIR, "base-tokens.txt"),
            language=lang,
            task="transcribe",
            num_threads=4,
            provider="cpu",
        )
        self._recognizer_lang = lang
        return self._recognizer

    def transcribe(self, wav_path: str, lang: str = "en") -> tuple[str, float]:
        t0 = time.perf_counter()
        recognizer = self._get_recognizer(lang)
        if recognizer is None:
            return "", 0.0

        samples, sr = read_wav_float32(wav_path, target_sr=16000)
        if len(samples) == 0:
            return "", 0.0

        stream = recognizer.create_stream()
        stream.accept_waveform(sr, samples)
        recognizer.decode_stream(stream)
        text = (stream.result.text or "").strip()
        stt_ms = round((time.perf_counter() - t0) * 1000.0, 1)
        return text, stt_ms

    def _build_qa_prompt(self, question: str, context: dict, lang: str) -> str:
        lang_name = {"en": "English", "ta": "Tamil (தமிழ்)", "hi": "Hindi (हिन्दी)"}.get(lang, "English")
        crop = context.get("crop", "Unknown")
        disease = context.get("disease", "Unknown").replace("_", " ")
        severity = context.get("severity_pct", 0.0)
        stage = context.get("severity_stage", "Unknown")
        cultural = context.get("cultural_action", "Maintain field hygiene.")
        organic = context.get("organic_remedy", "Apply botanical or bio-control spray.")
        chemical = context.get("chemical_name", "Withheld")
        dosage = context.get("chemical_dosage", "N/A")
        phi = context.get("phi_display", "N/A")
        gate_b = context.get("gate_b_passed", False)

        chem_line = (
            f"Approved Chemical (from SQLite): {chemical} at {dosage}, PHI {phi}"
            if gate_b and chemical and chemical not in ["None", "Withheld"]
            else "Chemical Status: Withheld under Gate B safety rules (cultural/organic only)."
        )

        return f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are KisanDrishti AI, an offline Indian agricultural advisor.
Answer the farmer's follow-up question clearly in {lang_name} using ONLY the verified field notes below.

Guidelines:
1. When the farmer asks about organic or natural care, explain ONLY the Verified Organic Remedy and Cultural Action below.
2. Stick to the exact product names and numbers given below without inventing extra ones.
3. Answer directly in 2 short, spoken-friendly sentences in {lang_name}.<|eot_id|><|start_header_id|>user<|end_header_id|>

Current Field Context:
- Crop: {crop}
- Condition: {disease}
- Leaf Severity Estimate: {severity}% ({stage})
- Verified Cultural Action: {cultural}
- Verified Organic Remedy: {organic}
- {chem_line}

Farmer Question: {question}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""

    def answer_question(
        self,
        question_text: str = "",
        wav_path: str = None,
        context: dict = None,
        lang: str = "en",
        voice: str = "female",
        voice_speed: str = "slow",
    ) -> dict:
        t_start = time.perf_counter()
        lang = lang.lower() if lang in ["en", "ta", "hi"] else "en"
        context = context or {}

        stt_ms = 0.0
        transcript = (question_text or "").strip()
        if not transcript and wav_path and os.path.exists(wav_path):
            transcript, stt_ms = self.transcribe(wav_path, lang=lang)

        if not transcript:
            return {
                "status": "NO_SPEECH_DETECTED",
                "transcript": "",
                "answer": "Could not detect speech or question. Please speak clearly near the microphone or type your question.",
                "stt_latency_ms": stt_ms,
                "total_latency_ms": round((time.perf_counter() - t_start) * 1000.0, 1),
            }

        prompt = self._build_qa_prompt(transcript, context, lang=lang)
        answer, llm_metrics = self.agronomist._run_llm(prompt, max_tokens=120)
        if not answer:
            answer = context.get("cultural_action") or "Follow verified cultural sanitation and organic control measures."

        self.voice_assistant.set_voice_persona(voice)
        t_tts = time.perf_counter()
        from src.audio.voice_assistant import normalize_for_speech
        spoken_answer = normalize_for_speech(answer, lang)
        audio_path = self.voice_assistant.speak(spoken_answer, lang=lang, speed=voice_speed)
        tts_ms = round((time.perf_counter() - t_tts) * 1000.0, 1)

        return {
            "status": "SUCCESS",
            "transcript": transcript,
            "answer": answer,
            "audio_path": audio_path,
            "audio_backend": self.voice_assistant.last_backend,
            "stt_latency_ms": stt_ms,
            "llm_metrics": llm_metrics,
            "tts_latency_ms": tts_ms,
            "total_latency_ms": round((time.perf_counter() - t_start) * 1000.0, 1),
            "telemetry": self.telemetry.snapshot(),
        }
