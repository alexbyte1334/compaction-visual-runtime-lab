"""Execute a synthetic, real PyJWT failure in a temporary directory."""
import difflib
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from lab.tokens import serialize

CASE = Path(__file__).resolve().parents[1] / "cases" / "refresh_token"
GOAL = "Fix refresh token authentication failure."
CONSTRAINT = "Do not replace the current JWT library; preserve signature validation."
ISSUE = "Refresh-token rejection is unresolved; access tokens must not refresh."
NEXT = "Inspect refresh_token and its expected_kind argument, then run the regression tests."


def item(id, kind, content, call_id=None):
    return {"id": id, "kind": kind, "content": content, "call_id": call_id}


def digest(value):
    return hashlib.sha256(serialize(value).encode()).hexdigest()


class Scenario:
    def __init__(self):
        self._temp = tempfile.TemporaryDirectory(prefix="compaction-lab-")
        self.path = Path(self._temp.name)
        for name in ("auth.py", "test_auth.py"):
            shutil.copyfile(CASE / name, self.path / name)

    def close(self):
        self._temp.cleanup()

    def run_tests(self, diagnostic=False):
        args = [sys.executable, "-m", "pytest", "test_auth.py", "--color=no", "--tb=short", "-p", "no:cacheprovider"]
        args += ["-v", "-s"] if diagnostic else ["-q"]
        env = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONDONTWRITEBYTECODE="1")
        env.pop("PYTEST_ADDOPTS", None)
        completed = subprocess.run(args, cwd=self.path, env=env, capture_output=True, text=True, timeout=30)
        # Remove machine-specific workspace and interpreter paths from exportable evidence.
        stdout = (completed.stdout + completed.stderr).replace(str(self.path), "<case-workspace>")
        stdout = stdout.replace(sys.executable, "<python>")
        return {"command": "python -m pytest test_auth.py " + ("-v -s" if diagnostic else "-q"),
                "exit_code": completed.returncode, "stdout": stdout}

    def collect(self):
        source = (self.path / "auth.py").read_text()
        result = self.run_tests(diagnostic=True)
        if result["exit_code"] != 1 or "2 failed, 81 passed" not in result["stdout"]:
            raise RuntimeError("Fixture did not reproduce the expected two failures: " + result["stdout"][-1000:])
        return [
            item("goal", "goal", GOAL),
            item("constraint", "constraint", CONSTRAINT),
            item("read-call", "tool_call", "read_file(auth.py)", "read-1"),
            item("read-result", "tool_result", source, "read-1"),
            item("test-call", "tool_call", result["command"], "test-1"),
            item("test-result", "tool_result", serialize(result), "test-1"),
            item("duplicate", "noise", "Repeated diagnostic summary: 2 failed, 81 passed"),
            item("issue", "open_issue", ISSUE),
            item("state", "state", "Diagnosis in progress; no patch has been applied."),
            item("next", "decision", NEXT),
        ]

    def continue_task(self, context):
        """A disclosed scripted worker, using ONLY the delivered context + current files.

        It never receives a strategy name, original snapshot, or validator results.
        This measures a narrow continuation contract, not LLM intelligence.
        """
        values = {(x["kind"], x["content"]) for x in context["items"]}
        required = [("goal", GOAL), ("constraint", CONSTRAINT), ("open_issue", ISSUE), ("decision", NEXT)]
        missing = [kind for kind, content in required if (kind, content) not in values]
        if missing:
            return {"status": "blocked", "reason": "Missing continuation contract: " + ", ".join(missing), "patch_applied": False}
        records = {x["id"]: x for x in context["items"]}
        if "2 failed, 81 passed" not in records.get("test-result", {}).get("content", ""):
            return {"status": "blocked", "reason": "Missing failure evidence; collect diagnostics again", "patch_applied": False}
        path = self.path / "auth.py"
        before = path.read_text()
        if records.get("read-result", {}).get("content") != before:
            return {"status": "blocked", "reason": "File differs from retained evidence; re-read before applying a patch", "patch_applied": False}
        old = 'claims = validate_token(token, expected_kind="access")'
        new = 'claims = validate_token(token, expected_kind="refresh")'
        if before.count(old) != 1:
            return {"status": "blocked", "reason": "Fixture drift: manual inspection required", "patch_applied": False}
        after = before.replace(old, new, 1)
        path.write_text(after)
        tests = self.run_tests()
        passed = tests["exit_code"] == 0 and "83 passed" in tests["stdout"]
        diff = "".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile="a/auth.py", tofile="b/auth.py"))
        return {"status": "passed" if passed else "failed", "patch_applied": True,
                "worker": "scripted-offline-v1", "diff": diff, "tests": tests,
                "before_sha256": digest(before), "after_sha256": digest(after)}
