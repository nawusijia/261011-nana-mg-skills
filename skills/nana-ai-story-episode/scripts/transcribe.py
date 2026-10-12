#!/usr/bin/env python3
"""口播识别: 输出带词级时间的 JSON, 用来切句和写字幕时间。

用法: python transcribe.py <录音或视频> <输出.json> [专有名词提示]
例:   python transcribe.py 娜娜的口播.mp4 vo.json "Claude。GPT。GitHub。skill。娜娜酱。"
依赖: faster-whisper, ffmpeg。没有 GPU 时用 CPU int8 也够快。
"""
import json, os, subprocess, sys, tempfile
from faster_whisper import WhisperModel

if len(sys.argv) < 3:
    sys.exit(__doc__)
src, out = sys.argv[1], sys.argv[2]
prompt = sys.argv[3] if len(sys.argv) > 3 else None
with tempfile.TemporaryDirectory() as d:
    wav = os.path.join(d, "vo.wav")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-ac", "1", "-ar", "16000", wav], check=True)
    model = WhisperModel(os.environ.get("WHISPER_MODEL", "mobiuslabsgmbh/faster-whisper-large-v3-turbo"),
                         device=os.environ.get("WHISPER_DEVICE", "cpu"), compute_type="int8")
    segs, _ = model.transcribe(wav, language="zh", word_timestamps=True, vad_filter=True, initial_prompt=prompt)
    rows = []
    for s in segs:
        rows.append({"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip(),
                     "words": [{"w": w.word, "s": round(w.start, 2), "e": round(w.end, 2)} for w in (s.words or [])]})
json.dump(rows, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for r in rows:
    print(f"{r['start']:6.2f}-{r['end']:6.2f}  {r['text']}")
print("识别可能有错字(尤其专有名词), 用来定时间; 字幕文字以她实际说的为准, 不确定的请她亲耳确认。")
