package com.kisandrishti.ai.ui.screens

import android.graphics.Bitmap
import androidx.compose.foundation.*
import androidx.compose.foundation.layout.*
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
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.kisandrishti.ai.data.*
import com.kisandrishti.ai.ui.theme.KisanColors

@Composable
fun ScanHomeScreen(
    language: AppLanguage,
    voiceSlow: Boolean,
    voiceMale: Boolean,
    selectedTarget: InspectionTarget,
    selectedState: String,
    selectedDistrict: String,
    selectedImageLabel: String,
    previewBitmap: Bitmap?,
    isScanning: Boolean,
    lastLatency: String,
    onSelectLanguage: (AppLanguage) -> Unit,
    onToggleVoiceSpeed: () -> Unit,
    onToggleVoiceGender: () -> Unit,
    onSelectTarget: (InspectionTarget) -> Unit,
    onOpenCamera: () -> Unit,
    onPickGallery: () -> Unit,
    onSelectDemo: (DemoSample) -> Unit,
    onSelectLocation: (String, String) -> Unit,
    onRunDiagnosis: () -> Unit
) {
    var locationExpanded by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 14.dp, vertical = 10.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        // Segmented Trilingual Switcher (matches Stitch Image 4)
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(10.dp))
                .background(KisanColors.BgCardDeep)
                .border(1.dp, KisanColors.BorderEmerald, RoundedCornerShape(10.dp))
                .padding(4.dp),
            horizontalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            AppLanguage.entries.forEach { lang ->
                val active = language == lang
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .clip(RoundedCornerShape(8.dp))
                        .background(if (active) KisanColors.Emerald else Color.Transparent)
                        .clickable { onSelectLanguage(lang) }
                        .padding(vertical = 8.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = if (active) "${lang.nativeLabel} ✓" else lang.nativeLabel,
                        color = if (active) Color(0xFF022C22) else KisanColors.TextSoft,
                        fontSize = 13.sp,
                        fontWeight = if (active) FontWeight.ExtraBold else FontWeight.SemiBold
                    )
                }
            }
        }

        // Voice Guide Bar
        Surface(
            color = KisanColors.BgCard,
            shape = RoundedCornerShape(12.dp),
            border = BorderStroke(1.dp, KisanColors.BorderEmerald)
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 12.dp, vertical = 9.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(30.dp)
                            .clip(CircleShape)
                            .background(KisanColors.BgCardInner),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(Icons.Default.VolumeUp, contentDescription = null, tint = KisanColors.Mint, modifier = Modifier.size(17.dp))
                    }
                    Spacer(Modifier.width(8.dp))
                    Column {
                        Text("Voice Guide", color = KisanColors.TextMain, fontSize = 13.sp, fontWeight = FontWeight.Bold)
                        Text("ஆடியோ வழிகாட்டி • आवाज़ सहायता", color = KisanColors.TextDim, fontSize = 10.sp)
                    }
                }
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    SmallToggleChip(
                        label = if (voiceSlow) "🐢 Slow" else "⚡ Normal",
                        onClick = onToggleVoiceSpeed
                    )
                    SmallToggleChip(
                        label = if (voiceMale) "👨 Male" else "👩 Female",
                        onClick = onToggleVoiceGender
                    )
                }
            }
        }

        // Step 1: Select Inspection Target
        StepSectionHeader(num = "1", title = "Select Inspection Target", sub = "Choose crop or pest to inspect / பயிர் தேர்வு")

        val cropTargets = listOf(InspectionTarget.POTATO, InspectionTarget.TOMATO, InspectionTarget.RICE, InspectionTarget.CORN)
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            for (row in cropTargets.chunked(2)) {
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    row.forEach { target ->
                        CropGridTile(
                            target = target,
                            selected = selectedTarget == target,
                            modifier = Modifier.weight(1f),
                            onClick = { onSelectTarget(target) }
                        )
                    }
                }
            }
        }

        // Mode 3: Check Insect Pest Card
        val pestSelected = selectedTarget == InspectionTarget.PEST
        Surface(
            color = if (pestSelected) Color(0xFF4C2D05) else KisanColors.AmberBg.copy(alpha = 0.65f),
            shape = RoundedCornerShape(14.dp),
            border = BorderStroke(if (pestSelected) 2.dp else 1.dp, if (pestSelected) KisanColors.Amber else KisanColors.AmberBorder),
            modifier = Modifier
                .fillMaxWidth()
                .clickable { onSelectTarget(InspectionTarget.PEST) }
        ) {
            Row(
                modifier = Modifier.padding(12.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .size(44.dp)
                        .clip(RoundedCornerShape(11.dp))
                        .background(KisanColors.Amber),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(Icons.Default.BugReport, contentDescription = null, tint = Color(0xFF271300), modifier = Modifier.size(26.dp))
                }
                Spacer(Modifier.width(12.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("Check Insect Pest", color = KisanColors.TextMain, fontWeight = FontWeight.ExtraBold, fontSize = 15.sp)
                        Spacer(Modifier.width(6.dp))
                        Surface(color = KisanColors.Amber, shape = RoundedCornerShape(4.dp)) {
                            Text(
                                "MODE 3",
                                color = Color(0xFF271300),
                                fontSize = 9.sp,
                                fontWeight = FontWeight.Black,
                                modifier = Modifier.padding(horizontal = 5.dp, vertical = 1.dp)
                            )
                        }
                    }
                    Text(InspectionTarget.PEST.localLine, color = Color(0xFFFDE68A), fontSize = 11.sp)
                    Text(InspectionTarget.PEST.subtitle, color = KisanColors.TextSoft.copy(alpha = 0.8f), fontSize = 11.sp)
                }
                if (pestSelected) {
                    Icon(Icons.Default.CheckCircle, contentDescription = null, tint = KisanColors.Amber)
                }
            }
        }

        // Step 2: Capture or Select Image (Camera + Upload Gallery)
        StepSectionHeader(num = "2", title = "Capture or Select Photo", sub = "Take a live photo or upload leaf/pest image")

        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            // Take Photo (CameraX)
            Surface(
                color = Color(0xFF10B981),
                shape = RoundedCornerShape(14.dp),
                modifier = Modifier
                    .weight(1f)
                    .heightIn(min = 104.dp)
                    .clickable(onClick = onOpenCamera)
            ) {
                Column(
                    modifier = Modifier.fillMaxWidth().padding(vertical = 14.dp, horizontal = 10.dp),
                    verticalArrangement = Arrangement.Center,
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Icon(Icons.Default.PhotoCamera, contentDescription = null, tint = Color(0xFF022C22), modifier = Modifier.size(28.dp))
                    Spacer(Modifier.height(4.dp))
                    Text("Take Photo", color = Color(0xFF022C22), fontWeight = FontWeight.ExtraBold, fontSize = 14.sp)
                    Text("Live Camera", color = Color(0xFF064E3B), fontSize = 10.sp, fontWeight = FontWeight.SemiBold)
                }
            }

            // Pick Image (Gallery Upload)
            Surface(
                color = KisanColors.BgCard,
                shape = RoundedCornerShape(14.dp),
                border = BorderStroke(1.dp, KisanColors.BorderEmerald),
                modifier = Modifier
                    .weight(1f)
                    .heightIn(min = 104.dp)
                    .clickable(onClick = onPickGallery)
            ) {
                Column(
                    modifier = Modifier.fillMaxWidth().padding(vertical = 14.dp, horizontal = 10.dp),
                    verticalArrangement = Arrangement.Center,
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Icon(Icons.Default.PhotoLibrary, contentDescription = null, tint = KisanColors.Cyan, modifier = Modifier.size(28.dp))
                    Spacer(Modifier.height(4.dp))
                    Text("Upload Image", color = KisanColors.TextMain, fontWeight = FontWeight.ExtraBold, fontSize = 14.sp)
                    Text("Phone Gallery", color = KisanColors.TextDim, fontSize = 10.sp)
                }
            }
        }

        // Active Photo Thumbnail Preview
        if (previewBitmap != null) {
            Surface(
                color = KisanColors.BgCardDeep,
                shape = RoundedCornerShape(12.dp),
                border = BorderStroke(1.dp, KisanColors.BorderEmerald)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Image(
                        bitmap = previewBitmap.asImageBitmap(),
                        contentDescription = "Selected photo",
                        contentScale = ContentScale.Crop,
                        modifier = Modifier.size(54.dp).clip(RoundedCornerShape(8.dp))
                    )
                    Spacer(Modifier.width(10.dp))
                    Column(modifier = Modifier.weight(1f)) {
                        Text("Selected Specimen", color = KisanColors.TextDim, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                        Text(selectedImageLabel, color = KisanColors.TextMain, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
                        Text("Target Guard: ${selectedTarget.titleEn}", color = KisanColors.Mint, fontSize = 11.sp)
                    }
                }
            }
        }

        // Instant Demo Samples Strip
        Text(
            "INSTANT DEMO SAMPLES (நேரடி சோதனை)",
            color = KisanColors.TextDim,
            fontSize = 10.sp,
            fontWeight = FontWeight.Bold
        )
        LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            items(DemoSamplesCatalog.samples) { sample ->
                Surface(
                    color = KisanColors.BgCard,
                    shape = RoundedCornerShape(999.dp),
                    border = BorderStroke(1.dp, KisanColors.BorderEmerald),
                    modifier = Modifier.clickable { onSelectDemo(sample) }
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 7.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Box(
                            modifier = Modifier
                                .size(7.dp)
                                .clip(CircleShape)
                                .background(if (sample.target.isPest) KisanColors.Amber else KisanColors.Mint)
                        )
                        Spacer(Modifier.width(6.dp))
                        Text("Sample: ${sample.chipLabel}", color = KisanColors.TextSoft, fontSize = 11.sp, fontWeight = FontWeight.SemiBold)
                    }
                }
            }
        }

        // Location & Gate B Baseline Selector
        Surface(
            color = KisanColors.BgCard,
            shape = RoundedCornerShape(12.dp),
            border = BorderStroke(1.dp, KisanColors.BorderEmerald),
            modifier = Modifier.fillMaxWidth().clickable { locationExpanded = !locationExpanded }
        ) {
            Column(modifier = Modifier.padding(12.dp)) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Default.LocationOn, contentDescription = null, tint = KisanColors.Mint, modifier = Modifier.size(18.dp))
                        Spacer(Modifier.width(8.dp))
                        Column {
                            Text("My Location & Safety Baseline", color = KisanColors.TextMain, fontSize = 13.sp, fontWeight = FontWeight.Bold)
                            Text("$selectedState ($selectedDistrict) • ICAR / TNAU", color = KisanColors.TextDim, fontSize = 11.sp)
                        }
                    }
                    Icon(
                        if (locationExpanded) Icons.Default.ExpandLess else Icons.Default.ExpandMore,
                        contentDescription = null,
                        tint = KisanColors.TextSoft
                    )
                }

                if (locationExpanded) {
                    Spacer(Modifier.height(10.dp))
                    Text("State (Gate B Zone Check)", color = KisanColors.TextDim, fontSize = 11.sp)
                    LazyRow(horizontalArrangement = Arrangement.spacedBy(6.dp), modifier = Modifier.padding(vertical = 4.dp)) {
                        items(VerifiedRegions.states.keys.toList()) { st ->
                            FilterChip(
                                selected = selectedState == st,
                                onClick = {
                                    val firstDist = VerifiedRegions.states[st]?.firstOrNull() ?: "All Districts"
                                    onSelectLocation(st, firstDist)
                                },
                                label = { Text(st, fontSize = 11.sp) }
                            )
                        }
                    }
                    val dists = VerifiedRegions.states[selectedState] ?: listOf("All Districts")
                    Text("District", color = KisanColors.TextDim, fontSize = 11.sp)
                    LazyRow(horizontalArrangement = Arrangement.spacedBy(6.dp), modifier = Modifier.padding(top = 4.dp)) {
                        items(dists) { dist ->
                            FilterChip(
                                selected = selectedDistrict == dist,
                                onClick = { onSelectLocation(selectedState, dist) },
                                label = { Text(dist, fontSize = 11.sp) }
                            )
                        }
                    }
                }
            }
        }

        // Primary Action CTA
        Button(
            onClick = onRunDiagnosis,
            enabled = previewBitmap != null && !isScanning,
            shape = RoundedCornerShape(14.dp),
            colors = ButtonDefaults.buttonColors(containerColor = Color.Transparent),
            contentPadding = PaddingValues(0.dp),
            modifier = Modifier.fillMaxWidth().height(56.dp)
        ) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(
                        Brush.horizontalGradient(listOf(Color(0xFF10B981), Color(0xFF0891B2))),
                        RoundedCornerShape(14.dp)
                    ),
                contentAlignment = Alignment.Center
            ) {
                if (isScanning) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        CircularProgressIndicator(color = Color(0xFF022C22), strokeWidth = 2.5.dp, modifier = Modifier.size(20.dp))
                        Spacer(Modifier.width(10.dp))
                        Text("Analyzing On-Device...", color = Color(0xFF022C22), fontWeight = FontWeight.ExtraBold, fontSize = 15.sp)
                    }
                } else {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Default.Search, contentDescription = null, tint = Color(0xFF022C22))
                        Spacer(Modifier.width(8.dp))
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Text("Check Plant Health Now", color = Color(0xFF022C22), fontWeight = FontWeight.Black, fontSize = 15.sp)
                            Text("சரிபார்க்கவும் • फसल स्वास्थ्य जांचें", color = Color(0xFF064E3B), fontSize = 10.sp, fontWeight = FontWeight.Bold)
                        }
                        Spacer(Modifier.width(8.dp))
                        Icon(Icons.Default.ArrowForward, contentDescription = null, tint = Color(0xFF022C22))
                    }
                }
            }
        }

        Text(
            text = "⚡ $lastLatency On-Device • Local ONNX Quantized MobileNetV3 + Gate A/B",
            color = KisanColors.TextDim,
            fontSize = 11.sp,
            modifier = Modifier.align(Alignment.CenterHorizontally).padding(bottom = 8.dp)
        )
    }
}

@Composable
private fun StepSectionHeader(num: String, title: String, sub: String) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Box(
            modifier = Modifier
                .size(22.dp)
                .clip(CircleShape)
                .background(KisanColors.Emerald),
            contentAlignment = Alignment.Center
        ) {
            Text(num, color = Color(0xFF022C22), fontSize = 12.sp, fontWeight = FontWeight.Black)
        }
        Spacer(Modifier.width(8.dp))
        Column {
            Text(title, color = KisanColors.TextMain, fontSize = 14.sp, fontWeight = FontWeight.ExtraBold)
            Text(sub, color = KisanColors.TextDim, fontSize = 11.sp)
        }
    }
}

@Composable
private fun SmallToggleChip(label: String, onClick: () -> Unit) {
    Surface(
        color = KisanColors.BgCardInner,
        shape = RoundedCornerShape(8.dp),
        border = BorderStroke(1.dp, KisanColors.BorderEmerald),
        modifier = Modifier.clickable(onClick = onClick)
    ) {
        Text(
            text = label,
            color = KisanColors.Mint,
            fontSize = 11.sp,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(horizontal = 9.dp, vertical = 5.dp)
        )
    }
}

@Composable
private fun CropGridTile(
    target: InspectionTarget,
    selected: Boolean,
    modifier: Modifier = Modifier,
    onClick: () -> Unit
) {
    val emoji = when (target) {
        InspectionTarget.POTATO -> "🥔"
        InspectionTarget.TOMATO -> "🍅"
        InspectionTarget.RICE -> "🌾"
        InspectionTarget.CORN -> "🌽"
        else -> "🌿"
    }
    Surface(
        color = if (selected) KisanColors.BgCardInner else KisanColors.BgCard,
        shape = RoundedCornerShape(14.dp),
        border = BorderStroke(if (selected) 2.dp else 1.dp, if (selected) KisanColors.Mint else KisanColors.BorderEmerald),
        modifier = modifier.clickable(onClick = onClick)
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .size(34.dp)
                        .clip(RoundedCornerShape(9.dp))
                        .background(KisanColors.BgCardDeep),
                    contentAlignment = Alignment.Center
                ) {
                    Text(emoji, fontSize = 18.sp)
                }
                if (selected) {
                    Icon(Icons.Default.CheckCircle, contentDescription = null, tint = KisanColors.Mint, modifier = Modifier.size(18.dp))
                }
            }
            Spacer(Modifier.height(8.dp))
            Text(target.titleEn, color = KisanColors.TextMain, fontWeight = FontWeight.ExtraBold, fontSize = 15.sp)
            Text(target.localLine, color = KisanColors.Mint, fontSize = 11.sp)
            Text(target.subtitle, color = KisanColors.TextDim, fontSize = 10.sp)
        }
    }
}
