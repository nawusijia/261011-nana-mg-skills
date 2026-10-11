#!/usr/bin/env python3
"""Video/audio factual QC for narrative MG; not an automated aesthetics judge.

Usage: python scripts/audit_mg.py VIDEO [--out FOLDER] [--ffmpeg PATH] [--ffprobe PATH]
Dependencies: Python 3.9+, Pillow, NumPy, FFmpeg & FFprobe on PATH (or a tools/ffmpeg/*/bin folder above this script).
No network calls, background jobs, installation or edits to the input project.
"""
import argparse
import json
import math
import shutil
import subprocess
from pathlib import Path

def resolve_binary(name, supplied, here):
    if supplied:
        return str(Path(supplied))
    direct = shutil.which(name)
    if direct:
        return direct
    # Fallback: look for a bundled FFmpeg in any parent folder's tools/ffmpeg/<version>/bin/.
    for root in [*here.parents]:
        ffmpeg_root = root / "tools" / "ffmpeg"
        if not ffmpeg_root.exists():
            continue
        candidates = sorted(ffmpeg_root.glob(f"*/bin/{name}.exe")) + sorted(ffmpeg_root.glob(f"*/bin/{name}"))
        if candidates:
            return str(candidates[-1])
    raise RuntimeError(f"Missing {name}. Provide --{name} path.")

def run(args, *, binary_output=False):
    res = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if res.returncode:
        raise RuntimeError(
            f"Failed {Path(args[0]).name}: {res.returncode}\n{res.stderr.decode('utf-8', errors='replace')[-1400:]}"
        )
    return res.stdout if binary_output else res.stdout.decode("utf-8", errors="replace")

def float_or_zero(s):
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0

def main():
    ap = argparse.ArgumentParser(description="MG video technical QA + 0.5s contact sheet and audio dynamics.")
    ap.add_argument("video", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--ffmpeg", default=None)
    ap.add_argument("--ffprobe", default=None)
    args = ap.parse_args()
    src = args.video.resolve()
    if not src.is_file():
        ap.error(f"Video not found: {src}")
    base = Path(__file__).resolve()
    ffmpeg = resolve_binary("ffmpeg", args.ffmpeg, base)
    ffprobe = resolve_binary("ffprobe", args.ffprobe, base)
    out = (args.out or (src.parent / ("qa-" + src.stem))).resolve()
    if out == src.parent:
        ap.error("--out must be a dedicated folder, not the input folder")
    out.mkdir(parents=True, exist_ok=True)

    info = json.loads(run([ffprobe,"-v","error","-show_streams","-show_format","-of","json",str(src)]))
    videos = [s for s in info["streams"] if s["codec_type"]=="video"]
    audios = [s for s in info["streams"] if s["codec_type"]=="audio"]
    if not videos:
        raise RuntimeError("No video stream")
    v = videos[0]
    dur = float_or_zero(info["format"].get("duration"))
    sample = {
        "video": str(src), "duration_seconds": dur,
        "video_stream": {k: v.get(k) for k in ("codec_name","width","height","r_frame_rate","nb_frames")},
        "audio_stream": {k: audios[0].get(k) for k in ("codec_name","sample_rate","channels")} if audios else None
    }
    frame_dir = out / "frames"
    frame_dir.mkdir(exist_ok=True)
    for old in frame_dir.glob("frame-*.jpg"):
        old.unlink()
    run([ffmpeg,"-hide_banner","-loglevel","error","-y","-i",str(src),
         "-vf","fps=2,scale=480:-2","-an","-q:v","4",str(frame_dir/"frame-%03d.jpg")])
    frames = sorted(frame_dir.glob("frame-*.jpg"))
    sample["contact_frames"]=len(frames)
    try:
        from PIL import Image, ImageDraw
        import numpy as np
        cols=4; tilew=480; tileh=290
        rows=math.ceil(len(frames)/cols)
        contact=Image.new("RGB",(cols*tilew,rows*tileh),(27,25,25))
        dr=ImageDraw.Draw(contact)
        previous=None; changes=[]
        for i,p in enumerate(frames):
            with Image.open(p) as im:
                im=im.convert("RGB")
                x=i%cols*tilew
                y=i//cols*tileh
                contact.paste(im,(x,y+20))
                dr.text((x+8,y+3),f"{i*.5:.1f} s",fill="white")
                cur=np.asarray(im.resize((48,27))).astype(np.int16)
                if previous is not None:
                    # Rough mean brightness difference, never use as an aesthetic grade.
                    changes.append({"at_seconds":i*.5,"frame_change_mean":round(float(np.abs(cur-previous).mean()),2)})
                previous=cur
        contact.save(out/"contact-sheet.jpg",quality=85)
        sample["frame_changes"]=changes
        sample["contact_sheet"]=str(out/"contact-sheet.jpg")
    except ImportError:
        sample["warning_images"]="Pillow and NumPy needed for contact sheet; extracted frame JPGs still available."

    if audios:
        import numpy as np
        pcm=run([ffmpeg,"-hide_banner","-loglevel","error","-i",str(src),"-vn",
                 "-ac","2","-ar","16000","-f","s16le","pipe:1"],binary_output=True)
        data=np.frombuffer(pcm,dtype="<i2").astype(np.float32).reshape(-1,2)/32768.0
        # AAC encoders/decoders can expose a few samples of end padding.
        # Limit analysis to the exact container duration rather than counting a phantom 0.5s window.
        data=data[:int(round(dur*16000))]
        segment=8000  # 0.5 sec at 16k
        levels=[]
        for i in range(0,len(data),segment):
            x=data[i:i+segment,:]
            if x.size:
                db=20*math.log10(float(np.sqrt(np.mean(x*x)))+1e-9)
                levels.append({"at_seconds":round(i/16000,3),"rms_dbfs":round(db,1)})
        sample["audio_rms_0_5_sec"]=levels
        sample["audio_peak_dbfs"]=round(20*math.log10(float(np.max(np.abs(data)))+1e-9),1)
    else:
        sample["warning_audio"]="No audio stream. Valid only when intentionally silent."

    report=out/"technical-report.json"
    report.write_text(json.dumps(sample,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({
      "input":str(src),"duration":dur,
      "video":sample["video_stream"],"audio":sample["audio_stream"],
      "frames_extracted":len(frames),
      "contact_sheet":sample.get("contact_sheet",None),
      "report":str(report)
    },ensure_ascii=False,indent=2))
    print("TECHNICAL_REPORT_ONLY — AUDIO/VIDEO FACTS, NOT A VISUAL PASS.")
    print("VISUAL_NOT_REVIEWED — extracted screenshots have NOT been visually inspected by this script.")
    print("NEXT: open actual frames and contact sheet, find issues, fix/re-render; then run scripts/visual_gate.py --check PROJECT to validate manually recorded evidence.")

if __name__=="__main__":
    main()
