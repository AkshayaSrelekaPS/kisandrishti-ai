"""
MobileNetV3-Small Training & INT8 Quantization Script for KisanDrishti AI.
Trains on Tomato and Potato classes per KisanDrishti_AI_new.md contract.
"""
import os
import time
import json
import torch
import torch.nn as nn
from torchvision import datasets, transforms
from torchvision.models import mobilenet_v3_small, MobileNet_V3_Small_Weights
from torch.utils.data import DataLoader

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
DATA_DIR = os.path.join(BASE_DIR, "data", "crops")
OUTPUT_DIR = os.path.join(BASE_DIR, "models")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def train_model(epochs=5, batch_size=32, lr=1e-3):
    print("=" * 65)
    print(f"  Training MobileNetV3-Small on {DEVICE}")
    print("=" * 65)

    # 1. Transforms
    data_transforms = transforms.Compose([
        transforms.Resize((256, 256)),
        transforms.RandomResizedCrop(224, scale=(0.8, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    # Load from organized dataset
    dataset = datasets.ImageFolder(root=DATA_DIR, transform=data_transforms)
    class_names = dataset.classes
    num_classes = len(class_names)
    print(f"Loaded {len(dataset)} images across {num_classes} classes:")
    for idx, name in enumerate(class_names):
        print(f"  [{idx:02d}] {name}")

    # Split 80/20
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size
    train_set, val_set = torch.utils.data.random_split(dataset, [train_size, val_size])

    train_loader = DataLoader(train_set, batch_size=batch_size, shuffle=True, num_workers=2)
    val_loader = DataLoader(val_set, batch_size=batch_size, shuffle=False, num_workers=2)

    # 2. Model setup
    weights = MobileNet_V3_Small_Weights.DEFAULT
    model = mobilenet_v3_small(weights=weights)
    in_features = model.classifier[3].in_features
    model.classifier[3] = nn.Linear(in_features=in_features, out_features=num_classes)
    model = model.to(DEVICE)

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    best_val_acc = 0.0
    for epoch in range(epochs):
        t0 = time.time()
        model.train()
        running_loss, running_correct = 0.0, 0
        for inputs, labels in train_loader:
            inputs, labels = inputs.to(DEVICE), labels.to(DEVICE)
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            _, preds = torch.max(outputs, 1)
            running_loss += loss.item() * inputs.size(0)
            running_correct += torch.sum(preds == labels.data).item()

        scheduler.step()
        train_acc = running_correct / train_size

        # Validation
        model.eval()
        val_correct = 0
        with torch.no_grad():
            for inputs, labels in val_loader:
                inputs, labels = inputs.to(DEVICE), labels.to(DEVICE)
                outputs = model(inputs)
                _, preds = torch.max(outputs, 1)
                val_correct += torch.sum(preds == labels.data).item()

        val_acc = val_correct / val_size
        elapsed = time.time() - t0
        print(f"Epoch [{epoch+1}/{epochs}] ({elapsed:.1f}s) | Train Acc: {train_acc*100:.2f}% | Val Acc: {val_acc*100:.2f}%")

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            save_path = os.path.join(OUTPUT_DIR, "best_mobilenetv3_model.pt")
            torch.save(model.state_dict(), save_path)

    print(f"\nBest Model Saved with Validation Accuracy: {best_val_acc*100:.2f}%")

    # Export Metadata
    with open(os.path.join(OUTPUT_DIR, "classes.json"), "w") as f:
        json.dump({"classes": class_names, "architecture": "mobilenet_v3_small"}, f, indent=2)

if __name__ == "__main__":
    train_model(epochs=5)

