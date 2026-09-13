# Round 9 本地使用

新增的单次工具数量纠正、英文运行时提示与 `llm_reach_v1` 实验入口见
[运行时实验说明](round9_llm_experiment.md)。原有上下文修复与历史数值结果保留。

## 上下文读取修复与聚焦验证

实际发送和只读检查共用 `DynamicCampaign.build_model_request()`，按 transport 的完整 UTF-8 JSON 编码计量（包含 system、user、tools 和转义），目标 50000 bytes，硬上限仍为 60000。候选默认包含参数变化、后端状态/核心指标和原文件引用；旧的大工具结果只在构建请求时转换，不覆盖原文件。超过目标依次压缩历史/最近决策、候选详情、非读页工具预览；当前证据页、任务、权限、工具 schema 和工作记忆保留。必要内容仍超过硬上限时保存 `context_pause.json`，状态改为 PAUSED，不预约模型预算。

已有 run 的 `inputs/system_prompt.md` 保持原样；构建请求时追加 `dynamic_evidence_reading_v1` 指引。真实发送时将原提示文本哈希、有效提示哈希和追加指引保存至 `inputs/prompt_versions/`，并在模型回执中关联版本；`request.json` 保存实际有效提示。

只读检查（不会调用 `load/save`、API 或求解器）：

```powershell
python examples/check_dynamic_context.py --root runs/round9_reach
```

本次当前磁盘状态的完整请求为 **61795 → 26016 bytes**；最新结果为 `attempts/025_compare_candidates/result.json`，选中 c000/c066/c057/c065 四个候选。修复前数值由原有未提交的 `round9_context_check.py` 在修改前测得，并非先前另一状态的 84572 bytes。原有未提交脚本未修改。

仅执行一个聚焦回归：`python -m unittest tests.test_dynamic_context -v`。244801 bytes 嵌套工具结果可逐层续读，5000 个原始样本数值保持一致，数组原索引通过 `record_verified_diagnosis` 核验；下一轮完整请求 26122 bytes。该场景也覆盖旧结果转换、转义 pointer/UTF-8 字符串、保留当前页、超限暂停且不扣模型预算。测试使用独立的 `runs/round9_context_tests/` 小型夹具，不改变当前 Round9 状态和预算。

进程、用户和系统环境均无 `DEEPSEEK_API_KEY`，真实模型闭环验证跳过。本次实际 API/MATLAB/MuJoCo 调用均为 0；未重新优化 c066。

`read_evidence` 保留原参数，新增 `max_bytes`（默认 4000，范围 1000–8000，包含整页元数据）。可直接使用以下真实参数读取 c066 的已有证据：

```json
{"evidence_ref":"candidates/c066/mujoco/bcd6ffa57302/diagnosis.json","pointer":"/queries","offset":0,"limit":2,"max_bytes":4000}
```

返回原文件 queries[0:2]（tendon_0、tendon_1），`returned_range={"start":0,"end_exclusive":2}`、`next_offset=2`、`has_more=true`。续读直接采用返回的 `next_read` 参数（此例 offset=2）。引用诊断时 `record_index=offset+content中的下标`。单个嵌套条目超限时，`mode=directory` 返回子 pointer，`returned_count=0`，应先沿 `next_read` 下钻，再用 `resume_container` 读取其余同级项；字符串页的 offset 是原字符串字符位置。不得把空数据目录页当作完整证据，也不得重新以页内下标引用原文件。

恢复命令：

```powershell
python examples/workbench.py dynamics resume --root runs/round9_reach --steps 120
```

`--steps 120` 表示本次最多推进 120 次模型请求，仍受剩余预算和停止条件约束，不新增 120 次预算；本次未执行该恢复命令。

在 `D:\softrobot-agent` 使用已有 `softagent` 环境，不安装新框架或升级依赖：

```powershell
conda activate softagent
python examples/workbench.py dynamics context --root runs/round9_reach
python examples/workbench.py dynamics observe --root runs/round9_reach
Start-Process 'D:\softrobot-agent\runs\round9_reach\index.html'
```

`observe` 仅读保存数据。已生成 c000、c032、c057、c066 两后端播放器，目录 `runs/round9_reach/observations/`；其中 `c066_matlab.html` 是 MATLAB 独立动力学轨迹，不是 MuJoCo 重放。浏览器可播放/暂停、拖动时间、选择绳/关节曲线、点击事件定位。直接打开 HTML 即可，无服务器或 MATLAB figure 依赖。

## 新建与继续

本轮实际新建命令已经执行：

```powershell
python examples/workbench.py dynamics new --root runs/round9_reach --source runs/round8_ready
```

这是**一次性授权分配命令**。现在 `runs/round9_budget.json` 已绑定该目录，再次 new 或换目录都会拒绝；不能删除账本来重新获得预算。Round 8 账本与旧 continue 兼容检查未放宽。

本地安全配置 `DEEPSEEK_API_KEY` 到启动此 Python 的环境后：

```powershell
python examples/workbench.py dynamics resume --root runs/round9_reach --steps 12
```

它使用 `configs/deepseek.yaml` 的现有模型/官方协议、thinking enabled、8192 输出及 60000 输入字节上限。密钥不写入请求/结果文件。没有密钥时保存 WAITING_FOR_KEY，API 请求计数保持 0。控制台会打印状态和 HTML 路径。API 错误/已启动失败计费；resume 不增加授权。不要把当前成功数值试验误认为已经完成外部模型闭环。

`examples/reach_dynamics.py` 提供等价命令；V2 可执行工具目录可由 `python examples/workbench.py catalog` 的 `dynamics_v2` 字段读取。

## 只执行一个候选或一个工具

推荐把 JSON 参数保存为文件，避免 Windows shell 的引号转义。例如已提供示例：

```powershell
python examples/workbench.py dynamics tool --root runs/round9_reach --name simulate_candidate --arguments-file configs/experiments/round9_commands/simulate_c066_matlab.json
python examples/workbench.py dynamics tool --root runs/round9_reach --name simulate_candidate --arguments-file configs/experiments/round9_commands/simulate_c066_mujoco.json
```

相同候选、控制、任务、环境、物理、模型、求解器与源码身份的已完成结果复用缓存，不再消耗 rollout。改变数值实现会产生新缓存身份；旧目录不删除。不要为查看结果调用仿真命令，应优先 observe 或 read_evidence。

查看一根绳或一个关节的一段时间：

```powershell
python examples/workbench.py dynamics tool --root runs/round9_reach --name diagnose_trajectory --arguments-file configs/experiments/round9_commands/tendon_1_window.json
python examples/workbench.py dynamics tool --root runs/round9_reach --name diagnose_trajectory --arguments-file configs/experiments/round9_commands/joint_0_window.json
```

`entity` 为 `tendon_0..`、`joint_0_y..`、`joint_0_z..` 或 `contact`；MATLAB 没有 z 关节。`fields` 可请求 `command_m`、`solver_tendon_length_m`、`solver_actuator_force_n`、`solver_qpos_rad`、`solver_qvel_rad_s`、`solver_qfrc_actuator_nm`、`solver_qfrc_passive_nm`、`solver_qfrc_constraint_nm`、`contacts` 等。未记录返回 NOT_RECORDED，不能把合力当作某个分量。原始窗口保存在返回 `raw_fields_ref`；用 read_evidence 的 JSON pointer 与 offset/limit 分页读取。

创建控制变体示例参数为 `{"parent_id":"c057","changes":{"mode":"C2"}}`；真实执行已登记为 c066，再次相同创建会返回同一身份。V2 物理参数平铺在 changes，例如 `line_density_kg_m`、`root_ei_nm2`；从旧物理切换必须明确 `physics_version:"equivalent_rod_v2"`，或明确修改一个 V2 物理字段。固定段数不可优化，显式弹性腱不可选。

`optimize_matlab` 参数见两份已执行计划 `round9_initial_search.json`、`round9_feedback_search.json` 中的 arguments。相同 search_id/参数用于恢复已存搜索；不能用同 ID 偷换目标/变量/预算。每个实际动态调用先扣 rollout，逐试验落盘；缓存试验不会多扣动态预算。初始搜索已成功结束，不建议为演示命令再次发起搜索。

## 数值实现与数据位置

* MATLAB 核心：`matlab/tdcr_planar_dynamic.m`；MATLAB 搜索数值步：`matlab/tdcr_search_step.m`。
* Python 调用：`tools/reach_dynamics.py` 的 `DynamicsBackends` 复用 `tools/matlab_tools.py::MatlabTools` Engine，以 `eng.tdcr_planar_dynamic(json_input, output_path, nargout=0, background=True)` 调用。所有关键输入先保存 `shared_input.json`；输出转存为结果与 `trajectory.json.gz`。
* 共享映射：`schemas/exploration.py`、`tools/design_compiler.py`、`tools/mujoco_tools.py`；合同 `physics_contracts/equivalent_rod_v2.md`。
* 外层确定性工作台：`tools/dynamic_campaign.py`，复用现有 owner 锁、持久化 IO、单模型 transport 与 WorkbenchResult；工具 schema/白名单在 `schemas/dynamic_workbench.py`。
* 最佳 c066：`candidates/c066/matlab/9883e86002ac/` 与 `candidates/c066/mujoco/bcd6ffa57302/`，相对 `runs/round9_reach/`。
* `solver_internal.json` 保存 MATLAB 内部积分网格；输出轨迹是固定时间查询，不能把其采样极值称为连续严格最大值。
* `final_configuration.json`、`candidate_table.json`、`comparisons/`、`diagnostics/`、`working_memory.json`、`verified_diagnoses.json`、`budget.json`、`inputs/lineage.json` 为交付入口。

聚焦测试命令为 `python -m unittest tests.test_round9 -v`，已执行并通过；本轮不需要重跑，不执行仓库历史 full-suite 命令。MATLAB 需要正常本机进程启动权限，Codex 沙箱曾阻止启动，正式数值实验在获准的本机后端权限下完成。浏览/诊断/比较不需要启动 Engine。
