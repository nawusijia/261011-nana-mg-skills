// Remotion 渲染: 静帧抽查或整片输出。
// 用法: node render.mjs stills 1,9,20     (按秒抽静帧到 out/stills/, 半分辨率, 用来审片)
//       node render.mjs video out/预览v1.mp4 [scale]
// 环境变量 COMP 指定合成 id (默认 EP1)。整片渲染较久, 建议后台运行并把进度写进日志。
import {bundle} from '@remotion/bundler';
import {renderMedia, renderStill, selectComposition} from '@remotion/renderer';
import path from 'node:path';
import fs from 'node:fs';

const root = path.resolve('.');
const mode = process.argv[2] || 'stills';
const serveUrl = await bundle({entryPoint: path.join(root, 'src/index.ts'), publicDir: path.join(root, 'public')});
const comp = await selectComposition({serveUrl, id: process.env.COMP || 'EP1'});
fs.mkdirSync('out/stills', {recursive: true});
if (mode === 'stills') {
  const secs = (process.argv[3] || '2,10,20,35,60,90,120').split(',').map(Number);
  for (const s of secs) {
    await renderStill({serveUrl, composition: comp, frame: Math.round(s * comp.fps), output: `out/stills/t${String(s).padStart(5, '0')}.png`, scale: 0.5});
    console.log('still', s);
  }
} else {
  const out = process.argv[3] || 'out/preview.mp4';
  const scale = Number(process.argv[4] || 1);
  await renderMedia({serveUrl, composition: comp, codec: 'h264', outputLocation: out, scale, crf: 20, concurrency: 8,
    onProgress: ({progress}) => { if (Math.round(progress * 100) % 10 === 0) process.stdout.write(`\r${Math.round(progress * 100)}%`); }});
  console.log('\ndone', out);
}
