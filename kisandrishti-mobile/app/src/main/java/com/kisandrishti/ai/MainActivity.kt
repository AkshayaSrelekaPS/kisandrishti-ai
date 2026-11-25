package com.kisandrishti.ai

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.core.content.ContextCompat
import androidx.lifecycle.viewmodel.compose.viewModel
import com.kisandrishti.ai.data.MainTab
import com.kisandrishti.ai.ui.MainViewModel
import com.kisandrishti.ai.ui.screens.*
import com.kisandrishti.ai.ui.theme.KisanColors
import com.kisandrishti.ai.ui.theme.KisanDrishtiTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            KisanDrishtiTheme {
                KisanDrishtiApp()
            }
        }
    }
}

@Composable
fun KisanDrishtiApp(vm: MainViewModel = viewModel()) {
    val context = LocalContext.current

    val activeTab by vm.activeTab.collectAsState()
    val showCamera by vm.showCameraScreen.collectAsState()
    val showResult by vm.showResultScreen.collectAsState()
    val showEdgeModal by vm.showEdgeModal.collectAsState()

    val language by vm.language.collectAsState()
    val voiceSlow by vm.voiceSlow.collectAsState()
    val voiceMale by vm.voiceMale.collectAsState()
    val selectedTarget by vm.selectedTarget.collectAsState()
    val selectedState by vm.selectedState.collectAsState()
    val selectedDistrict by vm.selectedDistrict.collectAsState()
    val selectedImageLabel by vm.selectedImageLabel.collectAsState()
    val previewBitmap by vm.previewBitmap.collectAsState()
    val isScanning by vm.isScanning.collectAsState()
    val activeDiag by vm.activeDiagnosis.collectAsState()

    val libraryList by vm.libraryList.collectAsState()
    val historyList by vm.historyList.collectAsState()
    val chatMessages by vm.chatMessages.collectAsState()
    val isChatBusy by vm.isChatBusy.collectAsState()
    val piConfig by vm.piConfig.collectAsState()
    val latencyBadge by vm.lastLatencyBadge.collectAsState()
    val storageUsedPct by vm.storageUsedPct.collectAsState()
    val freeGbText by vm.freeGbText.collectAsState()

    val isSpeaking by vm.voiceEngine.isSpeaking.collectAsState()
    val audioProgress by vm.voiceEngine.progress.collectAsState()
    val isListening by vm.voiceEngine.isListening.collectAsState()

    val galleryLauncher = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        if (uri != null) {
            vm.loadImageFromUri(uri)
        }
    }

    val cameraPermissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) vm.showCameraScreen.value = true
    }

    var pendingVoiceCallback by remember { mutableStateOf<(() -> Unit)?>(null) }
    val audioPermissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) pendingVoiceCallback?.invoke()
        pendingVoiceCallback = null
    }

    fun requestCameraOpen() {
        val granted = ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED
        if (granted) vm.showCameraScreen.value = true else cameraPermissionLauncher.launch(Manifest.permission.CAMERA)
    }

    fun requestAudioAction(action: () -> Unit) {
        val granted = ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED
        if (granted) action() else {
            pendingVoiceCallback = action
            audioPermissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
        }
    }

    BackHandler(enabled = showCamera || showResult) {
        if (showCamera) vm.showCameraScreen.value = false
        else if (showResult) vm.showResultScreen.value = false
    }

    if (showCamera) {
        CameraScannerScreen(
            selectedTarget = selectedTarget,
            hardwareLabel = vm.hardwareLabel,
            onBack = { vm.showCameraScreen.value = false },
            onPickGallery = { galleryLauncher.launch("image/*") },
            onCaptured = { bmp -> vm.onCapturedBitmap(bmp, autoRun = true) }
        )
    } else {
        Scaffold(
            containerColor = KisanColors.BgRoot,
            topBar = {
                KisanTopBar(
                    hardwareLabel = vm.hardwareLabel,
                    latencyBadge = latencyBadge,
                    piConfig = piConfig,
                    showBack = showResult && activeTab == MainTab.SCAN,
                    titleOverride = if (showResult && activeTab == MainTab.SCAN) "Diagnosis Result" else null,
                    onBack = { vm.showResultScreen.value = false },
                    onProfileClick = { vm.showEdgeModal.value = true }
                )
            },
            bottomBar = {
                KisanBottomNav(
                    activeTab = activeTab,
                    onSelect = { tab ->
                        vm.activeTab.value = tab
                        if (tab != MainTab.SCAN) vm.showResultScreen.value = false
                    }
                )
            }
        ) { innerPadding ->
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(KisanColors.BgRoot)
                    .padding(innerPadding)
            ) {
                when (activeTab) {
                    MainTab.SCAN -> {
                        if (showResult && activeDiag != null) {
                            DiagnosisResultScreen(
                                diag = activeDiag!!,
                                language = language,
                                isSpeaking = isSpeaking,
                                audioProgress = audioProgress,
                                voiceSlow = voiceSlow,
                                onPlayAudio = { slow -> vm.playDiagnosisAudio(slow) },
                                onStopAudio = { vm.voiceEngine.stopSpeaking() },
                                onToggleVoiceSpeed = vm::toggleVoiceSpeed,
                                onAskFollowUp = {
                                    vm.showResultScreen.value = false
                                    vm.activeTab.value = MainTab.ASK_AI
                                },
                                onShareReport = { vm.shareDiagnosticReport(activeDiag!!) }
                            )
                        } else {
                            ScanHomeScreen(
                                language = language,
                                voiceSlow = voiceSlow,
                                voiceMale = voiceMale,
                                selectedTarget = selectedTarget,
                                selectedState = selectedState,
                                selectedDistrict = selectedDistrict,
                                selectedImageLabel = selectedImageLabel,
                                previewBitmap = previewBitmap,
                                isScanning = isScanning,
                                lastLatency = latencyBadge,
                                onSelectLanguage = vm::setLanguage,
                                onToggleVoiceSpeed = vm::toggleVoiceSpeed,
                                onToggleVoiceGender = vm::toggleVoiceGender,
                                onSelectTarget = vm::selectTarget,
                                onOpenCamera = ::requestCameraOpen,
                                onPickGallery = { galleryLauncher.launch("image/*") },
                                onSelectDemo = vm::loadAssetSample,
                                onSelectLocation = vm::setLocation,
                                onRunDiagnosis = vm::runDiagnosis
                            )
                        }
                    }
                    MainTab.ASK_AI -> AskAiScreen(
                        activeDiag = activeDiag,
                        piConfig = piConfig,
                        messages = chatMessages,
                        isBusy = isChatBusy,
                        isListening = isListening,
                        onAskText = vm::askQuestion,
                        onStartVoice = { errCb ->
                            requestAudioAction {
                                vm.voiceEngine.startListening(
                                    lang = language,
                                    onResult = { vm.askQuestion(it) },
                                    onError = errCb
                                )
                            }
                        },
                        onPlayMessage = { txt -> vm.voiceEngine.speak(txt, language, voiceSlow, voiceMale) }
                    )
                    MainTab.GUIDE -> GuideScreen(
                        items = libraryList,
                        onVoiceSearch = { onResult ->
                            requestAudioAction {
                                vm.voiceEngine.startListening(language, onResult) {}
                            }
                        },
                        onReadAloud = { g ->
                            vm.voiceEngine.speak("${g.crop} ${g.diagnosis.replace('_', ' ')}. ${g.culturalAction} ${g.organicRemedy}", language, voiceSlow, voiceMale)
                        }
                    )
                    MainTab.HISTORY -> HistoryScreen(
                        items = historyList,
                        storageUsedPct = storageUsedPct,
                        freeGbText = freeGbText,
                        onOpenScan = vm::openHistoryScan,
                        onPlayAudio = vm::playHistoryAudio,
                        onClearHistory = vm::clearHistory
                    )
                }
            }
        }
    }

    if (showEdgeModal) {
        EdgeHardwareDialog(
            hardwareLabel = vm.hardwareLabel,
            piConfig = piConfig,
            onDismiss = { vm.showEdgeModal.value = false },
            onSave = vm::updatePiConfig,
            onTestPi = vm::testPiConnection
        )
    }
}
