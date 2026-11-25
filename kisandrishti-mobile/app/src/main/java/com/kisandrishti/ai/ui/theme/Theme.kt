package com.kisandrishti.ai.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

object KisanColors {
    val BgRoot = Color(0xFF02110B)
    val BgHeader = Color(0xFF051C13)
    val BgCard = Color(0xFF062116)
    val BgCardDeep = Color(0xFF041710)
    val BgCardInner = Color(0xFF0A2E20)
    val BorderEmerald = Color(0xFF145338)
    val BorderMuted = Color(0xFF0F3B28)

    val Emerald = Color(0xFF10B981)
    val Mint = Color(0xFF34D399)
    val Cyan = Color(0xFF22D3EE)
    val Teal = Color(0xFF14B8A6)
    val Amber = Color(0xFFF59E0B)
    val AmberBg = Color(0xFF3B2204)
    val AmberBorder = Color(0xFF854D0E)
    val Red = Color(0xFFF87171)
    val RedBg = Color(0xFF3B0D11)
    val RedBorder = Color(0xFF991B1B)

    val TextMain = Color(0xFFECFDF5)
    val TextSoft = Color(0xFFA7F3D0)
    val TextMuted = Color(0xFF6EE7B7)
    val TextDim = Color(0xFF648D7C)
}

private val DarkScheme = darkColorScheme(
    primary = KisanColors.Emerald,
    onPrimary = Color(0xFF022C22),
    secondary = KisanColors.Cyan,
    background = KisanColors.BgRoot,
    surface = KisanColors.BgCard,
    onBackground = KisanColors.TextMain,
    onSurface = KisanColors.TextMain,
)

@Composable
fun KisanDrishtiTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = DarkScheme,
        content = content
    )
}
