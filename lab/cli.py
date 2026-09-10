import argparse
import json
import os
from pathlib import Path
import tempfile

from lab.runtime import Budget, Runtime
from lab.scenario import Scenario
from lab.tokens import prepare


def experiment(strategy="structured", fault="none", budget=None):
    case = Scenario()
    try:
        runtime = Runtime(case.collect(), strategy=strategy, fault=fault, budget=budget).run()
        report = runtime.report()
        if runtime.status in {"committed", "skipped", "baseline"}:
            context = runtime.candidate if runtime.status == "baseline" else runtime.current
            report["continuation"] = case.continue_task(context)
        else:
            report["continuation"] = {"status": "not_run", "patch_applied": False, "reason": "Runtime rejected candidate"}
        return report
    finally:
        case.close()


def comparison():
    # One real snapshot shared by all policies; fresh identical filesystem per worker.
    case = Scenario()
    try:
        items = case.collect()
    finally:
        case.close()
    reports = []
    for strategy in ("full", "truncate", "structured"):
        runtime = Runtime(items, strategy=strategy).run()
        case = Scenario()
        try:
            report = runtime.report()
            if runtime.status in {"committed", "skipped", "baseline"}:
                delivered = runtime.candidate if runtime.status == "baseline" else runtime.current
                report["continuation"] = case.continue_task(delivered)
            else:
                report["continuation"] = {"status": "not_run", "patch_applied": False}
            reports.append(report)
        finally:
            case.close()
    return reports


def summary(report):
    return {k: report[k] for k in ("strategy", "fault", "status", "original_tokens", "candidate_tokens", "committed_tokens", "reduction_percent")} | {
        "continuation": report.get("continuation", {}).get("status", "not_run"),
        "checks": report["validation"],
    }


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        temp_path = f.name
    os.replace(temp_path, path)


def main():
    parser = argparse.ArgumentParser(description="Offline compaction experiment; no API calls")
    parser.add_argument("command", choices=["warmup", "demo", "compare"])
    parser.add_argument("--fault", choices=["none", "drop_constraint", "forged_evidence", "budget_overflow", "pending_tool", "provider_timeout"], default="none")
    parser.add_argument("--target", type=int, default=1800)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.command == "warmup":
        prepare(download=True)
        print("Tokenizer cache ready. Subsequent demo/test/UI runs do not need network.")
        return
    data = comparison() if args.command == "compare" else experiment(fault=args.fault, budget=Budget(target=args.target))
    if args.output:
        save_json(args.output, data)
    print(json.dumps([summary(x) for x in data] if isinstance(data, list) else summary(data), ensure_ascii=False, indent=2))
    if isinstance(data, dict) and args.fault == "none" and data["continuation"]["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
