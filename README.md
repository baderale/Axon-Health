# Axon Health

AI-native medical-technology umbrella platform. Federated subsidiaries, LangGraph agents, two-tier HIPAA + Compliance gatekeepers on a NATS bus.

> **Status:** This repository currently implements the **gatekeeper layer** of the platform end-to-end (Tier-1 deterministic policy + Tier-2 LLM judges + AUDIT/INCIDENT streams), as the first milestone of a larger prototype. Subsidiary LangGraph clusters, the FastAPI/HTMX user surface, and the pgvector data layer arrive in subsequent milestones.

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
                       allow/redact ──► axon.gatekeeper.out
                       Always ────────► AUDIT.*
```

## Repository layout

```
axon/
  bus/                 NATS client + canonical subject names
  gatekeeper/          Tier-1 policy, LLM judges, interceptor, verdict schema
  model_registry/      Logical model name → backend + weights + system prompt
  audit/               AUDIT.* / INCIDENT.* JetStream helpers
  tools/               Operator CLIs (fake_publisher, etc.)
seed_data/
  hipaa_rules/         RAG corpus for the HIPAA Agent
  compliance_policy/   RAG corpus for the Compliance Agent
tests/
  test_tier1_policy.py   Unit tests (no infra required)
  test_interceptor.py    Integration tests (require NATS)
```

## Prerequisites

- Docker Desktop (or a Docker Engine that supports Compose v2)
- Python 3.12+ (only required if you want to run the test suite outside Docker)
- ~6 GB of disk for the Ollama base model (`llama3.1:8b`)

## Quickstart — full stack via Docker Compose

```pwsh
copy .env.example .env
docker compose up -d                 # nats, ollama, ollama-init (pulls model), gatekeeper-interceptor
docker compose ps                    # confirm everything is healthy

docker compose run --rm fake-publisher allow
docker compose run --rm fake-publisher redact
docker compose run --rm fake-publisher block
docker compose run --rm fake-publisher intra
```

Inspect the audit and incident streams from inside the NATS container:

```pwsh
docker compose exec nats nats stream view AUDIT
docker compose exec nats nats stream view INCIDENT
```

Tear down (preserving volumes):

```pwsh
docker compose down
```

## Running the test suite locally

The unit tests need no infrastructure. The integration tests need a running NATS broker but stub the Tier-2 LLM judges (so no Ollama is required for tests).

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

The current suite is **16 tests passing**: 11 Tier-1 unit + 5 interceptor integration.

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

## Milestone roadmap

| Milestone | State |
|---|---|
| **Gatekeeper layer end-to-end** | **done** |
| Axon Clinical Research subsidiary (Supervisor + Intake + ClinSME + Compliance dept) | not started |
| Axon Pharma subsidiary (Supervisor + Pharma Research + Marketing) | not started |
| Cross-subsidiary primary scenario (redact path) | not started |
| Cross-subsidiary block-path smoke test (HITL) | not started |
| FastAPI + HTMX user surface (`/`, `/trace/<id>`, `/incidents`) | not started |
| pgvector data layer per subsidiary | not started |
| Real LoRA fine-tunes for departmental LLMs | deferred |

The full architecture and acceptance criteria for each milestone are in the design plan (kept in the maintainer's `~/.claude/plans/` — not in this repo).

## Design tenets

- **Federated, not multi-tenant.** Each subsidiary is independent; cross-subsidiary traffic is the only audited surface.
- **Two-tier enforcement.** Deterministic policy on the fast path; LLM judges only when needed (cross-subsidiary, external egress, escalation).
- **Severity-ladder verdicts.** Most violations are fixable; some need a human. The schema reflects that.
- **Provider-agnostic inference.** Agents speak to an OpenAI-compatible facade; Ollama in dev, vLLM in production, real LoRA fine-tunes per department later.
- **Lift-and-shift to production.** Today's Compose topology maps 1-for-1 to a HIPAA-eligible managed-Kubernetes deployment.

## License

Not yet specified. All rights reserved by the author pending license selection.
