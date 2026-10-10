"""
Bitewise — Dataset Downloader
==============================
Downloads all verified datasets into data/raw/ and unzips them.
Requires a free Kaggle account (https://www.kaggle.com/account → Create New Token).

Usage:
    python scripts/download_datasets.py

If you don't have ~/.kaggle/kaggle.json yet, the script will prompt you
to enter your Kaggle username and API key, then create the file for you.
"""

import json
import os
import sys
import zipfile
import glob
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

DATASETS = [
    {
        "slug": "ashishjangra27/swiggy-restaurants-dataset",
        "desc": "Swiggy Restaurants (100K+ restaurants, CC0)",
        "folder": "swiggy-restaurants-dataset",
    },
    {
        "slug": "abhijitdahatonde/27000-indian-restaurant-dataset",
        "desc": "27,000+ Indian Restaurants (CC0)",
        "folder": "27000-indian-restaurant-dataset",
    },
    {
        "slug": "nehaprabhavalkar/indian-food-101",
        "desc": "Indian Food 101 — 255 dish taxonomy",
        "folder": "indian-food-101",
    },
    {
        "slug": "danofer/india-census",
        "desc": "India Census 2011 — 640 districts (CC0)",
        "folder": "india-census",
    },
    {
        "slug": "nelgiriyewithana/indian-weather-repository-daily-snapshot",
        "desc": "Indian Weather Repository (daily, optional)",
        "folder": "indian-weather-repository-daily-snapshot",
    },
]


def setup_kaggle_credentials():
    """Ensure ~/.kaggle/kaggle.json exists."""
    kaggle_dir = Path.home() / ".kaggle"
    cred_file = kaggle_dir / "kaggle.json"

    if cred_file.exists():
        print(f"[OK] Kaggle credentials found at {cred_file}")
        return True

    print("=" * 60)
    print("  Kaggle API credentials not found.")
    print("  You need a free Kaggle account to download datasets.")
    print()
    print("  Steps:")
    print("  1. Go to https://www.kaggle.com/settings")
    print("  2. Scroll to 'API' section")
    print("  3. Click 'Create New Token'")
    print("  4. A kaggle.json file will download")
    print("  5. Enter the username and key from that file below")
    print("=" * 60)
    print()

    username = input("Kaggle username: ").strip()
    key = input("Kaggle API key:  ").strip()

    if not username or not key:
        print("[ERROR] Username and key cannot be empty.")
        return False

    kaggle_dir.mkdir(parents=True, exist_ok=True)
    cred_file.write_text(json.dumps({"username": username, "key": key}))

    # Kaggle CLI requires restricted permissions on Linux/Mac; on Windows this is fine
    print(f"[OK] Saved credentials to {cred_file}")
    return True


def download_dataset(slug: str, dest_dir: Path):
    """Download a Kaggle dataset using the kaggle CLI."""
    import subprocess

    python_exe = sys.executable
    cmd = [
        python_exe, "-m", "kaggle",
        "datasets", "download",
        "-d", slug,
        "-p", str(dest_dir),
    ]
    print(f"  Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  [ERROR] {result.stderr.strip()}")
        return False
    print(f"  {result.stdout.strip()}")
    return True


def unzip_all(directory: Path):
    """Unzip all .zip files in directory."""
    for zf in directory.glob("*.zip"):
        print(f"  Extracting {zf.name} ...")
        with zipfile.ZipFile(zf, "r") as z:
            z.extractall(directory)
        print(f"  [OK] Extracted {len(zipfile.ZipFile(zf).namelist())} files")


def count_csv_rows(directory: Path):
    """Print row counts for all CSVs in directory."""
    csv_files = list(directory.glob("*.csv"))
    if not csv_files:
        print("  No CSV files found.")
        return

    for csv_file in csv_files:
        try:
            with open(csv_file, "r", encoding="utf-8", errors="replace") as f:
                lines = sum(1 for _ in f) - 1  # subtract header
            size_mb = csv_file.stat().st_size / (1024 * 1024)
            print(f"  {csv_file.name}: {lines:,} rows, {size_mb:.1f} MB")
        except Exception as e:
            print(f"  {csv_file.name}: [ERROR reading] {e}")


def main():
    print()
    print("=" * 60)
    print("  BITEWISE — Dataset Downloader")
    print("=" * 60)
    print(f"  Download directory: {RAW_DIR}")
    print()

    # Step 1: Credentials
    if not setup_kaggle_credentials():
        print("\n[ABORT] Cannot proceed without Kaggle credentials.")
        sys.exit(1)

    # Step 2: Download each dataset
    print()
    for i, ds in enumerate(DATASETS, 1):
        print(f"\n[{i}/{len(DATASETS)}] {ds['desc']}")
        print(f"  Kaggle: {ds['slug']}")
        success = download_dataset(ds["slug"], RAW_DIR)
        if not success:
            print(f"  [SKIP] Failed to download {ds['slug']}")

    # Step 3: Unzip
    print("\n" + "=" * 60)
    print("  Extracting zip files...")
    print("=" * 60)
    unzip_all(RAW_DIR)

    # Step 4: Verify
    print("\n" + "=" * 60)
    print("  Verification — CSV row counts")
    print("=" * 60)
    count_csv_rows(RAW_DIR)

    # Step 5: Summary
    print("\n" + "=" * 60)
    print("  All files in data/raw/:")
    print("=" * 60)
    for f in sorted(RAW_DIR.iterdir()):
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"  {f.name:50s} {size_mb:8.2f} MB")

    print()
    print("  Done! Your datasets are ready in:")
    print(f"  {RAW_DIR}")
    print()
    print("  Next step: Run the menu preprocessing script")
    print("  python -m scripts.prepare_zomato_data")
    print()


if __name__ == "__main__":
    main()
