"""Streamlit is only a view/controller; all stage data comes from Runtime."""
import json
import streamlit as st

from lab.cli import comparison, summary
from lab.runtime import Budget, Runtime
from lab.scenario import Scenario
from lab.tokens import count, prepare

st.set_page_config(page_title="Compaction Runtime Lab", page_icon="🔬", layout="wide")
st.caption("CONTEXT ENGINEERING / 可运行的机制实验")
st.title("压缩以后，任务还能继续吗？")
st.write("用一个真实的 refresh token 测试故障，观察预算触发、信息取舍、重建校验与恢复执行。")
st.info("离线初步框架 · 压缩器与恢复 Worker 均为确定性规则 · 不是模型响应回放，也不是 OpenAI 内部机制复刻。")
try:
    prepare()
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()

FAULTS = {
    "正常运行": "none", "丢失早期约束": "drop_constraint", "伪造压缩证据": "forged_evidence",
    "压缩后仍然超预算": "budget_overflow", "存在未完成工具调用": "pending_tool", "压缩器超时": "provider_timeout",
}
with st.sidebar:
    st.header("实验控制")
    fault = st.selectbox("故障注入", list(FAULTS))
    target = st.slider("压缩目标 Token", 900, 2600, 1800, 100)
    st.caption("阈值 3500 · 实验窗口 20000 · 输出预留 1200 · 下一次工具结果预留 600")
    initialize = st.button("创建 / 重置实验", type="primary", use_container_width=True)
    st.caption("变更参数后点击重置。每次仅修改临时副本，仓库中的故障夹具保持不变。")

if initialize:
    if "case" in st.session_state:
        st.session_state.case.close()
    case = Scenario()
    try:
        with st.spinner("运行故障夹具，采集真实源码与 pytest 输出…"):
            runtime = Runtime(case.collect(), fault=FAULTS[fault], budget=Budget(target=target))
        st.session_state.case = case
        st.session_state.runtime = runtime
        st.session_state.steps = runtime.steps()
        st.session_state.continuation = None
    except Exception as exc:
        case.close()
        st.error(str(exc))

left, right = st.tabs(["逐阶段实验", "三组对照"])
with left:
    if "runtime" not in st.session_state:
        st.write("先创建实验。故障复现会产生 2 个失败、81 个通过的真实测试结果。")
        st.code("python -m lab.cli demo\npython -m lab.cli compare\npython -m pytest -q", language="bash")
    else:
        runtime = st.session_state.runtime
        st.caption(f"当前实验：{runtime.fault} · target={runtime.budget.target} · worker=scripted-offline-v1")
        a, b, c = st.columns(3)
        step = a.button("下一阶段", disabled=runtime.status not in {"ready", "running"}, use_container_width=True)
        auto = b.button("运行剩余阶段", disabled=runtime.status not in {"ready", "running"}, use_container_width=True)
        resume = c.button("恢复任务并运行测试", disabled=runtime.status not in {"committed", "skipped"} or st.session_state.continuation is not None, use_container_width=True)
        if step or auto:
            try:
                if auto:
                    for _ in st.session_state.steps:
                        pass
                else:
                    next(st.session_state.steps)
            except StopIteration:
                pass
            st.rerun()
        if resume:
            st.session_state.continuation = st.session_state.case.continue_task(runtime.current)
            st.rerun()
        report = runtime.report()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("原始上下文", report["original_tokens"])
        m2.metric("候选上下文", report["candidate_tokens"] if runtime.candidate else "—")
        m3.metric("已提交上下文", report["committed_tokens"])
        m4.metric("状态", runtime.status.upper())
        st.caption("Token 是 cl100k_base 对完整 JSON 信封的实测计数，包含 system、工具定义和状态；不代表 API 计费量。")
        if runtime.events:
            st.caption("阶段时间为实验创建后的累计墙钟时间，包含手动暂停；不是压缩计算耗时。")
            st.progress(min(len(runtime.events) / 7, 1.0))
            for event in runtime.events:
                with st.expander(f"{event['index'] + 1:02d} / {event['stage']} · {event['elapsed_ms']} ms", expanded=event is runtime.events[-1]):
                    st.json(event)
            if runtime.events[0]["stage"] == "snapshot":
                st.line_chart({"累计上下文 Token": [x["tokens"] for x in runtime.events[0]["growth"]]})
        if runtime.proposal:
            st.subheader("信息取舍")
            original = {x["id"]: x for x in runtime.snapshot}
            st.dataframe([{"item": d["item_id"], "type": original[d["item_id"]]["kind"],
                           "source tokens": count(original[d["item_id"]]), "action": d["action"], "reason": d["reason"]}
                          for d in runtime.proposal["decisions"]], hide_index=True, use_container_width=True)
        if runtime.candidate:
            st.subheader("上下文重建")
            before, after = st.columns(2)
            with before:
                st.write("Before / 原始快照")
                st.json(runtime.before, expanded=False)
            with after:
                st.write("After / 候选上下文（仅校验通过才提交）")
                st.json(runtime.candidate, expanded=False)
            st.json(runtime.validation)
        if st.session_state.continuation:
            continuation = st.session_state.continuation
            st.subheader("恢复执行证据")
            st.write("恢复结果：", continuation["status"])
            if "diff" in continuation:
                st.code(continuation["diff"], language="diff")
                st.code(continuation["tests"]["stdout"])
            else:
                st.json(continuation)
            report["continuation"] = continuation
        st.download_button("下载本次 Trace JSON", json.dumps(report, ensure_ascii=False, indent=2), "compaction-trace.json", mime="application/json")

with right:
    st.write("同一份真实输入、同一个恢复 Worker、每组独立的临时目录。完整上下文是参考组；截断和结构化压缩共享 1800 Token 目标。")
    st.caption("截断组允许观察缺失约束后的拒绝执行，不预设模型一定会换库。对照采用固定默认参数，与侧栏单次实验参数独立。")
    if st.button("运行三组对照"):
        with st.spinner("运行完整上下文、最老优先截断、结构化压缩…"):
            st.session_state.comparison = comparison()
    if "comparison" in st.session_state:
        reports = st.session_state.comparison
        st.dataframe([{k: v for k, v in summary(x).items() if k != "checks"} for x in reports], hide_index=True, use_container_width=True)
        st.download_button("下载对照证据 JSON", json.dumps(reports, ensure_ascii=False, indent=2), "comparison.json", mime="application/json")
