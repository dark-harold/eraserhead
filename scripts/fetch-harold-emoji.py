#!/usr/bin/env python3
"""Fetch and process real Harold photos into Discord-style custom emoji.

# 😐 Harold Photo Emoji Pipeline
Downloads available Harold images, crops the face region, applies
persona-specific color treatments, and generates multi-size PNG emoji.

## Persona Variants (from one source, six treatments):
- harold-standard:   Normal (the classic forced smile)
- harold-dark:       Desaturated + darkened (Dark Harold persona)
- harold-historian:  Warm sepia tone (Internet Historian persona)
- harold-shipper:    Brightened + slight saturation boost (shipping energy)
- harold-anemochory: Green/nature tint (seed dispersal vibes)
- harold-ultra-dark: High contrast + heavy desaturation (maximum paranoia)

## Output Sizes (Discord-style emoji):
- 128px: Full emoji size (Discord native)
- 64px:  Showcase / gallery
- 32px:  Table cells
- 24px:  Headings
- 20px:  Inline text

Attribution: Original stock photos by photographer "Nyul" via Dreamstime.
Subject: András István Arató (b. 1945), Hungarian electrical engineer.
Used as tiny transformative emoji for project commentary/documentation.
See: https://en.wikipedia.org/wiki/Hide_the_Pain_Harold

🌑 Dark Harold reminds us: if you're going to use someone's face as emoji,
at least document it properly.
"""

from __future__ import annotations

import io
import sys
import urllib.request
from pathlib import Path

try:
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps
except ImportError:
    print("ERROR: Pillow is required. Install with: pip install Pillow")
    sys.exit(1)


ROOT = Path(__file__).parent.parent
EMOJI_DIR = ROOT / "docs" / "memes" / "harold" / "emoji"
CACHE_DIR = ROOT / ".cache" / "harold-source"

# Known publicly-accessible Harold images
# The Wikipedia fair-use image (low-res 404x247, the iconic forced smile at computer)
HAROLD_SOURCES = [
    {
        "name": "harold-at-computer",
        "url": "https://upload.wikimedia.org/wikipedia/en/a/a4/Hide_the_Pain_Harold_%28Andr%C3%A1s_Arat%C3%B3%29.jpg",
        "description": "The iconic 'Hide the Pain Harold' stock photo - forced smile at computer",
        "crop_box_pct": (0.22, 0.0, 0.62, 0.85),  # (left%, top%, right%, bottom%) face region
    },
]

# Emoji output sizes in pixels
EMOJI_SIZES = [20, 24, 32, 64, 128]

# Persona color treatment definitions
PERSONA_TREATMENTS: dict[str, dict] = {
    "harold-standard": {
        "description": "Classic Harold - the original forced smile",
        "brightness": 1.0,
        "contrast": 1.05,
        "saturation": 1.0,
        "warmth": 0,
    },
    "harold-dark": {
        "description": "Dark Harold - desaturated, brooding paranoia",
        "brightness": 0.7,
        "contrast": 1.2,
        "saturation": 0.3,
        "warmth": -15,
    },
    "harold-historian": {
        "description": "Internet Historian Harold - warm sepia storyteller",
        "brightness": 1.05,
        "contrast": 1.0,
        "saturation": 0.6,
        "warmth": 30,
        "sepia": True,
    },
    "harold-shipper": {
        "description": "Shipper Harold - bright and optimistic (shipping code)",
        "brightness": 1.15,
        "contrast": 1.05,
        "saturation": 1.2,
        "warmth": 10,
    },
    "harold-anemochory": {
        "description": "Anemochory Harold - nature-tinted seed dispersal vibes",
        "brightness": 1.0,
        "contrast": 1.0,
        "saturation": 0.8,
        "warmth": 0,
        "green_tint": True,
    },
    "harold-ultra-dark": {
        "description": "Ultra Dark Harold - maximum paranoia, assume everything is compromised",
        "brightness": 0.5,
        "contrast": 1.5,
        "saturation": 0.1,
        "warmth": -20,
    },
}


def download_image(url: str, cache_path: Path) -> Image.Image:
    """Download image from URL with caching."""
    if cache_path.exists():
        print(f"  Using cached: {cache_path.name}")
        return Image.open(cache_path)

    print(f"  Downloading: {url}")
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "EraserHead-Harold-Emoji/1.0 (https://github.com/eraserhead; documentation emoji pipeline)"
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()

    # Save to cache
    cache_path.write_bytes(data)

    return Image.open(io.BytesIO(data))


def crop_face(img: Image.Image, crop_pct: tuple[float, float, float, float]) -> Image.Image:
    """Crop to face region and make square.

    crop_pct: (left%, top%, right%, bottom%) as fractions 0.0-1.0
    """
    w, h = img.size
    left = int(w * crop_pct[0])
    top = int(h * crop_pct[1])
    right = int(w * crop_pct[2])
    bottom = int(h * crop_pct[3])

    face = img.crop((left, top, right, bottom))

    # Make square (crop to center square)
    fw, fh = face.size
    if fw != fh:
        size = min(fw, fh)
        offset_x = (fw - size) // 2
        offset_y = (fh - size) // 2
        face = face.crop((offset_x, offset_y, offset_x + size, offset_y + size))

    return face


def apply_warmth(img: Image.Image, warmth: int) -> Image.Image:
    """Adjust color temperature. Positive = warmer, negative = cooler."""
    if warmth == 0:
        return img

    r, g, b = img.split()[:3]

    if warmth > 0:
        # Warmer: boost red, reduce blue
        r = r.point(lambda x: min(255, x + warmth))
        b = b.point(lambda x: max(0, x - warmth // 2))
    else:
        # Cooler: boost blue, reduce red
        b = b.point(lambda x: min(255, x + abs(warmth)))
        r = r.point(lambda x: max(0, x - abs(warmth) // 2))

    if img.mode == "RGBA":
        a = img.split()[3]
        return Image.merge("RGBA", (r, g, b, a))
    return Image.merge("RGB", (r, g, b))


def apply_sepia(img: Image.Image) -> Image.Image:
    """Apply a sepia tone effect."""
    gray = ImageOps.grayscale(img)
    sepia_r = gray.point(lambda x: min(255, int(x * 1.2 + 20)))
    sepia_g = gray.point(lambda x: min(255, int(x * 1.0 + 10)))
    sepia_b = gray.point(lambda x: min(255, int(x * 0.8)))
    return Image.merge("RGB", (sepia_r, sepia_g, sepia_b))


def apply_green_tint(img: Image.Image) -> Image.Image:
    """Apply a subtle green/nature tint."""
    r, g, b = img.split()[:3]
    g = g.point(lambda x: min(255, int(x * 1.15 + 8)))
    r = r.point(lambda x: max(0, int(x * 0.92)))
    b = b.point(lambda x: max(0, int(x * 0.90)))
    return Image.merge("RGB", (r, g, b))


def apply_treatment(img: Image.Image, treatment: dict) -> Image.Image:
    """Apply persona-specific color treatment to an image."""
    result = img.copy()

    # Ensure RGB mode for processing
    if result.mode == "RGBA":
        # Separate alpha for later
        alpha = result.split()[3]
        result = result.convert("RGB")
    else:
        alpha = None
        result = result.convert("RGB")

    # Apply sepia first if specified (replaces colors)
    if treatment.get("sepia"):
        result = apply_sepia(result)

    # Apply green tint if specified
    if treatment.get("green_tint"):
        result = apply_green_tint(result)

    # Brightness
    if treatment["brightness"] != 1.0:
        enhancer = ImageEnhance.Brightness(result)
        result = enhancer.enhance(treatment["brightness"])

    # Contrast
    if treatment["contrast"] != 1.0:
        enhancer = ImageEnhance.Contrast(result)
        result = enhancer.enhance(treatment["contrast"])

    # Saturation
    if treatment["saturation"] != 1.0:
        enhancer = ImageEnhance.Color(result)
        result = enhancer.enhance(treatment["saturation"])

    # Color temperature
    if treatment.get("warmth", 0) != 0:
        result = apply_warmth(result, treatment["warmth"])

    # Restore alpha if present
    if alpha is not None:
        result = result.convert("RGBA")
        result.putalpha(alpha)

    return result


def make_circular_mask(size: int) -> Image.Image:
    """Create a circular mask for Discord-style round emoji."""
    mask = Image.new("L", (size * 4, size * 4), 0)

    # Draw circle using basic pixel operations (no ImageDraw dependency)
    cx, cy = size * 2, size * 2
    radius = size * 2
    for y in range(size * 4):
        for x in range(size * 4):
            if (x - cx) ** 2 + (y - cy) ** 2 <= radius**2:
                mask.putpixel((x, y), 255)

    return mask.resize((size, size), Image.LANCZOS)


def generate_emoji(face: Image.Image, persona: str, treatment: dict) -> dict[int, Image.Image]:
    """Generate all sizes of emoji for a persona."""
    treated = apply_treatment(face, treatment)
    results = {}

    for size in EMOJI_SIZES:
        # High-quality downscale
        emoji = treated.copy()
        emoji = emoji.resize((size, size), Image.LANCZOS)

        # Slight sharpening for small sizes to preserve face detail
        if size <= 32:
            emoji = emoji.filter(ImageFilter.SHARPEN)

        results[size] = emoji

    return results


def main() -> None:
    """Main pipeline: download → crop → treat → resize → save."""
    print("=" * 60)
    print("😐 Harold Photo Emoji Pipeline")
    print("=" * 60)
    print()

    EMOJI_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: Download source images
    print("📥 Step 1: Downloading source images...")
    source_images = []
    for source in HAROLD_SOURCES:
        cache_path = CACHE_DIR / f"{source['name']}.jpg"
        try:
            img = download_image(source["url"], cache_path)
            source_images.append((source, img))
            print(f"  ✓ {source['name']}: {img.size[0]}×{img.size[1]}")
        except Exception as e:
            print(f"  ✗ {source['name']}: {e}")

    if not source_images:
        print("\n🌑 No source images available. Cannot generate emoji.")
        print("   Place Harold images manually in .cache/harold-source/")
        sys.exit(1)

    # Step 2: Crop face regions
    print("\n✂️  Step 2: Cropping face regions...")
    faces = []
    for source, img in source_images:
        face = crop_face(img, source["crop_box_pct"])
        faces.append((source["name"], face))
        print(f"  ✓ {source['name']}: {face.size[0]}×{face.size[1]} (square crop)")

    # Use the first (best) face for all personas
    _, base_face = faces[0]

    # Step 3: Generate persona variants
    print("\n🎨 Step 3: Generating persona variants...")
    total_files = 0
    for persona, treatment in PERSONA_TREATMENTS.items():
        emoji_set = generate_emoji(base_face, persona, treatment)
        print(f"  {persona}: {treatment['description']}")

        for size, emoji_img in emoji_set.items():
            output_path = EMOJI_DIR / f"{persona}-{size}.png"
            emoji_img.save(output_path, "PNG", optimize=True)
            total_files += 1
            print(f"    → {output_path.name} ({size}×{size}px)")

    # Step 4: Generate a 128px showcase composite
    print("\n📸 Step 4: Saving showcase composite...")
    showcase_width = 128 * len(PERSONA_TREATMENTS) + 8 * (len(PERSONA_TREATMENTS) - 1)
    showcase = Image.new("RGBA", (showcase_width, 128), (0, 0, 0, 0))
    x_offset = 0
    for persona in PERSONA_TREATMENTS:
        emoji_128 = Image.open(EMOJI_DIR / f"{persona}-128.png")
        showcase.paste(emoji_128, (x_offset, 0))
        x_offset += 128 + 8

    showcase_path = EMOJI_DIR / "harold-showcase.png"
    showcase.save(showcase_path, "PNG", optimize=True)
    print(f"  ✓ {showcase_path.name} ({showcase_width}×128px)")

    print(f"\n✅ Generated {total_files} emoji files + 1 showcase composite")
    print(f"📁 Output: {EMOJI_DIR.relative_to(ROOT)}/")

    # Step 5: Attribution reminder
    print("\n" + "=" * 60)
    print("📋 ATTRIBUTION NOTICE")
    print("=" * 60)
    print("Original stock photos: © H20.photo / Dreamstime")
    print("Photographer: 'Nyul'")
    print("Subject: András István Arató (b. 1945)")
    print("Usage: Tiny emoji for project documentation commentary")
    print("Info: https://en.wikipedia.org/wiki/Hide_the_Pain_Harold")
    print()
    print("🌑 Dark Harold says: 'At least you documented the attribution.'")


if __name__ == "__main__":
    main()
