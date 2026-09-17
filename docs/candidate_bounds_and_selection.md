# 候选最终约束与明确结构选择

> 当前输入分层已进一步整理：新推荐实体设计不含 `cells`，离散配置位于 `inputs/discretization.json` 和 `ExperimentPolicy.discretization`；公共文件加载、候选核对与装配位于 `extensions/tendon_family/preparation.py`。本文其余内容保留 `c04a5f9` 当时的修复与证据，当前命令和新旧关系以 [tendon_family.md](tendon_family.md) 为准。

本次在 `feat/independent-spatial-dynamics` / `64494f5311385f8be1dfa1a2fc2662f49d56edb4` 上修复，开始时工作区干净，未发现适用的 AGENTS.md。没有回退、commit、push 或 merge；没有修改物理模型、控制算法、搜索算法或历史任务。

## 两处修复

`extensions/tendon_family/candidate.py`：显式编辑授权与最终值检查复用 `check_value`。选择基线/完整模板并应用修改后，`validate_final` 遍历设计空间和任务策略中所有受约束路径，以最终设计判定 `when`；不启用的参数不要求存在，启用但缺失返回 `CONSTRAINED_PARAMETER_MISSING`。值同时满足空间范围和任务更窄范围。独立 `build` 使用请求中的空间；公共 `apply` 和 `build_tool` 继续传入当前任务的 `policy.editable`。失败仍使用既有异常或 `physically_invalid / backend_unsupported` 协议。

`examples/platform_tendon_family.py`：增加 `--candidate continuous|structural`。新 prepare 创建 `inputs/<candidate>_request.json`，其中明确指定 `baseline_file`、`space_file` 和 `changes`。设计和空间文件是唯一来源；后端配置仅保存待装配的会话设置，不再保存第二套权威设计副本。`prepare_candidate` 同时服务 build/run，并通过公共 `_candidate` 检查实际设计一致。运行仍由 `Host.invoke(simulation.run)` 执行，提交请求中的真实 `changes`，`candidate_id` 仅作标签。

构建快照 `<candidate>_<backend>_selection.json` 保存完整请求、任务约束、来源及请求/设计/物理/场景/控制身份。run 会重新构建并核对快照，输入改变时返回 `CANDIDATE_BUILD_STALE`，必须显式 build；不会裁剪范围或暗中替换机器人。显式 build 可更新未封存的构建产物；运行记录和平台封存证据独立保存，不被覆盖。

新记录为 `<candidate>_<backend>_record.json`，保存目录为 `saved/<candidate>_<backend>`。compare/view 使用同一选择定位记录；显式 structural 不回退到历史 continuous。原 single 入口保留；旧目录缺少请求文件时，明确使用其独立 design/space 文件及既有候选编辑，来源记录为 legacy。未指定候选的旧 compare/view 仍可读取原文件名。

## 可复制命令

以下使用新目录，只执行 structural 两次完整求解。任务保持原 0.35 s、目标 `[0.29,0.035,0.19] m`、10 mm 容差、同一控制、初态与外力。

```powershell
Set-Location D:\softrobot-agent
conda activate softagent
$selectedRun = 'runs/my_selected_tube'
python examples/workbench.py platform tendon-family prepare $selectedRun
python examples/workbench.py platform tendon-family build $selectedRun --candidate structural
python examples/workbench.py platform tendon-family run $selectedRun --candidate structural --backend matlab_spatial
python examples/workbench.py platform tendon-family run $selectedRun --candidate structural --backend family_mujoco
python examples/workbench.py platform tendon-family compare $selectedRun --candidate structural
python examples/workbench.py platform tendon-family view $selectedRun --candidate structural --backend matlab_spatial
python examples/workbench.py platform tendon-family view $selectedRun --candidate structural --backend family_mujoco
```

本轮数据已经在以下目录，可以直接读取和回放，不要再次 run：

```powershell
$selectedRun = 'runs/tendon_candidate_selection_20260917'
Get-Content "$selectedRun/inputs/structural_request.json" -Raw -Encoding UTF8
Get-Content "$selectedRun/selection_verification.json" -Raw -Encoding UTF8
python examples/workbench.py platform tendon-family compare $selectedRun --candidate structural
python examples/workbench.py platform tendon-family view $selectedRun --candidate structural --backend matlab_spatial
python examples/workbench.py platform tendon-family view $selectedRun --candidate structural --backend family_mujoco
```

如需合法覆盖，编辑请求 `changes` 为 `{"template":"tube_distal","components/near/length_m":0.175}`，然后明确重新 build 并创建独立运行。本轮没有提交覆盖，结构模板的近段长度保留 **0.16 m**。修改基线文件会进入请求身份；完整模板仍按原语义完整替换基线，不能隐式继承 continuous 的修改。

## 有限验证与本轮结果

`tests/test_tendon_family_candidates.py` 共 7 项针对性用例通过，其中新增 4 项覆盖模板空间越界及合法覆盖、公共任务范围、最终条件/缺失字段、build/run 来源一致及过期快照拒绝。前 6 项在沙箱内通过；文件测试因 Windows 临时目录权限失败，定位后仅该项在沙箱外通过，没有启动动力学。未运行全仓测试或额外物理样例。

实际选中请求仅 `{"template":"tube_distal"}`。设计名 `tube_distal_three_cells`，远段圆管、3 个单元，两段共 12 个弯曲 DOF，6 根绳、6 个独立执行器；近段 0.16 m。核对了平台封存 `CandidateInput.effective`、真实 changes、后端保存描述、解析物理和场景，避免仅凭文件名或 candidate_id 声称运行了某候选。

两个后端匹配的身份：

| 身份 | SHA-256 |
|---|---|
| 请求 | `703a00b5668bb858bf27ee28be958cbc6f1ec94a44eca1737cb4741273fdcdbc` |
| 最终设计 | `a220fa0933197518aa6507afe6fdffdc3627e297c88372a7d94b3843185f0dcd` |
| 解析物理 | `4679c3149906508d12ebea4f60d2943528964846206dcad03112b3509f669001` |
| 场景 | `f4dcc2a9fd6c90fad370ecafc2f4d649bb2f030409c33075135f8ade87472835` |
| 控制 | `dba9b78ad994f95f4d9031cb9c1256d8a48ebd279264b0e708ddc41ef7141163` |

| 后端 | 积分时长 | 求解状态 | 目标误差 | 任务成功 | 求解 / 后端总调用耗时 |
|---|---:|---|---:|---|---:|
| MATLAB | 0.35 s | completed | 21.1448 mm | false | 5.0941 / 12.6551 s |
| MuJoCo | 0.35 s | completed | 21.1543 mm | false | 0.0118 / 0.3205 s |

MATLAB 公共准备约 0.0061 s、引擎启动 7.2170 s；MuJoCo 公共准备约 0.0066 s、引擎编译 0.0158 s。MATLAB 保存 3651 个内部步的计数，MuJoCo 700 个积分步；两者均保存 35 个共同控制网格样本。后端内部步数不是精度比较指标。

末端最终后端差异 **0.09013 mm**，末端轨迹 RMS 差异 **0.11098 mm**，绳长最大差异 **0.01387 mm**，张力最大差异 **0.007614 N**。与任务误差分别报告；双后端接近不代表真实物理标定。

MATLAB 求解 execution_id 为 `61048c756a264987a535009cd6f189fc`，MuJoCo 为 `48d16333fd1e41d89dbb232931a1bc86`。实际完整积分 **2 次**，平台 `backend_solves` 扣账 **2 次**，没有求解失败或重试，没有重跑旧单段/continuous。MATLAB 使用获准的沙箱外 Engine 启动，避免已知启动拒绝导致无效扣账。

两后端均通过公共评价、末端/张力信号读取与 `visualization.saved_replay`，回放准备扣账 0 次求解。`selection_verification.json` 及版本化摘要 `docs/evidence/candidate_selection.json` 保存这条证据链。没有自动打开交互窗口；view 已按选择定位上述保存目录。任务仍未达到 10 mm 容差，没有为此改目标、控制或追加积分。
