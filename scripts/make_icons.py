"""Generate the favicon set and web app manifest for the docs site.

The mark is the same isometric cube used in the site navigation: a teal tile
with a white cube, drawn at 1024px and downsampled so 16px stays legible.

Usage:
    python scripts/make_icons.py

Writes to docs/ (the published root) and mirrors the two files the Space needs
into hf_space/.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SPACE = ROOT / "hf_space"

TEAL = (15, 118, 110)
TEAL_TOP = (63, 145, 139)
TEAL_LEFT = (34, 129, 122)
WHITE = (255, 255, 255)

SUPERSAMPLE = 1024
BASE = 64  # design grid

# Cube geometry on a 64-unit grid.
TOP = [(32, 8), (52, 20), (32, 32), (12, 20)]
LEFT = [(12, 20), (32, 32), (32, 56), (12, 44)]
RIGHT = [(52, 20), (32, 32), (32, 56), (52, 44)]
OUTLINE = [(32, 8), (52, 20), (52, 44), (32, 56), (12, 44), (12, 20)]
INNER = [((32, 32), (12, 20)), ((32, 32), (52, 20)), ((32, 32), (32, 56))]

SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="Large Anime Text Dataset">
  <rect width="64" height="64" rx="14" fill="#0f766e"/>
  <g stroke="#ffffff" stroke-width="3.4" stroke-linejoin="round" stroke-linecap="round">
    <path d="M32 8 L52 20 L32 32 L12 20 Z" fill="#3f918b"/>
    <path d="M12 20 L32 32 L32 56 L12 44 Z" fill="#22817a"/>
    <path d="M52 20 L32 32 L32 56 L52 44 Z" fill="#0f766e"/>
    <path d="M32 8 L52 20 L52 44 L32 56 L12 44 L12 20 Z" fill="none"/>
    <path d="M32 32 L12 20 M32 32 L52 20 M32 32 L32 56" fill="none"/>
  </g>
</svg>
"""

MANIFEST = """{
  "name": "Large Anime Text Dataset",
  "short_name": "Anime Dataset",
  "description": "Text-only anime corpus: 35,766 works and 2,436,445 structured text rows for LLM fine-tuning, RAG, QA and entity linking.",
  "start_url": "./",
  "scope": "./",
  "display": "browser",
  "background_color": "#f7f4ee",
  "theme_color": "#f7f4ee",
  "icons": [
    { "src": "icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "icon-512.png", "sizes": "512x512", "type": "image/png" },
    { "src": "favicon.svg", "sizes": "any", "type": "image/svg+xml" }
  ]
}
"""


def scale(points, factor: float, offset: float = 0.0):
    return [(x * factor + offset, y * factor + offset) for x, y in points]


def render(size: int, radius_ratio: float = 14 / 64, padding: float = 0.0) -> Image.Image:
    """Draw the tile at `size`, optionally inset for apple-touch/maskable icons."""
    inset = size * padding
    art = size - inset * 2
    factor = art / BASE

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    if padding:
        d.rectangle((0, 0, size, size), fill=TEAL)
    else:
        d.rounded_rectangle((0, 0, size - 1, size - 1), radius=size * radius_ratio, fill=TEAL)

    def poly(points, fill):
        d.polygon(scale(points, factor, inset), fill=fill)

    poly(TOP, TEAL_TOP)
    poly(LEFT, TEAL_LEFT)
    poly(RIGHT, TEAL)

    width = max(1, round(3.4 * factor))
    d.line(scale(OUTLINE + [OUTLINE[0]], factor, inset), fill=WHITE, width=width, joint="curve")
    for start, end in INNER:
        d.line([scale([start], factor, inset)[0], scale([end], factor, inset)[0]],
               fill=WHITE, width=width)
    return img


def main() -> int:
    DOCS.mkdir(exist_ok=True)

    (DOCS / "favicon.svg").write_text(SVG, encoding="utf-8")
    (DOCS / "site.webmanifest").write_text(MANIFEST, encoding="utf-8")

    master = render(SUPERSAMPLE)
    for size in (16, 32, 48, 64, 128, 192, 512):
        master.resize((size, size), Image.LANCZOS).save(DOCS / f"icon-{size}.png", "PNG", optimize=True)

    apple = render(512, padding=0.10)
    apple.resize((180, 180), Image.LANCZOS).save(DOCS / "apple-touch-icon.png", "PNG", optimize=True)

    # Multi-resolution .ico from the 256px master.
    ico = master.resize((256, 256), Image.LANCZOS)
    ico.save(DOCS / "favicon.ico", format="ICO",
             sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])

    # The Space is a single page; it needs the SVG and the ICO only.
    SPACE.mkdir(exist_ok=True)
    shutil.copy2(DOCS / "favicon.svg", SPACE / "favicon.svg")
    shutil.copy2(DOCS / "favicon.ico", SPACE / "favicon.ico")

    for name in ("favicon.svg", "favicon.ico", "apple-touch-icon.png",
                 "icon-192.png", "icon-512.png", "site.webmanifest"):
        path = DOCS / name
        print(f"  {name:<22} {path.stat().st_size / 1024:>6.1f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
