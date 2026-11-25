"""
Deterministic SQLite Knowledge Base for KisanDrishti AI.
Contains verified ICAR, TNAU & CIBRC records across 4 crops (20 classes):
- Potato (Solanum tuberosum)
- Tomato (Solanum lycopersicum)
- Corn / Maize (Zea mays)
- Rice / Paddy (Oryza sativa)

Trilingual Support:
- English (CIBRC / ICAR National standard)
- Tamil (TNAU Agritech Portal standard - 100% Pure Native Tamil)
- Hindi (ICAR Krishi Vigyan Kendra standard - 100% Pure Native Hindi)

Schema includes 24 regulatory & agronomic columns including scientific pathogen name,
verified agency citation, zone applicability, biological compatibility notes, and
borderline 3-point symptom checklists.
"""
import os
import sqlite3

DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "icar_agronomic_kb.sqlite")
)

VERIFIED_REGIONS = {
    "National (ICAR Baseline)": ["All Districts"],
    "Tamil Nadu": ["Coimbatore", "Thanjavur", "Madurai", "Erode", "Salem", "Dindigul", "Krishnagiri", "Tirunelveli"],
    "Uttar Pradesh": ["Lucknow", "Varanasi", "Agra", "Kanpur", "Meerut"],
    "Punjab": ["Ludhiana", "Amritsar", "Jalandhar", "Patiala"],
    "Maharashtra": ["Pune", "Nashik", "Nagpur", "Kolhapur"],
    "Karnataka": ["Bengaluru Rural", "Mysuru", "Belagavi", "Dharwad"],
    "Bihar": ["Patna", "Nalanda", "Muzaffarpur", "Bhagalpur"],
}


class ICARKnowledgeBase:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.create_and_seed()

    def create_and_seed(self):
        cursor = self.conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS treatment_guidelines")
        # 24 columns covering identity, pathogen, trilingual cultural/organic/chemical/dosage,
        # PHI, regulatory citations, regional zone, bio-compatibility, and 3-point checklists
        cursor.execute("""
            CREATE TABLE treatment_guidelines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crop TEXT NOT NULL,
                diagnosis TEXT NOT NULL,
                pathogen_scientific TEXT NOT NULL,
                stage TEXT NOT NULL,
                cultural_en TEXT NOT NULL,
                organic_en TEXT NOT NULL,
                chemical_en TEXT NOT NULL,
                dosage_en TEXT NOT NULL,
                cultural_ta TEXT NOT NULL,
                organic_ta TEXT NOT NULL,
                chemical_ta TEXT NOT NULL,
                dosage_ta TEXT NOT NULL,
                cultural_hi TEXT NOT NULL,
                organic_hi TEXT NOT NULL,
                chemical_hi TEXT NOT NULL,
                dosage_hi TEXT NOT NULL,
                phi_days INTEGER NOT NULL,
                source_citation TEXT NOT NULL,
                zone_applicability TEXT NOT NULL,
                bio_compatibility_note TEXT NOT NULL,
                checklist_en TEXT NOT NULL,
                checklist_ta TEXT NOT NULL,
                checklist_hi TEXT NOT NULL
            );
        """)

        guidelines = [
            # =====================================================================
            # POTATO (3)
            # =====================================================================
            (
                "Potato", "late_blight", "Phytophthora infestans", "Moderate",
                "Halt overhead sprinkler irrigation immediately. Hill up soil around potato tubers to shield against spore wash. Prune and incinerate infected vines outside the field.",
                "Spray 5% Neem Seed Kernel Extract (NSKE) or cow urine slurry (10%) during early morning hours.",
                "Cymoxanil 8% + Mancozeb 64% WP", "2.0-2.5 g/L water",
                "மேலிருந்து தெளிக்கும் நீர்ப்பாசனத்தை உடனே நிறுத்தவும். கிழங்குகளைச் சுற்றி மண் அணைத்து மூடவும். பாதிக்கப்பட்ட இலைகளை வெட்டி வயலுக்கு வெளியே அப்புறப்படுத்தி அழிக்கவும்.",
                "ஐந்து சதவீத வேப்பங்கொட்டை சாறு அல்லது பத்து சதவீத பசுஞ்சாணக் கரைசலை காலையில் இலைகளில் நன்கு தெளிக்கவும்.",
                "சைமோக்சனில் 8% + மேன்கோசெப் 64% தூள் மருந்து",
                "ஒரு லிட்டர் தண்ணீருக்கு 2.0 முதல் 2.5 கிராம்",
                "फव्वारा सिंचाई तुरंत बंद कर दें। आलू के कंदों पर मिट्टी चढ़ाएं। रोगग्रस्त पत्तों को काटकर खेत से बाहर जला दें।",
                "पांच प्रतिशत नीम के बीज का काढ़ा अथवा दस प्रतिशत देसी गोमूत्र और गोबर का घोल सुबह के समय छिड़कें।",
                "साइमोक्सानिल 8% + मैंकोजेब 64% घुलनशील चूर्ण",
                "2.0 से 2.5 ग्राम प्रति लीटर पानी",
                7,
                "ICAR-CPRI Shimla / CIBRC Label",
                "National (ICAR Baseline), Tamil Nadu, Uttar Pradesh, Punjab, Bihar, Karnataka",
                "Follow product label interval before applying foliar bio-agents after chemical fungicide spray.",
                "1. Water-soaked dark green/brown patches on leaf margins? | 2. White cottony fungal growth on leaf underside in cool morning dew? | 3. Rapidly spreading blight during humid/cloudy weather?",
                "1. இலை ஓரங்களில் நீர் கோர்த்த கரும்பழுப்புத் திட்டுகள் உள்ளதா? | 2. காலைப் பனியில் இலை அடிப்பகுதியில் வெள்ளை பூஞ்சாண வளர்ச்சி உள்ளதா? | 3. ஈரப்பதமான காலநிலையில் நோய் வேகமாகப் பரவுகிறதா?",
                "1. पत्ती के किनारों पर पानी से भीगे गहरे भूरे धब्बे हैं? | 2. सुबह की नमी में पत्ती की निचली सतह पर सफेद रुई जैसी फफूंद है? | 3. ठंडे व नम मौसम में रोग तेजी से फैल रहा है?"
            ),
            (
                "Potato", "early_blight", "Alternaria solani", "Moderate",
                "Maintain weed-free ridges to enhance canopy aeration. Clip off diseased bottom leaves touching wet soil.",
                "Spray 5% Neem oil emulsion or foliar spray of Pseudomonas fluorescens @ 10 g/L.",
                "Mancozeb 75% WP", "2.0 g/L water",
                "செடிகளைச் சுற்றி களைகளை நீக்கி போதிய காற்றோட்டம் ஏற்படுத்தவும். மண்ணைத் தொடும் பாதிக்கப்பட்ட கீழ் இலைகளை உடனே அப்புறப்படுத்தவும்.",
                "ஐந்து சதவீத வேப்பெண்ணெய் கரைசல் அல்லது சூடோமோனாஸ் புளோரசன்ஸ் உயிரியல் காரணியை 10 கிராம்/லிட்டர் அளவில் தெளிக்கவும்.",
                "மேன்கோசெப் 75% தூள் மருந்து",
                "ஒரு லிட்டர் தண்ணீருக்கு 2.0 கிராம்",
                "पौधों के आसपास से खरपतवार हटाएं ताकि हवा का संचार बना रहे। जमीन को छूने वाली रोगी निचली पत्तियों को काट दें।",
                "पांच प्रतिशत नीम के तेल का घोल अथवा स्यूडोमोनास फ्लोरोसेंस 10 ग्राम/लीटर का छिड़काव करें।",
                "मैंकोजेब 75% घुलनशील चूर्ण",
                "2.0 ग्राम प्रति लीटर पानी",
                5,
                "ICAR-CPRI / TNAU Crop Protection Guide",
                "National (ICAR Baseline), Tamil Nadu, Uttar Pradesh, Punjab, Bihar, Karnataka",
                "Avoid tank-mixing copper/synthetic dithiocarbamates directly with live Pseudomonas formulations.",
                "1. Concentric target-board rings inside brown spots? | 2. Symptoms start on older lower leaves first? | 3. Yellow halo surrounding dry necrotic spots?",
                "1. பழுப்புப் புள்ளிகளுக்குள் வளையம் போன்ற வட்டக் கோடுகள் உள்ளதா? | 2. அறிகுறிகள் கீழ் உள்ள முதிர்ந்த இலைகளில் முதலில் தோன்றியதா? | 3. காய்ந்த புள்ளிகளைச் சுற்றி மஞ்சள் வளையம் உள்ளதா?",
                "1. भूरे धब्बों के भीतर गोल छल्ले (टारगेट रिंग) दिखते हैं? | 2. लक्षण पहले नीचे की पुरानी पत्तियों पर शुरू हुए? | 3. सूखे धब्बों के चारों ओर पीला घेरा है?"
            ),
            (
                "Potato", "healthy", "No Pathogen Detected", "None",
                "Crop is robust and free from foliar pathogens. Continue scheduled furrow irrigation and balanced NPK nutrition.",
                "Apply Panchagavya 3% or vermiwash as an organic foliar growth promoter.",
                "None", "None",
                "உருளைக்கிழங்கு பயிர் சிறந்த ஆரோக்கியத்துடன் உள்ளது. வழக்கமான பாசனம் மற்றும் சீரான உர மேலாண்மையைத் தொடரவும்.",
                "பயிர் வளர்ச்சியை ஊக்குவிக்க மூன்று சதவீத பஞ்சகவ்யா கரைசலை இலைகளில் தெளிக்கலாம்.",
                "இல்லை", "இல்லை",
                "आलू की फसल पूरी तरह स्वस्थ है। नियमित सिंचाई एवं संतुलित उर्वरक प्रबंधन जारी रखें।",
                "फसल की अच्छी बढ़वार के लिए तीन प्रतिशत पंचगव्य या वर्मीवॉश का छिड़काव करें।",
                "कोई नहीं", "कोई नहीं",
                0,
                "ICAR-CPRI / TNAU Agronomy",
                "National (ICAR Baseline), Tamil Nadu, Uttar Pradesh, Punjab, Bihar, Karnataka",
                "Organic foliar boosters are fully compatible with routine crop management.",
                "1. Uniform green foliage across upper and lower leaves? | 2. No necrotic spots or wilting? | 3. Normal stem turgor?",
                "1. மேல் மற்றும் கீழ் இலைகள் சீரான பச்சை நிறத்தில் உள்ளதா? | 2. கரும்புள்ளிகள் அல்லது வாடல் அறிகுறி இல்லையா? | 3. தண்டு உறுதியாக உள்ளதா?",
                "1. ऊपर व नीचे की पत्तियां एकसमान हरी हैं? | 2. कोई धब्बे या मुरझाने के लक्षण नहीं हैं? | 3. तना स्वस्थ व मजबूत है?"
            ),

            # =====================================================================
            # RICE / PADDY (3)
            # =====================================================================
            (
                "Rice", "bacterial_leaf_blight", "Xanthomonas oryzae", "Severe",
                "Drain standing field water for 3 to 4 days to check bacterial spread. Strictly suspend urea top-dressing.",
                "Spray fresh cow dung slurry extract (20%) filtered through fine muslin cloth.",
                "Streptocycline 90:10 + Copper Oxychloride 50% WP", "0.1 g/L + 1.5 g/L water",
                "வயலில் தேங்கியுள்ள தண்ணீரை மூன்று முதல் நான்கு நாட்களுக்கு முழுமையாக வடித்துவிடவும். அதிகமாக யூரியா போன்ற தழைச்சத்து உரங்கள் இடுவதை முற்றிலும் தவிர்க்கவும்.",
                "இருபது சதவீத பசுஞ்சாணம் கலந்த கரைசலை மெல்லிய துணியில் வடிகட்டி இலைகளில் நன்கு படும்படி தெளிக்கவும்.",
                "ஸ்ட்ரெப்டோசைக்ளின் 90% + காப்பர் ஆக்ஸிகுளோரைடு 50% தூள் மருந்து",
                "ஒரு லிட்டர் தண்ணீருக்கு 0.1 கிராம் ஸ்ட்ரெப்டோசைக்ளின் + 1.5 கிராம் காப்பர் ஆக்ஸிகுளோரைடு",
                "खेत से तीन से चार दिनों के लिए पानी पूरी तरह निकाल दें। यूरिया खाद का छिड़काव तुरंत रोक दें।",
                "बीस प्रतिशत ताजे गाय के गोबर का घोल कपड़े से छानकर पत्तियों पर अच्छी तरह छिड़कें।",
                "स्ट्रेप्टोसाइक्लिन 90% + कॉपर ऑक्सीक्लोराइड 50%",
                "0.1 ग्राम स्ट्रेप्टोसाइक्लिन + 1.5 ग्राम कॉपर ऑक्सीक्लोराइड प्रति लीटर पानी",
                15,
                "TNAU Rice Portal / ICAR-IIRR / CIBRC",
                "National (ICAR Baseline), Tamil Nadu, Punjab, Uttar Pradesh, Bihar, Karnataka",
                "Antibiotic-copper mixtures should not be mixed with live bacterial bio-controls (Pseudomonas).",
                "1. Straw-yellow wavy stripes starting from leaf tips/margins? | 2. Milky bacterial ooze visible on cut leaf in clear water? | 3. Standing water and high nitrogen usage recently?",
                "1. இலை நுனி அல்லது ஓரங்களில் மஞ்சள் நிற அலை போன்ற கோடுகள் உள்ளதா? | 2. வெட்டிய இலையை சுத்தமான நீரில் வைத்தால் பால் போன்ற பாக்டீரியா கசிவு தெரிகிறதா? | 3. சமீபத்தில் அதிக யூரியா மற்றும் தேங்கிய நீர் இருந்ததா?",
                "1. पत्ती की नोक या किनारों से पीली लहरदार धारियां शुरू हो रही हैं? | 2. कटी पत्ती को साफ पानी में रखने पर दूधिया जीवाणु स्राव दिखता है? | 3. खेत में अधिक पानी व यूरिया का उपयोग हुआ था?"
            ),
            (
                "Rice", "brown_spot", "Bipolaris oryzae", "Moderate",
                "Apply recommended potassium and silicon fertilizers to strengthen cell walls. Maintain shallow standing water.",
                "Foliar spray of Pseudomonas fluorescens @ 10 g/L or 5% Neem oil emulsion.",
                "Propiconazole 25% EC (or Mancozeb 75% WP)", "1.0 ml/L (or 2.0 g/L) water",
                "நிலத்தில் பொட்டாஷ் உரங்களை பரிந்துரைக்கப்பட்ட அளவில் இடவும். நிலத்தில் சீரான ஈரப்பதம் இருக்குமாறு பாசனம் பராமரிக்கவும்.",
                "சூடோமோனாஸ் புளோரசன்ஸ் உயிரியல் காரணியை ஒரு லிட்டர் தண்ணீருக்கு 10 கிராம் என்ற அளவில் கலந்து தெளிக்கவும்.",
                "புரோபிகோனசோல் 25% EC (அல்லது மேன்கோசெப் 75% WP)",
                "ஒரு லிட்டர் தண்ணீருக்கு 1.0 மி.லி (அல்லது 2.0 கிராம்)",
                "खेत में पोटाश खाद की संतुलित मात्रा डालें। मिट्टी में पर्याप्त नमी बनाए रखने के लिए नियमित सिंचाई करें।",
                "स्यूडोमोनास फ्लोरोसेंस 10 ग्राम प्रति लीटर पानी में मिलाकर छिड़कें।",
                "प्रोपिकोनाज़ोल 25% EC (या मैंकोजेब 75% WP)",
                "1.0 मिली (या 2.0 ग्राम) प्रति लीटर पानी",
                12,
                "TNAU Agritech / ICAR-IIRR / CIBRC",
                "National (ICAR Baseline), Tamil Nadu, Bihar, Uttar Pradesh, Punjab",
                "Check soil nutrient deficiency; do not mix triazole fungicides with live bio-agent sprays.",
                "1. Oval sesame-seed-shaped brown spots with yellow margin? | 2. Spots present on both leaves and grain glumes? | 3. Field experiencing moisture stress or low potash?",
                "1. எள் விதை வடிவத்தில் மஞ்சள் ஓரத்துடன் கூடிய பழுப்புப் புள்ளிகள் உள்ளதா? | 2. இலைகளிலும் நெல் மணிகளிலும் புள்ளிகள் உள்ளதா? | 3. மண்ணில் ஈரப்பதம் அல்லது பொட்டாஷ் குறைபாடு உள்ளதா?",
                "1. तिल के दाने जैसे अंडाकार भूरे धब्बे पीले किनारे के साथ हैं? | 2. धब्बे पत्तियों और दानों दोनों पर दिख रहे हैं? | 3. खेत में नमी या पोटाश की कमी है?"
            ),
            (
                "Rice", "leaf_smut", "Entyloma oryzae", "Moderate",
                "Collect and burn post-harvest crop stubbles. Avoid over-application of nitrogenous fertilizers.",
                "Foliar application of 5% Neem oil extract or bio-fungicide Trichoderma per label.",
                "Copper Oxychloride 50% WP", "2.5 g/L water",
                "அறுவடைக்கு பின் பாதிக்கப்பட்ட பயிர் தாள்களை சேகரித்து எரிக்கவும். தழைச்சத்து உரங்களை பரிந்துரைக்கப்பட்ட அளவில் மட்டும் இடவும்.",
                "ஐந்து சதவீத வேப்பெண்ணெய் கரைசல் அல்லது டிரைக்கோடெர்மா உயிரியல் பூஞ்சாணக் கொல்லியை தெளிக்கவும்.",
                "காப்பர் ஆக்ஸிகுளோரைடு 50% தூள் மருந்து",
                "ஒரு லிட்டர் தண்ணீருக்கு 2.5 கிராம்",
                "कटाई के बाद अवशेषों को एकत्र करके नष्ट करें। नाइट्रोजन खाद का अत्यधिक उपयोग न करें।",
                "पांच प्रतिशत नीम के तेल का घोल या ट्राइकोडर्मा का छिड़काव करें।",
                "कॉपर ऑक्सीक्लोराइड 50% घुलनशील चूर्ण",
                "2.5 ग्राम प्रति लीटर पानी",
                10,
                "ICAR-IIRR / CIBRC Label",
                "National (ICAR Baseline), Tamil Nadu, Bihar, Uttar Pradesh",
                "Apply copper fungicides separately from Trichoderma bio-inputs per product label guidance.",
                "1. Small black angular raised spots scattered on leaf blade? | 2. Spots do not easily coalesce into long streaks? | 3. Mostly appears on older lower leaves near maturity?",
                "1. இலைப் பரப்பில் சிறிய கருப்பு நிற சதுரப் புள்ளிகள் சிதறியுள்ளதா? | 2. புள்ளிகள் நீளக் கோடுகளாக இணையாமல் தனித்தனியே உள்ளதா? | 3. முதிர்ந்த கீழ் இலைகளில் அதிகம் காணப்படுகிறதா?",
                "1. पत्ती पर छोटे काले कोणीय उभरे धब्बे बिखरे हुए हैं? | 2. धब्बे लंबी धारियों में नहीं मिल रहे? | 3. मुख्यतः पुरानी निचली पत्तियों पर दिखते हैं?"
            ),

            # =====================================================================
            # CORN / MAIZE (4)
            # =====================================================================
            (
                "Corn", "northern_leaf_blight", "Exserohilum turcicum", "Severe",
                "Deep-plow crop residues after harvest to bury fungal conidia. Maintain balanced potash levels.",
                "Foliar spray of Trichoderma harzianum @ 5 g/L or 5% Neem Seed Kernel Extract.",
                "Mancozeb 75% WP (or Azoxystrobin + Difenoconazole)", "2.5 g/L (or 1.0 ml/L) water",
                "அறுவடைக்குப் பிறகு பாதிக்கப்பட்ட பயிர் கழிவுகளை ஆழமாக உழுது மண்ணில் புதைக்கவும். சமச்சீரான பொட்டாஷ் உரங்களை இடவும்.",
                "டிரைக்கோடெர்மா உயிரியல் பூஞ்சாணக் கொல்லியை ஒரு லிட்டர் தண்ணீருக்கு 5 கிராம் வீதம் கலந்து தெளிக்கவும்.",
                "மேன்கோசெப் 75% தூள் மருந்து (அல்லது அசாக்ஸிஸ்ட்ரோபின் + டைபினோகோனசோல்)",
                "ஒரு லிட்டர் தண்ணீருக்கு 2.5 கிராம் (அல்லது 1.0 மி.லி)",
                "कटाई के बाद संक्रमित फसल अवशेषों को गहरी जुताई करके मिट्टी में दबा दें। संतुलित पोटाश खाद डालें।",
                "ट्राइकोडर्मा जैव कवकनाशी 5 ग्राम प्रति लीटर पानी में मिलाकर छिड़कें।",
                "मैंकोजेब 75% घुलनशील चूर्ण (या एज़ोक्सीस्ट्रोबिन + डाइफेनोकोनाज़ोल)",
                "2.5 ग्राम (या 1.0 मिली) प्रति लीटर पानी",
                14,
                "ICAR-IIMR / TNAU Maize Guide / CIBRC",
                "National (ICAR Baseline), Tamil Nadu, Karnataka, Bihar, Maharashtra",
                "Observe label waiting period between chemical fungicide sprays and Trichoderma applications.",
                "1. Long cigar-shaped grayish-green to tan lesions (2.5-15 cm)? | 2. Lesions start on lower leaves and progress upward? | 3. Dark sooty spore layer visible in humid weather?",
                "1. சுருட்டு வடிவிலான சாம்பல்-பச்சை அல்லது பழுப்புப் புள்ளிகள் உள்ளதா? | 2. நோய் கீழ் இலைகளில் தொடங்கி மேல் நோக்கிப் பரவுகிறதா? | 3. ஈரப்பதத்தில் புள்ளிகளில் கருப்பு தூள் படிவம் உள்ளதா?",
                "1. सिगार के आकार के लंबे भूरे-स्लेटी धब्बे हैं? | 2. धब्बे नीचे की पत्तियों से ऊपर की ओर बढ़ रहे हैं? | 3. नमी में धब्बों पर काले बीजाणु की परत दिखती है?"
            ),
            (
                "Corn", "common_rust", "Puccinia sorghi", "Moderate",
                "Ensure adequate row-to-row spacing to reduce canopy humidity. Rogue out heavily infested early plants.",
                "Spray bio-control agent Bacillus subtilis @ 5 g/L water.",
                "Azoxystrobin 18.2% + Difenoconazole 11.4% SC (or Mancozeb 75% WP)", "1.0 ml/L (or 2.0 g/L) water",
                "பயிர்களுக்கு இடையே போதிய இடைவெளி விட்டு நல்ல காற்றோட்டம் ஏற்படுத்தவும். ஆரம்பத்தில் தீவிரமாக தாக்கப்பட்ட செடிகளை அப்புறப்படுத்தவும்.",
                "பேசில்லஸ் சப்டிலிஸ் அல்லது சூடோமோனாஸ் உயிரியல் கரைசலை இலைகளில் தெளிக்கவும்.",
                "அசாக்ஸிஸ்ட்ரோபின் 18.2% + டைபினோகோனசோல் 11.4% திரவ மருந்து",
                "ஒரு லிட்டர் தண்ணீருக்கு 1.0 மில்லிலிட்டர்",
                "हवा के संचार के लिए पौधों के बीच उचित दूरी रखें। अत्यधिक संक्रमित शुरुआती पौधों को उखाड़कर नष्ट करें।",
                "बैसिलस सबटिलिस 5 ग्राम प्रति लीटर पानी में मिलाकर छिड़कें।",
                "एज़ोक्सीस्ट्रोबिन 18.2% + डाइफेनोकोनाज़ोल 11.4% SC",
                "1.0 मिलीलीटर प्रति लीटर पानी",
                10,
                "ICAR-IIMR / CIBRC Label",
                "National (ICAR Baseline), Tamil Nadu, Karnataka, Maharashtra, Bihar",
                "Separate foliar bio-agent sprays from broad-spectrum fungicides per product label.",
                "1. Raised brick-red/cinnamon pustules on both upper and lower leaf surfaces? | 2. Powdery rust spores rub off onto fingers? | 3. Cool temperatures with heavy dew?",
                "1. இலையின் மேல் மற்றும் கீழ் பக்கங்களில் செங்கல் சிவப்பு கொப்புளங்கள் உள்ளதா? | 2. தொட்டால் விரலில் துரு போன்ற பொடி ஒட்டுகிறதா? | 3. குளிர்ச்சியான பனி காலநிலையில் தோன்றியதா?",
                "1. पत्ती की ऊपरी व निचली दोनों सतहों पर ईंट जैसे लाल फफोले हैं? | 2. छूने पर उंगलियों में जंग जैसा पाउडर लगता है? | 3. ठंडी और ओस वाली परिस्थितियों में संक्रमण बढ़ा?"
            ),
            (
                "Corn", "cercospora_leaf_spot", "Cercospora zeae-maydis", "Moderate",
                "Practice crop rotation with non-host leguminous crops. Avoid surface pooling of irrigation water.",
                "Spray 5% Neem Seed Kernel Extract (NSKE) during morning hours.",
                "Pyraclostrobin 133 g/L + Epoxiconazole 50 g/L SE", "1.0 ml/L water",
                "ஒரே நிலத்தில் தொடர்ந்து மக்காச்சோளம் பயிரிடுவதைத் தவிர்த்து பயறு வகை பயிர்களுடன் பயிர் சுழற்சி செய்யவும். தண்ணீர் தேங்குவதைத் தவிர்க்கவும்.",
                "ஐந்து சதவீத வேப்பங்கொட்டை சாறு காலையில் இலைகளில் படும்படி தெளிக்கவும்.",
                "பைராக்ளோஸ்ட்ரோபின் + எபோக்ஸிகோனசோல் திரவ மருந்து",
                "ஒரு லிட்டர் தண்ணீருக்கு 1.0 மில்லிலிட்டர்",
                "फसल चक्र अपनाएं तथा दलहनी फसलों की बुवाई करें। खेत में पानी को रुकने न दें।",
                "सुबह के समय पांच प्रतिशत नीम के बीज के काढ़े का छिड़काव करें।",
                "पाइराक्लोस्ट्रोबिन + एपॉक्सीकोनाज़ोल तरल",
                "1.0 मिलीलीटर प्रति लीटर पानी",
                14,
                "ICAR-IIMR / CIBRC",
                "National (ICAR Baseline), Karnataka, Maharashtra, Tamil Nadu",
                "Observe label PHI strictly before harvesting green fodder or cobs.",
                "1. Rectangular tan-gray lesions restricted strictly by parallel leaf veins? | 2. Lesions look blocky/matchstick shaped? | 3. Continuous maize cultivation in the same plot?",
                "1. இலை நரம்புகளுக்கு இடையில் செவ்வக வடிவ பழுப்பு-சாம்பல் புள்ளிகள் உள்ளதா? | 2. புள்ளிகள் தீக்குச்சி போன்ற நேரான வடிவில் உள்ளதா? | 3. ஒரே நிலத்தில் தொடர்ந்து மக்காச்சோளம் பயிரிடப்பட்டதா?",
                "1. पत्ती की नसों के बीच आयताकार स्लेटी-भूरे धब्बे हैं? | 2. धब्बे माचिस की तीली जैसे सीधे किनारों वाले दिखते हैं? | 3. एक ही खेत में लगातार मक्का उगाया गया?"
            ),
            (
                "Corn", "healthy", "No Pathogen Detected", "None",
                "Maize foliage shows vigorous vegetative health with zero pathogen lesions. Continue uniform irrigation.",
                "Foliar spray of Panchagavya 3% at tasseling stage to boost cob filling.",
                "None", "None",
                "மக்காச்சோளப் பயிர் மிகவும் பசுமையாகவும் ஆரோக்கியமாகவும் உள்ளது. சீரான நீர்ப்பாசனத்தைத் தொடரவும்.",
                "கதிர் உருவாவதை ஊக்குவிக்க மூன்று சதவீத பஞ்சகவ்யா கரைசலை தெளிக்கலாம்.",
                "இல்லை", "இல்லை",
                "मक्के की फसल पूरी तरह हरी-भरी और स्वस्थ है। समय पर सिंचाई जारी रखें।",
                "भुट्टे के अच्छे विकास के लिए तीन प्रतिशत पंचगव्य का छिड़काव करें।",
                "कोई नहीं", "कोई नहीं",
                0,
                "ICAR-IIMR / TNAU Agronomy",
                "National (ICAR Baseline), Tamil Nadu, Karnataka, Bihar, Maharashtra",
                "Organic foliar boosters are safe during vegetative and tasseling stages.",
                "1. Deep green leaves without necrotic streaks or rust pustules? | 2. Uniform plant stand? | 3. No pest chewing damage?",
                "1. இலைகள் காய்ந்த கோடுகள் அல்லது துரு கொப்புளங்கள் இன்றி பசுமையாக உள்ளதா? | 2. பயிர் வளர்ச்சி சீராக உள்ளதா? | 3. பூச்சி சேதம் இல்லையா?",
                "1. पत्तियां बिना किसी धब्बे या रतुआ के गहरी हरी हैं? | 2. पौधों की बढ़वार एकसमान है? | 3. कीट कटाव के लक्षण नहीं हैं?"
            ),

            # =====================================================================
            # TOMATO (10)
            # =====================================================================
            (
                "Tomato", "early_blight", "Alternaria solani", "Moderate",
                "Stake indeterminate tomato vines upright to eliminate ground contact. Prune defoliated lower branches.",
                "Apply 5% Neem oil emulsion thoroughly covering the abaxial leaf surfaces.",
                "Chlorothalonil 75% WP (or Mancozeb 75% WP)", "2.0 g/L water",
                "தக்காளி செடிகளுக்கு முட்டுக் கொடுத்து நேராக நிறுத்தவும். தரைமட்டத்திற்கு அருகில் உள்ள பாதிக்கப்பட்ட கீழ் இலைகளை வெட்டி அகற்றவும்.",
                "ஐந்து சதவீத வேப்பெண்ணெய் கரைசலை இலைகளின் அடிப்பகுதியில் படும்படி நன்கு தெளிக்கவும்.",
                "குளோரோதலோனில் 75% WP (அல்லது மேன்கோசெப் 75% WP)",
                "ஒரு லிட்டர் தண்ணீருக்கு 2.0 கிராம்",
                "टमाटर के पौधों को डंडे से सहारा देकर सीधा बांधें। जमीन को छूने वाले निचले रोगी पत्तों को हटा दें।",
                "पांच प्रतिशत नीम के तेल का घोल पत्तियों के निचले हिस्से पर अच्छी तरह छिड़कें।",
                "क्लोरोथैलोनिल 75% WP (या मैंकोजेब 75% WP)",
                "2.0 ग्राम प्रति लीटर पानी",
                5,
                "TNAU Horticulture / ICAR-IIHR / CIBRC",
                "National (ICAR Baseline), Tamil Nadu, Karnataka, Maharashtra, Uttar Pradesh",
                "Maintain label interval before spraying foliar bio-pesticides.",
                "1. Dark brown spots with concentric rings on older lower leaves? | 2. Yellowing around lesions leading to leaf drop? | 3. Sunken dark spots near fruit stem end?",
                "1. கீழ் இலைகளில் வட்ட வளையங்களுடன் கூடிய கரும்பழுப்புப் புள்ளிகள் உள்ளதா? | 2. புள்ளிகளைச் சுற்றி மஞ்சளாகி இலை உதிர்கிறதா? | 3. காய் காம்புப் பகுதியில் கருப்புத் திட்டு உள்ளதா?",
                "1. निचली पुरानी पत्तियों पर गोल छल्लेदार गहरे भूरे धब्बे हैं? | 2. धब्बों के चारों ओर पीलापन व पत्ती झड़ना दिखता है? | 3. फल के डंठल के पास धंसे काले धब्बे हैं?"
            ),
            (
                "Tomato", "late_blight", "Phytophthora infestans", "Severe",
                "Avoid overhead irrigation in cloudy or foggy weather. Promptly destroy infected fruit and vine tissue.",
                "Spray 5% garlic-chili extract or foliar Trichoderma harzianum @ 5 g/L.",
                "Metalaxyl 8% + Mancozeb 64% WP", "2.0 g/L water",
                "மேலிருந்து தெளிக்கும் தெளிப்பு நீர்ப்பாசனத்தை தவிர்க்கவும். பாதிக்கப்பட்ட பழங்கள் மற்றும் இலைகளை உடனடியாக அகற்றி எரிக்கவும்.",
                "பூண்டு மற்றும் மிளகாய் சாறு கரைசல் அல்லது ஐந்து சதவீத வேப்பங்கொட்டை சாறு தெளிக்கவும்.",
                "மெட்டலாக்ஸில் 8% + மேன்கோசெப் 64% தூள் மருந்து",
                "ஒரு லிட்டர் தண்ணீருக்கு 2.0 கிராம்",
                "फव्वारा सिंचाई बंद करें। रोगग्रस्त फल और पौधों के अवशेषों को एकत्र करके तुरंत जला दें।",
                "लहसुन-मिर्च का अर्क अथवा पांच प्रतिशत नीम के बीज का काढ़ा छिड़कें।",
                "मेटालेक्सिल 8% + मैंकोजेब 64% घुलनशील चूर्ण",
                "2.0 ग्राम प्रति लीटर पानी",
                7,
                "ICAR-IIHR / TNAU / CIBRC",
                "National (ICAR Baseline), Tamil Nadu, Karnataka, Maharashtra, Punjab",
                "Do not mix systemic metalaxyl formulations directly with live Trichoderma cultures.",
                "1. Irregular water-soaked dark blotches on leaves and stems? | 2. White mold ring on underside of leaf in humid weather? | 3. Firm brown greasy rot on green fruits?",
                "1. இலை மற்றும் தண்டுகளில் ஒழுங்கற்ற நீர் கோர்த்த கருப்புத் திட்டுகள் உள்ளதா? | 2. ஈரப்பதத்தில் இலை அடியில் வெள்ளை பூஞ்சாணம் தெரிகிறதா? | 3. பச்சைக் காய்களில் பழுப்பு அழுகல் உள்ளதா?",
                "1. पत्तियों व तनों पर पानी से भीगे अनियमित काले धब्बे हैं? | 2. नमी में पत्ती के नीचे सफेद फफूंद दिखती है? | 3. हरे फलों पर भूरा तैलीय सड़न है?"
            ),
            (
                "Tomato", "bacterial_spot", "Xanthomonas campestris", "Moderate",
                "Disinfect pruning shears before moving between rows. Avoid handling wet tomato foliage.",
                "Foliar spray of Pseudomonas fluorescens @ 10 g/L water.",
                "Copper Oxychloride 50% WP + Streptocycline", "1.5 g/L + 0.1 g/L water",
                "செடிகளை நறுக்கும் கத்தரிகளை கிருமிநாசினி கொண்டு சுத்தம் செய்யவும். ஈரமாக இருக்கும்போது செடிகளைத் தொடுவதைத் தவிர்க்கவும்.",
                "சூடோமோனாஸ் புளோரசன்ஸ் உயிரியல் காரணியை ஒரு லிட்டர் தண்ணீருக்கு 10 கிராம் கலந்து தெளிக்கவும்.",
                "காப்பர் ஆக்ஸிகுளோரைடு 50% WP + ஸ்ட்ரெப்டோசைக்ளின்",
                "ஒரு லிட்டர் தண்ணீருக்கு 1.5 கிராம் காப்பர் + 0.1 கிராம் ஸ்ட்ரெப்டோசைக்ளின்",
                "कटाई-छंटाई के औजारों को साफ रखें। गीली पत्तियों को हाथ लगाने से बचें।",
                "स्यूडोमोनास फ्लोरोसेंस 10 ग्राम प्रति लीटर पानी में मिलाकर छिड़कें।",
                "कॉपर ऑक्सीक्लोराइड 50% WP + स्ट्रेप्टोसाइक्लिन",
                "1.5 ग्राम कॉपर + 0.1 ग्राम स्ट्रेप्टोसाइक्लिन प्रति लीटर पानी",
                7,
                "TNAU / ICAR-IIHR / CIBRC",
                "National (ICAR Baseline), Tamil Nadu, Karnataka, Maharashtra",
                "Copper + antibiotic sprays are incompatible for tank mixing with live Pseudomonas.",
                "1. Small water-soaked circular spots (<3 mm) turning dark brown/black? | 2. Shot-hole tearing or greasy appearance on leaves? | 3. Raised scab-like spots on fruits?",
                "1. 3 மி.மீ-க்கும் சிறிய நீர் கோர்த்த கரும்பழுப்புப் புள்ளிகள் உள்ளதா? | 2. இலைகளில் துளை விழுந்த தோற்றம் உள்ளதா? | 3. காய்களில் சொறி போன்ற புடைப்புகள் உள்ளதா?",
                "1. 3 मिमी से छोटे पानी से भीगे गहरे भूरे-काले धब्बे हैं? | 2. पत्तियों में छोटे छेद या चिकना दाग दिखता है? | 3. फलों पर उभरे खुरदरे धब्बे हैं?"
            ),
            (
                "Tomato", "leaf_mold", "Passalora fulva", "Moderate",
                "Increase greenhouse and row ventilation to lower relative humidity below 80%.",
                "Foliar spray of baking soda (sodium bicarbonate) solution @ 5 g/L water.",
                "Chlorothalonil 75% WP", "2.0 g/L water",
                "வயலில் அல்லது பாலிஹவுஸில் நல்ல காற்றோட்டம் ஏற்படுத்தவும். இலைகள் ஈரமாக இருக்கும் நேரத்தைக் குறைக்கவும்.",
                "ஐந்து கிராம் சமையல் சோடா கலந்த தண்ணீரை அல்லது வேப்பெண்ணெய் கரைசலை தெளிக்கவும்.",
                "குளோரோதலோனில் 75% தூள் மருந்து",
                "ஒரு லிட்டர் தண்ணீருக்கு 2.0 கிராம்",
                "हवा का संचार बढ़ाएं ताकि नमी 80% से कम रहे।",
                "पांच ग्राम बेकिंग सोडा प्रति लीटर पानी में घोलकर छिड़कें।",
                "क्लोरोथैलोनिल 75% घुलनशील चूर्ण",
                "2.0 ग्राम प्रति लीटर पानी",
                7,
                "ICAR-IIHR Protected Cultivation / CIBRC",
                "National (ICAR Baseline), Tamil Nadu, Karnataka, Maharashtra",
                "Ensure good coverage on lower leaf surfaces; follow PHI on protected/open crops.",
                "1. Pale green-yellow patches on upper leaf surface? | 2. Olive-green to purplish velvety mold on leaf underside? | 3. High humidity (>85%) or polyhouse growing conditions?",
                "1. இலையின் மேல் பக்கத்தில் வெளிர் மஞ்சள் திட்டுகள் உள்ளதா? | 2. இலை அடிப்பகுதியில் ஆலிவ்-பச்சை வெல்வெட் போன்ற பூஞ்சாணம் உள்ளதா? | 3. அதிக ஈரப்பதம் அல்லது பாலிஹவுஸ் சாகுபடியா?",
                "1. पत्ती की ऊपरी सतह पर हल्के पीले धब्बे हैं? | 2. निचली सतह पर मखमली जैतूनी-हरा फफूंद दिखता है? | 3. खेत/पॉलीहाउस में अत्यधिक नमी है?"
            ),
            (
                "Tomato", "septoria_leaf_spot", "Septoria lycopersici", "Moderate",
                "Mulch beneath plants with clean straw to prevent rain-splash transmission. Prune lower canopy leaves.",
                "Foliar spray of bio-fungicide Trichoderma @ 5 g/L water.",
                "Copper Oxychloride 50% WP", "2.5 g/L water",
                "மழைத்துளிகளால் மண் இலைகளில் தெறிக்காமல் இருக்க செடிகளைச் சுற்றி வைக்கோல் மூடாக்கு போடவும். பாதிக்கப்பட்ட கீழ் இலைகளை வெட்டவும்.",
                "டிரைக்கோடெர்மா விரிடி 5 கிராம் ஒரு லிட்டர் தண்ணீரில் கலந்து தெளிக்கவும்.",
                "காப்பர் ஆக்ஸிகுளோரைடு 50% தூள் மருந்து",
                "ஒரு லிட்டர் தண்ணீருக்கு 2.5 கிராம்",
                "मिट्टी की छींटों से बचाव के लिए पौधों के नीचे पुआल बिछाएं। निचली रोगी पत्तियों को छांट दें।",
                "ट्राइकोडर्मा 5 ग्राम प्रति लीटर पानी में मिलाकर छिड़कें।",
                "कॉपर ऑक्सीक्लोराइड 50% चूर्ण",
                "2.5 ग्राम प्रति लीटर पानी",
                7,
                "TNAU / ICAR-IIHR / CIBRC",
                "National (ICAR Baseline), Tamil Nadu, Karnataka, Uttar Pradesh",
                "Do not tank-mix copper sprays with live Trichoderma bio-fungicides.",
                "1. Numerous small circular spots (2-3 mm) with tan/gray centers and dark margins? | 2. Tiny black dots (pycnidia) visible in spot centers? | 3. Rarely affects fruit directly?",
                "1. சாம்பல் நடுப்பகுதியும் கருப்பு ஓரமும் கொண்ட சிறிய வட்டப் புள்ளிகள் உள்ளதா? | 2. புள்ளி மையத்தில் மிகச் சிறிய கருப்புப் புள்ளிகள் தெரிகிறதா? | 3. காய்களில் பாதிப்பு இல்லையா?",
                "1. छोटे गोल धब्बे जिनके केंद्र भूरे/स्लेटी व किनारे गहरे हों? | 2. धब्बे के बीच में बहुत छोटे काले बिंदु दिखते हैं? | 3. फलों पर आमतौर पर असर नहीं दिखता?"
            ),
            (
                "Tomato", "spider_mites", "Tetranychus urticae", "Moderate",
                "Eradicate broadleaf weeds like Parthenium along borders. Wash foliage with pressurized water spray to dislodge webs.",
                "Spray 3% Neem oil emulsion or horticultural mineral oil @ 2%.",
                "Spiromesifen 22.9% SC", "1.0 ml/L water",
                "வயல் வரப்புகளில் உள்ள பார்த்தீனியம் போன்ற களைகளை முற்றிலும் அழிக்கவும். நீர் தெளித்து சிலந்திக் கூடுகளை அழிக்கவும்.",
                "மூன்று சதவீத வேப்பெண்ணெய் கரைசல் அல்லது ஐந்து சதவீத வேப்பங்கொட்டை சாறு தெளிக்கவும்.",
                "ஸ்பைரோமெசிஃபென் 22.9% திரவ மருந்து",
                "ஒரு லிட்டர் தண்ணீருக்கு 1.0 மில்லிலிட்டர்",
                "मेड़ों से खरपतवार हटाएं। पत्तियों पर पानी की धार मारकर जाले नष्ट करें।",
                "तीन प्रतिशत नीम के तेल का घोल छिड़कें।",
                "स्पिरोमेसिफेन 22.9% तरल",
                "1.0 मिलीलीटर प्रति लीटर पानी",
                5,
                "TNAU / ICAR-IIHR / CIBRC",
                "National (ICAR Baseline), Tamil Nadu, Karnataka, Maharashtra",
                "Acaricide applications should target the underside of leaves; avoid spraying during peak midday heat.",
                "1. Fine yellow stippling/bronzing on upper leaf surface? | 2. Delicate silk webbing under leaves or on shoot tips? | 3. Tiny moving mites visible under hand lens in hot dry weather?",
                "1. இலை மேல் பரப்பில் மஞ்சள்/வெண்கல நிறப் புள்ளிகள் உள்ளதா? | 2. இலை அடியில் மெல்லிய சிலந்தி வலை பின்னல் உள்ளதா? | 3. வறண்ட வெப்ப காலநிலையில் நுண்ணிய பேன்கள் நகர்வது தெரிகிறதா?",
                "1. पत्ती की ऊपरी सतह पर बारीक पीले-तांबे जैसे धब्बे हैं? | 2. पत्तियों के नीचे बारीक मकड़ी का जाला दिखता है? | 3. गर्म सूखे मौसम में सूक्ष्म कीट चलते दिखते हैं?"
            ),
            (
                "Tomato", "target_spot", "Corynespora cassiicola", "Moderate",
                "Switch to drip irrigation to keep foliage dry. Maintain wide crop row spacing.",
                "Foliar spray of Pseudomonas fluorescens @ 10 g/L.",
                "Azoxystrobin 23% SC", "1.0 ml/L water",
                "இலைகள் நனையாமல் இருக்க சொட்டு நீர்ப்பாசன முறையைக் கையாளவும். செடிகளுக்கு இடையே போதிய இடைவெளி விடவும்.",
                "சூடோமோனாஸ் புளோரசன்ஸ் உயிரியல் காரணியை ஒரு லிட்டர் தண்ணீருக்கு 10 கிராம் கலந்து தெளிக்கவும்.",
                "அசோக்ஸிஸ்ட்ரோபின் 23% திரவ மருந்து",
                "ஒரு லிட்டர் தண்ணீருக்கு 1.0 மில்லிலிட்டர்",
                "टपक (ड्रिप) सिंचाई अपनाएं ताकि पत्तियां सूखी रहें। पौधों के बीच उचित दूरी रखें।",
                "स्यूडोमोनास फ्लोरोसेंस 10 ग्राम प्रति लीटर का छिड़काव करें।",
                "एज़ोक्सीस्ट्रोबिन 23% तरल",
                "1.0 मिलीलीटर प्रति लीटर पानी",
                5,
                "ICAR-IIHR / CIBRC Label",
                "National (ICAR Baseline), Tamil Nadu, Karnataka, Maharashtra",
                "Rotate strobilurin fungicides to prevent pathogen resistance per CIBRC label.",
                "1. Necrotic spots with light brown centers and faint concentric rings? | 2. Spots turning papery and cracking at center? | 3. Pitted lesions on ripe/green fruit?",
                "1. வெளிர் பழுப்பு மையத்துடன் கூடிய வட்டப் புள்ளிகள் உள்ளதா? | 2. புள்ளி மையம் காகிதம் போல் காய்ந்து விரிசல் விடுகிறதா? | 3. காய்களில் பள்ளமான புள்ளிகள் உள்ளதா?",
                "1. हल्के भूरे केंद्र व हल्के छल्लों वाले धब्बे हैं? | 2. धब्बों का बीच का भाग कागज जैसा सूखकर फट रहा है? | 3. फलों पर धंसे हुए धब्बे दिखते हैं?"
            ),
            (
                "Tomato", "tomato_yellow_leaf_curl_virus", "Begomovirus (TYLCV)", "Severe",
                "Install yellow sticky traps @ 12 traps/acre to trap vector whiteflies. Rogue and bury infected plants immediately.",
                "Foliar spray of 5% Neem Seed Kernel Extract (NSKE) to repel whiteflies.",
                "Thiamethoxam 25% WG", "0.5 g/L water",
                "வெள்ளை ஈக்களைக் கட்டுப்படுத்த ஏக்கருக்கு 12 மஞ்சள் நிற ஒட்டும் பொறிகளை வைக்கவும். பாதிக்கப்பட்ட செடிகளை உடனே பிடுங்கி அழிக்கவும்.",
                "வெள்ளை ஈக்களை விரட்ட ஐந்து சதவீத வேப்பங்கொட்டை சாறு அல்லது வேப்பெண்ணெய் தெளிக்கவும்.",
                "தயாமீதாக்ஸம் 25% தூள் மருந்து",
                "ஒரு லிட்டர் தண்ணீருக்கு 0.5 கிராம்",
                "सफेद मक्खी को फंसाने के लिए प्रति एकड़ 12 पीले चिपचिपे ट्रैप लगाएं। संक्रमित पौधों को तुरंत उखाड़कर नष्ट करें।",
                "पांच प्रतिशत नीम के बीज के काढ़े का छिड़काव करें।",
                "थियामेथोक्सम 25% घुलनशील चूर्ण",
                "0.5 ग्राम प्रति लीटर पानी",
                7,
                "TNAU / ICAR-IIHR / CIBRC",
                "National (ICAR Baseline), Tamil Nadu, Karnataka, Maharashtra, Uttar Pradesh",
                "Neonicotinoid vector control; avoid spraying during active honeybee foraging hours.",
                "1. Upward curling/cupping of young terminal leaves? | 2. Yellowing along leaf margins and severe plant stunting? | 3. Presence of tiny whiteflies when shaking plant?",
                "1. மேல் இளம் இலைகள் மேல்நோக்கி கிண்ணம் போல் சுருண்டு உள்ளதா? | 2. இலை ஓரங்கள் மஞ்சளாகி செடி வளர்ச்சி குன்றியுள்ளதா? | 3. செடியை அசைத்தால் வெள்ளை ஈக்கள் பறக்கிறதா?",
                "1. ऊपरी नई पत्तियां ऊपर की ओर कप जैसी मुड़ रही हैं? | 2. पत्तियों के किनारे पीले व पौधा बौना हो गया है? | 3. पौधा हिलाने पर छोटी सफेद मक्खियां उड़ती हैं?"
            ),
            (
                "Tomato", "tomato_mosaic_virus", "Tobamovirus (ToMV)", "Severe",
                "Rogue out and destroy infected viral plants. Disinfect hands and tools with 10% trisodium phosphate before handling.",
                "Spray 10% cow milk solution (100 ml milk per litre water) to inhibit viral coat protein transmission.",
                "None (Fungicides ineffective against viral genome; vector & hygiene control only)", "None",
                "பாதிக்கப்பட்ட செடிகளை உடனே வேருடன் பிடுங்கி அழிக்கவும். செடிகளைக் கையாளுவதற்கு முன் கைகளை சோப்பினால் கழுவவும்.",
                "பத்து சதவீத பசும்பால் கரைசல் (ஒரு லிட்டர் தண்ணீரில் 100 மில்லி பால்) தெளித்து வைரஸ் பரவலைத் தடுக்கவும்.",
                "இல்லை (வைரஸ் நோய்க்கு பூஞ்சாணக் கொல்லிகள் பயன் தராது; சுகாதாரம் மற்றும் வெக்டார் கட்டுப்பாடு மட்டும்)", "தேவை இல்லை",
                "संक्रमित पौधों को उखाड़कर नष्ट करें। काम करने से पहले हाथों और औजारों को साबुन से अच्छी तरह धोएं।",
                "दस प्रतिशत गाय के दूध का घोल (100 मिली दूध प्रति लीटर पानी) छिड़कें।",
                "कोई नहीं (विषाणु जनित रोग पर कवकनाशी काम नहीं करते)", "कोई नहीं",
                0,
                "ICAR-IIHR / TNAU Virology",
                "National (ICAR Baseline), Tamil Nadu, Karnataka, Maharashtra",
                "No chemical spray is advised for viral infection; focus strictly on sanitation and roguing.",
                "1. Light and dark green mottled/mosaic pattern on leaves? | 2. Narrow/fern-like leaf distortion? | 3. Frequent manual pruning or transplanting contact?",
                "1. இலைகளில் அடர் மற்றும் வெளிர் பச்சை திட்டுகள் (மொசைக்) உள்ளதா? | 2. இலைகள் குறுகி வடிவம் மாறியுள்ளதா? | 3. கைகளால் கவாத்து செய்த பின் நோய் பரவியதா?",
                "1. पत्तियों पर हल्के व गहरे हरे रंग का चित्तीदार (मोज़ेक) पैटर्न है? | 2. पत्तियां संकरी और विकृत हो गई हैं? | 3. छंटाई या छूने के बाद रोग तेजी से फैला?"
            ),
            (
                "Tomato", "healthy", "No Pathogen Detected", "None",
                "Foliage demonstrates prime physiological vitality with no pathogenic spotting. Maintain balanced fertigation.",
                "Spray Panchagavya 3% or Seaweed extract @ 2 ml/L as an organic flowering and fruit set booster.",
                "None", "None",
                "தக்காளிப் பயிர் மிகவும் பசுமையாகவும் ஆரோக்கியமாகவும் உள்ளது. சீரான நீர்ப்பாசனம் மற்றும் சமச்சீர் உர மேலாண்மையைத் தொடரவும்.",
                "பூ மற்றும் காய் பிடிப்பை அதிகரிக்க மூன்று சதவீத பஞ்சகவ்யா கரைசலை இலைகளில் தெளிக்கலாம்.",
                "இல்லை", "இல்லை",
                "टमाटर की फसल पूरी तरह हरी-भरी और स्वस्थ है। संतुलित सिंचाई जारी रखें।",
                "फूल और फल की अच्छी बढ़वार के लिए तीन प्रतिशत पंचगव्य का छिड़काव करें।",
                "कोई नहीं", "कोई नहीं",
                0,
                "TNAU / ICAR-IIHR Agronomy",
                "National (ICAR Baseline), Tamil Nadu, Karnataka, Maharashtra, Uttar Pradesh",
                "Organic foliar boosters are compatible with standard fertigation schedules.",
                "1. Uniform green leaves with no mosaic, curling, or spots? | 2. Healthy flower cluster formation? | 3. No pest webbing or mites?",
                "1. இலைகள் மொசைக், சுருள் அல்லது புள்ளிகள் இன்றி சீரான பச்சையில் உள்ளதா? | 2. பூக்கள் ஆரோக்கியமாக உள்ளதா? | 3. சிலந்தி வலை அல்லது பூச்சி இல்லையா?",
                "1. पत्तियां बिना किसी धब्बे, मुड़ाव या मोज़ेक के हरी हैं? | 2. फूलों का गुच्छा स्वस्थ है? | 3. कोई कीट या जाला नहीं है?"
            ),

            # =====================================================================
            # MODE 3: AGRICULTURAL INSECT PESTS (IP102 Verified Classes)
            # =====================================================================
            (
                "Pest", "whitefly", "Bemisia tabaci / Trialeurodes vaporariorum", "Moderate",
                "Install 12 yellow sticky traps per acre at crop canopy height. Remove alternate weed hosts like Abutilon and Parthenium.",
                "Spray 5% Neem Seed Kernel Extract or Neem oil 3% targeting leaf undersides.",
                "Thiamethoxam 25% WG (or Spiromesifen 22.9% SC)", "0.5 g/L (or 1.0 ml/L) water",
                "ஏக்கருக்கு 12 மஞ்சள் நிற ஒட்டும் பொறிகளைப் பயிர் உயரத்தில் வைக்கவும். வயல் வரப்பு களைகளை அகற்றவும்.",
                "ஐந்து சதவீத வேப்பங்கொட்டை சாறு அல்லது மூன்று சதவீத வேப்பெண்ணெய் கரைசலை இலைகளின் அடிப்பகுதியில் தெளிக்கவும்.",
                "தயாமீதாக்ஸம் 25% குருணை மருந்து",
                "ஒரு லிட்டர் தண்ணீருக்கு 0.5 கிராம்",
                "प्रति एकड़ 12 पीले चिपचिपे ट्रैप फसल की ऊंचाई पर लगाएं। मेड़ों से खरपतवार हटाएं।",
                "पांच प्रतिशत नीम के बीज का काढ़ा अथवा तीन प्रतिशत नीम का तेल पत्तियों की निचली सतह पर छिड़कें।",
                "थियामेथोक्सम 25% WG",
                "0.5 ग्राम प्रति लीटर पानी",
                7,
                "TNAU Crop Protection / ICAR-NBAIR / CIBRC",
                "National (ICAR Baseline), Tamil Nadu, Karnataka, Maharashtra, Uttar Pradesh, Punjab",
                "Avoid spraying neonicotinoids during active honeybee foraging hours.",
                "1. Tiny white moth-like insects flying up when plant is shaken? | 2. Sticky honeydew or black sooty mold on lower leaves? | 3. Tiny pale scale-like nymphs on leaf underside?",
                "1. செடியை அசைத்தால் சிறிய வெள்ளை ஈக்கள் பறக்கிறதா? | 2. கீழ் இலைகளில் தேன் போன்ற ஒட்டும் திரவம் அல்லது கருப்பு பூஞ்சாணம் உள்ளதா? | 3. இலை அடியில் சிறிய வெள்ளை குஞ்சுகள் உள்ளதா?",
                "1. पौधा हिलाने पर छोटी सफेद मक्खियां उड़ती हैं? | 2. निचली पत्तियों पर चिपचिपा पदार्थ या काला फफूंद दिखता है? | 3. पत्ती की निचली सतह पर छोटे शल्क जैसे शिशु हैं?"
            ),
            (
                "Pest", "aphid", "Aphis gossypii / Myzus persicae", "Moderate",
                "Conserve natural predators like ladybird beetles and lacewings. Install yellow sticky traps and remove heavily infested shoots.",
                "Spray 5% Neem Seed Kernel Extract or Verticillium lecanii bio-insecticide @ 5 g/L.",
                "Imidacloprid 17.8% SL", "0.5 ml/L water",
                "பொறிவண்டு போன்ற நன்மை செய்யும் பூச்சிகளைப் பாதுகாக்கவும். தீவிரமாக தாக்கப்பட்ட நுனிக் கிளைகளை அகற்றவும்.",
                "ஐந்து சதவீத வேப்பங்கொட்டை சாறு அல்லது வெர்டிசிலியம் லெக்கானி 5 கிராம் ஒரு லிட்டர் தண்ணீரில் கலந்து தெளிக்கவும்.",
                "இமிடாகுளோபிரிட் 17.8% திரவ மருந்து",
                "ஒரு லிட்டர் தண்ணீருக்கு 0.5 மில்லிலிட்டர்",
                "लेडीबर्ड बीटल जैसे मित्र कीटों को बचाएं। अधिक संक्रमित कोमल टहनियों को हटा दें।",
                "पांच प्रतिशत नीम के बीज का काढ़ा अथवा वर्टिसिलियम लेकानी 5 ग्राम प्रति लीटर पानी में छिड़कें।",
                "इमिडाक्लोप्रिड 17.8% SL",
                "0.5 मिलीलीटर प्रति लीटर पानी",
                7,
                "ICAR-NBAIR / TNAU / CIBRC",
                "National (ICAR Baseline), Tamil Nadu, Punjab, Uttar Pradesh, Bihar, Karnataka",
                "Do not mix entomopathogenic fungi (Verticillium) directly with chemical insecticides.",
                "1. Dense colonies of soft-bodied green/black insects on tender shoots? | 2. Curled or puckered young leaves with sticky honeydew? | 3. Ants moving up and down infested stems?",
                "1. இளம் தளிர் மற்றும் இலை அடியில் மென்மையான பச்சை/கருப்பு அசுவினி கூட்டங்கள் உள்ளதா? | 2. இளம் இலைகள் சுருண்டு ஒட்டும் தன்மையுடன் உள்ளதா? | 3. செடியில் எறும்பு நடமாட்டம் அதிகம் உள்ளதா?",
                "1. कोमल टहनियों व पत्तियों के नीचे मुलायम हरे/काले माहू के झुंड हैं? | 2. नई पत्तियां मुड़ी हुई और चिपचिपी हैं? | 3. तने पर चींटियों की आवाजाही दिखती है?"
            ),
            (
                "Pest", "leafminer", "Liriomyza trifolii / Leafminer", "Moderate",
                "Clip and destroy heavily mined cotyledons and lower leaves. Use yellow sticky cards to trap adult flies.",
                "Spray 5% Neem Seed Kernel Extract or Azadirachtin 0.03% @ 3 ml/L.",
                "Spinosad 45% SC (or Abamectin 1.9% EC)", "0.3 ml/L (or 0.5 ml/L) water",
                "சுரங்கம் போன்ற கோடுகள் உள்ள கீழ் இலைகளைக் கிள்ளி அழிக்கவும். தாய் ஈக்களைப் பிடிக்க மஞ்சள் ஒட்டும் பொறிகளை வைக்கவும்.",
                "ஐந்து சதவீத வேப்பங்கொட்டை சாறு அல்லது அசாடிராக்டின் 3 மி.லி ஒரு லிட்டர் தண்ணீரில் கலந்து தெளிக்கவும்.",
                "ஸ்பைனோசாட் 45% திரவ மருந்து",
                "ஒரு லிட்டர் தண்ணீருக்கு 0.3 மில்லிலிட்டர்",
                "सुरंग जैसी धारियों वाली निचली पत्तियों को तोड़कर नष्ट करें। वयस्क मक्खी पकड़ने के लिए पीले स्टिकी कार्ड लगाएं।",
                "पांच प्रतिशत नीम का काढ़ा अथवा अजाडिरेक्टिन 3 मिली प्रति लीटर पानी में छिड़कें।",
                "स्पिनोसैड 45% SC",
                "0.3 मिलीलीटर प्रति लीटर पानी",
                5,
                "TNAU / ICAR-IIHR / CIBRC",
                "National (ICAR Baseline), Tamil Nadu, Karnataka, Maharashtra",
                "Target early larval mining stages; observe 5-day PHI before tomato/vegetable harvest.",
                "1. Winding white serpentine tunnels etched inside leaf blade? | 2. Tiny yellow maggot visible at end of tunnel? | 3. Pinprick feeding punctures on upper leaf surface?",
                "1. இலையில் பாம்பு போன்ற வெள்ளை சுரங்கக் கோடுகள் உள்ளதா? | 2. கோட்டின் முடிவில் சிறிய மஞ்சள் புழு தெரிகிறதா? | 3. இலை மேல் பரப்பில் ஊசி குத்திய போன்ற புள்ளிகள் உள்ளதா?",
                "1. पत्ती के भीतर सांप जैसी सफेद टेढ़ी-मेढ़ी सुरंगें बनी हैं? | 2. सुरंग के सिरे पर छोटा पीला इल्ली जैसा लार्वा दिखता है? | 3. ऊपरी सतह पर सूक्ष्म छेद दिखते हैं?"
            ),
            (
                "Pest", "corn_borer", "Chilo partellus / Maize Stem Borer", "Severe",
                "Remove and destroy deadhearts and infested stalks after harvest. Intercrop maize with cowpea to boost natural parasitoids.",
                "Release Trichogramma chilonis egg cards @ 50,000 eggs/acre or spray Bacillus thuringiensis @ 2 g/L.",
                "Chlorantraniliprole 18.5% SC", "0.4 ml/L water (whorl application)",
                "காய்ந்த குருத்து செடிகளைப் பிடுங்கி அழிக்கவும். தட்டைப்பயறு ஊடுபயிர் சாகுபடி செய்து நன்மை செய்யும் ஒட்டுண்ணிகளை அதிகரிக்கவும்.",
                "டிரைக்கோகிராம்மா முட்டை அட்டைகளை ஏக்கருக்கு 50,000 வீதம் கட்டவும் அல்லது பேசில்லஸ் துரிஞ்சியென்சிஸ் 2 கிராம்/லிட்டர் தெளிக்கவும்.",
                "குளோரான்ட்ரானிலிப்ரோல் 18.5% திரவ மருந்து",
                "ஒரு லிட்டர் தண்ணீருக்கு 0.4 மில்லிலிட்டர்",
                "सूखे गोभ (डेडहार्ट) वाले पौधों को उखाड़कर नष्ट करें। मक्का के साथ लोबिया की अंतरफसल उगाएं।",
                "ट्राइकोग्रामा अंड कार्ड 50,000 प्रति एकड़ लगाएं अथवा बैसिलस थुरिंजिएंसिस 2 ग्राम/लीटर छिड़कें।",
                "क्लोरेंट्रानिलिप्रोल 18.5% SC",
                "0.4 मिलीलीटर प्रति लीटर पानी",
                14,
                "ICAR-IIMR / TNAU Maize Guide / CIBRC",
                "National (ICAR Baseline), Tamil Nadu, Karnataka, Bihar, Maharashtra",
                "Apply whorl treatments before larvae bore deep into the stalk; avoid mixing Bt with broad-spectrum chemicals.",
                "1. Pinholes in parallel rows across newly unfurled whorl leaves? | 2. Sawdust-like frass at whorl or stem entry holes? | 3. Drying of central shoot (deadheart)?",
                "1. விரியும் குருத்து இலைகளில் வரிசையாக சிறிய துளைகள் உள்ளதா? | 2. குருத்து அல்லது தண்டு துளையில் மரத்தூள் போன்ற கழிவு உள்ளதா? | 3. நடுக்குருத்து காய்ந்துள்ளதா?",
                "1. खुलती हुई गोभ की पत्तियों पर कतार में छोटे छेद हैं? | 2. गोभ या तने के छेद पर बुरादे जैसा मल दिखता है? | 3. पौधे का मध्य भाग सूख (डेडहार्ट) रहा है?"
            ),
            (
                "Pest", "rice_leaf_roller", "Cnaphalocrocis medinalis", "Moderate",
                "Keep bunds weed-free and avoid excessive nitrogen top-dressing. Drag a rope gently across flooded crop to dislodge larvae.",
                "Release Trichogramma japonicum @ 50,000 eggs/acre or spray 5% Neem Seed Kernel Extract.",
                "Cartap Hydrochloride 50% SP (or Chlorantraniliprole 18.5% SC)", "2.0 g/L (or 0.3 ml/L) water",
                "வரப்பு களைகளை அகற்றி அதிக தழைச்சத்து உரம் இடுவதைத் தவிர்க்கவும். வயலில் கயிறு இழுத்து புழுக்களைக் கீழே விழச் செய்யவும்.",
                "டிரைக்கோகிராம்மா ஜப்பானிக்கம் ஒட்டுண்ணி அட்டை கட்டவும் அல்லது 5% வேப்பங்கொட்டை சாறு தெளிக்கவும்.",
                "கார்டாப் ஹைட்ரோகுளோரைடு 50% தூள் மருந்து",
                "ஒரு லிட்டர் தண்ணீருக்கு 2.0 கிராம்",
                "मेड़ों को खरपतवार मुक्त रखें और अतिरिक्त नाइट्रोजन खाद न डालें। खेत में रस्सी चलाकर इल्लियों को पानी में गिराएं।",
                "ट्राइकोग्रामा जैपोनिकम 50,000 प्रति एकड़ छोड़ें अथवा पांच प्रतिशत नीम का काढ़ा छिड़कें।",
                "कार्टाप हाइड्रोक्लोराइड 50% SP",
                "2.0 ग्राम प्रति लीटर पानी",
                14,
                "ICAR-IIRR / TNAU Rice Portal / CIBRC",
                "National (ICAR Baseline), Tamil Nadu, Punjab, Uttar Pradesh, Bihar",
                "Maintain field water depth briefly if using rope-dislodging mechanical control.",
                "1. Rice leaf blade folded longitudinally into a tubular roll? | 2. White papery scraped streaks inside folded leaf? | 3. Small greenish caterpillar inside the leaf fold?",
                "1. நெல் இலைகள் நீளவாக்கில் குழாய் போல் மடிக்கப்பட்டுள்ளதா? | 2. மடித்த இலைக்குள் வெள்ளை நிற சுரண்டிய கோடுகள் உள்ளதா? | 3. மடிப்புக்குள் சிறிய பச்சைப் புழு உள்ளதா?",
                "1. धान की पत्ती लंबाई में नली की तरह मुड़ी हुई है? | 2. मुड़ी पत्ती के अंदर सफेद खुरची हुई धारियां हैं? | 3. पत्ती के अंदर छोटी हरी इल्ली दिखती है?"
            ),
            (
                "Pest", "brown_planthopper", "Nilaparvata lugens", "Severe",
                "Form 30 cm alleyways every 2 m rows for sunlight and airflow. Drain standing water for 3-4 days and avoid synthetic pyrethroids.",
                "Spray 3% Neem oil or Beauveria bassiana @ 5 g/L directed at the basal stem.",
                "Pymetrozine 50% WG (or Dinotefuran 20% SG)", "0.6 g/L (or 0.4 g/L) water",
                "இரண்டு மீட்டருக்கு ஒருமுறை 30 செ.மீ பாதை விட்டு சூரிய ஒளி உள்ளே புக வழி செய்யவும். வயலில் உள்ள தண்ணீரை வடிக்கவும்.",
                "மூன்று சதவீத வேப்பெண்ணெய் அல்லது பியூவேரியா பாசியானா 5 கிராம்/லிட்டர் அளவில் தண்டின் அடிப்பகுதியில் தெளிக்கவும்.",
                "பைமெட்ரோசைன் 50% குருணை மருந்து",
                "ஒரு லிட்டர் தண்ணீருக்கு 0.6 கிராம்",
                "हर दो मीटर पर 30 सेमी की क्यारी रास्ता (एलीवे) बनाएं। खेत से पानी निकाल दें और सिंथेटिक पाइरेथ्रॉइड से बचें।",
                "तीन प्रतिशत नीम का तेल या ब्यूवेरिया बैसियाना 5 ग्राम/लीटर तने के निचले हिस्से पर छिड़कें।",
                "पाइमेट्रोज़िन 50% WG",
                "0.6 ग्राम प्रति लीटर पानी",
                14,
                "ICAR-IIRR / TNAU / CIBRC",
                "National (ICAR Baseline), Tamil Nadu, Punjab, Uttar Pradesh, Bihar, Karnataka",
                "Direct nozzles strictly to plant base near water line; avoid resurgence-inducing pyrethroids.",
                "1. Brown insects clustering at base of rice tillers just above water line? | 2. Circular patches of yellowed/dried plants ('hopperburn')? | 3. Sooty mold near stem base?",
                "1. நெல் தூர்களின் அடிப்பகுதியில் பழுப்பு தத்துப்பூச்சிகள் கூட்டமாக உள்ளதா? | 2. வயலில் வட்டமாக பயிர் கருகிய (ஹாப்பர் பர்ன்) திட்டுகள் உள்ளதா? | 3. தண்டு அடியில் கருப்பு பூஞ்சாணம் உள்ளதா?",
                "1. धान के कल्लों के आधार पर भूरे फुदके झुंड में बैठे हैं? | 2. खेत में गोल चकत्तों में फसल सूख (हॉपर बर्न) रही है? | 3. तने के आधार पर काला फफूंद दिखता है?"
            ),
        ]

        cursor.executemany("""
            INSERT INTO treatment_guidelines
            (crop, diagnosis, pathogen_scientific, stage,
             cultural_en, organic_en, chemical_en, dosage_en,
             cultural_ta, organic_ta, chemical_ta, dosage_ta,
             cultural_hi, organic_hi, chemical_hi, dosage_hi,
             phi_days, source_citation, zone_applicability, bio_compatibility_note,
             checklist_en, checklist_ta, checklist_hi)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, guidelines)
        self.conn.commit()

    def _normalize_name(self, text: str) -> str:
        s = text.lower().replace(" ", "_").replace("-", "_").strip()
        while "__" in s:
            s = s.replace("__", "_")
        return s

    def is_region_verified(self, state: str, zone_applicability: str) -> bool:
        if not state or state == "National (ICAR Baseline)":
            return True
        if "National" in zone_applicability:
            return True
        return state.lower() in zone_applicability.lower()

    def get_treatment(self, crop: str, diagnosis: str, stage: str = "Moderate", lang: str = "en", state: str = "National (ICAR Baseline)"):
        cursor = self.conn.cursor()
        lang = lang.lower()
        if lang not in ["en", "ta", "hi"]:
            lang = "en"

        norm_crop = self._normalize_name(crop)
        norm_diag = self._normalize_name(diagnosis)

        if "corn" in norm_crop or "maize" in norm_crop:
            crop_key = "Corn"
        elif "potato" in norm_crop:
            crop_key = "Potato"
        elif "tomato" in norm_crop:
            crop_key = "Tomato"
        elif "rice" in norm_crop or "paddy" in norm_crop:
            crop_key = "Rice"
        else:
            crop_key = crop.capitalize()

        cursor.execute(
            "SELECT diagnosis FROM treatment_guidelines WHERE LOWER(crop) = LOWER(?)",
            (crop_key,),
        )
        available_diagnoses = [r[0] for r in cursor.fetchall()]

        matched_diag = None
        for cand in available_diagnoses:
            if cand.lower() in norm_diag or norm_diag in cand.lower():
                matched_diag = cand
                break

        if not matched_diag:
            for cand in available_diagnoses:
                parts = [p for p in cand.lower().split("_") if len(p) > 3]
                if any(p in norm_diag for p in parts):
                    matched_diag = cand
                    break

        if not matched_diag:
            matched_diag = available_diagnoses[0] if available_diagnoses else norm_diag

        cursor.execute(
            f"""
            SELECT pathogen_scientific, stage,
                   cultural_{lang}, organic_{lang}, chemical_{lang}, dosage_{lang},
                   phi_days, source_citation, zone_applicability, bio_compatibility_note,
                   checklist_{lang},
                   cultural_en, organic_en, chemical_en, dosage_en
            FROM treatment_guidelines
            WHERE LOWER(crop) = LOWER(?) AND LOWER(diagnosis) = LOWER(?)
            LIMIT 1;
            """,
            (crop_key, matched_diag),
        )

        row = cursor.fetchone()
        if not row:
            return None

        phi = row[6]
        phi_texts = {
            "en": f"{phi} days" if phi > 0 else "0 days",
            "ta": f"{phi} நாட்கள்" if phi > 0 else "தேவை இல்லை",
            "hi": f"{phi} दिन" if phi > 0 else "लागू नहीं",
        }
        zone_str = row[8]
        region_verified = self.is_region_verified(state, zone_str)
        checklist_items = [c.strip() for c in row[10].split("|") if c.strip()]

        return {
            "crop": crop_key,
            "diagnosis": matched_diag,
            "pathogen_scientific": row[0],
            "reference_stage": row[1],
            "cultural_action": row[2],
            "organic_remedy": row[3],
            "chemical_name": row[4],
            "chemical_dosage": row[5],
            "phi_days": phi,
            "phi_display": phi_texts.get(lang, f"{phi} days"),
            "source_citation": row[7],
            "zone_applicability": zone_str,
            "region_verified": region_verified,
            "bio_compatibility_note": row[9],
            "symptom_checklist": checklist_items,
            "raw_en": {
                "cultural": row[11],
                "organic": row[12],
                "chemical": row[13],
                "dosage": row[14],
            },
        }


if __name__ == "__main__":
    kb = ICARKnowledgeBase()
    print("Database successfully built with 20 ICAR/TNAU certified guidelines (24 columns)!")
    for test_crop, test_disease in [
        ("Potato", "Late_blight"),
        ("Rice", "Bacterial_leaf_blight"),
        ("Tomato", "Early_blight"),
        ("Corn", "Northern_Leaf_Blight"),
    ]:
        t = kb.get_treatment(test_crop, test_disease, lang="en")
        print(f"{test_crop} | {test_disease} -> {t['pathogen_scientific']} | {t['chemical_name']} @ {t['chemical_dosage']} [{t['source_citation']}]")
