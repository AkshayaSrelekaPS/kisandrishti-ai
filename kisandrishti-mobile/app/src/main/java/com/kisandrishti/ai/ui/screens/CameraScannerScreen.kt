package com.kisandrishti.ai.ui.screens

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import androidx.camera.core.Camera
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageCapture
import androidx.camera.core.ImageCaptureException
import androidx.camera.core.ImageProxy
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.*
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
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import com.kisandrishti.ai.data.InspectionTarget
import com.kisandrishti.ai.ui.theme.KisanColors
import java.util.concurrent.Executors

@Composable
fun CameraScannerScreen(
    selectedTarget: InspectionTarget,
    hardwareLabel: String,
    onBack: () -> Unit,
    onPickGallery: () -> Unit,
    onCaptured: (Bitmap) -> Unit
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val cameraExecutor = remember { Executors.newSingleThreadExecutor() }

    var lensFacing by remember { mutableIntStateOf(CameraSelector.LENS_FACING_BACK) }
    var flashOn by remember { mutableStateOf(false) }
    var imageCapture by remember { mutableStateOf<ImageCapture?>(null) }
    var boundCamera by remember { mutableStateOf<Camera?>(null) }
    var captureError by remember { mutableStateOf<String?>(null) }
    var capturing by remember { mutableStateOf(false) }

    val previewView = remember { PreviewView(context) }

    LaunchedEffect(lensFacing) {
        val providerFuture = ProcessCameraProvider.getInstance(context)
        providerFuture.addListener({
            try {
                val cameraProvider = providerFuture.get()
                val preview = Preview.Builder().build().also {
                    it.setSurfaceProvider(previewView.surfaceProvider)
                }
                val capture = ImageCapture.Builder()
                    .setCaptureMode(ImageCapture.CAPTURE_MODE_MINIMIZE_LATENCY)
                    .build()
                val selector = CameraSelector.Builder().requireLensFacing(lensFacing).build()
                cameraProvider.unbindAll()
                val cam = cameraProvider.bindToLifecycle(lifecycleOwner, selector, preview, capture)
                imageCapture = capture
                boundCamera = cam
                cam.cameraControl.enableTorch(flashOn)
            } catch (e: Exception) {
                captureError = "Camera preview unavailable: ${e.message}. Use Gallery upload instead."
            }
        }, ContextCompat.getMainExecutor(context))
    }

    DisposableEffect(Unit) {
        onDispose {
            cameraExecutor.shutdown()
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(KisanColors.BgRoot)
            .statusBarsPadding()
            .navigationBarsPadding()
    ) {
        // Header bar matching Stitch Image 2
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(KisanColors.BgHeader)
                .padding(horizontal = 12.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                IconButton(onClick = onBack) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back", tint = KisanColors.TextMain)
                }
                Icon(Icons.Default.Eco, contentDescription = null, tint = KisanColors.Mint, modifier = Modifier.size(20.dp))
                Spacer(Modifier.width(6.dp))
                Text("Live Edge Scanner", color = KisanColors.TextMain, fontWeight = FontWeight.Bold, fontSize = 15.sp)
            }
            Surface(
                color = KisanColors.BgCardInner,
                shape = RoundedCornerShape(999.dp),
                border = BorderStroke(1.dp, KisanColors.BorderEmerald)
            ) {
                Text(
                    text = selectedTarget.titleEn,
                    color = KisanColors.Mint,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp)
                )
            }
        }

        // Camera Viewfinder + Framing Reticle
        Box(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .background(Color.Black)
        ) {
            AndroidView(factory = { previewView }, modifier = Modifier.fillMaxSize())

            // Overlay Reticle Brackets & Crosshair
            Canvas(modifier = Modifier.fillMaxSize()) {
                val padX = size.width * 0.12f
                val boxSize = size.width - padX * 2f
                val topY = (size.height - boxSize) * 0.48f
                val len = 34.dp.toPx()
                val stroke = 3.dp.toPx()

                // Top-left
                drawLine(KisanColors.Cyan, Offset(padX, topY), Offset(padX + len, topY), stroke)
                drawLine(KisanColors.Cyan, Offset(padX, topY), Offset(padX, topY + len), stroke)
                // Top-right
                drawLine(KisanColors.Cyan, Offset(padX + boxSize, topY), Offset(padX + boxSize - len, topY), stroke)
                drawLine(KisanColors.Cyan, Offset(padX + boxSize, topY), Offset(padX + boxSize, topY + len), stroke)
                // Bottom-left
                drawLine(KisanColors.Mint, Offset(padX, topY + boxSize), Offset(padX + len, topY + boxSize), stroke)
                drawLine(KisanColors.Mint, Offset(padX, topY + boxSize), Offset(padX, topY + boxSize - len), stroke)
                // Bottom-right
                drawLine(KisanColors.Mint, Offset(padX + boxSize, topY + boxSize), Offset(padX + boxSize - len, topY + boxSize), stroke)
                drawLine(KisanColors.Mint, Offset(padX + boxSize, topY + boxSize), Offset(padX + boxSize, topY + boxSize - len), stroke)

                // Center Crosshair
                val cx = size.width / 2f
                val cy = topY + boxSize / 2f
                val ch = 12.dp.toPx()
                drawLine(KisanColors.Cyan, Offset(cx - ch, cy), Offset(cx + ch, cy), 2.dp.toPx())
                drawLine(KisanColors.Cyan, Offset(cx, cy - ch), Offset(cx, cy + ch), 2.dp.toPx())
            }

            // Top viewfinder status & flash
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .align(Alignment.TopCenter)
                    .padding(12.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Surface(
                    color = Color.Black.copy(alpha = 0.6f),
                    shape = RoundedCornerShape(999.dp),
                    border = BorderStroke(1.dp, KisanColors.Emerald.copy(alpha = 0.6f))
                ) {
                    Row(modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp), verticalAlignment = Alignment.CenterVertically) {
                        Box(modifier = Modifier.size(7.dp).clip(CircleShape).background(KisanColors.Mint))
                        Spacer(Modifier.width(6.dp))
                        Text("Edge AI Live | Hold Steady", color = Color.White, fontSize = 11.sp, fontWeight = FontWeight.SemiBold)
                    }
                }
                IconButton(
                    onClick = {
                        flashOn = !flashOn
                        boundCamera?.cameraControl?.enableTorch(flashOn)
                    },
                    modifier = Modifier
                        .size(38.dp)
                        .clip(CircleShape)
                        .background(Color.Black.copy(alpha = 0.6f))
                ) {
                    Icon(
                        if (flashOn) Icons.Default.FlashOn else Icons.Default.FlashOff,
                        contentDescription = "Flash",
                        tint = if (flashOn) KisanColors.Amber else Color.White
                    )
                }
            }

            // Target & Lighting Hint Row
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .align(Alignment.TopCenter)
                    .padding(top = 56.dp, start = 12.dp, end = 12.dp),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Surface(color = KisanColors.BgCard.copy(alpha = 0.85f), shape = RoundedCornerShape(999.dp)) {
                    Text(
                        "🌿 Inspecting: ${selectedTarget.titleEn}",
                        color = KisanColors.TextMain,
                        fontSize = 11.sp,
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp)
                    )
                }
                Surface(color = KisanColors.BgCard.copy(alpha = 0.85f), shape = RoundedCornerShape(999.dp)) {
                    Text(
                        "✔ Good Lighting",
                        color = KisanColors.Mint,
                        fontSize = 11.sp,
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp)
                    )
                }
            }

            // Bottom framing hint
            Surface(
                color = KisanColors.BgCardDeep.copy(alpha = 0.9f),
                shape = RoundedCornerShape(999.dp),
                border = BorderStroke(1.dp, KisanColors.BorderEmerald),
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .padding(bottom = 14.dp)
            ) {
                Text(
                    "Position leaf flat, 15–20 cm away • Avoid shadow",
                    color = KisanColors.TextSoft,
                    fontSize = 11.sp,
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 5.dp)
                )
            }

            if (captureError != null) {
                Surface(
                    color = KisanColors.RedBg.copy(alpha = 0.9f),
                    modifier = Modifier.align(Alignment.Center).padding(20.dp),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Text(captureError!!, color = Color.White, modifier = Modifier.padding(14.dp), fontSize = 13.sp)
                }
            }
        }

        // Bottom Controls matching Stitch Image 2
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .background(KisanColors.BgHeader)
                .padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Surface(
                color = KisanColors.BgCard,
                shape = RoundedCornerShape(12.dp),
                border = BorderStroke(1.dp, KisanColors.BorderEmerald),
                modifier = Modifier.fillMaxWidth()
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Default.Memory, contentDescription = null, tint = KisanColors.Mint, modifier = Modifier.size(18.dp))
                        Spacer(Modifier.width(8.dp))
                        Column {
                            Text("Edge Agronomist ONNX v2.4", color = KisanColors.TextMain, fontWeight = FontWeight.Bold, fontSize = 12.sp)
                            Text("Offline ready • Tamil, Hindi, English", color = KisanColors.TextDim, fontSize = 10.sp)
                        }
                    }
                    Text(hardwareLabel.take(12), color = KisanColors.Cyan, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                }
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceEvenly,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    modifier = Modifier.clickable {
                        onBack()
                        onPickGallery()
                    }
                ) {
                    Surface(
                        color = KisanColors.BgCardInner,
                        shape = RoundedCornerShape(12.dp),
                        border = BorderStroke(1.dp, KisanColors.BorderEmerald),
                        modifier = Modifier.size(48.dp)
                    ) {
                        Box(contentAlignment = Alignment.Center) {
                            Icon(Icons.Default.PhotoLibrary, contentDescription = "Gallery", tint = KisanColors.TextSoft)
                        }
                    }
                    Spacer(Modifier.height(3.dp))
                    Text("Gallery", color = KisanColors.TextSoft, fontSize = 11.sp)
                }

                // Giant Emerald Circular Shutter
                Box(
                    modifier = Modifier
                        .size(72.dp)
                        .clip(CircleShape)
                        .background(KisanColors.Emerald.copy(alpha = 0.28f))
                        .border(3.dp, KisanColors.Mint, CircleShape)
                        .clickable(enabled = !capturing && imageCapture != null) {
                            val cap = imageCapture ?: return@clickable
                            capturing = true
                            cap.takePicture(
                                cameraExecutor,
                                object : ImageCapture.OnImageCapturedCallback() {
                                    override fun onCaptureSuccess(image: ImageProxy) {
                                        val bmp = imageProxyToBitmap(image)
                                        image.close()
                                        capturing = false
                                        if (bmp != null) {
                                            ContextCompat.getMainExecutor(context).execute {
                                                onCaptured(bmp)
                                            }
                                        }
                                    }

                                    override fun onError(exception: ImageCaptureException) {
                                        capturing = false
                                        captureError = "Capture failed: ${exception.message}"
                                    }
                                }
                            )
                        },
                    contentAlignment = Alignment.Center
                ) {
                    Box(
                        modifier = Modifier
                            .size(54.dp)
                            .clip(CircleShape)
                            .background(KisanColors.Mint),
                        contentAlignment = Alignment.Center
                    ) {
                        if (capturing) {
                            CircularProgressIndicator(color = Color(0xFF022C22), strokeWidth = 2.dp, modifier = Modifier.size(22.dp))
                        } else {
                            Icon(Icons.Default.PhotoCamera, contentDescription = "Capture", tint = Color(0xFF022C22), modifier = Modifier.size(26.dp))
                        }
                    }
                }

                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    modifier = Modifier.clickable {
                        lensFacing = if (lensFacing == CameraSelector.LENS_FACING_BACK) {
                            CameraSelector.LENS_FACING_FRONT
                        } else {
                            CameraSelector.LENS_FACING_BACK
                        }
                    }
                ) {
                    Surface(
                        color = KisanColors.BgCardInner,
                        shape = RoundedCornerShape(12.dp),
                        border = BorderStroke(1.dp, KisanColors.BorderEmerald),
                        modifier = Modifier.size(48.dp)
                    ) {
                        Box(contentAlignment = Alignment.Center) {
                            Icon(Icons.Default.FlipCameraAndroid, contentDescription = "Flip Camera", tint = KisanColors.TextSoft)
                        }
                    }
                    Spacer(Modifier.height(3.dp))
                    Text("Flip Cam", color = KisanColors.TextSoft, fontSize = 11.sp)
                }
            }

            Text(
                "⚡ 100% Offline Edge Inference • Zero Data Cost",
                color = KisanColors.TextDim,
                fontSize = 10.sp
            )
        }
    }
}

private fun imageProxyToBitmap(image: ImageProxy): Bitmap? {
    val buffer = image.planes[0].buffer
    val bytes = ByteArray(buffer.remaining())
    buffer.get(bytes)
    val raw = BitmapFactory.decodeByteArray(bytes, 0, bytes.size) ?: return null
    val rot = image.imageInfo.rotationDegrees
    if (rot == 0) return raw
    val m = Matrix().apply { postRotate(rot.toFloat()) }
    return Bitmap.createBitmap(raw, 0, 0, raw.width, raw.height, m, true)
}
