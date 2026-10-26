# C3.2 后续小修复：执行入口与成本说明

2026-10-26，Asia/Shanghai。用户授权“C暴露出来的问题如果可以顺手修复可以直接修复并记录修复”。从已完成 A 外力集成 `6e8a963523bbe884928f7104870d0018f227dca7` 新建独立 `codex/c33-execution-feedback` 分支；保留原 C3.2 Control、Treatment、输入、评分和真实输出。

## 原问题与修复

C 的真实输出出现三种相关错误：N 把 Plan control_search 当作 Native 数学执行并声称物理零；K 用 diagnose/diagnostic=null 和自由文字 selected_method 表达希望运行 Native；N Treatment 另在 settings 中提交不存在的 regularization。原执行器没有按方法文字自动执行的漏洞；但字段级 Schema 对路由、额度与授权的说明不足，非法 regularization 反馈也没有专门指向实际设置契约。

仅改两处生产文件：

- `tools/research/contracts.py`：selected_method 明示只表达意图、不派发或授权；requested_budget 明示请求上限不是实际费用/权限，未知费用与缺失正式 scope 仍待准入；evaluation_requests 区分 physical replay 回调与 Native 克隆轨迹积分。
- `tools/research/agent.py`：Plan 工具说明补充 control_search 与 Native research_analysis 的入口区别。对 settings.regularization 的 extra_forbidden，原拒绝反馈保留，并从 LocalControlSearchSettings 的实际字段生成合法列表，提示使用注册 request_template 与原授权/成本准入。不会自动删除参数、改请求、改路由或执行。

未新增字段、方法、优化器、记忆或调度器；不解析自由方法文字来替模型选实验。diagnose 仍允许表达后续方法意图而只读诊断。原数学 scope、预算检查、实际成本账本和独立验收代码未改。模态估计过度解释、科研路线选择及是否遵从提示仍是模型判断问题，本补丁不宣称已解决。

## 验证

三项新增零执行回归，加两项直接受影响的原回归，共 **5 项通过**（unittest 2.267 s；进程耗时约 5.44 s）：

1. Provider 实际 Schema 投影保留路由、权限和费用说明。
2. Plan control_search 与 Native 共用设置的非法 regularization 仍拒绝，返回精确字段路径和真实合法字段，无科学执行或 Store 预算写入。
3. 无关非法字段保留原错误，不误给 regularization 纠错。
4. 原 Schema/runtime 的动作、intent 与 payload 关系保持一致。
5. 原 diagnose 回归确认不派发 Native、不计数学费用、状态不变，原执行入口查询仍可读取。

另核对 contracts 的 AST：移除 Field.description 元数据后与修复前完全一致，证明没有改变字段域、验证或序列化语义；diff 空白检查通过。新增 Provider、Tokens、数学/物理积分、NMPC/RL/Reporter 均为 0。没有重跑 C3.2、MockTransport、全仓测试或外力重型检查。

## 集成与后续

本补丁作为单独提交接入 A 集成分支；原 C3.2 结果分支保持只读结果记录。修复记录不覆盖 C 的负结果，也不把 5 项工程检查写成科研判断改善。后续若验证模型是否因此选择更好实验，需独立新任务/输入、授权及预算；不得在原冻结集反复刷分。
