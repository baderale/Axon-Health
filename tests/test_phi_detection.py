"""Unit tests for the Safe Harbor PHI detector and its use in Tier-1.

No infrastructure needed. The spaCy model ships as a project dependency; the
eval-set tests at the bottom run the same measurement as
``python -m axon.tools.phi_eval`` and fail if it regresses.
"""

from __future__ import annotations

import pytest

from axon.gatekeeper import phi, tier1_policy
from axon.gatekeeper.verdict import Decision, GatekeeperRequest
from axon.tools import phi_eval


def _removed(text: str, value: str) -> bool:
    out, _ = phi.redact_text(text)
    return value not in out


@pytest.mark.parametrize(
    ("kind", "text", "value"),
    [
        ("name", "Pt Maria Gonzalez presents with cirrhosis.", "Maria Gonzalez"),
        ("name", "Asked by Mr. Okafor about warfarin.", "Okafor"),
        ("name", "Daughter Lisa called about her mother's metformin.", "Lisa"),
        ("name", "Wei Chen reports nausea after starting metformin.", "Wei Chen"),
        ("address", "Lives at 42 Oak Street, Apt 3B, with her son.", "42 Oak Street, Apt 3B"),
        ("address", "Resident of Boise, ID with CKD stage 3.", "Boise"),
        ("zip", "Moved to Boise, ID 83702 last year.", "83702"),
        ("date", "Admitted 03/14/2026 for GI bleed.", "03/14/2026"),
        ("date", "DOB 1948-07-02.", "1948-07-02"),
        ("date", "Discharged March 3, 2026 on apixaban.", "March 3, 2026"),
        ("date", "Seen 3 June 2026 in clinic.", "3 June 2026"),
        ("age_over_89", "94 y/o with a hip fracture.", "94"),
        ("age_over_89", "Aged 91, frail.", "91"),
        ("phone", "Call back at (555) 201-9934.", "(555) 201-9934"),
        ("fax", "Fax records to 555-201-9935.", "555-201-9935"),
        ("email", "Portal message from maria.g@example.com.", "maria.g@example.com"),
        ("ssn", "SSN 123-45-6789 on file.", "123-45-6789"),
        ("mrn", "MRN MRN-AX-10442, admitted overnight.", "MRN-AX-10442"),
        ("health_plan_id", "Member ID: XJH4452109, prior auth pending.", "XJH4452109"),
        ("health_plan_id", "Medicare 1EG4TE5MK73 on file.", "1EG4TE5MK73"),
        ("account_number", "Acct# 99812-33 flagged by billing.", "99812-33"),
        ("license_number", "DL D1234567 scanned at intake.", "D1234567"),
        ("vehicle_id", "VIN 1HGCM82633A004352 in the MVA report.", "1HGCM82633A004352"),
        ("device_id", "Pacemaker serial no. PM-88213.", "PM-88213"),
        ("url", "Photos at https://portal.example.com/u/882.", "https://portal.example.com/u/882"),
        ("ip_address", "Telehealth login from 73.21.4.190.", "73.21.4.190"),
        ("biometric", "Fingerprint hash: 9f8a77c1d2 matched.", "9f8a77c1d2"),
        ("photo", "Wound photo data:image/png;base64,iVBORw0KGgoAAAA attached.", "iVBORw0KGgoAAAA"),
        ("patient_id", "Patient ID 448812 known to the service.", "448812"),
        ("other_id", "Claim #: CLM36102301 denied.", "CLM36102301"),
        ("other_id", "Ref 4471883221009 on the fax.", "4471883221009"),
    ],
)
def test_each_safe_harbor_kind_is_removed(kind, text, value):
    out, findings = phi.redact_text(text)
    assert value not in out, out
    assert kind in {f.kind for f in findings}, findings


@pytest.mark.parametrize(
    "text",
    [
        "Max 3 g/day in hepatic impairment.",
        "Hodgkin lymphoma, s/p ABVD since 2019.",
        "Parkinson's disease on carbidopa-levodopa 25/100 tid.",
        "Rash concerning for Stevens-Johnson syndrome.",
        "Child-Pugh B: halve the dose.",
        "Tylenol 500 mg q6h, Eliquis 5 mg bid.",
        "Plt 150000, INR 2.5, BP 128/82, 1/2 tab if eGFR under 30.",
        "Dosing plan 500mg bid for 7 days.",
        "Per https://www.fda.gov/drugs and https://dailymed.nlm.nih.gov/dailymed/ labels.",
        "Enrolled in NCT04368728 in Texas; Pfizer sponsors it.",
        "58 y/o with CKD in the United States.",
    ],
)
def test_clinical_text_survives(text):
    out, findings = phi.redact_text(text)
    assert out == text, findings


def test_redaction_keeps_the_label():
    out, _ = phi.redact_text("MRN MRN-AX-10442, member ID: XJH4452109")
    assert out == "MRN [REDACTED:mrn], member ID: [REDACTED:health_plan_id]"


def test_ner_can_be_turned_off(monkeypatch):
    monkeypatch.setenv("AXON_PHI_NER", "off")
    out, _ = phi.redact_text("Wei Chen reports nausea.")
    assert "Wei Chen" in out  # patterns alone do not know bare names


def _cross(payload):
    return GatekeeperRequest(
        source_subsidiary="clinical_research",
        target_subsidiary="pharma",
        subject="axon.clinical_research.pharma.research.query",
        payload=payload,
    )


def test_tier1_redacts_a_name_that_the_old_rules_missed():
    verdict = tier1_policy.evaluate(
        _cross({"question": "John Smith, 42 Oak Street, has hepatic impairment. Tylenol dose?"})
    )
    assert verdict.decision is Decision.REDACT
    forwarded = verdict.redacted_payload["question"]
    assert "John Smith" not in forwarded and "42 Oak Street" not in forwarded
    assert "hepatic impairment" in forwarded and "Tylenol" in forwarded
    assert "phi.ner.name" in verdict.matched_rules


def test_tier1_redacts_phi_named_fields_at_any_depth():
    verdict = tier1_policy.evaluate(
        _cross({"case": {"patient": {"first_name": "Ana", "dob": "1950-01-02"}, "drug": "warfarin"}})
    )
    assert verdict.decision is Decision.REDACT
    patient = verdict.redacted_payload["case"]["patient"]
    assert patient == {"first_name": "[REDACTED]", "dob": "[REDACTED]"}
    assert verdict.redacted_payload["case"]["drug"] == "warfarin"


def test_tier1_coaches_when_the_name_detector_is_missing(monkeypatch):
    def unavailable():
        raise phi.DetectorUnavailable("spaCy model not installed")

    monkeypatch.setenv("AXON_PHI_NER", "spacy")
    monkeypatch.setattr(phi, "_nlp", unavailable)
    verdict = tier1_policy.evaluate(_cross({"question": "Wei Chen, metformin dose?"}))
    assert verdict.decision is Decision.COACH
    assert "phi.detector_unavailable" in verdict.matched_rules


def test_egress_block_still_wins_over_redaction():
    verdict = tier1_policy.evaluate(
        _cross({"email_to": "someone@gmail.com", "body": "Wei Chen, MRN MRN-AX-10442"})
    )
    assert verdict.decision is Decision.BLOCK


# Floors for the evaluation sets, just under the scores measured when the
# milestone landed (docs/milestones/03-safe-harbor-phi.md). Raise them when the
# detector improves; a drop means a regression. The detector was tuned on
# "generated" and "handwritten". "holdout" was scored once, untuned: fixing its
# misses makes it a tuning set, so write a fresh holdout when that happens.
FLOORS = {
    "generated": {"recall": 1.0, "damage_rate": 0.0},
    "handwritten": {"recall": 0.96, "damage_rate": 0.0},
    "holdout": {"recall": 0.82, "damage_rate": 0.02},
}


@pytest.mark.parametrize("name", list(FLOORS))
def test_eval_set_does_not_regress(name):
    cases = phi_eval.load(name)
    if not cases:
        pytest.skip(f"evals/phi/{phi_eval.SETS[name]} not present")
    result = phi_eval.score(cases)
    assert result["recall"] >= FLOORS[name]["recall"], result["misses"]
    assert result["damage_rate"] <= FLOORS[name]["damage_rate"], result["damage"]
