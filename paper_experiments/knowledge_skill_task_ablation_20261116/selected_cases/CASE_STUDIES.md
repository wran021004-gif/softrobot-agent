# 代表性科研 Trace

六项案例各保留四条件原始决策与 Core 回执压缩日志，共 24 条详细轨迹。完整 44 单元均在总表和 episode_manifests 中，选择案例不改变总样本。

“未正式选择”包括完整未通过、部分/无效计算和时间终止，须按原生回执区分。下列过程引用来自模型公开决策；数值验收由原生证据独立核对。

## T03：Knowledge 条件对照：快速到达与稳定保持

通过模式 0/1/0/1。K+S− 的 core-295 指出数学预测已满足模型阈值，随后物理结果 9f9958f9… 获得验收；core-299 区分数学结果、物理验收和冻结确认要求。该单元没有 experience_retrieve 记录，故它支持 Knowledge 开关与结果的对应关系，不能作为某条 Knowledge 被读取并改变机制的实例。

|条件|验收及 SELECT|候选数|数学计数|物理计费次数|
|---|---|---:|---:|---:|
|K−S−|未选择|19|39|16|
|K+S−|通过|14|29|15|
|K−S+|未选择|12|18|20|
|K+S+|通过|9|26|5|

初始公开任务、科学模型、约束和初态身份详见各条件清单。每次 generate 的参数、假设与返回引用保存在 CANDIDATE_INTERVENTIONS.csv。

- [K0S0 清单](../episode_manifests/T03/K0S0.json)，原始目录 `episodes/T03/K0S0`，最终证据 `25bf5d1eac4616a407f5fda6bc2744df285f1cc6b115b3e2b9e54fcf2b27fdd0`。
- [K1S0 清单](../episode_manifests/T03/K1S0.json)，原始目录 `episodes/T03/K1S0`，最终证据 `9f9958f9be3092700644028d70ee5615cc33bdc095a3ef6d856a32c535b6962a`。
- [K0S1 清单](../episode_manifests/T03/K0S1.json)，原始目录 `episodes/T03/K0S1`，最终证据 `b1325331f9b532f190fcbc461ef996f9d4966d791ebe6b710f4bb9e77b31c816`。
- [K1S1 清单](../episode_manifests/T03/K1S1.json)，原始目录 `episodes/T03/K1S1`，最终证据 `c8cc7248212d0e20e0245701381d7467f20fb375a07e256f663642b464b7391f`。

## T05：Knowledge 可用性与空检索对照

通过模式 0/1/1/1。K+S− 的 core-8、core-9 先按任务和结构检索，再调整到 position_tool_axis 标签，两次均未取得资源正文，之后继续实际生成与计算。该案例保留了未奏效的检索，不把资源可用性当成成功迁移。

|条件|验收及 SELECT|候选数|数学计数|物理计费次数|
|---|---|---:|---:|---:|
|K−S−|未选择|3|3|5|
|K+S−|通过|2|3|3|
|K−S+|通过|5|11|3|
|K+S+|通过|10|19|4|

初始公开任务、科学模型、约束和初态身份详见各条件清单。每次 generate 的参数、假设与返回引用保存在 CANDIDATE_INTERVENTIONS.csv。

- [K0S0 清单](../episode_manifests/T05/K0S0.json)，原始目录 `episodes/T05/K0S0`，最终证据 `4eb787abbd500679946b9af155cffafe00fd7fd0e939af93002def40cdeab3b6`。
- [K1S0 清单](../episode_manifests/T05/K1S0.json)，原始目录 `episodes/T05/K1S0`，最终证据 `f30366bf9ab9dd9901a08d66eab04c6bb45a3ac6912cb987ad267c81572a36cb`。
- [K0S1 清单](../episode_manifests/T05/K0S1.json)，原始目录 `episodes/T05/K0S1`，最终证据 `5684e48cd8cea088e2b6ad95879c2722c4c633d850fa55c5d1dcb3fce1a0548e`。
- [K1S1 清单](../episode_manifests/T05/K1S1.json)，原始目录 `episodes/T05/K1S1`，最终证据 `d1bb2007e463d3bff377b8f16c55230082e4252c9583903588bd6dc3951420ba`。

## T01：Skill 条件对照：同结构多工况验证

通过模式 0/0/1/1。K−S+ 的 core-897 正式选择同一物理结构 91a964c0… 上的 central_high、negative_low、positive_high 三个完整通过结果。core-895 记录 central 数学预测的保持误差 0.00999836 m 和腱速上限附近的诊断结果，随后才执行物理验证。本单元没有单独 Skill 正文读取，结构化验证过程可复现，其资源因果归因仍未知。

|条件|验收及 SELECT|候选数|数学计数|物理计费次数|
|---|---|---:|---:|---:|
|K−S−|未选择|67|84|9|
|K+S−|未选择|135|300|46|
|K−S+|通过|125|191|23|
|K+S+|通过|12|13|16|

初始公开任务、科学模型、约束和初态身份详见各条件清单。每次 generate 的参数、假设与返回引用保存在 CANDIDATE_INTERVENTIONS.csv。

- [K0S0 清单](../episode_manifests/T01/K0S0.json)，原始目录 `episodes_full_corrected/T01/K0S0`，最终证据 `21fe7742be270b8ea64565a96cfbb9098d7ac09c1fe6ad6c3c0c74e3ff20382a`。
- [K1S0 清单](../episode_manifests/T01/K1S0.json)，原始目录 `episodes_full_corrected/T01/K1S0`，最终证据 `1b9d07ad000a2088f305ca4dd856b5d4d9414db4944739a8e2fce1f3fb7a4770`。
- [K0S1 清单](../episode_manifests/T01/K0S1.json)，原始目录 `episodes_full_corrected/T01/K0S1`，最终证据 `b28282d1ff01989d545dc61bcd6a93d781ef7961bf6330455400f68bcfa9acf7`。
- [K1S1 清单](../episode_manifests/T01/K1S1.json)，原始目录 `episodes_full_corrected/T01/K1S1`，最终证据 `cf0fbb244a8cce87b8ce4496d48c3f758cdacc402dfaa64d7fe29a97161e3ea1`。

## T04：Skill 条件对照：跟踪控制与完整回放

通过模式 0/0/1/1。K−S+ 的 core-139 注册 295 节点控制源，core-141 根据独立回放 6efc7adf… 正式选择。回放记录 RMSE 0.002306789 m、最大误差 0.003424919 m、周期漂移 0.000402252 m。研究轨迹显示了方法构造、计算与物理验收的顺序，但没有 Skill 正文读取记录。K+S− 的终态是时间终止，不能写成已穷尽所有可行科学方法。

|条件|验收及 SELECT|候选数|数学计数|物理计费次数|
|---|---|---:|---:|---:|
|K−S−|未选择|9|106|8|
|K+S−|未选择|18|82|11|
|K−S+|通过|7|14|8|
|K+S+|通过|13|284|9|

初始公开任务、科学模型、约束和初态身份详见各条件清单。每次 generate 的参数、假设与返回引用保存在 CANDIDATE_INTERVENTIONS.csv。

- [K0S0 清单](../episode_manifests/T04/K0S0.json)，原始目录 `episodes_full_corrected/T04/K0S0`，最终证据 `2b5a269790aa33ae7cfe24f20b3409d3eade82b8867cea66116a84fbcfa3de92`。
- [K1S0 清单](../episode_manifests/T04/K1S0.json)，原始目录 `episodes_full_corrected/T04/K1S0`，最终证据 `91bb9933ce3f8e52516ebe89f952de75667ff21d7c9e4a6fb7249baf93691547`。
- [K0S1 清单](../episode_manifests/T04/K0S1.json)，原始目录 `episodes_full_corrected/T04/K0S1`，最终证据 `6efc7adff5bd54b2318b65e1982bd811494e773139aefdfaa3a55f31ebd16688`。
- [K1S1 清单](../episode_manifests/T04/K1S1.json)，原始目录 `episodes_full_corrected/T04/K1S1`，最终证据 `66257236d61f72b99fe4754f2e3eee5b009840ef672425ddd1720310402df8e3`。

## T09：非单调对照：基线与联合条件通过

通过模式 1/0/0/1。K+S+ 的 core-192 将控制源绑定到当前候选，core-206 根据完整回放 2f78173b… 正式选择：按压位移 0.00206324 m、有效保持 0.5 s、最大力误差 0.003039 N、最大腱速 0.0170621 m/s。两个单资源条件未通过并不建立资源有害的机制；本任务不支持“每个任务均有单调增益”的说法。

|条件|验收及 SELECT|候选数|数学计数|物理计费次数|
|---|---|---:|---:|---:|
|K−S−|通过|14|0|35|
|K+S−|未选择|24|0|40|
|K−S+|未选择|22|0|23|
|K+S+|通过|7|0|21|

初始公开任务、科学模型、约束和初态身份详见各条件清单。每次 generate 的参数、假设与返回引用保存在 CANDIDATE_INTERVENTIONS.csv。

- [K0S0 清单](../episode_manifests/T09/K0S0.json)，原始目录 `episodes_full_corrected/T09/K0S0`，最终证据 `5c246173ce5664e84ab7be88b0497fef5b79f781f72f68ec526b66bdff720cbe`。
- [K1S0 清单](../episode_manifests/T09/K1S0.json)，原始目录 `episodes_full_corrected/T09/K1S0`，最终证据 `02c66e3bcbef726faca191ccebb3bf89827791136b2b849679c8d787f93e8939`。
- [K0S1 清单](../episode_manifests/T09/K0S1.json)，原始目录 `episodes_full_corrected/T09/K0S1`，最终证据 `12738e09565f1333c3a86b34c4bdd9d499c656e3993336b047053aa353587500`。
- [K1S1 清单](../episode_manifests/T09/K1S1.json)，原始目录 `episodes_full_corrected/T09/K1S1`，最终证据 `2f78173b43cc40cc0505b3f5d33d6ad7acead9363a0149dc6eb4298679422a6d`。

## PHS2D：联合条件特有通过：完整十工况物理结果

通过模式 0/0/0/1。core-407 生成 F8D，明确改变对称弯曲黏性 0.00010→0.00011 N·m²·s，之后完整十工况结果 73ae20f6… 被原生验收并在 core-861 正式选择。该案例显示联合条件的特有终态和可追溯机制干预；没有单独 Knowledge/Skill 正文检索链，因此不能把终态差异本身写成已证实的双资源协同机制。

|条件|验收及 SELECT|候选数|数学计数|物理计费次数|
|---|---|---:|---:|---:|
|K−S−|未选择|8|12|80|
|K+S−|未选择|9|19|50|
|K−S+|未选择|2|7|80|
|K+S+|通过|13|7|110|

初始公开任务、科学模型、约束和初态身份详见各条件清单。每次 generate 的参数、假设与返回引用保存在 CANDIDATE_INTERVENTIONS.csv。

- [K0S0 清单](../episode_manifests/PHS2D/K0S0.json)，原始目录 `episodes/PHS2D/K0S0`，最终证据 `7700403579a9c9d56f391e627ea1400740ff26a42e1852dba87984f0bc879b04`。
- [K1S0 清单](../episode_manifests/PHS2D/K1S0.json)，原始目录 `episodes/PHS2D/K1S0`，最终证据 `769ca78656afadc186a4b5f69d83abb87619f69909e6a88b6bf95bc32ba411c9`。
- [K0S1 清单](../episode_manifests/PHS2D/K0S1.json)，原始目录 `episodes/PHS2D/K0S1`，最终证据 `651755686b68c452582905389aac61057700ba4e82297973cd7f3ecf5ce380fa`。
- [K1S1 清单](../episode_manifests/PHS2D/K1S1.json)，原始目录 `episodes/PHS2D/K1S1`，最终证据 `73ae20f6ad14e4f374d724c17bcd568af9d48e07397c8ad104b69ebd41cb08ca`。

## 有实际正文读取的补充链

T02/K+S+ 的 core-23 精确读取 diagnostic-static-dynamic@2，core-24 自述采用静态能力与动态验收分离的诊断，随后查询 equilibrium 能力。这支持一条明确的经验到诊断操作链，尚未独立量化其对最终通过的贡献。

T10/K−S+ 的 core-29 精确读取 skill-parameter-model@4，core-30 明确引用并生成只改变 max_iterations 的匹配干预，后续仍未正式通过。这是 Skill 改变操作组织的可追溯实例，也避免把程序变化与任务成功混为一谈。

T10/K+S+ 的 diagnostic-convergence@2 被明确评为 context_only，模型自述未改变假设或动作。这条中性读取与两次空查询及一次未返回正文的读取都保留在资源总表中。

T07 和 T10 的 K+S− 通过而两个无 Knowledge 条件未通过，但它们同样没有独立正文检索记录，因此列为条件层面的 Knowledge 候选而非已证实的经验迁移。T06 四条件都通过，其成本对照见总表与图 5。
