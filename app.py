"""Technical console. Views render Runtime events; controls execute real stages."""
import json
from pathlib import Path
import streamlit as st

from lab.cli import comparison
from lab.runtime import Budget, Runtime
from lab.scenario import Scenario
from lab.tokens import count, prepare
from lab.console import console, table, event_log, status_text

st.set_page_config(page_title="Compaction Runtime Lab", layout="wide", initial_sidebar_state="collapsed")
st.markdown("<style>" + (Path(__file__).parent / "ui/console.css").read_text() + "</style>", unsafe_allow_html=True)
st.title("> compaction-runtime-lab")
st.caption("case: refresh_token  /  provider: offline-rules-v1  /  worker: scripted-offline-v1")
try:
    prepare()
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()

FAULTS = {
    "正常运行": "none", "丢失早期约束": "drop_constraint", "伪造压缩证据": "forged_evidence",
    "压缩后仍然超预算": "budget_overflow", "存在未完成工具调用": "pending_tool", "压缩器超时": "provider_timeout",
}
fault_col, target_col, reset_col = st.columns([3, 2, 2])
fault = fault_col.selectbox("fault / 故障注入", list(FAULTS))
target = target_col.number_input("target / Token", min_value=900, max_value=2600, value=1800, step=100)
reset_col.markdown('<div class="control-spacer" aria-hidden="true"></div>', unsafe_allow_html=True)
initialize = reset_col.button("创建 / 重置实验", use_container_width=True)

if initialize:
    if "case" in st.session_state:
        st.session_state.case.close()
    # A failed reset must not leave a closed case or stale context executable.
    for key in ("case", "runtime", "steps", "continuation"):
        st.session_state.pop(key, None)
    case = Scenario()
    try:
        with st.spinner("pytest / 采集故障输出"):
            runtime = Runtime(case.collect(), fault=FAULTS[fault], budget=Budget(target=target))
        st.session_state.case = case
        st.session_state.runtime = runtime
        st.session_state.steps = runtime.steps()
        st.session_state.continuation = None
    except Exception as exc:
        case.close()
        st.error(str(exc))

runtime = st.session_state.get("runtime")
continuation = st.session_state.get("continuation")
report = runtime.report() if runtime else None
if runtime:
    if runtime.fault != FAULTS[fault] or runtime.budget.target != target:
        st.caption("配置已修改，尚未应用。点击创建 / 重置实验后生效。")
    console(status_text(report, continuation))
else:
    console("state      IDLE\ncontext    -- → -- tokens    target --\nresume     NOT_RUN")

run_tab, inspect_tab, compare_tab = st.tabs(["运行记录", "检查上下文", "对照实验"])
with run_tab:
    step_col, run_col, resume_col = st.columns([1, 1, 1.4])
    active = runtime is not None and runtime.status in {"ready", "running"}
    step = step_col.button("下一阶段", disabled=not active, use_container_width=True)
    auto = run_col.button("运行剩余阶段", disabled=not active, use_container_width=True)
    can_resume = runtime is not None and runtime.status in {"committed", "skipped"} and continuation is None
    resume = resume_col.button("恢复任务并运行测试", disabled=not can_resume, use_container_width=True)
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

    if not runtime:
        console("[idle] 创建实验以采集 auth.py 与 pytest 输出。\n[mode] 离线规则；没有调用模型 API。")
    else:
        st.caption(f"fault={runtime.fault}  threshold={runtime.budget.trigger}  window={runtime.budget.max_context}  reserve={runtime.budget.reserved_output}+{runtime.budget.reserved_next_tool}")
        console(event_log(runtime.events) or "[ready] 故障已复现，等待下一阶段。")
        if runtime.validation:
            passed = sum(runtime.validation.values())
            with st.expander(f"validation / {passed} of {len(runtime.validation)} passed", expanded=not all(runtime.validation.values())):
                console("\n".join(f"[{'PASS' if ok else 'FAIL'}] {name}" for name, ok in runtime.validation.items()))
        if continuation:
            st.subheader("resume / 执行结果")
            if "diff" in continuation:
                st.code(continuation["diff"], language="diff")
                st.code(continuation["tests"]["stdout"], language=None)
            else:
                console(continuation.get("reason", continuation["status"]))
        if runtime.proposal:
            st.subheader("selection / 信息取舍")
            originals = {x["id"]: x for x in runtime.snapshot}
            candidate = {x["id"]: x for x in runtime.candidate["items"]} if runtime.candidate else None
            table(["item", "kind", "before", "candidate", "action"], [
                [d["item_id"], originals[d["item_id"]]["kind"], count(originals[d["item_id"]]),
                 "--" if candidate is None else count(candidate[d["item_id"]]) if d["item_id"] in candidate else 0, d["action"]]
                for d in runtime.proposal["decisions"]
            ], numeric={2, 3})
            st.caption("条目计数包含证据引用开销；总量以完整上下文计数为准。理由与原文见检查上下文。")

with inspect_tab:
    if not runtime:
        console("[idle] 尚无快照。")
    else:
        if runtime.events:
            selected = st.selectbox("stage / 阶段输入输出", range(len(runtime.events)),
                                    format_func=lambda i: f"{i + 1:02d} {runtime.events[i]['stage']}")
            st.json(runtime.events[selected], expanded=False)
        before, after = st.columns(2)
        with before:
            st.subheader("before / 原始快照")
            st.json(runtime.before, expanded=False)
        with after:
            st.subheader("candidate / 候选上下文")
            if runtime.candidate is not None:
                st.json(runtime.candidate, expanded=False)
            else:
                console("[pending] 尚未重建。")
        if runtime.events:
            with st.expander("growth / 上下文增长明细"):
                table(["item", "cumulative tokens"], [[x["item"], x["tokens"]] for x in runtime.events[0]["growth"]], numeric={1})
        st.caption("Token: cl100k_base / canonical JSON，非 API 计费量。elapsed_ms 为累计墙钟时间，包含单步等待。")

with compare_tab:
    st.caption("同一快照 / 同一 Worker / 独立故障副本 / 固定 target=1800。")
    if st.button("运行三组对照"):
        with st.spinner("compare / full · truncate · structured"):
            st.session_state.comparison = comparison()
    if "comparison" in st.session_state:
        reports = st.session_state.comparison
        table(["strategy", "before", "candidate", "reduction", "budget", "constraints", "resume"], [
            [x["strategy"], x["original_tokens"], x["candidate_tokens"], f"{x['reduction_percent']:.2f}%",
             "PASS" if x["validation"].get("within_target") else "FAIL",
             "PASS" if x["validation"].get("constraints_preserved") else "FAIL", x["continuation"]["status"].upper()]
            for x in reports
        ], numeric={1, 2, 3})
        st.download_button("导出对照 JSON", json.dumps(reports, ensure_ascii=False, indent=2), "comparison.json", mime="application/json")
    else:
        console("[idle] 对照尚未运行。")

if report:
    if continuation:
        report["continuation"] = continuation
    st.download_button("导出 Trace JSON", json.dumps(report, ensure_ascii=False, indent=2), "compaction-trace.json", mime="application/json")
