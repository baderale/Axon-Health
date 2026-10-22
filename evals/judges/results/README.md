# Saved judge_eval runs (milestone 4)

The raw `judge_eval --json` output behind the tables in
`docs/milestones/04-judge-evaluation.md`, run on 2026-10-22 against the Mac's
native Ollama. All payloads are synthetic.

| File | Set | Code | Model |
|---|---|---|---|
| `tuning-m3code-llama3.1-8b.json` | tuning | milestone 3 | llama3.1:8b |
| `tuning-m3code-qwen3.6-35b.json` | tuning | milestone 3 | qwen3.6:35b |
| `tuning-llama3.1-8b.json` | tuning | milestone 4 | llama3.1:8b |
| `tuning-qwen3.6-35b-thinking-off.json` | tuning | milestone 4 | qwen3.6:35b, `reasoning_effort=none` |
| `tuning-qwen3.6-35b-thinking-low.json` | tuning | milestone 4 | qwen3.6:35b, `reasoning_effort=low` |
| `holdout-*.json` | holdout | milestone 4 | as named |

The holdout files were scored with the labels as first written. The milestone
doc's holdout numbers come from rescoring these saved verdicts after four label
corrections (jh-007, jh-011, jh-024, jh-047); see the cases' `note` fields.
