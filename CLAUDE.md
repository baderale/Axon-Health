# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Axon Health is a prototype AI-native medical-technology platform: federated subsidiaries made of LangGraph department agents, which talk to each other only through HIPAA and Compliance gatekeepers on a NATS bus. Everything runs in Docker, with Ollama serving `llama3.1:8b`.

## Where things are documented

| Need | Read |
|---|---|
| What Axon Health is: mission, vision, goals, glossary (draft, pending the founder's review) | `docs/about.md` |
| The founder's original brief | `InitialPrompt.txt` |
| Quickstart, config variables, roadmap | `README.md` |
| What each milestone built, its acceptance criteria, what it found | `docs/milestones/` (one file per milestone) |
| Shareable dashboards, their published URLs, how to refresh them | `docs/dashboard/README.md` |

The original whole-platform design plan was never committed and is lost. `docs/milestones/` is the record from milestone 2 onward.

## Commands

Python 3.12+ with **uv** (not pip or poetry).

```sh
# Unit tests (no infrastructure)
uv run --extra dev python -m pytest tests/test_tier1_policy.py tests/test_phi_detection.py tests/test_subsidiary_graph.py tests/test_judge.py -q

# Full suite: integration tests need NATS, and skip themselves if it is unreachable
docker compose up -d nats
docker compose stop gatekeeper-interceptor clinical-research pharma   # see "trip you up"
NATS_URL=nats://localhost:4222 uv run --extra dev python -m pytest -q

# One test
uv run --extra dev python -m pytest tests/test_cross_subsidiary.py::test_coach_verdict_reaches_clinical_sme_without_hanging -q

# Lint (the pre-existing SIM105/UP042/UP041 findings are known; don't mass-fix them)
uv run --extra dev ruff check axon tests

# Full stack with real models, then a live question and its audit trail
OLLAMA_HOST_PORT=11435 docker compose up -d --build
docker compose run --rm ask "Patient_id 12345, MRN MRN-AX-99182, hepatic impairment. Safe dosing window for acetaminophen?"
docker compose run --rm audit <conversation_id> --payloads

# Tier-1 PHI score: recall and clinical-text damage on evals/phi/*.jsonl (add --misses for detail)
uv run python -m axon.tools.phi_eval

# Rebuild the shareable console (add --refresh with NATS_URL set to pull new live runs)
uv run python -m axon.tools.dashboard
```

The Docker image is built only by the `gatekeeper-interceptor` service. The other services use `image: axon-health:dev` with `pull_policy: never`, so after code changes run `up -d --build`.

## Architecture

**One message, end to end.** Everything between subsidiaries follows this path. Most bugs sit at one of its hand-offs.

1. An operator task arrives on `axon.ingress.<subsidiary>` (NATS request-reply, used by `axon.tools.ask`).
2. The subsidiary's `SubsidiaryRuntime` (`axon/subsidiary/runtime.py`) runs it through the `Supervisor` graph, which runs the department pipeline (Clinical Research: `intake` → `clinsme`). Each department's output is merged into the task the next department sees.
3. A department that needs another subsidiary calls the `consult(target, dept, payload)` function it was given. The runtime wraps that in a `GatekeeperRequest` (subject `axon.{src}.{tgt}.{dept}.query`, headers `conversation_id`) and publishes it to `axon.gatekeeper.in`. It then waits on a future keyed by `trace_id`.
4. The interceptor (`axon/gatekeeper/interceptor.py`) runs Tier-1 rules (`tier1_policy.py`). Tier-1 blocks external egress and redacts the 18 Safe Harbor identifiers found by `phi.py`: patterns for shaped or labelled identifiers, spaCy NER for names and places. It then runs the HIPAA and Compliance judges (`judge.py`, LangGraph retrieve → LLM) on **Tier-1's redacted payload**, and combines the verdicts: block > coach > redact > allow. Every stage goes to `AUDIT.<trace_id>`, and a block opens `INCIDENT.<id>`.
5. Allow or redact delivers to `axon.gatekeeper.out.<target_subsidiary>`, which the interceptor picks from the request's target, never from sender headers. Every verdict is also announced on `axon.gatekeeper.verdict` as `{trace_id, in_reply_to, ..., verdict}`.
6. The target runtime runs the department named in the subject and replies through the gatekeeper with verb `reply` and header `in_reply_to=<original trace_id>`. The sender's future resolves from its inbox. A coach or block on **either** leg fails the future at once as a `ConsultationError`, matched by `trace_id` or `in_reply_to`, instead of waiting for the timeout.

**Invariants to preserve**
- **Only the runtime publishes.** Departments (`axon/subsidiaries/*.py`) and `supervisor.py`/`department.py` must not import `axon.bus`, `nats` or the runtime. `tests/test_subsidiary_graph.py` enforces this with an AST check.
- **All model calls go through the Model Registry** (`axon/model_registry/registry.py`): a logical name maps to backend, base model, system prompt and retrieval profile. Departments call `ask_model(logical_name, ...)` in `axon/subsidiary/department.py`. A LoRA fine-tune later is a registry change only. Tests stub models by monkeypatching `department.get_client`, and judges by monkeypatching `hipaa_agent.evaluate` / `compliance_agent.evaluate`.
- **Judge failures fail safe to `coach`**: unparseable output, schema errors and LLM errors all return coach. `_parse_verdict` lowercases decisions because the 8B model writes `"ALLOW"`. Tier-1 follows the same rule: if the spaCy model cannot load, it coaches (`phi.detector_unavailable`) rather than forwarding without name detection.
- Subject names live only in `axon/bus/subjects.py` (`cross_subsidiary`, `parse_cross_subsidiary`, `inbox`, `ingress`).

**Adding a subsidiary:** write department classes (`name`, `description`, `async handle(task, consult)`), give it a `build()` that returns a `Supervisor`, register it in `axon/subsidiaries/__init__.py`, and add a Compose service running `python -m axon.subsidiaries.run <name>`.

The judges' knowledge is keyword retrieval over `seed_data/<profile>/*.md` (`axon/gatekeeper/retrieval.py`). It is meant to become pgvector later.

## Things that will trip you up

- **Running services steal test traffic.** The interceptor subscribes in a queue group and the subsidiaries subscribe to their inboxes and ingress. With them running, integration tests get answers from real models. Stop them before `pytest`, and restart them afterwards.
- **Host-side tools need `NATS_URL=nats://localhost:4222`.** The default, `nats://nats:4222`, only resolves inside Docker, and nats-py retries forever instead of failing.
- **The Ollama app on the Mac holds port 11434.** Start the stack with `OLLAMA_HOST_PORT=11435`. Containers reach Ollama over the Docker network, so only the host port changes. Do not stop the user's Ollama app.
- **The NATS image has no `nats` CLI.** Read the audit trail with the `audit` service, not `nats stream view`.
- **The 8B judges are not consistent.** A coach verdict in a live run may come from the model rather than the code. Read the audit trail before changing policy or prompts.
- **The AUDIT stream mixes test and live traffic.** Test conversations have judge rationales starting with `stub `. `axon.tools.dashboard --refresh` filters them out.
- **PHI detector changes are scored, not eyeballed.** Run `axon.tools.phi_eval --misses` before and after. `tests/test_phi_detection.py` has recall and damage floors per eval set. Tune on `generated` and `handwritten`, never on `holdout.jsonl`. It was written blind and scored once, so it is the honest number. If you fix its misses, have a fresh holdout written by someone (or an agent) who has not seen `phi.py`.
- **Over-redaction is a bug too.** spaCy tags doses ("Max 3 g/day"), eponyms, drug brands and diseases ("West Nile") as people or places. The fix goes in the filters in `phi.py` (`_NOT_A_NAME`, `_DRUG_STEM`, `_ALLOWED_PLACES`), and every fix gets a case in `test_clinical_text_survives`.
- **The 8B Compliance judge coaches any message that shows a redaction**, whatever the marker says (milestone 3). A `safe-harbor` fake-publisher run ends in coach. The `ask` flow passes only because Intake restates the question without identifiers first.
- **Pages meant to be shared must never contain real patient data.** Use the synthetic identifiers `patient_id 12345` / `MRN-AX-99182`.

## Branches and config

- **`main` holds everything.** Milestones 2 and 3 were built on `milestone-*` branches and fast-forwarded into `main` on 2026-09-30. Start each milestone on a new `milestone-NN-*` branch off `main`, fast-forward `main` when it lands, then delete the branch.
- **`.env.example` lists only variables the code or `docker-compose.yml` reads.** The unused Postgres DSN, judge-model names and `TIER1_ESCALATE_AMBIGUOUS` were removed on 2026-09-30. Judge models are set in the Model Registry, not by environment. A variable in `.env` reaches a container only if that service's `environment:` block passes it through, as `AXON_PHI_NER` is for the interceptor.

## When a milestone lands

Update the README roadmap, add `docs/milestones/NN-*.md` with acceptance criteria and a live-run record, and update the dashboards. The structure diagram, headline numbers and roadmap cards in `docs/dashboard/console.template.html` are hand-written. `docs/about.md` and the console's About section must stay in step.
