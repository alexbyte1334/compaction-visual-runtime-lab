# 机制与代码地图

需求以根目录 [PRD.md](../PRD.md) 为唯一基线。

## 责任边界

| 文件 | 责任 | 不做什么 |
|---|---|---|
| cases/refresh_token | 可复现的真实 PyJWT 故障和回归测试 | 不提供生产认证服务 |
| lab/scenario.py | 在临时目录复现、采集、恢复和跑测试 | 不修改仓库故障夹具 |
| lab/tokens.py | 规范 JSON 序列化、实际 tokenizer 计数 | 不估算 API 价格 |
| lab/providers.py | 根据请求返回纯提议 | 不修改 Runtime 或磁盘 |
| lab/runtime.py | 预算、快照、状态重建、校验、提交 | 不相信 Provider 自报成功 |
| lab/cli.py | 实验编排和 JSON 导出 | 不把 rejected 候选交给 Worker |
| app.py / lab/console.py / ui/console.css | 技术控制台、逐行日志、数据表和单步控制 | 不预设压缩成功或测试结果 |

## 一次受控变更

`snapshot` 复制输入并记录 SHA-256；`before` 是完整输入信封；`candidate` 是不可信候选；`current` 只有通过校验才会更新。报表分别记录 candidate_tokens 与 committed_tokens，因此失败候选变小不会伪装成压缩成功。

工具记录保留 `call_id`，同一次调用的 call/result 必须完整成对。未完成调用先等待或终止本次压缩。这里的工具事件是实验 schema，不直接声称兼容 Responses API 的所有工具项。

引文必须包含 `source_id`、源条目哈希和逐字 `quote`。Runtime 从源条目继承 kind 和 call_id，Provider 不能把工具文本升级为用户约束。引文检查能证明字符串来自指定源，**不能证明该字符串对任务的完整性或语义蕴含**。

状态由保留的 goal/constraint/open_issue/state/decision 派生。当前版本为方便审计同时保留原条目和状态投影，Token 计算已包含这些重复开销。后续可以按字段去重，但需保持引用可追溯。

## 预算与恢复

信封大小 = 对 system + tool_schemas + items + compacted_state 完整 JSON 做分词计数。默认实验窗口 20000，trigger 3500，target 1800；另外预留输出 1200、下一工具结果 600。它们是可解释的实验参数，不代表任何模型配置。

protected_floor 包含必须逐字保留的条目、最近两个条目和对应状态。available_history_tokens 是 target 减去这个下限的规划值；Tokenizer 在文本边界可能合并 token，因此重建后必须再次对完整信封计数，不能把独立条目计数简单相加当作最终量。

恢复 Worker 不接收 strategy、原始快照或 validator。它只看交付的上下文和当前临时文件：确认目标/约束/未决问题/下一步，确认失败证据还在，确认当前源码与上下文证据一致，再执行固定规则修复。文件漂移时拒绝修改。这里的实际工作是确定性程序修复实验，不是通用自主 Agent。

## 保留的工程缺口

- 单次压缩框架，暂不支持将压缩结果反复作为新原始输入并维护跨代证据索引。
- Trace JSON 是观测产物；原子写文件不等于完整 checkpoint 协议，也未实现跨进程恢复。
- API 超时和预算失败当前直接拒绝并保留原状态；尚无重试、退避和费用预算。
- 只执行仓库可信合成夹具，不接受任意上传脚本、Shell 命令或公司日志。
- 小型 fixture 规则、脚本修复和严格字符串合同限制了泛化；接入模型时要重做语义评测。
