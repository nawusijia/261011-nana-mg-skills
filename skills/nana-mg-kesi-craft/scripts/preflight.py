#!/usr/bin/env python3
"""Preflight for nana-mg-kesi-craft without launching renderers or browsers.

Usage:
  python scripts/preflight.py                      # tools only: node, ffmpeg, Chrome
  python scripts/preflight.py --cases-dir DIR      # also check Kesi's teaching cases in DIR
  python scripts/preflight.py --cases-dir DIR --case 3d

Read-only: checks files and tools, never modifies or renders anything.
"""
from __future__ import annotations
import argparse
import json
import os
import shutil
import sys
from pathlib import Path

CASES = {
    "liquid": {
        "folder": "kesi-liquid",
        "files": ["make.sh", "film/scene.js", "film/index.html", "film/cues.json", "film/audio.py", "film/prep_sdf.py", "film/logo_sdf.bin", "harness/render.mjs"],
    },
    "3d": {
        "folder": "kesi-3d",
        "files": ["make.sh", "film/motion.js", "film/index.html", "film/export_cues.cjs", "film/cues.json", "film/audio.py", "film/prep_font.cjs", "film/ruan_font.json", "harness/render.mjs"],
    },
    "iso": {
        "folder": "kesi-iso",
        "files": ["make.sh", "film/motion.js", "film/index.html", "film/export_cues.cjs", "film/cues.json", "film/audio.py", "harness/render.mjs"],
    },
}

CHROME_CANDIDATES = [
    os.environ.get("MG_CHROME", ""),
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    shutil.which("google-chrome") or "",
    shutil.which("chromium") or "",
    shutil.which("chromium-browser") or "",
]


def find_case(cases_dir: Path, which: str) -> Path | None:
    folder = CASES[which]["folder"]
    hits = [p for p in cases_dir.iterdir() if p.is_dir() and p.name.endswith(folder)] if cases_dir.is_dir() else []
    return sorted(hits)[-1] if hits else None


def inspect(cases_dir: Path, which: str) -> bool:
    folder = find_case(cases_dir, which)
    if folder is None:
        print(f"[{which}] CHECK — no folder ending with '{CASES[which]['folder']}' in {cases_dir}")
        return False
    problems = []
    for name in CASES[which]["files"]:
        if not (folder / name).is_file():
            problems.append(f"MISSING {folder / name}")
    if not (folder / "node_modules/three").exists():
        problems.append("THREE_MISSING — install three in the copy, or link existing node_modules (prepare_case.py --node-modules)")
    if not (folder / "film/fonts").is_dir():
        problems.append("LOCAL_FONTS_MISSING — fonts are required locally; do not redistribute")
    cues = folder / "film/cues.json"
    if cues.exists():
        try:
            data = json.loads(cues.read_text(encoding="utf-8"))
            assert isinstance(data, dict) and data, "empty cues"
        except (OSError, ValueError, AssertionError) as e:
            problems.append(f"INVALID_CUES {cues}: {e}")
    if which == "liquid":
        # SDF distance fields must be full-float, not a compressed 8-bit image.
        sdf = folder / "film/logo_sdf.bin"
        if sdf.exists() and sdf.stat().st_size < 100_000:
            problems.append("SDF_TEXTURE_SUSPICIOUSLY_SMALL")
    print(f"[{which}] {folder}:", "PASS" if not problems else "CHECK")
    for v in problems:
        print("   ", v)
    print("   run from an isolated COPY of the example; make.sh writes outputs in its own folder")
    return not problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", choices=["all", *CASES], default="all")
    ap.add_argument("--cases-dir", type=Path, default=None,
                    help="folder that contains Kesi's teaching cases (optional)")
    args = ap.parse_args()
    ok = True
    node = shutil.which("node")
    ffmpeg = shutil.which("ffmpeg")
    chrome = next((c for c in CHROME_CANDIDATES if c and Path(c).is_file()), None)
    for label, yes in [("node", bool(node)), ("ffmpeg", bool(ffmpeg)), ("Chrome/Chromium (or MG_CHROME)", bool(chrome))]:
        print(label, "OK" if yes else "CHECK")
        if not yes:
            ok = False
    if args.cases_dir is None:
        print("cases: skipped (no --cases-dir). Without teaching cases, use route B: original work guided by references/.")
    else:
        for kind in ([*CASES] if args.case == "all" else [args.case]):
            if not inspect(args.cases_dir.resolve(), kind):
                ok = False
    print("ENV_PREFLIGHT", "PASS" if ok else "INCOMPLETE", "(read-only, no render launched)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
