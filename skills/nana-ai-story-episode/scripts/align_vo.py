#!/usr/bin/env python3
"""把博主的真实录音和 AI 生成的口播视频按句对齐。

用法:
  python align_vo.py <她的录音> <AI视频> <台词.txt> <输出.mp4>   # 推荐: 声音不动, 变速 AI 视频去贴她的声音
  python align_vo.py <她的录音> <AI视频> <台词.txt> <输出.wav>   # 备选: 画面不动, 把她的声音挪到 AI 的口型位置(不变调伸缩)

步骤: 两边各自识别出字级时间 -> 按台词标点切句 -> 序列对齐找到每句在两边的时间 -> 分段变速。
依赖: faster-whisper, numpy, ffmpeg (PATH 上)。模型可用环境变量 WHISPER_MODEL 指定。
台词.txt 写她实际说的话(包括语气词), 对齐最准。
"""
import json, os, re, subprocess, sys, difflib, tempfile
import numpy as np
from faster_whisper import WhisperModel

SR = 48000
PUNCT = re.compile(r"[，。？！、,.?!…：:；;\s“”\"'（）()]")


def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def save(arr, path):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", path],
                   input=arr.astype(np.float32).tobytes(), check=True)


def stretch(seg, ratio):
    """ratio = 原长/目标长, 用 atempo 不变调伸缩"""
    if abs(ratio - 1) < 0.02:
        return seg
    with tempfile.TemporaryDirectory() as d:
        a, b = os.path.join(d, "a.wav"), os.path.join(d, "b.wav")
        save(seg, a)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", a, "-filter:a", f"atempo={ratio:.4f}", b], check=True)
        return load(b)


model = WhisperModel(os.environ.get("WHISPER_MODEL", "mobiuslabsgmbh/faster-whisper-large-v3-turbo"),
                     device=os.environ.get("WHISPER_DEVICE", "cpu"), compute_type="int8")


def char_times(arr, prompt):
    with tempfile.TemporaryDirectory() as d:
        w = os.path.join(d, "x.wav")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                        "-ar", "16000", w], input=arr.tobytes(), check=True)
        segs, _ = model.transcribe(w, language="zh", word_timestamps=True, vad_filter=True,
                                   condition_on_previous_text=False, initial_prompt=prompt)
        out = []
        for s in segs:
            for wd in (s.words or []):
                chars = PUNCT.sub("", wd.word)
                if not chars:
                    continue
                step = (wd.end - wd.start) / len(chars)
                for i, c in enumerate(chars):
                    out.append((c.lower(), wd.start + i * step, wd.start + (i + 1) * step))
        return out


def phrase_spans(script_chars, phrases, ct):
    """把每句台词映射到识别结果的时间范围(识别有错字也能对上大部分)"""
    asr = "".join(c for c, _, _ in ct)
    sm = difflib.SequenceMatcher(None, script_chars, asr, autojunk=False)
    m = {}
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            m[a + k] = b + k
    spans, pos = [], 0
    for p in phrases:
        idx = [m[i] for i in range(pos, pos + len(p)) if i in m]
        pos += len(p)
        spans.append((ct[idx[0]][1], ct[idx[-1]][2]) if idx else None)
    return spans


def warp_video(her_path, ai_path, her, ai, sp_her, sp_ai, out_path):
    """她的声音不动, 把 AI 视频按句分段变速, 口型对到她的声音上"""
    her_len, ai_len = len(her) / SR, len(ai) / SR
    anchors = [(0.0, 0.0)]
    for h, a in zip(sp_her, sp_ai):
        if not h or not a:
            continue
        pts = [(a[0], h[0])]
        # 句尾也对齐(停顿里慢放不显眼); 识别边界可疑时(句子本身伸缩太大)只对句首
        if 0.65 <= (h[1] - h[0]) / max(0.01, a[1] - a[0]) <= 1.6:
            pts.append((a[1], h[1]))
        for at, ht in pts:
            if at > anchors[-1][0] + 0.05 and ht > anchors[-1][1] + 0.05:
                anchors.append((at, ht))
    last = next(((h, a) for h, a in zip(reversed(sp_her), reversed(sp_ai)) if h and a), None)
    if last is None:
        sys.exit("没有任何一句对上, 检查台词.txt 是否是她实际说的话")
    last_h, last_a = last
    # 最后一句句尾只在比例正常时对齐(AI 常把“拜拜”拖很长, 硬对会把挥手压成快进)
    cand = (last_a[1] + 0.15, last_h[1] + 0.15)
    pa, ph = anchors[-1]
    if cand[0] > pa + 0.05 and 0.5 <= (cand[1] - ph) / (cand[0] - pa) <= 2.0:
        anchors.append(cand)
        anchors.append((min(ai_len, cand[0] + (her_len - cand[1])), her_len))
    else:
        anchors.append((ai_len, her_len))
    parts, labels = [], []
    for i in range(len(anchors) - 1):
        (a0, h0), (a1, h1) = anchors[i], anchors[i + 1]
        f = (h1 - h0) / (a1 - a0)
        parts.append(f"[0:v]trim=start={a0:.3f}:end={a1:.3f},setpts=(PTS-STARTPTS)*{f:.4f}[v{i}]")
        labels.append(f"[v{i}]")
        print(f"AI {a0:5.2f}-{a1:5.2f} -> 她 {h0:5.2f}-{h1:5.2f}  x{f:.2f}")
    fc = ";".join(parts) + ";" + "".join(labels) + f"concat=n={len(labels)}:v=1:a=0,fps=30[v]"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", ai_path, "-i", her_path, "-filter_complex", fc,
                    "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", out_path], check=True)


def warp_audio(her, ai, phrases, sp_her, sp_ai, out_path):
    """画面不动, 把她每句声音挪到 AI 那句的位置, 不变调伸缩(0.7~1.4 倍)"""
    out = np.zeros(len(ai) + SR, dtype=np.float32)
    report = []
    PRE, POST = 0.06, 0.12
    for p, h, a in zip(phrases, sp_her, sp_ai):
        if not h or not a:
            report.append({"句": p, "状态": "没对上, 跳过"})
            continue
        hs, he = max(0, h[0] - PRE), h[1] + POST
        seg = her[int(hs * SR):int(he * SR)]
        tgt = (a[1] - a[0]) + PRE + POST
        ratio = min(1.4, max(0.7, (he - hs) / tgt))
        seg = stretch(seg, ratio)
        st = int(max(0, a[0] - PRE) * SR)
        end = min(len(out), st + len(seg))
        out[st:end] += seg[:end - st]
        report.append({"句": p, "她": [round(h[0], 2), round(h[1], 2)], "AI": [round(a[0], 2), round(a[1], 2)],
                       "伸缩": round(ratio, 3)})
    out = out[:len(ai)]
    peak = np.abs(out).max()
    if peak > 0.98:
        out *= 0.98 / peak
    save(out, out_path)
    print(json.dumps(report, ensure_ascii=False, indent=1))


def main():
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    her_path, ai_path, txt_path, out_path = sys.argv[1:5]
    script = open(txt_path, encoding="utf-8").read().strip()
    phrases = [PUNCT.sub("", p).lower() for p in re.split(r"[，。？！,.?!]+", script)]
    phrases = [p for p in phrases if p]
    script_chars = "".join(phrases)
    her, ai = load(her_path), load(ai_path)
    ct_her, ct_ai = char_times(her, script), char_times(ai, script)
    for name, ct in (("她", ct_her), ("AI", ct_ai)):
        print(name, "".join(c for c, _, _ in ct), file=sys.stderr)
    sp_her = phrase_spans(script_chars, phrases, ct_her)
    sp_ai = phrase_spans(script_chars, phrases, ct_ai)
    if out_path.endswith(".mp4"):
        warp_video(her_path, ai_path, her, ai, sp_her, sp_ai, out_path)
    else:
        warp_audio(her, ai, phrases, sp_her, sp_ai, out_path)


if __name__ == "__main__":
    main()
