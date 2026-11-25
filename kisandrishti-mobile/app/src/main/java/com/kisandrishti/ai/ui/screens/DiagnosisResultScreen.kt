package com.kisandrishti.ai.ui.screens

import android.graphics.BitmapFactory
import androidx.compose.foundation.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import com.kisandrishti.ai.data.AppLanguage
import com.kisandrishti.ai.data.DiagnosisResult
import com.kisandrishti.ai.ui.theme.KisanColors
import java.io.File

@Composable
fun DiagnosisResultScreen(
    diag: DiagnosisResult,
    language: AppLanguage,
    isSpeaking: Boolean,
    audioProgress: Float,
    voiceSlow: Boolean,
    onPlayAudio: (Boolean) -> Unit,
    onStopAudio: () -> Unit,
    onToggleVoiceSpeed: () -> Unit,
    onAskFollowUp: () -> Unit,
    onShareReport: () -> Unit
) {
    var showOverlay by remember(diag.id) { mutableStateOf(true) }
    var enlargePhoto by remember { mutableStateOf(false) }

    val origBmp = remember(diag.originalImagePath) {
        if (File(diag.originalImagePath).exists()) BitmapFactory.decodeFile(diag.originalImagePath) else null
    }
    val overBmp = remember(diag.overlayImagePath) {
        if (File(diag.overlayImagePath).exists()) BitmapFactory.decodeFile(diag.overlayImagePath) else null
    }
    val activeBmp = if (showOverlay) (overBmp ?: origBmp) else (origBmp ?: overBmp)

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 14.dp, vertical = 10.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        // Latency & Offline Badge Row (matches Stitch Image 5 top strip)
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Surface(
                color = KisanColors.BgCardInner,
                shape = RoundedCornerShape(999.dp),
                border = BorderStroke(1.dp, KisanColors.BorderEmerald)
            ) {
                Text(
                    "⚡ Edge Inference: ${diag.totalLatencyMs}ms • Offline Ready",
                    color = KisanColors.Mint,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp)
                )
            }
            Text("MobileNetV3 • ONNX", color = KisanColors.TextDim, fontSize = 10.sp)
        }

        // Gate A Rejection View if rejected
        if (!diag.gateAPassed) {
            Surface(
                color = KisanColors.RedBg,
                shape = RoundedCornerShape(14.dp),
                border = BorderStroke(1.5.dp, KisanColors.RedBorder),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Default.Warning, contentDescription = null, tint = KisanColors.Red)
                        Spacer(Modifier.width(8.dp))
                        Text("Gate A Safety Halt (${diag.gateAReason})", color = Color(0xFFFECACA), fontWeight = FontWeight.ExtraBold, fontSize = 16.sp)
                    }
                    Text(diag.gateAMessage, color = Color(0xFFFEE2E2), fontSize = 13.sp, lineHeight = 19.sp)
                    if (origBmp != null) {
                        Image(
                            bitmap = origBmp.asImageBitmap(),
                            contentDescription = "Rejected sample",
                            contentScale = ContentScale.Crop,
                            modifier = Modifier.fillMaxWidth().height(180.dp).clip(RoundedCornerShape(10.dp))
                        )
                    }
                    Text(
                        "Blur Variance: ${String.format("%.1f", diag.blurVariance)} | Foliage: ${String.format("%.1f", diag.foliageRatio * 100f)}%",
                        color = Color(0xFFFCA5A5),
                        fontSize = 11.sp
                    )
                }
            }
            return
        }

        // Detected Condition Header Card
        Surface(
            color = KisanColors.BgCard,
            shape = RoundedCornerShape(14.dp),
            border = BorderStroke(1.dp, KisanColors.BorderEmerald),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("DETECTED CONDITION", color = KisanColors.Mint, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                Text(diag.localizedTitle, color = Color.White, fontSize = 21.sp, fontWeight = FontWeight.ExtraBold)
                if (diag.pathogenScientific.isNotBlank()) {
                    Text(diag.pathogenScientific, color = KisanColors.Mint, fontSize = 12.sp, fontStyle = FontStyle.Italic)
                }
                Text(diag.summaryAdvice, color = KisanColors.TextSoft, fontSize = 13.sp, lineHeight = 18.sp)

                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Surface(color = Color(0xFF064E3B), shape = RoundedCornerShape(8.dp), border = BorderStroke(1.dp, KisanColors.Emerald)) {
                        Text(
                            "✔ ${diag.confidencePct}% Match",
                            color = KisanColors.Mint,
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                        )
                    }
                    if (!diag.isPestMode) {
                        Surface(
                            color = KisanColors.AmberBg,
                            shape = RoundedCornerShape(8.dp),
                            border = BorderStroke(1.dp, KisanColors.AmberBorder)
                        ) {
                            Text(
                                "⚠ ${diag.severityPct}% Leaf Area (${diag.severityStage})",
                                color = Color(0xFFFDE68A),
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                            )
                        }
                    }
                }
            }
        }

        // Photo Compare Card: Original Photo vs Damage Highlight (HSV Mask)
        if (activeBmp != null) {
            Surface(
                color = KisanColors.BgCard,
                shape = RoundedCornerShape(14.dp),
                border = BorderStroke(1.dp, KisanColors.BorderEmerald),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    if (!diag.isPestMode) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clip(RoundedCornerShape(8.dp))
                                .background(KisanColors.BgCardDeep)
                                .padding(3.dp),
                            horizontalArrangement = Arrangement.spacedBy(4.dp)
                        ) {
                            TogglePhotoPill("📷 Original Photo", !showOverlay, Modifier.weight(1f)) { showOverlay = false }
                            TogglePhotoPill("🎯 Damage Highlight", showOverlay, Modifier.weight(1f)) { showOverlay = true }
                        }
                    }
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(210.dp)
                            .clip(RoundedCornerShape(10.dp))
                            .clickable { enlargePhoto = true }
                    ) {
                        Image(
                            bitmap = activeBmp.asImageBitmap(),
                            contentDescription = "Diagnosis specimen",
                            contentScale = ContentScale.Crop,
                            modifier = Modifier.fillMaxSize()
                        )
                        Surface(
                            color = Color.Black.copy(alpha = 0.7f),
                            shape = RoundedCornerShape(6.dp),
                            modifier = Modifier.align(Alignment.BottomEnd).padding(8.dp)
                        ) {
                            Text(
                                if (diag.isPestMode) "Mode 3 Pest Screening"
                                else "Healthy ${diag.healthyPct}% • Necrotic ${diag.necrosisPct}%",
                                color = Color.White,
                                fontSize = 10.sp,
                                modifier = Modifier.padding(horizontal = 7.dp, vertical = 3.dp)
                            )
                        }
                    }
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("🔍 Tap photo to enlarge", color = KisanColors.TextDim, fontSize = 11.sp)
                        Text("Vision ${diag.visionLatencyMs}ms", color = KisanColors.Cyan, fontSize = 11.sp, fontWeight = FontWeight.SemiBold)
                    }
                }
            }
        }

        // Voice Agronomist Playback Card (matches Stitch Image 5)
        Surface(
            color = Color(0xFF073121),
            shape = RoundedCornerShape(14.dp),
            border = BorderStroke(1.dp, KisanColors.Emerald),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.weight(1f)) {
                        Box(
                            modifier = Modifier
                                .size(40.dp)
                                .clip(CircleShape)
                                .background(KisanColors.Mint)
                                .clickable {
                                    if (isSpeaking) onStopAudio() else onPlayAudio(voiceSlow)
                                },
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                if (isSpeaking) Icons.Default.Stop else Icons.Default.VolumeUp,
                                contentDescription = "Listen",
                                tint = Color(0xFF022C22)
                            )
                        }
                        Spacer(Modifier.width(10.dp))
                        Column {
                            Text("VOICE AGRONOMIST", color = KisanColors.Mint, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                            Text(
                                "Listen in ${language.nativeLabel}",
                                color = Color.White,
                                fontSize = 14.sp,
                                fontWeight = FontWeight.ExtraBold
                            )
                        }
                    }
                    Surface(
                        color = KisanColors.BgCardDeep,
                        shape = RoundedCornerShape(8.dp),
                        border = BorderStroke(1.dp, KisanColors.BorderEmerald),
                        modifier = Modifier.clickable(onClick = onToggleVoiceSpeed)
                    ) {
                        Text(
                            if (voiceSlow) "0.8x" else "1.0x",
                            color = KisanColors.Cyan,
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(horizontal = 9.dp, vertical = 5.dp)
                        )
                    }
                }
                LinearProgressIndicator(
                    progress = { audioProgress },
                    color = KisanColors.Mint,
                    trackColor = KisanColors.BgCardDeep,
                    modifier = Modifier.fillMaxWidth().height(5.dp).clip(RoundedCornerShape(4.dp))
                )
            }
        }

        // Gate B Verification Card
        Surface(
            color = if (diag.gateBPassed) KisanColors.BgCardDeep else KisanColors.AmberBg,
            shape = RoundedCornerShape(12.dp),
            border = BorderStroke(1.dp, if (diag.gateBPassed) KisanColors.BorderEmerald else KisanColors.AmberBorder),
            modifier = Modifier.fillMaxWidth()
        ) {
            Row(modifier = Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    if (diag.gateBPassed) Icons.Default.VerifiedUser else Icons.Default.GppMaybe,
                    contentDescription = null,
                    tint = if (diag.gateBPassed) KisanColors.Mint else KisanColors.Amber
                )
                Spacer(Modifier.width(10.dp))
                Text(
                    if (diag.gateBPassed)
                        "ICAR Guardrail Verified: Crop matched (${diag.confidencePct}%) & regional dosage verified for ${diag.state}."
                    else
                        "Gate B Chemical Guardrail: Synthetic sprays held back (confidence <75% or unverified zone). Follow Steps 1–2 safely.",
                    color = KisanColors.TextSoft,
                    fontSize = 12.sp,
                    lineHeight = 17.sp
                )
            }
        }

        // 3-Step Action Plan (matches Stitch Image 5)
        val g = diag.guideline
        if (g != null) {
            Text("Action Plan (3 Steps)", color = Color.White, fontSize = 16.sp, fontWeight = FontWeight.ExtraBold)

            // Step 1
            Surface(
                color = KisanColors.BgCard,
                shape = RoundedCornerShape(14.dp),
                border = BorderStroke(1.dp, KisanColors.BorderEmerald),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("STEP 1 — ZERO COST ACTION TODAY", color = KisanColors.Mint, fontSize = 10.sp, fontWeight = FontWeight.Black)
                        Text("Today", color = KisanColors.TextDim, fontSize = 11.sp)
                    }
                    Text("Physical & Field Sanitation", color = Color.White, fontSize = 15.sp, fontWeight = FontWeight.Bold)
                    Text(g.culturalAction, color = KisanColors.TextSoft, fontSize = 13.sp, lineHeight = 19.sp)
                }
            }

            // Step 2
            Surface(
                color = KisanColors.BgCard,
                shape = RoundedCornerShape(14.dp),
                border = BorderStroke(1.dp, KisanColors.BorderEmerald),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("STEP 2 — SAFE ORGANIC SPRAY", color = KisanColors.Amber, fontSize = 10.sp, fontWeight = FontWeight.Black)
                        Text("Day 1–2", color = KisanColors.TextDim, fontSize = 11.sp)
                    }
                    Text("Biological & Botanical Remedy", color = Color.White, fontSize = 15.sp, fontWeight = FontWeight.Bold)
                    Text(g.organicRemedy, color = KisanColors.TextSoft, fontSize = 13.sp, lineHeight = 19.sp)
                }
            }

            // Step 3 (only if Gate B Passed)
            if (diag.gateBPassed) {
                Surface(
                    color = Color(0xFF042622),
                    shape = RoundedCornerShape(14.dp),
                    border = BorderStroke(1.dp, KisanColors.Teal),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text("STEP 3 — CERTIFIED TREATMENT & DOSAGE", color = KisanColors.Cyan, fontSize = 10.sp, fontWeight = FontWeight.Black)
                            Text(g.sourceCitation, color = KisanColors.Cyan, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                        }
                        Text(g.chemicalName, color = Color.White, fontSize = 16.sp, fontWeight = FontWeight.ExtraBold)
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Surface(color = KisanColors.BgCardDeep, shape = RoundedCornerShape(10.dp), modifier = Modifier.weight(1f)) {
                                Column(modifier = Modifier.padding(10.dp)) {
                                    Text("💧 Per Litre Water", color = KisanColors.Cyan, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                                    Text(g.chemicalDosage, color = Color.White, fontSize = 14.sp, fontWeight = FontWeight.ExtraBold)
                                }
                            }
                            Surface(color = KisanColors.BgCardDeep, shape = RoundedCornerShape(10.dp), modifier = Modifier.weight(1f)) {
                                Column(modifier = Modifier.padding(10.dp)) {
                                    Text("⏳ Safe Harvest Wait", color = KisanColors.Amber, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                                    Text("${g.phiDays} Days (PHI)", color = Color.White, fontSize = 14.sp, fontWeight = FontWeight.ExtraBold)
                                }
                            }
                        }
                        if (g.bioCompatibilityNote.isNotBlank()) {
                            Surface(color = KisanColors.BgCardDeep, shape = RoundedCornerShape(8.dp)) {
                                Column(modifier = Modifier.padding(10.dp)) {
                                    Text("MANDATORY SAFETY GUARDRAIL", color = KisanColors.Amber, fontSize = 10.sp, fontWeight = FontWeight.Black)
                                    Spacer(Modifier.height(2.dp))
                                    Text(g.bioCompatibilityNote, color = KisanColors.TextSoft, fontSize = 12.sp)
                                }
                            }
                        }
                    }
                }
            }

            // Symptoms Checklist if borderline or helpful
            if (g.symptomChecklist.isNotEmpty()) {
                Surface(
                    color = KisanColors.BgCard,
                    shape = RoundedCornerShape(14.dp),
                    border = BorderStroke(1.dp, KisanColors.BorderEmerald),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text("FIELD SYMPTOM VERIFICATION CHECKLIST", color = KisanColors.Mint, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                        g.symptomChecklist.forEach { item ->
                            Text("✔ $item", color = KisanColors.TextSoft, fontSize = 12.sp)
                        }
                    }
                }
            }

            // Recovery Timeline Strip (4 dots matching Stitch Image 5)
            Surface(
                color = KisanColors.BgCard,
                shape = RoundedCornerShape(14.dp),
                border = BorderStroke(1.dp, KisanColors.BorderEmerald),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("📅 Expected Recovery Timeline", color = Color.White, fontSize = 13.sp, fontWeight = FontWeight.Bold)
                        Text("7 to 10 Days", color = KisanColors.Mint, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                    }
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        TimelineStep("Day 0", "Prune", true)
                        TimelineStep("Day 1", "Spray", true)
                        TimelineStep("Day 5", "Re-check", false)
                        TimelineStep("Day ${g.phiDays.coerceAtLeast(1)}", "PHI Safe", false)
                    }
                }
            }
        }

        // Bottom CTAs matching Stitch Image 5
        Button(
            onClick = onAskFollowUp,
            shape = RoundedCornerShape(12.dp),
            colors = ButtonDefaults.buttonColors(containerColor = KisanColors.Emerald),
            modifier = Modifier.fillMaxWidth().height(50.dp)
        ) {
            Icon(Icons.Default.Mic, contentDescription = null, tint = Color(0xFF022C22))
            Spacer(Modifier.width(8.dp))
            Text("Ask Follow-up Question (Voice / Text)", color = Color(0xFF022C22), fontWeight = FontWeight.ExtraBold)
        }

        OutlinedButton(
            onClick = onShareReport,
            shape = RoundedCornerShape(12.dp),
            border = BorderStroke(1.dp, KisanColors.BorderEmerald),
            modifier = Modifier.fillMaxWidth().height(48.dp)
        ) {
            Icon(Icons.Default.Share, contentDescription = null, tint = KisanColors.Mint)
            Spacer(Modifier.width(8.dp))
            Text("Save / Share Offline Diagnostic Report", color = KisanColors.TextMain, fontWeight = FontWeight.Bold)
        }
    }

    if (enlargePhoto && activeBmp != null) {
        Dialog(onDismissRequest = { enlargePhoto = false }) {
            Surface(color = KisanColors.BgCard, shape = RoundedCornerShape(14.dp)) {
                Column(modifier = Modifier.padding(10.dp)) {
                    Image(
                        bitmap = activeBmp.asImageBitmap(),
                        contentDescription = "Zoomed leaf",
                        contentScale = ContentScale.Fit,
                        modifier = Modifier.fillMaxWidth().heightIn(max = 420.dp)
                    )
                    TextButton(onClick = { enlargePhoto = false }, modifier = Modifier.align(Alignment.End)) {
                        Text("Close", color = KisanColors.Mint)
                    }
                }
            }
        }
    }
}

@Composable
private fun TogglePhotoPill(label: String, selected: Boolean, modifier: Modifier, onClick: () -> Unit) {
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(6.dp))
            .background(if (selected) KisanColors.Emerald else Color.Transparent)
            .clickable(onClick = onClick)
            .padding(vertical = 7.dp),
        contentAlignment = Alignment.Center
    ) {
        Text(
            label,
            color = if (selected) Color(0xFF022C22) else KisanColors.TextSoft,
            fontSize = 12.sp,
            fontWeight = FontWeight.Bold
        )
    }
}

@Composable
private fun TimelineStep(day: String, label: String, active: Boolean) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Box(
            modifier = Modifier
                .size(14.dp)
                .clip(CircleShape)
                .background(if (active) KisanColors.Mint else KisanColors.BgCardInner)
                .border(2.dp, KisanColors.Emerald, CircleShape)
        )
        Spacer(Modifier.height(4.dp))
        Text(day, color = KisanColors.TextMain, fontSize = 10.sp, fontWeight = FontWeight.Bold)
        Text(label, color = KisanColors.TextDim, fontSize = 10.sp)
    }
}
