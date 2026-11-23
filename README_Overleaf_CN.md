# PRIME-Soft 初稿整理版（2026-11-23）

入口为 `main.tex`，编译器为 pdfLaTeX。当前阶段只修改 GitHub 论文版本，尚未同步 Overleaf。

正文顺序：Introduction → Related Work → Problem Formulation → Method → Experimental Setup → Results → Discussion → Conclusion。
Results 顺序：整体任务结果 → 三个研究案例 → 数学证据 → 研究连续性与模型比较。
正文保留 Figure 1–4、Table I–II 和 Algorithm 1；辅助资源及决策实验图移至附录。

附录 A：设计空间、数学推导、工具接口；B：架构对照协议；C：任务定义与结果；D：研究连续性实验；E：资源对比。
旧 PDF 的附录 F（原源文件 `C_evidence_provenance.tex`）已移除；数学附录保留并改用与排版编号一致的文件名。

真机实验位置保留在 `sections/08_real_world_validation.tex`，`main.tex` 中有注释入口；待实测数据齐备后启用。
设计空间 Table S1 的基础配置快照位于 `paper_handoff/design_space_sources/`。表中范围对应这一实现配置，逐任务授权子集由各任务冻结配置决定。

本轮是结构与重心调整。下一轮建议依次精修摘要、引言贡献、Method B、Results，再统一术语与句式。
