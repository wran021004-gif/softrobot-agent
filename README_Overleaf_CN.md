# Softrobot-Agent 论文 v0.4 — GitHub 版（含真实导出图）

本分支 `paper/overleaf-v0.4` 基于用户实际使用的 Overleaf v0.1 工程，保留 IEEEtran 模板、main.tex 和原有九章节文件名，正文已按 C1/C2/C3 科学叙事重新组织。

## 原始图片已包含

`figures/` 下包含从 `wran021004-gif/softrobot-demo-showcase` 的 `codex/paper-figures-spring-button-20261111` 分支直接复制的 8 张**原始导出 PDF**，每张通过 Git blob SHA-1 与原始仓库逐一校验，未重新绘制、生成或修改。

正文引用的五张图（M1、Figure-eight、P3 两张、PHS-2D）已经在 `figures/` 内，不需要另行运行图片下载脚本。完整来源见 `figures/original_assets_manifest.json`。PowerShell 脚本仅用于日后重新下载和验证原图。

## 在中科大 Overleaf 中使用

**推荐（无需本地 Git）：** 打开 GitHub 仓库切换至 `paper/overleaf-v0.4` 分支，点击 **Code → Download ZIP**，然后在 `https://latex.ustc.edu.cn` 选择 **New Project → Upload Project** 上传从 GitHub 下载的 ZIP，并将 `main.tex` 设置为主文件，编译器选 `pdfLaTeX`。

如果 USTC Overleaf 提供 **Import from GitHub**，可以尝试，但请确认它导入的是正确的分支；这一自建实例是否提供官方云端 GitHub 同步功能尚未验证，不能假定能够直接选择非默认分支。

已有的 Overleaf 项目不会因为 GitHub 分支更新而自动同步。原项目建议先保存备份后再替换源码。

## 主要内容

- C1 Mechanism-Guided Autonomous Research。
- C2 Composable Mathematical Research（科研意图投影、参数/观测组合、数学操作、有效性检查）。
- C3 Evidence-Grounded Iterative Research。
- P3 No-Math、No-Intent-Projection、No-Pairwise-Interaction、No-Knowledge、Fixed-Plan。
- M1 物理探针消融、Reporter 快照、Tracking 数学迁移与三模型对照。
- 200 Provider 请求、100 数学评价、150 物理启动的实验硬预算协议。

详情见 `OVERLEAF_GITHUB_IMPORT_CN.md`、`EXPERIMENT_MATRIX.md` 和附录。
