# 第二、第三 Gateway 账号真实推理验证

2026-11-06，用户明确批准两个账号发送模型推理请求并允许自行选择型号。
两账号登录和 ChatGPT plan usage 均通过，且真实短文本推理最终均成功。
本轮未创建科研 Study，没有验证新账号的 function tools 或科研决策能力。

| 账号 | 地址 | 目录 | 型号 / reasoning | 首轮 | 修复后受控复验 | 当前 PID |
|---|---|---|---|---|---|---:|
| Account2 | 127.0.0.1:8788/v1 | HTTP 200，8 型号 | gpt-5.6-luna / none | 502 empty_response | HTTP 200，OK，15 tokens | 166208 |
| Account3 | 127.0.0.1:8789/v1 | HTTP 200，8 型号 | gpt-5.6-luna / none | 502 empty_response | HTTP 200，OK，15 tokens | 94940 |

两份目录均包含 gpt-6.1-sol、gpt-6-astra、gpt-6.1-terra、gpt-6-sol、gpt-6-luna、
gpt-5.6-sol、gpt-5.6-terra、gpt-5.6-luna。选择的是目录实际存在且已有 none 支持依据的 Luna，
未根据目录排序选择，也未声称它在 ChatGPT plan 下最便宜。其余七个型号未逐一推理验证。

## 首轮失败及最小修复

最初按每账号一次执行，均返回本地 502 empty_response，未返回 usage。真实错误和原始本地 HTTP 响应保留，
不把模型目录可见、已登录或 response.completed 等同于可交付内容。

配置新账号时沿用了较早 V2 代码，遗漏了原 8787 实际正在使用的完成事件修复，这是本次配置的工程遗漏。
旧转换只读取 response.completed.output，会忽略此前 response.output_item.done 中已完整返回的 item。
这条路径已有 P6 的离线复现与真实验证，因此从现有 p6-3b6-gateway-repair-retest 移入原最小修复，
未另行设计转换层或修改 OAuth、SDK、DPAPI、代理、模型和研究框架。

修复仅在最终 response.completed 成功、terminal output 为空时，使用原始完整 done item，并按 output_index 排序。
非空 terminal output 继续优先；中断、incomplete、failed 和未完成 item 均拒绝，仍不从 text delta 伪造结果。
原始 call ID、参数、opaque reasoning 和 usage 的处理保持既有修复语义。
25 项 Responses/HTTP Mock 回归全部通过；之前的账号隔离/CLI/OAuth 9 项也已通过。

首轮上游 SSE 未被归档，只有本地 502 响应，不能据此认定该缺陷是两条失败各自的唯一原因。
修复后两次真实响应均报告 output_source=completed_item_events、terminal_output_items=0、completed_item_events=1，
并准确交付 OK，证明修复在本轮真实请求中生效。

发现缺陷后，先向用户说明工程遗漏、离线回归及总共四次的有界复验安排，然后各进行一次修复后请求。
没有自动网络重试、换模型或删除首轮失败；成功后立即结束推理验证。

## 隔离、额度和证据

第三账号由用户将 SDK 生成的网址复制到本机无痕窗口完成授权，state、nonce、PKCE、loopback callback 和 token 验证仍由原 SDK 负责。
各账号状态目录、API Key 与凭据文件独立，六组不同账号 Key 交叉访问均为 401。
原 8787 进程 PID=56416 未停止或切换；仅逐一核实并重启第二、第三个进程以加载修复。
没有删除锁或账号状态，原锁由正常机制过期。前两个账号状态、Key 及既有连接凭据共 9 个文件在最终核查中内容未变。

实际共 **4 次推理尝试：2 次失败、2 次成功**。两条成功 usage 合计 prompt=20、completion=10、total=30，reasoning tokens=0。
两条首轮失败 usage 缺失，全账本 tokens、费用及 ChatGPT plan 剩余额度均 unknown；不能把缺失项按零累加。
目录请求和本地 health/认证检查不是推理请求。

源修复提交为 P6 的 76a3e1db1，本主线移入提交 d4ba77e7e。最终报告提交见交付消息。
[脱敏结果审计](gateway_accounts23_validation_20261106.json) 保留状态、usage、响应 SHA256 和计数。
原始请求、原始本地 Gateway 响应和进程记录在 ignored 的 runs/gateway-account2-20261106 与 runs/gateway-account3-20261106；
凭据、授权网址和完整 provider_output 不纳入 Git。

官方依据：[Responses 流式事件](https://developers.openai.com/api/reference/resources/responses/streaming-events)、
[GPT-5.6 Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna)。
