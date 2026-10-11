#!/usr/bin/env python3
"""Copy one Kesi teaching case into a NEW project folder, preserving the original.

Run:
  python scripts/prepare_case.py --cases-dir DIR --case 3d --name 3d-study-copy [--dest PARENT] [--node-modules PATH]

No rendering. Copies source files, not finished media. Never overwrites an existing folder.
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

CASES = {"liquid": "kesi-liquid", "3d": "kesi-3d", "iso": "kesi-iso"}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cases-dir", required=True, type=Path, help="folder that contains Kesi's teaching cases")
    p.add_argument("--case", required=True, choices=CASES)
    p.add_argument("--name", required=True, help="new folder basename")
    p.add_argument("--dest", type=Path, default=None, help="parent folder for the copy (default: --cases-dir)")
    p.add_argument("--node-modules", type=Path, default=None, help="existing node_modules to link instead of reinstalling")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    name = args.name
    if name in (".", "..") or any(x in name for x in ("/", "\\", ":")) or not name.strip():
        p.error("--name must be a safe new folder basename")
    cases_dir = args.cases_dir.resolve()
    hits = sorted(q for q in cases_dir.iterdir() if q.is_dir() and q.name.endswith(CASES[args.case])) if cases_dir.is_dir() else []
    if not hits:
        print("MISSING source case folder ending with", CASES[args.case], "in", cases_dir)
        return 2
    src = hits[-1]
    dst = (args.dest.resolve() if args.dest else cases_dir) / name
    deps = args.node_modules.resolve() if args.node_modules else None
    if deps is not None and not deps.is_dir():
        print("MISSING node_modules:", deps)
        return 2
    if dst.exists() or dst.is_symlink():
        print("DESTINATION_EXISTS; refusing to overwrite:", dst)
        return 3
    print("SOURCE READ ONLY", src)
    print("NEW", dst)
    if args.dry_run:
        print("DRY_RUN_PASS; would copy project sources and fonts" + (", link shared node_modules" if deps else ""))
        return 0
    try:
        dst.mkdir(parents=False, exist_ok=False)
        shutil.copytree(src / "film", dst / "film",
                        ignore=shutil.ignore_patterns("out", "*.mp4", "*.wav", "*.log", "audio_spec.png"))
        (dst / "film/out").mkdir(exist_ok=True)
        shutil.copytree(src / "harness", dst / "harness")
        shutil.copy2(src / "make.sh", dst / "make.sh")
        if deps is not None:
            link = dst / "node_modules"
            try:
                os.symlink(deps, link, target_is_directory=True)
            except (OSError, NotImplementedError):
                if os.name == "nt":
                    res = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(deps)],
                                         capture_output=True, text=True, errors="replace")
                    if res.returncode:
                        print("JUNCTION_REQUIRED:", res.stdout, res.stderr)
                        return 4
                else:
                    raise
    except Exception as exc:
        print("COPY_INCOMPLETE", exc, "; inspect target without touching source")
        return 5
    print("PREPARED", dst)
    print("RUN from clone:", dst / "make.sh")
    print("No font files should be distributed to users.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
