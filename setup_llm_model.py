"""
KisanDrishti AI: Automated ExecuTorch LLM (.pte) Provisioner for Raspberry Pi 5
Downloads llama3_2_1b_instruct_8da4w_xnnpack.pte from the project's GitHub Release
when not already present locally in models/.
"""
import hashlib
import os
import sys
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")
PTE_FILENAME = "llama3_2_1b_instruct_8da4w_xnnpack.pte"
DEFAULT_RELEASE_URL = (
    "https://github.com/AkshayaSrelekaPS/kisandrishti-ai/releases/download/"
    f"v1.0-models/{PTE_FILENAME}"
)
EXPECTED_MIN_BYTES = 750_000_000


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def ensure_pte_model(url: str = None) -> str:
    os.makedirs(MODELS_DIR, exist_ok=True)
    target = os.path.join(MODELS_DIR, PTE_FILENAME)
    if os.path.exists(target) and os.path.getsize(target) >= EXPECTED_MIN_BYTES:
        print(f"OK: {PTE_FILENAME} already present ({os.path.getsize(target) / (1024**2):.1f} MB).")
        return target

    download_url = url or os.environ.get("KISANDRISHTI_PTE_URL", DEFAULT_RELEASE_URL)
    part_path = target + ".part"
    print(f"Downloading ExecuTorch model from:\n  {download_url}")
    req = urllib.request.Request(download_url, headers={"User-Agent": "KisanDrishti-Setup/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp, open(part_path, "wb") as out:
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        last_pct = -1
        while True:
            buf = resp.read(1024 * 1024)
            if not buf:
                break
            out.write(buf)
            done += len(buf)
            if total > 0:
                pct = int(done * 100 / total)
                if pct >= last_pct + 5 or pct == 100:
                    print(f"  Progress: {pct}% ({done // (1024*1024)} / {total // (1024*1024)} MB)", flush=True)
                    last_pct = pct

    if os.path.getsize(part_path) < EXPECTED_MIN_BYTES:
        raise RuntimeError(f"Downloaded file too small ({os.path.getsize(part_path)} bytes); check URL.")
    os.replace(part_path, target)
    print(f"Saved: {target} ({os.path.getsize(target) / (1024**2):.1f} MB)")
    return target


if __name__ == "__main__":
    ensure_pte_model(sys.argv[1] if len(sys.argv) > 1 else None)
