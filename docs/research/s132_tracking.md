# S132：可选时间约束的独立 Tracking

基于已验证并推送的 S131 `8af4ab82337ebcb2fceb6f6ce835f3e29e49d0d3`。按用户后续澄清，默认是**几何路径正确即可，不要求在指定时刻到达**；又按“有无时间都可以”的要求，增加独立可选的 timed 模式。没有重开 F3、调用 Provider、启动 NMPC/PPO 或进行物理 rollout。

## 经过 Codex 人工审查的开发配置

完整配置：[默认无时间样例](../../tasks/tracking_linear_development.json)、[可选有时间样例](../../tasks/tracking_timed_development.json)。两者均为 `status=draft`、development seed 17，不是正式科研批准或 `development_valid`。

| 字段 | 默认几何模式 | 可选 timed 模式 | 来源与理由 |
| --- | --- | --- | --- |
| 独立任务/评价器 | `task.tracking@1.0.0` / `evaluate.tracking@1.0.0` | 同左，模式显式区分 | 本次注册，不伪装为 Reach |
| 参考坐标/单位 | world / m | world / m | 复用原 tip_position 信号规范 |
| 三个路径点 | `[0.30,0,0.15]` → `[0.31,0.01,0.16]` → `[0.30,0.02,0.15]` m | 同左 | Codex 暂定的小幅三维折线，便于离线复算；未证明物理可达 |
| 时间约束 | `time_requirement=none`，不允许携带节点时间 | `timed`，节点时间 `[0,0.20,0.40]` s | 默认来自用户澄清；timed 是按用户要求保留的可选能力 |
| 初态 | 原参考中的全部具名 qpos/qvel 为零，unspecified=zero | 同左 | 从 `tasks/reach_hold.json` 原样复制 initializer；实际机器人绑定仍需原准入 |
| 环境 | 原固定 world 环境、mount `[0,0,0.15]` m、重力 `[0,0,-9.81]` m/s²、external_forces=[] | 同左 | 复用原可信场景；没有新增碰撞/接触或扰动验收 |
| 插值 | 按几何线段连接，行进顺序从起点到终点 | 按节点时间分段线性插值 | 两种参数化不互相推导 |
| 空间容差 | 0.004 m | 0.004 m | Codex 暂定开发值，独立于 F3 的 10 mm / 20 mm/s 标准 |
| 几何复算分辨率 | 弧长间隔不大于 0.001 m | 不用于 timed 误差 | Codex 暂定，可复算；决定几何诊断分辨率 |
| 采集配置 | integration 0.001 s、control/sample 0.02 s、名义记录长度 0.40 s | 同左 | 开发样例参数；**几何评价不检查完成时长，不裁剪到名义时间窗** |
| 评价范围 | 完整保存的有序位置折线；时间戳仅保留原观测身份与顺序 | `[0.02,0.40]` s 含端点，20 个完整 post-step 样本 | 几何模式无到达期限或速度要求；timed 才检查对应时间网格 |

首版支持一条直线或两段开放折线。几何模式拒绝重复零长边、重叠回折、隐含节点时间；更长折线与闭环没有在此版本中宣称支持。timed 的节点时间严格递增，可表达停留或反向段。两种模式都不自动添加绝对速度/保持速度阈值。

正式科研仍需研究者确认参考路径、空间容差、几何分辨率、允许的回退/噪声、观测完整性及实际执行预算。只有选择 timed 模式时才需确认相应节点时间和评分窗口；默认几何任务不存在这些时间验收要求。

## 独立评价与证据身份

`reference.tracking_goal` 与 `reference.tracking_evaluation` 由原 Registry 解析，`tools.platform_tasks.check_definition` 校验任务、单位、世界坐标和所需 post_step 末端位置。评价器读取保存的 BackendResult，保留原 source、evaluator/version、comparison_identity；正式 `evaluation.run` 仍由既有工具追加 execution/candidate 身份。测试夹具明确标为 synthetic，不进入真实研究 Store。

几何模式将保存位置解释为有序折线，在均匀弧长网格及原顶点计算到参考线段的最近距离，并反向检查参考路径覆盖。硬检查为最大路径偏差、参考覆盖误差、起点误差、终点误差和最大累计路径进度回退；开发样例暂统一采用 4 mm。RMS 是均匀弧长误差的诊断，不以记录时间或停顿次数加权。这里检查的是保存折线的几何采样表示，不能证明缺失观测间的真实物理轨迹或连续时间性能。

timed 模式计算保存时间 `t_k` 下的 `||p_k-p_ref(t_k)||`，最大误差为硬检查，算术 RMS 与终点误差为诊断；校验完整时间网格和含端点评分窗口。未完成 solver、无位置信号或样本不足返回 incomplete，错误单位/坐标/相位或 timed 错误网格返回 invalid；它们的 task_success 为 null，不伪装为普通任务失败。有效保存轨迹违反几何/误差条件才返回 valid + false。几何模式允许不同持续时间、非均匀时间戳和停顿；稀疏观测只能证明其保存折线，不能据此声称完整原物理轨迹正确。

测试包含完全匹配、2 mm 法向偏移、同最大误差而 RMS 不同、单点 6 mm 越界、截弯、静止、逆序、回退、缺失/无效证据，以及 0.1/4/100 s 的不同重参数化。数值见 [离线验证记录](../../evidence/s132_tracking/validation.json)。

## SOCP/T2：两种模式的真实数学支持

复用现有 `TaskAnalysisRequirement`。timed 生成原 `norm_bound`，每个样本绑定自己的参考值；旧 Reach 和旧 norm-bound 语义不变。无时间模式新增独立 `PathAnalysisConstraint(kind=path_bound)`，保留原路径、空间容差和物理输入上下界，**reference 列表为空，不伪造逐时刻目标**。

无时间 SOCP 联合优化真实张力 `U` 和无量纲路径进度 `s_k`：

`||p_k - P(s_k)|| <= epsilon * (1+t)`，`0=s_0 <= ... <= s_N=1`。

单线段是一个凸锥子问题。两段折线枚举可行的拐点采样边界，每个子问题要求访问拐点并按顺序前进；拐点时刻由求解选择，不写入任务参考。它没有用凸包替代折线，也没有只检查终点。每个子问题保留真实物理输入箱与独立状态重放，并检查进度上下界/单调性、完整 KKT、对偶锥、互补与支撑下估计。只有全部子问题完成数值检查后才报告跨离散分支的数值最优性；没有严格浮点或非线性证书。

新增算法语义标识为 `sampled-affine-conic-path-progress-v1`，旧 timed/norm 算法保留 `sampled-affine-conic-minimax-v1`。真实张力数组始终只有真实腱通道，进度单独输出为 dimensionless；没有增加虚构腱或把进度当成 N。

无时间任务的有限分析时域只是构造数值见证的选择。时域太短或当前局部模型未找到解，**不能证明不限完成时间的任务不可行**。折线拐点只在所选采样网格上枚举，不声称求解任意连续拐点时刻。当前 free-progress sampled tube 也不替代独立评价器的几何覆盖/回退检查，因此适用性报告仍将 `full_task_supported=false`，单独报告哪些数学采样约束被覆盖。

T2 新语义为 `controlled-path-progress-sensitivity-v1`，使用原受控参数 stencil 和精确来源/坐标/输入绑定。每个参数点重新优化张力和自由进度；对照诊断才固定基线张力及基线进度。进度约束乘子进入 stationarity、包络贡献和近最优对偶面；拐点最优分支切换或并列时，只给方向比较，不伪称单一导数。数值对偶面 unresolved 时保留该状态，有限差分一致不升级为严格梯度。原 timed T2 保持原算法版本和结果语义。

解析合成夹具 `x_dot=d*u`，`u∈[0,1] N`、`d=0.5 m/(N*s)`、所选时域 1 s、路径 0→1 m、容差 0.1 m，得到 `V=4`、重优化灵敏度及包络约 `-10 (N*s)/m`；同一有时间夹具的早期瓶颈灵敏度约 `-2.5 (N*s)/m`。这些是显式合成增益模型，**不是机器人长度/材料敏感性结论**。折线见证夹具自由选择中间采样边界；只会沿对角线移动的模型即使能到终点，也因无法经过折角而失败。

每次内部锥求解均计数。例如 5 个采样点的两段路径枚举 3 个子问题；五个参数点的 T2 进行 15 次锥求解，另记对偶面求解。默认 21 点数学网格有 19 个拐点子问题，不能仍按一个内部 solve 描述。新 free-progress 版本未借用 F3 旧 grant 获得正式 Study 执行权限。

## 生产接口与未支持范围

| 层次 | 当前状态 |
| --- | --- |
| 任务/独立评价器 | 已实现、以合成保存轨迹验证；默认几何、可选 timed |
| Task Adapter / 数学契约 | 两模式均已接通；world/m、源身份和真实输入边界保留 |
| 已保存、精确绑定的 affine 模型 + SOCP | timed norm-bound 可算；free progress 可算，简单折线枚举，已离线验证 |
| T2 数值内核 | 两模式均已离线验证；仍需完整受控模型组，分支/对偶面不确定性明确保留 |
| 原 SLSQP sampled kernel | timed 固定参考可用；free-progress 不支持，明确拒绝，不降级成 Reach |
| 机器人模型构建器 | 当前 GVS/SoRoSim builder 仍读取固定 target_m、依赖 Reach 控制准备；Tracking 自动构建 not_applicable |
| backend.family_mujoco | 已有 world/m/post_step tip_position 信号；原 families=['task.reach'] 与执行准入未改 |
| GVS / SoRoSim NMPC、现有 PPO | `tracking_controller_support=unsupported / not_yet_verified`；未改目标函数或训练 |
| 物理重放与组合验收 | Tracking 在进入物理构建前明确拒绝；组合验收不借用 offline_reach_hold_v1，也不宣称已有可执行 offline_tracking 协议 |
| Agent / S130 | 研究自主选择和会话系统未改；S130 报告已注册定义，但 N2 仍 Reach-only、executable=false，不自动映射圆形等未支持请求 |

`tools.research.analysis` 和原正式数学准入对 Tracking 的机器人 worker 路径继续返回 not_applicable，避免注册任务后直接读取 target_m、误用原授权或收费。这里的成果是独立任务、评价器、已有模型上的两模式数学内核与准确能力报告；不是完整自主 Tracking Study 或真实控制成功。

## 验证与规模

相关离线回归 **172 项通过**，覆盖两模式 Tracking、原 SOCP/T2、原 Reach/Task Intake、独立证据、F3 修复及局部控制搜索。最后的小范围变更另外重跑 Tracking/数学契约测试；准确次数见 validation.json。Clarabel 一项近最优对偶面返回 optimal_inaccurate，代码正确保留 envelope unresolved，测试未把它当作导数证明。

复算入口：`python -m unittest tests.research.test_tracking tests.research.test_tracking_math tests.research.test_conic_capability tests.research.test_capability_sensitivity`。Windows 运行旧数学契约测试还需 `PYTHONPATH=.;tests/research`。使用现有 `.f3-prestudy-env`，没有安装依赖或发起真实科研。

核心改动超过最初 150–350 行建议，原因是用户追加了自由进度的 SOCP/T2 适配：决策变量维度、独立重放、硬进度约束 KKT、折角离散分支和 T2 对偶面必须同步处理，否则会错误标注物理输入或漏掉最优性条件。实现集中在既有 contracts/implementation、trajectory/conic/sensitivity 和 task adapter 文件，没有新增业务 manager、Agent、审核程序或第二套 Store/配置加载器。
