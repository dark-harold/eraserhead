#!/usr/bin/env python3
"""Convert Unicode emoji to inline Harold PNG images in markdown files.

Replaces persona emoji (😐🌑📺✅🌱⚠️) with <img> tags pointing to
the actual Harold face PNGs. Leaves emoji inside code blocks untouched.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

# Emoji → Harold filename mapping
EMOJI_MAP = {
    "😐": "harold-standard",
    "🌑": "harold-dark",
    "📺": "harold-historian",
    "✅": "harold-shipper",
    "🌱": "harold-anemochory",
    "⚠️": "harold-ultra-dark",
}

# Files to process with their relative path to the emoji directory
FILES = {
    ROOT / "README.md": "docs/memes/harold/emoji",
    ROOT / "CONSTITUTION.md": "docs/memes/harold/emoji",
    ROOT / "CONTRIBUTING.md": "docs/memes/harold/emoji",
    ROOT / "docs/user-guide.md": "memes/harold/emoji",
    ROOT / "docs/api-reference.md": "memes/harold/emoji",
    ROOT / "docs/adapter-development.md": "memes/harold/emoji",
    ROOT / "docs/memes/harold/emoji-reference.md": "emoji",
    ROOT / "docs/memes/harold/MEME-GALLERY.md": "emoji",
}


def make_img(name: str, base_path: str, size: int = 20) -> str:
    """Generate an <img> tag for a Harold emoji."""
    return f'<img src="{base_path}/{name}-{size}.png" height="{size}" alt="{name}">'


def replace_in_text(text: str, base_path: str) -> str:
    """Replace emoji in non-code text."""
    for emoji_char, harold_name in EMOJI_MAP.items():
        tag = make_img(harold_name, base_path)
        text = text.replace(emoji_char, tag)
    return text


def process_file(filepath: Path, base_path: str) -> int:
    """Process a markdown file, replacing emoji outside code blocks.
    
    Returns the number of replacements made.
    """
    content = filepath.read_text(encoding="utf-8")
    
    # Count existing emoji
    count_before = sum(content.count(e) for e in EMOJI_MAP)
    
    # Split on fenced code blocks (```...```) and inline code (`...`)
    # Pattern: match fenced blocks first, then inline code
    code_pattern = re.compile(r"(```[\s\S]*?```|`[^`\n]+`)")
    
    parts = code_pattern.split(content)
    result_parts = []
    
    for part in parts:
        if part.startswith("```") or part.startswith("`"):
            # Inside code — leave untouched
            result_parts.append(part)
        else:
            result_parts.append(replace_in_text(part, base_path))
    
    new_content = "".join(result_parts)
    
    if new_content != content:
        filepath.write_text(new_content, encoding="utf-8")
        return count_before
    return 0


def main():
    total = 0
    for filepath, base_path in FILES.items():
        if not filepath.exists():
            print(f"SKIP {filepath.name} (not found)")
            continue
        count = process_file(filepath, base_path)
        print(f"  {filepath.name}: {count} emoji → Harold faces")
        total += count
    
    print(f"\nTotal: {total} emoji converted to inline Harold images")


if __name__ == "__main__":
    main()
