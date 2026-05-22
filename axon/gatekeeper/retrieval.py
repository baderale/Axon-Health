"""Simple corpus retrieval for the gatekeeper LLM judges.

For the prototype, retrieval is in-memory keyword scoring over the markdown
files in ``seed_data/<profile>/``. The interface is intentionally minimal
so that swapping to a real pgvector-backed similarity search later is a
one-file change.
"""

from __future__ import annotations

import os
import re
from collections import Counter
from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path

SEED_ROOT = Path(os.environ.get("SEED_DATA_ROOT", "/app/seed_data"))


_WORD = re.compile(r"[A-Za-z][A-Za-z0-9_-]+")


def _tokenize(text: str) -> list[str]:
    return [tok.lower() for tok in _WORD.findall(text)]


@lru_cache(maxsize=8)
def _load_corpus(profile: str) -> list[tuple[Path, str, Counter[str]]]:
    """Load and tokenize every markdown file in seed_data/<profile>/."""
    # Defense-in-depth: refuse profile names that could escape SEED_ROOT, even
    # though callers today are only ever the hardcoded Model Registry entries.
    if not profile or any(ch in profile for ch in ("/", "\\", "..", "\x00")):
        return []
    folder = SEED_ROOT / profile
    if not folder.exists():
        return []
    out: list[tuple[Path, str, Counter[str]]] = []
    for path in sorted(folder.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        out.append((path, text, Counter(_tokenize(text))))
    return out


def retrieve(profile: str, query: str, *, top_k: int = 3, max_chars: int = 4000) -> str:
    """Return a concatenated context block of the top-k most relevant docs."""
    corpus = _load_corpus(profile)
    if not corpus:
        return ""
    q_tokens = Counter(_tokenize(query))
    scored: list[tuple[float, Path, str]] = []
    for path, text, doc_tokens in corpus:
        score = sum(min(q_tokens[t], doc_tokens[t]) for t in q_tokens)
        # length-normalize so a giant file doesn't dominate by accident
        norm = score / (1 + len(doc_tokens) ** 0.5)
        scored.append((norm, path, text))
    scored.sort(key=lambda x: x[0], reverse=True)

    blocks: list[str] = []
    total = 0
    for score, path, text in scored[:top_k]:
        if score <= 0:
            break
        header = f"--- {path.name} (score={score:.3f}) ---\n"
        room = max_chars - total - len(header)
        if room <= 0:
            break
        snippet = text[:room]
        blocks.append(header + snippet)
        total += len(header) + len(snippet)
    return "\n\n".join(blocks)


def list_profiles() -> Iterable[str]:
    if not SEED_ROOT.exists():
        return []
    return sorted(p.name for p in SEED_ROOT.iterdir() if p.is_dir())
