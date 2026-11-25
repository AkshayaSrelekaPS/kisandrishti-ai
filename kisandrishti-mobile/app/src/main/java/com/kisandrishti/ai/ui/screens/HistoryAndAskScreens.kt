package com.kisandrishti.ai.ui.screens

import android.graphics.BitmapFactory
import androidx.compose.foundation.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.kisandrishti.ai.data.*
import com.kisandrishti.ai.ui.theme.KisanColors
import java.io.File
import java.text.SimpleDateFormat
import java.util.*

@Composable
fun AskAiScreen(
    activeDiag: DiagnosisResult?,
    piConfig: PiEdgeConfig,
    messages: List<ChatMessage>,
    isBusy: Boolean,
    isListening: Boolean,
    onAskText: (String) -> Unit,
    onStartVoice: ((String) -> Unit) -> Unit,
    onPlayMessage: (String) -> Unit
) {
    var inputText by remember { mutableStateOf("") }
    var voiceStatus by remember { mutableStateOf<String?>(null) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 14.dp, vertical = 10.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        // Active Field Context Banner
        Surface(
            color = KisanColors.BgCard,
            shape = RoundedCornerShape(12.dp),
            border = BorderStroke(1.dp, KisanColors.BorderEmerald),
            modifier = Modifier.fillMaxWidth()
        ) {
            Row(modifier = Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.Psychology, contentDescription = null, tint = KisanColors.Mint)
                Spacer(Modifier.width(10.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        if (activeDiag != null) "Context: ${activeDiag.localizedTitle} (${activeDiag.severityStage})"
                        else "No Active Scan Yet — Run Scan First",
                        color = Color.White,
                        fontWeight = FontWeight.Bold,
                        fontSize = 13.sp
                    )
                    Text(
                        if (piConfig.usePiServer) "Connected: Pi 5 ExecuTorch Llama 3.2"
                        else "Standalone Offline Mode (Verified ICAR SQLite QA)",
                        color = KisanColors.Cyan,
                        fontSize = 11.sp
                    )
                }
            }
        }

        // Quick 1-Tap Question Chips
        val presets = listOf(
            "What organic spray can I use?",
            "What should I do today?",
            "When can I harvest (PHI)?",
            "Is this safe for bees?"
        )
        LazyRow(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            items(presets) { p ->
                AssistChip(
                    onClick = { onAskText(p) },
                    label = { Text(p, fontSize = 11.sp, color = KisanColors.TextSoft) }
                )
            }
        }

        // Chat Feed
        LazyColumn(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .clip(RoundedCornerShape(14.dp))
                .background(KisanColors.BgCardDeep)
                .border(1.dp, KisanColors.BorderEmerald, RoundedCornerShape(14.dp))
                .padding(10.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            items(messages) { m ->
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = if (m.isUser) Arrangement.End else Arrangement.Start
                ) {
                    Surface(
                        color = if (m.isUser) Color(0xFF065F46) else KisanColors.BgCardInner,
                        shape = RoundedCornerShape(12.dp),
                        border = BorderStroke(1.dp, if (m.isUser) KisanColors.Emerald else KisanColors.BorderEmerald),
                        modifier = Modifier.widthIn(max = 310.dp)
                    ) {
                        Column(modifier = Modifier.padding(10.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            Text(m.text, color = Color.White, fontSize = 13.sp, lineHeight = 19.sp)
                            if (!m.isUser) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Text(m.meta, color = KisanColors.TextDim, fontSize = 10.sp)
                                    TextButton(
                                        onClick = { onPlayMessage(m.text) },
                                        contentPadding = PaddingValues(horizontal = 6.dp, vertical = 2.dp),
                                        modifier = Modifier.height(26.dp)
                                    ) {
                                        Icon(Icons.Default.VolumeUp, contentDescription = "Play", tint = KisanColors.Mint, modifier = Modifier.size(15.dp))
                                        Spacer(Modifier.width(4.dp))
                                        Text("Play", color = KisanColors.Mint, fontSize = 11.sp)
                                    }
                                }
                            }
                        }
                    }
                }
            }
            if (isBusy) {
                item {
                    Text("Thinking...", color = KisanColors.Cyan, fontSize = 12.sp, modifier = Modifier.padding(6.dp))
                }
            }
        }

        if (voiceStatus != null) {
            Text(voiceStatus!!, color = KisanColors.Amber, fontSize = 11.sp)
        }

        // Bottom Voice + Text Input Bar
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Box(
                modifier = Modifier
                    .size(48.dp)
                    .clip(CircleShape)
                    .background(if (isListening) KisanColors.Red else KisanColors.Emerald)
                    .clickable {
                        voiceStatus = "Listening..."
                        onStartVoice { err -> voiceStatus = err }
                    },
                contentAlignment = Alignment.Center
            ) {
                Icon(Icons.Default.Mic, contentDescription = "Speak", tint = Color(0xFF022C22))
            }

            OutlinedTextField(
                value = inputText,
                onValueChange = { inputText = it },
                placeholder = { Text("Ask in English / தமிழ் / हिन्दी...", fontSize = 13.sp) },
                singleLine = true,
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier.weight(1f)
            )

            IconButton(
                onClick = {
                    val txt = inputText.trim()
                    if (txt.isNotEmpty()) {
                        inputText = ""
                        onAskText(txt)
                    }
                },
                modifier = Modifier
                    .size(48.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .background(KisanColors.Cyan)
            ) {
                Icon(Icons.Default.Send, contentDescription = "Send", tint = Color(0xFF022C22))
            }
        }
    }
}

@Composable
fun HistoryScreen(
    items: List<ScanHistoryEntry>,
    storageUsedPct: Int,
    freeGbText: String,
    onOpenScan: (ScanHistoryEntry) -> Unit,
    onPlayAudio: (ScanHistoryEntry) -> Unit,
    onClearHistory: () -> Unit
) {
    var filter by remember { mutableStateOf("All") }
    val cleanCount = items.count { it.severityStage.equals("Healthy", true) }
    val alertCount = items.size - cleanCount
    val visible = remember(items, filter) {
        when (filter) {
            "Alerts" -> items.filter { !it.severityStage.equals("Healthy", true) }
            "Clean" -> items.filter { it.severityStage.equals("Healthy", true) }
            else -> items
        }
    }
    val fmt = remember { SimpleDateFormat("MMM dd, hh:mm a", Locale.getDefault()) }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 14.dp, vertical = 10.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        item {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text("Farm Scan History", color = Color.White, fontSize = 20.sp, fontWeight = FontWeight.ExtraBold)
                        Text("Saved offline on device • ${items.size} Scans recorded", color = KisanColors.TextDim, fontSize = 11.sp)
                    }
                    OutlinedButton(onClick = onClearHistory, border = BorderStroke(1.dp, KisanColors.BorderEmerald)) {
                        Icon(Icons.Default.DeleteOutline, contentDescription = null, tint = KisanColors.Red, modifier = Modifier.size(16.dp))
                        Spacer(Modifier.width(4.dp))
                        Text("Clear", color = KisanColors.Red, fontSize = 12.sp)
                    }
                }

                // 3 KPI Counters matching Stitch Image 3
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    HistoryKpiTile("TOTAL", "${items.size}", "Scans Logged", KisanColors.TextMain, Modifier.weight(1f))
                    HistoryKpiTile("CLEAN", "$cleanCount", "Healthy", KisanColors.Mint, Modifier.weight(1f))
                    HistoryKpiTile("ALERTS", "$alertCount", "Need Action", KisanColors.Amber, Modifier.weight(1f))
                }

                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    FilterChip(selected = filter == "All", onClick = { filter = "All" }, label = { Text("All (${items.size})", fontSize = 11.sp) })
                    FilterChip(selected = filter == "Alerts", onClick = { filter = "Alerts" }, label = { Text("Active Issues ($alertCount)", fontSize = 11.sp) })
                    FilterChip(selected = filter == "Clean", onClick = { filter = "Clean" }, label = { Text("Healthy ($cleanCount)", fontSize = 11.sp) })
                }
            }
        }

        if (visible.isEmpty()) {
            item {
                Surface(
                    color = KisanColors.BgCard,
                    shape = RoundedCornerShape(14.dp),
                    border = BorderStroke(1.dp, KisanColors.BorderEmerald),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(
                        "No scans recorded yet. Capture or upload a leaf/pest photo from the Scan tab.",
                        color = KisanColors.TextSoft,
                        modifier = Modifier.padding(18.dp),
                        fontSize = 13.sp
                    )
                }
            }
        }

        items(visible) { entry ->
            val thumb = remember(entry.imagePath) {
                if (File(entry.imagePath).exists()) BitmapFactory.decodeFile(entry.imagePath) else null
            }
            val isHealthy = entry.severityStage.equals("Healthy", true)
            Surface(
                color = KisanColors.BgCard,
                shape = RoundedCornerShape(14.dp),
                border = BorderStroke(1.dp, KisanColors.BorderEmerald),
                modifier = Modifier.fillMaxWidth().clickable { onOpenScan(entry) }
            ) {
                Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(fmt.format(Date(entry.timestampMs)), color = KisanColors.TextDim, fontSize = 11.sp)
                        Surface(
                            color = if (isHealthy) Color(0xFF064E3B) else KisanColors.RedBg,
                            shape = RoundedCornerShape(999.dp)
                        ) {
                            Text(
                                if (isHealthy) "✔ Healthy" else "• ${entry.severityPct}% ${entry.severityStage}",
                                color = if (isHealthy) KisanColors.Mint else KisanColors.Red,
                                fontSize = 10.sp,
                                fontWeight = FontWeight.Bold,
                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp)
                            )
                        }
                    }

                    Row(verticalAlignment = Alignment.CenterVertically) {
                        if (thumb != null) {
                            Image(
                                bitmap = thumb.asImageBitmap(),
                                contentDescription = entry.localizedTitle,
                                contentScale = ContentScale.Crop,
                                modifier = Modifier.size(60.dp).clip(RoundedCornerShape(10.dp))
                            )
                            Spacer(Modifier.width(10.dp))
                        }
                        Column(modifier = Modifier.weight(1f)) {
                            Text(entry.localizedTitle, color = Color.White, fontWeight = FontWeight.ExtraBold, fontSize = 15.sp)
                            Text("${entry.confidencePct}% Edge Match • ${entry.totalLatencyMs}ms", color = KisanColors.Mint, fontSize = 11.sp)
                        }
                    }

                    Surface(color = KisanColors.BgCardDeep, shape = RoundedCornerShape(10.dp), modifier = Modifier.fillMaxWidth()) {
                        Text(entry.summaryNote, color = KisanColors.TextSoft, fontSize = 12.sp, modifier = Modifier.padding(10.dp), maxLines = 2)
                    }

                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(
                            onClick = { onOpenScan(entry) },
                            colors = ButtonDefaults.buttonColors(containerColor = KisanColors.Emerald),
                            shape = RoundedCornerShape(10.dp),
                            modifier = Modifier.weight(1f).height(42.dp)
                        ) {
                            Text("View Full Diagnosis", color = Color(0xFF022C22), fontWeight = FontWeight.ExtraBold, fontSize = 13.sp)
                        }
                        IconButton(
                            onClick = { onPlayAudio(entry) },
                            modifier = Modifier
                                .size(42.dp)
                                .clip(RoundedCornerShape(10.dp))
                                .background(KisanColors.BgCardInner)
                        ) {
                            Icon(Icons.Default.VolumeUp, contentDescription = "Play", tint = KisanColors.Mint)
                        }
                    }
                }
            }
        }

        // Device Storage Footer Card matching Stitch Image 3
        item {
            Surface(
                color = KisanColors.BgCard,
                shape = RoundedCornerShape(14.dp),
                border = BorderStroke(1.dp, KisanColors.BorderEmerald),
                modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp)
            ) {
                Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("On-Device Storage", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                        Text(freeGbText, color = KisanColors.Mint, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                    }
                    LinearProgressIndicator(
                        progress = { storageUsedPct / 100f },
                        color = KisanColors.Mint,
                        trackColor = KisanColors.BgCardDeep,
                        modifier = Modifier.fillMaxWidth().height(6.dp).clip(RoundedCornerShape(4.dp))
                    )
                    Text("$storageUsedPct% storage used • All models & SQLite offline", color = KisanColors.TextDim, fontSize = 11.sp)
                }
            }
        }
    }
}

@Composable
private fun HistoryKpiTile(label: String, value: String, sub: String, valueColor: Color, modifier: Modifier) {
    Surface(
        color = KisanColors.BgCard,
        shape = RoundedCornerShape(12.dp),
        border = BorderStroke(1.dp, KisanColors.BorderEmerald),
        modifier = modifier
    ) {
        Column(modifier = Modifier.padding(10.dp)) {
            Text(label, color = KisanColors.TextDim, fontSize = 10.sp, fontWeight = FontWeight.Bold)
            Text(value, color = valueColor, fontSize = 20.sp, fontWeight = FontWeight.Black)
            Text(sub, color = KisanColors.TextDim, fontSize = 10.sp)
        }
    }
}
