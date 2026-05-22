# Intellectual Property and Trade-Secret Handling

Axon Health subsidiaries share infrastructure but not all data is freely
shareable across subsidiary boundaries:

  - Axon Pharma's pre-publication drug-discovery research is trade secret.
    It may flow to Axon Clinical Research (legitimate internal use), but
    must NEVER leave the platform without explicit publication review by
    the IP committee.
  - Axon Consumer's marketing campaigns, customer lists, and product roadmaps
    are confidential business information.

For each outbound cross-platform action, the Compliance Agent verifies:

  - Is the payload referencing internal trade secrets? If yes and the
    destination is external, BLOCK.
  - Is the action a known publication channel (e.g., a peer-reviewed
    submission to a registered journal)? COACH the caller to confirm IP
    committee approval ID has been attached.
  - Is the action between two trusted internal subsidiaries? ALLOW.

If unsure, prefer COACH over BLOCK so the caller can supply more context
on a retry.
