package com.kisandrishti.ai.ml

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import com.kisandrishti.ai.data.AppLanguage
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import java.util.Locale

class VoiceEngine(private val context: Context) {

    private var tts: TextToSpeech? = null
    private var ttsReady = false
    private var recognizer: SpeechRecognizer? = null

    private val _isSpeaking = MutableStateFlow(false)
    val isSpeaking: StateFlow<Boolean> = _isSpeaking

    private val _progress = MutableStateFlow(0f)
    val progress: StateFlow<Float> = _progress

    private val _isListening = MutableStateFlow(false)
    val isListening: StateFlow<Boolean> = _isListening

    init {
        tts = TextToSpeech(context) { status ->
            ttsReady = (status == TextToSpeech.SUCCESS)
            tts?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                override fun onStart(utteranceId: String?) {
                    _isSpeaking.value = true
                    _progress.value = 0.08f
                }

                override fun onDone(utteranceId: String?) {
                    _isSpeaking.value = false
                    _progress.value = 1f
                }

                @Deprecated("Deprecated in Java")
                override fun onError(utteranceId: String?) {
                    _isSpeaking.value = false
                    _progress.value = 0f
                }

                override fun onRangeStart(utteranceId: String?, start: Int, end: Int, frame: Int) {
                    val total = lastSpokenLength.coerceAtLeast(1)
                    _progress.value = (end.toFloat() / total.toFloat()).coerceIn(0.05f, 0.98f)
                }
            })
        }
    }

    private var lastSpokenLength = 1

    fun speak(text: String, lang: AppLanguage, isSlow: Boolean, isMaleVoice: Boolean) {
        if (!ttsReady || text.isBlank()) return
        val engine = tts ?: return
        val locale = Locale.forLanguageTag(lang.localeTag)
        val res = engine.setLanguage(locale)
        if (res == TextToSpeech.LANG_MISSING_DATA || res == TextToSpeech.LANG_NOT_SUPPORTED) {
            engine.setLanguage(Locale("en", "IN"))
        }
        engine.setSpeechRate(if (isSlow) 0.78f else 0.98f)
        engine.setPitch(if (isMaleVoice) 0.85f else 1.05f)
        lastSpokenLength = text.length
        _progress.value = 0.05f
        engine.speak(text, TextToSpeech.QUEUE_FLUSH, null, "kd_utt_${System.currentTimeMillis()}")
    }

    fun stopSpeaking() {
        tts?.stop()
        _isSpeaking.value = false
        _progress.value = 0f
    }

    fun startListening(lang: AppLanguage, onResult: (String) -> Unit, onError: (String) -> Unit) {
        if (!SpeechRecognizer.isRecognitionAvailable(context)) {
            onError("Speech recognition service unavailable on this device. Please type your question.")
            return
        }
        stopListening()
        recognizer = SpeechRecognizer.createSpeechRecognizer(context).apply {
            setRecognitionListener(object : RecognitionListener {
                override fun onReadyForSpeech(params: Bundle?) {
                    _isListening.value = true
                }
                override fun onBeginningOfSpeech() {}
                override fun onRmsChanged(rmsdB: Float) {}
                override fun onBufferReceived(buffer: ByteArray?) {}
                override fun onEndOfSpeech() {
                    _isListening.value = false
                }
                override fun onError(error: Int) {
                    _isListening.value = false
                    onError("Could not hear clearly (code $error). Try again or type below.")
                }
                override fun onResults(results: Bundle?) {
                    _isListening.value = false
                    val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    val best = matches?.firstOrNull().orEmpty().trim()
                    if (best.isNotEmpty()) onResult(best) else onError("No speech detected.")
                }
                override fun onPartialResults(partialResults: Bundle?) {}
                override fun onEvent(eventType: Int, params: Bundle?) {}
            })
        }
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, lang.localeTag)
            putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, true)
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
        }
        recognizer?.startListening(intent)
    }

    fun stopListening() {
        _isListening.value = false
        try {
            recognizer?.stopListening()
            recognizer?.destroy()
        } catch (_: Exception) {}
        recognizer = null
    }

    fun release() {
        stopSpeaking()
        stopListening()
        tts?.shutdown()
        tts = null
    }
}
