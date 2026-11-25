"""
KisanDrishti AI: Context-Constrained Agronomist Reasoning Engine
Built for Meta Llama 3.2 1B-Instruct via ExecuTorch (.pte, XNNPACK 8da4w) primary runtime
with llama.cpp (Q4_K_M GGUF) fallback on Arm Cortex-A76.
Supports Trilingual Advisory: Tamil (தமிழ்), Hindi (हिन्दी), and English.

Architecture Compliance:
- Gate B: 4-Point Advisory Safety Validation Gate
  1. Confidence >= 75%
  2. District/State regional applicability verified
  3. Product & formulation applicability (not 'None')
  4. Authoritative source citation present (TNAU / ICAR / CIBRC)
- Role: Cultural Explainer & Multilingual Translator ONLY
- STRICT RULE: Chemical dosages & PHI are rendered statically from SQLite to eliminate hallucinations.
"""
import ctypes
import glob
import os
import shutil
import subprocess
import sys
import threading
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODELS_DIR = os.path.join(BASE_DIR, "models")
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    import torch
    import executorch.runtime as et_rt
    import pytorch_tokenizers
except ImportError:
    torch = None
    et_rt = None
    pytorch_tokenizers = None

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None


def _load_executorch_extension_libs() -> None:
    """Loads ExecuTorch LLM custom_ops and quantized_ops shared libraries when present."""
    if et_rt is None:
        return
    pkg_dir = os.path.dirname(os.path.dirname(et_rt.__file__))
    patterns = (
        ["custom_ops_aot_lib.dll", "quantized_ops_aot_lib.dll"]
        if os.name == "nt"
        else ["libcustom_ops_aot_lib*.so*", "libquantized_ops_aot_lib*.so*"]
    )
    rtld_flag = getattr(ctypes, "RTLD_GLOBAL", 0)
    for pat in patterns:
        matches = glob.glob(os.path.join(pkg_dir, "**", pat), recursive=True)
        for lib_path in matches:
            try:
                ctypes.CDLL(lib_path, mode=rtld_flag) if rtld_flag else ctypes.CDLL(lib_path)
            except Exception:
                pass


class MultilingualAgronomistEngine:
    def __init__(
        self,
        gguf_model_path: str = None,
        enable_llm: bool = True,
        n_threads: int = 4,
        pte_model_path: str = None,
        tokenizer_path: str = None,
    ):
        self.enable_llm = enable_llm
        self.n_threads = n_threads
        self.pte_model_path = pte_model_path or self._discover_pte()
        self.tokenizer_path = tokenizer_path or self._discover_tokenizer()
        self.gguf_model_path = gguf_model_path or self._discover_gguf()

        self._et_lock = threading.Lock()
        self._et_runtime = None
        self._et_program = None
        self._et_forward = None
        self._et_tokenizer = None
        self._et_eos_ids = {128009, 128001}
        self._et_max_seq_len = 1024

        self.llama_model = None
        tools_dir = os.path.join(BASE_DIR, "tools", "llama_cpp")
        exe_ext = ".exe" if os.name == "nt" else ""
        completion_bin = os.path.join(tools_dir, f"llama-completion{exe_ext}")
        cli_bin = os.path.join(tools_dir, f"llama-cli{exe_ext}")
        self.llama_cli_bin = (
            completion_bin if os.path.exists(completion_bin)
            else (cli_bin if os.path.exists(cli_bin) else (shutil.which("llama-completion") or shutil.which("llama-cli")))
        )
        self.backend_name = "deterministic-sqlite-fallback"

        if self.enable_llm:
            et_ok = self._init_executorch()
            if not et_ok:
                if self.gguf_model_path and os.path.exists(self.gguf_model_path):
                    if self.llama_cli_bin:
                        self.backend_name = f"llama.cpp ({os.path.basename(self.gguf_model_path)})"
                    elif Llama is not None:
                        try:
                            self.llama_model = Llama(
                                model_path=self.gguf_model_path,
                                n_ctx=1024,
                                n_threads=self.n_threads,
                                n_batch=256,
                                verbose=False,
                            )
                            self.backend_name = f"llama.cpp-python ({os.path.basename(self.gguf_model_path)})"
                        except Exception as exc:
                            self.backend_name = f"llama.cpp-load-error ({exc})"
                    else:
                        self.backend_name = "llm-model-present-no-runner"
                else:
                    self.backend_name = "deterministic-sqlite-fallback (PTE/GGUF not found)"

        self.supported_languages = {
            "en": "English",
            "ta": "Tamil (தமிழ்)",
            "hi": "Hindi (हिन्दी)",
        }

        self.headers = {
            "en": {
                "diagnosis_title": "AI Clinical Diagnostic Summary",
                "severity_label": "Leaf-Level Severity (Experimental)",
                "confidence_label": "Diagnostic Confidence",
                "sec1_title": "1. IMMEDIATE CULTURAL STEP (Zero-Cost Physical Action)",
                "sec2_title": "2. LOW-COST ORGANIC REMEDY (Bio-Fungicide / Natural Spray)",
                "sec3_title": "3. REGULATORY CHEMICAL TREATMENT (ICAR / TNAU / CIBRC Approved)",
                "chem_label": "Compound",
                "dosage_label": "Dilution & Dosage",
                "phi_label": "Pre-Harvest Safety Interval (PHI)",
                "source_label": "Verified Source",
                "compat_label": "Product Label Guidance",
                "gate_b_suppressed": "Gate B Safety Halt: Chemical recommendation suppressed (confidence < 75% or unverified regional match). Follow cultural/organic steps and field checklist.",
                "days": "days",
            },
            "ta": {
                "diagnosis_title": "உழவர் பார்வை ஏ ஐ: கள நோய் கண்டறிதல் மற்றும் பரிந்துரை அட்டை",
                "severity_label": "இலை பாதிப்பின் தீவிரம்",
                "confidence_label": "கண்டறிதல் துல்லியம்",
                "sec1_title": "1. உடனடி வேளாண் பராமரிப்பு (செலவில்லாத நேரடி நடவடிக்கை)",
                "sec2_title": "2. இயற்கை மற்றும் உயிரியல் கட்டுப்பாடு (குறைந்த செலவு)",
                "sec3_title": "3. அங்கீகரிக்கப்பட்ட இரசாயன சிகிச்சை (TNAU / CIBRC வழிகாட்டுதல்)",
                "chem_label": "மருந்துப்பொருள்",
                "dosage_label": "கலவை மற்றும் அளவு",
                "phi_label": "அறுவடைக்கு முந்தைய காத்திருப்பு காலம் (PHI)",
                "source_label": "அங்கீகரிக்கப்பட்ட ஆதாரம்",
                "compat_label": "உயிரியல் இணக்க வழிகாட்டுதல்",
                "gate_b_suppressed": "பாதுகாப்பு விதி B: துல்லியம் 75%-க்கு கீழ் உள்ளதால் அல்லது மண்டல சரிபார்ப்பு இல்லாததால் இரசாயன மருந்து பரிந்துரை நிறுத்தப்பட்டுள்ளது.",
                "days": "நாட்கள்",
            },
            "hi": {
                "diagnosis_title": "किसान दृष्टि एआई: खेत निदान एवं विशेषज्ञ परामर्श रिपोर्ट",
                "severity_label": "पत्ती संक्रमण गंभीरता",
                "confidence_label": "निदान सटीकता",
                "sec1_title": "1. तत्काल कृषि कार्य (शून्य-लागत भौतिक उपाय)",
                "sec2_title": "2. जैविक एवं प्राकृतिक उपचार (कम लागत)",
                "sec3_title": "3. आधिकारिक रासायनिक उपचार (ICAR / CIBRC अनुमोदित)",
                "chem_label": "रासायनिक तत्व",
                "dosage_label": "घोल एवं छिड़काव मात्रा",
                "phi_label": "फसल कटाई से पहले प्रतीक्षा अवधि (PHI)",
                "source_label": "सत्यापित स्रोत",
                "compat_label": "लेबल एवं जैव-अनुकूलता निर्देश",
                "gate_b_suppressed": "सुरक्षा नियम B: सटीकता 75% से कम होने या क्षेत्रीय सत्यापन न मिलने के कारण रासायनिक सलाह रोकी गई है।",
                "days": "दिन",
            },
        }

    @staticmethod
    def _discover_pte() -> str:
        if not os.path.exists(MODELS_DIR):
            return ""
        preferred = [
            os.path.join(MODELS_DIR, "llama3_2_1b_instruct_8da4w_xnnpack.pte"),
            os.path.join(MODELS_DIR, "Llama-3.2-1B-Instruct.pte"),
            os.path.join(MODELS_DIR, "model.pte"),
        ]
        for p in preferred:
            if os.path.exists(p):
                return p
        any_pte = sorted(glob.glob(os.path.join(MODELS_DIR, "*.pte")))
        return any_pte[0] if any_pte else ""

    @staticmethod
    def _discover_tokenizer() -> str:
        if not os.path.exists(MODELS_DIR):
            return ""
        preferred = [
            os.path.join(MODELS_DIR, "tokenizer.model"),
            os.path.join(MODELS_DIR, "tokenizer.json"),
        ]
        for p in preferred:
            if os.path.exists(p):
                return p
        any_tok = sorted(glob.glob(os.path.join(MODELS_DIR, "*tokenizer*")))
        return any_tok[0] if any_tok else ""

    def _init_executorch(self) -> bool:
        if (
            et_rt is None
            or torch is None
            or pytorch_tokenizers is None
            or not self.pte_model_path
            or not os.path.exists(self.pte_model_path)
            or not self.tokenizer_path
            or not os.path.exists(self.tokenizer_path)
        ):
            return False
        try:
            _load_executorch_extension_libs()
            self._et_runtime = et_rt.Runtime.get()
            self._et_program = self._et_runtime.load_program(self.pte_model_path)
            if "forward" not in self._et_program.method_names:
                return False
            self._et_forward = self._et_program.load_method("forward")
            self._et_tokenizer = pytorch_tokenizers.get_tokenizer(self.tokenizer_path)
            if "get_eos_ids" in self._et_program.method_names:
                eos_vals = self._et_program.load_method("get_eos_ids").execute([])
                parsed = {int(v) for v in eos_vals if isinstance(v, (int,))}
                if parsed:
                    self._et_eos_ids = parsed
            if "get_max_seq_len" in self._et_program.method_names:
                seq_vals = self._et_program.load_method("get_max_seq_len").execute([])
                if seq_vals and int(seq_vals[0]) > 0:
                    self._et_max_seq_len = int(seq_vals[0])
            self.backend_name = f"executorch ({os.path.basename(self.pte_model_path)})"
            return True
        except Exception as exc:
            self._et_forward = None
            self._et_program = None
            self._et_tokenizer = None
            print(f"[AgronomistEngine] ExecuTorch init skipped ({exc}); trying fallback.")
            return False

    @staticmethod
    def _discover_gguf() -> str:
        if not os.path.exists(MODELS_DIR):
            return ""
        preferred = [
            os.path.join(MODELS_DIR, "Llama-3.2-1B-Instruct-Q4_K_M.gguf"),
            os.path.join(MODELS_DIR, "llama-3.2-1b-instruct-q4_k_m.gguf"),
            os.path.join(MODELS_DIR, "llama3_2_1b_instruct_q4_k_m.gguf"),
        ]
        for p in preferred:
            if os.path.exists(p):
                return p
        any_gguf = sorted(glob.glob(os.path.join(MODELS_DIR, "*.gguf")))
        return any_gguf[0] if any_gguf else ""

    def format_llama_system_prompt(
        self,
        crop: str,
        disease: str,
        severity_pct: float,
        stage: str,
        confidence: float,
        treatment: dict,
        lang: str = "en",
    ) -> str:
        """
        Builds the strict Llama 3.2 1B-Instruct chat prompt.
        Constrains Llama strictly to cultural explanation and translation (zero chemical generation).
        """
        target_lang_name = self.supported_languages.get(lang, "English")

        return f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are KisanDrishti AI, a helpful Indian agricultural advisor running offline on an Arm edge device.
Summarize the cultural care and organic treatment steps below in clear, natural {target_lang_name} for a farmer.

Guidelines:
1. Stick strictly to the Cultural Action and Organic Remedy provided below.
2. Focus only on natural and cultural field care; do not add extra product names or dosage numbers.
3. Keep it brief: 2 short, practical sentences in {target_lang_name}.<|eot_id|><|start_header_id|>user<|end_header_id|>

Crop: {crop}
Condition: {disease} (Confidence: {confidence*100:.1f}%, Leaf Severity: {severity_pct}% {stage})
Cultural Action: {treatment.get('cultural_action', 'None')}
Organic Remedy: {treatment.get('organic_remedy', 'None')}

Write 2 concise, farmer-friendly sentences in {target_lang_name}.<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""

    @staticmethod
    def _sample_next_token(logits, recent_tokens: list, repetition_penalty: float = 1.18, temperature: float = 0.25, top_p: float = 0.9) -> int:
        logits = logits.float().clone()
        if recent_tokens and repetition_penalty > 1.0:
            unique_ids = torch.tensor(list(set(recent_tokens[-64:])), dtype=torch.long)
            scores = logits[unique_ids]
            logits[unique_ids] = torch.where(scores < 0, scores * repetition_penalty, scores / repetition_penalty)
        if temperature <= 0.05:
            return int(torch.argmax(logits).item())
        probs = torch.softmax(logits / temperature, dim=-1)
        sorted_probs, sorted_idx = torch.sort(probs, descending=True)
        cum_probs = torch.cumsum(sorted_probs, dim=-1)
        cutoff = cum_probs > top_p
        cutoff[1:] = cutoff[:-1].clone()
        cutoff[0] = False
        sorted_probs = sorted_probs.masked_fill(cutoff, 0.0)
        sorted_probs = sorted_probs / sorted_probs.sum().clamp_min(1e-8)
        choice = int(torch.multinomial(sorted_probs, num_samples=1).item())
        return int(sorted_idx[choice].item())

    def _run_executorch(self, prompt: str, max_tokens: int = 110) -> tuple:
        """Executes Llama 3.2 1B via ExecuTorch (.pte, XNNPACK 8da4w) and returns (text, metrics_dict)."""
        if self._et_forward is None or self._et_tokenizer is None or torch is None:
            return "", {"backend": self.backend_name, "executed": False, "ttft_ms": None, "tokens_generated": 0, "tokens_per_sec": 0.0, "total_llm_ms": 0.0}

        try:
            ids = self._et_tokenizer.encode(prompt, bos=False, eos=False, allowed_special="all")
            max_prompt = max(self._et_max_seq_len - max_tokens - 1, 32)
            if len(ids) > max_prompt:
                ids = ids[-max_prompt:]

            with self._et_lock:
                t_start = time.perf_counter()
                out = self._et_forward.execute([
                    torch.tensor([ids], dtype=torch.long),
                    torch.tensor([0], dtype=torch.long),
                ])[0]
                t_prefill = time.perf_counter()

                logits = out[0, -1] if out.ndim == 3 else out.view(-1)
                generated = []
                next_tok = self._sample_next_token(logits, generated)
                pos = len(ids)

                if next_tok not in self._et_eos_ids:
                    generated.append(next_tok)
                    for _ in range(max_tokens - 1):
                        if pos >= self._et_max_seq_len:
                            break
                        out = self._et_forward.execute([
                            torch.tensor([[next_tok]], dtype=torch.long),
                            torch.tensor([pos], dtype=torch.long),
                        ])[0]
                        pos += 1
                        logits = out[0, -1] if out.ndim == 3 else out.view(-1)
                        next_tok = self._sample_next_token(logits, generated)
                        if next_tok in self._et_eos_ids:
                            break
                        generated.append(next_tok)

                t_end = time.perf_counter()

            text = self._et_tokenizer.decode(generated).strip() if generated else ""
            ttft_ms = (t_prefill - t_start) * 1000.0
            decode_sec = max(t_end - t_prefill, 1e-6)
            tok_per_sec = (max(len(generated) - 1, 1) / decode_sec) if len(generated) > 1 else 0.0
            return text, {
                "backend": self.backend_name,
                "executed": bool(text),
                "ttft_ms": round(ttft_ms, 1),
                "tokens_generated": len(generated),
                "tokens_per_sec": round(tok_per_sec, 1),
                "total_llm_ms": round((t_end - t_start) * 1000.0, 1),
            }
        except Exception as exc:
            return "", {
                "backend": f"executorch-error ({exc})",
                "executed": False,
                "ttft_ms": None,
                "tokens_generated": 0,
                "tokens_per_sec": 0.0,
                "total_llm_ms": 0.0,
            }

    def _run_llm(self, prompt: str, max_tokens: int = 140) -> tuple:
        """Runs primary ExecuTorch LLM backend, falling back to llama.cpp if unavailable."""
        if self._et_forward is not None:
            text, metrics = self._run_executorch(prompt, max_tokens=max_tokens)
            if metrics.get("executed") and text:
                return text, metrics
        return self._run_llama_cpp(prompt, max_tokens=max_tokens)

    def _run_llama_cpp(self, prompt: str, max_tokens: int = 140) -> tuple:
        """Executes Llama 3.2 1B via llama-cpp-python or llama-cli and returns (text, metrics_dict)."""
        if self.llama_model is not None:
            t_start = time.perf_counter()
            first_token_time = None
            chunks = []
            token_count = 0

            stream = self.llama_model(
                prompt,
                max_tokens=max_tokens,
                temperature=0.2,
                top_p=0.9,
                stop=["<|eot_id|>", "<|end_of_text|>"],
                stream=True,
            )
            for out in stream:
                piece = out["choices"][0]["text"]
                if piece:
                    if first_token_time is None:
                        first_token_time = time.perf_counter()
                    chunks.append(piece)
                    token_count += 1

            t_end = time.perf_counter()
            ttft_ms = ((first_token_time or t_end) - t_start) * 1000.0
            decode_sec = max(t_end - (first_token_time or t_end), 1e-6)
            tok_per_sec = (max(token_count - 1, 1) / decode_sec) if token_count > 1 else 0.0
            return "".join(chunks).strip(), {
                "backend": self.backend_name,
                "executed": True,
                "ttft_ms": round(ttft_ms, 1),
                "tokens_generated": token_count,
                "tokens_per_sec": round(tok_per_sec, 1),
                "total_llm_ms": round((t_end - t_start) * 1000.0, 1),
            }

        if self.llama_cli_bin and self.gguf_model_path and os.path.exists(self.gguf_model_path):
            t_start = time.perf_counter()
            cmd = [
                self.llama_cli_bin,
                "-m", self.gguf_model_path,
                "-p", prompt,
                "-c", "1024",
                "-n", str(max_tokens),
                "--temp", "0.2",
                "-t", str(self.n_threads),
                "--no-display-prompt",
                "--simple-io",
                "-no-cnv",
            ]
            try:
                proc = subprocess.run(
                    cmd, input="", capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=90
                )
                elapsed_ms = (time.perf_counter() - t_start) * 1000.0
                output_text = (proc.stdout or "").replace("[end of text]", "").strip()
                ttft_ms = None
                tok_s = None
                gen_tokens = None
                for line in (proc.stderr or "").splitlines():
                    if "prompt eval time =" in line:
                        try:
                            ttft_ms = float(line.split("=")[1].split("ms")[0].strip())
                        except Exception:
                            pass
                    elif "eval time =" in line and "tokens per second" in line:
                        try:
                            rhs = line.split("=")[1]
                            gen_tokens = int(rhs.split("/")[1].strip().split()[0])
                            tok_s = float(line.split(",")[-1].strip().split()[0])
                        except Exception:
                            pass
                approx_tokens = gen_tokens if gen_tokens is not None else (max(len(output_text.split()), 1) if output_text else 0)
                return output_text, {
                    "backend": self.backend_name,
                    "executed": proc.returncode == 0 and bool(output_text),
                    "ttft_ms": round(ttft_ms, 1) if ttft_ms is not None else None,
                    "tokens_generated": approx_tokens,
                    "tokens_per_sec": round(tok_s, 1) if tok_s else (round(approx_tokens / max(elapsed_ms / 1000.0, 1e-6), 1) if approx_tokens else 0.0),
                    "total_llm_ms": round(elapsed_ms, 1),
                }
            except Exception as exc:
                return "", {
                    "backend": f"llama-cli-error ({exc})",
                    "executed": False,
                    "ttft_ms": None,
                    "tokens_generated": 0,
                    "tokens_per_sec": 0.0,
                    "total_llm_ms": 0.0,
                }

        return "", {
            "backend": self.backend_name,
            "executed": False,
            "ttft_ms": None,
            "tokens_generated": 0,
            "tokens_per_sec": 0.0,
            "total_llm_ms": 0.0,
        }

    def generate_advisory(self, diagnostic_payload: dict, lang: str = "en") -> dict:
        """
        Processes diagnostic output through the 4-point Gate B check,
        runs context-constrained llama.cpp cultural explanation (when available),
        and renders statutory chemical parameters statically from SQLite.
        """
        t0 = time.perf_counter()
        lang = lang.lower() if lang in ["en", "ta", "hi"] else "en"
        h = self.headers[lang]

        crop = diagnostic_payload.get("crop", "Unknown")
        disease = diagnostic_payload.get("disease", "Unknown").replace("_", " ")
        pathogen = diagnostic_payload.get("pathogen_scientific", "")
        confidence = diagnostic_payload.get("confidence", 0.0)
        severity_pct = diagnostic_payload.get("severity_pct", 0.0)
        stage = diagnostic_payload.get("severity_stage", "Moderate")
        treatment = diagnostic_payload.get("treatment") or {}

        # 4-Point Gate B Verification Check
        conf_ok = confidence >= 0.75
        region_ok = bool(treatment.get("region_verified", True))
        source_ok = bool(treatment.get("source_citation"))
        chemical_name = treatment.get("chemical_name", "None")
        has_chemical = bool(
            chemical_name and not any(chemical_name.startswith(x) for x in ["None", "இல்லை", "कोई नहीं"])
        )

        gate_b_passed = conf_ok and region_ok and source_ok
        chemical_active = gate_b_passed and has_chemical

        cultural_text = treatment.get("cultural_action", "Maintain clean field hygiene and balanced irrigation.")
        organic_text = treatment.get("organic_remedy", "Spray organic botanical extract or bio-fungicide.")

        stage_map = {
            "ta": {"Mild": "ஆரம்ப நிலை", "Moderate": "மிதமான நிலை", "Severe": "தீவிர நிலை", "Healthy": "ஆரோக்கிய நிலை", "None": "ஆரோக்கிய நிலை", "Uncertain": "தெளிவற்றது"},
            "hi": {"Mild": "शुरुआती चरण", "Moderate": "मध्यम चरण", "Severe": "गंभीर चरण", "Healthy": "स्वस्थ चरण", "None": "स्वस्थ चरण", "Uncertain": "अनिश्चित"},
            "en": {"Mild": "Mild", "Moderate": "Moderate", "Severe": "Severe", "Healthy": "Healthy", "None": "Healthy", "Uncertain": "Uncertain"},
        }
        localized_stage = stage_map.get(lang, stage_map["en"]).get(stage, stage)

        prescription_card = {
            "title": h["diagnosis_title"],
            "language": self.supported_languages[lang],
            "crop": crop,
            "disease": disease,
            "pathogen_scientific": pathogen,
            "confidence_display": f"{confidence*100:.1f}%",
            "severity_display": f"{severity_pct}% ({localized_stage})",
            "labels": {
                "chem_label": h["chem_label"],
                "dosage_label": h["dosage_label"],
                "phi_label": h["phi_label"],
                "source_label": h["source_label"],
                "compat_label": h["compat_label"],
            },
            "sections": [
                {
                    "title": h["sec1_title"],
                    "content": cultural_text,
                    "type": "cultural",
                },
                {
                    "title": h["sec2_title"],
                    "content": organic_text,
                    "type": "organic",
                },
            ],
        }

        if chemical_active:
            dosage_str = treatment.get("chemical_dosage", "")
            phi_str = treatment.get("phi_display", f"{treatment.get('phi_days', 0)} {h['days']}")
            prescription_card["sections"].append({
                "title": h["sec3_title"],
                "chemical_name": chemical_name,
                "dosage": dosage_str,
                "phi": phi_str,
                "source_citation": treatment.get("source_citation", "ICAR/TNAU/CIBRC"),
                "bio_compatibility_note": treatment.get("bio_compatibility_note", ""),
                "type": "chemical",
            })
        else:
            if not gate_b_passed:
                msg = h["gate_b_suppressed"]
            else:
                msg = (
                    "இரசாயன மருந்து தேவை இல்லை. இயற்கை முறைகளே போதுமானது."
                    if lang == "ta"
                    else (
                        "रासायनिक दवा की आवश्यकता नहीं है। जैविक उपाय पर्याप्त हैं।"
                        if lang == "hi"
                        else "No chemical spray required; cultural and biological measures are sufficient."
                    )
                )
            prescription_card["sections"].append({
                "title": h["sec3_title"],
                "content": msg,
                "type": "suppressed",
            })

        llama_prompt = self.format_llama_system_prompt(
            crop, disease, severity_pct, stage, confidence, treatment, lang=lang
        )
        llama_explanation, llm_metrics = (
            self._run_llm(llama_prompt) if self.enable_llm else ("", {"backend": "disabled", "executed": False})
        )

        if not llama_explanation:
            llama_explanation = f"{cultural_text} {organic_text}".strip()

        generation_time_ms = (time.perf_counter() - t0) * 1000.0

        return {
            "prescription_card": prescription_card,
            "llama_prompt": llama_prompt,
            "llama_explanation": llama_explanation,
            "llm_metrics": llm_metrics,
            "gate_b_passed": gate_b_passed,
            "generation_time_ms": round(generation_time_ms, 2),
        }
