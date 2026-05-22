# 21 CFR Part 11 Audit Trail Integrity

When Axon Clinical Research is acting in an FDA-regulated capacity (clinical
trials, drug development records, electronic submissions), every agent
action that creates, modifies, or deletes an electronic record must be:

  - Attributable to a specific identified actor (agent + caller chain).
  - Time-stamped to a synchronized clock.
  - Immutable (the audit record cannot be silently altered).
  - Tied to the underlying record.

The Compliance Agent must REJECT (block) any agent action that:

  - Attempts to bypass the AUDIT.* JetStream by writing directly to a target
    subsidiary's data store without traversing the gatekeeper interceptor.
  - Modifies an existing electronic record without a corresponding audit
    record of the change.
  - Truncates, deletes, or rewrites historical audit entries.

If an action would generate a valid audit entry through normal channels,
COACH or ALLOW as appropriate.
