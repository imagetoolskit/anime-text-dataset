"""Assemble the static documentation site for GitHub Pages.

The pages in ``docs/`` are written as if they live at the site root, but they
link to repository files (``../LICENSE``, ``../llms.txt``) that sit above
``docs/``. Publishing ``docs/`` directly would break those links, so this script
copies the pages and the referenced repository files into one ``_site`` tree
where every relative link resolves.

Usage:
    python scripts/build_site.py [--base-url https://example.com]
"""
from __future__ import annotations

import argparse
import datetime as dt
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
OUT = ROOT / "_site"

DEFAULT_BASE = "https://muqeet-1138.github.io/anime-text-dataset"

# Files the rendered pages link to with ../<name>. They must sit at the site
# root next to the copied pages.
ROOT_FILES = (
    "LICENSE",
    "NOTICE",
    "README.md",
    "DATASET_CARD.md",
    "CITATION.cff",
    "LICENSE_AUDIT.md",
    "ACKNOWLEDGMENTS.md",
    "CHANGELOG.md",
    "llms.txt",
)

PAGES = (
    ("", "1.0"),
    ("explore.html", "0.8"),
    ("training.html", "0.8"),
    ("commands.html", "0.6"),
    ("CITATION.md", "0.6"),
)


def build(base_url: str) -> None:
    base = base_url.rstrip("/")
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(DOCS, OUT)

    copied = 0
    for name in ROOT_FILES:
        src = ROOT / name
        if src.exists():
            shutil.copy2(src, OUT / name)
            copied += 1

    report = ROOT / "reports" / "final_report.md"
    if report.exists():
        (OUT / "reports").mkdir(exist_ok=True)
        shutil.copy2(report, OUT / "reports" / "final_report.md")

    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    (OUT / "robots.txt").write_text(
        "User-agent: *\nAllow: /\n\nSitemap: " + base + "/sitemap.xml\n",
        encoding="utf-8",
    )

    today = dt.date.today().isoformat()
    entries = "\n".join(
        "  <url>\n"
        f"    <loc>{base}/{path}</loc>\n"
        f"    <lastmod>{today}</lastmod>\n"
        f"    <priority>{priority}</priority>\n"
        "  </url>"
        for path, priority in PAGES
    )
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{entries}\n</urlset>\n",
        encoding="utf-8",
    )

    pages = len(list(OUT.glob("*.html")))
    print(f"site: {OUT}")
    print(f"  html pages: {pages}")
    print(f"  root files copied: {copied}")
    print(f"  base url: {base}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-url", default=DEFAULT_BASE,
                    help="public URL of the site (no trailing slash)")
    args = ap.parse_args()
    build(args.base_url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
