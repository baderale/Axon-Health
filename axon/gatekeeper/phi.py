"""PHI detection for Tier-1: the 18 HIPAA Safe Harbor identifiers.

Two detectors feed one list of findings:

  - **Patterns** (always on): regular expressions for identifiers that have a
    shape (SSN, phone, dates, IP addresses, VINs) or a label ("MRN", "member
    ID", "serial no."). Labelled patterns redact only the value, so the
    forwarded text still says what kind of thing was removed.
  - **Names and places** (spaCy NER, ``en_core_web_sm``): people, cities and
    other sub-state places, which have no fixed shape. Honorific and
    relationship patterns ("Mr. Okafor", "daughter Lisa") back it up.

``AXON_PHI_NER=off`` turns the NER detector off (patterns only). If it is on
and the model cannot be loaded, :func:`find_phi` raises
:class:`DetectorUnavailable` and Tier-1 fails safe to coach, the same rule
the judges follow.

Kinds, numbered as in 45 CFR 164.514(b)(2)(i) and ``seed_data/hipaa_rules``:

   1 name              7 ssn                13 device_id
   2 address / zip     8 mrn                14 url
   3 date / age_over_89  9 health_plan_id  15 ip_address
   4 phone            10 account_number     16 biometric
   5 fax              11 license_number     17 photo
   6 email            12 vehicle_id         18 other_id (incl. patient_id)
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from functools import lru_cache

import structlog

log = structlog.get_logger(__name__)


@dataclass(frozen=True)
class Finding:
    kind: str
    start: int
    end: int
    text: str
    detector: str  # "pattern" or "ner"


class DetectorUnavailable(RuntimeError):
    """The NER detector is enabled but its model could not be loaded."""


# --- building blocks --------------------------------------------------------

# A value in a labelled identifier: 4+ characters, at least one digit, so
# "account for renal function" or "MRN pending" do not match.
_ID_VALUE = r"(?P<v>(?=[A-Za-z0-9-]*\d)[A-Za-z0-9][A-Za-z0-9-]{3,})"
# After an unambiguous label (MRN, SSN, DEA): "MRN 123", "MRN #123", "MRN: 123".
_LABEL_TAIL = r"\b\.?(?:\s*(?:number|num|no\.?|#))?\s*[:#=]?\s*"
# After a label that is also an ordinary word (plan, account, device): the
# value must follow "ID", "number", "#" or a colon. "dosing plan 500mg" stays.
_STRICT_TAIL = r"\b\.?(?:\s*(?:id|identifier|number|num|no\.?|#)\s*[:#=]?|\s*(?:#\s*:?|[:=]))\s*"

_US_STATES = (  # noqa: SIM905 (a word list reads better as one string)
    "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH "
    "NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC PR"
).split()
_STATE_ALT = "|".join(_US_STATES)

_MONTH = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?"
    r"|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?"
)
_STREET_SUFFIX = (
    r"(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Way|Place|Pl"
    r"|Terrace|Ter|Circle|Cir|Parkway|Pkwy|Highway|Hwy|Square|Sq|Trail|Trl|Loop)\b\.?"
)
# A capitalised word, accents included ("Yıldız", "Núñez").
_CAP_WORD = r"[A-ZÀ-ÖØ-Þ][a-zß-öø-ÿĀ-ž'’-]+"
_PHONE = r"(?:\+?1[\s.-]?)?(?:\(\d{3}\)\s?|\b\d{3}[\s.-]?)\d{3}[\s.-]?\d{4}\b"

# Order matters only for ties: at the same start, the longer match wins, then
# the earlier pattern.
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # 18: the platform's own patient identifier.
    ("patient_id", re.compile(r"(?i)\bpatient[\s_-]?id\b\s*[:#=]?\s*(?P<v>\d{3,})")),
    ("patient_id", re.compile(r"(?i)\b(?:patient|pt)\.?[\s_-]*(?:id\b|#|no\.|number\b)\s*[:#=]?\s*(?P<v>\d{3,})")),
    # 8
    ("mrn", re.compile(r"(?i)\b(?:MRN|med(?:ical)?\.?\s*rec(?:ord)?)" + _LABEL_TAIL + _ID_VALUE)),
    # 7
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    (
        "ssn",
        re.compile(
            r"(?i)\b(?:SSN?|social security)" + _LABEL_TAIL + r"(?P<v>\d{9}|\d{3}[\s-]\d{2}[\s-]\d{4})\b"
        ),
    ),
    # 9
    (
        "health_plan_id",
        re.compile(
            r"(?i)\b(?:member|subscriber|policy|beneficiary|insurance|health plan|group|plan)"
            + _STRICT_TAIL
            + _ID_VALUE
        ),
    ),
    # Medicare Beneficiary Identifier: 11 characters with a fixed letter/digit layout.
    ("health_plan_id", re.compile(r"\b[1-9][A-Z][A-Z0-9]\d[A-Z][A-Z0-9]\d[A-Z]{2}\d{2}\b")),
    # 10
    ("health_plan_id", re.compile(r"(?i)\b(?:medicare|medicaid|MBI)" + _LABEL_TAIL + _ID_VALUE)),
    # 10
    ("account_number", re.compile(r"(?i)\b(?:account|acct)" + _LABEL_TAIL + _ID_VALUE)),
    ("account_number", re.compile(r"(?i)\bbilling" + _STRICT_TAIL + _ID_VALUE)),
    # 11
    (
        "license_number",
        re.compile(
            r"(?:(?i:\b(?:driver'?s licen[cs]e|licen[cs]e|certificate|cert))" + _STRICT_TAIL
            + r"|(?:(?i:\b(?:DEA|NPI|driver'?s?\s+lic(?:en[cs]e)?|lic))|\bDL)" + _LABEL_TAIL + r")"
            + _ID_VALUE
        ),
    ),
    # 12
    ("vehicle_id", re.compile(r"\b(?=[A-HJ-NPR-Z0-9]*\d)(?=[A-HJ-NPR-Z0-9]*[A-HJ-NPR-Z])[A-HJ-NPR-Z0-9]{17}\b")),
    (
        "vehicle_id",
        re.compile(r"(?i)\b(?:licen[cs]e plate|plate|tag|VIN)" + _STRICT_TAIL + r"(?P<v>(?=[A-Za-z0-9-]*\d)[A-Za-z0-9-]{2,17})\b"),
    ),
    # "plate 7XKR219": capitals and digits together, so "plate 2" is not one.
    (
        "vehicle_id",
        re.compile(r"(?i:\b(?:licen[cs]e plate|plate))" + _LABEL_TAIL + r"(?P<v>(?=[A-Z0-9-]*\d)(?=[A-Z0-9-]*[A-Z])[A-Z0-9-]{5,8})\b"),
    ),
    # 13
    (
        "device_id",
        re.compile(
            r"(?i)\b(?:(?:device|implant|sensor|pump|transmitter|pacemaker|monitor|generator)" + _STRICT_TAIL
            + r"|(?:serial|s/n|SN|UDI|IMEI)" + _LABEL_TAIL + r")"
            + _ID_VALUE
        ),
    ),
    ("device_id", re.compile(r"\(01\)\d{14}(?:\(\d{2}\)[A-Za-z0-9]+)*")),  # GS1 UDI
    # 5 before 4, so a labelled fax number is not reported as a phone.
    ("fax", re.compile(r"(?i)\bfax(?:ed)?\b(?:\s+[a-z]+){0,3}?" + _LABEL_TAIL + r"(?P<v>" + _PHONE + r")")),
    ("phone", re.compile(_PHONE)),
    # 6
    ("email", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    # 14 (public references are let through in _keep)
    ("url", re.compile(r"(?i)\b(?:https?://|www\.)[^\s\"'<>)\]]*[^\s\"'<>)\].,;:!?]")),
    # 15
    ("ip_address", re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\b")),
    ("ip_address", re.compile(r"(?i)\b(?:[0-9a-f]{1,4}:){7}[0-9a-f]{1,4}\b|\b(?:[0-9a-f]{1,4}:){1,6}:[0-9a-f]{1,4}\b")),
    # 3: every date element except the year, and ages over 89.
    ("date", re.compile(r"\b(?:19|20)\d{2}-\d{1,2}-\d{1,2}\b")),
    ("date", re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-](?:\d{4}|\d{2})\b")),
    ("date", re.compile(r"\b" + _MONTH + r"\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?\b")),
    ("date", re.compile(r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?" + _MONTH + r"(?:,?\s+\d{4})?\b")),
    ("date", re.compile(r"\b" + _MONTH + r",?\s+(?:19|20)\d{2}\b")),
    ("date", re.compile(r"\b\d{1,2}\.\d{1,2}\.(?:\d{4}|\d{2})\b")),  # 23.07.1958
    ("date", re.compile(r"\b\d{1,2}[-/](?i:" + _MONTH + r")[-/](?:\d{4}|\d{2})\b")),  # 04-Jun-2025
    # A month/day with no year only after a word that marks it as a date, so
    # "1/2 tab" and "3/4 strength" stay.
    (
        "date",
        re.compile(
            r"(?i:\b(?:on|d/c'?d|dc'?d|discharged|admitted|adm|seen|since|until|til|through|thru"
            r"|from|f/u|dos|dob|visit(?:ed)?|dated?|born|died|expired|surgery|procedure))\s+"
            r"(?P<v>(?:0?[1-9]|1[0-2])/(?:0?[1-9]|[12]\d|3[01]))\b(?!\s*(?:tabs?|mg|mcg|dose|strength|of))"
        ),
    ),
    (
        "age_over_89",
        re.compile(r"(?i)\b(?P<v>9\d|1[0-4]\d)(?:\s*|-)(?:years?|yrs?|y/?o\b|yo\b)(?:[\s-]*old)?"),
    ),
    ("age_over_89", re.compile(r"(?i)\bage[d]?\s*[:=]?\s*(?P<v>9\d|1[0-4]\d)\b")),
    (
        "age_over_89",
        re.compile(
            r"(?i)\b(?P<v>(?:ninety|one hundred)(?:[\s-](?:and[\s-])?(?:one|two|three|four|five|six|seven|eight|nine))?)"
            r"[\s-]+(?:years?|yrs?|y/?o\b)"
        ),
    ),
    # 2: street addresses, PO boxes, ZIP codes, "City, ST".
    (
        "address",
        re.compile(
            r"\b\d{1,6}\s+(?:[NSEW]\.?\s+)?(?:" + _CAP_WORD + r"\s+){0,3}" + _CAP_WORD + r"\s+" + _STREET_SUFFIX
            + r"(?:,?\s*(?:Apt|Apartment|Unit|Suite|Ste|#)\.?\s*[A-Za-z0-9-]+)?"
        ),
    ),
    ("address", re.compile(r"(?i)\bP\.?\s?O\.?\s*Box\s+\d+\b")),
    ("zip", re.compile(r"(?i)\bzip(?:\s*code)?\s*[:#]?\s*(?P<v>\d{5}(?:-\d{4})?)\b")),
    ("zip", re.compile(r"\b(?:" + _STATE_ALT + r")\s+(?P<v>\d{5}(?:-\d{4})?)\b")),
    ("address", re.compile(r"(?P<v>\b" + _CAP_WORD + r"(?:\s" + _CAP_WORD + r")?),\s*(?:" + _STATE_ALT + r")\b")),
    # "Flagstaff AZ 86001": no comma, but the ZIP makes it an address.
    ("address", re.compile(r"(?P<v>\b" + _CAP_WORD + r"(?:\s" + _CAP_WORD + r")?)\s+(?:" + _STATE_ALT + r")\s+\d{5}\b")),
    # 16
    (
        "biometric",
        re.compile(
            r"(?i)\b(?:fingerprint|voiceprint|voice print|retina(?:l)? scan|iris scan|faceprint"
            r"|biometric)s?(?:\s*(?:hash|template|id|data|code))?\s*[:=#]?\s*(?P<v>(?=[^\s,;]*\d)[^\s,;]{4,})"
        ),
    ),
    # 17
    ("photo", re.compile(r"data:image/[a-z+]+;base64,[A-Za-z0-9+/=]+")),
    ("photo", re.compile(r"(?i)\b[\w-]+(?:\.[\w-]+)*\.(?:jpe?g|png|heic|gif|bmp|tiff?|webp|dcm)\b")),
    # 1: honorifics and family members; spaCy covers bare names.
    (
        "name",
        re.compile(r"\b(?:Mr|Mrs|Ms|Mx|Miss|Dr|Prof)\.?\s+(?P<v>" + _CAP_WORD + r"(?:\s+" + _CAP_WORD + r"){0,2})"),
    ),
    (
        "name",
        re.compile(
            r"(?i:\b(?:patient|pt|name|daughter|son|wife|husband|spouse|mother|father|sister"
            r"|brother|guardian|caregiver|named))\s*[:,-]?\s+(?P<v>" + _CAP_WORD + r"(?:\s+" + _CAP_WORD + r"){0,2})"
        ),
    ),
    # "PT: GARCIA-LOPEZ, MARIA J.": after a colon label, capitals and "LAST, First" too.
    (
        "name",
        re.compile(
            r"(?i:\b(?:patient|pt|name|patient name|pt name))\s*:\s*"
            r"(?P<v>[A-ZÀ-Þ][A-Za-zÀ-ÿ'’-]+(?:,?\s+[A-ZÀ-Þ][A-Za-zÀ-ÿ'’-]+){0,2}(?:\s+[A-Z]\.)?)"
        ),
    ),
    # 18: any other labelled identifier, and bare numbers too long to be a dose.
    (
        "other_id",
        re.compile(
            r"(?i)\b(?:id|identifier|case|encounter|visit|claim|record|accession|specimen|subject"
            r"|study id|barcode|badge|passport|visa|employee|student)\b(?:\s*(?:number|num|no\.?|id))?\s*(?:#\s*:?|[:=])\s*" + _ID_VALUE
        ),
    ),
    ("other_id", re.compile(r"(?i)\b(?:badge|passport|visa)" + _LABEL_TAIL + _ID_VALUE)),
    ("other_id", re.compile(r"\b\d{8,}\b")),
]

# Public reference sites are not identifiers of an individual; citing a drug
# label must survive the reply leg.
PUBLIC_URL_DOMAINS = (
    "nih.gov", "fda.gov", "cdc.gov", "cms.gov", "hhs.gov", "who.int", "clinicaltrials.gov",
    "axonhealth.internal", "axonhealth.local",
)

# Words the NER model mistakes for people in clinical text: eponyms
# ("Hodgkin lymphoma"), dosing words ("Max 2 g/day") and drug names.
_NOT_A_NAME = {
    w.lower()
    for w in (  # noqa: SIM905
        "Addison Alzheimer Apgar Asperger Barr Behcet Bell Brugada Burkitt Child Crohn Cushing "
        "Down Epstein Ewing Fabry Gaucher Gehrig Glasgow Graves Guillain Barre Hashimoto "
        "Horner Huntington Johnson Kaposi Kawasaki Korsakoff Marfan Meniere Paget Parkinson "
        "Pompe Pugh Raynaud Reye Sachs Sjogren Stevens Tay Tourette Wernicke Whipple Wilms "
        "Wilson Wolff Max Min Dose Tylenol Advil Motrin Aleve Coumadin Eliquis Xarelto "
        "Lipitor Zocor Glucophage Lasix Norvasc Synthroid Ozempic Wegovy Mounjaro Humira "
        "Keytruda Narcan Benadryl Zyrtec Claritin Prilosec Nexium Zoloft Prozac Lexapro "
        "Xanax Valium Ativan Ambien Adderall Ritalin Vicodin Percocet Oxycontin Lyrica "
        "Neurontin Plavix Brilinta Entresto Jardiance Farxiga Januvia Lantus Humalog Novolog "
        "Acetaminophen Ibuprofen Warfarin Metformin Lisinopril Patient Pt "
        "Paxlovid Lagevrio Veklury Tamiflu Xofluza Biktarvy Descovy Truvada Genvoya Epclusa "
        "Harvoni Mavyret Suboxone Sublocade Vivitrol Dupixent Stelara Skyrizi Rinvoq Enbrel "
        "Remicade Ocrevus Opdivo Tagrisso Ibrance Revlimid Imbruvica Xtandi Trulicity Rybelsus "
        "Victoza Toujeo Tresiba Basaglar Levemir Spiriva Symbicort Advair Breo Trelegy Singulair "
        "Flonase Augmentin Keflex Cipro Levaquin Bactrim Zithromax Flagyl Diflucan Valtrex "
        "Depakote Lamictal Keppra Topamax Tegretol Seroquel Abilify Risperdal Zyprexa Latuda "
        "Wellbutrin Effexor Cymbalta Pristiq Trintellix Buspar Klonopin Restoril Lunesta "
        "Toradol Ultram Dilaudid Norco Mobic Celebrex Medrol Decadron Prednisone Imuran "
        "Cellcept Prograf Rapamune Zofran Reglan Protonix Pepcid Carafate Colace Miralax "
        "Aldactone Coreg Toprol Lopressor Tenormin Cozaar Diovan Benicar Cardizem Lanoxin "
        "Multaq Pradaxa Savaysa Lovenox Heparin Repatha Praluent Zetia Crestor Pravachol "
        "Pfizer Merck Moderna Novartis Roche Genentech AstraZeneca Sanofi GSK Lilly AbbVie "
        "Amgen Gilead Bayer Janssen Takeda Biogen Regeneron Teva Novo Nordisk Squibb Bristol "
        "Medtronic Abbott Dexcom Boston Scientific Baxter Stryker "
        "Hx Dx Rx Sx Tx Fx Pmh Hpi Ros Cc Plt Hgb Hct Wbc Anc Inr Bun Cr Na Mg Ast Alt Ldl Hdl "
        "Tsh A1c Bid Tid Qid Qhs Qd Prn Po Iv Im Sq Sc Sl Pr Npo Etoh Xr Er Sr Xl Cr La Odt Ir "
        "Dob Dos Mrn Ssn Icu Ed Er Or Pacu Snf Ltc Cbc Bmp Cmp Lft Lfts Ecg Ekg Mri Ct Cxr "
        "Pod Abx Cabg Pci Copd Chf Ckd Esrd Afib Dvt Pe Uti Gerd Htn Dm Cad Mi Tia Cva"
    ).split()
}
_EPONYM_TAIL = re.compile(r"(?i)^['’]?s?\s+(?:disease|syndrome|lymphoma|sarcoma|palsy|sign|criteria|score|scale|test|classification)")

# Places at state level or above may stay (Safe Harbor removes only smaller units).
_ALLOWED_PLACES = {
    s.lower()
    for s in (  # noqa: SIM905
        "Alabama Alaska Arizona Arkansas California Colorado Connecticut Delaware Florida Georgia "
        "Hawaii Idaho Illinois Indiana Iowa Kansas Kentucky Louisiana Maine Maryland "
        "Massachusetts Michigan Minnesota Mississippi Missouri Montana Nebraska Nevada Ohio "
        "Oklahoma Oregon Pennsylvania Tennessee Texas Utah Vermont Virginia Washington "
        "Wisconsin Wyoming US USA U.S. U.S.A. America Canada Mexico Europe EU UK Asia Africa "
        # Countries, and Canadian provinces (the equivalent of a state).
        "Afghanistan Albania Algeria Argentina Armenia Australia Austria Bangladesh Belarus "
        "Belgium Bolivia Bosnia Brazil Bulgaria Cambodia Cameroon Chile China Colombia Congo "
        "Croatia Cuba Cyprus Czechia Denmark Ecuador Egypt England Eritrea Estonia Ethiopia "
        "Finland France Germany Ghana Greece Guatemala Haiti Honduras Hungary Iceland India "
        "Indonesia Iran Iraq Ireland Israel Italy Jamaica Japan Jordan Kazakhstan Kenya Korea "
        "Kuwait Laos Latvia Lebanon Liberia Libya Lithuania Malaysia Mali Morocco Myanmar Nepal "
        "Netherlands Nicaragua Niger Nigeria Norway Pakistan Panama Paraguay Peru Philippines "
        "Poland Portugal Qatar Romania Russia Rwanda Scotland Senegal Serbia Singapore Slovakia "
        "Somalia Spain Sudan Sweden Switzerland Syria Taiwan Tanzania Thailand Tunisia Turkey "
        "Uganda Ukraine Uruguay Uzbekistan Venezuela Vietnam Wales Yemen Zambia Zimbabwe "
        "Alberta Manitoba Ontario Quebec Saskatchewan Nunavut Yukon"
    ).split()
} | {
    "new hampshire", "new jersey", "new mexico", "new york", "north carolina", "north dakota",
    "rhode island", "south carolina", "south dakota", "west virginia", "united states",
    "the united states", "district of columbia", "puerto rico", "united kingdom",
    "south africa", "south korea", "north korea", "new zealand", "saudi arabia", "sri lanka",
    "el salvador", "costa rica", "dominican republic", "united arab emirates", "hong kong",
    "british columbia", "nova scotia", "new brunswick", "prince edward island",
    "newfoundland and labrador", "northwest territories", "latin america", "middle east",
} | {s.lower() for s in _US_STATES}

_NER_LABELS = {"PERSON": "name", "GPE": "address", "LOC": "address", "FAC": "address"}


# --- NER --------------------------------------------------------------------


def ner_enabled() -> bool:
    return os.environ.get("AXON_PHI_NER", "spacy").strip().lower() not in {"off", "0", "false", "no"}


@lru_cache(maxsize=1)
def _nlp():
    model = os.environ.get("AXON_PHI_NER_MODEL", "en_core_web_sm")
    try:
        import spacy

        return spacy.load(model, disable=["lemmatizer"])
    except Exception as exc:  # noqa: BLE001
        raise DetectorUnavailable(
            f"PHI name detector could not load spaCy model {model!r}: {exc}. "
            "Install the project dependencies, or set AXON_PHI_NER=off for patterns only."
        ) from exc


# Generic drug names share stems (INN suffixes), so drugs missing from the list
# above are still not taken for people or places.
_DRUG_STEM = re.compile(
    r"(?:mab|nib|vir|pril|sartan|olol|statin|azole|cillin|mycin|floxacin|prazole|tidine"
    r"|gliptin|gliflozin|glutide|parin|xaban|gatran|dipine|afil|triptan|setron|lukast|azepam"
    r"|zolam|oxetine|pramine|triptyline|profen|oxacin|cycline|sone|olone|terol|tropium"
    r"|thiazide|semide|dronate|lukast|platin|rubicin|taxel|tinib|ciclib|lisib|parib|zumab"
    r"|ximab|umab|cept|kinra|navir|buvir|asvir|tegravir|previr|citabine|fovir|amivir)$"
)


def _is_false_name(text: str, following: str) -> bool:
    words = re.split(r"[\s/-]+", text)
    tokens = [t.strip("'’.,:;").removesuffix("'s").removesuffix("’s").lower() for t in words]
    # Only words count: spaCy reads "Max 2 g/day" as a person called "Max 2".
    tokens = [t for t in tokens if any(c.isalpha() for c in t)]
    if all(t in _NOT_A_NAME or (len(t) > 6 and _DRUG_STEM.search(t)) for t in tokens):
        return True
    return bool(_EPONYM_TAIL.match(following))


def _is_abbreviation(value: str) -> bool:
    """Short all-capital words are abbreviations (ETOH, TAF, MRSA), not people or places."""
    return all(w.isupper() and len(w) <= 4 for w in re.findall(r"[^\W\d_]+", value))


_NAME_PARTICLES = {"de", "del", "della", "la", "le", "da", "di", "van", "von", "der", "den", "bin", "al", "el"}


def _name_part(value: str) -> str:
    """The leading run of name-shaped words: "Max 3 g/day" becomes "Max"."""
    words: list[str] = []
    for word in value.split():
        core = word.strip(",.;:")
        name_shaped = core[:1].isupper() and core.replace("'", "").replace("’", "").replace("-", "").isalpha()
        if name_shaped or core in _NAME_PARTICLES:
            words.append(word)
        else:
            break
    while words and words[-1] in _NAME_PARTICLES:
        words.pop()
    return " ".join(words).rstrip(",.;:")


def _ner_findings(text: str) -> list[Finding]:
    doc = _nlp()(text)
    out: list[Finding] = []
    for ent in doc.ents:
        kind = _NER_LABELS.get(ent.label_)
        if kind is None or "REDACTED" in ent.text:
            continue
        # spaCy sometimes swallows a leading "Patient" or "the" into the entity.
        start, value = ent.start_char, ent.text
        stripped = re.sub(r"(?i)^(?:the|patient|pt\.?)\s+", "", value)
        start += len(value) - len(stripped)
        value = stripped
        if not value or not value[0].isupper():
            continue
        if _is_abbreviation(value):
            continue
        if kind == "name":
            value = _name_part(value)
            if not value or _is_false_name(value, text[start + len(value) :]):
                continue
        # Places have no digits; spaCy tags trial IDs like NCT04368728 as places.
        if kind == "address" and (
            value.lower().strip(". ") in _ALLOWED_PLACES
            or any(c.isdigit() for c in value)
            or _is_false_name(value, "")
        ):
            continue
        out.append(Finding(kind, start, start + len(value), value, "ner"))
    return out


# --- public API -------------------------------------------------------------


def _keep(kind: str, value: str) -> bool:
    """True for matches that look like PHI but are not."""
    if kind == "url":
        host = re.sub(r"(?i)^(?:https?://)?(?:www\.)?", "", value).split("/")[0].split(":")[0].lower()
        return any(host == d or host.endswith("." + d) for d in PUBLIC_URL_DOMAINS)
    return kind == "address" and value.lower() in _ALLOWED_PLACES


def find_phi(text: str, *, use_ner: bool | None = None) -> list[Finding]:
    """Return non-overlapping PHI findings in ``text``, in order of position."""
    found: list[Finding] = []
    for kind, pattern in _PATTERNS:
        for m in pattern.finditer(text):
            group = "v" if "v" in pattern.groupindex and m.group("v") else 0
            start, end = m.span(group)
            value = text[start:end]
            if kind == "name" and (_is_false_name(value, text[end:]) or _is_abbreviation(value)):
                continue
            if not _keep(kind, value):
                found.append(Finding(kind, start, end, value, "pattern"))
    if ner_enabled() if use_ner is None else use_ner:
        found.extend(_ner_findings(text))

    # Earliest first; at the same start the longest; then patterns before NER.
    found.sort(key=lambda f: (f.start, -(f.end - f.start), f.detector != "pattern"))
    merged: list[Finding] = []
    for f in found:
        if merged and f.start < merged[-1].end:
            continue
        merged.append(f)
    return merged


def redact_text(text: str, *, use_ner: bool | None = None) -> tuple[str, list[Finding]]:
    """Replace each finding with ``[REDACTED:<kind>]``."""
    findings = find_phi(text, use_ner=use_ner)
    out = text
    for f in reversed(findings):
        out = f"{out[: f.start]}[REDACTED:{f.kind}]{out[f.end :]}"
    return out, findings


# Structured fields whose whole value is PHI, whatever it looks like.
FIELD_KINDS: dict[str, str] = {
    **dict.fromkeys(
        ["name", "patient_name", "full_name", "first_name", "last_name", "given_name",
         "family_name", "middle_name", "maiden_name", "next_of_kin", "emergency_contact"],
        "name",
    ),
    **dict.fromkeys(
        ["address", "street", "street_address", "address_line1", "address_line2", "city",
         "county", "home_address"],
        "address",
    ),
    **dict.fromkeys(["zip", "zip_code", "zipcode", "postal_code"], "zip"),
    **dict.fromkeys(
        ["dob", "date_of_birth", "birth_date", "birthdate", "admission_date", "admit_date",
         "discharge_date", "date_of_death", "death_date", "visit_date", "service_date"],
        "date",
    ),
    **dict.fromkeys(["phone", "phone_number", "mobile", "cell", "telephone", "home_phone"], "phone"),
    **dict.fromkeys(["fax", "fax_number"], "fax"),
    **dict.fromkeys(["email", "email_address"], "email"),
    **dict.fromkeys(["ssn", "social_security_number"], "ssn"),
    **dict.fromkeys(["mrn", "medical_record_number"], "mrn"),
    **dict.fromkeys(
        ["member_id", "insurance_id", "policy_number", "subscriber_id", "health_plan_id",
         "medicare_id", "medicaid_id", "beneficiary_id", "group_number"],
        "health_plan_id",
    ),
    **dict.fromkeys(["account_number", "account_id", "billing_account"], "account_number"),
    **dict.fromkeys(
        ["license_number", "drivers_license", "driver_license", "certificate_number"],
        "license_number",
    ),
    **dict.fromkeys(["vin", "license_plate", "vehicle_id"], "vehicle_id"),
    **dict.fromkeys(["device_id", "device_serial", "serial_number", "udi", "imei"], "device_id"),
    **dict.fromkeys(["ip", "ip_address"], "ip_address"),
    **dict.fromkeys(
        ["fingerprint", "voiceprint", "retina_scan", "iris_scan", "biometric", "biometrics"],
        "biometric",
    ),
    **dict.fromkeys(["photo", "photograph", "face_photo", "headshot", "face_image"], "photo"),
    **dict.fromkeys(["patient_id"], "patient_id"),
}


def field_kind(key: str) -> str | None:
    """The Safe Harbor kind for a field whose whole value is PHI, or None."""
    return FIELD_KINDS.get(key.strip().lower().replace("-", "_").replace(" ", "_"))
