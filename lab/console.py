"""Escaped, text-first views of real runtime output."""
from html import escape

import streamlit as st


def console(text):
    st.html(f'<pre class="console-output">{escape(str(text))}</pre>')


def table(headers, rows, numeric=None):
    numeric = numeric or set()
    def row(values, tag):
        return "<tr>" + "".join(
            f'<{tag} class="{"numeric" if i in numeric else "text"}">{escape(str(value))}</{tag}>'
            for i, value in enumerate(values)
        ) + "</tr>"
    st.html('<div class="console-table-scroll"><table class="console-table"><thead>'
                + row(headers, "th") + "</thead><tbody>"
                + "".join(row(values, "td") for values in rows) + "</tbody></table></div>")


def status_text(report, continuation=None):
    candidate = report["candidate_tokens"] if report["candidate"] is not None else "--"
    reduction = f"{report['reduction_percent']:.2f}%" if report["candidate"] is not None else "--"
    status = continuation["status"].upper() if continuation else "NOT_RUN"
    return (f"state      {report['status'].upper()}\n"
            f"context    {report['original_tokens']} → {candidate} tokens    target {report['budget']['target']}\n"
            f"active     {report['committed_tokens']} tokens    candidate reduction {reduction}\n"
            f"resume     {status}")


def event_log(events):
    lines = []
    for e in events:
        stage = e["stage"]
        label = "INFO"
        if stage == "snapshot":
            detail = f"items={e['items']} tokens={e['tokens']} sha256={e['sha256'][:12]}"
        elif stage == "trigger":
            detail = f"triggered={str(e['triggered']).lower()} input_fits={str(e['input_fits_window']).lower()} tool_pairs={str(e['tool_pairs_complete']).lower()}"
        elif stage == "policy_request":
            request = e["request"]
            detail = f"protected={request['protected_tokens']} history_budget={request['available_history_tokens']}"
        elif stage == "selection":
            ds = e["proposal"]["decisions"]
            detail = " ".join(f"{action}={sum(d['action'] == action for d in ds)}" for action in ("KEEP", "COMPRESS", "DROP"))
        elif stage == "reconstruction":
            detail = f"candidate={e['tokens']} tokens (not committed)"
        elif stage == "validation":
            checks = e["checks"]
            label = "PASS" if all(checks.values()) else "FAIL"
            detail = f"{sum(checks.values())}/{len(checks)} checks"
            if label == "FAIL":
                detail += " failed=" + ",".join(name for name, ok in checks.items() if not ok)
        elif stage == "commit":
            label, detail = "PASS", f"active={e['tokens']} tokens sha256={e['context_sha256'][:12]}"
        elif stage == "abort":
            label, detail = "FAIL", e["reason"]
        else:
            detail = e.get("reason", e.get("note", ""))
        lines.append(f"{e['index'] + 1:02d} [{label}] {stage:<15} {detail}")
    return "\n".join(lines)
