#!/usr/bin/env python3
"""Strip all inline Harold emoji <img> tags from documentation.

Removes:
- Inline <img src="...harold..."> tags (leaves surrounding text)
- Lines that are ONLY whitespace + img tag(s) + whitespace (removes whole line)
- The 64px showcase gallery blocks
- Cleans up double/triple spaces left behind
- Removes empty blockquotes and leftover formatting
"""

import re
import sys
from pathlib import Path


ROOT = Path(__file__).parent.parent

FILES = [
    ROOT / "README.md",
    ROOT / "CONSTITUTION.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "docs/user-guide.md",
    ROOT / "docs/api-reference.md",
    ROOT / "docs/adapter-development.md",
    ROOT / "docs/memes/harold/emoji-reference.md",
    ROOT / "docs/memes/harold/MEME-GALLERY.md",
]

# Match <img src="...harold..." ...> tags (greedy on attributes, but stop at >)
HAROLD_IMG_RE = re.compile(
    r"<img\s+[^>]*harold[^>]*>",
    re.IGNORECASE,
)

# Match the showcase composite image too
SHOWCASE_IMG_RE = re.compile(
    r"<img\s+[^>]*harold-showcase[^>]*>",
    re.IGNORECASE,
)


def strip_file(filepath: Path) -> int:
    """Strip all Harold img tags from a file. Returns count of removals."""
    if not filepath.exists():
        print(f"  SKIP (not found): {filepath}")
        return 0

    text = filepath.read_text(encoding="utf-8")
    original = text
    count = len(HAROLD_IMG_RE.findall(text))

    if count == 0:
        print(f"  SKIP (no tags): {filepath.name}")
        return 0

    # Step 1: Remove img tags
    text = HAROLD_IMG_RE.sub("", text)

    # Step 2: Clean up lines that are now empty or just whitespace/formatting
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()

        # Remove lines that are now just "&nbsp;" or "&nbsp;&nbsp;" etc
        if re.match(r"^(\s*&nbsp;\s*)+$", stripped):
            continue

        # Remove lines that are now just empty HTML tags like <p align="center"></p>
        if re.match(r"^<p[^>]*>\s*</p>$", stripped):
            continue

        # Remove lines that are now just <em>...</em> with only spacing content
        if re.match(r"^<em>\s*(&nbsp;\s*[·]\s*(&nbsp;\s*)?)*</em>$", stripped):
            continue

        # Remove lines that are just ">" (empty blockquote) unless next line continues it
        # We'll handle this in a second pass

        cleaned.append(line)

    text = "\n".join(cleaned)

    # Step 3: Clean up multiple consecutive blank lines (max 2)
    text = re.sub(r"\n{4,}", "\n\n\n", text)

    # Step 4: Clean up double+ spaces within lines (but not leading whitespace)
    lines = text.split("\n")
    final = []
    for line in lines:
        if line.strip():
            # Preserve leading whitespace, collapse internal multiple spaces
            leading = len(line) - len(line.lstrip())
            content = line[leading:]
            content = re.sub(r"  +", " ", content)
            # Remove leading/trailing spaces from content (not indentation)
            content = content.strip()
            line = " " * leading + content
        final.append(line)

    text = "\n".join(final)

    # Step 5: Fix "**text** :" → "**text**:" and similar spacing artifacts
    text = re.sub(r"\*\*\s+:", "**:", text)

    filepath.write_text(text, encoding="utf-8")
    print(f"  ✓ {filepath.name}: removed {count} img tags")
    return count


def main():
    print("Stripping Harold emoji img tags from documentation...")
    print()

    total = 0
    for f in FILES:
        total += strip_file(f)

    print(f"\nDone. Removed {total} img tags across {len(FILES)} files.")


if __name__ == "__main__":
    main()
