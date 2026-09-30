# About Axon Health

> **Status: draft, pending review.** The mission, vision and goals below were
> written on 2026-09-29 from the founding brief (`InitialPrompt.txt`) and the
> roadmap. The brief does not state them itself. They also appear on the
> Enterprise Console (`docs/dashboard/`), so change both together.

## In one sentence

Axon Health is an AI-native medical-technology company where every department
is run by its own specialist AI, and every message between its companies passes
privacy and compliance checks first.

## What it is

Axon Health is an umbrella company with subsidiaries across the health-care
value chain: Axon Clinical Research, Axon Pharma, Axon Enterprise, Axon Consumer
and others. Inside each subsidiary, departments such as Intake, Clinical SME,
Pharma Research, Marketing and Finance are AI agents, each with a model trained
or prompted for its field. The agents work together and share knowledge, and two
AI gatekeepers, the HIPAA Agent and the Compliance Agent, make sure nothing they
exchange breaks HIPAA or other federal and state law.

## Mission

Help medical research and care move faster by letting specialist AI agents work
together across the whole enterprise, without compromising patient privacy or
regulatory compliance.

## Vision

A health enterprise where every department has its own expert AI, and where
compliance is enforced by the platform on every message instead of by review
after the fact.

## How it works

| | |
|---|---|
| **Separate subsidiaries** | Each subsidiary keeps its own agents, data and models. Nothing is shared by default, so one company's records stay with that company. |
| **A specialist AI per department** | Each department has its own model. A Finance model knows corporate finance and accounting law; a Pharma model follows drug research. |
| **One supervised channel** | Each subsidiary has one Supervisor, the only agent allowed to contact another subsidiary. All of that traffic goes over one shared message bus. |
| **Two gatekeepers, full audit** | The HIPAA Agent and Compliance Agent check every message. Patient identifiers are removed, risky messages are stopped, and every decision is kept for seven years. |
| **Private by design** | Everything runs in Docker with open models served by Ollama on Axon's own hardware. No patient data is sent to an outside AI service. |

The engineering version of these points is in the README under *Design tenets*.

## Goals

| State | Goal |
|---|---|
| Done | Prove that two subsidiaries can share clinical knowledge with patient identifiers removed automatically ([milestone 2](milestones/02-cross-subsidiary.md)). |
| Done | Catch every kind of patient identifier HIPAA lists (names, addresses, dates, ID numbers and 14 more), and measure it: 83% on messages the system had never seen, up from 18% ([milestone 3](milestones/03-safe-harbor-phi.md)). |
| Next | Measure the AI gatekeepers' decisions the same way, and fix them rejecting safe messages once identifiers have been removed. |
| Next | Put a person in the loop: every blocked message goes to a human reviewer who approves or denies it. |
| Next | Give operators a live console inside the platform, like the Enterprise Console but updating in real time. |
| Later | Give each department its own fine-tuned model instead of a shared base model. |
| Later | Bring Axon Enterprise and Axon Consumer online, and add Compliance, Marketing and Finance departments. |
| Later | Run in production on HIPAA-eligible managed Kubernetes, using the same design as today. |

## Open questions for the founder

- Which departments do Axon Enterprise and Axon Consumer have?
- Which subsidiary does Finance belong to, or is it shared at the parent level?
- Are the mission, vision and goals above right?

## Glossary

| Term | Meaning |
|---|---|
| Subsidiary | One Axon company, such as Axon Pharma. |
| Department | A specialist AI agent inside a subsidiary. |
| Supervisor | The agent that routes a subsidiary's work and is its only contact with other subsidiaries. |
| Gatekeeper | The checks every message between subsidiaries must pass: fixed rules, then the HIPAA Agent, then the Compliance Agent. |
| PHI | Protected health information: anything that could identify a patient, like a name, ID or record number. |
| Verdict | The gatekeeper's decision. **allow**: deliver as is. **redact**: remove identifiers, then deliver. **coach**: send back with advice. **block**: stop and open an incident. |
| Audit log | The permanent record of every check and decision (the `AUDIT` stream). |
| Incident | A record opened for every blocked message, for a person to review (the `INCIDENT` stream). |
