# 第五轮结果：统一机器人设计工作台

基线为 `feat/round4-tools-visualization@c7e0dd5`，开发分支为 `feat/round5-design-workbench`。用户原有未跟踪文件 `round3_total_codex_prompt_6d857fb.md` 保留；任务、评分、物理定义和第三/第四轮原始证据未改动。

## 完成内容

- `examples/workbench.py` 统一提供 run、resume、observe、context、catalog。任务读取、设计检查、PCC 数学分析、原 Harness 完整候选评价、诊断、观察及停止组成有限决策循环。
- Decision 与 WorkbenchResult 使用严格 JSON 合同。固定规则与未来模型共用 `decide(context)` 接口；执行器独立检查工具、参数、证据、权限、前置条件和预算。库目录与执行白名单分开，旧实验脚本不能直接调用。
- 原 Harness 继续生成控制、编译模型、执行仿真和裁定任务成绩，仅增加可选正常轨迹保存。共享原子 JSON / 哈希工具提取至 `tools/state_io.py`，旧导入路径兼容。未改写数值算法。
- 每个工作台保存输入副本、Git 提交和 dirty 状态、源码快照、依赖版本、证据哈希、决策依据、持久预算和工具日志。支持暂停恢复、相同请求结果复用及显式封存历史运行回放；超时和中断不返还预算，也不自动重试。
- 中文页面显示设计、C1 控制器、执行阶段、真实或历史成绩、决策理由和失败证据。复用 ObservationViewer，提供 GIF、曲线及原交互观察命令。已修正能力文档中“优化仍未实现”等过时说明。

## 运行与观察

最直接查看本轮已完成的闭环，无新仿真：

```powershell
conda activate softagent
python examples/workbench.py observe runs/round5_replay_complete
```

打开 <http://127.0.0.1:8765>；或直接打开 `runs/round5_replay_complete/index.html`。

新建一个只读历史闭环：

```powershell
python examples/workbench.py run --root runs/my_replay --replay-run runs/20260912T082002_895497Z_10d68758
```

具备可用 MATLAB 环境后，新候选评价的统一命令为 `python examples/workbench.py run`。本轮没有通过重复此命令追加尝试。恢复使用 `python examples/workbench.py resume <目录>`，不会重置预算。其余选项与未来模型接法见[使用说明](round5_workbench.md)。

## 实际验证与次数

| 验证 | 实际结果 |
| --- | --- |
| 第一次针对性单元检查 | `python -m unittest tests.test_workbench -v`：10 项通过，无后端调用 |
| 新增回放与无效 JSON 检查 | 只运行新增的 2 项，通过；没有重复全模块测试 |
| 新评价工作台 `runs/round5_demo` | 暂停、恢复、历史 JSON 读取、检查、分析及缓存复用通过；评价启动失败后引用错误并以 CAPABILITY_MISSING 停止 |
| 预定后端上限 | 1 次候选 / MuJoCo 尝试、2 次 MATLAB 分析预留；已消耗的预留未返还 |
| 实际新后端运行 | MATLAB 会话启动尝试 1 次；实际数学分析 0 次、MuJoCo 仿真 0 次、重试 0 次 |
| 真实历史闭环 `runs/round5_replay_complete` | 暂停恢复后，5 次工具执行、6 次决策，STOPPED；新后端预算及调用均为 0 |
| 证据与观察 | 两工作台 36 / 59 项证据哈希及源码快照校验通过；33 个页面链接存在；HTTP 200；51 帧 GIF 解码通过；1540×880 PNG 已目视检查 |
| 第三/第四轮实验与全量测试 | 均未重跑 |

新增实时评价在原 Harness 的 `model` 阶段启动 MATLAB 时出现：

```text
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xbe in position 129: invalid start byte
```

原始 `error.json` 和 `trace.jsonl` 完整保留，未推断更深层原因，也没有把失败包装为任务不成功。已用完本轮预留尝试，因此不再尝试修复后启动 MATLAB。

历史回放使用 `20260912T082002_895497Z_10d68758` 的封存 C1 运行。校验原文件、源码与 trace 后复制，设计为原 0.4 m / 8 segments / 4 tendons。原评价 `TASK_FAILED`，末端误差 **0.17116166894090315 m**，PCC 预测误差 **0.08714456960728613 m**。这些都是历史数值；**本轮任务成绩为 NOT_RUN**。决策器读取它们后实际执行了诊断读取与观察材料生成，随后停止。

回放导入开发过程中曾因复制目录名不符合旧 trace 的 run_id 校验而被拒绝；已改为保留原 run_id 目录并完成验证，没有数值调用或历史证据修改。

## 接入条件与缺口

**已具备固定 reach_free / C1 范围内的受限模型决策接入接口；已验证只读历史反馈闭环。新的实时数值闭环本轮未完成验证，仍受 MATLAB 启动问题阻塞。**

未来模型实现 `decide(context) -> Decision`，只能调用 catalog 的六个白名单工具。它不能写代码、改任务/评分/物理、增加预算、选择任意文件、启动旧实验或把回放变成新仿真。成绩仍来自既有评价程序。

目前没有真实模型 API、硬件、RL、跨工作台自动检索缓存、多候选设计搜索、C2 参数提案执行或标定物理模型。恢复以整次候选工具为边界，不支持仿真中途续积分；权限是应用边界，未来部署仍需隔离模型的本地执行权限。本轮没有追求任务必须成功。

## 便携证据

[验证记录](evidence/round5/verification.json)、[包清单与哈希](evidence/round5/package.json)、[完整两工作台](evidence/round5/workbenches.zip)包含失败尝试、已完成历史闭环、原始引用副本、源码快照、中文页面和 GIF / PNG。在仓库根目录解压到尚不存在的同名目录，即可用 observe 查看，无需重跑实验。

执行时 Git 提交仍为基线，dirty=true；每份快照与逐文件 SHA256 定位实际执行代码。失败工作台保存了回放功能加入前的源码，完整回放保存了最终执行源码，两份记录均保留，未追改版本证据。
