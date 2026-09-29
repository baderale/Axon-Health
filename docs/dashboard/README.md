# Dashboards

Two shareable pages that explain Axon Health to people who don't read code.
Both are published as private claude.ai artifacts; share them from the page's
**Share** menu.

| Page | File | Published at |
|---|---|---|
| **Axon Health Enterprise Console**: about Axon Health, enterprise map, live gatekeeper traces, models, roadmap | `axon-console.html` (built) | https://claude.ai/artifact/LRyuKZ9cZjSD3pDskCuyk1 |
| **Axon Health Org Map**: one-page organisational chart with built / planned / idea status | `org-map.html` | https://claude.ai/artifact/XqDRLGNk9xBRVRu69i9bLf |

The console is a **snapshot**, not a live feed: a shared web page cannot reach
the platform's NATS server. The live version inside the platform is the
"operator web interface" milestone on the roadmap.

## Files

| File | What it is | Edit it? |
|---|---|---|
| `console.template.html` | The console's layout, styles, script, and hand-written content (About section, enterprise map, model list, roadmap, headline numbers) | Yes, for content and design |
| `snapshot.json` | Live-run audit events, plus a note and final answer per run | Yes, for run notes and final answers |
| `axon-console.html` | Template + snapshot, built by the tool below | No, rebuild it |
| `org-map.html` | The org chart, a standalone page | Yes |

## Rebuild or refresh

```sh
# Rebuild the page after editing the template or snapshot.json:
uv run python -m axon.tools.dashboard

# Pull new live runs from the AUDIT stream first (needs NATS running):
NATS_URL=nats://localhost:4222 uv run python -m axon.tools.dashboard --refresh
```

`--refresh` keeps every conversation that used real models and drops the ones
the automated tests produced (their stand-in judges' reasons start with
`stub `). It keeps existing notes and final answers. New runs get empty ones:
fill them in `snapshot.json`. The final answer is not in the audit log, so copy
it from the `ask` output.

Then publish `axon-console.html` to the same URL (ask Claude to "republish the
Enterprise Console", or pass the URL above as the artifact to update).

## Keep in step

- The About section repeats `docs/about.md`. Change both together.
- The headline numbers (subsidiaries and departments live, test count) and the
  roadmap cards are hand-written in the template. Update them when a milestone
  lands.
- The traces show the synthetic test identifiers `patient_id 12345` and
  `MRN-AX-99182`. Never put real patient data in `snapshot.json`: this page is
  meant to be shared.
