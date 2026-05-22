# Minimum Necessary Standard — 45 CFR 164.502(b)

A covered entity must make reasonable efforts to limit PHI to the minimum
necessary to accomplish the intended purpose of the use, disclosure, or
request. This standard does not apply to:

  - Disclosures to or requests by a health care provider for treatment.
  - Uses or disclosures made to the individual.
  - Uses or disclosures made pursuant to an authorization.
  - Disclosures made to the Secretary of HHS.
  - Uses or disclosures that are required by law.
  - Uses or disclosures that are required for compliance with HIPAA.

Operational implications for the Axon Health gatekeeper:

  - When Clinical Research's Clinical SME consults Axon Pharma about a drug
    interaction, the Pharma Research department does not need the patient's
    identity, only the relevant clinical context (condition, medications,
    relevant lab values). REDACT identifiers.
  - When a department requests aggregated population analytics, never include
    individual identifiers. REDACT or BLOCK if redaction would defeat the
    request.
  - When the action is patient-facing (treating the individual), full PHI
    flow is permitted.
