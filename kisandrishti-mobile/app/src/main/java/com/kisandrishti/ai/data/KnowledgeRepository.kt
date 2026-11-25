package com.kisandrishti.ai.data

import android.content.Context
import android.database.sqlite.SQLiteDatabase
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream

object VerifiedRegions {
    val states: LinkedHashMap<String, List<String>> = linkedMapOf(
        "National (ICAR Baseline)" to listOf("All Districts"),
        "Tamil Nadu" to listOf("Coimbatore", "Thanjavur", "Madurai", "Erode", "Salem", "Tiruchirappalli"),
        "Punjab" to listOf("Ludhiana", "Amritsar", "Jalandhar", "Patiala", "Bathinda"),
        "Uttar Pradesh" to listOf("Lucknow", "Agra", "Kanpur", "Varanasi", "Meerut"),
        "Maharashtra" to listOf("Pune", "Nashik", "Nagpur", "Aurangabad"),
        "Karnataka" to listOf("Bengaluru Rural", "Mysuru", "Belagavi", "Hassan"),
        "Bihar" to listOf("Patna", "Nalanda", "Muzaffarpur", "Bhagalpur")
    )
}

object DemoSamplesCatalog {
    val samples = listOf(
        DemoSample("potato_late_blight", "samples/potato_late_blight.jpg", InspectionTarget.POTATO, "Blight Leaf", "Potato Late Blight"),
        DemoSample("potato_healthy", "samples/potato_healthy.jpg", InspectionTarget.POTATO, "Potato Healthy", "Potato Healthy Leaf"),
        DemoSample("tomato_early_blight", "samples/tomato_early_blight.jpg", InspectionTarget.TOMATO, "Tomato Spot", "Tomato Early Blight"),
        DemoSample("rice_bacterial_blight", "samples/rice_bacterial_blight.jpg", InspectionTarget.RICE, "Rice Blight", "Rice Bacterial Blight"),
        DemoSample("rice_brown_spot", "samples/rice_brown_spot.jpg", InspectionTarget.RICE, "Brown Spot", "Rice Brown Spot"),
        DemoSample("corn_leaf_blight", "samples/corn_leaf_blight.jpg", InspectionTarget.CORN, "Corn Blight", "Corn Northern Blight"),
        DemoSample("pest_aphid", "samples/pest_aphid.jpg", InspectionTarget.PEST, "Aphid Infested", "Insect Pest — Aphid")
    )
}

class KnowledgeRepository(private val context: Context) {

    private val dbFile = File(context.filesDir, "icar_agronomic_kb.sqlite")
    private val historyFile = File(context.filesDir, "scan_history.json")
    private val prefs = context.getSharedPreferences("kisandrishti_prefs", Context.MODE_PRIVATE)

    @Synchronized
    private fun openDb(): SQLiteDatabase {
        if (!dbFile.exists() || dbFile.length() < 10_000L) {
            context.assets.open("icar_agronomic_kb.sqlite").use { input ->
                FileOutputStream(dbFile).use { output ->
                    input.copyTo(output)
                }
            }
        }
        return SQLiteDatabase.openDatabase(
            dbFile.absolutePath,
            null,
            SQLiteDatabase.OPEN_READONLY or SQLiteDatabase.NO_LOCALIZED_COLLATORS
        )
    }

    private fun normalizeKey(text: String): String {
        var s = text.lowercase().replace(" ", "_").replace("-", "_").trim()
        while (s.contains("__")) s = s.replace("__", "_")
        return s
    }

    private fun normalizeCrop(crop: String): String {
        val l = crop.lowercase()
        return when {
            "corn" in l || "maize" in l -> "Corn"
            "potato" in l -> "Potato"
            "tomato" in l -> "Tomato"
            "rice" in l || "paddy" in l -> "Rice"
            "pest" in l -> "Pest"
            else -> crop.replaceFirstChar { it.uppercase() }
        }
    }

    private fun isRegionVerified(state: String, zoneApplicability: String): Boolean {
        if (state.isBlank() || state == "National (ICAR Baseline)") return true
        if ("National" in zoneApplicability) return true
        return state.lowercase() in zoneApplicability.lowercase()
    }

    fun getTreatment(crop: String, diagnosis: String, lang: AppLanguage, state: String): TreatmentGuideline? {
        val db = openDb()
        return db.use { database ->
            val cropKey = normalizeCrop(crop)
            val normDiag = normalizeKey(diagnosis)

            val available = mutableListOf<String>()
            database.rawQuery(
                "SELECT diagnosis FROM treatment_guidelines WHERE LOWER(crop) = LOWER(?)",
                arrayOf(cropKey)
            ).use { c ->
                while (c.moveToNext()) available.add(c.getString(0))
            }

            val matchedDiag = available.firstOrNull { cand ->
                cand.lowercase() in normDiag || normDiag in cand.lowercase()
            } ?: available.firstOrNull { cand ->
                cand.lowercase().split("_").filter { it.length > 3 }.any { it in normDiag }
            } ?: available.firstOrNull() ?: normDiag

            val langCol = when (lang) {
                AppLanguage.TA -> "ta"
                AppLanguage.HI -> "hi"
                AppLanguage.EN -> "en"
            }

            database.rawQuery(
                """
                SELECT crop, diagnosis, pathogen_scientific, stage,
                       cultural_$langCol, organic_$langCol, chemical_$langCol, dosage_$langCol,
                       phi_days, source_citation, zone_applicability, bio_compatibility_note,
                       checklist_$langCol, cultural_en, organic_en, chemical_en, dosage_en
                FROM treatment_guidelines
                WHERE LOWER(crop) = LOWER(?) AND LOWER(diagnosis) = LOWER(?)
                LIMIT 1
                """.trimIndent(),
                arrayOf(cropKey, matchedDiag)
            ).use { cursor ->
                if (!cursor.moveToFirst()) return@use null
                val zone = cursor.getString(10) ?: ""
                val checklistRaw = cursor.getString(12) ?: ""
                TreatmentGuideline(
                    crop = cursor.getString(0),
                    diagnosis = cursor.getString(1),
                    pathogenScientific = cursor.getString(2) ?: "",
                    referenceStage = cursor.getString(3) ?: "Moderate",
                    culturalAction = cursor.getString(4) ?: "",
                    organicRemedy = cursor.getString(5) ?: "",
                    chemicalName = cursor.getString(6) ?: "None",
                    chemicalDosage = cursor.getString(7) ?: "N/A",
                    phiDays = cursor.getInt(8),
                    sourceCitation = cursor.getString(9) ?: "ICAR/TNAU/CIBRC",
                    zoneApplicability = zone,
                    regionVerified = isRegionVerified(state, zone),
                    bioCompatibilityNote = cursor.getString(11) ?: "",
                    symptomChecklist = checklistRaw.split("|").map { it.trim() }.filter { it.isNotEmpty() },
                    culturalEn = cursor.getString(13) ?: "",
                    organicEn = cursor.getString(14) ?: "",
                    chemicalEn = cursor.getString(15) ?: "",
                    dosageEn = cursor.getString(16) ?: ""
                )
            }
        }
    }

    fun listAllGuidelines(lang: AppLanguage): List<TreatmentGuideline> {
        val db = openDb()
        val langCol = when (lang) {
            AppLanguage.TA -> "ta"
            AppLanguage.HI -> "hi"
            AppLanguage.EN -> "en"
        }
        val list = mutableListOf<TreatmentGuideline>()
        db.use { database ->
            database.rawQuery(
                """
                SELECT crop, diagnosis, pathogen_scientific, stage,
                       cultural_$langCol, organic_$langCol, chemical_$langCol, dosage_$langCol,
                       phi_days, source_citation, zone_applicability, bio_compatibility_note,
                       checklist_$langCol, cultural_en, organic_en, chemical_en, dosage_en
                FROM treatment_guidelines
                ORDER BY CASE crop WHEN 'Pest' THEN 2 ELSE 1 END, crop, diagnosis
                """.trimIndent(),
                null
            ).use { cursor ->
                while (cursor.moveToNext()) {
                    val checklistRaw = cursor.getString(12) ?: ""
                    list.add(
                        TreatmentGuideline(
                            crop = cursor.getString(0),
                            diagnosis = cursor.getString(1),
                            pathogenScientific = cursor.getString(2) ?: "",
                            referenceStage = cursor.getString(3) ?: "Moderate",
                            culturalAction = cursor.getString(4) ?: "",
                            organicRemedy = cursor.getString(5) ?: "",
                            chemicalName = cursor.getString(6) ?: "None",
                            chemicalDosage = cursor.getString(7) ?: "N/A",
                            phiDays = cursor.getInt(8),
                            sourceCitation = cursor.getString(9) ?: "ICAR/TNAU/CIBRC",
                            zoneApplicability = cursor.getString(10) ?: "",
                            regionVerified = true,
                            bioCompatibilityNote = cursor.getString(11) ?: "",
                            symptomChecklist = checklistRaw.split("|").map { it.trim() }.filter { it.isNotEmpty() },
                            culturalEn = cursor.getString(13) ?: "",
                            organicEn = cursor.getString(14) ?: "",
                            chemicalEn = cursor.getString(15) ?: "",
                            dosageEn = cursor.getString(16) ?: ""
                        )
                    )
                }
            }
        }
        return list
    }

    fun answerFollowUpOffline(question: String, diag: DiagnosisResult?, lang: AppLanguage): String {
        val q = question.lowercase()
        val g = diag?.guideline
        if (diag == null || g == null) {
            return when (lang) {
                AppLanguage.TA -> "முதலில் ஒரு இலை அல்லது பூச்சி படத்தை ஆய்வு செய்யுங்கள். பிறகு உங்கள் பயிர் கேள்விகளுக்கு உடனடி ஆலோசனை வழங்கப்படும்."
                AppLanguage.HI -> "कृपया पहले किसी पत्ती या कीट की फोटो स्कैन करें। इसके बाद मैं आपकी फसल के अनुसार सही सलाह दे सकूंगा।"
                AppLanguage.EN -> "Scan or pick a crop leaf or pest photo first so I can give verified ICAR/TNAU care guidance for your field."
            }
        }

        val wantsOrganic = anyIn(q, listOf("organic", "natural", "bio", "neem", "இயற்கை", "வேம்பு", "जैविक", "नीम"))
        val wantsPhi = anyIn(q, listOf("phi", "harvest", "wait", "days", "அறுவடை", "நாள்", "कटाई", "दिन"))
        val wantsChem = anyIn(q, listOf("chemical", "spray", "dose", "dosage", "medicine", "மருந்து", "அளவு", "दवा", "मात्रा", "छिड़काव"))
        val wantsBee = anyIn(q, listOf("bee", "pollinator", "insect", "safe", "தேனீ", "மகரந்தம்", "मधुमक्खी", "सुरक्षा"))

        return when {
            wantsOrganic -> g.organicRemedy
            wantsPhi -> {
                if (!diag.gateBPassed || g.chemicalName.startsWith("None", true)) {
                    when (lang) {
                        AppLanguage.TA -> "இந்த நிலைக்கு இரசாயன மருந்து பரிந்துரைக்கப்படவில்லை; அறுவடை காத்திருப்பு காலம் தேவையில்லை."
                        AppLanguage.HI -> "इस स्थिति में रासायनिक दवा नहीं दी गई है, इसलिए कटाई प्रतीक्षा अवधि लागू नहीं होती।"
                        AppLanguage.EN -> "No chemical spray is active for this diagnosis, so there is no chemical pre-harvest wait period."
                    }
                } else {
                    when (lang) {
                        AppLanguage.TA -> "${g.chemicalName} தெளித்த பிறகு அறுவடைக்கு முன் குறைந்தது ${g.phiDays} நாட்கள் காத்திருக்க வேண்டும். (${g.sourceCitation})"
                        AppLanguage.HI -> "${g.chemicalName} के छिड़काव के बाद कटाई से पहले कम से कम ${g.phiDays} दिन प्रतीक्षा करें। (${g.sourceCitation})"
                        AppLanguage.EN -> "Wait at least ${g.phiDays} days before harvesting after applying ${g.chemicalName}. Verified source: ${g.sourceCitation}."
                    }
                }
            }
            wantsBee -> g.bioCompatibilityNote.ifBlank {
                "Spray during early dawn or late afternoon to avoid active honeybee foraging hours."
            }
            wantsChem -> {
                if (!diag.gateBPassed) {
                    when (lang) {
                        AppLanguage.TA -> "பாதுகாப்பு விதி B (75% கீழ் துல்லியம்) காரணமாக இரசாயன மருந்து நிறுத்தப்பட்டுள்ளது. ${g.culturalAction}"
                        AppLanguage.HI -> "सुरक्षा नियम B (75% से कम सटीकता) के कारण रासायनिक सलाह रोकी गई है। ${g.culturalAction}"
                        AppLanguage.EN -> "Gate B halted chemical sprays because confidence is below 75%. Follow cultural care: ${g.culturalAction}"
                    }
                } else if (g.chemicalName.startsWith("None", true) || g.chemicalName.startsWith("இல்லை") || g.chemicalName.startsWith("कोई नहीं")) {
                    g.culturalAction
                } else {
                    "${g.chemicalName} @ ${g.chemicalDosage} (PHI: ${g.phiDays} days). ${g.bioCompatibilityNote}"
                }
            }
            else -> "${g.culturalAction} ${g.organicRemedy}".trim()
        }
    }

    private fun anyIn(text: String, keys: List<String>): Boolean = keys.any { it in text }

    fun loadHistory(): List<ScanHistoryEntry> {
        if (!historyFile.exists()) return emptyList()
        return try {
            val arr = JSONArray(historyFile.readText())
            (0 until arr.length()).map { idx ->
                val o = arr.getJSONObject(idx)
                ScanHistoryEntry(
                    id = o.getString("id"),
                    timestampMs = o.getLong("timestampMs"),
                    crop = o.getString("crop"),
                    disease = o.getString("disease"),
                    localizedTitle = o.optString("localizedTitle", o.getString("disease")),
                    confidencePct = o.getDouble("confidencePct").toFloat(),
                    severityPct = o.getDouble("severityPct").toFloat(),
                    severityStage = o.getString("severityStage"),
                    isPestMode = o.optBoolean("isPestMode", false),
                    imagePath = o.optString("imagePath", ""),
                    summaryNote = o.optString("summaryNote", ""),
                    totalLatencyMs = o.optLong("totalLatencyMs", 0L),
                    resultJson = o.optString("resultJson", "")
                )
            }
        } catch (_: Exception) {
            emptyList()
        }
    }

    fun saveScan(diag: DiagnosisResult): List<ScanHistoryEntry> {
        val current = loadHistory().toMutableList()
        val serialized = serializeDiagnosis(diag).toString()
        val entry = ScanHistoryEntry(
            id = diag.id,
            timestampMs = diag.timestampMs,
            crop = diag.crop,
            disease = diag.disease,
            localizedTitle = diag.localizedTitle,
            confidencePct = diag.confidencePct,
            severityPct = diag.severityPct,
            severityStage = diag.severityStage,
            isPestMode = diag.isPestMode,
            imagePath = diag.originalImagePath,
            summaryNote = diag.guideline?.culturalAction ?: diag.summaryAdvice,
            totalLatencyMs = diag.totalLatencyMs,
            resultJson = serialized
        )
        current.add(0, entry)
        val trimmed = current.take(25)
        persistHistory(trimmed)
        return trimmed
    }

    fun clearHistory(): List<ScanHistoryEntry> {
        if (historyFile.exists()) historyFile.delete()
        return emptyList()
    }

    private fun persistHistory(list: List<ScanHistoryEntry>) {
        val arr = JSONArray()
        list.forEach { e ->
            arr.put(JSONObject().apply {
                put("id", e.id)
                put("timestampMs", e.timestampMs)
                put("crop", e.crop)
                put("disease", e.disease)
                put("localizedTitle", e.localizedTitle)
                put("confidencePct", e.confidencePct)
                put("severityPct", e.severityPct)
                put("severityStage", e.severityStage)
                put("isPestMode", e.isPestMode)
                put("imagePath", e.imagePath)
                put("summaryNote", e.summaryNote)
                put("totalLatencyMs", e.totalLatencyMs)
                put("resultJson", e.resultJson)
            })
        }
        historyFile.writeText(arr.toString())
    }

    fun loadPiConfig(): PiEdgeConfig = PiEdgeConfig(
        usePiServer = prefs.getBoolean("use_pi_server", false),
        piBaseUrl = prefs.getString("pi_base_url", "http://192.168.1.100:8000") ?: "http://192.168.1.100:8000",
        lastStatusText = prefs.getString("last_status", "Standalone On-Device Edge Ready") ?: "Standalone On-Device Edge Ready"
    )

    fun savePiConfig(cfg: PiEdgeConfig) {
        prefs.edit()
            .putBoolean("use_pi_server", cfg.usePiServer)
            .putString("pi_base_url", cfg.piBaseUrl)
            .putString("last_status", cfg.lastStatusText)
            .apply()
    }

    private fun serializeDiagnosis(d: DiagnosisResult): JSONObject {
        return JSONObject().apply {
            put("id", d.id)
            put("timestampMs", d.timestampMs)
            put("crop", d.crop)
            put("disease", d.disease)
            put("localizedTitle", d.localizedTitle)
            put("pathogenScientific", d.pathogenScientific)
            put("confidencePct", d.confidencePct)
            put("severityPct", d.severityPct)
            put("severityStage", d.severityStage)
            put("isPestMode", d.isPestMode)
            put("gateAPassed", d.gateAPassed)
            put("gateAReason", d.gateAReason)
            put("gateAMessage", d.gateAMessage)
            put("gateBPassed", d.gateBPassed)
            put("isBorderline", d.isBorderline)
            put("state", d.state)
            put("district", d.district)
            put("blurVariance", d.blurVariance)
            put("foliageRatio", d.foliageRatio)
            put("leafIsolationPct", d.leafIsolationPct)
            put("healthyPct", d.healthyPct)
            put("chlorosisPct", d.chlorosisPct)
            put("necrosisPct", d.necrosisPct)
            put("summaryAdvice", d.summaryAdvice)
            put("spokenScript", d.spokenScript)
            put("originalImagePath", d.originalImagePath)
            put("overlayImagePath", d.overlayImagePath)
            put("inferenceEngine", d.inferenceEngine)
            put("visionLatencyMs", d.visionLatencyMs)
            put("totalLatencyMs", d.totalLatencyMs)
            put("languageCode", d.languageCode)
            put("topCandidates", JSONArray().apply {
                d.topCandidates.forEach {
                    put(JSONObject().apply {
                        put("label", it.label)
                        put("probabilityPct", it.probabilityPct)
                    })
                }
            })
        }
    }

    fun restoreDiagnosis(entry: ScanHistoryEntry, lang: AppLanguage): DiagnosisResult? {
        if (entry.resultJson.isBlank()) return null
        return try {
            val o = JSONObject(entry.resultJson)
            val crop = o.getString("crop")
            val disease = o.getString("disease")
            val state = o.optString("state", "National (ICAR Baseline)")
            val guideline = getTreatment(if (o.optBoolean("isPestMode")) "Pest" else crop, disease, lang, state)
            val candsArr = o.optJSONArray("topCandidates") ?: JSONArray()
            val cands = (0 until candsArr.length()).map { i ->
                val co = candsArr.getJSONObject(i)
                CandidateScore(co.getString("label"), co.getDouble("probabilityPct").toFloat())
            }
            DiagnosisResult(
                id = o.getString("id"),
                timestampMs = o.getLong("timestampMs"),
                crop = crop,
                disease = disease,
                localizedTitle = o.optString("localizedTitle", disease),
                pathogenScientific = o.optString("pathogenScientific", ""),
                confidencePct = o.getDouble("confidencePct").toFloat(),
                severityPct = o.getDouble("severityPct").toFloat(),
                severityStage = o.getString("severityStage"),
                isPestMode = o.optBoolean("isPestMode", false),
                gateAPassed = o.optBoolean("gateAPassed", true),
                gateAReason = o.optString("gateAReason", ""),
                gateAMessage = o.optString("gateAMessage", ""),
                gateBPassed = o.optBoolean("gateBPassed", true),
                isBorderline = o.optBoolean("isBorderline", false),
                state = state,
                district = o.optString("district", "All Districts"),
                blurVariance = o.optDouble("blurVariance", 0.0).toFloat(),
                foliageRatio = o.optDouble("foliageRatio", 0.0).toFloat(),
                leafIsolationPct = o.optDouble("leafIsolationPct", 0.0).toFloat(),
                healthyPct = o.optDouble("healthyPct", 0.0).toFloat(),
                chlorosisPct = o.optDouble("chlorosisPct", 0.0).toFloat(),
                necrosisPct = o.optDouble("necrosisPct", 0.0).toFloat(),
                topCandidates = cands,
                guideline = guideline,
                summaryAdvice = guideline?.let { "${it.culturalAction} ${it.organicRemedy}" } ?: o.optString("summaryAdvice", ""),
                spokenScript = o.optString("spokenScript", ""),
                originalImagePath = o.optString("originalImagePath", ""),
                overlayImagePath = o.optString("overlayImagePath", ""),
                inferenceEngine = o.optString("inferenceEngine", "On-Device ONNX"),
                visionLatencyMs = o.optLong("visionLatencyMs", 0L),
                totalLatencyMs = o.optLong("totalLatencyMs", 0L),
                languageCode = lang.code
            )
        } catch (_: Exception) {
            null
        }
    }
}
