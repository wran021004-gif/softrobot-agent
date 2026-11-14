# Softrobot-Agent 论文 v1.0 — GitHub 工作分支

当前重组稿位于：

- Branch: \`paper/research-restructure-v1.0\`
- Base: \`paper/overleaf-v0.4\`
- Main document: \`main.tex\`
- Compiler: \`pdfLaTeX\`

本分支将论文叙事重组为：Problem Formulation → Physics-Guided Agentic Research Method → System Implementation → Multi-task Results → Real-World Robot Validation。M0--M3 被定义为不同的敏感性研究语义，而不是四个独立优化器。

## 当前稿件结构

1. Introduction
2. Related Work
3. Problem Formulation
4. Method: Physics-Guided Agentic Research
5. System Implementation
6. Experimental Setup
7. Results and Analysis
8. Real-World Robot Validation
9. Discussion
10. Conclusion

附录包括第一批 A/B/C 对照协议、11 项任务组合，以及 PHS-2D 数学证据的来源与适用范围。

## 图表与数据状态

- Figure 1 的研究架构图使用 TikZ 源码。
- PHS-2D 结构图、18 组梯度配对图、A/B/C 对照图和真机演示图保留了明确的插图位置。
- A/B 第一批为 PHS-2D、T01、T04、T07，共 8 次新运行；当前稿件不包含尚未产生的 A/B 结果。
- PHS-2D 主案例采用九段四腱 Round-3 证据包。旧七段图像资产不用于当前正文，避免结构和性能数据混用。
- 真机结果单独放在 Section 8，待从已归档的硬件实验记录导入。

## 同步到 USTC Overleaf

本地 Git 仓库已经配置了 GitHub \`origin\` 和 USTC Overleaf \`overleaf\` 两个 remote。确认本地没有未提交修改后，可执行：

\`\`\`powershell
git fetch origin
git switch -c paper/research-restructure-v1.0 --track origin/paper/research-restructure-v1.0
git push overleaf HEAD:main
\`\`\`

如果本地分支已经存在，使用 \`git switch paper/research-restructure-v1.0\`。推送前若 Overleaf 网页端有新修改，应先 fetch 并检查差异；不要使用 force push。

原始 v0.4 分支和 Overleaf 原有项目未被本次修改覆盖。
