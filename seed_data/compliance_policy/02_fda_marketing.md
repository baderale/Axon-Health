# FDA Marketing & Promotion Restrictions

Axon Pharma's Marketing department must not publish or transmit claims about
drug efficacy, indications, or off-label uses that have not been approved by
FDA labeling. The Compliance Agent must REDACT or BLOCK such claims when
they appear in cross-subsidiary messages destined for Pharma Marketing.

Allowed:
  - Statements about FDA-approved indications, dosing, and safety as
    reflected in the most recent FDA label.
  - Internal scientific discussions between Clinical Research and Pharma
    Research (NOT marketing) that reference investigational uses.

Blocked or coached:
  - Sending investigational or off-label claims to Pharma Marketing for
    external promotion.
  - Sending pre-approval efficacy data to any external audience.

Coached:
  - Internal discussions where the boundary is unclear (e.g. a Marketing
    department asking a Pharma Research department about an emerging
    indication). Return decision="coach" with a coaching_message asking the
    caller to specify whether the request is for internal scientific
    discussion or external promotional copy.
