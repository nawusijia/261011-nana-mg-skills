#!/usr/bin/env python3
"""Evidence-only visual review gate for motion-graphics projects.

This does NOT evaluate visual quality or confirm a human/agent really saw the
images. It prevents "all green" reports based only on ffprobe / blackdetect.
Real screenshot viewing and honest human/agent visual judgement are mandatory.

Commands:
  python visual_gate.py --init path/to/PROJECT
  python visual_gate.py --check path/to/PROJECT
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

MIN_NOTE = 10


def path_inside(project: Path, rel: str, label: str, problems: list[str]) -> Path | None:
    if not isinstance(rel, str) or not rel.strip():
        problems.append(f"{label}: missing project-local relative path")
        return None
    if Path(rel).is_absolute() or ":" in rel or "\\" in rel:
        problems.append(f"{label}: must be a project-local POSIX-style relative path")
        return None
    target = (project / rel).resolve()
    if not target.is_relative_to(project):
        problems.append(f"{label}: path escapes project")
        return None
    if not target.is_file() or target.stat().st_size <= 0:
        problems.append(f"{label}: actual file missing or empty ({rel})")
        return None
    return target


def note(value: object, label: str, problems: list[str], minimum: int = MIN_NOTE) -> None:
    if not isinstance(value, str) or len(value.strip()) < minimum:
        problems.append(f"{label}: must describe a real specific visual observation (min {minimum} chars)")


def image_file(path: Path, label: str, problems: list[str]) -> tuple[int, int] | None:
    try:
        from PIL import Image
        with Image.open(path) as im:
            if im.width < 320 or im.height < 180:
                problems.append(f"{label}: image too small to inspect ({im.size})")
            size = im.size
            im.verify()
            return size
    except ImportError:
        # Do not claim image verification if Pillow is unavailable.
        problems.append("Pillow required to verify actual screenshot image files")
    except Exception as exc:
        problems.append(f"{label}: invalid image file ({exc})")


def load_record(project: Path) -> tuple[dict | None, list[str]]:
    problems: list[str] = []
    f = project / "visual-review.json"
    if not f.is_file():
        return None, ["visual-review.json does not exist (run --init)"]
    try:
        record = json.loads(f.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return None, [f"visual-review.json unreadable: {exc}"]
    if not isinstance(record, dict):
        return None, ["visual-review.json must be an object"]
    return record, problems


def check_project(project: Path) -> tuple[bool, list[str]]:
    problems: list[str] = []
    if not project.is_dir():
        return False, [f"project does not exist: {project}"]
    record, errors = load_record(project)
    problems.extend(errors)
    if record is None:
        return False, problems
    if record.get("schema_version") != 1:
        problems.append("schema_version must be 1")
    note(record.get("reviewer"), "reviewer", problems, minimum=2)
    note(record.get("self_assessment"), "self_assessment", problems, minimum=10)
    if record.get("self_assessment") != "ready_for_user_review":
        problems.append("self_assessment must be exactly ready_for_user_review (never 'passed')")
    blockers = record.get("open_blockers")
    if not isinstance(blockers, list):
        problems.append("open_blockers must be a list")
    elif blockers:
        problems.append(f"{len(blockers)} unresolved visual blockers remain; may NOT report ready")
    rounds = record.get("rounds", [])
    if not isinstance(rounds, list):
        rounds = []
        problems.append("rounds must be a list")
    if len(rounds) < 3:
        problems.append("at least 3 actual image-viewing review rounds required (initial, revision, final)")
    images: dict[tuple[str, str], tuple[Path, dict]] = {}
    defects: set[tuple[str, str]] = set()
    version_files: set[str] = set()
    for ri, rd in enumerate(rounds):
        label = f"rounds[{ri}]"
        if not isinstance(rd, dict):
            problems.append(f"{label}: not an object")
            continue
        round_id = rd.get("id")
        if not isinstance(round_id, str) or not round_id.strip():
            problems.append(f"{label}.id missing")
            round_id = str(ri)
        version = rd.get("version")
        note(version, f"{label}.version", problems, minimum=2)
        video = rd.get("video")
        vf = path_inside(project, video, f"{label}.video", problems)
        if vf:
            version_files.add(str(vf))
            if vf.suffix.lower() not in (".mp4", ".mov", ".mkv", ".webm"):
                problems.append(f"{label}.video: not a video file")
        note(rd.get("summary"), f"{label}.summary", problems, minimum=15)
        if rd.get("actually_viewed") is not True:
            problems.append(f"{label}.actually_viewed must be true ONLY after viewing the images")
        shots = rd.get("shots", [])
        found_detail = False
        found_sequence = False
        if not isinstance(shots, list) or len(shots) < 2:
            problems.append(f"{label}.shots: need >=2 actual screenshots per review round")
            continue
        for si, shot in enumerate(shots):
            label_s = f"{label}.shots[{si}]"
            if not isinstance(shot, dict):
                problems.append(f"{label_s} not an object")
                continue
            path = path_inside(project, shot.get("image"), f"{label_s}.image", problems)
            if path:
                size = image_file(path, label_s, problems)
                images[(str(round_id), shot["image"])] = path, shot
            else:
                size = None
            kind = shot.get("kind")
            if kind not in ("overview", "detail", "sequence"):
                problems.append(f"{label_s}.kind must be overview/detail/sequence")
            if kind == "detail" and size is not None:
                if max(size) >= 760 and min(size) >= 480:
                    found_detail = True
                else:
                    problems.append(f"{label_s}: detail image too small for visual inspection")
            if kind == "sequence" and size is not None:
                found_sequence = True
            focus = shot.get("focus")
            note(focus, f"{label_s}.focus", problems, minimum=3)
            note(shot.get("observation"), f"{label_s}.observation", problems, minimum=15)
            timestamp = shot.get("time_seconds")
            if not isinstance(timestamp, (int, float)) or isinstance(timestamp, bool) or not math.isfinite(timestamp) or timestamp < 0:
                problems.append(f"{label_s}.time_seconds must be an actual nonnegative video timestamp")
            finding = shot.get("finding")
            if finding not in ("defect", "ok", "uncertain"):
                problems.append(f"{label_s}.finding must be defect/ok/uncertain")
            if finding in ("defect", "uncertain"):
                defects.add((str(round_id), str(shot.get("image"))))
        if not found_detail:
            problems.append(f"{label}: no high-resolution close-up was inspected")
        if ri == len(rounds)-1 and not found_sequence:
            problems.append(f"{label}: final round needs an actual frame-sequence/contact-sheet image")

    if len(version_files) < 2:
        problems.append("screenshots must come from >=2 distinct project-local video versions")

    fixes = record.get("fixes", [])
    if not isinstance(fixes, list):
        problems.append("fixes must be a list")
        fixes = []
    if not fixes:
        problems.append("at least 1 evidence-backed discovered problem -> code change -> rerender comparison required")
    addressed: set[tuple[str, str]] = set()
    for i, fx in enumerate(fixes):
        label = f"fixes[{i}]"
        if not isinstance(fx, dict):
            problems.append(f"{label}: not an object")
            continue
        note(fx.get("problem"), f"{label}.problem", problems, minimum=15)
        note(fx.get("code_or_asset_change"), f"{label}.code_or_asset_change", problems, minimum=15)
        note(fx.get("visual_result"), f"{label}.visual_result", problems, minimum=15)
        b = (str(fx.get("before_round")), str(fx.get("before_image")))
        a = (str(fx.get("after_round")), str(fx.get("after_image")))
        if b not in images or a not in images:
            problems.append(f"{label}: before/after images must be referenced in rounds[*].shots")
            continue
        if b[0] == a[0]:
            problems.append(f"{label}: before and after must be in different review rounds")
        if b not in defects:
            problems.append(f"{label}: before screenshot must actually be marked defect/uncertain")
        else:
            addressed.add(b)
        old_img, old = images[b]
        new_img, new = images[a]
        if old.get("focus") != new.get("focus"):
            problems.append(f"{label}: before/after must inspect the same camera target/focus")
        if abs(old.get("time_seconds", -100) - new.get("time_seconds", -200)) > 0.067:
            problems.append(f"{label}: before/after must compare essentially the same timestamp (<=2 frames)")
        if hashlib.sha256(old_img.read_bytes()).digest() == hashlib.sha256(new_img.read_bytes()).digest():
            problems.append(f"{label}: before/after screenshots are byte-for-byte identical; no visible rerender evidence")
        if new.get("finding") != "ok":
            problems.append(f"{label}: after screenshot still marked defect/uncertain; revision not verified")
    unresolved = defects - addressed
    for round_id, rel in sorted(unresolved):
        problems.append(f"unresolved visual finding: round={round_id} screenshot={rel}")

    last_round = rounds[-1] if rounds else {}
    final_video = record.get("final_video")
    if isinstance(last_round, dict) and final_video != last_round.get("video"):
        problems.append("final_video must be the video inspected in the last review round")
    path_inside(project, final_video, "final_video", problems)
    return not problems, problems


def create_template(project: Path) -> int:
    if not project.is_dir():
        print(f"PROJECT_NOT_FOUND — initialize review only inside an existing project: {project}")
        return 2
    target = project / "visual-review.json"
    if target.exists():
        print(f"REFUSING overwrite of existing {target}")
        return 2
    template = {
        "_instructions": "MANUAL observations ONLY after actual rendered images are opened. Never auto-fill subjective verdicts. See references/visual-review-loop.md.",
        "schema_version": 1,
        "reviewer": "",
        "self_assessment": "visual_not_reviewed",
        "final_video": "",
        "open_blockers": ["No image review has been completed yet"],
        "rounds": [
            {"id": "initial", "version": "", "video": "", "actually_viewed": False,
             "summary": "", "shots": [
                 {"image": "", "time_seconds": 0, "focus": "", "observation": "", "finding": "uncertain"},
                 {"image": "", "time_seconds": 0, "focus": "", "observation": "", "finding": "uncertain"}]},
            {"id": "revised", "version": "", "video": "", "actually_viewed": False, "summary": "",
             "shots": [
                 {"image": "", "time_seconds": 0, "focus": "", "observation": "", "finding": "uncertain"},
                 {"image": "", "time_seconds": 0, "focus": "", "observation": "", "finding": "uncertain"}]},
            {"id": "final", "version": "", "video": "", "actually_viewed": False, "summary": "",
             "shots": [
                 {"image": "", "time_seconds": 0, "focus": "", "observation": "", "finding": "uncertain"},
                 {"image": "", "time_seconds": 0, "focus": "", "observation": "", "finding": "uncertain"}]}
        ],
        "fixes": [
            {"problem": "", "before_round": "initial", "before_image": "",
             "code_or_asset_change": "", "after_round": "revised", "after_image": "",
             "visual_result": ""}
        ]
    }
    for ri, rd in enumerate(template["rounds"]):
        rd["shots"][0]["kind"] = "detail"
        rd["shots"][1]["kind"] = "sequence" if ri == 2 else "overview"
    target.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
    (project / "visual-qa").mkdir(exist_ok=True)
    print(f"CREATED_EMPTY_REVIEW_TEMPLATE {target}")
    print("VISUAL_NOT_REVIEWED — screenshots must be genuinely opened and reviewed")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Evidence-only visual QA gate; NEVER an aesthetics pass")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--init", type=Path)
    mode.add_argument("--check", type=Path)
    args = p.parse_args()
    if args.init is not None:
        return create_template(args.init.resolve())
    good, problems = check_project(args.check.resolve())
    if good:
        print("EVIDENCE_READY_AWAITING_USER — structural evidence complete; visual quality NOT automatically verified")
        return 0
    print("VISUAL_EVIDENCE_INCOMPLETE — do NOT say the film visually passed:")
    for problem in problems:
        print("  -", problem)
    return 1


if __name__ == "__main__":
    sys.exit(main())
