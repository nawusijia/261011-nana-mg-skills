# 娜娜 MG Skills：让别的 AI 也像 Claude 一样做片

这是娜乌斯嘉AI视频《AI天团 第一集：同一道题》里开源的两个 Skill。

同一台电脑、同一套工具，Claude（克肆）做的动效片“克制、高级、让人一眼记住”，GPT（洄光）做的却看不懂。我们把 Claude 做片的方法拆出来，写成 Skill 教给洄光，他后来真的学会了自己检查、自己返工。

整个方法其实就两招：

1. **动手前先问：屏幕上到底发生了一件什么事？** 用一句话说清“起始状态 → 触发 → 结束状态”，说不清就不准写代码。光讲道理、只会堆特效的，全部打回去重做。
2. **做完让 AI 自己抽帧看。** 渲出真实画面，每隔几帧抽一张拼成大图，用眼睛看，找出问题、返工、同一机位再渲一次对比。“代码说没问题”不算数，看着对才算。

## 里面有什么

| Skill | 用途 |
|---|---|
| [`skills/nana-mg-storycraft`](skills/nana-mg-storycraft/SKILL.md) | 导演方法：一句话变化句、声画共用的事件表、对象连续变形、运动的因果、声音设计，以及强制的“真实看图”审片闭环。附两个脚本：`audit_mg.py`（抽帧拼图 + 音视频数值检查）和 `visual_gate.py`（检查审片证据链是否齐全，防止 AI 不看图就报“全绿”）。 |
| [`skills/nana-mg-kesi-craft`](skills/nana-mg-kesi-craft/SKILL.md) | 进阶工艺：SDF 液体、Three.js PBR 软体阵列、真等轴 2.5D 城市三种风格的做法，外加一个真实返工案例（折纸山脊锯齿 + 风车闪烁，V3→V4）。 |

两个 Skill 配合用：先用 storycraft 想清楚拍什么、怎么验收，再按题材看 kesi-craft 里对应的工艺单。

## 怎么用

把 `skills/` 下的两个文件夹复制到你的 Agent 读取 Skill 的位置，例如：

- Claude Code：项目里的 `.claude/skills/`，或 `~/.claude/skills/`
- Codex 等支持 `SKILL.md` 的 Agent：对应的 skills 目录（如 `.agents/skills/`）

然后直接跟 AI 说：

> 用 nana-mg-storycraft，帮我做一条 10–15 秒的动效短片，主题是“……”。做完先自己抽帧看，有问题自己改，改完再给我。

两个 Skill 要放在同一级目录里，它们会互相引用。

脚本需要 Python 3.9+、Pillow、NumPy 和 FFmpeg：

```bash
pip install pillow numpy
python skills/nana-mg-storycraft/scripts/audit_mg.py 你的视频.mp4
python skills/nana-mg-storycraft/scripts/visual_gate.py --init 你的工程目录
python skills/nana-mg-kesi-craft/scripts/preflight.py
```

## 诚实说明

- 这些方法来自我们自己几轮真实的做片和返工，**不是模型能力的评测**。在你的 Agent 上有没有用，要你自己跑一遍才知道。
- 案例里的原始工程和成片在作者本地，**没有放进仓库**；文档里已经写清楚了每个案例学到了什么，没有源码也能用。kesi-craft 的“技术重演”需要老师案例源码，没有的话直接走“原创迁移”。
- 脚本只检查文件、数值和证据链，**不会判断好不好看**。好不好看，最后由人来看。

## 致谢与许可

- Skill 内容由娜乌斯嘉的 AI 助理们整理：克肆（Claude）提供做片方法和案例，洄光（GPT）把它写成 Skill 并用它返工。
- kesi-craft 的部分技术参考了 [Vincentwei1021/mg-styles-15](https://github.com/Vincentwei1021/mg-styles-15)（MIT）。
- 本仓库以 [MIT 许可证](LICENSE) 开源。仓库里不包含任何字体、HDRI 或音频素材，使用时请自行确认这些素材的授权。
