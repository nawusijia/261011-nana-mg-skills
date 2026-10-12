// 糖果贴纸包装组件（Remotion 4）—— 来自《AI天团 第一集》的实际工程，整理成可复用的一份。
// 用法：把本文件放进 Remotion 工程的 src/，素材放 public/（视频 film/、图 img/、口播 vo/、字体 heavy.otf）。
// 在你的合成里 import 需要的组件；时间单位全部是“秒”，组件内部按 FPS 换算成帧。
import React from 'react';
import {AbsoluteFill, Audio, Freeze, OffthreadVideo, Sequence, staticFile, useCurrentFrame} from 'remotion';

// ───────── 品牌 ─────────
export const C = {cream: '#FFF4EA', ink: '#3B2340', pink: '#FF6FA8', yellow: '#FFD84D', mint: '#5FD3B3', lav: '#B9A7FF', peach: '#FFB38A'};
export const FPS = 30;
export const fr = (sec: number) => Math.round(sec * FPS);
export const FONT = '"NanaHeavy","Source Han Sans SC","Microsoft YaHei",sans-serif';
export const useSec = () => useCurrentFrame() / FPS;
const clamp = (x: number) => Math.max(0, Math.min(1, x));
export const ease = (x: number) => 1 - Math.pow(1 - clamp(x), 3);

// 回弹进场：冲过头 1.12 → 回落 → 两下小摇摆
export const popIn = (t: number) => {
  if (t <= 0) return {scale: 0, rotate: -3};
  const pts = [[0, 0], [0.14, 1.12], [0.25, 0.97], [0.38, 1.02], [0.5, 1]];
  let scale = 1;
  for (let i = 1; i < pts.length; i++) if (t <= pts[i][0]) {
    const [a, av] = pts[i - 1]; const [b, bv] = pts[i];
    const p = (t - a) / (b - a); scale = av + (bv - av) * (p * p * (3 - 2 * p)); break;
  }
  const rotate = t < 0.5 ? 3 * Math.sin((t / 0.5) * Math.PI * 4) * (1 - t / 0.5) : 0;
  return {scale, rotate};
};
// 出场：0.25 秒缩小下沉（left = 距离结束还有几秒）
export const sinkOut = (left: number) => {
  const p = clamp(1 - left / 0.25);
  return {scale: 1 - 0.85 * p * p, y: 30 * p * p, opacity: 1 - p};
};

// 贴纸外观：粗描边 + 实色投影 + 圆角
export const stickerStyle = (fill: string, radius = 28, border = 6, shadow = 10): React.CSSProperties => ({
  background: fill, border: `${border}px solid ${C.ink}`, boxShadow: `${shadow}px ${shadow}px 0 ${C.ink}`,
  borderRadius: radius, boxSizing: 'border-box', color: C.ink, fontFamily: FONT, fontWeight: 900,
});

// 进出场包装：dur 为所在段落总时长（秒）
export const Pop: React.FC<React.PropsWithChildren<{dur: number; delay?: number; tilt?: number; style?: React.CSSProperties; noOut?: boolean}>> = ({dur, delay = 0, tilt = 0, style, noOut, children}) => {
  const t = useSec() - delay;
  if (t < 0) return null;
  const pi = popIn(t);
  const so = noOut ? {scale: 1, y: 0, opacity: 1} : sinkOut(dur - delay - t);
  return (
    <div style={{position: 'absolute', transform: `translateY(${so.y}px) scale(${pi.scale * so.scale}) rotate(${tilt + pi.rotate}deg)`, opacity: so.opacity, ...style}}>{children}</div>
  );
};

// 段落：a–b 秒
export const Seg: React.FC<React.PropsWithChildren<{a: number; b: number}>> = ({a, b, children}) => (
  <Sequence from={fr(a)} durationInFrames={fr(b - a)} layout="none">{children}</Sequence>
);

// 背景：奶油细点阵
export const Backdrop: React.FC = () => (
  <AbsoluteFill style={{background: C.cream}}>
    <AbsoluteFill style={{backgroundImage: `radial-gradient(${C.ink}22 2.2px, transparent 2.6px)`, backgroundSize: '38px 38px', backgroundPosition: '19px 19px'}} />
  </AbsoluteFill>
);

// 小标签胶囊
export const Chip: React.FC<{text: string; fill: string; delay?: number; style?: React.CSSProperties; tilt?: number; dur: number; size?: number}> = ({text, fill, delay = 0, style, tilt = -4, dur, size = 38}) => (
  <Pop dur={dur} delay={delay} tilt={tilt} style={style}>
    <div style={{...stickerStyle(fill, 999, 5, 6), padding: `${size * 0.22}px ${size * 0.6}px`, fontSize: size, whiteSpace: 'nowrap'}}>{text}</div>
  </Pop>
);

// 视频贴纸窗：所有成片和角色镜头都装在这里，左上角带“谁做的/谁在说”标签
type WinProps = {src: string; x: number; y: number; w: number; h: number; dur: number; tilt?: number; vol?: number | ((t: number) => number);
  startFrom?: number; flip?: boolean; freezeAt?: number; label?: {text: string; fill: string; delay?: number}; noOut?: boolean};
export const Win: React.FC<WinProps> = ({src, x, y, w, h, dur, tilt = 0, vol = 1, startFrom = 0, flip, freezeAt, label, noOut}) => {
  const t = useSec();
  const frozen = freezeAt !== undefined && t >= freezeAt;
  const volume = typeof vol === 'function' ? (f: number) => vol(f / FPS) : vol;
  return (
    <Pop dur={dur} tilt={tilt} noOut={noOut} style={{left: x, top: y, width: w, height: h}}>
      <div style={{...stickerStyle(C.ink, 30, 6, 12), width: '100%', height: '100%', overflow: 'hidden'}}>
        <Freeze frame={fr(freezeAt ?? 0)} active={frozen}>
          <OffthreadVideo src={staticFile('film/' + src)} startFrom={fr(startFrom)} volume={volume} muted={vol === 0}
            style={{width: '100%', height: '100%', objectFit: 'cover', transform: flip ? 'scaleX(-1)' : undefined}} />
        </Freeze>
      </div>
      {label && <Chip text={label.text} fill={label.fill} delay={label.delay ?? 0.25} style={{left: -26, top: -34}} tilt={-5} dur={dur} />}
    </Pop>
  );
};
export const BIG = {x: 232, y: 46, w: 1456, h: 819}; // 1920×1080 下的大窗

// 手绘圈：SVG 描边动画（圈出穿模、重点）
export const Scribble: React.FC<{x: number; y: number; w: number; h: number; delay: number; color?: string}> = ({x, y, w, h, delay, color = C.pink}) => {
  const t = useSec() - delay; // hooks 先调用，再提前返回
  if (t < 0) return null;
  const p = ease(t / 0.45);
  const len = 1000;
  return (
    <svg style={{position: 'absolute', left: x, top: y, overflow: 'visible'}} width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
      <path d={`M ${w * 0.55} ${h * 0.02} C ${w * 1.05} ${h * 0.05}, ${w * 1.02} ${h * 0.98}, ${w * 0.45} ${h * 0.98} C ${-w * 0.05} ${h * 0.96}, ${-w * 0.02} ${h * 0.06}, ${w * 0.62} ${h * 0.1}`}
        fill="none" stroke={color} strokeWidth={9} strokeLinecap="round" pathLength={len} strokeDasharray={len} strokeDashoffset={len * (1 - p)} />
    </svg>
  );
};

// ───────── 字幕 ─────────
// 说话人名牌 + 胶囊句子；{重点词} 自动变糖果粉
export type Speaker = {name: string; fill: string};
export type Sub = {a: number; b: number; who: Speaker; text: string};
const renderMarked = (text: string) => text.split(/(\{[^}]+\})/).map((part, i) =>
  part.startsWith('{') ? <span key={i} style={{color: C.pink, fontSize: '1.12em'}}>{part.slice(1, -1)}</span> : <span key={i}>{part}</span>);

export const SubLine: React.FC<{s: Sub}> = ({s}) => {
  const k = ease(useSec() / 0.14);
  return (
    <div style={{position: 'absolute', left: 0, right: 0, bottom: 58, display: 'flex', justifyContent: 'center'}}>
      <div style={{display: 'flex', alignItems: 'center', gap: 18, transform: `translateY(${(1 - k) * 18}px) scale(${0.94 + 0.06 * k})`, opacity: k}}>
        <div style={{...stickerStyle(s.who.fill, 999, 5, 5), padding: '6px 18px', fontSize: 30, transform: 'rotate(-4deg)'}}>{s.who.name}</div>
        <div style={{...stickerStyle(C.cream, 999, 5, 7), padding: '12px 36px', fontSize: 50, letterSpacing: 1, maxWidth: 1500, textAlign: 'center'}}>{renderMarked(s.text)}</div>
      </div>
    </div>
  );
};
export const Subtitles: React.FC<{subs: Sub[]}> = ({subs}) => (
  <>{subs.map((s, i) => (
    <Sequence key={'s' + i} from={fr(s.a)} durationInFrames={Math.max(1, fr(s.b) - fr(s.a))} layout="none"><SubLine s={s} /></Sequence>
  ))}</>
);

// ───────── 口播表：声音、字幕、小头像都读同一张表 ─────────
// id: public/vo/<id>.wav；T: 时间线起点；c0: 这句在原录音里的起点；d: 时长
export type VoLine = {id: string; T: number; c0: number; d: number; volume?: number};
// 把录音里 a–b 秒的一句字幕换算到时间线
export const at = (T: number, c0: number, a: number, b: number) => ({a: T + (a - c0), b: T + (b - c0)});

export const VoiceTrack: React.FC<{lines: VoLine[]}> = ({lines}) => (
  <>{lines.map((v) => (
    <Sequence key={v.id} from={fr(v.T)} layout="none"><Audio src={staticFile('vo/' + v.id + '.wav')} volume={v.volume ?? 1} /></Sequence>
  ))}</>
);

// 博主说话时左下角的圆形小头像：从对齐好的整条头像视频 film/<camSrc> 里按 c0 取画面，静音播放
export const SpeakerCam: React.FC<{c0: number; dur: number; camSrc?: string; size?: number; fill?: string}> = ({c0, dur, camSrc = 'host_cam.mp4', size = 250, fill = C.peach}) => {
  const t = useSec();
  const pi = popIn(t);
  const out = clamp((t - (dur - 0.22)) / 0.22);
  return (
    <div style={{position: 'absolute', left: 44, bottom: 150, width: size, height: size,
      transform: `scale(${pi.scale * (1 - 0.6 * out)}) rotate(${-4 + pi.rotate}deg) translateY(${out * 40}px)`, transformOrigin: '50% 100%'}}>
      <div style={{...stickerStyle(fill, 999, 7, 9), width: size, height: size, overflow: 'hidden', padding: 0}}>
        <OffthreadVideo src={staticFile('film/' + camSrc)} startFrom={Math.max(0, fr(c0))} muted style={{width: '100%', height: '100%', objectFit: 'cover'}} />
      </div>
    </div>
  );
};
export const SpeakerCams: React.FC<{lines: VoLine[]; skip?: string[]; camSrc?: string}> = ({lines, skip = [], camSrc}) => (
  <>{lines.filter((v) => !skip.includes(v.id)).map((v) => (
    <Sequence key={'cam' + v.id} from={fr(v.T - 0.1)} durationInFrames={fr(v.d + 0.35)} layout="none">
      <SpeakerCam c0={v.c0 - 0.1} dur={v.d + 0.35} camSrc={camSrc} />
    </Sequence>
  ))}</>
);

// 角标：右下角最边上，比字幕低，不压画面。写清 AI 实际做了哪部分。
export const CornerBadge: React.FC<{text: string}> = ({text}) => (
  <div style={{position: 'absolute', right: 26, bottom: 10, transform: 'rotate(-1.5deg)', opacity: 0.92}}>
    <div style={{...stickerStyle(C.cream, 999, 4, 4), padding: '6px 18px', fontSize: 24, display: 'flex', alignItems: 'center', gap: 10}}>
      <span style={{width: 12, height: 12, borderRadius: 99, background: C.pink, border: `3px solid ${C.ink}`, display: 'inline-block'}} />
      {text}
    </div>
  </div>
);

// ───────── 最小示例 ─────────
// export const Episode: React.FC = () => {
//   const HOST = {name: '娜娜', fill: C.peach};
//   const VO: VoLine[] = [{id: 'N1', T: 0.3, c0: 0, d: 6.6}];
//   const SUBS: Sub[] = [{...at(0.3, 0, 0.02, 2.4), who: HOST, text: '这个呢，是我家{Claude}做的视频。'}];
//   return (
//     <AbsoluteFill style={{fontFamily: FONT}}>
//       <Backdrop />
//       <Seg a={0} b={8}><Win src="film01.mp4" {...BIG} dur={8} tilt={-0.8} vol={0.35} label={{text: 'Claude 做的', fill: C.mint}} /></Seg>
//       <CornerBadge text="全片编导与包装：Claude" />
//       <SpeakerCams lines={VO} />
//       <Subtitles subs={SUBS} />
//       <VoiceTrack lines={VO} />
//     </AbsoluteFill>
//   );
// };
