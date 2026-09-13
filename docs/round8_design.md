# 第八轮：持续设计与原生场景回放

基于第七轮提交 `b8ac5fd` 和随后实际运行的 `runs/round7_ready`。新分支为 `feat/round8-memory-native-replay`。原任务、评分、物理、数值流程及用户未跟踪文件保持不变。

## 直接使用

已准备 `runs/round8_ready`，包含两个旧候选的真实评价、历史请求、工作记忆、诊断曲线和新导出的原生场景 GIF。当前进程没有 `DEEPSEEK_API_KEY`，因此状态为 `WAITING_FOR_KEY`，本轮未发送真实模型请求。

在有密钥的普通 PowerShell 中运行：

```powershell
conda activate softagent
$deepseekSecret = Read-Host 'DeepSeek API Key' -AsSecureString
$env:DEEPSEEK_API_KEY = [System.Net.NetworkCredential]::new('', $deepseekSecret).Password
python examples/workbench.py resume runs/round8_ready
```

另一个终端查看中文工作台：

```powershell
python examples/workbench.py observe runs/round8_ready
```

打开 <http://127.0.0.1:8765>。页面展示每次实际请求的模型/思考参数、响应模型、token 用量、输入字节组成、决策依据、工具反馈、工作记忆，以及历史和本轮各自的预算。旧请求当时关闭思考，仍按真实请求显示 `disabled`，不会被当前配置覆盖。

## 原生 MuJoCo 回放

```powershell
python examples/native_replay.py runs/round8_ready --candidate c001
```

省略候选时默认选择最佳已评价候选；也接受 `attempts/.../execution/<run_id>` 原数值运行目录。原生窗口支持：

- 空格：暂停/继续；结束时停在最后保存状态。
- 左右键：暂停并逐帧；R：回到开始，暂停时再按空格播放。
- 鼠标拖动：旋转/平移；滚轮：缩放；关闭窗口退出。

窗口显示保存 XML 中的机器人实体、真实腱线位置、红色目标和场景。腱线原本位于外壳内部，因此显示层使用半透明外壳、彩色腱线和较亮头灯；不移动几何、不修改保存模型或物理参数。

原生场景导出：

```powershell
python examples/native_replay.py runs/round8_ready --candidate c001 --export runs/my_native_export
```

选择新输出目录；已有同名导出不会覆盖。生成 `native_scene.gif`、最终帧 `native_scene.png` 和 `native_replay.json`，后者记录原模型/轨迹哈希、实际选取的保存帧索引、时间戳和 GIF 帧时长。已导出的本轮结果位于 `runs/round8_ready/observations/c001/`，中文页面可直接播放，旧诊断曲线继续保留。

回放复用 `load_observation` 和保存的 `robot.xml`，按保存时间取对应 qpos；只更新运动学和腱线显示，不调用 `mj_step`、控制器或评分器，也不插值生成新状态。原生窗口使用 `launch_passive` 和 `sync(state_only=False)`；官方说明 `state_only=True` 会调用 `mj_forward`，所以这里不使用该模式。导出使用 MuJoCo `Renderer`，不是把诊断曲线换个标题当原生画面。依据：[MuJoCo Python/Passive viewer 文档](https://mujoco.readthedocs.io/en/stable/python.html#passive-viewer)。

模型后续调用 `observe_candidate` 时，既有曲线导出仍执行，同时尝试导出原生场景。若本机 OpenGL 不可用，会保留曲线并在工具结果里明确报告原生导出失败及原生查看命令；不会据此重新仿真。

## 输入、工作记忆和证据读取

实际问题不是输入上限过低：第七轮新增 11 次请求全部读取证据，其中 7 次复用旧读取结果。目录与评价首页在两次往返重建会话后反复出现。`eval:c001 /data` 有 16 个键，但默认只返回前 10 个，诊断没有随首页返回；57 条候选目录的后续大页又被截成 JSON 文本片段。

本轮不再根据 `context_turns` 重建对话。完整 assistant/tool 消息持续回传，仅在序列化请求达到 `max_input_bytes × context_compact_ratio` 时整理历史，保留落盘原始请求与回复。默认阈值为 60,000 × 0.85 字节；整理后从工作记忆和权威候选状态开始新会话，不裁剪正在回传的思考字段或拆散工具交互。

每次模型工具调用附带简短 `working_memory`：`findings`、`unresolved`、`next_action`、`evidence`。这些是有引用的工作笔记，单项最长 300 字，不是完整思考过程，也不改写评价真值。程序额外维护 `working_memory.reads`，包括已读选择器、实际返回的部分事实、历史决策序号、结果引用和未读分页/分片位置。暂停、恢复和输入整理均保留这些记录，创建本轮时也从第七轮真实读取记录重建。

重复读取相同字段或页时，工具反馈明确返回 `REPEATED_READ` 和先前读取位置，说明没有新增实验信息，提示使用已有发现推进修改、比较或停止；没有人为禁止模型读证据，也不会伪造新发现。

候选摘要直接给出 `diagnostic_entries`，例如：

```json
{"evidence_id":"eval:c001","pointer":"/data/diagnostics/compare_model_sim"}
```

无需先遍历目录。评价根或 `/data` 返回完整基本评价摘要和诊断入口，默认不会把它拆成“前十个字段”。小诊断对象能放入字节上限时完整返回。`catalog:c001 /entries` 只返回能放下的完整条目；使用实际 `next_offset` 继续，不能自行加请求的 limit 跳过条目。若单个条目仍放不下，返回所需字节数，不把半截 JSON 当完整条目。

原始大字段仍支持 JSON Pointer 和有明确格式标记的字节分片。完整数据、原始评价、模型回复和目录都留在结果文件中。本轮首次待发送请求预览为 **28,519 字节**，包括继承读取记忆和完整诊断入口，低于保留的 60,000 字节上限。

## 思考模式和官方协议

默认配置现在是：

```yaml
model: deepseek-flash
thinking: enabled
max_tokens: 8192
max_input_bytes: 60000
context_compact_ratio: 0.85
model_calls: 12
```

继续使用单个决策模型。思考模式下不发送 `temperature` 或强制 `tool_choice`；工具选择通过提示词和原有决策验证约束。按官方 V4 兼容说明，强制 `tool_choice` 在思考模式下可能导致拒绝。保存响应原始 `reasoning_content`、`content`、`tool_calls`，回传时完整保留思考内容，必要时仅把 nullable content 转为空字符串。协议字段存于响应文件，页面只展示简短行动依据。依据：[DeepSeek 思考模式](https://api-docs.deepseek.com/guides/thinking_mode/)、[官方 V4 工具兼容说明](https://api-docs.deepseek.com/quick_start/agent_integrations/oh_my_pi/)。

**开启模式的协议、暂停恢复和多轮回传已用注入传输验证；真实 API 尚未验证，因为当前进程无密钥。** 不能把注入响应或原生渲染结果算作真实模型设计。本轮已冻结的配置直接由 `resume` 使用，之后修改仓库 YAML 不会暗中修改运行请求。

## 独立预算与历史保留

`runs/round8_ready/request.json` 的 `round_budget` 独立记录本次用户授权；旧 request/state/源码快照等保存在 `lineage/`，旧的请求和尝试数组继续保留。预算按累计记录减去明确的本轮起点计算，不清空历史数组。

| 资源 | 已继承历史消耗 | 本轮新增上限 | 本轮实际新增 |
| --- | ---: | ---: | ---: |
| 模型请求 | 18 | 12 | 0 |
| 候选 | 2 | 1 | 0 |
| 仿真 | 2 | 1 | 0 |
| MATLAB 数学调用预留 | 6 | 3 | 0 |
| 工具执行 | 12 | 16 | 0 |
| 决策 | 20 | 16 | 0 |

本轮原生渲染直接读取保存数据，没有向模型或数值执行器提交新实验。12 次新模型请求耗尽后，累计记录会达到 30 次；旧任务的 18 次请求仍显示为已耗尽。

首次建立本轮的命令为：

```powershell
python examples/workbench.py round runs/round7_ready --root runs/round8_ready
```

**本工作区已经执行过，后续直接 resume。** 一次性账本 `runs/round8_budget.json` 绑定本次授权与运行目录；再次 `round` 会指向已经分配的运行。该轮不通过 `continue` 再导入，复制目录也不能领取新预算。保留账本，不能通过删除或改写它重置授权。计算兼容检查仍覆盖旧证据哈希、候选、原运行封存记录、数值源码、任务/评分/物理和依赖版本。

## 实际验证与限制

仅运行 `python -m unittest tests.test_round8 -v`：四项针对性检查、四次执行，均通过。覆盖基本评价/完整目录页与继承读取记忆、思考多轮工具回传及按字节整理、独立预算扣减与重复导入限制、原生保存状态渲染且禁用 `mj_step`/`mj_forward` 的检查。没有全量测试或重跑旧实验。

原生窗口实际启动并关闭，观察约 3 秒。完成两次完整 GIF 导出：首次视觉检查发现外壳遮挡腱线，第二次只调整显示层后确认腱线可见。最终 GIF 为 51 帧；130 个页面文件链接有效；旧登记证据哈希保持不变。数值仿真、MATLAB 调用和真实模型请求新增均为零。详见[验证记录](evidence/round8/verification.json)。

开发、协议检查和原生回放已完成；**真实思考模型的设计推进尚待密钥联调**，不会声称反复查资料问题已通过真实模型验收。最佳继承候选仍是 c001，真实误差 **0.12187854248137178 m**，冻结阈值 **0.01 m**，机器人任务未达标。输入组织和提示能减少重复读取，但不保证模型一定选择新候选或改善精度。

[保存证据包](evidence/round8/workbenches.zip)包含最新第七轮实际记录、第八轮待联调运行及一次性预算账本。仅在对应路径不存在时恢复，已有运行与账本继续保留；不要用打包时的零新增用量覆盖之后已经发生的请求记录。
