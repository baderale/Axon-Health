# Axon Health

AI-native medical-technology umbrella platform. Federated subsidiaries, LangGraph agents, two-tier HIPAA + Compliance gatekeepers on a NATS bus.

**New here?** Start with [`docs/about.md`](docs/about.md): what Axon Health is, its mission, vision and goals, and a glossary. To show the platform to someone, share the **Enterprise Console** or the **Org Map**. Both are listed with their links in [`docs/dashboard/`](docs/dashboard/README.md).

> **Status:** Three milestones done. The **gatekeeper layer** (Tier-1 deterministic policy + Tier-2 LLM judges + AUDIT/INCIDENT streams); the **first two subsidiaries**, Axon Clinical Research and Axon Pharma, which consult each other through it; and **Tier-1 coverage of all 18 HIPAA Safe Harbor identifiers**, measured at **82.9% recall with 1.5% damage to clinical text** on a held-out set (the milestone-2 rules caught 17.6%). The FastAPI/HTMX user surface, human review of blocks, and the pgvector data layer arrive in later milestones. Milestone details and acceptance criteria live in [`docs/milestones/`](docs/milestones/).

## Architecture in one paragraph

Subsidiaries (Axon Clinical Research, Axon Pharma, Axon Consumer, …) are **federated**: each runs its own LangGraph cluster, its own data stores, and its own model-serving pool. Cross-subsidiary traffic only flows over an **Inter-Subsidiary Bus** (NATS + JetStream). The **HIPAA Agent** and **Compliance Agent** sit as subscriber-interceptors on that bus and emit verdicts on a **severity ladder**: `allow`, `redact`, `coach`, `block`. Every cross-subsidiary message is mirrored to an immutable `AUDIT.*` stream; `block` verdicts open an incident on `INCIDENT.*` for human-in-the-loop review. Each subsidiary has exactly one Supervisor agent that owns *all* outbound publishes — this "single well-known publisher per subsidiary" invariant is what makes cross-subsidiary audit and authority enforcement tractable.

## Verdict pipeline

```
NATS axon.gatekeeper.in
       │
       ▼
  Tier-1 deterministic policy ──BLOCK──► INCIDENT.* + verdict
  (egress rules; 18 Safe Harbor
   identifiers: patterns + spaCy NER)
       │
       ├─REDACT  (escalate) ─┐
       └─ALLOW   (escalate) ─┤
                             ▼
                       HIPAA Agent ──BLOCK──► INCIDENT.* + verdict
                             │
                             ▼
                      Compliance Agent ──BLOCK──► INCIDENT.* + verdict
                             │                ──COACH──► verdict (no forward)
                             ▼
                    Combine verdicts
                       allow/redact ──► axon.gatekeeper.out.<target>  (target's inbox)
                       Always ────────► AUDIT.*
```

## A question, end to end

```
ask ─► axon.ingress.clinical_research
         Supervisor ─► Intake ─► Clinical SME ── consult("pharma", "research", record)
                                                        │
               gatekeeper (redacts patient_id, MRN) ◄───┘
                        │
                        ▼
         axon.gatekeeper.out.pharma ─► Pharma Supervisor ─► Pharma Research
                                                                  │ reply
               gatekeeper (checks the answer too) ◄───────────────┘
                        │
                        ▼
         axon.gatekeeper.out.clinical_research ─► Clinical SME writes the final answer
```

Departments never touch the bus. Each subsidiary's runtime (`axon/subsidiary/runtime.py`) is its only publisher, and a test enforces that.

## What Tier-1 removes

Tier-1 (`axon/gatekeeper/tier1_policy.py`, detector in `axon/gatekeeper/phi.py`) redacts the 18 HIPAA Safe Harbor identifiers before any AI judge sees a message:
- names
- sub-state places: street, city, ZIP
- every date element except the year, and ages over 89
- phone and fax numbers, and email addresses
- SSN, MRN, health-plan, account and licence numbers
- vehicle and device identifiers
- URLs and IP addresses
- biometric identifiers and photos
- any other identifying code.

Identifiers with a shape or a label are found by patterns. Names and places are found by spaCy (`en_core_web_sm`), with filters that keep eponyms, drug names, doses and lab values intact. Fields named like PHI (`dob`, `first_name`, `member_id`, …) are replaced whole at any depth.

Its score is measured, not assumed:

```sh
uv run python -m axon.tools.phi_eval            # recall and clinical-text damage per set
uv run python -m axon.tools.phi_eval --misses   # plus every miss and every damaged string
```

| Eval set (`evals/phi/`) | Cases | Recall | Clinical text damaged |
|---|---|---|---|
| `holdout.jsonl`: written blind, never tuned on | 100 | **82.9%** | 1.5% |
| `handwritten.jsonl`: written blind, used for tuning | 80 | 96.6% | 0.0% |
| `generated.jsonl`: seeded templates | 200 | 100.0% | 0.0% |

What it still misses, and why the 8B judges currently coach free-text messages after redaction, is in [milestone 3](docs/milestones/03-safe-harbor-phi.md).

## Repository layout

```
axon/
  bus/                 NATS client + canonical subject names
  gatekeeper/          Tier-1 policy, Safe Harbor PHI detector (phi.py), LLM judges, interceptor, verdict schema
  model_registry/      Logical model name → backend + weights + system prompt
  audit/               AUDIT.* / INCIDENT.* JetStream helpers
  subsidiary/          Template: department contract, Supervisor graph, runtime
  subsidiaries/        Axon Clinical Research, Axon Pharma, service entry point
  tools/               Operator CLIs (ask, audit, dashboard, fake_publisher, phi_eval)
evals/phi/             PHI evaluation sets (generated, handwritten, holdout) and their generator
docs/about.md          What Axon Health is: mission, vision, goals, glossary
docs/milestones/       Goals and acceptance criteria per milestone
docs/dashboard/        Shareable Enterprise Console and Org Map, and how to refresh them
seed_data/
  hipaa_rules/         RAG corpus for the HIPAA Agent
  compliance_policy/   RAG corpus for the Compliance Agent
tests/
  test_tier1_policy.py        Unit tests (no infra required)
  test_phi_detection.py       Unit tests (no infra required): 18 kinds, clinical text, eval floors
  test_judge.py               Unit tests (no infra required)
  test_subsidiary_graph.py    Unit tests (no infra required)
  test_interceptor.py         Integration tests (require NATS)
  test_cross_subsidiary.py    Integration tests (require NATS)
```

## Prerequisites

- Docker Desktop (or a Docker Engine that supports Compose v2)
- Python 3.12+ (only required if you want to run the test suite outside Docker)
- ~6 GB of disk for the Ollama base model (`llama3.1:8b`)

## Quickstart — full stack via Docker Compose

```pwsh
copy .env.example .env
docker compose up -d --build         # nats, ollama, ollama-init (pulls model), gatekeeper-interceptor,
                                     # clinical-research, pharma
docker compose ps                    # confirm everything is healthy

# Ask Clinical Research a question (it consults Pharma through the gatekeeper):
docker compose run --rm ask "Patient_id 12345, MRN MRN-AX-99182, hepatic impairment. Safe dosing window for acetaminophen?"

# Gatekeeper-only synthetic traffic:
docker compose run --rm fake-publisher allow
docker compose run --rm fake-publisher redact
docker compose run --rm fake-publisher safe-harbor --timeout 180   # free-text name, address, DOB
docker compose run --rm fake-publisher block
docker compose run --rm fake-publisher intra
```

Read the audit trail (the NATS image has no `nats` CLI, so use the bundled tool). Pass the `conversation_id` that `ask` printed to see one question's two legs:

```pwsh
docker compose run --rm audit <conversation_id> --payloads
docker compose run --rm audit                    # everything
```

**macOS with the Ollama app installed:** the native app already holds port 11434. Put `OLLAMA_HOST_PORT=11435` in `.env` (or export it) before `docker compose up`. The containers reach Ollama over the Docker network, so only the host-side port changes. Docker Desktop on a Mac runs Ollama on the CPU; one `ask` takes about a minute.

Tear down (preserving volumes):

```pwsh
docker compose down
```

## Running the test suite locally

The unit tests need no infrastructure. The integration tests need a running NATS broker but stub the Tier-2 LLM judges and the department models (so no Ollama is required for tests). Stop the `gatekeeper-interceptor`, `clinical-research` and `pharma` services while running them (`docker compose stop gatekeeper-interceptor clinical-research pharma`), or they pick up the test traffic and answer with real models.

macOS / Linux:

```sh
uv run --extra dev python -m pytest tests/test_tier1_policy.py tests/test_phi_detection.py tests/test_subsidiary_graph.py tests/test_judge.py -q   # unit only

docker compose up -d nats
NATS_URL=nats://localhost:4222 uv run --extra dev python -m pytest -q                               # full suite
```

Windows:

```pwsh
uv venv .venv --python 3.12
uv pip install -e .[dev]

# Unit tests only:
.venv\Scripts\python -m pytest tests/test_tier1_policy.py -v

# Full suite (needs NATS; brought up with `docker compose up -d nats`):
docker compose up -d nats
$env:NATS_URL = "nats://localhost:4222"
.venv\Scripts\python -m pytest -v
```

The current suite is **88 tests passing**: 79 unit (Tier-1 policy, Safe Harbor detection and eval floors, judge parsing, subsidiary graphs, single-publisher check) + 9 integration (interceptor, cross-subsidiary).

## Configuration

Environment variables (see `.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `NATS_URL` | `nats://nats:4222` | NATS broker address |
| `OLLAMA_BASE_URL` | `http://ollama:11434/v1` | OpenAI-compatible Ollama endpoint |
| `OLLAMA_API_KEY` | `ollama` | Ollama's placeholder API key (Ollama does no auth by default) |
| `DEFAULT_MODEL` | `llama3.1:8b` | Base model the judges use |
| `LOG_LEVEL` | `INFO` | Interceptor log level |
| `SEED_DATA_ROOT` | `/app/seed_data` | Where the judges find their RAG corpora |
| `AXON_CONSULT_TIMEOUT` | `300` | Seconds a department waits for another subsidiary's reply |
| `OLLAMA_HOST_PORT` | `11434` | Host-side port for the Ollama container |
| `AXON_PHI_NER` | `spacy` | Tier-1 name and place detection. `off` runs patterns only (bare names are then missed). If the model is missing and this is on, Tier-1 coaches every message |
| `AXON_PHI_NER_MODEL` | `en_core_web_sm` | spaCy model for that detection |

## Milestone roadmap

| Milestone | State |
|---|---|
| **Gatekeeper layer end-to-end** | **done** |
| Axon Clinical Research subsidiary (Supervisor + Intake + ClinSME + Compliance dept) | **done** except Compliance dept |
| Axon Pharma subsidiary (Supervisor + Pharma Research + Marketing) | **done** except Marketing |
| Cross-subsidiary primary scenario (redact path) | **done** ([milestone 2](docs/milestones/02-cross-subsidiary.md)) |
| Tier-1 covers all 18 Safe Harbor identifiers, with a measured score | **done** ([milestone 3](docs/milestones/03-safe-harbor-phi.md)) |
| Judge evaluation: labelled verdicts, per-model scores (the 8B judges coach free text after redaction) | next |
| Cross-subsidiary block-path smoke test (HITL) | not started |
| FastAPI + HTMX user surface (`/`, `/trace/<id>`, `/incidents`) | not started |
| pgvector data layer per subsidiary | not started |
| Real LoRA fine-tunes for departmental LLMs | deferred |

Acceptance criteria for each milestone from milestone 2 on are in [`docs/milestones/`](docs/milestones/). The original design plan for the whole platform was kept outside the repo and has not been recovered.

## Design tenets

- **Federated, not multi-tenant.** Each subsidiary is independent; cross-subsidiary traffic is the only audited surface.
- **Two-tier enforcement.** Deterministic policy on the fast path; LLM judges only when needed (cross-subsidiary, external egress, escalation).
- **Severity-ladder verdicts.** Most violations are fixable; some need a human. The schema reflects that.
- **Provider-agnostic inference.** Agents speak to an OpenAI-compatible facade; Ollama in dev, vLLM in production, real LoRA fine-tunes per department later.
- **Lift-and-shift to production.** Today's Compose topology maps 1-for-1 to a HIPAA-eligible managed-Kubernetes deployment.

## License

Not yet specified. All rights reserved by the author pending license selection.
