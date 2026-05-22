# External disclosures and the BAA boundary

PHI may only flow outside the Axon Health platform to entities that have
signed a Business Associate Agreement (BAA) with Axon Health. Common
non-BAA destinations that must NEVER receive PHI:

  - Personal email addresses (gmail.com, outlook.com, yahoo.com, etc.)
  - Generic external research domains without a BAA
  - Public webhooks
  - Third-party consumer APIs (translation services, generic LLM providers,
    consumer cloud storage)
  - Internet-published URLs (any HTTP/HTTPS outside the axonhealth.internal
    or axonhealth.local DNS zones)

If a proposed agent action attempts to send PHI to one of these
destinations, the HIPAA Agent MUST return:

    { "decision": "block",
      "severity": "high",
      "rationale": "Attempted disclosure of PHI to a non-BAA destination." }

An incident must be opened so that a human reviewer can determine whether
the destination should be onboarded under a BAA, whether the action was
inappropriate, or whether the PHI should have been redacted before sending.

A request to send fully de-identified information (no PHI per Safe Harbor)
to an external destination MAY be allowed, subject to the Compliance Agent's
review of FDA marketing, IP, and trade-secret considerations.
