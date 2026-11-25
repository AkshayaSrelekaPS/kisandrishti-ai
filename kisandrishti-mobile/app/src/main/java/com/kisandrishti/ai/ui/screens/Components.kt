package com.kisandrishti.ai.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.kisandrishti.ai.data.MainTab
import com.kisandrishti.ai.data.PiEdgeConfig
import com.kisandrishti.ai.ui.theme.KisanColors

@Composable
fun KisanTopBar(
    hardwareLabel: String,
    latencyBadge: String,
    piConfig: PiEdgeConfig,
    showBack: Boolean = false,
    titleOverride: String? = null,
    onBack: () -> Unit = {},
    onProfileClick: () -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(KisanColors.BgHeader)
            .statusBarsPadding()
            .padding(horizontal = 14.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.weight(1f)
        ) {
            if (showBack) {
                IconButton(
                    onClick = onBack,
                    modifier = Modifier.size(34.dp)
                ) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back", tint = KisanColors.TextMain)
                }
                Spacer(Modifier.width(4.dp))
            }
            Box(
                modifier = Modifier
                    .size(34.dp)
                    .clip(RoundedCornerShape(10.dp))
                    .background(KisanColors.Emerald.copy(alpha = 0.22f))
                    .border(1.dp, KisanColors.Emerald, RoundedCornerShape(10.dp)),
                contentAlignment = Alignment.Center
            ) {
                Icon(Icons.Default.Eco, contentDescription = null, tint = KisanColors.Mint, modifier = Modifier.size(20.dp))
            }
            Spacer(Modifier.width(8.dp))
            Column {
                Text(
                    text = titleOverride ?: "KisanDrishti AI",
                    color = KisanColors.TextMain,
                    fontSize = 15.sp,
                    fontWeight = FontWeight.ExtraBold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                Text(
                    text = "உழவர் பார்வை • किसान दृष्टि",
                    color = KisanColors.TextDim,
                    fontSize = 10.sp,
                    maxLines = 1
                )
            }
        }

        // Top-Right Hardware Connected + Latency Badges (explicitly requested by user)
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Column(horizontalAlignment = Alignment.End) {
                Surface(
                    color = Color(0xFF063826),
                    shape = RoundedCornerShape(999.dp),
                    border = BorderStroke(1.dp, KisanColors.Emerald.copy(alpha = 0.55f))
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Box(
                            modifier = Modifier
                                .size(6.dp)
                                .clip(CircleShape)
                                .background(KisanColors.Mint)
                        )
                        Spacer(Modifier.width(4.dp))
                        val hwShort = if (piConfig.usePiServer) "Pi 5" else hardwareLabel.take(10)
                        Text(
                            text = "$hwShort • $latencyBadge",
                            color = KisanColors.TextMain,
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Bold,
                            maxLines = 1
                        )
                    }
                }
                Spacer(Modifier.height(3.dp))
                Surface(
                    color = KisanColors.BgCardInner,
                    shape = RoundedCornerShape(4.dp),
                    border = BorderStroke(1.dp, KisanColors.BorderEmerald)
                ) {
                    Text(
                        text = if (piConfig.usePiServer) "PI EXECUTORCH" else "OFFLINE READY",
                        color = KisanColors.Mint,
                        fontSize = 8.5.sp,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 1.dp)
                    )
                }
            }

            Box(
                modifier = Modifier
                    .size(34.dp)
                    .clip(CircleShape)
                    .background(KisanColors.Emerald)
                    .clickable(onClick = onProfileClick),
                contentAlignment = Alignment.Center
            ) {
                Icon(Icons.Default.Person, contentDescription = "Hardware Settings", tint = Color(0xFF022C22), modifier = Modifier.size(19.dp))
            }
        }
    }
}

@Composable
fun KisanBottomNav(
    activeTab: MainTab,
    onSelect: (MainTab) -> Unit
) {
    NavigationBar(
        containerColor = KisanColors.BgHeader,
        contentColor = KisanColors.TextMain,
        modifier = Modifier
            .navigationBarsPadding()
            .border(BorderStroke(1.dp, KisanColors.BorderMuted))
    ) {
        NavItem(
            selected = activeTab == MainTab.SCAN,
            icon = Icons.Default.PhotoCamera,
            label = "Scan",
            onClick = { onSelect(MainTab.SCAN) }
        )
        NavItem(
            selected = activeTab == MainTab.ASK_AI,
            icon = Icons.Default.Mic,
            label = "Ask AI",
            onClick = { onSelect(MainTab.ASK_AI) }
        )
        NavItem(
            selected = activeTab == MainTab.GUIDE,
            icon = Icons.Default.MenuBook,
            label = "Guide",
            onClick = { onSelect(MainTab.GUIDE) }
        )
        NavItem(
            selected = activeTab == MainTab.HISTORY,
            icon = Icons.Default.History,
            label = "History",
            onClick = { onSelect(MainTab.HISTORY) }
        )
    }
}

@Composable
private fun RowScope.NavItem(
    selected: Boolean,
    icon: ImageVector,
    label: String,
    onClick: () -> Unit
) {
    NavigationBarItem(
        selected = selected,
        onClick = onClick,
        icon = { Icon(icon, contentDescription = label, modifier = Modifier.size(21.dp)) },
        label = { Text(label, fontSize = 11.sp, fontWeight = if (selected) FontWeight.Bold else FontWeight.Medium) },
        colors = NavigationBarItemDefaults.colors(
            selectedIconColor = KisanColors.Mint,
            selectedTextColor = KisanColors.Mint,
            unselectedIconColor = KisanColors.TextDim,
            unselectedTextColor = KisanColors.TextDim,
            indicatorColor = KisanColors.Emerald.copy(alpha = 0.16f)
        )
    )
}

@Composable
fun EdgeHardwareDialog(
    hardwareLabel: String,
    piConfig: PiEdgeConfig,
    onDismiss: () -> Unit,
    onSave: (Boolean, String) -> Unit,
    onTestPi: (String, (Boolean, String) -> Unit) -> Unit
) {
    var usePi by remember { mutableStateOf(piConfig.usePiServer) }
    var url by remember { mutableStateOf(piConfig.piBaseUrl) }
    var statusMsg by remember { mutableStateOf(piConfig.lastStatusText) }
    var testing by remember { mutableStateOf(false) }

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = KisanColors.BgCard,
        titleContentColor = KisanColors.TextMain,
        textContentColor = KisanColors.TextSoft,
        title = {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.Memory, contentDescription = null, tint = KisanColors.Mint)
                Spacer(Modifier.width(8.dp))
                Text("Edge Hardware & Pi 5 Sync", fontWeight = FontWeight.Bold, fontSize = 17.sp)
            }
        },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("Phone Device: $hardwareLabel", fontSize = 12.sp, color = KisanColors.Cyan)
                Text(
                    "By default this APK runs 100% standalone offline (ONNX MobileNetV3 + HSV + SQLite + TTS). Optionally connect to a Raspberry Pi 5 ExecuTorch server on Wi-Fi for Llama 3.2 chat.",
                    fontSize = 12.sp
                )
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Use Pi 5 ExecuTorch for Ask AI", fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
                    Switch(checked = usePi, onCheckedChange = { usePi = it })
                }
                OutlinedTextField(
                    value = url,
                    onValueChange = { url = it },
                    label = { Text("Raspberry Pi 5 URL") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(
                        onClick = {
                            testing = true
                            onTestPi(url) { ok, msg ->
                                testing = false
                                usePi = ok
                                statusMsg = msg
                            }
                        },
                        enabled = !testing,
                        colors = ButtonDefaults.buttonColors(containerColor = KisanColors.BgCardInner)
                    ) {
                        Text(if (testing) "Checking..." else "Test Pi Connection", color = KisanColors.Mint, fontSize = 12.sp)
                    }
                }
                Text("Status: $statusMsg", fontSize = 11.sp, color = KisanColors.TextMuted)
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    onSave(usePi, url)
                    onDismiss()
                },
                colors = ButtonDefaults.buttonColors(containerColor = KisanColors.Emerald)
            ) {
                Text("Save", color = Color(0xFF022C22), fontWeight = FontWeight.Bold)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Close", color = KisanColors.TextSoft) }
        }
    )
}
