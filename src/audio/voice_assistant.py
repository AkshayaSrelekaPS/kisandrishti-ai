"""
KisanDrishti AI: Native Trilingual Voice Assistant
Specialized for Indian Smallholder Farmers in:
- Tamil (தமிழ் - TNAU Agricultural Extension Broadcast Style)
- Hindi (हिन्दी - ICAR Krishi Vigyan Kendra Style)
- Indian English (Clear, Paced Smallholder Advisory)

Key Improvements for Clarity & Understandability:
1. Full Native Speech Normalization:
   - Converts all numbers (0-1000), decimals (e.g. 2.5), percentages (%),
     formulation acronyms (WP, EC, SC, WG, DF), and dosage units (g/L, ml/L)
     into pure spoken words in Tamil, Hindi, and English.
2. Natural Breath Pauses & Required Speaking Speed:
   - Supports 'slow' (0.82x / -18%, default for rural clarity), 'normal' (0.90x / -10%),
     and 'fast' (1.0x / +0%).
3. Native Speaker Engine Priority:
   a) Sherpa-ONNX offline neural VITS/Piper models (models/tts/<lang>/) — 100% offline
   b) Piper TTS CLI offline models (models/piper/) — 100% offline
   c) Cached native speaker audio (data/audio_cache/) — 100% offline
   d) Native Neural Edge-TTS (ta-IN-Pallavi/Valluvar, hi-IN-Swara/Madhur, en-IN-Neerja/Prabhat)
   e) Last-resort offline eSpeak-NG / pyttsx3 fallback
"""
import asyncio
import hashlib
import os
import re
import shutil
import subprocess
import sys
import time

try:
    import sherpa_onnx
except ImportError:
    sherpa_onnx = None

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

AUDIO_DIR = os.path.abspath(os.path.join(PROJECT_ROOT, "data", "audio_outputs"))
AUDIO_CACHE_DIR = os.path.abspath(os.path.join(PROJECT_ROOT, "data", "audio_cache"))
PIPER_MODELS_DIR = os.path.abspath(os.path.join(PROJECT_ROOT, "models", "piper"))
SHERPA_MODELS_DIR = os.path.abspath(os.path.join(PROJECT_ROOT, "models", "tts"))

for _d in [AUDIO_DIR, AUDIO_CACHE_DIR]:
    os.makedirs(_d, exist_ok=True)


def int_to_tamil(n: int) -> str:
    """Converts integers 0-1000 into natural spoken Tamil words."""
    units = ["பூஜ்ஜியம்", "ஒன்று", "இரண்டு", "மூன்று", "நான்கு", "ஐந்து", "ஆறு", "ஏழு", "எட்டு", "ஒன்பது"]
    teens = ["பத்து", "பதினொன்று", "பன்னிரண்டு", "பதிமூன்று", "பதினான்கு", "பதினைந்து", "பதினாறு", "பதினேழு", "பதினெட்டு", "பத்தொன்பது"]
    tens_prefix = ["", "", "இருபத்தி ", "முப்பத்தி ", "நாற்பத்தி ", "ஐம்பத்தி ", "அறுபத்தி ", "எழுபத்தி ", "எண்பத்தி ", "தொண்ணூற்று "]
    tens_exact = ["", "", "இருபது", "முப்பது", "நாற்பது", "ஐம்பது", "அறுபது", "எழுபது", "எண்பது", "தொண்ணூறு"]
    hundreds_exact = ["", "நூறு", "இருநூறு", "முந்நூறு", "நானூறு", "ஐந்நூறு", "அறுநூறு", "எழுநூறு", "எண்ணூறு", "தொள்ளாயிரம்"]
    hundreds_prefix = ["", "நூற்று ", "இருநூற்று ", "முந்நூற்று ", "நானூற்று ", "ஐந்நூற்று ", "அறுநூற்று ", "எழுநூற்று ", "எண்ணூற்று ", "தொள்ளாயிரத்து "]

    n = max(0, min(1000, int(n)))
    if n == 1000:
        return "ஆயிரம்"
    if n < 10:
        return units[n]
    if n < 20:
        return teens[n - 10]
    if n < 100:
        if n % 10 == 0:
            return tens_exact[n // 10]
        return tens_prefix[n // 10] + units[n % 10]
    h = n // 100
    rem = n % 100
    if rem == 0:
        return hundreds_exact[h]
    return hundreds_prefix[h] + int_to_tamil(rem)


_HINDI_0_99 = [
    "शून्य", "एक", "दो", "तीन", "चार", "पांच", "छह", "सात", "आठ", "नौ",
    "दस", "ग्यारह", "बारह", "तेरह", "चौदह", "पंद्रह", "सोलह", "सत्रह", "अठारह", "उन्नीस",
    "बीस", "इक्कीस", "बाईस", "तेईस", "चौबीस", "पच्चीस", "छब्बीस", "सत्ताईस", "अट्ठाईस", "उनतीस",
    "तीस", "इकतीस", "बत्तीस", "तैंतीस", "चौंतीस", "पैंतीस", "छत्तीस", "सैंतीस", "अड़तीस", "उनतालीस",
    "चालीस", "इकतालीस", "बयालीस", "तैंतालीस", "चवालीस", "पैंतालीस", "छियालीस", "सैंतालीस", "अड़तालीस", "उनचास",
    "पचास", "इक्यावन", "बावन", "तिरपन", "चौवन", "पचपन", "छप्पन", "सत्तावन", "अट्ठावन", "उनसठ",
    "साठ", "इकसठ", "बासठ", "तिरसठ", "चौंसठ", "पैंसठ", "छियासठ", "सड़सठ", "अड़सठ", "उनहत्तर",
    "सत्तर", "इकहत्तर", "बहत्तर", "तिहत्तर", "चौहत्तर", "पचहत्तर", "छिहत्तर", "सतहत्तर", "अठहत्तर", "उनासी",
    "अस्सी", "इक्यासी", "बयासी", "तिरासी", "चौरासी", "पचासी", "छियासी", "सत्तासी", "अट्ठासी", "नवासी",
    "नब्बे", "इक्यानबे", "बानबे", "तिरानबे", "चौरानबे", "पचानबे", "छियानबे", "सत्तानबे", "अट्ठानबे", "निन्यानबे",
]


def int_to_hindi(n: int) -> str:
    """Converts integers 0-1000 into natural spoken Hindi words."""
    n = max(0, min(1000, int(n)))
    if n == 1000:
        return "एक हजार"
    if n < 100:
        return _HINDI_0_99[n]
    h = n // 100
    rem = n % 100
    prefix = f"{_HINDI_0_99[h]} सौ"
    return prefix if rem == 0 else f"{prefix} {_HINDI_0_99[rem]}"


def number_to_spoken(num_str: str, lang: str) -> str:
    """Converts integers or decimals like '2.5' or '2.0' into natural spoken native words."""
    if "." in num_str:
        parts = num_str.split(".", 1)
        try:
            whole = int(parts[0])
            frac_digits = parts[1]
        except ValueError:
            return num_str
        # Treat trailing zero decimals like 2.0 or 1.0 as clean whole numbers
        if set(frac_digits) == {"0"}:
            return number_to_spoken(str(whole), lang)
        if lang == "ta":
            if frac_digits == "5" and whole == 0:
                return "அரை"
            if frac_digits == "5" and whole == 1:
                return "ஒன்றரை"
            if frac_digits == "5" and whole == 2:
                return "இரண்டரை"
            frac_words = " ".join(int_to_tamil(int(d)) for d in frac_digits if d.isdigit())
            return f"{int_to_tamil(whole)} புள்ளி {frac_words}".strip()
        if lang == "hi":
            if frac_digits == "5" and whole == 0:
                return "आधा"
            if frac_digits == "5" and whole == 1:
                return "डेढ़"
            if frac_digits == "5" and whole == 2:
                return "ढाई"
            frac_words = " ".join(int_to_hindi(int(d)) for d in frac_digits if d.isdigit())
            return f"{int_to_hindi(whole)} दशमलव {frac_words}".strip()
        return f"{whole} point {' '.join(frac_digits)}"

    try:
        val = int(num_str)
    except ValueError:
        return num_str
    if lang == "ta":
        return int_to_tamil(val)
    if lang == "hi":
        return int_to_hindi(val)
    return str(val)


def normalize_for_speech(text: str, lang: str) -> str:
    """
    Replaces symbols, chemical abbreviations, units, percentages, and digits
    with natural spoken words in Tamil, Hindi, or English so native voices
    pronounce every word clearly without awkward English acronym spelling.
    """
    if not text:
        return ""

    if lang == "ta":
        replacements = [
            (r"\bWP\b", "தூள் மருந்து"),
            (r"\bEC\b", "திரவ மருந்து"),
            (r"\bSC\b", "திரவ மருந்து"),
            (r"\bWG\b", "குருணை மருந்து"),
            (r"\bDF\b", "குருணை மருந்து"),
            (r"\bSE\b", "திரவ மருந்து"),
            (r"\bNSKE\b", "வேப்பங்கொட்டை சாறு"),
            (r"\bPHI\b", "பாதுகாப்பு காத்திருப்பு காலம்"),
            (r"\bg/L\b", "கிராம் ஒரு லிட்டர் தண்ணீருக்கு"),
            (r"\bml/L\b", "மில்லிலிட்டர் ஒரு லிட்டர் தண்ணீருக்கு"),
            (r"கிராம்/லிட்டர்", "கிராம் ஒரு லிட்டர் தண்ணீருக்கு"),
            (r"மி\.லி", "மில்லிலிட்டர்"),
            (r"\s*\+\s*", " மற்றும் "),
            (r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)", lambda m: f"{number_to_spoken(m.group(1), 'ta')} முதல் {number_to_spoken(m.group(2), 'ta')}"),
            (r"(\d+(?:\.\d+)?)\s*%", lambda m: f"{number_to_spoken(m.group(1), 'ta')} சதவீதம்"),
            (r"\b(\d+(?:\.\d+)?)\b", lambda m: number_to_spoken(m.group(1), "ta")),
        ]
    elif lang == "hi":
        replacements = [
            (r"\bWP\b", "घुलनशील चूर्ण"),
            (r"\bEC\b", "तरल दवा"),
            (r"\bSC\b", "तरल घोल"),
            (r"\bWG\b", "दानेदार चूर्ण"),
            (r"\bDF\b", "दानेदार चूर्ण"),
            (r"\bSE\b", "तरल घोल"),
            (r"\bNSKE\b", "नीम के बीज का काढ़ा"),
            (r"\bPHI\b", "प्रतीक्षा अवधि"),
            (r"\bg/L\b", "ग्राम प्रति लीटर पानी"),
            (r"\bml/L\b", "मिलीलीटर प्रति लीटर पानी"),
            (r"ग्राम/लीटर", "ग्राम प्रति लीटर पानी"),
            (r"मिली", "मिलीलीटर"),
            (r"\s*\+\s*", " और "),
            (r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)", lambda m: f"{number_to_spoken(m.group(1), 'hi')} से {number_to_spoken(m.group(2), 'hi')}"),
            (r"(\d+(?:\.\d+)?)\s*%", lambda m: f"{number_to_spoken(m.group(1), 'hi')} प्रतिशत"),
            (r"\b(\d+(?:\.\d+)?)\b", lambda m: number_to_spoken(m.group(1), "hi")),
        ]
    else:
        replacements = [
            (r"\(NSKE\)", ""),
            (r"\bWP\b", "wettable powder"),
            (r"\bEC\b", "emulsifiable concentrate"),
            (r"\bSC\b", "suspension concentrate"),
            (r"\bWG\b", "water dispersible granules"),
            (r"\bDF\b", "dry flowable"),
            (r"\bNSKE\b", "neem seed kernel extract"),
            (r"\bPHI\b", "pre-harvest interval"),
            (r"\bg/L\b", "grams per liter"),
            (r"\bml/L\b", "milliliters per liter"),
            (r"\s*\+\s*", " plus "),
            (r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)", r"\1 to \2"),
            (r"(\d+(?:\.\d+)?)\s*%", r"\1 percent"),
        ]

    out = text
    for pattern, repl in replacements:
        out = re.sub(pattern, repl, out)

    # Clean redundant parentheses, duplicate punctuation, & spacing for smooth natural phrasing
    out = out.replace("(", ", ").replace(")", ", ")
    out = re.sub(r"\s+,", ",", out)
    out = re.sub(r",\s*,+", ",", out)
    out = re.sub(r"\s{2,}", " ", out)
    out = out.strip().rstrip(".। ")
    return out


class FarmerVoiceAssistant:
    # Speed presets tuned for farmer comprehension
    SPEED_PRESETS = {
        "slow": {"edge_rate": "-18%", "sherpa_speed": 0.82, "piper_length_scale": 1.22, "pyttsx_rate": 118, "espeak_wpm": "118"},
        "normal": {"edge_rate": "-10%", "sherpa_speed": 0.92, "piper_length_scale": 1.08, "pyttsx_rate": 135, "espeak_wpm": "135"},
        "fast": {"edge_rate": "+0%", "sherpa_speed": 1.00, "piper_length_scale": 1.00, "pyttsx_rate": 155, "espeak_wpm": "155"},
    }

    VOICE_PERSONAS = {
        "ta": {"female": "ta-IN-PallaviNeural", "male": "ta-IN-ValluvarNeural"},
        "hi": {"female": "hi-IN-SwaraNeural", "male": "hi-IN-MadhurNeural"},
        "en": {"female": "en-IN-NeerjaNeural", "male": "en-IN-PrabhatNeural"},
    }

    def __init__(self, tamil_voice: str = "ta-IN-PallaviNeural", allow_online: bool = True, speed: str = "slow"):
        self.tamil_voice = tamil_voice
        self.voice_gender = "male" if "Valluvar" in tamil_voice else "female"
        self.allow_online = allow_online
        self.speed = speed if speed in self.SPEED_PRESETS else "slow"
        self.piper_bin = shutil.which("piper")
        self.espeak_bin = shutil.which("espeak-ng") or shutil.which("espeak")
        self.last_backend = "none"
        self._sherpa_cache = {}

        self.crop_translations = {
            "ta": {"potato": "உருளைக்கிழங்கு", "tomato": "தக்காளி", "corn": "மக்காச்சோளம்", "rice": "நெல்"},
            "hi": {"potato": "आलू", "tomato": "टमाटर", "corn": "मक्का", "rice": "धान"},
        }

        self.disease_translations = {
            "ta": {
                "late_blight": "பின்பருவ இலைக்கருகல் நோய்",
                "early_blight": "முன்பருவ இலைக்கருகல் நோய்",
                "bacterial_leaf_blight": "பாக்டீரியா இலைக்கருகல் நோய்",
                "brown_spot": "பழுப்பு புள்ளி நோய்",
                "leaf_smut": "இலை கரிப்பூட்டை நோய்",
                "northern_leaf_blight": "வடக்கு இலைக்கருகல் நோய்",
                "common_rust": "இலை துரு நோய்",
                "common_rust_": "இலை துரு நோய்",
                "cercospora_leaf_spot": "சாம்பல் நிற இலைப்புள்ளி நோய்",
                "gray_leaf_spot": "சாம்பல் நிற இலைப்புள்ளி நோய்",
                "bacterial_spot": "பாக்டீரியா இலைப்புள்ளி நோய்",
                "leaf_mold": "இலை பூஞ்சாண அச்சு நோய்",
                "septoria_leaf_spot": "செப்டோரியா இலைப்புள்ளி நோய்",
                "spider_mites": "இரண்டு புள்ளி சிலந்திப் பேன் தாக்குதல்",
                "target_spot": "இலக்கு இலைப்புள்ளி நோய்",
                "tomato_yellow_leaf_curl_virus": "இலை சுருள் நச்சுயிரி நோய்",
                "tomato_mosaic_virus": "மொசைக் நச்சுயிரி நோய்",
                "healthy": "ஆரோக்கியமாக உள்ளது",
                "whitefly": "வெள்ளை ஈ பூச்சி தாக்குதல்",
                "aphid": "அசுவினி பூச்சி தாக்குதல்",
                "leafminer": "இலைத் துளைப்பான் புழு தாக்குதல்",
                "corn_borer": "தண்டுத் துளைப்பான் பூச்சி தாக்குதல்",
                "rice_leaf_roller": "நெல் இலைச் சுருட்டுப் புழு தாக்குதல்",
                "brown_planthopper": "புகையான் பழுப்பு தத்துப்பூச்சி தாக்குதல்",
            },
            "hi": {
                "late_blight": "पछेती झुलसा रोग",
                "early_blight": "अगेती झुलसा रोग",
                "bacterial_leaf_blight": "जीवाणु पत्ती झुलसा रोग",
                "brown_spot": "भूरा धब्बा रोग",
                "leaf_smut": "पत्ती कंडुवा रोग",
                "northern_leaf_blight": "पत्ती झुलसा रोग",
                "common_rust": "गेरुआ रतुआ रोग",
                "common_rust_": "गेरुआ रतुआ रोग",
                "cercospora_leaf_spot": "सर्कोस्पोरा धब्बा रोग",
                "gray_leaf_spot": "धूसर पत्ती धब्बा रोग",
                "bacterial_spot": "जीवाणु पत्ती धब्बा रोग",
                "leaf_mold": "पत्ती फफूंद रोग",
                "septoria_leaf_spot": "सेप्टोरिया पत्ती धब्बा रोग",
                "spider_mites": "लाल मकड़ी कीट प्रकोप",
                "target_spot": "टारगेट स्पॉट रोग",
                "tomato_yellow_leaf_curl_virus": "पत्ती मरोड़ विषाणु रोग",
                "tomato_mosaic_virus": "मोज़ेक विषाणु रोग",
                "healthy": "पूरी तरह स्वस्थ",
                "whitefly": "सफेद मक्खी कीट प्रकोप",
                "aphid": "माहू कीट प्रकोप",
                "leafminer": "पत्ती सुरंगक कीट प्रकोप",
                "corn_borer": "मक्का तना छेदक कीट प्रकोप",
                "rice_leaf_roller": "धान पत्ती लपेटक कीट प्रकोप",
                "brown_planthopper": "भूरा फुदका कीट प्रकोप",
            },
        }

    def set_voice_persona(self, gender: str = "female"):
        self.voice_gender = "male" if gender == "male" else "female"
        self.tamil_voice = self.VOICE_PERSONAS["ta"][self.voice_gender]

    def _normalize_key(self, text: str) -> str:
        s = text.lower().replace(" ", "_").replace("-", "_").strip()
        while "__" in s:
            s = s.replace("__", "_")
        return s

    def build_spoken_script(self, diagnostic_payload: dict, lang: str = "en") -> str:
        raw_crop = diagnostic_payload.get("crop", "Crop").lower()
        raw_disease = diagnostic_payload.get("disease", "disease").lower()
        norm_disease = self._normalize_key(raw_disease)

        severity_val = round(diagnostic_payload.get("severity_pct", 0.0))
        stage = diagnostic_payload.get("severity_stage", "Moderate")
        confidence = diagnostic_payload.get("confidence", 0.9)
        treatment = diagnostic_payload.get("treatment") or {}

        is_healthy = "healthy" in norm_disease
        gate_b_passed = (confidence >= 0.75) and bool(treatment.get("region_verified", True))

        lang = lang.lower() if lang in ["en", "ta", "hi"] else "en"

        cultural = normalize_for_speech(treatment.get("cultural_action", ""), lang)
        organic = normalize_for_speech(treatment.get("organic_remedy", ""), lang)
        chemical = normalize_for_speech(treatment.get("chemical_name", ""), lang)
        dosage = normalize_for_speech(treatment.get("chemical_dosage", ""), lang)
        phi_days = int(treatment.get("phi_days", 0) or 0)

        if lang == "ta":
            crop_ta = self.crop_translations["ta"].get(raw_crop, "பயிர்")
            disease_ta = next(
                (v for k, v in self.disease_translations["ta"].items() if k in norm_disease or norm_disease in k),
                norm_disease.replace("_", " "),
            )
            stage_ta_map = {
                "Mild": "ஆரம்ப நிலை",
                "Moderate": "மிதமான நிலை",
                "Severe": "தீவிர நிலை",
                "Healthy": "ஆரோக்கிய நிலை",
                "None": "ஆரோக்கிய நிலை",
                "Uncertain": "தெளிவற்ற நிலை",
            }
            stage_ta = stage_ta_map.get(stage, "மிதமான நிலை")
            sev_words = int_to_tamil(severity_val)
            phi_words = int_to_tamil(phi_days)

            if is_healthy:
                return (
                    f"வணக்கம் விவசாய பெருமக்களே! உழவர் பார்வை ஏ ஐ கள ஆய்வின்படி, "
                    f"உங்கள் {crop_ta} பயிர் முற்றிலும் ஆரோக்கியமாக உள்ளது. "
                    f"இலையில் நோய் பாதிப்பு பூஜ்ஜியம் சதவீதம். "
                    f"வழக்கமான பராமரிப்பாக, {cultural}. "
                    f"இயற்கை ஊட்டமாக, {organic}. நன்றி!"
                )

            script = (
                f"வணக்கம் விவசாய பெருமக்களே! உழவர் பார்வை ஏ ஐ கள ஆய்வின்படி, "
                f"உங்கள் {crop_ta} பயிரில், {disease_ta} இருப்பது கண்டறியப்பட்டுள்ளது. "
                f"இலையில் பாதிப்பின் அளவு சுமார் {sev_words} சதவீதம் ஆகும். இது {stage_ta} பாதிப்பாகும். "
                f"உடனடி வேளாண் பராமரிப்பாக, {cultural}. "
                f"இயற்கை மற்றும் உயிரியல் தீர்வாக, {organic}. "
            )
            raw_chem = treatment.get("chemical_name", "")
            if gate_b_passed and raw_chem and not any(raw_chem.startswith(x) for x in ["None", "இல்லை"]):
                chem_spoken = chemical if "மருந்து" in chemical else f"{chemical} மருந்தை"
                chem_spoken = chem_spoken.replace("தூள் மருந்து", "தூள் மருந்தை").replace("திரவ மருந்து", "திரவ மருந்தை")
                script += (
                    f"தேவைப்பட்டால் அங்கீகரிக்கப்பட்ட இரசாயன சிகிச்சையாக, {chem_spoken}, "
                    f"{dosage} என்ற அளவில் கலந்து தெளிக்கவும். "
                    f"மருந்து தெளித்த பின் அறுவடை செய்வதற்கு, {phi_words} நாட்கள் காத்திருக்க வேண்டும். நன்றி!"
                )
            else:
                script += "பாதுகாப்பு விதிப்படி இரசாயன மருந்து பரிந்துரை தவிர்க்கப்பட்டுள்ளது. இயற்கை முறைகளைப் பின்பற்றவும். நன்றி!"
            return script

        if lang == "hi":
            crop_hi = self.crop_translations["hi"].get(raw_crop, "फसल")
            disease_hi = next(
                (v for k, v in self.disease_translations["hi"].items() if k in norm_disease or norm_disease in k),
                norm_disease.replace("_", " "),
            )
            stage_hi_map = {"Mild": "शुरुआती", "Moderate": "मध्यम", "Severe": "गंभीर", "Healthy": "स्वस्थ", "None": "स्वस्थ", "Uncertain": "अनिश्चित"}
            stage_hi = stage_hi_map.get(stage, "मध्यम")
            sev_words_hi = int_to_hindi(severity_val)
            phi_words_hi = int_to_hindi(phi_days)

            if is_healthy:
                return (
                    f"नमस्ते किसान भाइयों! किसान दृष्टि एआई विश्लेषण के अनुसार, "
                    f"आपकी {crop_hi} की फसल पूरी तरह स्वस्थ है। इसमें किसी रोग का लक्षण नहीं है। "
                    f"नियमित देखभाल के लिए, {cultural}। "
                    f"जैविक संवर्धन के लिए, {organic}। धन्यवाद!"
                )

            script = (
                f"नमस्ते किसान भाइयों! किसान दृष्टि एआई विश्लेषण के अनुसार, "
                f"आपकी {crop_hi} की फसल में, {disease_hi} पाया गया है। "
                f"पत्ती में संक्रमण लगभग {sev_words_hi} प्रतिशत है, जो कि {stage_hi} स्तर पर है। "
                f"तत्काल कृषि उपाय के रूप में, {cultural}। "
                f"जैविक रोकथाम के लिए, {organic}। "
            )
            raw_chem = treatment.get("chemical_name", "")
            if gate_b_passed and raw_chem and not any(raw_chem.startswith(x) for x in ["None", "कोई नहीं"]):
                script += (
                    f"आवश्यकता पड़ने पर रासायनिक उपचार हेतु, {chemical}, {dosage} में मिलाकर छिड़कें। "
                    f"छिड़काव के बाद कटाई में कम से कम {phi_words_hi} दिनों का अंतर अवश्य रखें। धन्यवाद!"
                )
            else:
                script += "सुरक्षा नियम के कारण रासायनिक दवा रोकी गई है। जैविक उपाय अपनाएं। धन्यवाद!"
            return script

        if is_healthy:
            return (
                f"Greetings farmer! KisanDrishti AI field diagnostic confirms that your "
                f"{raw_crop.capitalize()} crop is completely healthy, with zero foliar infection. "
                f"For routine crop care: {cultural}. "
                f"For organic nourishment: {organic}. Thank you!"
            )

        script = (
            f"Greetings farmer! KisanDrishti AI field diagnostic confirms that your "
            f"{raw_crop.capitalize()} crop is affected by {raw_disease.replace('_', ' ').title()}. "
            f"Estimated leaf severity is {severity_val} percent, classified as {stage} stage. "
            f"Immediate cultural action: {cultural}. "
            f"Organic remedy: {organic}. "
        )
        raw_chem = treatment.get("chemical_name", "")
        if gate_b_passed and raw_chem and not raw_chem.startswith("None"):
            script += (
                f"Approved chemical treatment: apply {chemical}, at {dosage}. "
                f"Observe a pre-harvest safety waiting period of {phi_days} days. Thank you!"
            )
        else:
            script += "Chemical treatment is withheld under Gate B safety rules. Follow cultural and organic measures. Thank you!"
        return script

    def _get_sherpa_tts(self, lang: str):
        """
        Loads Sherpa-ONNX OfflineTts from models/tts/<lang>/.
        Keeps only ONE language model resident in RAM at a time to minimize memory footprint.
        """
        if sherpa_onnx is None:
            return None
        if lang in self._sherpa_cache:
            return self._sherpa_cache[lang]

        # Evict any previously loaded language model to keep RAM low
        if self._sherpa_cache:
            self._sherpa_cache.clear()
            import gc
            gc.collect()

        lang_dir = os.path.join(SHERPA_MODELS_DIR, lang)
        if not os.path.isdir(lang_dir):
            return None

        onnx_files = [f for f in os.listdir(lang_dir) if f.endswith(".onnx")]
        tokens_path = os.path.join(lang_dir, "tokens.txt")
        if not onnx_files or not os.path.exists(tokens_path):
            return None

        model_path = os.path.join(lang_dir, onnx_files[0])
        data_dir = os.path.join(lang_dir, "espeak-ng-data")
        # For MMS-TTS (character input, no espeak-ng-data), look for lexicon or leave data_dir=""
        vits_cfg = sherpa_onnx.OfflineTtsVitsModelConfig(
            model=model_path,
            tokens=tokens_path,
            data_dir=data_dir if os.path.isdir(data_dir) else "",
        )
        cfg = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(vits=vits_cfg, provider="cpu", num_threads=4)
        )
        if not cfg.validate():
            return None
        tts = sherpa_onnx.OfflineTts(cfg)
        self._sherpa_cache[lang] = tts
        return tts

    def _find_piper_model(self, lang: str) -> str:
        if not os.path.exists(PIPER_MODELS_DIR):
            return ""
        for fname in os.listdir(PIPER_MODELS_DIR):
            if fname.endswith(".onnx") and (f"{lang}_" in fname or f"-{lang}" in fname or fname.startswith(lang)):
                return os.path.join(PIPER_MODELS_DIR, fname)
        return ""

    async def _synthesize_edge_tts(self, text: str, lang: str, out_path: str, rate: str):
        import edge_tts
        voice = self.VOICE_PERSONAS.get(lang, self.VOICE_PERSONAS["en"]).get(self.voice_gender, "en-IN-NeerjaNeural")
        if lang == "ta" and self.tamil_voice:
            voice = self.tamil_voice
        comm = edge_tts.Communicate(text, voice, rate=rate, pitch="+0Hz")
        await comm.save(out_path)

    def speak(self, text: str, lang: str = "en", output_filename: str = None, speed: str = None) -> str:
        """
        Synthesizes native, clearly paced audio in Tamil, Hindi, or English.
        Priority:
          1. Sherpa-ONNX offline neural VITS (100% offline, models/tts/<lang>/)
          2. Piper TTS offline CLI (100% offline, models/piper/)
          3. Offline Disk Cache (data/audio_cache/) for repeated advisories
          4. Native Neural Edge-TTS (ta-IN / hi-IN / en-IN native voices, auto-cached offline!)
          5. Last-resort offline eSpeak-NG / pyttsx3
        """
        lang = lang.lower() if lang in ["en", "ta", "hi"] else "en"
        spd_key = speed if speed in self.SPEED_PRESETS else self.speed
        preset = self.SPEED_PRESETS[spd_key]

        base_wav = output_filename or os.path.join(AUDIO_DIR, f"advisory_{lang}_{int(time.time()*1000)}.wav")
        cache_key = hashlib.sha256(f"{lang}|{self.voice_gender}|{spd_key}|{text}".encode("utf-8")).hexdigest()[:16]
        cached_mp3 = os.path.join(AUDIO_CACHE_DIR, f"cache_{lang}_{self.voice_gender}_{spd_key}_{cache_key}.mp3")

        # 1. Offline Sherpa-ONNX Native Neural VITS (Live Dynamic Offline Speech)
        sherpa_tts = self._get_sherpa_tts(lang)
        if sherpa_tts is not None:
            try:
                synth_text = text
                # Tamil MMS-TTS uses character-level tokens without punctuation symbols like . ! : -
                if lang == "ta" and not os.path.isdir(os.path.join(SHERPA_MODELS_DIR, "ta", "espeak-ng-data")):
                    synth_text = re.sub(r"[.,!:;\-()\[\]\"']", " ", synth_text)
                    synth_text = re.sub(r"\s{2,}", " ", synth_text).strip().lower()
                audio = sherpa_tts.generate(synth_text, sid=0, speed=preset["sherpa_speed"])
                if len(audio.samples) > 0:
                    sherpa_onnx.write_wave(base_wav, audio.samples, audio.sample_rate)
                    self.last_backend = f"sherpa-onnx neural ({lang}, {spd_key}, offline)"
                    return base_wav
            except Exception:
                pass

        # 2. Offline Piper CLI
        piper_model = self._find_piper_model(lang)
        if self.piper_bin and piper_model:
            try:
                subprocess.run(
                    [
                        self.piper_bin,
                        "--model", piper_model,
                        "--length_scale", str(preset["piper_length_scale"]),
                        "--output_file", base_wav,
                    ],
                    input=text,
                    text=True,
                    check=True,
                    timeout=30,
                )
                if os.path.exists(base_wav) and os.path.getsize(base_wav) > 500:
                    self.last_backend = f"piper-tts ({lang}, {spd_key}, offline)"
                    return base_wav
            except Exception:
                pass

        # 3. Cached Native Speaker Audio (Works 100% Offline once cached)
        if os.path.exists(cached_mp3) and os.path.getsize(cached_mp3) > 1000:
            mp3_out = base_wav.replace(".wav", ".mp3")
            shutil.copy2(cached_mp3, mp3_out)
            self.last_backend = f"native-voice-cache ({lang}, {spd_key}, offline)"
            return mp3_out

        # 4. Native Speaker Neural Voices (ta-IN / hi-IN / en-IN) — auto-cached for offline replay
        if self.allow_online:
            mp3_out = base_wav.replace(".wav", ".mp3")
            try:
                coro = self._synthesize_edge_tts(text, lang, mp3_out, rate=preset["edge_rate"])
                try:
                    asyncio.get_running_loop()
                    # Already inside an event loop (e.g. async web handler): run in worker thread
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                        pool.submit(asyncio.run, coro).result(timeout=30)
                except RuntimeError:
                    asyncio.run(coro)
                if os.path.exists(mp3_out) and os.path.getsize(mp3_out) > 1000:
                    shutil.copy2(mp3_out, cached_mp3)
                    voice_used = self.VOICE_PERSONAS[lang][self.voice_gender]
                    self.last_backend = f"native-neural ({voice_used}, {spd_key})"
                    return mp3_out
            except Exception:
                pass

        # 5. Last-resort offline eSpeak-NG / pyttsx3
        if self.espeak_bin:
            try:
                espeak_lang = {"ta": "ta", "hi": "hi", "en": "en-in"}.get(lang, "en")
                subprocess.run(
                    [self.espeak_bin, "-v", espeak_lang, "-s", preset["espeak_wpm"], "-w", base_wav, text],
                    check=True,
                    timeout=30,
                )
                if os.path.exists(base_wav) and os.path.getsize(base_wav) > 500:
                    self.last_backend = f"espeak-ng ({lang}, {spd_key}, offline)"
                    return base_wav
            except Exception:
                pass

        if pyttsx3 is not None:
            try:
                engine = pyttsx3.init()
                engine.setProperty("rate", preset["pyttsx_rate"])
                engine.save_to_file(text, base_wav)
                engine.runAndWait()
                if os.path.exists(base_wav) and os.path.getsize(base_wav) > 500:
                    self.last_backend = f"pyttsx3 ({lang}, {spd_key}, offline)"
                    return base_wav
            except Exception:
                pass

        self.last_backend = "text-only (no TTS backend)"
        return ""
