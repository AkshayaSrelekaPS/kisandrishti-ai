package com.kisandrishti.ai.data

import org.json.JSONObject
import java.io.BufferedReader
import java.io.DataOutputStream
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL

object PiSyncClient {

    fun testConnection(baseUrl: String): Pair<Boolean, String> {
        return try {
            val clean = baseUrl.trim().trimEnd('/')
            val conn = (URL("$clean/api/telemetry").openConnection() as HttpURLConnection).apply {
                connectTimeout = 3500
                readTimeout = 4000
                requestMethod = "GET"
            }
            if (conn.responseCode == 200) {
                val txt = BufferedReader(InputStreamReader(conn.inputStream)).readText()
                val obj = JSONObject(txt)
                val llm = obj.optString("llm_backend", "ExecuTorch")
                val vision = obj.optString("vision_backend", "ONNXRuntime")
                true to "Connected: $vision + $llm"
            } else {
                false to "HTTP ${conn.responseCode}"
            }
        } catch (e: Exception) {
            false to (e.message ?: "Unreachable")
        }
    }

    fun askPiExecuTorch(
        baseUrl: String,
        question: String,
        lang: AppLanguage,
        diag: DiagnosisResult?
    ): Pair<String, String>? {
        return try {
            val clean = baseUrl.trim().trimEnd('/')
            val boundary = "----KisanDrishtiBoundary${System.currentTimeMillis()}"
            val conn = (URL("$clean/api/voice-qa").openConnection() as HttpURLConnection).apply {
                connectTimeout = 5000
                readTimeout = 30000
                requestMethod = "POST"
                doOutput = true
                setRequestProperty("Content-Type", "multipart/form-data; boundary=$boundary")
            }

            val ctx = JSONObject().apply {
                if (diag != null) {
                    put("crop", diag.crop)
                    put("disease", diag.disease)
                    put("severity_pct", diag.severityPct)
                    put("severity_stage", diag.severityStage)
                    put("gate_b_passed", diag.gateBPassed)
                    put("cultural_action", diag.guideline?.culturalAction ?: "")
                    put("organic_remedy", diag.guideline?.organicRemedy ?: "")
                    put("chemical_name", diag.guideline?.chemicalName ?: "Withheld")
                    put("chemical_dosage", diag.guideline?.chemicalDosage ?: "N/A")
                    put("phi_display", "${diag.guideline?.phiDays ?: 0} days")
                }
            }.toString()

            DataOutputStream(conn.outputStream).use { out ->
                fun field(name: String, value: String) {
                    out.writeBytes("--$boundary\r\n")
                    out.writeBytes("Content-Disposition: form-data; name=\"$name\"\r\n\r\n")
                    out.write(value.toByteArray(Charsets.UTF_8))
                    out.writeBytes("\r\n")
                }
                field("question_text", question)
                field("lang", lang.code)
                field("context_json", ctx)
                out.writeBytes("--$boundary--\r\n")
            }

            if (conn.responseCode != 200) return null
            val body = BufferedReader(InputStreamReader(conn.inputStream)).readText()
            val obj = JSONObject(body)
            val ans = obj.optString("answer", "").trim()
            val lm = obj.optJSONObject("llm_metrics")
            val tokS = lm?.optDouble("tokens_per_sec", 0.0) ?: 0.0
            val backend = lm?.optString("backend", "Pi 5 ExecuTorch") ?: "Pi 5 ExecuTorch"
            if (ans.isNotEmpty()) ans to "$backend • ${String.format("%.1f", tokS)} tok/s" else null
        } catch (_: Exception) {
            null
        }
    }
}
