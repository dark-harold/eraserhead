#!/usr/bin/env python3
"""Fetch multiple different Harold meme images and resize for docs.

Downloads several distinct Harold photos from public sources,
resizes them to reasonable widths for documentation placement.

Attribution: Original stock photos by photographer "Nyul" via Dreamstime.
Subject: András István Arató (b. 1945), Hungarian electrical engineer.
See: https://en.wikipedia.org/wiki/Hide_the_Pain_Harold
"""

import hashlib
import sys
import urllib.request
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Pillow required: pip install Pillow")
    sys.exit(1)

ROOT = Path(__file__).parent.parent
OUTPUT_DIR = ROOT / "docs" / "memes" / "harold"
CACHE_DIR = ROOT / ".cache" / "harold-source"

# Target width for doc images (height scales proportionally)
TARGET_WIDTH = 400

# Public URLs for different Harold images
# Each: (output_name, url, description)
SOURCES = [
    (
        "harold-laptop",
        "https://upload.wikimedia.org/wikipedia/en/a/a4/"
        "Hide_the_Pain_Harold_%28Andr%C3%A1s_Arat%C3%B3%29.jpg",
        "The classic: Harold at laptop, the original meme photo",
    ),
    (
        "harold-thumbsup",
        "https://i.kym-cdn.com/entries/icons/original/000/016/546/hidethepainharold.jpg",
        "Harold giving thumbs up with the iconic forced smile",
    ),
    (
        "harold-imgflip",
        "https://imgflip.com/s/meme/Hide-the-Pain-Harold.jpg",
        "The iconic close-up meme template",
    ),
    (
        "harold-tedx",
        "https://img.youtube.com/vi/FScfGU7rQaM/maxresdefault.jpg",
        "TEDx Kyiv 2018 — 'Waking up as a meme hero'",
    ),
    (
        "harold-buzzfeed",
        "https://img.youtube.com/vi/a3WnvDtDD2M/hqdefault.jpg",
        "BuzzFeed — 'I Accidentally Became A Meme'",
    ),
    (
        "harold-documentary",
        "https://img.youtube.com/vi/9dOdsv6sYjA/hqdefault.jpg",
        "Documentary: 'The living meme'",
    ),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
}


def download(url: str, dest: Path) -> bool:
    """Download a URL to a file. Returns True on success."""
    if dest.exists():
        print(f"  cached: {dest.name}")
        return True
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
            dest.write_bytes(data)
            print(f"  downloaded: {dest.name} ({len(data):,} bytes)")
            return True
    except Exception as e:
        print(f"  FAILED: {e}")
        return False


def resize_and_save(src: Path, dest: Path, target_width: int) -> bool:
    """Resize image to target width, maintaining aspect ratio."""
    try:
        with Image.open(src) as img:
            if img.mode != "RGB":
                img = img.convert("RGB")
            w, h = img.size
            if w > target_width:
                ratio = target_width / w
                new_h = int(h * ratio)
                img = img.resize((target_width, new_h), Image.Resampling.LANCZOS)
            img.save(dest, "PNG", optimize=True)
            print(f"  -> {dest.name} ({img.size[0]}x{img.size[1]})")
            return True
    except Exception as e:
        print(f"  FAILED resize: {e}")
        return False


def main():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Fetching Harold meme images...\n")

    # Download
    downloaded = []
    for name, url, desc in SOURCES:
        ext = url.rsplit(".", 1)[-1].split("?")[0][:4]
        cache_file = CACHE_DIR / f"{name}.{ext}"
        print(f"[{name}] {desc}")
        if download(url, cache_file):
            downloaded.append((name, cache_file, desc))
        print()

    if not downloaded:
        print("No images downloaded. Check network connectivity.")
        sys.exit(1)

    # Deduplicate by visual hash
    unique = []
    seen_hashes: set[str] = set()
    for name, path, desc in downloaded:
        try:
            with Image.open(path) as img:
                small = img.resize((64, 64)).convert("RGB")
                h = hashlib.md5(small.tobytes()).hexdigest()  # noqa: S324
                if h in seen_hashes:
                    print(f"  SKIP duplicate: {name}")
                    continue
                seen_hashes.add(h)
        except Exception:
            pass
        unique.append((name, path, desc))

    print(f"\n{len(unique)} unique image(s).\n")

    # Resize and save as PNG
    print("Resizing for documentation...")
    results = []
    for name, src_path, desc in unique:
        out_path = OUTPUT_DIR / f"{name}.png"
        if resize_and_save(src_path, out_path, TARGET_WIDTH):
            results.append((name, out_path, desc))

    print(f"\nDone. {len(results)} image(s) in {OUTPUT_DIR}/")
    for name, path, desc in results:
        print(f"  {path.name} ({path.stat().st_size:,} bytes) — {desc}")


if __name__ == "__main__":
    main()
