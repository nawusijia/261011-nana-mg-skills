#!/usr/bin/env python3
"""Tests ONLY evidence structure, NEVER aesthetics or actual visual judgement."""
from __future__ import annotations
import json
import tempfile
from pathlib import Path
from PIL import Image
from visual_gate import check_project, create_template


def main():
    with tempfile.TemporaryDirectory(prefix="nana-visualgate-test-") as tmp:
        project = Path(tmp)
        assert create_template(project) == 0
        ok, problems = check_project(project)
        assert not ok and problems, "an empty automatic template MUST be rejected"
        assert any("round" in p for p in problems)
        assert create_template(project) == 2, "must not overwrite user review"
        print("REJECT_EMPTY_REVIEW: PASS")

        def img(name, rgb):
            p = project / "visual-qa" / name
            Image.new("RGB", (960, 540), rgb).save(p)
            return "visual-qa/" + name

        i1 = img("v1-5.5.png", (150, 70, 65))
        i1b = img("v1-8.png", (140, 90, 70))
        i2 = img("v2-5.5.png", (100, 80, 65))
        i2b = img("v2-8.png", (110, 80, 70))
        i3 = img("v3-5.5.png", (110, 81, 66))
        i3b = img("v3-8.png", (109, 82, 70))
        for name in ("v1.mp4", "v2.mp4", "v3.mp4"):
            (project / name).write_bytes(b"MOCK_VIDEO_FOR_STRUCTURAL_TEST_ONLY")

        def shot(path, time, focus, finding, observation, kind=None):
            return {"image": path, "kind": kind or ("detail" if focus=="windmill rotation" else "overview"),
                    "time_seconds": time, "focus": focus, "finding": finding, "observation": observation}

        def rd(name, video, shots, summary):
            return {"id": name, "version": name, "video": video, "actually_viewed": True,
                    "shots": shots, "summary": summary}

        record = {
            "schema_version": 1, "reviewer": "agent-under-test",
            "self_assessment": "ready_for_user_review",
            "final_video": "v3.mp4", "open_blockers": [],
            "rounds": [
                rd("initial", "v1.mp4", [
                    shot(i1, 5.5, "windmill rotation", "defect",
                         "Mock-review fixture: windmill blades appear to flicker under motion."),
                    shot(i1b, 8.0, "final poster", "ok",
                         "Mock-review fixture: type and hero composition visibly clear.")],
                   "Fixture initial review has an example defect and a separate passing image."),
                rd("revised", "v2.mp4", [
                    shot(i2, 5.5, "windmill rotation", "ok",
                         "Fixture corrected windmill overlapping blades and inspected screenshot."),
                    shot(i2b, 8.0, "final poster", "ok",
                         "Fixture second review shows readable type and clearly framed subject.")],
                   "Fixture revised review includes equal-angle evidence of a change."),
                rd("final", "v3.mp4", [
                    shot(i3, 5.5, "windmill rotation", "ok",
                         "Fixture final review sees stable colors in the same model closeup."),
                    shot(i3b, 8.0, "final poster", "ok",
                         "Fixture final output confirms a clean layout in this synthetic case.", "sequence")],
                   "Fixture final review has distinct image and video output evidence.")
            ],
            "fixes": [{
                "problem": "Two paper windmill blades appear overlapped in mock screenshot.",
                "before_round": "initial", "before_image": i1,
                "code_or_asset_change": "Mock change: replace coplanar blades by separated thickness meshes.",
                "after_round": "revised", "after_image": i2,
                "visual_result": "Mock after screenshot shows a visibly different image and alignment."
            }]
        }

        review = project / "visual-review.json"
        review.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        good, reasons = check_project(project)
        assert good, reasons
        print("EVIDENCE_STRUCTURE_READY, NO AESTHETIC_VERDICT: PASS")

        record["rounds"][1]["shots"][0]["image"] = i1
        record["fixes"][0]["after_image"] = i1
        review.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        good, reasons = check_project(project)
        assert not good and any("identical" in p for p in reasons), reasons
        print("REJECT_SAME_BEFORE_AFTER: PASS")

        record["rounds"][1]["shots"][0]["image"] = i2
        record["fixes"][0]["after_image"] = i2
        record["rounds"][1]["actually_viewed"] = False
        review.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        good, reasons = check_project(project)
        assert not good and any("actually_viewed" in p for p in reasons), reasons
        print("REJECT_NO_IMAGE_VIEW_CONFIRMATION: PASS")

        record["rounds"][1]["actually_viewed"] = True
        record["open_blockers"].append("Mock unresolved visible penetration")
        review.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        good, reasons = check_project(project)
        assert not good and any("unresolved" in p for p in reasons), reasons
        print("REJECT_VISIBLE_BLOCKER: PASS")

    print("ALL_VISUAL_GATE_STRUCTURAL_TESTS_PASS — does not certify visual beauty")


if __name__ == "__main__":
    main()
