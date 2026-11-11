# 从 GitHub 导入论文到中科大 Overleaf

## 最稳妥的方法：GitHub ZIP → Overleaf 上传

1. 打开 [GitHub 论文分支](https://github.com/wran021004-gif/softrobot-agent/tree/paper/overleaf-v0.4)。
2. 确认左上角分支选择为 `paper/overleaf-v0.4`，而不是 `main`。
3. 点击 **Code → Download ZIP**。下载直接来自 GitHub，不依赖 ChatGPT 附件。
4. 登录 [中科大 Overleaf](https://latex.ustc.edu.cn/)。
5. 选择 **New Project → Upload Project**，上传从 GitHub 下载的 ZIP。
6. 打开 `main.tex`，设置 Main document = `main.tex`，Compiler = `pdfLaTeX`，然后 Recompile。

本分支已经含有 8 张 SHA-1 校验过的原始导出 PDF，位于 `figures/`，不需要手动生成或替换图片。

## 如果菜单包含 Import from GitHub

可以尝试连接 GitHub 并导入项目，但中科大 Overleaf 是独立部署的实例，是否提供官方云端 GitHub Sync 尚不确定。官方 GitHub Synchronization 主要面向 Overleaf Cloud；不要假定这里能直接选取已有仓库的非默认分支。

若导入后看到的不是论文 `main.tex`，请改用上面的 GitHub ZIP 上传方法。

## 已有 Overleaf 项目

GitHub 导入通常创建新项目，不能自动覆盖或接管已有的 Overleaf 项目。建议先备份当前项目，再从本分支上传文件或创建一个新的论文项目。后续 GitHub 分支更新也不会自动改变你当前的 Overleaf 项目。
