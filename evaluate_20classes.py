#!/usr/bin/env python3
"""
Full 20-Class Evaluation, Confusion Matrix & Confidence Calibration Suite
Evaluates models/mobilenetv3_4crops_standalone.onnx via ONNX Runtime on a
deterministic 20% stratified held-out split of all 24,283 images in data/crops/.
"""
import json
import os
import random
import sys
import time
import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import onnxruntime as ort

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CROPS_DIR = os.path.join(BASE_DIR, "data", "crops")
MODELS_DIR = os.path.join(BASE_DIR, "models")

FOLDER_TO_CLASS = {
    "Corn/Gray_Leaf_Spot": "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot",
    "Corn/Common_Rust": "Corn_(maize)___Common_rust_",
    "Corn/Northern_Leaf_Blight": "Corn_(maize)___Northern_Leaf_Blight",
    "Corn/Healthy": "Corn_(maize)___healthy",
    "Potato/Early_Blight": "Potato___Early_blight",
    "Potato/Late_Blight": "Potato___Late_blight",
    "Potato/Healthy": "Potato___healthy",
    "Rice/Bacterial_Leaf_Blight": "Rice___Bacterial_leaf_blight",
    "Rice/Brown_Spot": "Rice___Brown_spot",
    "Rice/Leaf_Smut": "Rice___Leaf_smut",
    "Tomato/Bacterial_Spot": "Tomato___Bacterial_spot",
    "Tomato/Early_Blight": "Tomato___Early_blight",
    "Tomato/Late_Blight": "Tomato___Late_blight",
    "Tomato/Leaf_Mold": "Tomato___Leaf_Mold",
    "Tomato/Septoria_Leaf_Spot": "Tomato___Septoria_leaf_spot",
    "Tomato/Spider_Mites": "Tomato___Spider_mites Two-spotted_spider_mite",
    "Tomato/Target_Spot": "Tomato___Target_Spot",
    "Tomato/Yellow_Leaf_Curl": "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
    "Tomato/Mosaic_Virus": "Tomato___Tomato_mosaic_virus",
    "Tomato/Healthy": "Tomato___healthy",
}


def softmax(logits: np.ndarray, temp: float = 1.0) -> np.ndarray:
    scaled = logits / temp
    shifted = scaled - np.max(scaled, axis=-1, keepdims=True)
    exps = np.exp(shifted)
    return exps / np.sum(exps, axis=-1, keepdims=True)


def compute_ece(probs: np.ndarray, targets: np.ndarray, n_bins: int = 10) -> float:
    confs = np.max(probs, axis=1)
    preds = np.argmax(probs, axis=1)
    accs = (preds == targets).astype(np.float64)
    ece = 0.0
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    for i in range(n_bins):
        mask = (confs > bins[i]) & (confs <= bins[i + 1])
        if np.any(mask):
            ece += (np.sum(mask) / len(targets)) * abs(np.mean(accs[mask]) - np.mean(confs[mask]))
    return float(ece)


def fit_temperature(logits: np.ndarray, targets: np.ndarray) -> float:
    best_t, best_nll = 1.0, float("inf")
    for t in np.linspace(0.5, 3.0, 51):
        p = softmax(logits, temp=float(t))
        nll = -np.mean(np.log(np.clip(p[np.arange(len(targets)), targets], 1e-12, 1.0)))
        if nll < best_nll:
            best_nll = float(nll)
            best_t = float(t)
    return round(best_t, 2)


def preprocess(img_bgr: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    resized = cv2.resize(img_rgb, (256, 256), interpolation=cv2.INTER_LINEAR)
    start = (256 - 224) // 2
    cropped = resized[start:start + 224, start:start + 224]
    arr = cropped.astype(np.float32) / 255.0
    arr = (arr - mean) / std
    return np.expand_dims(np.transpose(arr, (2, 0, 1)), axis=0).astype(np.float32)


def normalize_crop(raw_cls: str) -> str:
    s = raw_cls.split("___")[0].lower()
    if "corn" in s:
        return "Corn"
    if "potato" in s:
        return "Potato"
    if "tomato" in s:
        return "Tomato"
    if "rice" in s:
        return "Rice"
    return s.capitalize()


def run_evaluation(val_ratio: float = 0.20):
    random.seed(42)
    with open(os.path.join(MODELS_DIR, "classes_4crops.json"), "r", encoding="utf-8") as f:
        meta = json.load(f)

    class_names = meta["classes"]
    class_to_idx = {c: i for i, c in enumerate(class_names)}
    mean = np.array(meta["mean"], dtype=np.float32)
    std = np.array(meta["std"], dtype=np.float32)

    onnx_path = os.path.join(MODELS_DIR, "mobilenetv3_4crops_standalone.onnx")
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 4
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    session = ort.InferenceSession(onnx_path, sess_options=opts, providers=["CPUExecutionProvider"])
    inp_name = session.get_inputs()[0].name

    eval_samples = []
    for rel_dir, cls_name in FOLDER_TO_CLASS.items():
        full_dir = os.path.join(CROPS_DIR, rel_dir)
        imgs = sorted(
            f for f in os.listdir(full_dir) if f.lower().endswith((".jpg", ".jpeg", ".png"))
        )
        random.shuffle(imgs)
        n_val = max(1, int(round(len(imgs) * val_ratio)))
        for f in imgs[:n_val]:
            eval_samples.append((os.path.join(full_dir, f), class_to_idx[cls_name]))

    print("=" * 75)
    print(f"  20-Class ONNX Evaluation ({len(eval_samples)} held-out images, 20% split)")
    print("=" * 75)

    all_logits = []
    all_targets = []
    latencies = []

    for i, (fpath, tgt) in enumerate(eval_samples, 1):
        img = cv2.imread(fpath)
        if img is None:
            continue
        x = preprocess(img, mean, std)
        t0 = time.perf_counter()
        logits = session.run(None, {inp_name: x})[0][0]
        latencies.append((time.perf_counter() - t0) * 1000.0)
        all_logits.append(logits)
        all_targets.append(tgt)
        if i % 1000 == 0:
            print(f"  Evaluated {i}/{len(eval_samples)} images...")

    logits_arr = np.vstack(all_logits)
    targets_arr = np.array(all_targets, dtype=int)
    probs_raw = softmax(logits_arr, temp=1.0)
    preds = np.argmax(probs_raw, axis=1)
    confs = np.max(probs_raw, axis=1)

    overall_acc = float(np.mean(preds == targets_arr))
    crop_correct = sum(
        normalize_crop(class_names[p]) == normalize_crop(class_names[t])
        for p, t in zip(preds, targets_arr)
    )
    gate_a_crop_acc = crop_correct / len(targets_arr)

    # Per-class metrics & confusion matrix
    num_classes = len(class_names)
    cm = np.zeros((num_classes, num_classes), dtype=int)
    for t, p in zip(targets_arr, preds):
        cm[t, p] += 1

    print("\nPer-Class Held-Out Accuracy:")
    per_class = {}
    f1_scores = []
    for idx, cname in enumerate(class_names):
        tp = cm[idx, idx]
        total = int(np.sum(cm[idx, :]))
        pred_total = int(np.sum(cm[:, idx]))
        acc = (tp / total) if total else 0.0
        prec = (tp / pred_total) if pred_total else 0.0
        f1 = (2 * prec * acc / (prec + acc)) if (prec + acc) > 0 else 0.0
        f1_scores.append(f1)
        per_class[cname] = {"support": total, "correct": int(tp), "accuracy": round(acc, 4), "f1": round(f1, 4)}
        print(f"  [{idx:02d}] {cname:<52s} | {tp:4d}/{total:4d} ({acc*100:6.2f}%) | F1={f1*100:6.2f}%")

    # Calibration & threshold analysis
    ece_before = compute_ece(probs_raw, targets_arr)
    opt_temp = fit_temperature(logits_arr, targets_arr)
    probs_cal = softmax(logits_arr, temp=opt_temp)
    ece_after = compute_ece(probs_cal, targets_arr)

    high_mask = confs >= 0.75
    border_mask = (confs >= 0.50) & (confs < 0.75)
    low_mask = confs < 0.50

    high_acc = float(np.mean(preds[high_mask] == targets_arr[high_mask])) if np.any(high_mask) else 0.0
    border_acc = float(np.mean(preds[border_mask] == targets_arr[border_mask])) if np.any(border_mask) else 0.0
    low_acc = float(np.mean(preds[low_mask] == targets_arr[low_mask])) if np.any(low_mask) else 0.0

    print("\n" + "=" * 75)
    print(f"Overall 20-Class Accuracy:    {overall_acc*100:.2f}% ({int(np.sum(preds==targets_arr))}/{len(targets_arr)})")
    print(f"Macro-Averaged F1:            {np.mean(f1_scores)*100:.2f}%")
    print(f"Gate A Crop-Identity Acc:     {gate_a_crop_acc*100:.2f}%")
    print(f"Mean ONNX Vision Latency:     {np.mean(latencies):.2f} ms (p95: {np.percentile(latencies, 95):.2f} ms)")
    print(f"Confidence Thresholds (>=75%): {int(np.sum(high_mask))} samples, Acc={high_acc*100:.2f}%")
    print(f"Borderline (50-75%):           {int(np.sum(border_mask))} samples, Acc={border_acc*100:.2f}%")
    print(f"Rejected (<50%):               {int(np.sum(low_mask))} samples, Acc={low_acc*100:.2f}%")
    print(f"ECE Before / After Temp (T={opt_temp}): {ece_before:.4f} -> {ece_after:.4f}")
    print("=" * 75)

    # Save confusion matrix PNG
    fig, ax = plt.subplots(figsize=(13, 11))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_title(f"KisanDrishti 20-Class ONNX Confusion Matrix (Acc={overall_acc*100:.2f}%, N={len(targets_arr)})")
    ax.set_xlabel("Predicted Class")
    ax.set_ylabel("True Class")
    short_names = [c.replace("Corn_(maize)___", "Corn/").replace("Tomato___", "Tom/").replace("Potato___", "Pot/").replace("Rice___", "Rice/") for c in class_names]
    ax.set_xticks(range(num_classes))
    ax.set_yticks(range(num_classes))
    ax.set_xticklabels(short_names, rotation=60, ha="right", fontsize=8)
    ax.set_yticklabels(short_names, fontsize=8)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    cm_path = os.path.join(MODELS_DIR, "confusion_matrix_20classes_eval.png")
    fig.savefig(cm_path, dpi=180)
    plt.close(fig)

    report = {
        "model": os.path.basename(onnx_path),
        "num_evaluated": int(len(targets_arr)),
        "overall_accuracy": round(overall_acc, 4),
        "macro_f1": round(float(np.mean(f1_scores)), 4),
        "gate_a_crop_accuracy": round(gate_a_crop_acc, 4),
        "mean_onnx_latency_ms": round(float(np.mean(latencies)), 2),
        "p95_onnx_latency_ms": round(float(np.percentile(latencies, 95)), 2),
        "optimal_temperature": opt_temp,
        "ece_before": round(ece_before, 4),
        "ece_after": round(ece_after, 4),
        "confidence_bands": {
            "high_ge_75": {"count": int(np.sum(high_mask)), "accuracy": round(high_acc, 4)},
            "borderline_50_75": {"count": int(np.sum(border_mask)), "accuracy": round(border_acc, 4)},
            "rejected_lt_50": {"count": int(np.sum(low_mask)), "accuracy": round(low_acc, 4)},
        },
        "per_class": per_class,
        "confusion_matrix_path": cm_path,
    }
    rep_path = os.path.join(MODELS_DIR, "evaluation_report_20classes.json")
    with open(rep_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"Saved confusion matrix: {cm_path}")
    print(f"Saved JSON report:      {rep_path}")


if __name__ == "__main__":
    run_evaluation()
