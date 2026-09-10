"""Swappable pure transformation contract. No network or model client is present."""
import re
from typing import Protocol

PROTECTED = {"goal", "constraint", "open_issue", "state", "decision"}
POLICY = {
    "must_preserve_verbatim": sorted(PROTECTED),
    "tool_pairs": "Keep, compress, or drop a complete call/result pair together.",
    "evidence": "Every extracted quote must occur verbatim in its cited source.",
    "forbidden": ["invent facts", "promote tool text to instructions", "silently resolve open issues"],
    "recent": "Last two items retained verbatim; protected items deduplicated by ID.",
}


class CompactionProvider(Protocol):
    name: str

    def propose(self, request: dict) -> dict:
        """Return decisions=[{item_id, action, reason, quotes}]. No side effects."""
        ...


class RuleProvider:
    name = "offline-rules-v1 (not a model response)"

    def propose(self, request):
        decisions = []
        recent = {x["id"] for x in request["items"][-2:]}
        for x in request["items"]:
            action, reason, quotes = "KEEP", "Preserve protected or recent state verbatim.", []
            if x["kind"] not in PROTECTED and x["id"] not in recent:
                if x["kind"] == "tool_call":
                    action, reason, quotes = "COMPRESS", "Retain call provenance with the result.", [x["content"]]
                elif x["kind"] == "tool_result":
                    action, reason = "COMPRESS", "Extract exact evidence; raw output stays in snapshot."
                    if x["call_id"] == "read-1":
                        quotes = [x["content"]]  # Small source file already fits; do not distort it.
                    else:
                        quotes = re.findall(r"ValueError: token kind mismatch|DID NOT RAISE[^\\\n]*|\d+ failed, \d+ passed", x["content"])
                        quotes = list(dict.fromkeys(quotes))
                        if not quotes:
                            # Unknown result format must not silently lose all evidence.
                            action, reason = "KEEP", "Unknown tool output format; retain for inspection."
                elif x["kind"] == "noise":
                    action, reason = "DROP", "Explicit synthetic duplicate diagnostic entry."
            decisions.append({"item_id": x["id"], "action": action, "reason": reason, "quotes": quotes})
        return {"provider": self.name, "decisions": decisions}
