# PHS-2D 成功见证的独立 Benchmark 增量导出

本代码分支从原导出工具 `feat/base-only-benchmark-export@c8085b8faa4d802d529d4bc8468f7c3c907662c4` 建立，
只导出冻结的 `research/phs2d-inverse-passive-design@9d6d160e050c836b87d0563a497fc0ec1c3761a8`。
不合并科研主线，不导入完整 Store 或大型数据到 Git，不优化结构，不执行新的科学积分。

交付中的 PHS 仍是开发性独立数值验收通过，原字段 `registered_acceptance=not_registered` 保留。
M1–M6 的十条主动任务、原文件和历史验收不变。

## 实现和来源绑定

- `tools/phs2d_package_export.py` 逐项核对冻结 Git blob、归档 member SHA、只读 SQLite artifact SHA。
  SQLite 使用 `mode=ro&immutable=1`，二进制采用 readonly blob 流式提取，所有科学 Store 保持封存。
- 直接复制原 solution/model.xml；SHA-256 为 `75de64d10a2e2eaa605e3d59d16eec1bea6a8081d9c537c8deb2f6a09b47c77a`。
- 只使用独立复现 replicate=1 的无力基准及十个条件，不将半步长和扰动轨迹作为主要展示数据。
- 每条原 NPZ 有 32,000×442 float64 数据，导出加入原 samples[0] 得到 32,001 行。
  原 post-step 数组的二进制 SHA 完全保留，完整 qacc 保留于 NPZ，CSV 为 322 列、`.17g` 表示。
- 独立 `mj_forward` 重建 Tip、材料点和接触诊断；原张力、腱长和 qacc 从封存记录取值，未以重算反力覆盖。
  施力表保留上一个状态上的实际材料点位置，原 10 ms snapshot 的额外力映射相位另有说明。
- 原 XML 加载后 runtime overrides 为 iterations=100、tolerance=1e-10；32 MiB 编译线程解决深层 XML 栈需求。
  XML 本身没有改写，完整 native options 和原惯量/主轴表示均另存。
- payload XML 完整惯量严格检查，MuJoCo 主轴分解约 2e-15 kg·m² 的表示舍入单列诊断，不修改物理参数或验收阈值。

## 独立接收方工具

`scripts/phs2d_io.py` 只负责被动状态、材料点和原力映射。
`view_phs2d.py` 为保存状态动画、无 GUI 逐帧检查和原 MuJoCo PNG 渲染。
空格、R、L、+/- 分别操作暂停、重播、循环、速度，绝不积分。

`simulate_phs2d.py` 供接收方以后明确运行新的动力学复现，要求新包外输出目录；本轮只执行 `--check-only`。
配方保留单侧固定 payout、变形材料点世界 x 力、原 smoothstep 和 10 ms snapshot 的额外 force-map forward。
它不自动产生新的 SELECT，也不覆盖历史数据。

`validate_phs2d.py` 检查全部物理绑定、原 JSON 身份、初态、11 条 NPZ/CSV、力与相位、标签及相对路径。
`validate_all.py` 进行类型化分派：原 `validate_package.py` 原样验证 M1–M6，只将新增 PHS 交给新校验器。
`manifest.trajectories` 仍为原十条；新增 `passive_benchmarks`。
原 package_io、主动查看器、主动模拟器、旧校验器与导出框架都没有修改。

只读工具覆盖 mj_step、mj_step1、mj_step2 为显式报错入口，避免验证阶段意外积分。
接收方只需 Python、MuJoCo 和 NumPy，不依赖 Agent、Provider、Store 或 Harness。
Matplotlib 只用于开发端科学图表生成，不是独立查看器依赖。

## 发布流程

`tools/phs2d_package_delivery.py` 先快照原全部文件哈希，再复制至独立 staging。
数据、文档、图形和实际查看器测试完成后更新清单，根完整性检查通过后生成交付报告并重建最终清单。
发布工具构建临时 ZIP64，核对 CRC 及每个文件 SHA，再备份原 ZIP、原子加入完整 PHS 目录、最后更新清单并原子替换 ZIP。
原不可变文件逐项核对；原根报告内容在新 JSON 的 legacy 中保留。

`tools/phs2d_package_zipcheck.py` 将最终 ZIP 解压至含空格和中文的新路径，再执行全部 21 条零积分校验。
ZIP 的最终大小、SHA、原 ZIP 备份身份和解压测试保存在包外同名发布记录，避免 ZIP 自身哈希循环。
该记录可随 ZIP 转发，不是运行模型所需依赖。

开发端相对路径命令示例（按实际 checkout/输出位置选择参数）：

```powershell
python -B -m tools.phs2d_package_delivery prepare --package ../exports/base_only_accepted_20261028 --staging ../exports/.phs2d_staging
python -B -m tools.phs2d_package_export --source ../phs2d-inverse-passive-design --package ../exports/.phs2d_staging --cache runs/phs2d-source-cache
python -B -m tools.phs2d_package_docs --package ../exports/.phs2d_staging
python -B -m tools.phs2d_package_plots --package ../exports/.phs2d_staging
python -B -m tools.phs2d_package_checks --package ../exports/.phs2d_staging --gui
python -B -m tools.phs2d_package_delivery index --staging ../exports/.phs2d_staging
python -B ../exports/.phs2d_staging/scripts/validate_all.py --package ../exports/.phs2d_staging --report runs/phs2d-validation.json
python -B -m tools.phs2d_package_report --package ../exports/.phs2d_staging --validation runs/phs2d-validation.json
python -B -m tools.phs2d_package_delivery index --staging ../exports/.phs2d_staging
python -B -m tools.phs2d_package_delivery publish --package ../exports/base_only_accepted_20261028 --staging ../exports/.phs2d_staging
```

接收方命令在资料包的中文 README 中，均相对资料包根目录。
Linux 命令提供但未验证；本次实际环境为 Windows、Python 3.11.16、MuJoCo 3.13.0、NumPy 2.4.6。

## 实际检查

- 新被动导出及旧主动导出针对性回归共 15 项单元测试通过；数值单元夹具均为人工构造，未调用真实积分器。
- PHS 首轮全部 352,011 帧检查通过，CSV/NPZ 共享字段最大误差 0，独立 forward 位姿误差 0。
- M1–M6 原十条通过原完整性校验，255 个原不可变文件哈希一致。
- 无 GUI 查看器验证 32,001 帧，位姿误差 0；PNG 原生渲染成功；GUI smoke 3 秒正常播放，实际帧数见包中 viewer_validation.json。
- 暂停、循环、重播和速度控制逻辑、错误工况标签拒绝、真实 t=0、float64 往返和禁积分入口均有针对性测试。
- 动力学重放仅检查配方，未自动运行任何新科学积分；完整逐步数据始终来自封存证据。

数据规模、逐文件哈希、代码提交和最终 ZIP 验证结果以资料包交付报告、清单及包外发布记录为准。
