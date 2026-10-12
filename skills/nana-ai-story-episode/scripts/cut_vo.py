#!/usr/bin/env python3
"""把整段口播按句切开, 每句一个 wav, 方便在时间线上单独摆放。

用法: python cut_vo.py <录音或视频> <切点.json> <输出目录>
切点.json 例: {"N1": [0.0, 6.62], "N2": [6.86, 11.42]}   (秒, 从 transcribe.py 的词级时间里读)
每句加 30ms 淡入、60ms 淡出, 防止爆音。
"""
import json, os, subprocess, sys

if len(sys.argv) != 4:
    sys.exit(__doc__)
src, cuts, out = sys.argv[1], json.load(open(sys.argv[2], encoding="utf-8")), sys.argv[3]
os.makedirs(out, exist_ok=True)
for k, (a, b) in cuts.items():
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(a), "-to", str(b), "-i", src,
                    "-vn", "-ac", "2", "-ar", "48000",
                    "-af", "afade=t=in:d=0.03,areverse,afade=t=in:d=0.06,areverse",
                    os.path.join(out, f"{k}.wav")], check=True)
    print(k, round(b - a, 2))
