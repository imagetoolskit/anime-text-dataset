"""Render the 1200x630 social preview image used by og:image / twitter:image.

Usage:
    python scripts/make_og.py [--out docs/og.png]

Uses the same palette and type pairing as the docs site. Fonts are the
Windows system faces (Georgia, Segoe UI); on other platforms the script
falls back to whatever DejaVu face Pillow can find.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent

W, H = 1200, 630
PAPER = (247, 244, 238)
PAPER_2 = (255, 253, 248)
INK = (28, 36, 48)
SOFT = (91, 102, 117)
TEAL = (15, 118, 110)
TEAL_SOFT = (233, 244, 242)
AMBER = (180, 83, 9)
LINE = (227, 221, 208)

FONT_DIRS = [Path(r"C:\Windows\Fonts"), Path("/usr/share/fonts/truetype"), Path("/Library/Fonts")]


def font(names: list[str], size: int) -> ImageFont.FreeTypeFont:
    for directory in FONT_DIRS:
        for name in names:
            candidate = directory / name
            if candidate.exists():
                return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default(size=size)


SERIF_BOLD = ["georgiab.ttf", "DejaVuSerif-Bold.ttf", "Georgia Bold.ttf"]
SANS = ["segoeui.ttf", "DejaVuSans.ttf", "Arial.ttf"]
SANS_BOLD = ["seguisb.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf"]


def rounded(draw: ImageDraw.ImageDraw, box, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def build(out: Path) -> None:
    img = Image.new("RGB", (W, H), PAPER)

    # Soft corner washes, approximated with translucent ellipses.
    wash = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    wd = ImageDraw.Draw(wash)
    wd.ellipse((-260, -420, 620, 220), fill=(15, 118, 110, 26))
    wd.ellipse((820, -260, 1460, 300), fill=(180, 83, 9, 18))
    img = Image.alpha_composite(img.convert("RGBA"), wash).convert("RGB")
    d = ImageDraw.Draw(img)

    # Brand mark: teal rounded square with a tilted white frame.
    d.rounded_rectangle((72, 64, 118, 110), radius=13, fill=TEAL)
    d.rectangle((85, 78, 105, 96), outline=(255, 255, 255), width=3)

    eyebrow = font(SANS_BOLD, 21)
    d.text((134, 74), "TEXT-ONLY DATASET", font=eyebrow, fill=TEAL)
    d.text((134, 100), "v2.1.0  ·  Hugging Face + GitHub", font=font(SANS, 19), fill=SOFT)

    headline = font(SERIF_BOLD, 84)
    d.text((72, 168), "Large Anime", font=headline, fill=INK)
    d.text((72, 258), "Text Dataset", font=headline, fill=TEAL)

    d.line((72, 380, 1128, 380), fill=LINE, width=2)

    sub = font(SANS, 30)
    d.text((72, 408), "35,766 anime works  ·  2,436,445 structured text rows", font=sub, fill=INK)
    d.text((72, 452), "LLM fine-tuning · instruction tuning · RAG · QA · entity linking",
           font=font(SANS, 23), fill=SOFT)

    # Three metric chips.
    chips = [("317,907", "grounded QA pairs"), ("235,395", "instructions"), ("206,906", "RAG chunks")]
    x = 72
    for value, label in chips:
        width = 300
        rounded(d, (x, 508, x + width, 566), 12, fill=PAPER_2, outline=LINE, width=2)
        d.text((x + 18, 518), value, font=font(SANS_BOLD, 22), fill=TEAL)
        d.text((x + 118, 522), label, font=font(SANS, 17), fill=SOFT)
        x += width + 18

    # Footer.
    d.line((72, 588, 1128, 588), fill=LINE, width=2)
    d.text((72, 600), "dataset.animearray.site", font=font(SANS, 17), fill=SOFT)
    right = "Free 30% preview  ·  mixed-rights, CC0 subset"
    rw = d.textlength(right, font=font(SANS_BOLD, 17))
    d.text((1128 - rw, 600), right, font=font(SANS_BOLD, 17), fill=AMBER)

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG", optimize=True)
    print(f"wrote {out} ({out.stat().st_size / 1024:.0f} KB, {W}x{H})")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(ROOT / "docs" / "og.png"))
    args = ap.parse_args()
    build(Path(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
