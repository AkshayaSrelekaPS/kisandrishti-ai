package com.kisandrishti.ai.ui.screens

import androidx.compose.foundation.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.kisandrishti.ai.data.TreatmentGuideline
import com.kisandrishti.ai.ui.theme.KisanColors

@Composable
fun GuideScreen(
    items: List<TreatmentGuideline>,
    onVoiceSearch: ((String) -> Unit) -> Unit,
    onReadAloud: (TreatmentGuideline) -> Unit
) {
    var query by remember { mutableStateOf("") }
    var selectedFilter by remember { mutableStateOf("All") }
    var activeProtocol by remember { mutableStateOf<TreatmentGuideline?>(null) }

    val filters = listOf("All", "Potato", "Tomato", "Rice", "Corn", "Pest")
    val filtered = remember(items, query, selectedFilter) {
        items.filter { g ->
            val cropOk = selectedFilter == "All" || g.crop.equals(selectedFilter, ignoreCase = true)
            val q = query.trim().lowercase()
            val searchOk = q.isEmpty() ||
                g.diagnosis.lowercase().contains(q) ||
                g.crop.lowercase().contains(q) ||
                g.pathogenScientific.lowercase().contains(q) ||
                g.culturalAction.lowercase().contains(q) ||
                g.chemicalName.lowercase().contains(q)
            cropOk && searchOk
        }
    }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 14.dp, vertical = 10.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        item {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Crop & Pest Diagnostic Library", color = Color.White, fontSize = 20.sp, fontWeight = FontWeight.ExtraBold)
                Text("${items.size} Verified Field Conditions • Offline Knowledge Base", color = KisanColors.TextDim, fontSize = 12.sp)

                OutlinedTextField(
                    value = query,
                    onValueChange = { query = it },
                    placeholder = { Text("Search diseases, symptoms, pests...", fontSize = 13.sp) },
                    leadingIcon = { Icon(Icons.Default.Search, contentDescription = null, tint = KisanColors.Mint) },
                    trailingIcon = {
                        IconButton(onClick = { onVoiceSearch { spoken -> query = spoken } }) {
                            Icon(Icons.Default.Mic, contentDescription = "Voice Search", tint = KisanColors.Mint)
                        }
                    },
                    singleLine = true,
                    shape = RoundedCornerShape(12.dp),
                    modifier = Modifier.fillMaxWidth()
                )

                LazyRow(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    items(filters) { f ->
                        val count = if (f == "All") items.size else items.count { it.crop.equals(f, true) }
                        FilterChip(
                            selected = selectedFilter == f,
                            onClick = { selectedFilter = f },
                            label = { Text("${if (f == "Pest") "Pests" else f} ($count)", fontSize = 12.sp) }
                        )
                    }
                }
            }
        }

        items(filtered) { g ->
            LibraryConditionCard(
                g = g,
                onClick = { activeProtocol = g }
            )
        }

        item {
            Surface(
                color = KisanColors.BgCard,
                shape = RoundedCornerShape(14.dp),
                border = BorderStroke(1.dp, KisanColors.BorderEmerald),
                modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp)
            ) {
                Row(modifier = Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Default.OfflinePin, contentDescription = null, tint = KisanColors.Mint)
                    Spacer(Modifier.width(10.dp))
                    Column {
                        Text("Offline Knowledge Base Ready", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                        Text(
                            "All ${items.size} ICAR / TNAU protocols are stored inside device storage. Zero internet needed in field.",
                            color = KisanColors.TextDim,
                            fontSize = 11.sp
                        )
                    }
                }
            }
        }
    }

    if (activeProtocol != null) {
        val g = activeProtocol!!
        AlertDialog(
            onDismissRequest = { activeProtocol = null },
            containerColor = KisanColors.BgCard,
            titleContentColor = Color.White,
            textContentColor = KisanColors.TextSoft,
            title = {
                Column {
                    Text("${g.crop}: ${formatConditionTitle(g.diagnosis)}", fontWeight = FontWeight.ExtraBold, fontSize = 17.sp)
                    if (g.pathogenScientific.isNotBlank()) {
                        Text(g.pathogenScientific, color = KisanColors.Mint, fontSize = 12.sp, fontStyle = FontStyle.Italic)
                    }
                }
            },
            text = {
                Column(modifier = Modifier.verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Cultural Action:", color = KisanColors.Mint, fontWeight = FontWeight.Bold, fontSize = 12.sp)
                    Text(g.culturalAction, fontSize = 13.sp)
                    Text("Organic Control:", color = KisanColors.Amber, fontWeight = FontWeight.Bold, fontSize = 12.sp)
                    Text(g.organicRemedy, fontSize = 13.sp)
                    Text("Certified Medicine (${g.sourceCitation}):", color = KisanColors.Cyan, fontWeight = FontWeight.Bold, fontSize = 12.sp)
                    Text("${g.chemicalName} @ ${g.chemicalDosage} (PHI: ${g.phiDays} days)", fontSize = 13.sp)
                    if (g.symptomChecklist.isNotEmpty()) {
                        Text("Symptoms Checklist:", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 12.sp)
                        g.symptomChecklist.forEach { Text("• $it", fontSize = 12.sp) }
                    }
                }
            },
            confirmButton = {
                Button(
                    onClick = { onReadAloud(g) },
                    colors = ButtonDefaults.buttonColors(containerColor = KisanColors.Emerald)
                ) {
                    Icon(Icons.Default.VolumeUp, contentDescription = null, tint = Color(0xFF022C22))
                    Spacer(Modifier.width(6.dp))
                    Text("Listen", color = Color(0xFF022C22), fontWeight = FontWeight.Bold)
                }
            },
            dismissButton = {
                TextButton(onClick = { activeProtocol = null }) { Text("Close", color = KisanColors.TextSoft) }
            }
        )
    }
}

@Composable
private fun LibraryConditionCard(g: TreatmentGuideline, onClick: () -> Unit) {
    val isSevere = g.referenceStage.equals("Severe", true)
    Surface(
        color = KisanColors.BgCard,
        shape = RoundedCornerShape(14.dp),
        border = BorderStroke(1.dp, KisanColors.BorderEmerald),
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick)
    ) {
        Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
                Surface(
                    color = if (isSevere) KisanColors.RedBg else KisanColors.AmberBg,
                    shape = RoundedCornerShape(999.dp)
                ) {
                    Text(
                        "${g.crop} • ${g.referenceStage}",
                        color = if (isSevere) KisanColors.Red else Color(0xFFFDE68A),
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp)
                    )
                }
                Surface(color = Color(0xFF064E3B), shape = RoundedCornerShape(999.dp)) {
                    Text(
                        g.sourceCitation,
                        color = KisanColors.Mint,
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp)
                    )
                }
            }

            Text(formatConditionTitle(g.diagnosis), color = Color.White, fontSize = 17.sp, fontWeight = FontWeight.ExtraBold)
            if (g.pathogenScientific.isNotBlank()) {
                Text(g.pathogenScientific, color = KisanColors.Mint, fontSize = 12.sp, fontStyle = FontStyle.Italic)
            }

            if (g.symptomChecklist.isNotEmpty()) {
                Surface(color = KisanColors.BgCardDeep, shape = RoundedCornerShape(10.dp), modifier = Modifier.fillMaxWidth()) {
                    Text(
                        "⚠ Field Clue: ${g.symptomChecklist.first()}",
                        color = KisanColors.TextSoft,
                        fontSize = 12.sp,
                        modifier = Modifier.padding(10.dp)
                    )
                }
            }

            Surface(color = KisanColors.BgCardInner, shape = RoundedCornerShape(10.dp), modifier = Modifier.fillMaxWidth()) {
                Text(
                    "🛡 Quick Remedy: ${g.culturalAction}",
                    color = KisanColors.TextMain,
                    fontSize = 12.sp,
                    modifier = Modifier.padding(10.dp)
                )
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("Rx: ${g.chemicalName}", color = KisanColors.Cyan, fontSize = 11.sp, fontWeight = FontWeight.SemiBold, modifier = Modifier.weight(1f))
                Text("View Full Protocol ›", color = KisanColors.Mint, fontSize = 12.sp, fontWeight = FontWeight.Bold)
            }
        }
    }
}

private fun formatConditionTitle(raw: String): String =
    raw.replace('_', ' ')
        .trim()
        .split(Regex("\\s+"))
        .filter { it.isNotEmpty() }
        .joinToString(" ") { word ->
            word.replaceFirstChar { if (it.isLowerCase()) it.titlecase() else it.toString() }
        }
