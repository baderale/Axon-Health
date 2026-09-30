# Milestone 3: Tier-1 covers all 18 Safe Harbor identifiers, with a measured score

**Status:** done (2026-09-30)

## Goal

Make the gatekeeper's core claim true and measurable. Before this milestone,
Tier-1 knew six identifier shapes (patient ID, MRN, SSN, ISO dates, phone,
email) and no names at all: "John Smith, 42 Oak Street" passed Tier-1
untouched. A buyer's first question is "what share of patient data do you
catch?", and there was no way to answer it.

This milestone extends Tier-1 to the 18 HIPAA Safe Harbor identifiers
(45 CFR 164.514(b)(2), listed in `seed_data/hipaa_rules/01_phi_definition.md`)
and builds an evaluation that reports both what is caught and what clinical
text is damaged.

## What was built

| Piece | Where |
|---|---|
| Safe Harbor detector: labelled and shaped patterns for all 18 kinds, spaCy NER for names and places, clinical false-positive filters | `axon/gatekeeper/phi.py` |
| Tier-1 uses it; PHI-named fields are redacted at any depth; fails safe to coach if the name model is missing | `axon/gatekeeper/tier1_policy.py` |
| Evaluation tool: recall per kind, damage to clinical text, altered negatives | `axon/tools/phi_eval.py` |
| Three evaluation sets (380 synthetic cases) | `evals/phi/` |
| 51 unit tests, including per-kind cases and regression floors on each set | `tests/test_phi_detection.py` |
| `safe-harbor` scenario: a free-text note with a name, address, DOB and a relative | `axon/tools/fake_publisher.py` |
| Judge prompts say that a `[REDACTED:…]` marker is not PHI | `axon/model_registry/registry.py` |

### How detection works

- **Patterns** (always on) find identifiers with a shape (SSN, phone, dates,
  IPv4/IPv6, VIN, Medicare MBI, GS1 UDI, image filenames, base64 images) or a
  label ("MRN", "member ID", "acct #", "serial no.", "badge #", "passport
  no."). For labelled identifiers only the value is replaced, so the forwarded
  text reads `MRN [REDACTED:mrn]` and the judges can see what was removed.
  Labels that are also ordinary words (plan, account, device, billing) need
  "ID", "number", "#" or a colon before the value, so "dosing plan 500mg"
  survives.
- **Names and places** come from spaCy `en_core_web_sm` (12 MB, about 5 ms a
  message), backed by honorific, relationship and `Name:` patterns. `Mr.
  Okafor`, `daughter Lisa` and `PT: GARCIA-LOPEZ, MARIA` are caught without
  the model.
- **False-positive filters** keep clinical text intact. A list of about 330
  words covers eponyms ("Hodgkin lymphoma", "Child-Pugh", "Guillain-Barre"),
  drug brands, pharma companies and clinical abbreviations (Plt, XR, ETOH, PO).
  Generic-drug stems (-mab, -vir, -pril) catch drugs not on the list. Short
  all-capital words are never taken for names, and neither is dose text spaCy
  swallows into a name ("Max 3 g/day" read as a person). States,
  countries and Canadian provinces stay, as Safe Harbor allows. Public
  reference URLs (fda.gov, nih.gov, cdc.gov, cms.gov, who.int) stay, and so
  does the year of a date.
- **Fields** whose name marks them as PHI (`first_name`, `dob`, `address`,
  `member_id`, `device_serial` and about 80 others) are replaced whole,
  including inside nested objects. Before, only top-level fields were checked.
- **Fail safe.** If the spaCy model cannot load, Tier-1 returns `coach`
  (`phi.detector_unavailable`) and nothing crosses. `AXON_PHI_NER=off` runs
  on patterns only, and then bare names are not caught.

Matched rules now name the detector and kind (`phi.ner.name`,
`phi.pattern.date`, `phi.field.dob`), so the audit trail shows what was found
and how.

### The evaluation sets

| Set | Cases | Written by | Role |
|---|---|---|---|
| `generated.jsonl` | 200 (20 negatives) | `evals/phi/generate.py`, seeded templates written alongside the detector | Breadth: every kind in many formats |
| `handwritten.jsonl` | 80 (25 negatives) | A separate agent that never saw the detector | Tuning set: realistic, adversarial clinical notes |
| `holdout.jsonl` | 100 (30 negatives) | A second blind agent, written after tuning stopped | **The honest number.** Scored once, never tuned on |

Each case lists `phi` (values that must be removed) and `keep` (clinical text
that must survive verbatim). All data is synthetic. Provider names count as
PHI in the holdout, which is stricter than Safe Harbor needs.

## Results

`uv run python -m axon.tools.phi_eval`, same cases through each version of Tier-1:

| Set | Milestone-2 rules: recall | Milestone 3: recall | Milestone 3: clinical text damaged | Negatives altered |
|---|---|---|---|---|
| generated | 16.7% | 100.0% of 324 | 0.0% of 560 | 0 / 20 |
| handwritten | 17.2% | 96.6% of 87 | 0.0% of 216 | 0 / 25 |
| **holdout** | **17.6%** | **82.9% of 187** | **1.5% of 476** | **4 / 30** |

The milestone-2 rules caught no names at all. Damage was 0% before only
because they redacted almost nothing.

The holdout is the number to quote. The gap between 96.6% and 82.9% is what
tuning on a set does to its score.

**Holdout misses, by class**, which is the work list for the next iteration:

- Names in tabular text: CSV rows (`P-008812,Aisha Rahman,…`) with no label
  and no sentence around them. Four of the 11 missed names.
- Names after uncommon lead-ins: "seen by NP Carmen Reyes", "Case from J.P.
  Morales", "Re:" letter headers, "contact via neighbor Eli Yoder".
- Identifiers with labels not yet known: `Acc#`, `Rx#`, `Encounter`, `claim`
  without `#:`, `subject 104-0037`, `Incident ref`, `patient_id=HX29071`
  (letters in a patient ID).
- Dates: year-month (`07/1958`), `2026/07/22`, day-of-month alone ("the
  13th"), and `10/03` after "scheduled".
- `96 y.o.` (periods), phone extensions (`ext. 22`), UK postcodes, and
  plates written with a state (`plate CA 8QRT512`).

**Holdout damage:** spaCy tags diseases as places ("West Nile", "Ebola",
"Marburg") and some brands as names or places (Concerta, Zepbound, "Sanford
Guide"). The eval also counts a wound-photo filename as damage, because the
holdout's author ruled that a photo that does not show the face is not PHI.
The detector redacts every image filename.

## Acceptance criteria

| # | Criterion | Checked by |
|---|---|---|
| 1 | Every one of the 18 Safe Harbor kinds is detected in free text | `test_each_safe_harbor_kind_is_removed` (31 cases) |
| 2 | Names and street addresses in free text are redacted by Tier-1 | `test_tier1_redacts_a_name_that_the_old_rules_missed`, live run |
| 3 | Clinical text survives: eponyms, drugs, doses, labs, fractions, public URLs, years, states | `test_clinical_text_survives` (11 cases) |
| 4 | PHI-named fields are redacted inside nested objects | `test_tier1_redacts_phi_named_fields_at_any_depth` |
| 5 | A missing name model stops traffic (coach), not silently degrades | `test_tier1_coaches_when_the_name_detector_is_missing` |
| 6 | Recall and damage are measured on a set the detector was not tuned on | `holdout.jsonl`, table above |
| 7 | Scores cannot regress unnoticed | `test_eval_set_does_not_regress` (floors per set) |
| 8 | All pre-existing tests still pass | full suite: 88 passed |

### Live runs (2026-09-30, `llama3.1:8b`, Docker Desktop on macOS, CPU)

**1. The demo question, extended with a name, DOB, street address, city and
phone** (`ask`, conversation `d11186cc`). It was answered end to end in about
a minute. The Intake model had already restated the question without
identifiers, so the free-text PHI never reached the wire. The gatekeeper
redacted the patient ID and MRN fields as before, and Pharma's reply came back
undamaged ("500-1000 mg every 6 hours", "4 grams per day"):

```
tier1.redact                  axon.clinical_research.pharma.research.query
tier2.hipaa.redact            axon.clinical_research.pharma.research.query
tier2.compliance.allow        axon.clinical_research.pharma.research.query
interceptor.published.redact  axon.clinical_research.pharma.research.query
tier1.allow                   axon.pharma.clinical_research.research.reply
tier2.hipaa.allow             axon.pharma.clinical_research.research.reply
tier2.compliance.allow        axon.pharma.clinical_research.research.reply
interceptor.published.allow   axon.pharma.clinical_research.research.reply
```

**2. Free-text PHI straight through the gatekeeper**
(`fake-publisher safe-harbor`). Tier-1 caught every identifier:

```
in:  Maria Gonzalez, DOB 03/14/1968, of 42 Oak Street, Springfield, IL, 58 year old with
     hepatic impairment. Her daughter Ana Gonzalez asks: what is the safe dosing window ...
out: [REDACTED:name], DOB [REDACTED:date], of [REDACTED:address], [REDACTED:address], IL,
     58 year old with hepatic impairment. Her daughter [REDACTED:name] asks: ...
     matched: phi.ner.name, phi.pattern.date, phi.pattern.address, phi.pattern.name
```

The Tier-2 judges then stopped it: HIPAA `redact`, Compliance `coach` ("The
payload references a patient's protected health information… internal
scientific discussion or external promotional copy?"). It was coached 3 out of
3 times, including after the judge prompts were told that markers are not PHI.

## Finding: the 8B Compliance judge coaches any message that shows a redaction

The judges were called directly with three versions of the same message, two
runs each:

| Payload the judges saw | HIPAA | Compliance |
|---|---|---|
| Tier-1 output, `[REDACTED:name]` markers | redact, redact | **coach, coach** |
| Same, markers written `[name removed]` | redact, redact | **coach, coach** |
| Same clinical content, no trace of identifiers | allow, allow | allow, allow |

The detector is doing its job. The bottleneck for free-text PHI is now the 8B
judge: it reacts to the fact that something was removed, whatever the marker
says, and the prompt instruction did not change that. The ask flow is
unaffected today only because the Intake model restates the question without
identifiers first.

Options for the next milestone, cheapest first:
1. Measure the judges the way this milestone measured Tier-1: a labelled set
   of messages with the verdict each should get, scored per model.
2. Try a larger or instruction-tuned judge model through the Model Registry
   (a registry change only).
3. Show the judges the redaction as structured data (`"redactions": ["name",
   "date"]`) rather than inline markers.

The prompt line was kept. It is correct, and a larger judge model may follow
it; it made no difference with `llama3.1:8b`.

## Known limits, for later milestones

- The holdout misses above. Fixing them against `holdout.jsonl` would turn it
  into a tuning set, so write a fresh holdout at the same time.
- Lowercase names ("spoke w/ daughter priya raghunathan") are not caught.
  spaCy's small model relies on capitals, and a lowercase-name pattern would
  redact ordinary words.
- The drug and eponym lists are hand-written. A drug lexicon (RxNorm) would
  replace them.
- `en_core_web_sm` was chosen over `en_core_web_lg` (560 MB). On the sample
  text both found the same names with the same false positives. A clinical
  NER model is the next step if name recall matters more than image size.
- Full-face photographs and biometrics are only caught when the message
  carries a label, a filename or inline image data. Tier-1 does not inspect
  image content.
- Tier-1 now redacts provider names too ("Dr. Patel"). Safe Harbor does not
  require it, but inter-subsidiary queries do not need them.
