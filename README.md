# Axon Health

AI-native medical-technology umbrella platform. Federated subsidiaries, LangGraph agents, two-tier HIPAA + Compliance gatekeepers on a NATS bus.

> **Status:** Two milestones done. The **gatekeeper layer** (Tier-1 deterministic policy + Tier-2 LLM judges + AUDIT/INCIDENT streams) and the **first two subsidiaries**, Axon Clinical Research and Axon Pharma, which consult each other through it. The FastAPI/HTMX user surface, human review of blocks, and the pgvector data layer arrive in later milestones. Milestone details and acceptance criteria live in [`docs/milestones/`](docs/milestones/).

## Architecture in one paragraph

Subsidiaries (Axon Clinical Research, Axon Pharma, Axon Consumer, …) are **federated**: each runs its own LangGraph cluster, its own data stores, and its own model-serving pool. Cross-subsidiary traffic only flows over an **Inter-Subsidiary Bus** (NATS + JetStream). The **HIPAA Agent** and **Compliance Agent** sit as subscriber-interceptors on that bus and emit verdicts on a **severity ladder**: `allow`, `redact`, `coach`, `block`. Every cross-subsidiary message is mirrored to an immutable `AUDIT.*` stream; `block` verdicts open an incident on `INCIDENT.*` for human-in-the-loop review. Each subsidiary has exactly one Supervisor agent that owns *all* outbound publishes — this "single well-known publisher per subsidiary" invariant is what makes cross-subsidiary audit and authority enforcement tractable.

## Verdict pipeline

```
NATS axon.gatekeeper.in
       │
       ▼
  Tier-1 deterministic policy ──BLOCK──► INCIDENT.* + verdict
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

## Repository layout

```
axon/
  bus/                 NATS client + canonical subject names
  gatekeeper/          Tier-1 policy, LLM judges, interceptor, verdict schema
  model_registry/      Logical model name → backend + weights + system prompt
  audit/               AUDIT.* / INCIDENT.* JetStream helpers
  subsidiary/          Template: department contract, Supervisor graph, runtime
  subsidiaries/        Axon Clinical Research, Axon Pharma, service entry point
  tools/               Operator CLIs (ask, fake_publisher)
docs/milestones/       Goals and acceptance criteria per milestone
seed_data/
  hipaa_rules/         RAG corpus for the HIPAA Agent
  compliance_policy/   RAG corpus for the Compliance Agent
tests/
  test_tier1_policy.py        Unit tests (no infra required)
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
uv run --extra dev python -m pytest tests/test_tier1_policy.py tests/test_subsidiary_graph.py -q   # unit only

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

The current suite is **37 tests passing**: 28 unit (Tier-1 policy, judge parsing, subsidiary graphs, single-publisher check) + 9 integration (interceptor, cross-subsidiary).

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

## Milestone roadmap

| Milestone | State |
|---|---|
| **Gatekeeper layer end-to-end** | **done** |
| Axon Clinical Research subsidiary (Supervisor + Intake + ClinSME + Compliance dept) | **done** except Compliance dept |
| Axon Pharma subsidiary (Supervisor + Pharma Research + Marketing) | **done** except Marketing |
| Cross-subsidiary primary scenario (redact path) | **done** ([milestone 2](docs/milestones/02-cross-subsidiary.md)) |
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
