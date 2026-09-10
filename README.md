# Compaction Visual Runtime Lab

**用一个真的测试故障，解释上下文压缩为什么是受控的状态转换。**

这是供组会分享和后续开发的 **v0.1 离线初步框架**。运行真实 PyJWT 测试 → 采集源码与测试输出 → 触发压缩 → 查看 KEEP / COMPRESS / DROP → 校验并提交 → 在临时副本中恢复修复并再次运行测试。

没有 LLM API、密钥、模型响应回放或 API 费用。规则压缩器、脚本恢复 Worker 都有明确标识。首次安装依赖与缓存词表需要网络，准备后实验可离线运行。

## 先看什么

- [方案审阅与 V1.1 范围](docs/PRD_REVIEW.md)：原 PRD 为什么还不够、补强后的验收条件。
- [机制与代码地图](docs/ARCHITECTURE.md)：数据从哪里来、谁能修改状态、如何拒绝错误结果。
- [公司电脑接续开发](docs/HANDOFF.md)：后续 API 接入顺序和待办。
- [15 分钟分享走查](docs/SHARING.md)：每一步展示什么、能证明什么。
- [本次验证记录](docs/VALIDATION.md)：实际测试和对照结果。

## 本地启动（Python 3.11+）

macOS / Linux：

```bash
git clone https://github.com/alexbyte1334/compaction-visual-runtime-lab.git
cd compaction-visual-runtime-lab
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m lab.cli warmup
python -m pytest -q
python -m streamlit run app.py
```

Windows PowerShell（无需修改脚本执行策略）：

```powershell
git clone https://github.com/alexbyte1334/compaction-visual-runtime-lab.git
cd compaction-visual-runtime-lab
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m lab.cli warmup
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m streamlit run app.py
```

打开 `http://localhost:8501`，点 **创建 / 重置实验 → 下一阶段 / 运行剩余阶段 → 恢复任务并运行测试**。侧栏可注入故障；“三组对照”页使用固定默认预算，与侧栏单次实验独立。

仓库默认私有，Clone 需登录有权限的 GitHub 账号。联网准备阶段需要访问 Python 包源和 tokenizer 词表地址；公司网络能否访问需在公司电脑确认。没有把你的本地虚拟环境、缓存或任何密钥上传。

## 不启动 UI 也能验证

```bash
python -m lab.cli demo --output runs/demo.json
python -m lab.cli compare --output runs/comparison.json
python -m lab.cli demo --fault drop_constraint --output runs/rejected.json
python -m lab.cli demo --fault forged_evidence
python -m lab.cli demo --fault budget_overflow
python -m lab.cli demo --fault pending_tool
python -m lab.cli demo --fault provider_timeout
```

正常实验中，原始夹具有 **2 个失败、81 个通过**；恢复后应为 **83 个通过**。五类故障应返回 `rejected`，候选不提交、不运行修复。故障实验被正确拦截不算命令错误；正常 demo 若恢复未通过则返回非零退出码。

输出目录 `runs/` 默认不进 Git，可用 UI 下载 Trace JSON。原始故障文件故意有 bug，根目录 pytest 只收集 `tests/`；场景测试由实验在临时目录单独执行。

## 实验能说明什么

| 方案 | 是否满足压缩目标 | 是否保留早期目标与约束 | 脚本恢复 |
|---|---|---|---|
| 完整上下文参考组 | 否 | 是 | 真实测试通过 |
| 最老优先截断（按完整工具对删除） | 是 | 否 | 因缺失合同而拒绝修改 |
| 结构化压缩 | 是 | 是 | 真实测试通过 |

三组读取**同一快照**，使用**相同 Worker**，各自使用全新的故障副本。没有将截断后的行为写成“模型一定会换库”。这个对照验证指定任务的恢复合同，不衡量模型智能或通用语义保真能力。

Token 使用 `cl100k_base` 对规范 JSON 信封实测，包含 system、工具定义、内容和结构化状态；这是统一的本地计量方法，**不是 API 计费 Token 或某个模型的精确窗口用量**。展示数字随 Python/pytest 输出变化，以当次运行报告为准。

## 当前边界

- 已有：真实故障输入、7 阶段真实单步执行、规则 Provider、证据引用校验、失败时保留原状态、三组对照、脚本修复与真实测试、Trace 导出、自动化测试、CI。
- 尚未实现：真实模型压缩和继续推理、模型响应录制回放、自适应多轮压缩、跨进程 checkpoint 恢复、多轮长任务评测、生产级日志脱敏。
- 这是独立的合成学习案例；没有包含雇主、客户或内部项目代码，不代表本人经历过的生产事故。
- 自建透明流水线不能被称为 OpenAI compaction 的内部实现。官方返回的压缩项不供人工解析，详见 [OpenAI Compaction 文档](https://developers.openai.com/api/docs/guides/compaction)。
