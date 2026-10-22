# Milestone 4: The AI judges are measured, and decide only whether a message goes

**Status:** done (2026-10-22)

## Goal

Measure the Tier-2 judges the way milestone 3 measured Tier-1, and fix them
stopping safe messages. Milestone 3 found that the 8B Compliance judge coached
any message that showed a redaction, so free-text PHI could never cross even
after Tier-1 removed it. There was no number for how often the judges were
wrong, in either direction.

## What was built

| Piece | Where |
|---|---|
| Evaluation tool: runs each case through Tier-1, both judges and the interceptor's combine rule, then scores what would be delivered | `axon/tools/judge_eval.py` |
| Two labelled sets (100 synthetic cases) | `evals/judges/` |
| Judges no longer rewrite payloads: a judge's `redact` is sent back as a `coach`; only Tier-1's redaction is ever delivered | `axon/gatekeeper/interceptor.py` (`_combine_for_redact`) |
| New judge prompts: HIPAA looks for what Tier-1 missed; Compliance says what internal work is allowed | `axon/model_registry/registry.py` |
| Judges moved to `qwen3.6:35b` with thinking off (`JUDGE_MODEL`); departments stay on `llama3.1:8b` | `axon/model_registry/registry.py`, `docker-compose.yml` |
| `reasoning_effort` on `ModelSpec`, passed to the model when set | `axon/model_registry/` |
| Policy pages for securities, sanctions and controlled substances, which the Compliance prompt always listed but had nothing to retrieve | `seed_data/compliance_policy/04_*.md`, `05_*.md` |
| Fail-safe judge verdicts are tagged (`judge.parse_failed`, `judge.schema_invalid`, `judge.llm_error`); `"REJECT"` reads as block | `axon/gatekeeper/judge.py` |
| Tier-1 catches an MRN with the label fused on (`MRN-AX-99182` on its own), found by the holdout | `axon/gatekeeper/phi.py` |
| 6 unit tests | `tests/test_judge.py`, `tests/test_phi_detection.py` |

### The evaluation sets

Each case is a raw cross-subsidiary message with what each judge should do
(`pass` = deliver, `stop` = coach or block), the `residual` identifiers that
Tier-1 misses, and `keep` strings the target needs.

| Set | Cases | Written by | Role |
|---|---|---|---|
| `tuning.jsonl` | 40 (24 both pass, 6 HIPAA stop, 10 Compliance stop) | Written alongside the fixes | Tuning set |
| `holdout.jsonl` | 60 (35 both pass, 12 HIPAA stop, 13 Compliance stop) | A separate agent that never saw the judge prompts or code | **The honest number.** Each configuration scored once |

### What is scored

The first runs showed that a verdict label is not enough. The 8B HIPAA judge
never coached: it answered `redact` on 19 of 40 tuning cases, 14 of them clean,
and the interceptor delivered its rewritten payload unchecked. The rewrites
left names in ("np carmen reyes"), deleted doses ("clozapine 300 mg, ANC 1200"
became markers) and dropped ages ("52M", "74F"). So the tool scores what would
reach the target:

- **false stops**: safe messages stopped.
- **PHI leaked**: messages carrying identifiers Tier-1 missed that were
  delivered with one still in them.
- **compliance caught**: messages the Compliance judge should stop that were
  stopped.
- **damage**: clinical strings in delivered messages that did not arrive
  verbatim.

## Results

`uv run python -m axon.tools.judge_eval`, on the Mac's native Ollama (Apple
M5 Pro, Metal).

**Tuning set**, 2 runs per case:

| Configuration | False stops | PHI leaked | Compliance caught | Damage | s/case |
|---|---|---|---|---|---|
| Milestone-3 code, llama3.1:8b | 12.5% | 66.7% | 80.0% | 10.4% | 13.8 |
| Milestone-3 code, qwen3.6:35b | 0.0% | 33.3% | 100% | 6.7% | 20.5 |
| This milestone, llama3.1:8b | 25.0% | 0.0% | 100% | 0.0% | 12.4 |
| This milestone, qwen3.6:35b, thinking off | 12.5% | 0.0% | 100% | 0.0% | 12.0 |
| This milestone, qwen3.6:35b, thinking low | 0.0% | 0.0% | 100% | 0.0% | 108.8 |

Every configuration gave the same final outcome in both runs of every case.

**Holdout**, scored once per configuration after the code was frozen:

| Configuration | False stops | PHI leaked | Compliance caught | Damage | s/case |
|---|---|---|---|---|---|
| llama3.1:8b | 6.1% | **50.0%** (7 of 14) | 92.3% | 0.0% | 13.0 |
| **qwen3.6:35b, thinking off (shipped)** | **0.0%** | **7.1%** (1 of 14) | **100%** | **0.0%** | 14.6 |
| qwen3.6:35b, thinking low | 0.0% | 0.0% | 100% | 0.0% | 105.4 |

These are the numbers after correcting four holdout labels; see below. As
first scored, the three rows were 8.6% / 41.7% / 92.3%, 8.6% / 8.3% / 100% and
8.6% / 0.0% / 100%.

Thinking is 7 times slower for one more catch. A consultation crosses the
gatekeeper twice, so thinking judges would take three to four minutes against
a 300-second consult timeout. Thinking off ships.

**What the shipped judges still get wrong on the holdout:**

- Leaked: a device code (`7731AXQ0098`) that the HIPAA judge read as a lab or
  device code, not an identifier.
- Over-cautious, in cases that were stopped for other reasons anyway: a study
  subject code ("subject 0412"), a redacted address next to "epilepsy", one
  parse failure (the model reasoned inside `rationale` and ran past the token
  limit), and one HIPAA `block` on a trade-secret message.
- The llama misses were all quasi-identifiers and unusual IDs: "the oldest
  resident of tangier island", "the only known fibrodysplasia ossificans
  progressiva patient in marfa, texas", a social-media handle, a member ID with
  an unknown label.

### Holdout label corrections

The holdout's author labelled cases by what they expected Tier-1 to remove.
Four expectations were wrong, and the labels are defined as "what remains
after Tier-1", so they were corrected after scoring and the saved verdicts
rescored without re-running anything:

- jh-007, jh-024, jh-047: `MRN-AX-99182` on its own, with no "MRN " label in
  front, was not caught by Tier-1. The ID reached the judges, and qwen was
  right to coach. Counted as HIPAA `stop` for the numbers above. Tier-1 now
  catches it (below), so the file labels them `pass` again for future runs.
- jh-011: Tier-1 does catch the three names in its CSV rows. Relabelled `pass`.

Each correction is recorded in the case's `note`.

## Finding: an LLM judge must not be the redactor

Before this milestone a judge answering `redact` supplied the payload that was
delivered, and nothing checked it: not Tier-1, not the other judge. On the
tuning set the 8B rewrites leaked identifiers in 4 of 6 cases and damaged 10%
of the clinical text. Now Tier-1 is the only redactor; the judges decide
whether a message goes and never what it says. A judge that finds an
identifier coaches the sender with the detail quoted ("Remove 'carmen
reyes'"), and the department restates. The schema keeps `redact` so old
verdicts in the AUDIT stream still parse.

## Finding: the 8B model cannot ignore redaction markers

With the new prompts the 8B HIPAA judge took over the milestone-3 failure: it
coached 7 safe tuning messages for "the patient's name '[REDACTED:name]'".
`qwen3.6:35b` reads the markers correctly in most cases. The one marker case it
still coaches with thinking off is a dense one: "[REDACTED:name], DOB
[REDACTED:date], … 58 year old … Her daughter [REDACTED:name] asks". That is
the `safe-harbor` scenario, which was coached 3 of 3 times in the live run
below, now by HIPAA rather than Compliance. With thinking on, it passes.

## Acceptance criteria

| # | Criterion | Checked by |
|---|---|---|
| 1 | The judges have a score: false stops, leaks, compliance catches, damage, per model | `judge_eval`, tables above |
| 2 | Measured on a set written blind and scored once | `holdout.jsonl`, tables above |
| 3 | Fewer safe messages stopped than with llama3.1:8b, the milestone-3 judge model, on the holdout | 0.0%, against 6.1% for llama3.1:8b |
| 4 | Fewer leftover identifiers delivered than with llama3.1:8b, on the holdout | 7.1%, against 50.0% for llama3.1:8b |
| 5 | Only Tier-1's deterministic redaction is ever delivered | `test_a_judge_redact_is_sent_back_not_delivered`, `test_only_the_tier1_redaction_is_delivered` |
| 6 | Fail-safe verdicts are visible in the audit trail | `test_fail_safe_verdicts_are_tagged` |
| 7 | Tier-1 changes are scored and do not regress | `phi_eval` unchanged on all three sets; new case in `test_each_safe_harbor_kind_is_removed` |
| 8 | All tests pass | full suite: 94 passed |

### Live run (2026-10-22, judges `qwen3.6:35b`, departments `llama3.1:8b`)

Docker was not installed on this machine, so the services ran on the host
(`python -m axon.gatekeeper.interceptor`, `python -m axon.subsidiaries.run
clinical_research` and `pharma`) against a local `nats-server` and the native
Ollama.

**1. The demo question** (`ask`, conversation `e5e074d3`), answered end to end
in 17 seconds, against about a minute on Docker's CPU in milestone 3:

```
tier1.redact                  axon.clinical_research.pharma.research.query
tier2.hipaa.allow             axon.clinical_research.pharma.research.query
tier2.compliance.allow        axon.clinical_research.pharma.research.query
interceptor.published.redact  axon.clinical_research.pharma.research.query
tier1.allow                   axon.pharma.clinical_research.research.reply
tier2.hipaa.allow             axon.pharma.clinical_research.research.reply
tier2.compliance.allow        axon.pharma.clinical_research.research.reply
interceptor.published.allow   axon.pharma.clinical_research.research.reply
```

Answer: "a maximum of 2 grams per day, divided into 2-3 doses, with a maximum
single dose of 1 gram."

**2. `fake-publisher safe-harbor`**, three times: coached by the HIPAA judge
each time, "Remove '58 year old' and '[REDACTED:name]'". See the finding above.

## Known limits, for later milestones

- The `safe-harbor` scenario is still coached. Options: thinking on for the
  HIPAA judge only (it passed with thinking; the cost is time on every
  message), or show the judges the removed identifiers as structured data
  (`"removed": ["name", "date"]`) instead of inline markers. The second is
  untested.
- Coaching only helps if the sender acts on it. Today a coach fails the
  consultation (`ConsultationError`); no department retries with the judge's
  advice.
- `qwen3.6:35b` is 23 GB. Docker Desktop on a Mac runs Ollama on the CPU and
  needs about 28 GB of memory for it; the runs here used the native Ollama on
  Metal. The Docker stack was not run in this milestone.
- The holdout has 14 leftover-PHI cases, so one leak moves the rate by 7
  points. A larger set is needed before the leak rate means much.
- A new holdout is needed before tuning against this one's misses.
