"""Generate the templated half of the PHI evaluation set.

    uv run python evals/phi/generate.py      # rewrites evals/phi/generated.jsonl

Seeded, so the output is the same on every run. Each case is a clinical
message with identifiers dropped into it. ``phi`` lists what must be removed;
``keep`` lists clinical text that must come through unchanged. All values are
invented: 555 phone numbers, example.com addresses, made-up IDs.

These templates were written alongside the detector, so they measure breadth
more than difficulty. ``handwritten.jsonl`` is the held-out set, written
without sight of the detector.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

OUT = Path(__file__).with_name("generated.jsonl")

FIRST = ["Maria", "Chinedu", "Wei", "Aisha", "Tomasz", "Priya", "Diego", "Hana", "Olusegun",
         "Ingrid", "Rahul", "Fatima", "Kenji", "Siobhan", "Mateo", "Leilani", "Dmitri", "Amara"]
LAST = ["Gonzalez", "Okafor", "Chen", "Rahman", "Kowalski", "Natarajan", "Herrera", "Sato",
        "Adeyemi", "Lindqvist", "Mehta", "Haddad", "Takahashi", "Brennan", "Ruiz", "Kahale",
        "Volkov", "Nwosu"]
STREETS = ["Oak Street", "Maple Ave", "Harbor View Rd", "Lincoln Blvd", "Cedar Lane",
           "Sunset Drive", "Birchwood Ct", "Elm St"]
CITIES = [("Springfield", "IL"), ("Boise", "ID"), ("Tacoma", "WA"), ("Dayton", "OH"),
          ("Macon", "GA"), ("Fresno", "CA"), ("Provo", "UT"), ("Albany", "NY")]
MONTHS = ["January", "February", "March", "April", "June", "July", "August", "September",
          "October", "November", "December"]

CLINICAL = [
    ("acetaminophen", "hepatic impairment", "Max 2 g/day"),
    ("warfarin", "atrial fibrillation", "INR 2.5"),
    ("metformin", "type 2 diabetes", "eGFR 42"),
    ("apixaban", "DVT", "5 mg twice daily"),
    ("lisinopril", "hypertension", "BP 142/90"),
    ("vancomycin", "MRSA bacteremia", "trough 15-20"),
    ("levothyroxine", "hypothyroidism", "TSH 6.2"),
    ("pembrolizumab", "Hodgkin lymphoma", "200 mg q3w"),
    ("carbidopa-levodopa", "Parkinson's disease", "25/100 tid"),
    ("allopurinol", "gout", "Stevens-Johnson syndrome"),
]


def _rng_id(rng: random.Random, n: int, alpha: str = "") -> str:
    chars = "0123456789" + alpha
    return "".join(rng.choice(chars) for _ in range(n))


def _phone(rng: random.Random) -> str:
    a, b = f"555-{rng.randint(100, 999)}", rng.randint(1000, 9999)
    return rng.choice([f"({a[:3]}) {a[4:]}-{b}", f"{a}-{b}", f"{a.replace('-', '.')}.{b}"])


def _date(rng: random.Random) -> str:
    m, d, y = rng.randint(1, 12), rng.randint(1, 28), rng.randint(1940, 2026)
    return rng.choice([
        f"{m:02d}/{d:02d}/{y}", f"{y}-{m:02d}-{d:02d}", f"{MONTHS[rng.randrange(11)]} {d}, {y}",
        f"{d} {MONTHS[rng.randrange(11)]} {y}", f"{m}/{d}/{str(y)[2:]}",
    ])


def _identifier(rng: random.Random) -> tuple[str, str, str]:
    """Return (kind, sentence-with-{v}, value) for one identifier."""
    first, last = rng.choice(FIRST), rng.choice(LAST)
    city, state = rng.choice(CITIES)
    choices = [
        ("name", "Pt {v} presents with", f"{first} {last}"),
        ("name", "Mrs. {v} asked about", last),
        ("name", "{v}, 58 y/o, presents with", f"{first} {last}"),
        ("name", "Daughter {v} reports the patient has", first),
        ("address", "Lives at {v}, managing", f"{rng.randint(10, 9999)} {rng.choice(STREETS)}"),
        ("address", "Resident of {v}, " + state + ", with", city),
        ("zip", "Home ZIP {v}; history of", _rng_id(rng, 5)),
        ("date", "Admitted {v} for", _date(rng)),
        ("date", "DOB {v}, history of", _date(rng)),
        ("age_over_89", "{v} y/o with", str(rng.randint(90, 104))),
        ("age_over_89", "Aged {v}, frail, with", str(rng.randint(90, 104))),
        ("phone", "Call back at {v} re:", _phone(rng)),
        ("fax", "Fax records to {v}; pt has", _phone(rng)),
        ("email", "Portal msg from {v} about", f"{first.lower()}.{last.lower()}@example.com"),
        ("ssn", "SSN {v} on file; managing", f"{_rng_id(rng, 3)}-{_rng_id(rng, 2)}-{_rng_id(rng, 4)}"),
        ("mrn", "MRN {v}, admitted with", f"MRN-{_rng_id(rng, 7)}"),
        ("mrn", "Medical record no. {v}; dx", _rng_id(rng, 8)),
        ("health_plan_id", "Member ID {v}, coverage for", f"XJH{_rng_id(rng, 7)}"),
        ("health_plan_id", "Policy number: {v}; prior auth for", f"PL-{_rng_id(rng, 6)}"),
        ("account_number", "Acct # {v} flagged; managing", _rng_id(rng, 9)),
        ("license_number", "Driver's license no. {v} scanned at intake; managing", f"D{_rng_id(rng, 7)}"),
        ("vehicle_id", "Pt's vehicle VIN {v} noted in MVA report; managing",
         "1HGCM" + _rng_id(rng, 12, "ABCDEFGHJKLMNPRSTUVWXYZ")),
        ("device_id", "Pacemaker serial no. {v}; managing", f"PM-{_rng_id(rng, 6)}"),
        ("device_id", "Insulin pump S/N {v}; managing", _rng_id(rng, 10, "ABCDEF")),
        ("url", "Photos uploaded to {v} for", f"https://portal.example.com/u/{_rng_id(rng, 5)}"),
        ("ip_address", "Telehealth login from {v}; managing",
         f"{rng.randint(11, 223)}.{rng.randint(0, 255)}.{rng.randint(0, 255)}.{rng.randint(1, 254)}"),
        ("biometric", "Fingerprint hash: {v} matched; managing", _rng_id(rng, 16, "abcdef")),
        ("photo", "Wound photo data:image/png;base64,{v} attached; managing",
         "iVBORw0KGgo" + _rng_id(rng, 20, "ABCDEFabcdef")),
        ("patient_id", "Patient ID {v}, known", _rng_id(rng, 6)),
        ("other_id", "Claim #: {v} denied for", f"CLM{_rng_id(rng, 8)}"),
        ("other_id", "Specimen ID: {v} positive; managing", f"SP-{_rng_id(rng, 7)}"),
    ]
    return rng.choice(choices)


def _positive(rng: random.Random, n: int) -> dict:
    drug, condition, detail = rng.choice(CLINICAL)
    phi, parts = [], []
    for _ in range(rng.choice([1, 1, 2, 3])):
        kind, sentence, value = _identifier(rng)
        if kind == "photo":
            value_in_text = value
            parts.append(sentence.replace("{v}", value_in_text) + f" {condition}.")
            phi.append({"kind": kind, "text": "data:image/png;base64," + value})
            continue
        parts.append(sentence.replace("{v}", value) + f" {condition}.")
        phi.append({"kind": kind, "text": value})
    parts.append(f"Question on {drug}: {detail}?")
    return {
        "id": f"gen-{n:03d}",
        "text": " ".join(parts),
        "phi": phi,
        "keep": [drug, condition, detail],
        "note": "templated: " + ", ".join(p["kind"] for p in phi),
    }


NEGATIVES = [
    "Max 3 g/day of acetaminophen in hepatic impairment; avoid with daily alcohol use.",
    "Child-Pugh B cirrhosis: reduce the dose by 50% and monitor LFTs weekly.",
    "58 y/o with Hodgkin lymphoma, s/p 4 cycles ABVD, since 2019. Eligible for pembrolizumab?",
    "Hx Parkinson's disease on carbidopa-levodopa 25/100 tid; new orthostatic hypotension.",
    "Allopurinol started 2024; rash concerning for Stevens-Johnson syndrome. Stop and refer?",
    "Wilson's disease on penicillamine 250 mg qid. Is zinc acetate a reasonable switch?",
    "GCS 14 on arrival (Glasgow Coma Scale). Hold sedation until reassessed.",
    "Tylenol 500 mg q6h prn, Eliquis 5 mg bid, Keytruda 200 mg q3w per protocol.",
    "Plt 150000, INR 2.5, eGFR 42, BP 128/82. Is enoxaparin still appropriate?",
    "Dosing plan 500mg bid for 7 days; 1/2 tab if eGFR under 30.",
    "Label at https://dailymed.nlm.nih.gov/dailymed/ and https://www.fda.gov/drugs say max 4 g/day.",
    "Enrolled in NCT04368728 in Texas; Pfizer sponsors the extension study.",
    "Patient reports nausea after starting metformin 1000 mg daily; A1c 8.1.",
    "Cushing syndrome workup: 24-hour urine cortisol elevated twice.",
    "Warfarin with fluconazole raises INR; check INR in 3 days.",
    "Guillain-Barre syndrome after infection; IVIG 0.4 g/kg/day for 5 days.",
    "Graves disease on methimazole 10 mg daily; TSH suppressed, free T4 normal.",
    "Crohn disease flare; budesonide 9 mg daily for 8 weeks then taper.",
    "Seen in the US and Canada; trial sites in New York and California.",
    "Vancomycin trough 15-20 for MRSA bacteremia; renal dosing per pharmacy.",
]


def main() -> None:
    rng = random.Random(20260930)
    cases = [_positive(rng, i) for i in range(1, 181)]
    for i, text in enumerate(NEGATIVES, start=1):
        cases.append({"id": f"gen-neg-{i:02d}", "text": text, "phi": [], "keep": [text],
                      "note": "templated negative: the whole message must survive"})
    OUT.write_text("".join(json.dumps(c) + "\n" for c in cases))
    print(f"wrote {len(cases)} cases to {OUT}")


if __name__ == "__main__":
    main()
