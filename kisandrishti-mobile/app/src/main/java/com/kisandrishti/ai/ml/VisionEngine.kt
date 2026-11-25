package com.kisandrishti.ai.ml

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.Context
import android.graphics.Bitmap
import android.graphics.Color
import com.kisandrishti.ai.data.AppLanguage
import com.kisandrishti.ai.data.CandidateScore
import com.kisandrishti.ai.data.DiagnosisResult
import com.kisandrishti.ai.data.KnowledgeRepository
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.nio.FloatBuffer
import kotlin.math.exp
import kotlin.math.max
import kotlin.math.min

class VisionEngine(
    private val context: Context,
    private val repo: KnowledgeRepository
) {
    companion object {
        const val MIN_LAPLACIAN_BLUR_VAR = 20.0f
        const val MIN_FOLIAGE_RATIO = 0.08f
        const val REJECT_CONFIDENCE_THRESHOLD = 0.50f
        const val ACCEPT_CONFIDENCE_THRESHOLD = 0.75f
    }

    private val env: OrtEnvironment by lazy { OrtEnvironment.getEnvironment() }
    private var leafSession: OrtSession? = null
    private var pestSession: OrtSession? = null
    private var leafClasses: List<String> = emptyList()
    private var pestClasses: List<String> = emptyList()
    private var mean = floatArrayOf(0.485f, 0.456f, 0.406f)
    private var std = floatArrayOf(0.229f, 0.224f, 0.225f)

    private val scansDir = File(context.filesDir, "scans").apply { mkdirs() }

    @Synchronized
    private fun ensureLoaded() {
        if (leafSession == null) {
            val meta = JSONObject(context.assets.open("models/classes_4crops.json").bufferedReader().readText())
            val arr = meta.getJSONArray("classes")
            leafClasses = (0 until arr.length()).map { arr.getString(it) }
            val mArr = meta.optJSONArray("mean")
            val sArr = meta.optJSONArray("std")
            if (mArr != null && mArr.length() == 3) {
                mean = floatArrayOf(mArr.getDouble(0).toFloat(), mArr.getDouble(1).toFloat(), mArr.getDouble(2).toFloat())
            }
            if (sArr != null && sArr.length() == 3) {
                std = floatArrayOf(sArr.getDouble(0).toFloat(), sArr.getDouble(1).toFloat(), sArr.getDouble(2).toFloat())
            }
            val bytes = context.assets.open("models/mobilenetv3_4crops_standalone.onnx").use { it.readBytes() }
            leafSession = env.createSession(bytes, OrtSession.SessionOptions().apply {
                setIntraOpNumThreads(4)
            })
        }
        if (pestSession == null) {
            val meta = JSONObject(context.assets.open("models/pest_classes.json").bufferedReader().readText())
            val arr = meta.getJSONArray("classes")
            pestClasses = (0 until arr.length()).map { arr.getString(it) }
            val bytes = context.assets.open("models/pest_mobilenetv3.onnx").use { it.readBytes() }
            pestSession = env.createSession(bytes, OrtSession.SessionOptions().apply {
                setIntraOpNumThreads(4)
            })
        }
    }

    private fun preprocessNchw(bitmap: Bitmap): FloatBuffer {
        val resized = Bitmap.createScaledBitmap(bitmap, 256, 256, true)
        val cropStart = (256 - 224) / 2
        val pixels = IntArray(224 * 224)
        resized.getPixels(pixels, 0, 224, cropStart, cropStart, 224, 224)

        val buf = FloatBuffer.allocate(3 * 224 * 224)
        val planeSize = 224 * 224
        for (i in pixels.indices) {
            val c = pixels[i]
            val r = ((c shr 16) and 0xFF) / 255.0f
            val g = ((c shr 8) and 0xFF) / 255.0f
            val b = (c and 0xFF) / 255.0f
            buf.put(i, (r - mean[0]) / std[0])
            buf.put(planeSize + i, (g - mean[1]) / std[1])
            buf.put(planeSize * 2 + i, (b - mean[2]) / std[2])
        }
        buf.rewind()
        return buf
    }

    private fun computeLaplacianVariance(bitmap: Bitmap): Float {
        val small = Bitmap.createScaledBitmap(bitmap, 256, 256, true)
        val w = 256
        val h = 256
        val pixels = IntArray(w * h)
        small.getPixels(pixels, 0, w, 0, 0, w, h)
        val gray = FloatArray(w * h)
        for (i in pixels.indices) {
            val c = pixels[i]
            gray[i] = 0.299f * ((c shr 16) and 0xFF) +
                0.587f * ((c shr 8) and 0xFF) +
                0.114f * (c and 0xFF)
        }
        var sum = 0.0
        var sumSq = 0.0
        var count = 0
        for (y in 1 until h - 1) {
            for (x in 1 until w - 1) {
                val idx = y * w + x
                val lap = gray[idx - w] + gray[idx + w] + gray[idx - 1] + gray[idx + 1] - 4f * gray[idx]
                sum += lap
                sumSq += lap * lap
                count++
            }
        }
        val m = sum / max(count, 1)
        return (sumSq / max(count, 1) - m * m).toFloat().coerceAtLeast(0f)
    }

    private data class HsvAnalysis(
        val foliageRatio: Float,
        val leafIsolationPct: Float,
        val healthyPct: Float,
        val chlorosisPct: Float,
        val necrosisPct: Float,
        val severityPct: Float,
        val stage: String,
        val overlayBitmap: Bitmap
    )

    private fun analyzeHsv(bitmap: Bitmap, uncertain: Boolean): HsvAnalysis {
        val w = bitmap.width
        val h = bitmap.height
        val pixels = IntArray(w * h)
        bitmap.getPixels(pixels, 0, w, 0, 0, w, h)
        val outPixels = pixels.copyOf()

        val hsv = FloatArray(3)
        var leafCount = 0
        var healthyCount = 0
        var chlorosisCount = 0
        var necrosisCount = 0
        var lesionCount = 0

        for (i in pixels.indices) {
            val px = pixels[i]
            Color.colorToHSV(px, hsv)
            // OpenCV HSV ranges: H = 0..180, S = 0..255, V = 0..255
            val cvH = hsv[0] / 2.0f
            val cvS = hsv[1] * 255.0f
            val cvV = hsv[2] * 255.0f

            val isHealthy = cvH in 25f..85f && cvS >= 30f && cvV >= 30f
            val isNecrosis = cvH in 5f..24f && cvS >= 40f && cvV in 20f..180f
            val isChlorosis = cvH in 22f..38f && cvS >= 100f && cvV >= 100f

            if (isHealthy || isNecrosis || isChlorosis) {
                leafCount++
                if (isHealthy) healthyCount++
                if (isNecrosis) necrosisCount++
                if (isChlorosis) chlorosisCount++
                if (isNecrosis || isChlorosis) {
                    lesionCount++
                    // Blend red highlight on lesions cleanly while keeping leaf veins visible
                    val r = (((px shr 16) and 0xFF) * 0.35f + 235f * 0.65f).toInt().coerceIn(0, 255)
                    val g = (((px shr 8) and 0xFF) * 0.35f + 40f * 0.65f).toInt().coerceIn(0, 255)
                    val b = ((px and 0xFF) * 0.35f + 50f * 0.65f).toInt().coerceIn(0, 255)
                    outPixels[i] = Color.rgb(r, g, b)
                }
            }
        }

        val total = max(pixels.size, 1)
        val foliageRatio = leafCount.toFloat() / total.toFloat()
        val leafIsolationPct = (foliageRatio * 100f).coerceIn(0f, 100f)
        val overlayBitmap = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
        overlayBitmap.setPixels(outPixels, 0, w, 0, 0, w, h)

        if (leafCount == 0) {
            return HsvAnalysis(0f, 0f, 0f, 0f, 0f, 0f, "Uncertain", overlayBitmap)
        }

        val sev = (lesionCount.toFloat() / leafCount.toFloat()) * 100f
        val necPct = min((necrosisCount.toFloat() / leafCount.toFloat()) * 100f, 100f)
        val chlPct = min((chlorosisCount.toFloat() / leafCount.toFloat()) * 100f, 100f)
        val hltPct = max(0f, min(100f - sev, 100f))

        val stage = when {
            uncertain -> "Uncertain"
            sev < 2.0f -> "Healthy"
            sev < 10.0f -> "Mild"
            sev <= 25.0f -> "Moderate"
            else -> "Severe"
        }

        return HsvAnalysis(
            foliageRatio = foliageRatio,
            leafIsolationPct = (leafIsolationPct * 10f).toInt() / 10f,
            healthyPct = (hltPct * 10f).toInt() / 10f,
            chlorosisPct = (chlPct * 10f).toInt() / 10f,
            necrosisPct = (necPct * 10f).toInt() / 10f,
            severityPct = (sev * 10f).toInt() / 10f,
            stage = stage,
            overlayBitmap = overlayBitmap
        )
    }

    private fun softmax(logits: FloatArray): FloatArray {
        val maxVal = logits.maxOrNull() ?: 0f
        val exps = FloatArray(logits.size)
        var sum = 0.0
        for (i in logits.indices) {
            val v = exp((logits[i] - maxVal).toDouble())
            exps[i] = v.toFloat()
            sum += v
        }
        val inv = (1.0 / max(sum, 1e-9)).toFloat()
        for (i in exps.indices) exps[i] *= inv
        return exps
    }

    private fun normalizeCrop(raw: String): String {
        val s = raw.lowercase().trim()
        return when {
            "corn" in s || "maize" in s -> "Corn"
            "potato" in s -> "Potato"
            "tomato" in s -> "Tomato"
            "rice" in s || "paddy" in s -> "Rice"
            else -> raw.replaceFirstChar { it.uppercase() }
        }
    }

    private fun saveBitmap(bitmap: Bitmap, name: String): String {
        val f = File(scansDir, name)
        FileOutputStream(f).use { out ->
            bitmap.compress(Bitmap.CompressFormat.JPEG, 90, out)
        }
        return f.absolutePath
    }

    fun diagnose(
        bitmap: Bitmap,
        selectedCrop: String,
        isPestMode: Boolean,
        lang: AppLanguage,
        state: String,
        district: String
    ): DiagnosisResult {
        val tStart = System.currentTimeMillis()
        ensureLoaded()

        val id = "kd_${tStart}"
        val origPath = saveBitmap(bitmap, "${id}_orig.jpg")

        val blurVar = computeLaplacianVariance(bitmap)
        if (blurVar < MIN_LAPLACIAN_BLUR_VAR) {
            return rejectedResult(
                id, tStart, selectedCrop, isPestMode, state, district,
                "IMAGE_TOO_BLURRY",
                "Gate A Halt: Photo is too blurry (sharpness=%.1f < 20.0). Hold camera steady and retake.".format(blurVar),
                blurVar, 0f, origPath
            )
        }

        val preHsv = if (!isPestMode) analyzeHsv(bitmap, uncertain = false) else null
        if (preHsv != null && preHsv.foliageRatio < MIN_FOLIAGE_RATIO) {
            return rejectedResult(
                id, tStart, selectedCrop, false, state, district,
                "NON_LEAF_IMAGE",
                "Gate A Halt: Very low plant foliage detected (%.1f%%). Frame a close-up of a single leaf.".format(preHsv.foliageRatio * 100f),
                blurVar, preHsv.foliageRatio, origPath
            )
        }

        val tVisionStart = System.currentTimeMillis()
        val session = (if (isPestMode) pestSession else leafSession)!!
        val classes = if (isPestMode) pestClasses else leafClasses
        val inputName = session.inputNames.first()
        val floatBuf = preprocessNchw(bitmap)
        val logits = OnnxTensor.createTensor(env, floatBuf, longArrayOf(1L, 3L, 224L, 224L)).use { tensor ->
            session.run(mapOf(inputName to tensor)).use { res ->
                val outArr = res[0].value as Array<FloatArray>
                outArr[0]
            }
        }
        val visionMs = max(1L, System.currentTimeMillis() - tVisionStart)
        val probs = softmax(logits)

        val sortedIdx = probs.indices.sortedByDescending { probs[it] }
        val topIdx = sortedIdx.first()
        val conf = probs[topIdx]
        val confPct = (conf * 1000f).toInt() / 10f

        val candidates = sortedIdx.take(4).map { idx ->
            val rawName = classes[idx]
            val clean = rawName.replace("___", " — ").replace("_", " ")
            CandidateScore(clean, ((probs[idx] * 1000f).toInt() / 10f))
        }

        if (conf < REJECT_CONFIDENCE_THRESHOLD) {
            return rejectedResult(
                id, tStart, selectedCrop, isPestMode, state, district,
                "LOW_CONFIDENCE_UNKNOWN",
                "Gate A Halt: Prediction confidence (%.1f%%) is below the 50%% floor. Capture a sharper close-up.".format(confPct),
                blurVar, preHsv?.foliageRatio ?: 1f, origPath, confPct, visionMs, candidates
            )
        }

        val topClass = classes[topIdx]
        val diagnosedCrop: String
        val diseaseKey: String
        if (isPestMode) {
            diagnosedCrop = "Pest"
            diseaseKey = topClass
        } else {
            val parts = topClass.split("___")
            diagnosedCrop = normalizeCrop(parts.getOrElse(0) { selectedCrop })
            diseaseKey = parts.getOrElse(1) { topClass }

            val normSelected = normalizeCrop(selectedCrop)
            if (normSelected != diagnosedCrop) {
                return rejectedResult(
                    id, tStart, normSelected, false, state, district,
                    "CROP_MISMATCH",
                    "Crop Mismatch Alert: You selected $normSelected, but this leaf matches $diagnosedCrop ($confPct%). Halted to prevent wrong treatment.",
                    blurVar, preHsv?.foliageRatio ?: 0f, origPath, confPct, visionMs, candidates
                )
            }
        }

        val isBorderline = conf < ACCEPT_CONFIDENCE_THRESHOLD
        val finalHsv = if (!isPestMode) analyzeHsv(bitmap, uncertain = isBorderline) else null
        val overlayPath = if (finalHsv != null) saveBitmap(finalHsv.overlayBitmap, "${id}_overlay.jpg") else origPath

        val guideline = repo.getTreatment(if (isPestMode) "Pest" else diagnosedCrop, diseaseKey, lang, state)
        val hasChem = guideline != null &&
            !guideline.chemicalName.startsWith("None", true) &&
            !guideline.chemicalName.startsWith("இல்லை") &&
            !guideline.chemicalName.startsWith("कोई नहीं")
        val gateBPassed = conf >= ACCEPT_CONFIDENCE_THRESHOLD &&
            (guideline?.regionVerified ?: true) &&
            !guideline?.sourceCitation.isNullOrBlank() &&
            hasChem

        val sevStage = if (isPestMode) (if (isBorderline) "Uncertain" else "Moderate") else (finalHsv?.stage ?: "Moderate")
        val sevPct = if (isPestMode) 0f else (finalHsv?.severityPct ?: 0f)
        val cleanDisease = diseaseKey.replace("_", " ")
        val localizedTitle = if (isPestMode) "Pest: $cleanDisease" else "$diagnosedCrop $cleanDisease"
        val summaryAdvice = guideline?.let { "${it.culturalAction} ${it.organicRemedy}".trim() }
            ?: "Maintain field sanitation and inspect lower leaves."

        val totalMs = max(visionMs + 4L, System.currentTimeMillis() - tStart)
        return DiagnosisResult(
            id = id,
            timestampMs = tStart,
            crop = diagnosedCrop,
            disease = cleanDisease,
            localizedTitle = localizedTitle,
            pathogenScientific = guideline?.pathogenScientific ?: "",
            confidencePct = confPct,
            severityPct = sevPct,
            severityStage = sevStage,
            isPestMode = isPestMode,
            gateAPassed = true,
            gateAReason = "PASSED",
            gateAMessage = "",
            gateBPassed = gateBPassed,
            isBorderline = isBorderline,
            state = state,
            district = district,
            blurVariance = blurVar,
            foliageRatio = preHsv?.foliageRatio ?: 1f,
            leafIsolationPct = finalHsv?.leafIsolationPct ?: 0f,
            healthyPct = finalHsv?.healthyPct ?: 0f,
            chlorosisPct = finalHsv?.chlorosisPct ?: 0f,
            necrosisPct = finalHsv?.necrosisPct ?: 0f,
            topCandidates = candidates,
            guideline = guideline,
            summaryAdvice = summaryAdvice,
            spokenScript = "$localizedTitle. ${summaryAdvice}",
            originalImagePath = origPath,
            overlayImagePath = overlayPath,
            inferenceEngine = if (isPestMode) "On-Device ONNX (pest_mobilenetv3)" else "On-Device ONNX (mobilenetv3_4crops)",
            visionLatencyMs = visionMs,
            totalLatencyMs = totalMs,
            languageCode = lang.code
        )
    }

    private fun rejectedResult(
        id: String,
        tStart: Long,
        selectedCrop: String,
        isPestMode: Boolean,
        state: String,
        district: String,
        reason: String,
        message: String,
        blurVar: Float,
        foliageRatio: Float,
        origPath: String,
        confPct: Float = 0f,
        visionMs: Long = 0L,
        candidates: List<CandidateScore> = emptyList()
    ): DiagnosisResult {
        val totalMs = max(1L, System.currentTimeMillis() - tStart)
        return DiagnosisResult(
            id = id,
            timestampMs = tStart,
            crop = selectedCrop,
            disease = "Rejected by Safety Gate A",
            localizedTitle = "Gate A Safety Halt",
            pathogenScientific = "",
            confidencePct = confPct,
            severityPct = 0f,
            severityStage = "Rejected",
            isPestMode = isPestMode,
            gateAPassed = false,
            gateAReason = reason,
            gateAMessage = message,
            gateBPassed = false,
            isBorderline = false,
            state = state,
            district = district,
            blurVariance = blurVar,
            foliageRatio = foliageRatio,
            leafIsolationPct = 0f,
            healthyPct = 0f,
            chlorosisPct = 0f,
            necrosisPct = 0f,
            topCandidates = candidates,
            guideline = null,
            summaryAdvice = message,
            spokenScript = message,
            originalImagePath = origPath,
            overlayImagePath = origPath,
            inferenceEngine = "On-Device Gate A",
            visionLatencyMs = visionMs,
            totalLatencyMs = totalMs,
            languageCode = "en"
        )
    }
}
