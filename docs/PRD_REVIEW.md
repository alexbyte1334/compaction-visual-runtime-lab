# PRD 审阅与 V1.1 方案

审阅对象：用户提供的《Compaction Visual Runtime Lab — 项目PRD.md》，V1.0。文档作为需求材料使用，其“必须”描述不等于已经交付。此次授权范围是搭建初步框架，API 后续接入。

## 是否执行

**执行补强后的方案。原 PRD 作为分享选题足够，作为“实际项目证明”还不够。**

优点是主题收敛、观察点明确、重视状态和验证。主要不足不在于页面数量，而在于证据链缺口。V1.1 保留项目名与 refresh token 场景，把叙事改为：**同一故障任务在预算受限时，哪种上下文处理还能让任务正确继续？失败时 Runtime 如何保护原状态？**

| 原方案缺口 | V1.1 调整 | 可检查的证据 |
|---|---|---|
| 固定模拟事件容易变成动画演示 | 实际执行合成 PyJWT 源码与 pytest，采集真实输出 | Before 的退出码、两处失败和源码 |
| Agent Continue 仅再说一句话 | 初步框架使用披露身份的脚本 Worker，检查上下文合同、源码漂移、应用局部修复、跑测试 | diff、源码哈希、83 个测试通过 |
| 自建流程容易被误认为厂商黑盒内部 | 明确“本项目的 Runtime 策略”与官方接口公开行为的边界 | 官方资料链接与页面上的模式标识 |
| “约束字符串还在”被当作语义无损 | 拆分逐字保留、来源引用、预算、状态一致性、工具配对与任务结果 | 每项 validation，标注无法证明一般语义等价 |
| 截断会换库是预设故事 | 同一快照、同一 Worker、同一压缩目标，按完整工具对做截断 | 截断实际导致恢复合同缺失，拒绝执行 |
| 只有成功路径 | 约束丢失、伪造证据、压缩超预算、未完成工具调用、Provider 超时 | rejected，current 与 before 相同，没有应用补丁 |
| 十多个模型阶段令范围膨胀 | 合并为 7 个可暂停阶段；分类/选择/抽取来自同一 Provider 提议 | 单步测试证明没有提前执行后续阶段 |
| API 不可用时混淆 fixture 与真实回放 | 本次仅 rule mode，绝不称其为模型响应 replay | UI/JSON 中的离线 Provider 和 Worker 名称 |

## 修订架构与本次范围

```text
真实合成故障（临时副本）
  → Snapshot + Growth
  → Trigger + Window / Tool boundary check
  → Policy / Provider Request / Budget floor
  → Rule Provider Proposal（KEEP / COMPRESS / DROP + 引文）
  → Reconstruction / Working State
  → Validation
  → Commit 或 Abort
  → 用户点击 Continue → 同一脚本 Worker → 补丁 + pytest
```

将原文的“模型任务相关度 0.91”等看似精确的数值删去：离线规则并没有可以解释该数字的模型评分，不应制造可信度。

“动态预算”在 v0.1 的具体含义仅为：实测信封大小，预留输出和下一工具结果，计算保护项占用和历史剩余额度，验证重建结果。Provider 收到预算但尚不自适应迭代；超预算时拒绝，不自动二次摘要。

## 能否满足领导要求

补强后的项目设计可以承载一次机制深入的组会分享：有真实代码故障、有可走查 Runtime、有对照、有失败保护，也有可重复结果。

**“结合自己的案例”应表述为自己复跑并改动过的学习实验。** 当前案例由本项目合成，不能包装为工作中的真实生产事故。分享前至少亲自改变一次约束、预算或故障点，记录自己的观察。若领导明确要求生产案例，还需另行添加经许可的脱敏记录；本仓库没有假装完成该要求。

当前交付满足“可接续开发的初步框架”，不宣称完成原 PRD 的全部功能，也不宣称证明 LLM 压缩质量。接入模型之后，才可以讨论模型生成信息的质量、成本、延迟和稳定性。

## 原 PRD 的 14 个观察问题如何落地

| 问题 | v0.1 观察入口 | 限制 / 下一步 |
|---|---|---|
| 1 Context 为什么增长 | snapshot.growth 与真实测试输出 | 当前一次采集，未实现连续 Agent loop |
| 2 谁触发压缩 | trigger event 与 Budget | 本地实验阈值，不映射产品默认值 |
| 3 给压缩器什么约束 | policy_request | 本次给规则组件，不是给模型 |
| 4 实际输入是什么 | policy_request.request | 无真实模型请求 |
| 5 如何分类 | item.kind + RuleProvider | 可信采集器分类，非模型语义分类 |
| 6 为什么 KEEP | proposal.decisions | 规则理由 |
| 7 为什么 COMPRESS | proposal.decisions | 抽取可核对的原文引文 |
| 8 为什么 DROP | duplicate/noise 的 decision | 重复摘要是显式构造的噪声标签 |
| 9 预算影响 | protected_floor / available_history_tokens / within_target | 暂无自适应迭代 |
| 10 长输出如何提取 | result content 与 evidence.quote | 固定 pytest 格式，不是通用摘要 |
| 11 State 如何产生 | working_state() 与 source_id | Runtime 根据保留的可信字段派生 |
| 12 Context 如何重建 | reconstruction.candidate 与 Before/After | 页面为并排 JSON，补丁另有文本 diff |
| 13 如何验关键约束 | validation + drop_constraint | 逐字检查不等于语义完全保真 |
| 14 为什么能继续 | Continue 的输入检查、真实补丁和测试 | Worker 是脚本；模型继续推理待做 |

## 分享验收门槛

- 初步框架：新机器按 README 安装，测试通过，正常 demo 通过，五类故障拦截，三组对照可导出。
- 分享准备：讲者独立复跑与修改参数；能从 source_id 回到原始证据；能解释为什么失败时不提交。
- 模型版本：接入 Provider 后，至少做 3 次重复实验、多个变体和跨多轮压缩；记录真实模型/配置、输入输出用量、耗时、约束保留和任务完成率。
- 不以“压缩率高”单独判成功；任务结果、证据可核查、约束保留必须同时成立。

## 公开事实边界

2026-09-10 核对 [OpenAI 官方 Compaction 文档](https://developers.openai.com/api/docs/guides/compaction)：官方提供服务端压缩和独立 compact 接口；返回的压缩项是不供人工解释的 opaque 内容。本项目透明的 JSON 引文状态是自建方案，不能推断为官方内部分类、评分、摘要或重建算法。
