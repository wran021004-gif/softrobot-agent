# 调试顺序

1. **定义与能力**：`platform check <session.yaml>`。先处理字段／单位／版本，再处理缺失实现、环境／执行器／信号相位不兼容。catalog 的已声明、实现存在、依赖可用、获准和当前可执行各自独立。
2. **冻结输入**：`platform status <root> <run_id>`，随后读取数据库会话输入快照或 `context`。核对 task_version、实例、seed、时长、评价器和 allowed_tools；不要只查看已修改的模板。
3. **模型实际输入**：`platform inputs ...`。它输出 context_delivery 对应的原始传输载荷。context 只是预览；图片／视频路径不会成为 images_submitted。
4. **请求与回执**：`platform events ...`，按 request_id 和 execution_id 查请求链；`--parent <event_id>` 沿因果链筛选。rejected 表示没有执行，failed 表示执行出错，unknown 表示不能确认完成；completed 不是任务成功。
5. **资源**：`platform resources ...` 分别查看 limit、used、remaining、occupied。unknown 保留预留。只读查询不结算工作者；明确 collect／accept 才执行验收状态更新。
6. **原始数值证据**：用 output.artifact_id 运行 `platform evidence <root> <artifact_id>`。查看 BackendResult 的 solver_status、model_id、signal.spec、初态与 backend_data；原后端文件字节也作为不可变对象记录。
7. **评价与诊断**：分别检查 EvaluationResult.validity／task_success／metrics／constraints，以及规则的 status、sample_indices、source。缺数据不是无事件，任务失败不是数值无效，数值匹配不证明因果。
8. **恢复**：先运行 compatibility，再决定 resume。重复请求返回原回执；没有封存回执时保留 unknown，不通过换 ID 悄悄重做未知昂贵操作。

## 常见问题

| 提示 | 含义与处理 |
| --- | --- |
| CONTRACT_IMPLEMENTATION_REQUIRED | 负载契约或版本未登记；在扩展包补实现，不写动态 import |
| TOOL_NOT_GRANTED | 已实现但会话未允许；新策略／新会话才能改变冻结权限 |
| BACKEND_SIGNAL_PHASE_UNSUPPORTED | 例如 MATLAB 插值采样不能伪装 MuJoCo 步后状态；选匹配契约 |
| REQUEST_ID_COLLISION | 同一请求身份对应了不同参数或调用者 |
| RESOURCE_BUSY_OR_NOT_GRANTED | 资源容量不足或没有该资源声明；查看占用与未知预留 |
| DEPENDENCIES_CHANGED | 实际计算依赖已变；旧会话只读，使用新版本或显式迁移 |
| NO_SEALED_RECEIPT | 执行可能发生但无法核对；保留预算，检查外部日志和工作目录 |
| CONTEXT_LIMIT_REQUIRED_STATE_TOO_LARGE | 必需任务／权限／待执行信息无法压缩到限制；缩小工具范围或显式调整模型策略 |
| MODEL_KEY_MISSING | 本地未配置真实供应方凭据；离线接口验收仍可运行 |

导出页面按指标名称与单位显示，来源身份留在页面详情。旧工作台页面及原生视频／轨迹入口继续保留，不为调试或展示重新求解。

仿真事件还引用 `ExportBundle`，明确映射原始文件名与不可变内容身份。执行 `platform export-bundle <root> <bundle_artifact_id> <新目录>` 可恢复原始文件字节，再交给原有保存轨迹／原生回放入口；导出本身不改变项目数据库或重新求解。
