---
name: nana-mg-kesi-craft
description: "Build advanced 3D soft-body, 2.5D isometric city and SDF liquid motion graphics, using Kesi's tested projects for progressive examples. Includes sound synchronization, rendering and visual review."
metadata:
  version: "1.2.0"
---

# 克肆第三课｜MG 复现与创作 Skill

目标：让 Agent 做出实际可播放的3D、2.5D、流体动画，而非只写计划。与 nana-mg-storycraft 的叙事导演方法配合使用。

## 使用顺序

1. 新工程建在你自己的工作区里一个独立目录，例如 `projects/<日期>-<独立主题>`。参考工程只读，不覆盖旧片。
2. 依题材只选一个按需参考：
   - 液态、拉丝、浪、液体文字：`references/liquid-sdf.md`
   - 3D软体、PBR、阵列、摄影：`references/soft-3d.md`
   - 等轴城市、楼房生长、视差：`references/isometric-world.md`
3. **必须先读** `../nana-mg-storycraft/references/visual-review-loop.md` 真实看片与返工门禁，并看 `references/director-and-qa.md`；写一句变化句、冲击性转折和同源声画 CUE 表。**涉及纸折山脊、地形狗牙、薄片旋转、不同颜色层面闪烁等实际三维问题时，额外只读 `references/case-ridge-windmill-v4.md`**，这是完成实际返工的错误→修复→同机位验证案例。
4. 先运行 `python scripts/preflight.py` 检查 node / ffmpeg / Chrome。若你手上有克肆的老师案例源码（见下文“原始案例”），用 `--cases-dir` 指过去再预检；技术重演 A 用 `python scripts/prepare_case.py --cases-dir <案例目录> --case liquid --name liquid-training-copy`（或 `3d` / `iso`）创建**全新副本**，在副本里运行 `make.sh`，绝不能在老师原目录里重渲覆盖源成片。预检不启动浏览器。
5. 从可随意抽帧的 `sceneAt(t)` 或 `motionAt(t)` 渲6–18张静帧，检查构图、材质、接触、遮挡；3D项目还须至少一组**同机位高清微距静帧 + 高风险运动件连续3–10帧**，检查锯齿狗牙、z-fighting、浮空、错面和突然消失。再渲全片并按0.33秒抽帧做拼图。每次真正看图后返工。
6. 声音读取画面事实源导出的 `cues.json`；重排镜头必须重新生成 CUE 与音轨。
7. 交付有音乐的正式MP4、可编辑工程、事件表、版本和**真实看图的返工记录**。必须执行 `../nana-mg-storycraft/scripts/visual_gate.py --check <项目目录>` 检查实际证据链，没有视觉轮次/同机位前后图即 `VISUAL_NOT_REVIEWED`，**绝不报全绿**。ffprobe检查规格，ebur128检查响度及真峰值；技术合格不代表视觉过关，更不代表用户审美认可。

## 两种复现

A 技术重演：在独立副本重渲克肆原案，证明运行链有效。B 真正迁移：另选题材原创，不能直接复刻老师现成叙事、配色、音乐。验证其他Agent是否学会，必须看B，并比较同等条件下是否加载Skill的作品。

**没有老师案例源码也能用**：三个 reference 已经写下每种风格的关键技术和踩过的坑，直接走 B（原创迁移）即可。

## 原始案例

克肆第三课原文《液态、3D、等轴三条片是怎么做出来的》，以及三条技术示例（liquid / 3d / iso，各有 `make.sh`、`film/`、`harness/` 与成片），目前在作者本地，**未随本仓库公开**。如果以后公开，会放进本仓库的 `cases/` 目录，`--cases-dir cases` 即可直接用。

这些示例原文件只读，按需看代码，不要一次全塞上下文。上游 mg-styles-15 为 MIT，转用代码留版权与许可证；字体、HDRI、音频素材的权利另查。不得分发字体文件。

Windows渲染使用本机Chrome，可能需要环境参数 `MG_CHROME` 与 `MG_GPU_ARGS=--use-angle=d3d11`。复用项目依赖，不重复安装、启动长驻服务；任务后精确清理自己的临时进程，不影响机器上其他正在运行的服务。
