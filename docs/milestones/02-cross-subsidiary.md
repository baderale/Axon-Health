# Milestone 2: First two subsidiaries talking through the gatekeepers

**Status:** done (2026-09-29)

## Goal

Replace the gatekeeper's fake test traffic with real subsidiaries. A clinician's
question enters Axon Clinical Research, which consults Axon Pharma through the
gatekeeper. Patient identifiers are stripped on the way out, Pharma's answer
comes back through the gatekeeper too, and every step lands in `AUDIT`.

## What was built

| Piece | Where |
|---|---|
| Subsidiary template: department contract, Supervisor graph, runtime | `axon/subsidiary/` |
| Axon Clinical Research: Intake, Clinical SME | `axon/subsidiaries/clinical_research.py` |
| Axon Pharma: Pharma Research | `axon/subsidiaries/pharma.py` |
| Department models `intake.v0`, `clinsme.v0`, `pharma-research.v0` | `axon/model_registry/registry.py` |
| Service entry point, demo CLI, audit viewer | `axon/subsidiaries/run.py`, `axon/tools/ask.py`, `axon/tools/audit.py` |

### How a subsidiary is put together

- **Departments** are LangGraph workflows with their own logical model. They
  get a task and return a result. They cannot reach the bus; to talk to another
  subsidiary they call the `consult(target, dept, payload)` function their
  Supervisor gives them.
- **The Supervisor** routes a task through the department pipeline
  (Clinical Research: `intake` → `clinsme`), or to one named department for a
  request arriving from another subsidiary.
- **The runtime** is the only publisher. It sends consults to
  `axon.gatekeeper.in`, receives cleared messages on its inbox
  `axon.gatekeeper.out.<name>`, answers requests back through the gatekeeper
  with verb `reply`, and accepts operator input on `axon.ingress.<name>`.

To add a subsidiary: write its departments, a `build()` that returns a
`Supervisor`, register it in `axon/subsidiaries/__init__.py`, and add a Compose
service running `python -m axon.subsidiaries.run <name>`.

### Gatekeeper changes made along the way

- Cleared messages go to the target's inbox, chosen by the interceptor from
  `target_subsidiary`. The old sender-controlled `forward_to` header is gone.
- Verdicts are published as `{trace_id, in_reply_to, source_subsidiary,
  target_subsidiary, verdict}` so a sender can match them to its own messages.
- Forwarded messages carry `in_reply_to` and `conversation_id`.
- Tier-1 checks both the department and verb segments of the subject for
  egress words. Before, `axon.x.y.research.send` was not caught.
- A blocked message now produces one verdict announcement (with the incident
  id) instead of two.

Found during the live run with real models:

- The Tier-2 judges were given the original payload, not Tier-1's redacted
  one, so the Compliance Agent objected to an MRN that had already been
  removed. They now judge what would actually be forwarded, as the HIPAA
  judge's prompt always said.
- The judges get a plain-language `exchange` line (for example, "The research
  department of pharma is answering a question that clinical_research asked")
  instead of having to decode the subject. Without it, the 8B model treated
  Pharma's dosing answer as possible promotional copy.
- The verdict parser accepts `"ALLOW"` / `"High"`. The 8B model answered in
  capitals, and an intended allow was being turned into a coach.
- `OLLAMA_HOST_PORT` makes the Ollama container's host port configurable, for
  Macs where the native Ollama app already uses 11434.

## Acceptance criteria

| # | Criterion | Checked by |
|---|---|---|
| 1 | A case containing `patient_id 12345` and an MRN, sent to Clinical Research, produces a final answer | `test_case_is_redacted_on_the_way_to_pharma_and_answered`, live run |
| 2 | The message Pharma receives contains neither `12345` nor the MRN, and is marked `redacted: true` | same test, live run |
| 3 | Pharma's reply also passes through the gatekeeper, as a second trace linked by `in_reply_to` | same test, live run |
| 4 | A coach or block verdict on either leg reaches Clinical SME as an error, without waiting for the timeout | `test_coach_verdict_reaches_clinical_sme_without_hanging`, `test_block_on_the_reply_leg_also_fails_fast` |
| 5 | No department or Supervisor module imports `axon.bus`, `nats` or the runtime | `test_departments_and_supervisors_never_touch_the_bus` |
| 6 | All pre-existing tests still pass | full suite |

### Live run (2026-09-29, `llama3.1:8b`, Docker Desktop on macOS, CPU)

Case: *"Patient_id 12345, MRN MRN-AX-99182, 58 year old with hepatic
impairment. What is the safe dosing window for acetaminophen?"* About 50 seconds.

```
tier1.redact                  axon.clinical_research.pharma.research.query
tier2.hipaa.redact            axon.clinical_research.pharma.research.query
tier2.compliance.allow        axon.clinical_research.pharma.research.query
interceptor.published.redact  axon.clinical_research.pharma.research.query
    forwarded: {"condition": "hepatic impairment", "drug": "acetaminophen",
                "question": "What is the safe dosing window for acetaminophen?"}
tier1.allow                   axon.pharma.clinical_research.research.reply
tier2.hipaa.allow             axon.pharma.clinical_research.research.reply
tier2.compliance.allow        axon.pharma.clinical_research.research.reply
interceptor.published.allow   axon.pharma.clinical_research.research.reply
```

Final answer from Clinical SME: at most 2 g/day, at most 1 g per dose in
hepatic impairment, based on Axon Pharma's notes. The answer's medical
accuracy is not an acceptance criterion; the flow is.

## Known limits, for later milestones

- `axon.gatekeeper.verdict` is one shared subject, so every subsidiary sees
  every verdict (including redacted payloads). Per-subsidiary verdict subjects
  would fit the federated model better.
- A timed-out or failed consult is reported to the caller but not retried.
- Department models are persona prompts on `llama3.1:8b`; LoRA fine-tunes are
  still deferred. One case makes seven model calls (about 50 s on CPU-only
  Docker on a Mac).
- The 8B judges are not fully consistent. Before the fixes above, the same
  case was coached on one run and allowed on the next. Expect some coach
  verdicts that a larger judge model would not give.
- Clinical Research's Compliance department and Pharma's Marketing department
  are not built yet.
