# Healthcare AI Gatekeeper: Use Cases and Demand Signals

Scope: the need for a layer that sits between AI agents or LLM apps and other systems or outside model APIs, redacts PHI (the 18 Safe Harbor identifiers), runs policy judges (allow/block/coach), and keeps an audit trail. Researched 2026-11-11. US focus.

Source-quality legend used below: **[Fact]** = primary source or multiple consistent reports. **[Vendor]** = vendor blog or marketing, treat as opinion or unverified. **[Opinion]** = practitioner comment. **[Preprint]** = not peer reviewed.

Method note: Reddit is blocked from the search and fetch tools used here, so **no Reddit posts could be quoted**. Practitioner voice comes from Hacker News (Algolia API) and news reports of real incidents.

---

## 1. Concrete workflows that need PHI scrubbing or guardrails before data reaches an LLM or agent

### Takeaway
The clearest, best-documented use case is **staff pasting PHI into consumer AI tools** (shadow AI). Real 2026 incidents exist: a Washington state psychiatric facility employee used personal ChatGPT for case notes, and Weill Cornell found imaging data uploaded to unauthorized AI tools. The second clear use case is **developers and startups sending PHI to LLM APIs**. A BAA plus zero data retention is the usual route, and vendors and practitioners repeatedly say that by itself is not enough. Agent-to-agent and payer/pharma data-sharing use cases are plausible, but this pass found little hard evidence of demand for them.

### Cited Findings
- **Shadow AI with real PHI, in production (2026 incident).** At Washington DSHS's Lake Burien Transitional Care Facility, a staff member "used their personal ChatGPT account to draft summaries for client case notes." The notes held patient names, diagnoses and medications. The employee had done it several times before it was caught. 12 families were notified about Lake Burien patients, and 4 Western State Hospital patients were affected. Staff were told to delete all ChatGPT prompts before deleting their accounts. **[Fact]** — [HIPAA Journal](https://www.hipaajournal.com/healthcare-providers-unauthorized-disclosure-phi-ai-tools/)
- **Research data sent to unauthorized AI tools (2026 incident).** Weill Cornell Medicine found on 2026-09-06 that NewYork-Presbyterian radiology data had been "entered into AI and machine learning tools without authorization" between June 10 and 20, 2026. The data included MRNs, accession numbers, service dates, provider names, diagnoses, procedures and medications, but not names or SSNs. The research was suspended, deletion was requested, and staff were retrained. **[Fact]** — [HIPAA Journal](https://www.hipaajournal.com/healthcare-providers-unauthorized-disclosure-phi-ai-tools/). Relevance: a breach can happen with names and SSNs removed, because MRNs, accession numbers and dates are Safe Harbor identifiers too. A naive "strip name and SSN" tool would not have prevented it.
- **Loma Linda University Health:** reported PHI exposure through an external AI platform (details not verified here). **[Vendor/security blog]** — [RedBot Security](https://redbotsecurity.com/threat-intelligence/loma-linda-health-ai-phi-exposure/)
- **Clinician demand for note drafting.** In a 2024 pediatric survey (older), 63% said that **if a HIPAA-compliant version were available** they would use it to draft all or part of a clinical note. The demand depends on a compliant channel existing. **[Fact, 2024]** — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC11427860/table/table3)
- **Startups and developers calling OpenAI or Anthropic APIs.** The OpenAI API can be used with PHI only "with proper setup (BAA + zero-retention endpoints)". A DEV post describes developers sending patient data through standard API setups without a BAA. **[Opinion/anecdote]** — [DEV Community](https://dev.to/dannwaneri/i-found-50-companies-accidentally-breaking-hipaa-with-chatgpt-1olc)
- **Open-source and commercial redaction proxies already exist,** which shows builders feel this pain:
  - "Show HN: Phi-Redactor" is a reverse proxy between an app and OpenAI or Anthropic. It uses Presidio and spaCy to mask the 18 Safe Harbor identifiers with synthetic values, then rehydrates them in the response. — [HN](https://news.ycombinator.com/item?id=47170744), [GitHub](https://github.com/DilawarShafiq/phi-redactor)
  - Redact-Proxy ("the ngrok for PHI") is a commercial drop-in tool. — [redact.health](https://www.redact.health/redact-proxy)
- **AI vendors in utilization management handle large PHI volumes.** Xsolis, an AI utilization-management vendor, had a phishing breach exposing about 1.4M patients across 7 to 9 health systems (reports differ), including SSNs, insurance and treatment data. One source says HHS notice came 135 days after discovery, against a 60-day rule. The AI was incidental to the attack, so this case argues for vendor governance and audit, not prompt redaction. **[Fact; details conflict]** — [Paubox](https://www.paubox.com/blog/ai-vendor-xsolis-breach-exposes-data-on-1.4-million-patients), [TechTimes](https://www.techtimes.com/articles/319011/20260624/healthcare-breach-ai-vendor-xsolis-exposes-14-million-records-across-seven-major-hospitals.htm)
- **Agentic AI widens the attack surface.** "AI now connects to EHRs, billing tools, scheduling systems, and third-party apps." A March 2026 disclosure reportedly involved Heidi Health's scribe, where guardrails could be rewritten with three prompts. **[Vendor; unverified incident]** — [Censinet](https://censinet.com/perspectives/prompt-injection-agent-hijacking-matter-healthcare)
- **Research on de-identification tooling:** small expert NER models "consistently outperform LLMs in de-identification tasks" **[Preprint, 2024]** — [arXiv 2412.10918](https://arxiv.org/html/2412.10918v1). Hybrid rule-plus-ML-plus-LLM clinical de-identification (RedactOR) **[Preprint, 2025]** — [arXiv 2505.18380](https://arxiv.org/pdf/2505.18380v2)

### Inferences
- The strongest buyer story is for **hospitals and health systems**: catch or route the PHI staff are already sending to AI. The second is for **digital health builders**: a drop-in proxy in front of LLM APIs. Both are crowded by free OSS (Presidio-based proxies) and by enterprise LLM vendors.
- The Weill Cornell case supports Axon's full-18-identifier approach (MRNs, accession numbers, dates) over name-only scrubbing.
- Agent-to-agent gatekeeping (Axon's distinctive design) is ahead of documented demand. I found no buyer or practitioner explicitly asking for inter-agent PHI gatekeepers.

### Gaps
- No Reddit quotes (domain blocked for these tools). A follow-up should use a browser or Reddit API to mine r/healthIT, r/medicine, r/sysadmin and r/LocalLLaMA.
- Not found: evidence of demand in payer-provider exchange, pharma or clinical-research data sharing, or de-identified training data for an LLM gatekeeper specifically. The incumbents there (tokenization and Expert Determination vendors such as Datavant and Privacy Analytics) were not researched.

---

## 2. What practitioners say (Hacker News, blogs; Reddit unavailable)

### Takeaway
Practitioners mostly say "sign a BAA, use zero retention, and you're on your own for the rest." There is visible fear of leakage and a steady stream of DIY redaction proxies. Skeptics call redaction a "band-aid" and prefer local models or confidential computing.

### Cited Findings (HN comments, verbatim, via Algolia API)
- "You need to sign a BAA (Business Associate Agreement)." — caymanjim, 2026-11-08 — [HN](https://news.ycombinator.com/item?id=50416163) **[Opinion]**
- "these aren't HIPAA compliant out of the box. You still have to sign a BAA with OpenAI" — selinkocalar, 2024-02-26 — [HN](https://news.ycombinator.com/item?id=39515984) **[Opinion]**
- "The chance of data leaking out through the LLM or hacks is too high without HIPAA." — simple10, 2024-09-08 — [HN](https://news.ycombinator.com/item?id=41482710) **[Opinion]**
- "It's not HIPAA compliant and shares data with LLM providers currently, so best to use a fake patient profile" — augustinemp (builder of a health LLM prototype), 2024-08-25 — [HN](https://news.ycombinator.com/item?id=41346012) **[Opinion]**
- On a mental-health LLM tool: "erroneously sharing HIPAA PHI, because that alone looks like a HIPAA violation waiting to happen." — xerox13ster, 2026-08-27 — [HN](https://news.ycombinator.com/item?id=49472399) **[Opinion]**
- Preference for local models: "HIPAA with medical records is another one." (a reason to run LLMs locally) — jmyeet, 2026-10-28 — [HN](https://news.ycombinator.com/item?id=50278479) **[Opinion]**
- On consumer self-entered data: "If users choose to enter their own healthcare data then that's on them and there is no legal protection." — nradov, 2026-01-05 — [HN](https://news.ycombinator.com/item?id=46505001) **[Opinion]**
- A 2023 thread (older) said that redacting all identifying information "would most likely be legally Kosher." Commenters noted that heavy redaction makes records much less useful. — [HN](https://news.ycombinator.com/item?id=35160524) **[Opinion, older]**
- The Tinfoil (YC) launch thread called PII redaction a "band-aid" and argued for hardware-verified confidential inference instead. — [HN](https://news.ycombinator.com/item?id=43996555) **[Opinion; competing approach]**
- A comment on an xAI CLI analysis said the covered entity or business associate, not the AI vendor, generally bears responsibility for PHI disclosures. — [HN](https://news.ycombinator.com/item?id=48877371) **[Opinion]**
- Blogs and vendors: "NLP de-identification misses identifiers buried in free text, and one false negative means patient data left your boundary unprotected." Also: "Automated redaction rarely clears that bar [Safe Harbor/Expert Determination], so most teams keep [the BAA]." **[Vendor]** — [Respan](https://www.respan.ai/resources/hipaa-baa-llm-engineering), [Specode](https://www.specode.ai/blog/openai-llm-api-hipaa)
- A redaction or de-identification provider that touches PHI is itself a business associate and needs a BAA with its client. **[Opinion; legal claim to verify with counsel]** — [Substack](https://quiteafewclaims.substack.com/p/the-paths-to-healthcare-plg-part-a99)
- "Shadow AI is a data movement problem, and blocking apps won't fix it." **[Opinion, title]** — [Side Effects (Substack)](https://sideeffectsdhi.substack.com/p/shadow-ai-is-a-data-movement-problem)

### Inferences
- The developer pain is real but low-intensity. Most treat "BAA + ZDR" as the bar and do not ask for more. Redaction is wanted mainly when there is no BAA, for local or multi-vendor routing, or as a backstop.
- The recall worry ("one false negative") is the main objection a buyer will raise. Axon's scored PHI eval with holdout recall numbers directly answers it and should be front and center.
- Because a gatekeeper vendor becomes a business associate, Axon would need to sign BAAs, which means real security and compliance overhead. Self-hosted deployment avoids some of that.

### Gaps
- No clinician-voiced (Reddit or forum) quotes captured. The HN sample is developer-heavy.
- Algolia search on "PHI redaction / deidentification hospital ChatGPT" returned zero comments, which may itself be a weak signal of low HN discussion volume.

---

## 3. Regulatory drivers (status as of Nov 2026)

### Takeaway
No US federal rule today specifically **requires** an AI gatekeeper or AI-specific audit trail for LLM traffic. The federal trend in 2025 and 2026 is **deregulatory**: HTI-5 removed the HTI-1 AI transparency requirements, and the HIPAA Security Rule overhaul has slipped to a 2027 target. The drivers are existing HIPAA duties (minimum necessary, BAAs, audit controls, breach notification), voluntary but influential governance frameworks (Joint Commission/CHAI, plus a June 2026 voluntary certification), Section 1557, and a patchwork of state laws focused mostly on **disclosure and human review**, not data flow.

### Cited Findings
- **HIPAA Security Rule NPRM (Jan 6, 2025):** not finalized as of an Oct 5, 2026 Federal Register check. More than 4,700 comments. The Unified Agenda now lists **July 2027** for final action, a planning estimate (the original target was May 2026). CHIME and more than 100 provider groups asked HHS to withdraw or scale it back (single source). The current rule, including risk analysis and audit controls, remains enforceable. **[Secondary; verify on Federal Register]** — [hipaariskassessmenttool.com](https://hipaariskassessmenttool.com/hipaa-rule-status/), [Pact-One](https://www.pact-one.com/2026/09/hipaa-security-rule-2026-status/), [Medcurity](https://medcurity.com/hipaa-security-rule-2026/)
- **ONC HTI-5 final rule (released about Oct 26, 2026):** removes the HTI-1 DSI source-attribute requirements (§170.315(b)(11)(iv)-(v)) and the predictive-DSI risk-management requirements ((b)(11)(vi)). ONC says it may revisit. **[Fact, law-firm and trade-press]** — [HealthSystemCIO](https://healthsystemcio.com/2026/10/26/hti-5-final-rule-ai-source-attributes/), [Akin Gump](https://www.akingump.com/en/insights/ai-law-and-regulation-tracker/onc-issues-hti-5-final-rule-removing-model-card-and-risk-management-requirements-for-predictive-decision-support-interventions), [McDermott](https://www.mcdermottlaw.com/insights/oncs-hti-5-final-rule-trims-health-it-certification-requirements-charts-fhir-forward-course/), [Federal Register NPRM 2025-12-29](https://www.federalregister.gov/documents/2025/12/29/2025-23896/health-data-technology-and-interoperability-astponc-deregulatory-actions-to-unleash-prosperity)
- **Section 1557 (nondiscrimination), patient care decision support tools:** compliance was due May 1, 2025. Covered entities must identify tools that use race, sex, age or disability inputs and mitigate discrimination risk. OCR's Jan 2025 "Dear Colleague" letter suggests written policies and an **internal AI registry**. Enforcement is complaint-driven. Repeal or revision under the current administration has been predicted but not confirmed. **[Fact + prediction]** — [Crowell](https://www.crowell.com/en/insights/client-alerts/hhs-applies-discrimination-prohibitions-to-use-of-automated-and-non-automated-patient-care-decision-support-tools), [Baker Donelson](https://www.bakerdonelson.com/ocr-issues-dear-colleagues-letter-regarding-ai-in-medicine), [livecompliance](https://livecompliance.com/learn/ai-healthcare-regulations/)
- **Joint Commission + CHAI "Responsible Use of AI in Healthcare" (RUAIH), Sept 17, 2025:** voluntary. Seven elements, including a formal AI governance structure, privacy and transparency, data security, **ongoing quality monitoring** (risk-based, validate in real-world use), vendor diligence, and voluntary blinded reporting of AI safety events. Expected to inform future accreditation. **[Fact]** — [Fierce Healthcare](https://www.fiercehealthcare.com/ai-and-machine-learning/chai-and-joint-commission-release-guiding-document-health-systems-using-ai), [Fenwick](https://www.fenwick.com/insights/publications/joint-commission-and-chai-release-guidance-on-responsible-use-of-ai-in-healthcare), [Duane Morris](https://www.duanemorris.com/alerts/joint_commission_coalition_health_ai_issue_guidance_provider_use_ai_0925.html)
- **Joint Commission voluntary RUAIH certification (reported launch June 2026)** certifies organizational practices, not products. The 2026 review process guide cites standards such as RUAIH.02.01.01 and evidence of lifecycle monitoring, with tracers for high-risk clinical uses. **[Partly verified; check the JC manual]** — [JC Review Process Guide PDF](https://digitalassets.jointcommission.org/api/public/content/7bd26620a3e54c0ead2138afa37fc167?v=5f349b78), [Radarfirst](https://www.radarfirst.com/blog/joint-commission-chai-ai-guidance-healthcare-governance/)
- **State laws (secondary trackers; verify statutes):**
  - CA **AB 3030** (eff. 2025-01-01): a disclaimer is required on unreviewed gen-AI patient clinical messages, plus a path to a human. CA **SB 1120**: a licensed clinician must make medical-necessity denials. CA **AB 489** (eff. 2026-01-01): AI may not imply a licensed professional is behind it. — [Lexology](https://www.lexology.com/library/detail.aspx?g=801f0844-1f2b-4423-a98d-1e0f3f3b61ca), [healthcarelawinsights](https://www.healthcarelawinsights.com/2026/02/shaping-the-future-navigating-state-level-ai-legislation-in-healthcare/)
  - TX **TRAIGA (HB 149)** (eff. 2026-01-01): providers must disclose AI use in care. TX **SB 1188** (eff. 2025-09-01): practitioners must review AI diagnostic output and disclose it, and certain EHR data must be stored in the US from 2026-01-01. — [verticomply](https://verticomply.com/blog/state-ai-healthcare-laws-2026), [BastionGPT](https://bastiongpt.com/post/state-laws-on-healthcare-ai)
  - IL **HB 1806 (WOPR Act)** (eff. 2025-08-01): bans AI-delivered therapy. Administrative use is allowed with consent and clinician review. — same trackers
  - **Colorado AI Act:** status conflicts. Reports say SB 24-205 was delayed to 2026-06-30, then repealed and replaced by SB 26-189, effective 2027-01-01. One source says a federal preemption effort is in litigation. **[Conflicting; verify]** — [Orrick tracker](https://ai-law-center.orrick.com/us-ai-law-tracker-see-all-states/), [startbusinessbystate](https://startbusinessbystate.com/ai-healthcare-laws-by-state/)
- **Patient expectations (CHAI patient survey, Jan 2026, n=1,456, NORC):** 93% have at least one AI concern. 51% say AI makes them trust care less, and more than 80% say clear accountability would raise trust. 77 to 85% want to be told when AI is used, and about 60% want permission asked first. **[Fact]** — [AHCJ](https://healthjournalism.org/blog/2026/02/shadow-ai-on-the-rise-in-health-care-as-patients-report-less-trust-surveys-say/)

### Inferences
- An audit trail is a **governance enabler** (it helps meet JC/CHAI monitoring, Section 1557 registry and policy expectations, HIPAA audit controls and breach investigation), not a mandated feature. Sell it as "evidence for your AI governance committee and accreditor," not as "required by law."
- State laws mostly regulate **disclosure and human review** of AI outputs. A judge layer that coaches or flags an unreviewed patient-facing message (AB 3030) or an AI-only denial (SB 1120) is a plausible policy pack. This is speculative product fit, not documented demand.
- Federal deregulation weakens the "compliance-forced" buying motive. Risk reduction (breaches like Weill Cornell and DSHS) and accreditation are the stronger levers.

### Gaps
- FDA: not researched in this pass (search budget). January 2026 FDA guidance on CDS and AI was mentioned in a secondary blog ([bloodgpt](https://bloodgpt.com/blog/fda-guidance-openai-claude-healthcare-ai-2026)) but not verified.
- HHS AI Strategy (Dec 2025) and any OCR guidance specific to generative AI and HIPAA: not found in this pass.
- **EU AI Act (brief):** not researched with sources in this pass. AI in medical devices is generally treated as high-risk, with logging and record-keeping duties. Exact obligations and application dates (including any 2025-26 "digital omnibus" delays) must be verified before use.

---

## 4. Survey data: adoption, shadow AI, governance, incidents (2024-2026)

### Takeaway
Adoption is fast, and shadow AI with PHI is common in self-reported surveys: roughly 1 in 6 shadow-AI users admit sometimes including identifiable patient data. Documented, enforced policies are rare (about a quarter of organizations). Exact figures vary by survey.

### Cited Findings
- **Wolters Kluwer Health (release 2026-01-22, n=518 providers and administrators):** 57% have encountered or used unauthorized AI tools (40% encountered, 17% used). About half cite faster workflow as the reason. 1 in 3 cite no approved tool, or approved tools that lack needed features. 42% of administrators vs 30% of providers strongly agree AI policies were clearly communicated. **[Fact]** — [AHCJ](https://healthjournalism.org/blog/2026/02/shadow-ai-on-the-rise-in-health-care-as-patients-report-less-trust-surveys-say/), [BusinessWire](https://www.businesswire.com/news/home/20260122063603/en)
  - From the same Wolters Kluwer data as reported secondarily: among shadow-AI adopters, 17% "sometimes or often include identifiable patient data," and 27% said PHI "might slip" into prompts. **[Secondary; not confirmed in primary]** — [Wolters Kluwer PDF](https://assets.contenthub.wolterskluwer.com/api/public/content/shadow-ai-a-hidden-risk-to-healthcare-pdf), [DH Insights](https://dhinsights.org/news/shadow-ai-emerges-as-one-of-healthcares-biggest-security-risks)
- **Black Book Market Research (Dec 2025):** 58% used generic AI tools (ChatGPT, Gemini, Copilot) for work in the last 30 days. About 44% of those included identifiable patient info or feel at risk of doing so. Only 24% say they have "a clear, documented, enforced staff policy." **[Secondary write-up]** — [DH Insights](https://dhinsights.org/news/shadow-ai-emerges-as-one-of-healthcares-biggest-security-risks), [healthcare.digital](https://www.healthcare.digital/single-post/shadow-ai-is-becoming-a-growing-issue-for-hospitals-and-health-systems)
- **Ponemon (cited secondarily):** only 32% of healthcare organizations believe they have full visibility into staff shadow-AI use. **[Secondary]** — [DH Insights](https://dhinsights.org/news/shadow-ai-emerges-as-one-of-healthcares-biggest-security-risks)
- **Paubox (Oct 2025):** shadow AI is outpacing email security. About 1 in 4 organizations have not formally approved any AI use. **[Vendor report]** — [Paubox PDF](https://www.paubox.com/hubfs/Report%20Assets/RPT.202510.ShadowAI/RPT.202510.ShadowAI.pdf), [BusinessWire](https://www.businesswire.com/news/home/20251014137455/en/Shadow-AI-Is-Outpacing-Healthcare-Security-New-Paubox-Report-Warns)
- **Menlo Ventures, "2025: State of AI in Healthcare" (Oct 21, 2025; n>700 execs; Morning Consult):** healthcare AI spend about $1.4B in 2025 (about 3x 2024). 22% of organizations have implemented domain-specific AI tools (7x 2024): health systems 27%, outpatient 18%, payers 14%. Providers make up about 75% of spend. Startups capture about 85% of gen-AI spend. Ambient scribes are about $600M (2.4x YoY). Customers still prefer EHR vendors beyond scribing. **[Fact: VC survey]** — [Menlo Ventures](https://menlovc.com/perspective/2025-the-state-of-ai-in-healthcare/), [X post](https://x.com/MenloVentures/status/1983242617652646373)
- **Breach cost:** average healthcare breach cost more than $7.4M in 2025 (per Wolters Kluwer release). Third-party vendors are reportedly 58% of healthcare breaches (HSCC, April 2026, secondary). **[Secondary]** — [AHCJ](https://healthjournalism.org/blog/2026/02/shadow-ai-on-the-rise-in-health-care-as-patients-report-less-trust-surveys-say/), [TechTimes](https://www.techtimes.com/articles/319011/20260624/healthcare-breach-ai-vendor-xsolis-exposes-14-million-records-across-seven-major-hospitals.htm)
- **Incidents involving AI and PHI (2026):** DSHS/ChatGPT case notes, Weill Cornell unauthorized AI uploads, Xsolis AI-vendor breach (1.4M). See section 1. — [HIPAA Journal](https://www.hipaajournal.com/healthcare-providers-unauthorized-disclosure-phi-ai-tools/), [Paubox](https://www.paubox.com/blog/ai-vendor-xsolis-breach-exposes-data-on-1.4-million-patients)
- **Unverified:** a vendor blog cites "AMIA 2025: 67% of physicians use consumer AI weekly." The primary source was not found. **Do not use.**

### Inferences
- Shadow AI's root cause, per the surveys, is **no approved tool that does the job**. That favors selling a sanctioned, fast path (gateway plus approved models) over a blocker. "Coach" verdicts that explain and reroute fit this better than hard blocks.
- With only about 24% of organizations having enforced policies, governance tooling has room to grow. With 22% domain-AI adoption, the buyer base is still early.

### Gaps
- No KLAS, Gartner, Rock Health or Bessemer figures captured (budget). No count of OCR enforcement actions specifically about AI found. Primary Black Book and Ponemon reports not fetched.

---

## 5. Does vendor BAA availability reduce the need for a gatekeeper?

### Takeaway
BAAs are now broadly available: OpenAI API, ChatGPT Enterprise and ChatGPT for Healthcare (Jan 2026); Anthropic's Claude for Healthcare (Jan 2026) and HIPAA-ready Enterprise and API; and the clouds (Azure, Bedrock, Vertex). That removes the strongest old reason for redaction ("we can't legally send PHI"). The case for a gatekeeper shifts to minimum necessary, defense in depth, multi-vendor routing and local models, agent and prompt-injection controls, shadow-AI capture, and audit evidence. These are real but softer, "nice to have" arguments, and enterprise LLM bundles and cloud guardrails (e.g. Bedrock Guardrails) compete with them directly.

### Cited Findings
- **OpenAI for Healthcare (Jan 8, 2026):** includes ChatGPT for Healthcare with HIPAA support and BAAs. Rollouts at AdventHealth, HCA, Boston Children's, Cedars-Sinai and Stanford Medicine Children's. **[Fact]** — [Axios](https://www.axios.com/2026/01/08/openai-chatgpt-doctors-patients-health-tab), [IntuitionLabs](https://intuitionlabs.ai/articles/chatgpt-vs-claude-for-healthcare)
- **Anthropic Claude for Healthcare (Jan 11, 2026):** BAA covers Claude Enterprise once HIPAA readiness is activated, and HIPAA-ready Developer Platform orgs, for listed eligible services. Also available via Bedrock, Vertex and Azure under those clouds' BAAs. **[Secondary; sources partly conflict — verify on Anthropic docs]** — [IntuitionLabs](https://intuitionlabs.ai/articles/is-claude-hipaa-compliant), [Paubox](https://www.paubox.com/blog/anthropic-brings-claude-ai-to-healthcare-with-hipaa-tools)
- **The BAA is not the whole job:** "The BAA covers OpenAI's role as a Business Associate. You remain responsible for de-identification, audit logging, encryption, access control, redaction, and ensuring no PHI leaks via system prompts or logs." **[Vendor]** — [Respan](https://www.respan.ai/resources/hipaa-baa-llm-engineering). Similar: "Signing a BAA ... does not, by itself, make a healthcare organization's overall system HIPAA compliant." — [Paubox](https://www.paubox.com/blog/is-claude-ai-hipaa-compliant)
- **Consumer tools fall outside HIPAA:** HIPAA protections don't extend "to non-HIPAA-covered entities, like developers of health apps, wearable health trackers, or AI companies" in consumer contexts. **[Expert quote via news]** — [Yahoo/Decrypt](https://www.yahoo.com/news/articles/openai-chatgpt-health-push-raises-015503387.html)
- **Against redaction:** it is a "band-aid," and confidential computing is the better route. — [HN Tinfoil launch](https://news.ycombinator.com/item?id=43996555). Automated redaction rarely meets Safe Harbor, so teams keep BAAs anyway. — [Respan](https://www.respan.ai/resources/hipaa-baa-llm-engineering). Heavy redaction lowers clinical usefulness. — [HN 2023](https://news.ycombinator.com/item?id=35160524) **[Opinion]**
- **For a separate layer (agentic and injection):** generic prompt-injection detectors miss PHI exfiltration that "looks like fluent, legitimate requests." PromptGuard-2 recall on healthcare threats was 0.40, vs 0.83 for a scope-plus-PHI firewall (self-reported). **[Preprint, June 2026]** — [medRxiv](https://www.medrxiv.org/content/10.64898/2026.06.04.26354950v2.full). Advice: keep guardrails in app logic and access rules, not only prompts. — [Censinet](https://censinet.com/perspectives/prompt-injection-agent-hijacking-matter-healthcare) **[Vendor]**
- **Competing guardrail products** marketed to healthcare: NeMo Guardrails, Lakera Guard, AWS Bedrock Guardrails, Protect AI. **[Vendor listicle]** — [Future AGI](https://futureagi.com/blog/best-healthcare-ai-guardrails-2026/)
- **Shadow AI is not solved by enterprise BAAs** when staff use personal accounts (the DSHS case). — [HIPAA Journal](https://www.hipaajournal.com/healthcare-providers-unauthorized-disclosure-phi-ai-tools/)

### Inferences
- The arguments that still hold after BAAs: (1) **minimum necessary**: the HIPAA standard says send only what the task needs, and a gateway enforces it; (2) **multi-vendor and local-model routing** where not every endpoint has a BAA; (3) **agent-to-agent and tool-use control** with a positive-security scope, where injection classifiers fall short; (4) **one audit trail across vendors** for governance committees and JC/CHAI evidence; (5) **sanctioned alternative** to shadow AI. (1) is an inference from the HIPAA standard and was not researched with sources here.
- The weak points for Axon: free OSS proxies (Presidio-based) cover basic redaction. Cloud-native guardrails come bundled with the BAA'd model. Buyers will ask for proven recall. Health systems buy from EHR vendors and big platforms (Menlo).
- Positioning that seems most defensible: **a scored, auditable policy gateway for agentic workflows** (judges plus Tier-1 PHI plus audit), not "a PHI redactor."

### Gaps
- Not verified: exact Anthropic and OpenAI BAA scopes from primary docs, Google and Azure specifics, or whether zero data retention is required under each.
- No buyer interviews or willingness-to-pay data found. Pricing for competitors (Redact-Proxy, Lakera, Private AI, John Snow Labs, Skyflow) not researched.
- No primary-source or sourced statement on HIPAA "minimum necessary" applied to LLM prompts was captured.
