"""Exact cl100k tokenization of our serialized text, NOT API billing tokens."""
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".token-cache"
VOCAB_URL = "https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken"


def prepare(download=False):
    cache_file = CACHE / hashlib.sha1(VOCAB_URL.encode()).hexdigest()
    if not download and not cache_file.is_file():
        raise RuntimeError("Tokenizer cache missing. Run: python -m lab.cli warmup (one-time network setup).")
    os.environ["TIKTOKEN_CACHE_DIR"] = str(CACHE)
    import tiktoken
    return tiktoken.get_encoding("cl100k_base")


def serialize(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def count(value):
    return len(prepare().encode(serialize(value), disallowed_special=()))
