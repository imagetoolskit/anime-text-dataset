"""SHA-256 checksums for every release asset.

`checksums.json` and the `.sha256` sidecar files are derived artifacts: they are
regenerated on every run and must not be listed inside the manifest they belong
to, otherwise a second run records a hash for the previous manifest and the
result can never verify. They are excluded here, and the manifest records the
files it actually covers.
"""

import hashlib
import json

from ..db import ROOT, connect, cp_set, log

EXPORT_DIR = ROOT / "exports"
SKIP = {"checksums.json"}


def _sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def run() -> int:
    results = []
    for p in sorted(EXPORT_DIR.iterdir()):
        if not p.is_file():
            continue
        if p.name in SKIP or p.name.endswith(".sha256"):
            continue
        digest = _sha256(p)
        (EXPORT_DIR / f"{p.name}.sha256").write_text(
            f"{digest}  {p.name}\n", encoding="utf-8", newline="\n")
        results.append({"file": p.name, "bytes": p.stat().st_size, "sha256": digest})

    manifest = EXPORT_DIR / "checksums.json"
    manifest.write_text(json.dumps({
        "algorithm": "sha256",
        "files_covered": len(results),
        "excluded": sorted(SKIP) + ["*.sha256"],
        "files": results,
    }, indent=2), encoding="utf-8", newline="\n")

    conn = connect()
    cp_set(conn, "checksums_done", True)
    log(conn, "checksums", f"files={len(results)}")
    print(f"checksums written for {len(results)} files")
    conn.close()
    return 0
