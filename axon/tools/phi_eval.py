"""Measure how much PHI the Tier-1 gatekeeper removes, and what it damages.

    uv run python -m axon.tools.phi_eval                 # both sets, summary table
    uv run python -m axon.tools.phi_eval --misses        # also list every miss
    uv run python -m axon.tools.phi_eval --json out.json # machine-readable result

Each case in ``evals/phi/*.jsonl`` is sent through ``tier1_policy.evaluate`` as
a cross-subsidiary message, exactly as the interceptor would. Two numbers
matter:

  - **recall**: of the identifiers a case lists under ``phi``, the share that
    no longer appear in what would be forwarded.
  - **damage**: of the clinical strings a case lists under ``keep``, the share
    that were altered. Over-redaction breaks answers ("Max 2 g/day" becoming
    "[REDACTED:name] g/day"), so it is measured as carefully as misses.

Tier-2 judges are not run here; this measures the deterministic layer only.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from axon.gatekeeper import tier1_policy
from axon.gatekeeper.verdict import Decision, GatekeeperRequest

EVAL_DIR = Path(__file__).resolve().parents[2] / "evals" / "phi"
SETS = {
    "generated": "generated.jsonl",
    "handwritten": "handwritten.jsonl",
    "holdout": "holdout.jsonl",
}


def load(name: str) -> list[dict[str, Any]]:
    path = EVAL_DIR / SETS[name]
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def forwarded_text(text: str) -> tuple[str, Decision]:
    request = GatekeeperRequest(
        source_subsidiary="clinical_research",
        target_subsidiary="pharma",
        subject="axon.clinical_research.pharma.research.query",
        payload={"question": text},
    )
    verdict = tier1_policy.evaluate(request)
    payload = verdict.redacted_payload if verdict.redacted_payload is not None else request.payload
    return payload["question"], verdict.decision


def score(cases: list[dict[str, Any]]) -> dict[str, Any]:
    by_kind: dict[str, list[int]] = defaultdict(lambda: [0, 0])  # [caught, total]
    keep_ok = keep_total = 0
    negatives = negatives_touched = 0
    misses: list[dict[str, str]] = []
    damage: list[dict[str, str]] = []

    for case in cases:
        out, decision = forwarded_text(case["text"])
        if decision is Decision.COACH:
            raise SystemExit(f"Tier-1 coached {case['id']}: is the name detector installed?")
        for item in case["phi"]:
            tally = by_kind[item["kind"]]
            tally[1] += 1
            if item["text"] in out:
                misses.append({"id": case["id"], "kind": item["kind"], "text": item["text"], "out": out})
            else:
                tally[0] += 1
        for keep in case.get("keep", []):
            keep_total += 1
            if keep in out:
                keep_ok += 1
            else:
                damage.append({"id": case["id"], "keep": keep, "out": out})
        if not case["phi"]:
            negatives += 1
            negatives_touched += out != case["text"]

    caught = sum(c for c, _ in by_kind.values())
    total = sum(t for _, t in by_kind.values())
    return {
        "cases": len(cases),
        "identifiers": total,
        "recall": caught / total if total else None,
        "by_kind": {k: {"caught": c, "total": t} for k, (c, t) in sorted(by_kind.items())},
        "keep_strings": keep_total,
        "damage_rate": (keep_total - keep_ok) / keep_total if keep_total else None,
        "negatives": negatives,
        "negatives_touched": negatives_touched,
        "misses": misses,
        "damage": damage,
    }


def _pct(x: float | None) -> str:
    return "  -  " if x is None else f"{100 * x:5.1f}%"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--set", choices=[*SETS, "all"], default="all")
    parser.add_argument("--misses", action="store_true", help="list every miss and every damaged string")
    parser.add_argument("--json", type=Path, help="write the full result as JSON")
    args = parser.parse_args(argv)

    names = list(SETS) if args.set == "all" else [args.set]
    results = {n: score(load(n)) for n in names}

    kinds = sorted({k for r in results.values() for k in r["by_kind"]})
    print(f"{'kind':<16}" + "".join(f"{n:>22}" for n in names))
    for kind in kinds:
        row = f"{kind:<16}"
        for n in names:
            k = results[n]["by_kind"].get(kind)
            row += f"{'':>22}" if k is None else f"{k['caught']:>8}/{k['total']:<4}{_pct(k['caught'] / k['total']):>10}"
        print(row)
    print()
    for n in names:
        r = results[n]
        print(
            f"{n:<12} {r['cases']:>4} cases  recall {_pct(r['recall'])} of {r['identifiers']} identifiers  "
            f"damage {_pct(r['damage_rate'])} of {r['keep_strings']} clinical strings  "
            f"negatives altered {r['negatives_touched']}/{r['negatives']}"
        )
        if args.misses:
            for m in r["misses"]:
                print(f"    MISS   {m['id']:<10} {m['kind']:<15} {m['text']!r}\n           -> {m['out']}")
            for d in r["damage"]:
                print(f"    DAMAGE {d['id']:<10} {d['keep']!r}\n           -> {d['out']}")

    if args.json:
        args.json.write_text(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
