"""Measure the Tier-2 judges: which messages they stop, which they should have.

    uv run python -m axon.tools.judge_eval                          # registry models, all sets
    uv run python -m axon.tools.judge_eval --model qwen3.6:35b      # swap the judges' base model
    uv run python -m axon.tools.judge_eval --repeats 3 --misses     # consistency, and every error
    uv run python -m axon.tools.judge_eval --json out.json

Needs a running Ollama with the model pulled. From the host, point at it with
``OLLAMA_BASE_URL=http://localhost:11434/v1`` (the default only resolves
inside Docker).

Each case in ``evals/judges/*.jsonl`` is a raw cross-subsidiary message. It is
run as the interceptor runs it: Tier-1 first, then both judges on Tier-1's
redacted payload, then the interceptor's own rule for combining verdicts and
picking the payload to deliver. Each case is labelled with what each judge
should do, ``pass`` (deliver) or ``stop`` (coach or block), and lists
``residual`` identifiers Tier-1 misses and ``keep`` strings the target needs.
The scores are about what would reach the target, not only the verdict:

  - **false stops**: of the messages that should be delivered, the share the
    pipeline stopped. This is the milestone-3 finding (the Compliance judge
    coaching anything that shows a redaction) as a number.
  - **PHI leaked**: of the messages carrying identifiers Tier-1 missed, the
    share delivered with one of them still in it. A judge's ``redact`` counts
    as protection only if its rewrite really removed them.
  - **compliance caught**: of the messages the Compliance judge should stop,
    the share stopped.
  - **damage**: of the ``keep`` strings in delivered messages, the share that
    did not arrive verbatim (Tier-1 over-redaction, or a judge's rewrite).
  - **fail-safe**: verdicts that were coach only because the judge output did
    not parse or the model call failed (``judge.*`` matched rules).

Both judges always run here, even where the interceptor would skip Compliance
after a HIPAA block, so each judge gets a score of its own.
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

from axon.bus.subjects import Subjects
from axon.gatekeeper import compliance_agent, hipaa_agent, tier1_policy
from axon.gatekeeper.interceptor import _combine_for_redact
from axon.gatekeeper.verdict import Decision, GatekeeperRequest, Verdict
from axon.model_registry import registry

EVAL_DIR = Path(__file__).resolve().parents[2] / "evals" / "judges"
SETS = {"tuning": "tuning.jsonl", "holdout": "holdout.jsonl"}
JUDGES = {"hipaa": hipaa_agent, "compliance": compliance_agent}
STOPS = {Decision.COACH, Decision.BLOCK}


def load(name: str) -> list[dict[str, Any]]:
    path = EVAL_DIR / SETS[name]
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def use_model(base_model: str, reasoning_effort: str | None, max_tokens: int | None = None) -> None:
    """Point both judge entries at another base model, in this process only."""
    for agent in JUDGES.values():
        spec = registry.REGISTRY[agent.LOGICAL_MODEL]
        registry.REGISTRY[agent.LOGICAL_MODEL] = dataclasses.replace(
            spec,
            base_model=base_model,
            reasoning_effort=reasoning_effort,
            max_tokens=max_tokens or spec.max_tokens,
        )


def request_for(case: dict[str, Any]) -> GatekeeperRequest:
    parsed = Subjects.parse_cross_subsidiary(case["subject"])
    if parsed is None:
        raise SystemExit(f"{case['id']}: not a cross-subsidiary subject: {case['subject']}")
    source, target, _, _ = parsed
    return GatekeeperRequest(
        source_subsidiary=source,
        target_subsidiary=target,
        subject=case["subject"],
        payload=case["payload"],
    )


def _fail_safe(verdict: Verdict) -> bool:
    return any(rule.startswith("judge.") for rule in verdict.matched_rules)


async def run_case(case: dict[str, Any], sem: asyncio.Semaphore) -> dict[str, Any]:
    request = request_for(case)
    tier1 = tier1_policy.evaluate(request)
    row: dict[str, Any] = {"id": case["id"], "tier1": tier1.decision.value}
    if tier1.decision is not Decision.REDACT and not tier1.needs_escalation():
        # Tier-1 settled it (a block, or a coach for a missing name model); the
        # judges never see this message in the interceptor either.
        row["final"] = "stop" if tier1.decision in STOPS else "pass"
        row["delivered"] = request.payload if row["final"] == "pass" else None
        return row

    judged = request
    if tier1.decision is Decision.REDACT and tier1.redacted_payload is not None:
        judged = request.model_copy(update={"payload": tier1.redacted_payload})
    row["judged_payload"] = judged.payload

    verdicts: list[Verdict] = []
    async with sem:
        start = time.monotonic()
        for name, agent in JUDGES.items():
            verdict = await agent.evaluate(judged)
            verdicts.append(verdict)
            row[name] = verdict.decision.value
            row[f"{name}_rationale"] = verdict.coaching_message or verdict.rationale
            row[f"{name}_fail_safe"] = _fail_safe(verdict)
        row["seconds"] = time.monotonic() - start

    final, payload = _combine_for_redact(request, tier1, verdicts)
    row["final"] = "stop" if final.decision in STOPS else "pass"
    row["delivered"] = payload if row["final"] == "pass" else None
    return row


def _text(payload: dict[str, Any] | None) -> str:
    return "" if payload is None else json.dumps(payload, ensure_ascii=False)


def outcome(decision: str) -> str:
    return "stop" if Decision(decision) in STOPS else "pass"


def score(cases: list[dict[str, Any]], runs: list[list[dict[str, Any]]]) -> dict[str, Any]:
    """Score every run of the same cases. Rates are pooled across runs."""
    by_id = {c["id"]: c for c in cases}
    deliver = false_stops = fail_safe = verdicts = 0
    phi_cases = leaked = comp_cases = comp_caught = keep_total = keep_lost = 0
    judge = {n: Counter() for n in JUDGES}
    decisions = {n: Counter() for n in JUDGES}
    errors: list[dict[str, Any]] = []
    seconds: list[float] = []

    for run in runs:
        for row in run:
            case = by_id[row["id"]]
            expect = "stop" if "stop" in (case["hipaa"], case["compliance"]) else "pass"
            if expect == "pass":
                deliver += 1
                false_stops += row["final"] == "stop"
            if case["compliance"] == "stop":
                comp_cases += 1
                comp_caught += row["final"] == "stop"
            delivered = _text(row["delivered"])
            if case.get("residual"):
                phi_cases += 1
                left = [r for r in case["residual"] if r in delivered]
                leaked += bool(left)
                if left:
                    errors.append({"id": row["id"], "judge": "delivered", "expected": "no PHI",
                                   "got": "leak", "why": f"still contains {left}", "payload": row["delivered"]})
            if row["delivered"] is not None:
                for keep in case.get("keep", []):
                    keep_total += 1
                    # json.dumps escapes newlines and quotes; compare like for like.
                    if json.dumps(keep, ensure_ascii=False)[1:-1] not in delivered:
                        keep_lost += 1
                        errors.append({"id": row["id"], "judge": "delivered", "expected": "keep",
                                       "got": "damaged", "why": keep, "payload": row["delivered"]})
            if "seconds" in row:
                seconds.append(row["seconds"])
            for n in JUDGES:
                if n not in row:
                    continue
                verdicts += 1
                fail_safe += row[f"{n}_fail_safe"]
                decisions[n][row[n]] += 1
                ok = outcome(row[n]) == case[n]
                judge[n]["right" if ok else "wrong"] += 1
                judge[n][f"{case[n]}_total"] += 1
                judge[n][f"{case[n]}_right"] += ok
                if not ok:
                    errors.append(
                        {
                            "id": row["id"],
                            "judge": n,
                            "expected": case[n],
                            "got": row[n],
                            "why": row[f"{n}_rationale"],
                            "payload": row.get("judged_payload"),
                        }
                    )

    # Consistency: share of cases whose final outcome was the same in every run.
    finals: dict[str, set[str]] = {}
    for run in runs:
        for row in run:
            finals.setdefault(row["id"], set()).add(row["final"])
    stable = sum(len(f) == 1 for f in finals.values())

    def rate(a: int, b: int) -> float | None:
        return a / b if b else None

    return {
        "cases": len(cases),
        "runs": len(runs),
        "false_stop_rate": rate(false_stops, deliver),
        "phi_leak_rate": rate(leaked, phi_cases),
        "compliance_catch_rate": rate(comp_caught, comp_cases),
        "damage_rate": rate(keep_lost, keep_total),
        "fail_safe": fail_safe,
        "verdicts": verdicts,
        "consistent": rate(stable, len(finals)) if len(runs) > 1 else None,
        "seconds_per_case": sum(seconds) / len(seconds) if seconds else None,
        "judges": {
            n: {
                "accuracy": rate(c["right"], c["right"] + c["wrong"]),
                "pass_right": rate(c["pass_right"], c["pass_total"]),
                "stop_right": rate(c["stop_right"], c["stop_total"]),
                "decisions": dict(decisions[n]),
            }
            for n, c in judge.items()
        },
        "errors": errors,
    }


def _pct(x: float | None) -> str:
    return "  -  " if x is None else f"{100 * x:5.1f}%"


async def evaluate_set(cases: list[dict[str, Any]], repeats: int, parallel: int) -> list[list[dict[str, Any]]]:
    sem = asyncio.Semaphore(parallel)
    runs = []
    for _ in range(repeats):
        runs.append(list(await asyncio.gather(*(run_case(c, sem) for c in cases))))
    return runs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--set", choices=[*SETS, "all"], default="all")
    parser.add_argument("--model", action="append", help="judge base model (repeat to compare); default: the registry's")
    parser.add_argument(
        "--reasoning-effort",
        default=None,
        help='passed to the model, e.g. "none" to turn off a thinking model\'s reasoning',
    )
    parser.add_argument("--max-tokens", type=int, help="override the judges' max_tokens (thinking needs more)")
    parser.add_argument("--repeats", type=int, default=1, help="run every case this many times")
    parser.add_argument("--parallel", type=int, default=2, help="cases judged at once")
    parser.add_argument("--misses", action="store_true", help="list every wrong judge verdict")
    parser.add_argument("--json", type=Path, help="write the full result, with every verdict, as JSON")
    args = parser.parse_args(argv)

    names = list(SETS) if args.set == "all" else [args.set]
    sets = {n: load(n) for n in names}
    models = args.model or [None]
    results: dict[str, dict[str, Any]] = {}

    for model in models:
        if model is not None:
            use_model(model, args.reasoning_effort, args.max_tokens)
        label = registry.REGISTRY[hipaa_agent.LOGICAL_MODEL].base_model
        results[label] = {}
        for n, cases in sets.items():
            if not cases:
                continue
            runs = asyncio.run(evaluate_set(cases, args.repeats, args.parallel))
            results[label][n] = {**score(cases, runs), "rows": runs}

    print(
        f"{'model':<16} {'set':<9} {'cases':>5}  {'false stops':>11}  {'PHI leaked':>10}  "
        f"{'compl caught':>12}  {'damage':>6}  {'fail-safe':>9}  {'consistent':>10}  {'s/case':>6}"
    )
    for label, by_set in results.items():
        for n, r in by_set.items():
            secs = "  -   " if r["seconds_per_case"] is None else f"{r['seconds_per_case']:6.1f}"
            print(
                f"{label:<16} {n:<9} {r['cases']:>5}  {_pct(r['false_stop_rate']):>11}  "
                f"{_pct(r['phi_leak_rate']):>10}  {_pct(r['compliance_catch_rate']):>12}  "
                f"{_pct(r['damage_rate']):>6}  "
                f"{r['fail_safe']:>4}/{r['verdicts']:<4}  {_pct(r['consistent']):>10}  {secs}"
            )
            if args.misses:
                for e in r["errors"]:
                    print(
                        f"    {e['id']:<8} {e['judge']:<10} expected {e['expected']:<4} got {e['got']:<8} "
                        f"{(e['why'] or '')[:150]!r}"
                    )

    if args.json:
        args.json.write_text(json.dumps(results, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
