package com.kisandrishti.ai.data

enum class AppLanguage(val code: String, val label: String, val nativeLabel: String, val localeTag: String) {
    EN("en", "English", "English", "en-IN"),
    TA("ta", "Tamil", "தமிழ்", "ta-IN"),
    HI("hi", "Hindi", "हिन्दी", "hi-IN");

    companion object {
        fun fromCode(code: String): AppLanguage = entries.firstOrNull { it.code == code } ?: EN
    }
}

enum class MainTab {
    SCAN, ASK_AI, GUIDE, HISTORY
}

enum class InspectionTarget(
    val id: String,
    val cropKey: String,
    val titleEn: String,
    val subtitle: String,
    val localLine: String,
    val isPest: Boolean = false
) {
    POTATO("potato", "Potato", "Potato", "Late & Early Blight", "உருளை • आलू"),
    TOMATO("tomato", "Tomato", "Tomato", "Blight, Curl, Spot", "தக்காளி • टमाटर"),
    RICE("rice", "Rice", "Rice", "Blast, Brown Spot", "நெல் • धान"),
    CORN("corn", "Corn", "Corn", "Blight, Rust", "சோளம் • मक्का"),
    PEST("pest", "Pest", "Check Insect Pest", "Aphid, Whitefly, Leafminer, Borer", "பூச்சி தாக்குதல் • कीट जांच", isPest = true)
}

data class DemoSample(
    val id: String,
    val assetPath: String,
    val target: InspectionTarget,
    val chipLabel: String,
    val fullTitle: String
)

data class CandidateScore(
    val label: String,
    val probabilityPct: Float
)

data class TreatmentGuideline(
    val crop: String,
    val diagnosis: String,
    val pathogenScientific: String,
    val referenceStage: String,
    val culturalAction: String,
    val organicRemedy: String,
    val chemicalName: String,
    val chemicalDosage: String,
    val phiDays: Int,
    val sourceCitation: String,
    val zoneApplicability: String,
    val regionVerified: Boolean,
    val bioCompatibilityNote: String,
    val symptomChecklist: List<String>,
    val culturalEn: String,
    val organicEn: String,
    val chemicalEn: String,
    val dosageEn: String
)

data class DiagnosisResult(
    val id: String,
    val timestampMs: Long,
    val crop: String,
    val disease: String,
    val localizedTitle: String,
    val pathogenScientific: String,
    val confidencePct: Float,
    val severityPct: Float,
    val severityStage: String,
    val isPestMode: Boolean,
    val gateAPassed: Boolean,
    val gateAReason: String,
    val gateAMessage: String,
    val gateBPassed: Boolean,
    val isBorderline: Boolean,
    val state: String,
    val district: String,
    val blurVariance: Float,
    val foliageRatio: Float,
    val leafIsolationPct: Float,
    val healthyPct: Float,
    val chlorosisPct: Float,
    val necrosisPct: Float,
    val topCandidates: List<CandidateScore>,
    val guideline: TreatmentGuideline?,
    val summaryAdvice: String,
    val spokenScript: String,
    val originalImagePath: String,
    val overlayImagePath: String,
    val inferenceEngine: String,
    val visionLatencyMs: Long,
    val totalLatencyMs: Long,
    val languageCode: String
)

data class ChatMessage(
    val id: String,
    val isUser: Boolean,
    val text: String,
    val meta: String = "",
    val timestampMs: Long = System.currentTimeMillis()
)

data class ScanHistoryEntry(
    val id: String,
    val timestampMs: Long,
    val crop: String,
    val disease: String,
    val localizedTitle: String,
    val confidencePct: Float,
    val severityPct: Float,
    val severityStage: String,
    val isPestMode: Boolean,
    val imagePath: String,
    val summaryNote: String,
    val totalLatencyMs: Long,
    val resultJson: String
)

data class PiEdgeConfig(
    val usePiServer: Boolean = false,
    val piBaseUrl: String = "http://192.168.1.100:8000",
    val lastStatusText: String = "Standalone On-Device Edge Ready"
)
