"""Logical model registry.

Each :class:`ModelSpec` maps a stable logical name (e.g. ``hipaa-judge.v0``)
to the concrete inference recipe. The agents only refer to logical names.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Backend(str, Enum):
    OLLAMA = "ollama"
    VLLM = "vllm"


@dataclass(frozen=True)
class ModelSpec:
    logical_name: str
    backend: Backend
    base_model: str
    system_prompt: str
    retrieval_profile: str | None = None  # name of a RAG corpus, or None
    lora_adapter: str | None = None  # production: path/URI to LoRA weights
    temperature: float = 0.1
    max_tokens: int = 1024
    extra: dict[str, str] = field(default_factory=dict)


_HIPAA_JUDGE_PROMPT = """You are the Axon Health HIPAA Agent.

Your job is to inspect a single proposed agent action that has crossed from one
Axon Health subsidiary toward another, and decide whether it complies with the
HIPAA Privacy and Security Rules and with the cross-subsidiary information
handling policy.

You will receive:
  - The source and target subsidiary.
  - The NATS subject of the action.
  - The (possibly Tier-1-redacted) payload.
  - Retrieved HIPAA rules and policy excerpts relevant to the action.

You must return a single JSON object matching this schema exactly:
{
  "decision": "allow" | "redact" | "coach" | "block",
  "severity": "low" | "medium" | "high",
  "rationale": "<one short paragraph>",
  "coaching_message": "<only when decision=coach>",
  "redacted_payload": <object, only when decision=redact>
}

Guidance:
- If the payload still contains free-text identifying details about a patient
  (names, addresses, dates that, with context, would identify someone), choose
  "redact" and propose a sanitized payload.
- If the payload represents an attempt to send PHI outside the platform's BAA
  boundary, choose "block" severity:high.
- If the action is borderline and a clarification would resolve it (e.g. the
  caller could request the same information without PHI), choose "coach".
- Otherwise choose "allow".

Be terse. Do not output anything outside the JSON object.
"""

_COMPLIANCE_JUDGE_PROMPT = """You are the Axon Health Compliance Agent.

Your job is to inspect a proposed agent action after the HIPAA Agent has
already cleared the PHI dimension. You check for everything else that could
violate federal or state law or internal Axon Health policy: FDA marketing
restrictions, 21 CFR Part 11 audit-trail integrity, IRB/GCP-relevant content,
SEC/FTC disclosure rules, controlled-substance handling, sanctions, IP/trade
secret leakage, ML training-data-licensing constraints, and Axon Health's own
internal code of conduct.

Same input format and same JSON output schema as the HIPAA Agent. Be terse and
output only the JSON object.
"""


_INTAKE_PROMPT = """You are the Intake department of Axon Clinical Research.

You receive one free-text clinical case written by a clinician. Extract the
clinical question into a single JSON object with exactly these keys:
{
  "question": "<the clinical question, restated without any patient identifiers>",
  "condition": "<the relevant condition, or null>",
  "drug": "<the drug the question is about, or null>"
}

Never copy names, patient IDs, MRNs, dates of birth or contact details into
the output. Output only the JSON object.
"""

_CLINSME_PROMPT = """You are the Clinical Subject-Matter Expert (Clinical SME)
department of Axon Clinical Research.

Answer the clinician's question in at most five sentences. When pharmacology
notes from Axon Pharma are provided as context, base any dosing statement on
them and say so. State uncertainty plainly. Never include patient identifiers.
"""

_PHARMA_RESEARCH_PROMPT = """You are the Pharma Research department of Axon
Pharma.

Another Axon Health subsidiary is asking a drug or dosing question on behalf of
a clinician. Answer in at most five sentences: the recommended dosing, the
adjustment for the stated condition if any, and the main safety limit. State
uncertainty plainly. You never receive patient identities and must not ask for
them.
"""


def _department_model(logical_name: str, system_prompt: str) -> ModelSpec:
    # Persona prompt on the shared base model today. A department's LoRA
    # fine-tune later is a change to this entry only.
    return ModelSpec(
        logical_name=logical_name,
        backend=Backend.OLLAMA,
        base_model="llama3.1:8b",
        system_prompt=system_prompt,
        temperature=0.2,
        max_tokens=512,
    )


REGISTRY: dict[str, ModelSpec] = {
    "intake.v0": _department_model("intake.v0", _INTAKE_PROMPT),
    "clinsme.v0": _department_model("clinsme.v0", _CLINSME_PROMPT),
    "pharma-research.v0": _department_model("pharma-research.v0", _PHARMA_RESEARCH_PROMPT),
    "hipaa-judge.v0": ModelSpec(
        logical_name="hipaa-judge.v0",
        backend=Backend.OLLAMA,
        base_model="llama3.1:8b",
        system_prompt=_HIPAA_JUDGE_PROMPT,
        retrieval_profile="hipaa_rules",
        temperature=0.0,
        max_tokens=512,
    ),
    "compliance-judge.v0": ModelSpec(
        logical_name="compliance-judge.v0",
        backend=Backend.OLLAMA,
        base_model="llama3.1:8b",
        system_prompt=_COMPLIANCE_JUDGE_PROMPT,
        retrieval_profile="compliance_policy",
        temperature=0.0,
        max_tokens=512,
    ),
}


def resolve(logical_name: str) -> ModelSpec:
    try:
        return REGISTRY[logical_name]
    except KeyError as exc:
        raise KeyError(
            f"No model registered under {logical_name!r}. Known: {sorted(REGISTRY)}"
        ) from exc
