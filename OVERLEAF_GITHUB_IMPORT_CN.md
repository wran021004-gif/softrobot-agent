# 将论文重组稿同步到中科大 Overleaf

## 当前 GitHub 版本

- Repository: \`wran021004-gif/softrobot-agent\`
- Manuscript branch: \`paper/research-restructure-v1.0\`
- Main file: \`main.tex\`
- Compiler: \`pdfLaTeX\`

本分支从 \`paper/overleaf-v0.4\` 创建，原始 v0.4 分支保持不变。本次只推送到 GitHub 的新分支，没有直接修改 Overleaf 的 \`main\`。

## 使用已配置的 Overleaf Git remote

本地仓库此前已配置 \`overleaf\` remote，且 Overleaf 的 \`main\` 与 v0.4 基线一致。若本地没有未提交修改，可在论文仓库目录执行：

\`\`\`powershell
git fetch origin
git switch -c paper/research-restructure-v1.0 --track origin/paper/research-restructure-v1.0
git push overleaf HEAD:main
\`\`\`

若本地分支已经存在，改用：

\`\`\`powershell
git switch paper/research-restructure-v1.0
git push overleaf HEAD:main
\`\`\`

这是普通 fast-forward 推送，不需要 force push。若 Overleaf 端已经产生新的提交，推送会被拒绝；此时先 fetch 并检查差异，不要强制覆盖。

## 使用 ZIP 上传

如果不使用 Git remote，也可以打开 GitHub 的 \`paper/research-restructure-v1.0\` 分支，选择 **Code → Download ZIP**，再在 USTC Overleaf 中上传项目。设置 \`main.tex\` 为主文件，Compiler 选择 \`pdfLaTeX\`。

## 当前稿件中的图表状态

Figure 1 架构图为 TikZ 源码。PHS-2D 结构图、梯度一致性图、A/B/C 对比图和真机演示图目前是有明确说明的占位框，待导入对应原始数据和图像。旧 v0.4 PDF 图像仍保留在仓库，但没有在新稿中引用，避免使用与当前九段 PHS-2D 主案例不一致的旧图。
