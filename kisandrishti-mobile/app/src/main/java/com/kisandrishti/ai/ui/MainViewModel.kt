package com.kisandrishti.ai.ui

import android.app.Application
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.net.Uri
import android.os.Build
import android.os.StatFs
import androidx.core.content.FileProvider
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.kisandrishti.ai.data.*
import com.kisandrishti.ai.ml.VisionEngine
import com.kisandrishti.ai.ml.VoiceEngine
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File

class MainViewModel(application: Application) : AndroidViewModel(application) {

    private val ctx = application.applicationContext
    private val repo = KnowledgeRepository(ctx)
    private val visionEngine = VisionEngine(ctx, repo)
    val voiceEngine = VoiceEngine(ctx)

    val activeTab = MutableStateFlow(MainTab.SCAN)
    val showCameraScreen = MutableStateFlow(false)
    val showResultScreen = MutableStateFlow(false)
    val showEdgeModal = MutableStateFlow(false)

    val language = MutableStateFlow(AppLanguage.EN)
    val voiceSlow = MutableStateFlow(false)
    val voiceMale = MutableStateFlow(false)

    val selectedTarget = MutableStateFlow(InspectionTarget.POTATO)
    val selectedState = MutableStateFlow("Tamil Nadu")
    val selectedDistrict = MutableStateFlow("Coimbatore")

    val selectedImageLabel = MutableStateFlow("Sample: Potato Late Blight")
    val previewBitmap = MutableStateFlow<Bitmap?>(null)
    val isScanning = MutableStateFlow(false)
    val activeDiagnosis = MutableStateFlow<DiagnosisResult?>(null)

    val libraryList = MutableStateFlow<List<TreatmentGuideline>>(emptyList())
    val historyList = MutableStateFlow<List<ScanHistoryEntry>>(emptyList())
    val chatMessages = MutableStateFlow<List<ChatMessage>>(emptyList())
    val isChatBusy = MutableStateFlow(false)

    val piConfig = MutableStateFlow(repo.loadPiConfig())
    val lastLatencyBadge = MutableStateFlow("Ready")
    val hardwareLabel: String = "${Build.MANUFACTURER.replaceFirstChar { it.uppercase() }} ${Build.MODEL}"

    val storageUsedPct = MutableStateFlow(12)
    val freeGbText = MutableStateFlow("4.2 GB free")

    init {
        loadAssetSample(DemoSamplesCatalog.samples.first())
        refreshLibrary()
        historyList.value = repo.loadHistory()
        refreshStorageInfo()
        chatMessages.value = listOf(
            ChatMessage(
                id = "welcome",
                isUser = false,
                text = "Hello! I am KisanDrishti AI. Scan a leaf or insect photo, or ask me any farming question offline in English, Tamil, or Hindi.",
                meta = "ICAR/TNAU Guardrail Engine"
            )
        )
    }

    private fun refreshStorageInfo() {
        try {
            val stat = StatFs(ctx.filesDir.absolutePath)
            val total = stat.totalBytes.coerceAtLeast(1L)
            val avail = stat.availableBytes
            val pct = (((total - avail).toDouble() / total.toDouble()) * 100.0).toInt().coerceIn(1, 99)
            val freeGb = avail.toDouble() / (1024.0 * 1024.0 * 1024.0)
            storageUsedPct.value = pct
            freeGbText.value = String.format("%.1f GB free", freeGb)
        } catch (_: Exception) {}
    }

    fun setLanguage(lang: AppLanguage) {
        language.value = lang
        refreshLibrary()
        val cur = activeDiagnosis.value
        if (cur != null && cur.gateAPassed) {
            val updated = repo.getTreatment(if (cur.isPestMode) "Pest" else cur.crop, cur.disease, lang, cur.state)
            if (updated != null) {
                val summary = "${updated.culturalAction} ${updated.organicRemedy}".trim()
                activeDiagnosis.value = cur.copy(
                    guideline = updated,
                    summaryAdvice = summary,
                    spokenScript = "${cur.localizedTitle}. $summary",
                    languageCode = lang.code
                )
            }
        }
    }

    fun toggleVoiceSpeed() {
        voiceSlow.value = !voiceSlow.value
    }

    fun toggleVoiceGender() {
        voiceMale.value = !voiceMale.value
    }

    fun selectTarget(target: InspectionTarget) {
        selectedTarget.value = target
    }

    fun setLocation(state: String, district: String) {
        selectedState.value = state
        selectedDistrict.value = district
    }

    fun loadAssetSample(sample: DemoSample) {
        selectedTarget.value = sample.target
        selectedImageLabel.value = "Sample: ${sample.fullTitle}"
        viewModelScope.launch(Dispatchers.IO) {
            val bmp = ctx.assets.open(sample.assetPath).use { BitmapFactory.decodeStream(it) }
            previewBitmap.value = bmp
        }
    }

    fun loadImageFromUri(uri: Uri) {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val bmp = ctx.contentResolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it) }
                if (bmp != null) {
                    val scaled = scaleDownIfNeeded(bmp, 1024)
                    previewBitmap.value = scaled
                    selectedImageLabel.value = "Gallery Photo Ready"
                }
            } catch (_: Exception) {}
        }
    }

    fun onCapturedBitmap(bitmap: Bitmap, autoRun: Boolean = true) {
        val scaled = scaleDownIfNeeded(bitmap, 1024)
        previewBitmap.value = scaled
        selectedImageLabel.value = "Camera Capture Ready"
        showCameraScreen.value = false
        if (autoRun) {
            runDiagnosis()
        }
    }

    private fun scaleDownIfNeeded(bmp: Bitmap, maxDim: Int): Bitmap {
        val w = bmp.width
        val h = bmp.height
        if (w <= maxDim && h <= maxDim) return bmp
        val ratio = maxDim.toFloat() / maxOf(w, h).toFloat()
        val m = Matrix().apply { postScale(ratio, ratio) }
        return Bitmap.createBitmap(bmp, 0, 0, w, h, m, true)
    }

    fun runDiagnosis() {
        val bmp = previewBitmap.value ?: return
        val target = selectedTarget.value
        val lang = language.value
        val state = selectedState.value
        val district = selectedDistrict.value

        isScanning.value = true
        viewModelScope.launch(Dispatchers.IO) {
            val res = visionEngine.diagnose(
                bitmap = bmp,
                selectedCrop = target.cropKey,
                isPestMode = target.isPest,
                lang = lang,
                state = state,
                district = district
            )
            activeDiagnosis.value = res
            lastLatencyBadge.value = "${res.totalLatencyMs}ms"
            if (res.gateAPassed) {
                historyList.value = repo.saveScan(res)
                refreshStorageInfo()
            }
            withContext(Dispatchers.Main) {
                isScanning.value = false
                showResultScreen.value = true
            }
        }
    }

    fun playDiagnosisAudio(overrideSlow: Boolean? = null) {
        val diag = activeDiagnosis.value ?: return
        val slow = overrideSlow ?: voiceSlow.value
        voiceEngine.speak(diag.spokenScript, language.value, slow, voiceMale.value)
    }

    fun playHistoryAudio(entry: ScanHistoryEntry) {
        val restored = repo.restoreDiagnosis(entry, language.value) ?: return
        voiceEngine.speak(restored.spokenScript, language.value, voiceSlow.value, voiceMale.value)
    }

    fun openHistoryScan(entry: ScanHistoryEntry) {
        val restored = repo.restoreDiagnosis(entry, language.value) ?: return
        activeDiagnosis.value = restored
        lastLatencyBadge.value = "${restored.totalLatencyMs}ms"
        showResultScreen.value = true
        activeTab.value = MainTab.SCAN
    }

    fun clearHistory() {
        historyList.value = repo.clearHistory()
        refreshStorageInfo()
    }

    fun refreshLibrary() {
        viewModelScope.launch(Dispatchers.IO) {
            libraryList.value = repo.listAllGuidelines(language.value)
        }
    }

    fun askQuestion(question: String) {
        val q = question.trim()
        if (q.isEmpty()) return
        val userMsg = ChatMessage("u_${System.currentTimeMillis()}", true, q)
        chatMessages.value = chatMessages.value + userMsg
        isChatBusy.value = true

        val diag = activeDiagnosis.value
        val lang = language.value
        val cfg = piConfig.value

        viewModelScope.launch(Dispatchers.IO) {
            val t0 = System.currentTimeMillis()
            val piReply = if (cfg.usePiServer && cfg.piBaseUrl.isNotBlank()) {
                PiSyncClient.askPiExecuTorch(cfg.piBaseUrl, q, lang, diag)
            } else null

            val answerText: String
            val metaText: String
            if (piReply != null) {
                answerText = piReply.first
                metaText = piReply.second
            } else {
                answerText = repo.answerFollowUpOffline(q, diag, lang)
                val dt = (System.currentTimeMillis() - t0).coerceAtLeast(1L)
                metaText = "Offline ICAR Knowledge Engine • ${dt}ms"
            }

            val botMsg = ChatMessage("b_${System.currentTimeMillis()}", false, answerText, metaText)
            chatMessages.value = chatMessages.value + botMsg
            isChatBusy.value = false
        }
    }

    fun startVoiceQuestion(onStatusError: (String) -> Unit) {
        voiceEngine.startListening(
            lang = language.value,
            onResult = { transcript -> askQuestion(transcript) },
            onError = onStatusError
        )
    }

    fun updatePiConfig(usePi: Boolean, url: String) {
        val updated = piConfig.value.copy(usePiServer = usePi, piBaseUrl = url)
        piConfig.value = updated
        repo.savePiConfig(updated)
    }

    fun testPiConnection(url: String, onDone: (Boolean, String) -> Unit) {
        viewModelScope.launch(Dispatchers.IO) {
            val (ok, msg) = PiSyncClient.testConnection(url)
            val updated = piConfig.value.copy(usePiServer = ok, piBaseUrl = url, lastStatusText = msg)
            piConfig.value = updated
            repo.savePiConfig(updated)
            withContext(Dispatchers.Main) { onDone(ok, msg) }
        }
    }

    fun shareDiagnosticReport(diag: DiagnosisResult) {
        val g = diag.guideline
        val textReport = buildString {
            appendLine("=== KISANDRISHTI AI — DIAGNOSTIC REPORT ===")
            appendLine("Crop: ${diag.crop}")
            appendLine("Detected Condition: ${diag.disease}")
            if (diag.pathogenScientific.isNotBlank()) appendLine("Pathogen / Taxon: ${diag.pathogenScientific}")
            appendLine("Confidence: ${diag.confidencePct}% | Leaf Severity: ${diag.severityPct}% (${diag.severityStage})")
            appendLine("Region: ${diag.state} / ${diag.district}")
            appendLine("Safety Gate A: ${if (diag.gateAPassed) "PASSED" else diag.gateAReason}")
            appendLine("Safety Gate B: ${if (diag.gateBPassed) "AUTHORIZED" else "CHEMICALS SUPPRESSED"}")
            if (g != null) {
                appendLine()
                appendLine("1. Immediate Cultural Action:")
                appendLine("   ${g.culturalAction}")
                appendLine("2. Organic Remedy:")
                appendLine("   ${g.organicRemedy}")
                if (diag.gateBPassed) {
                    appendLine("3. Regulatory Compound (${g.sourceCitation}):")
                    appendLine("   ${g.chemicalName} @ ${g.chemicalDosage} | PHI: ${g.phiDays} days")
                    if (g.bioCompatibilityNote.isNotBlank()) appendLine("   Safety Note: ${g.bioCompatibilityNote}")
                }
            }
            appendLine()
            appendLine("Inference Engine: ${diag.inferenceEngine} (${diag.totalLatencyMs}ms)")
        }

        val intent = Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_SUBJECT, "KisanDrishti AI Report: ${diag.localizedTitle}")
            putExtra(Intent.EXTRA_TEXT, textReport)
            val file = File(diag.overlayImagePath)
            if (file.exists()) {
                val uri = FileProvider.getUriForFile(ctx, "${ctx.packageName}.fileprovider", file)
                putExtra(Intent.EXTRA_STREAM, uri)
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        ctx.startActivity(Intent.createChooser(intent, "Share / Save Diagnostic Report").apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        })
    }

    override fun onCleared() {
        voiceEngine.release()
        super.onCleared()
    }
}
