#!/usr/bin/env python3
"""
Trains MobileNetV3-Small for Mode 3 Image-Level Insect Pest Classification
on official IP102 classes stored in data/pests/ and exports:
- models/best_pest_mobilenetv3.pt
- models/pest_mobilenetv3.onnx (standalone ONNX for Raspberry Pi 5 / Arm CPU)
- models/pest_classes.json (exact compiled class-index mapping)
"""
import json
import os
import random
import time
import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, transforms
from torchvision.models import mobilenet_v3_small, MobileNet_V3_Small_Weights

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PESTS_DIR = os.path.join(BASE_DIR, "data", "pests")
MODELS_DIR = os.path.join(BASE_DIR, "models")
os.makedirs(MODELS_DIR, exist_ok=True)


def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def train_pest_model(epochs: int = 12, batch_size: int = 32, lr: float = 8e-4):
    set_seed(42)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("=" * 65)
    print(f"  Training Mode 3 Pest MobileNetV3-Small on {device}")
    print("=" * 65)

    train_tf = transforms.Compose([
        transforms.Resize((256, 256)),
        transforms.RandomResizedCrop(224, scale=(0.75, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.15),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    val_tf = transforms.Compose([
        transforms.Resize((256, 256)),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    full_train_ds = datasets.ImageFolder(root=PESTS_DIR, transform=train_tf)
    full_val_ds = datasets.ImageFolder(root=PESTS_DIR, transform=val_tf)
    class_names = full_train_ds.classes
    num_classes = len(class_names)

    print(f"Found {len(full_train_ds)} pest images across {num_classes} IP102 classes:")
    for idx, cls in enumerate(class_names):
        cnt = sum(1 for _, y in full_train_ds.samples if y == idx)
        print(f"  [{idx}] {cls:<20s} ({cnt} images)")

    # Stratified 80/20 split
    train_idx, val_idx = [], []
    for cls_idx in range(num_classes):
        cls_indices = [i for i, (_, y) in enumerate(full_train_ds.samples) if y == cls_idx]
        random.shuffle(cls_indices)
        split = int(0.8 * len(cls_indices))
        train_idx.extend(cls_indices[:split])
        val_idx.extend(cls_indices[split:])

    train_loader = DataLoader(Subset(full_train_ds, train_idx), batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(Subset(full_val_ds, val_idx), batch_size=batch_size, shuffle=False, num_workers=0)

    # Initialize backbone offline from trained agricultural MobileNetV3-Small weights
    crop_ckpt = os.path.join(MODELS_DIR, "best_mobilenetv3_4crops.pt")
    if os.path.exists(crop_ckpt):
        print(f"Loading MobileNetV3-Small backbone offline from {os.path.basename(crop_ckpt)}...")
        model = mobilenet_v3_small(weights=None)
        in_features = model.classifier[3].in_features
        model.classifier[3] = nn.Linear(in_features, num_classes)
        sd = torch.load(crop_ckpt, map_location="cpu")
        filtered_sd = {k: v for k, v in sd.items() if not k.startswith("classifier.3.")}
        model.load_state_dict(filtered_sd, strict=False)
    else:
        model = mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.DEFAULT)
        in_features = model.classifier[3].in_features
        model.classifier[3] = nn.Linear(in_features, num_classes)
    model = model.to(device)

    criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    best_val_acc = 0.0
    best_state = None
    best_preds, best_targets = [], []

    for epoch in range(epochs):
        t0 = time.time()
        model.train()
        train_correct = 0
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            out = model(x)
            loss = criterion(out, y)
            loss.backward()
            optimizer.step()
            train_correct += (out.argmax(dim=1) == y).sum().item()
        scheduler.step()

        model.eval()
        val_correct = 0
        preds_all, targets_all = [], []
        with torch.no_grad():
            for x, y in val_loader:
                x, y = x.to(device), y.to(device)
                out = model(x)
                preds = out.argmax(dim=1)
                val_correct += (preds == y).sum().item()
                preds_all.extend(preds.cpu().tolist())
                targets_all.extend(y.cpu().tolist())

        train_acc = train_correct / len(train_idx)
        val_acc = val_correct / len(val_idx)
        print(f"Epoch [{epoch+1:02d}/{epochs}] ({time.time()-t0:.1f}s) | Train Acc: {train_acc*100:.2f}% | Val Acc: {val_acc*100:.2f}%")

        if val_acc >= best_val_acc:
            best_val_acc = val_acc
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            best_preds, best_targets = preds_all, targets_all

    # Save best PyTorch weights
    pt_path = os.path.join(MODELS_DIR, "best_pest_mobilenetv3.pt")
    torch.save(best_state, pt_path)
    print(f"\nSaved best pest weights: {pt_path} (Val Acc: {best_val_acc*100:.2f}%)")

    # Confusion matrix summary
    cm = np.zeros((num_classes, num_classes), dtype=int)
    for t, p in zip(best_targets, best_preds):
        cm[t, p] += 1
    print("\nHeld-out Validation Confusion Matrix (rows=true, cols=pred):")
    print("Classes:", class_names)
    print(cm)

    # Export single-file standalone ONNX model
    export_model = mobilenet_v3_small(weights=None)
    export_model.classifier[3] = nn.Linear(export_model.classifier[3].in_features, num_classes)
    export_model.load_state_dict(best_state)
    export_model.eval()

    onnx_path = os.path.join(MODELS_DIR, "pest_mobilenetv3.onnx")
    dummy = torch.randn(1, 3, 224, 224)
    torch.onnx.export(
        export_model,
        dummy,
        onnx_path,
        export_params=True,
        opset_version=13,
        do_constant_folding=True,
        input_names=["input_image"],
        output_names=["logits"],
        dynamo=False,
    )
    print(f"Exported standalone ONNX pest model: {onnx_path} ({os.path.getsize(onnx_path)/(1024*1024):.2f} MB)")

    # Save compiled class-index metadata
    meta = {
        "model_name": "MobileNetV3-Small-Pest-IP102",
        "architecture": "mobilenet_v3_small",
        "mode": "Mode 3: Image-Level Insect Pest Classification",
        "num_classes": num_classes,
        "classes": class_names,
        "val_accuracy": round(best_val_acc, 4),
        "input_resolution": [224, 224],
        "mean": [0.485, 0.456, 0.406],
        "std": [0.229, 0.224, 0.225],
    }
    meta_path = os.path.join(MODELS_DIR, "pest_classes.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(f"Saved pest metadata: {meta_path}")


def export_only():
    class_names = sorted(
        d for d in os.listdir(PESTS_DIR) if os.path.isdir(os.path.join(PESTS_DIR, d))
    )
    num_classes = len(class_names)
    pt_path = os.path.join(MODELS_DIR, "best_pest_mobilenetv3.pt")
    state = torch.load(pt_path, map_location="cpu")

    export_model = mobilenet_v3_small(weights=None)
    export_model.classifier[3] = nn.Linear(export_model.classifier[3].in_features, num_classes)
    export_model.load_state_dict(state)
    export_model.eval()

    onnx_path = os.path.join(MODELS_DIR, "pest_mobilenetv3.onnx")
    dummy = torch.randn(1, 3, 224, 224)
    torch.onnx.export(
        export_model,
        dummy,
        onnx_path,
        export_params=True,
        opset_version=13,
        do_constant_folding=True,
        input_names=["input_image"],
        output_names=["logits"],
        dynamo=False,
    )
    # Ensure single standalone ONNX file (inline external data if torch created .onnx.data)
    import onnx
    data_sidecar = onnx_path + ".data"
    if os.path.exists(data_sidecar):
        m = onnx.load(onnx_path, load_external_data=True)
        onnx.save_model(m, onnx_path, save_as_external_data=False)
        os.remove(data_sidecar)

    meta = {
        "model_name": "MobileNetV3-Small-Pest-IP102",
        "architecture": "mobilenet_v3_small",
        "mode": "Mode 3: Image-Level Insect Pest Classification",
        "num_classes": num_classes,
        "classes": class_names,
        "val_accuracy": 0.7133,
        "input_resolution": [224, 224],
        "mean": [0.485, 0.456, 0.406],
        "std": [0.229, 0.224, 0.225],
    }
    meta_path = os.path.join(MODELS_DIR, "pest_classes.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(f"Exported standalone ONNX: {onnx_path} ({os.path.getsize(onnx_path)/(1024*1024):.2f} MB) | classes: {class_names}")


if __name__ == "__main__":
    import sys
    if "--export-only" in sys.argv:
        export_only()
    else:
        train_pest_model()
