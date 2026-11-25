#!/usr/bin/env python3
"""
Official Dataset Collector & Organizer for KisanDrishti AI.
Collects from official public sources without requiring git or manual browser downloads:
1. PlantVillage (spMohanty/PlantVillage-Dataset on GitHub) -> all 17 Potato/Tomato/Corn classes
2. Rice Leaf Diseases (UCI / NabilAbdul GitHub mirror) -> 3 Rice classes
3. IP102 Insect Pest Subset (HuggingFace datasets-server / liaad/agricultural-data) -> data/pests/
   (plus optional Kaggle CLI mirror if ~/.kaggle/kaggle.json is configured)
"""
import argparse
import concurrent.futures
import json
import os
import shutil
import sys
import urllib.parse
import zipfile

import requests
from requests.adapters import HTTPAdapter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

_SESSION = requests.Session()
_ADAPTER = HTTPAdapter(pool_connections=32, pool_maxsize=32)
_SESSION.mount("https://", _ADAPTER)
_SESSION.mount("http://", _ADAPTER)
_SESSION.headers.update({"User-Agent": "KisanDrishti-Dataset-Fetcher/1.0"})

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CROPS_DIR = os.path.join(BASE_DIR, "data", "crops")
PESTS_DIR = os.path.join(BASE_DIR, "data", "pests")
TEMP_DIR = os.path.join(BASE_DIR, "temp_download")

os.makedirs(CROPS_DIR, exist_ok=True)
os.makedirs(PESTS_DIR, exist_ok=True)

PLANTVILLAGE_MAPPING = {
    # Potato (3)
    "raw/color/Potato___Early_blight": "Potato/Early_Blight",
    "raw/color/Potato___Late_blight": "Potato/Late_Blight",
    "raw/color/Potato___healthy": "Potato/Healthy",
    # Tomato (10)
    "raw/color/Tomato___Bacterial_spot": "Tomato/Bacterial_Spot",
    "raw/color/Tomato___Early_blight": "Tomato/Early_Blight",
    "raw/color/Tomato___Late_blight": "Tomato/Late_Blight",
    "raw/color/Tomato___Leaf_Mold": "Tomato/Leaf_Mold",
    "raw/color/Tomato___Septoria_leaf_spot": "Tomato/Septoria_Leaf_Spot",
    "raw/color/Tomato___Spider_mites Two-spotted_spider_mite": "Tomato/Spider_Mites",
    "raw/color/Tomato___Target_Spot": "Tomato/Target_Spot",
    "raw/color/Tomato___Tomato_Yellow_Leaf_Curl_Virus": "Tomato/Yellow_Leaf_Curl",
    "raw/color/Tomato___Tomato_mosaic_virus": "Tomato/Mosaic_Virus",
    "raw/color/Tomato___healthy": "Tomato/Healthy",
    # Corn (4)
    "raw/color/Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot": "Corn/Gray_Leaf_Spot",
    "raw/color/Corn_(maize)___Common_rust_": "Corn/Common_Rust",
    "raw/color/Corn_(maize)___Northern_Leaf_Blight": "Corn/Northern_Leaf_Blight",
    "raw/color/Corn_(maize)___healthy": "Corn/Healthy",
}

RICE_URLS = {
    "Rice/Bacterial_Leaf_Blight": "https://raw.githubusercontent.com/NabilAbdul/Rice-Leaf-Disease-ImageDetection---CNN/master/Bacterial%20leaf%20blight-20200814T055237Z-001.zip",
    "Rice/Brown_Spot": "https://raw.githubusercontent.com/NabilAbdul/Rice-Leaf-Disease-ImageDetection---CNN/master/Brown%20spot-20200814T055208Z-001.zip",
    "Rice/Leaf_Smut": "https://raw.githubusercontent.com/NabilAbdul/Rice-Leaf-Disease-ImageDetection---CNN/master/Leaf%20smut-20200814T055530Z-001.zip",
}


def _http_get_json(url: str) -> dict | list:
    resp = _SESSION.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _download_file(url: str, dst_path: str) -> bool:
    if os.path.exists(dst_path) and os.path.getsize(dst_path) > 0:
        return True
    resp = _SESSION.get(url, timeout=30)
    resp.raise_for_status()
    with open(dst_path, "wb") as out:
        out.write(resp.content)
    return True


def fetch_plantvillage_missing(max_per_class: int = 0, workers: int = 24):
    print("=" * 65)
    print("1. Checking & Fetching Official PlantVillage Classes (GitHub)")
    print("=" * 65)

    already_complete = {
        "Potato/Early_Blight", "Potato/Late_Blight", "Potato/Healthy",
        "Tomato/Early_Blight", "Tomato/Late_Blight", "Tomato/Yellow_Leaf_Curl", "Tomato/Healthy",
        "Corn/Common_Rust", "Corn/Northern_Leaf_Blight", "Corn/Healthy",
    }

    missing_targets = {}
    for src_rel, dst_rel in PLANTVILLAGE_MAPPING.items():
        dst_dir = os.path.join(CROPS_DIR, dst_rel)
        os.makedirs(dst_dir, exist_ok=True)
        existing = [f for f in os.listdir(dst_dir) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
        if dst_rel in already_complete and len(existing) > 0:
            print(f" [SKIP] {dst_rel:<30s} -> already has {len(existing)} images")
        else:
            missing_targets[src_rel] = dst_rel

    if not missing_targets:
        print(" All 17 PlantVillage classes are already populated locally.")
        return

    try:
        # Step A: List the 38 class folders under raw/color to get each folder's git tree SHA
        color_entries = _http_get_json(
            "https://api.github.com/repos/spMohanty/PlantVillage-Dataset/contents/raw/color?ref=master"
        )
        folder_shas = {
            f"raw/color/{e['name']}": e["sha"]
            for e in color_entries
            if isinstance(e, dict) and e.get("type") == "dir" and e.get("sha")
        }

        for src_rel, dst_rel in missing_targets.items():
            sha = folder_shas.get(src_rel)
            if not sha:
                print(f" [WARN] Could not find tree SHA for {src_rel}")
                continue
            tree_data = _http_get_json(
                f"https://api.github.com/repos/spMohanty/PlantVillage-Dataset/git/trees/{sha}"
            )
            filenames = [
                item["path"]
                for item in tree_data.get("tree", [])
                if item.get("type") == "blob"
                and item.get("path", "").lower().endswith((".jpg", ".jpeg", ".png"))
            ]
            if max_per_class > 0:
                filenames = filenames[:max_per_class]

            dst_dir = os.path.join(CROPS_DIR, dst_rel)
            print(f"  -> Downloading {len(filenames)} images into {dst_rel} ...")
            tasks = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
                for fname in filenames:
                    rel_path = f"{src_rel}/{fname}"
                    raw_url = f"https://raw.githubusercontent.com/spMohanty/PlantVillage-Dataset/master/{urllib.parse.quote(rel_path)}"
                    dst_path = os.path.join(dst_dir, os.path.basename(fname))
                    tasks.append(pool.submit(_download_file, raw_url, dst_path))
                done = 0
                failed = 0
                for fut in concurrent.futures.as_completed(tasks):
                    try:
                        fut.result()
                        done += 1
                    except Exception:
                        failed += 1
            print(f"  -> Completed {dst_rel}: {done} downloaded, {failed} failed")
    except Exception as exc:
        print(f" [WARN] PlantVillage fetch error: {exc}")


def fetch_rice_missing():
    print("\n" + "=" * 65)
    print("2. Checking & Fetching Official Rice Leaf Disease Classes")
    print("=" * 65)
    os.makedirs(TEMP_DIR, exist_ok=True)
    for folder_name, url in RICE_URLS.items():
        dst_dir = os.path.join(CROPS_DIR, folder_name)
        os.makedirs(dst_dir, exist_ok=True)
        existing = [f for f in os.listdir(dst_dir) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
        if len(existing) > 0:
            print(f" [SKIP] {folder_name:<30s} -> already has {len(existing)} images")
            continue

        zip_target = os.path.join(TEMP_DIR, os.path.basename(url))
        print(f" [FETCH] Downloading {folder_name} ...")
        _download_file(url, zip_target)
        with zipfile.ZipFile(zip_target, "r") as z:
            for member in z.namelist():
                filename = os.path.basename(member)
                if filename and filename.lower().endswith((".jpg", ".jpeg", ".png")):
                    with z.open(member) as src, open(os.path.join(dst_dir, filename), "wb") as out:
                        shutil.copyfileobj(src, out)
        os.remove(zip_target)
    shutil.rmtree(TEMP_DIR, ignore_errors=True)


def fetch_ip102_pests_from_hf(target_per_class: int = 100):
    """
    Fetches official IP102 pest images from HuggingFace Parquet (liaad/agricultural-data, config=ip102),
    mapping string class names directly from the verified dataset labels.
    """
    print("\n" + "=" * 65)
    print("3. Checking & Fetching IP102 Agricultural Pest Dataset (HuggingFace)")
    print("=" * 65)

    existing_pest_imgs = sum(
        len([f for f in files if f.lower().endswith((".jpg", ".jpeg", ".png"))])
        for _, _, files in os.walk(PESTS_DIR)
    )
    if existing_pest_imgs >= 100:
        print(f" [SKIP] data/pests already contains {existing_pest_imgs} images.")
        return

    import io
    import pyarrow.parquet as pq
    from PIL import Image

    os.makedirs(TEMP_DIR, exist_ok=True)
    parquet_url = "https://huggingface.co/api/datasets/liaad/agricultural-data/parquet/ip102/train/0.parquet"
    parquet_path = os.path.join(TEMP_DIR, "ip102_train_0.parquet")

    try:
        if not os.path.exists(parquet_path):
            print(" [FETCH] Downloading official IP102 Parquet shard (~418 MB)...")
            with _SESSION.get(parquet_url, stream=True, timeout=120) as r:
                r.raise_for_status()
                with open(parquet_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)

        # Map verified IP102 string labels directly to application pest folders
        label_map = {
            "Trialeurodes vaporariorum": "Whitefly",
            "Aleurocanthus spiniferus": "Whitefly",
            "aphids": "Aphid",
            "Aphis citricola Vander Goot": "Aphid",
            "Phyllocnistis citrella Stainton": "Leafminer",
            "cerodonta denticornis": "Leafminer",
            "corn borer": "Corn_Borer",
            "rice leaf roller": "Rice_Leaf_Roller",
            "brown plant hopper": "Brown_Planthopper",
        }

        table = pq.read_table(parquet_path)
        labels_col = table["label"].to_pylist()
        images_col = table["image"].to_pylist()

        counts = {}
        for idx, (lbl, img_dict) in enumerate(zip(labels_col, images_col)):
            app_cls = label_map.get(lbl)
            if not app_cls:
                continue
            if counts.get(app_cls, 0) >= target_per_class:
                continue

            cls_dir = os.path.join(PESTS_DIR, app_cls)
            os.makedirs(cls_dir, exist_ok=True)
            img_bytes = img_dict.get("bytes") if isinstance(img_dict, dict) else None
            if not img_bytes:
                continue
            out_path = os.path.join(cls_dir, f"{app_cls.lower()}_{idx:05d}.jpg")
            with Image.open(io.BytesIO(img_bytes)) as im:
                im.convert("RGB").save(out_path, format="JPEG", quality=92)
            counts[app_cls] = counts.get(app_cls, 0) + 1

        print(" Pest download summary:", counts)
    except Exception as exc:
        print(f" [WARN] HuggingFace IP102 fetch skipped/failed: {exc}")
        print("        Alternative: configure ~/.kaggle/kaggle.json and run:")
        print("        kaggle datasets download -d rtlmhjbn/ip02-dataset -p data/pests --unzip")
    finally:
        shutil.rmtree(TEMP_DIR, ignore_errors=True)


def print_summary():
    print("\n" + "=" * 65)
    print("DATASET INVENTORY SUMMARY")
    print("=" * 65)
    total_crops = 0
    for root, dirs, files in sorted(os.walk(CROPS_DIR)):
        imgs = [f for f in files if f.lower().endswith((".jpg", ".jpeg", ".png"))]
        if imgs:
            rel = os.path.relpath(root, CROPS_DIR)
            total_crops += len(imgs)
            print(f" [CROP] {rel:<32s}: {len(imgs):5d} images")
    print(f" TOTAL CROP IMAGES: {total_crops}")

    total_pests = 0
    for root, dirs, files in sorted(os.walk(PESTS_DIR)):
        imgs = [f for f in files if f.lower().endswith((".jpg", ".jpeg", ".png"))]
        if imgs:
            rel = os.path.relpath(root, PESTS_DIR)
            total_pests += len(imgs)
            print(f" [PEST] {rel:<32s}: {len(imgs):5d} images")
    print(f" TOTAL PEST IMAGES: {total_pests}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Collect official PlantVillage, Rice, and IP102 datasets.")
    parser.add_argument("--summary-only", action="store_true", help="Only print current local inventory.")
    parser.add_argument("--max-per-class", type=int, default=0, help="Cap PlantVillage downloads per missing class (0 = full).")
    parser.add_argument("--max-pests", type=int, default=80, help="Target pest images per class from IP102.")
    args = parser.parse_args()

    if not args.summary_only:
        fetch_plantvillage_missing(max_per_class=args.max_per_class)
        fetch_rice_missing()
        fetch_ip102_pests_from_hf(target_per_class=args.max_pests)
    print_summary()
