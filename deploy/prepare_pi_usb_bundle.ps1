<#
KisanDrishti AI: Offline Raspberry Pi 5 Weight & Voice Bundle Copier
Copies non-Git binary assets (.pte, offline TTS/STT models, optional fallback .gguf)
to a USB drive or staging folder for 100% air-gapped Raspberry Pi provisioning.

Usage:
  powershell -ExecutionPolicy Bypass -File deploy\prepare_pi_usb_bundle.ps1 -TargetDir E:\kisandrishti_models
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$TargetDir
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$SrcModels = Join-Path $RepoRoot "models"
$DstModels = Join-Path $TargetDir "models"

New-Item -ItemType Directory -Force -Path $DstModels | Out-Null

$RequiredFiles = @(
    "llama3_2_1b_instruct_8da4w_xnnpack.pte",
    "tokenizer.model",
    "mobilenetv3_4crops_standalone.onnx",
    "classes_4crops.json",
    "pest_mobilenetv3.onnx",
    "pest_classes.json"
)

foreach ($f in $RequiredFiles) {
    $src = Join-Path $SrcModels $f
    if (Test-Path $src) {
        Write-Host "Copying $f..."
        Copy-Item -Force $src (Join-Path $DstModels $f)
    } else {
        Write-Warning "Missing expected file: $src"
    }
}

foreach ($sub in @("tts", "stt")) {
    $srcDir = Join-Path $SrcModels $sub
    if (Test-Path $srcDir) {
        Write-Host "Copying models\$sub\..."
        Copy-Item -Recurse -Force $srcDir (Join-Path $DstModels $sub)
    }
}

Write-Host "`nOffline Pi 5 model bundle ready at: $DstModels"
Write-Host "On Raspberry Pi 5: cp -r $DstModels/* ~/kisandrishti-ai/models/"
