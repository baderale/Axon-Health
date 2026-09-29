# Axon Health — orientation

Read these first instead of re-deriving them:

| Need | Read |
|---|---|
| What Axon Health is: mission, vision, goals, glossary (draft, pending review) | `docs/about.md` |
| The founder's original brief | `InitialPrompt.txt` |
| Architecture, quickstart, roadmap | `README.md` |
| What each milestone built, its acceptance criteria, and what it found | `docs/milestones/` |
| The shareable dashboards, their published URLs, how to refresh them | `docs/dashboard/README.md` |

The original whole-platform design plan was never committed and is lost.
`docs/milestones/` is the record from milestone 2 onward. Write one file there
per milestone.

## Things that will trip you up

- **Tests against NATS pick up running services.** Stop `gatekeeper-interceptor`,
  `clinical-research` and `pharma` before `pytest`, or they answer the test
  traffic with real models. Restart them afterwards.
- **Tools run on the host need `NATS_URL=nats://localhost:4222`.** The default,
  `nats://nats:4222`, only resolves inside Docker, and nats-py retries forever
  instead of failing.
- **The Ollama app on the Mac holds port 11434.** Start the stack with
  `OLLAMA_HOST_PORT=11435`. Do not stop the user's Ollama app.
- **The NATS image has no `nats` CLI.** Read the audit trail with
  `docker compose run --rm audit <conversation_id>`.
- **Only the subsidiary runtime may publish.** Departments get a `consult`
  function. `tests/test_subsidiary_graph.py` fails if a department or Supervisor
  module imports `axon.bus`, `nats` or the runtime.
- **The 8B judges are not consistent.** A coach verdict from a live run may be
  the model, not the code. Read the audit trail before changing policy.
- **Pages meant to be shared must never contain real patient data.** Use the
  synthetic identifiers `patient_id 12345` / `MRN-AX-99182`.

## Conventions

- Python with **uv**. Tests: `uv run --extra dev python -m pytest -q` (with NATS
  up for the integration tests).
- When a milestone lands, update the README roadmap, add `docs/milestones/NN-*.md`,
  and refresh the dashboards (`docs/dashboard/README.md`).
