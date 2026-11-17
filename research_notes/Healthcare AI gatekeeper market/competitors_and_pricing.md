# Healthcare AI Gatekeeper: Competitors, Funding, Pricing, Gaps

Research date: 2026-11-11. About 16 search/fetch calls. Many sources are vendor blogs or aggregators; reliability is flagged inline. Items older than 2024 are flagged.

## 1. PHI/PII redaction and de-identification vendors: pricing and claimed accuracy

### Takeaway
The redaction layer is crowded and cheap at the bottom (Presidio free; Google DLP about $0.03 per 1M chars; AWS Comprehend PII about $1-2 per 1M chars; Azure PII $1.67-6.67 per 1M chars). The premium tier (John Snow Labs, Limina/ex-Private AI, Skyflow) sells on accuracy claims and HIPAA "expert determination" support, with mostly enterprise, unpublished pricing. Accuracy claims are vendor-run and on different corpora, so they are not comparable.

### Cited Findings

**Limina (formerly Private AI)**
- Private AI rebranded as Limina in March 2026; company says product, API, features and deployment options are unchanged — [Limina announcement](https://www.getlimina.ai/en/private-ai-is-now-limina); [LLM Capsule comparison](https://llmcapsule.ai/resources/learn/llm-capsule-vs-limina/)
- Vendor claims it misses 0.2% to 7% of entities across its test datasets; a comparison site cites a vendor-reported "99.5% accuracy" on an undisclosed test set — [Limina site](https://www.private-ai.com/en); [Eden AI comparison](https://www.edenai.co/post/best-document-redaction-apis)
- G2 listing claims "less than half the error rate" of AWS Comprehend, Google DLP and Presidio on real-world data (vendor-style claim); 22 reviews — [G2](https://www.g2.com/products/limina/reviews)
- Pricing: one source reports a free Starter plan capped at 75 API calls/day, a quoted Batch plan, and custom Enterprise (committed volume, regional deployment); HIPAA expert-determination reports come through partners, priced separately. Another source says per-document plus per-entity charges and no public free tier. Sources conflict — [Eden AI](https://www.edenai.co/post/best-document-redaction-apis); [Wald.ai](https://wald.ai/blog/top-4-pii-redaction-tools-a-deep-dive-comparison)
- Vendor markets "expert determination-ready outputs" for HIPAA de-identification — [Limina site](https://www.private-ai.com/en)

**John Snow Labs (Healthcare NLP de-identification)**
- Vendor benchmark (published 2026-08-27, by CEO David Talby): 0.98 micro F1 on official 2014 i2b2 test set (13 labels), 0.96 (7 labels); 0.96 PHI F1, 0.98 recall on a public 1,479-chunk / 48-doc expert-annotated set; 0.98 recall, 0.95 F1 on a private 381,959-token corpus — [JSL benchmarks 2026](https://www.johnsnowlabs.com/clinical-de-identification-benchmarks-2026-john-snow-labs-against-openai-databricks-presidio-and-llm-apis/)
- Same page: per-entity F1 on 1,479-chunk set: AGE 0.97, CONTACT 0.95, DATE 0.98, IDNUM 0.95, LOCATION 0.93, NAME 0.93 — [JSL benchmarks 2026](https://www.johnsnowlabs.com/clinical-de-identification-benchmarks-2026-john-snow-labs-against-openai-databricks-presidio-and-llm-apis/)
- Claims 54% more PHI detected than OpenAI Privacy Filter at 5.8x CPU throughput; Privacy Filter: recall 0.64, F1 0.55, address recall 0.25 on JSL's private corpus (vendor-run) — [JSL benchmarks 2026](https://www.johnsnowlabs.com/clinical-de-identification-benchmarks-2026-john-snow-labs-against-openai-databricks-presidio-and-llm-apis/)
- No public prices on that page; pipelines listed on AWS, Azure, Snowflake and Databricks marketplaces — [JSL benchmarks 2026](https://www.johnsnowlabs.com/clinical-de-identification-benchmarks-2026-john-snow-labs-against-openai-databricks-presidio-and-llm-apis/)

**Microsoft Presidio (open source)**
- MIT licence, $0; total cost = compute + engineering to tune recognizers; source says Presidio is "transitioning to a community-owned project" — [Beri.net pricing article, Oct 2026](https://www.beri.net/article/pii-redaction-pricing-comprehend-azure-google-presidio-cost-per-million-characters)
- Independent studies: Alrazihi et al. 2025, 200 UK neurosurgical docs: precision 0.51, recall 0.74, F1 0.60. Kotevski et al. 2022, 300 Australian oncology docs: strict P 0.89 / R 0.81 / F1 0.85; relaxed R 0.90 / F1 0.90 — as summarized in [JSL benchmarks 2026](https://www.johnsnowlabs.com/clinical-de-identification-benchmarks-2026-john-snow-labs-against-openai-databricks-presidio-and-llm-apis/)
- Open-source "phi-redactor" proxy builds on Presidio + spaCy with custom recognizers, encrypted SQLite PHI-to-synthetic vault, hash-chained audit log and Safe Harbor evidence report (single-developer repo, maturity unverified) — [GitHub phi-redactor](https://github.com/DilawarShafiq/phi-redactor)

**Hyperscaler APIs: pricing**
- AWS Comprehend DetectPiiEntities: $0.0001 per 100-char unit, 3-unit (300 char) minimum per request: about $1.00 per 1M chars at list, about $2.00 on 150-char chat messages; about $3,000/month for 10M messages; English and Spanish only. ContainsPiiEntities $0.000002/unit (two-stage screen about $0.24 per 1M chars) — [Beri.net, Oct 2026](https://www.beri.net/article/pii-redaction-pricing-comprehend-azure-google-presidio-cost-per-million-characters)
- Azure AI Language Text PII: $1.00 per 1,000 records (up to 1,000 chars each), tiering to $0.25 above 10M; $6.67 to $1.67 per 1M chars; free tier 5,000 records/month — [Beri.net](https://www.beri.net/article/pii-redaction-pricing-comprehend-azure-google-presidio-cost-per-million-characters)
- Google Cloud Sensitive Data Protection (DLP): inspection $3.00/GiB, transformation $2.00/GiB (lower above 1 TiB); first GiB free; about $0.03 per 1M chars; about $40/month for 10M messages — [Beri.net](https://www.beri.net/article/pii-redaction-pricing-comprehend-azure-google-presidio-cost-per-million-characters)
- Comparison point in same article: Claude Haiku 5.5 input about $0.025 per 1M chars; headline "Comprehend bills 40x the model it guards" — [Beri.net](https://www.beri.net/article/pii-redaction-pricing-comprehend-azure-google-presidio-cost-per-million-characters)
- Azure Health Data Services de-identification service: billed per MB across its three operations (tag, redact, surrogate); 50 MB/month free allotment; dollar rate not visible in fetch — [Microsoft Learn](https://learn.microsoft.com/en-us/azure/healthcare-apis/deidentification/overview); [Azure pricing page](https://azure.microsoft.com/en-ca/pricing/details/health-data-services/)
- Comprehend Medical DetectPHI detects PHI but alone does not meet HIPAA de-identification requirements — [AccountableHQ](https://www.accountablehq.com/post/is-amazon-comprehend-medical-hipaa-compliant-everything-you-need-to-know)

**Hyperscaler APIs: accuracy (peer-reviewed, ML4H 2023, 100 i2b2 notes, micro F1)** — older than 2024, flagged
- JSL 0.97 (patient name recall 93%); AWS Comprehend Medical 0.96 (name recall 90%); Azure Text Analytics for Health 0.72 (patient name recall 67%, physician 55%); GCP Healthcare API 0.64 (patient name recall 42%) — summarized in [JSL benchmarks 2026](https://www.johnsnowlabs.com/clinical-de-identification-benchmarks-2026-john-snow-labs-against-openai-databricks-presidio-and-llm-apis/)
- A separate arXiv paper on 100 i2b2 notes: AWS 0.94, Azure 0.81; Azure and GCP could not identify ID numbers, so IDs were excluded from scoring — [arXiv 2312.08495](https://arxiv.org/pdf/2312.08495)
- Radiology de-id paper benchmarking large-scale-trained models against cloud vendor methods (Nov 2025) — [arXiv 2511.04079](https://arxiv.org/pdf/2511.04079) (not fetched; numbers not extracted)

**Frontier LLMs and data-platform built-ins as de-identifiers (vendor-run by JSL, 1,479-chunk set)**
- PHI F1: Claude Opus 4.8 0.91 (CONTACT 0.49, AGE 0.68); GPT-5.5 0.89 (CONTACT 0.55); Gemini 3.1 Pro 0.86; GPT-4o 0.79 (earlier 2025 eval) — [JSL benchmarks 2026](https://www.johnsnowlabs.com/clinical-de-identification-benchmarks-2026-john-snow-labs-against-openai-databricks-presidio-and-llm-apis/)
- Databricks ai_mask(): F1 0.71 (6 labels) falling to 0.61 (full 18-label HIPAA list); contact identifiers found only 35% of the time — [JSL benchmarks 2026](https://www.johnsnowlabs.com/clinical-de-identification-benchmarks-2026-john-snow-labs-against-openai-databricks-presidio-and-llm-apis/)

**Skyflow (LLM privacy vault)**
- $30M Series B extension led by Khosla Ventures, March 2024, tied to demand for PII protection in enterprise LLMs and data residency — [BusinessWire](https://www.businesswire.com/news/home/20240328765469/en/Skyflow-Raises-$30-Million-led-by-Khosla-Ventures-for-Data-Privacy-in-AI-and-Global-Data-Residency); [Diginomica](https://diginomica.com/skyflow-raises-$30m-data-privacy-enterprise-llms)
- Total raised about $97-100M (sources differ) — [CB Insights](https://www.cbinsights.com/company/skyflow-2/financials); [Clay](https://clay.com/dossier/skyflow-funding)
- Earlier $45M Series B pitched at fintech and healthtech (pre-2024) — [Dark Reading](https://www.darkreading.com/application-security/data-privacy-api-company-skyflow-raises-45m-series-b-funding-to-help-fintech-and-healthtech-companies-ship-faster)

**Nightfall AI**
- Reported $40M Series B (date not given in snippet; likely pre-2024) — [Signalbase](https://www.trysignalbase.com/news/funding/nightfall-ai-secures-40m-in-series-b-funding-for-leading-cloud-data-loss-prevention-technology)

**Protecto.ai**
- Seed round dated 2023-11-08, total about $5M; launched "Protecto Vault" SaaS for AI agent builders in December 2025 — [Caplight](https://www.caplight.com/company/protecto)

**Gretel (synthetic data)**
- Acquired by NVIDIA, March 2025; reported nine-figure price above its last $320M valuation (Wired via TechCrunch); about 80 employees; raised more than $67M — [TechCrunch](https://techcrunch.com/2025/03/19/nvidia-reportedly-acquires-synthetic-data-startup-gretel/); CB Insights says $65.5M — [CB Insights](https://www.cbinsights.com/company/gretel/financials)

### Inferences
- Commodity cloud redaction is priced at cents to a few dollars per million characters; a new entrant cannot win on per-character price against Google DLP or free Presidio. Pricing must be value-based (per deployment / per agent / per bed), tied to the judge + audit layer, not to redaction volume.
- Every published accuracy number uses a different corpus, label set and strict/relaxed scoring. A vendor that publishes a reproducible, blind holdout with scoring code (which JSL partly does with its public 1,479-chunk set) has a credibility edge.
- Weak categories across tools: CONTACT identifiers (LLMs 0.49-0.69 F1), ID numbers (Azure/GCP could not detect), addresses (OpenAI Privacy Filter 0.25 recall). These are where shaped/labelled pattern rules (like Axon's Tier-1) add most value over pure NER or LLM detectors.
- Presidio's 2025 clinical recall of 0.74 at 0.51 precision shows out-of-the-box open-source tooling over-redacts and under-recalls on clinical text; "clinical text damage" (over-redaction of doses, eponyms) is rarely measured by vendors.

### Gaps
- No verified current price for Comprehend Medical DetectPHI or Azure Health Data Services de-identification per MB (pricing pages did not render).
- No public pricing found for Nightfall, Skyflow, Tonic.ai, Protecto, John Snow Labs.
- Tonic.ai (Textual) and iMerit not researched in this pass (call budget).
- No 2025-2026 funding confirmed for Skyflow, Nightfall or Protecto.

## 2. LLM guardrails / firewalls / AI security: acquisitions 2024-2026

### Takeaway
The horizontal AI-security layer consolidated into big security vendors in 2024-2025 at roughly $150M-$700M per deal. These products target prompt injection, data leakage and model security for any industry, not HIPAA semantics. Independent survivors (HiddenLayer, Lasso, Zenity) are pivoting to agent/MCP runtime security.

### Cited Findings
- Palo Alto Networks acquired Protect AI; closed July 2025; reported $500M-$700M, one source $634.5M; now powers Prisma AIRS — [Superblocks roundup](https://www.superblocks.com/blog/generative-ai-security-tools); [Infosecurity Magazine](https://www.infosecurity-magazine.com/news-features/cybersecurity-ma-crowdstrike/)
- Check Point acquired Lakera, announced 2025-09-16; terms undisclosed, press reports about $300M — [Infosecurity Magazine](https://www.infosecurity-magazine.com/news-features/cybersecurity-ma-crowdstrike/); [Forrester](https://www.forrester.com/blogs/securing-ais-ma-feeding-frenzy-is-on/)
- F5 acquired CalypsoAI for $180M, mostly cash, closed 2025-09-29; one source says $145.2M — [F5 Wikipedia](https://en.wikipedia.org/wiki/F5,_Inc.); [CalypsoAI profile](https://cybercompanyprofiles.com/companies/calypsoai)
- SentinelOne acquired Prompt Security, reported about $250M (one source $133.6M) — [Superblocks](https://www.superblocks.com/blog/generative-ai-security-tools); [BankInfoSecurity](https://www.bankinfosecurity.com/blogs/largest-cyber-stocks-feast-in-2025-as-smaller-stocks-famish-p-4014)
- Cato Networks acquired Aim Security (September 2025), its first acquisition; earlier report of talks at $350-400M (not a confirmed price); Aim raised $10M seed (Jan 2024) + $18M (June 2025) — [SecurityWeek](https://securityweek.com/cato-networks-acquires-ai-security-firm-aim-security); [Calcalist](https://www.calcalistech.com/ctechnews/article/ryl75cmqgl)
- Cisco acquired Robust Intelligence (announced 2024; price not found); became basis of Cisco's Foundation AI group — [SecurityWeek / CB Insights matrix](https://cbinsights.com/research/ai-security-aquisition-matrix/)
- Aggregate: eight major vendors (Check Point, Cisco, CrowdStrike, F5, Palo Alto and others) spent over $2.0B acquiring AI-security startups — [Forrester](https://www.forrester.com/blogs/securing-ais-ma-feeding-frenzy-is-on/); [Killchain Sales](https://www.killchainsales.com/blog/ai-security-consolidation-cybersecurity-aes)
- HiddenLayer: $100M Series B led by Delta-v Capital (an aggregator dates it September 2026), total at least $156M ($6M seed 2022, $50M Series A 2023), pitched at runtime security for AI agents — [Unite.ai](https://www.unite.ai/hiddenlayer-raises-100m-series-b-to-expand-ai-agent-security-platform/); [TechCrunch 2023](https://techcrunch.com/2023/09/19/hiddenlayer-raises-50m-for-its-ai-defending-cybersecurity-tools)
- Lasso Security: $30M round led by ClearSky (year unconfirmed); ships an open-source MCP Gateway inspecting tool descriptions, parameters and responses — [DH Insights](https://www.dhinsights.org/news/investors-flock-to-agentic-ai-as-startups-pitch-fixes-for-cybersecurity-gaps); [Check Point agentic roundup](https://www.checkpoint.com/cyber-hub/cyber-security/what-is-ai-security/what-is-agentic-ai-security/top-agentic-ai-security-solutions-in-2026/)
- SentinelOne (Prompt Security) AI Gateway sits between AI apps and MCP servers, inspecting every request and response — [Check Point roundup](https://www.checkpoint.com/cyber-hub/cyber-security/what-is-ai-security/what-is-agentic-ai-security/top-agentic-ai-security-solutions-in-2026/)
- Single-source, unverified: Zenity $125M Series C (Aug 2026, about $185M total); Oasis Security about $195M total; Astrix Security acquired by Cisco June 2026 — [Mintive blog](https://www.mintive.com/blog/agentic-ai-security)
- Runlayer (MCP security) backed by Khosla and Felicis — [Omid Saffari MCP roundup](https://omidsaffari.com/blog/best-mcp-security-platforms-for-enterprise-agents-2026)
- PointGuard AI launched MCP Security Gateway, March 2026 — [EIN Presswire](https://www.einpresswire.com/article/900087831/pointguard-ai-unveils-mcp-security-gateway-to-secure-autonomous-ai-agents)

### Inferences
- Exit prices of $150M-$700M for horizontal AI-firewall startups with modest revenue show strategic buyers pay for the control point in the AI request path. A healthcare-specific control point is a plausible acquisition target for these same buyers (Palo Alto, Check Point, F5, Cisco) or for health-IT vendors.
- Being acquired means these products are now bundled into network/endpoint platforms (SASE, firewalls). They will be sold to hospital CISOs as "good enough" PHI/DLP. A new entrant must show what they miss: HIPAA minimum-necessary reasoning, clinical-text damage, and per-message audit tied to HIPAA retention.

### Gaps
- NVIDIA NeMo Guardrails, Guardrails AI, and Arthur not researched in this pass (open-source / observability players; no funding or pricing verified).
- No confirmed price for Cisco/Robust Intelligence or Cato/Aim.
- No public list pricing for any acquired guardrail product.

## 3. Healthcare-specific AI governance, assurance and HIPAA LLM gateways

### Takeaway
Healthcare AI governance money is going to enterprise-wide "AI enablement + governance" platforms (Qualified Health, $30M seed then $125M Series B) and to policy/registry tools (Credo AI, Censinet). The inline "HIPAA gateway for LLMs" niche is filled by small or early players (Redact-Proxy, nRouter, Concentrate AI, Tetrate, MintMCP/Mintive) and an open-source repo. None found does LLM-based HIPAA judging of agent-to-agent traffic.

### Cited Findings
- Qualified Health launched January 2025 with $30M seed (SignalFire, Healthier Capital, Town Hall Ventures, Frist Cressey; Intermountain Ventures, Flare Capital participating) — [PR Newswire](https://www.prnewswire.com/news-releases/qualified-health-launches-with-30m-seed-funding-to-develop-the-infrastructure-for-generative-ai-in-healthcare-302345625.html); [Fierce Healthcare](https://www.fiercehealthcare.com/ai-and-machine-learning/new-startup-qualified-health-aims-build-infrastructure-generative-ai-armed)
- Qualified Health raised $125M Series B; partners include Mercy, Emory Healthcare, University of Rochester Medicine, Jefferson Health, UT System; one summary says NEA led (date/lead to confirm) — [PR Newswire Series B](https://www.prnewswire.com/news-releases/qualified-health-raises-125m-series-b-to-meet-growing-demand-for-enterprise-ai-transformation-across-health-systems-302723600.html); [MLQ](https://mlq.ai/news/qualified-health-raises-125m-series-b-for-ai-healthcare-platform/)
- Qualified Health platform: enforceable governance, role-based access, risk alerts, privacy protections, hallucination safeguards — [HC Innovation Group](https://www.hcinnovationgroup.com/analytics-ai/generative-ai/article/55300289/qualified-healths-kedar-mate-md-on-digital-governance-for-generative-ai)
- Credo AI joined the CHAI Partner Program (April 2026); positions as enterprise AI governance across models, apps, agents and third-party vendors — [BusinessWire](https://www.businesswire.com/news/home/20260428575394/en/); [AI Magazine](https://aimagazine.com/news/credo-ai-ceo-navrina-singh-on-governing-ai-at-scale)
- Censinet: TPRM AI and ERM AI on its RiskOps platform; claims 80% faster third-party risk assessments (vendor claim, Oct 2025) — [Censinet knowledge base](https://knowledgebase.censinet.com/post/censinet-ai-tm-transforming-ai-risk-management-in-healthcare)
- CHAI assurance labs: Fierce Healthcare reported the program "created confusion" and labs were scrapped/reshaped toward post-deployment monitoring; a less-established outlet says the concept "quietly collapsed" by early 2025; CHAI site still says providers list "will be shared soon" — [Fierce: scrapped labs](https://www.fiercehealthcare.com/ai-and-machine-learning/inside-chais-failed-assurance-labs); [Fierce: post-deployment monitoring](https://www.fiercehealthcare.com/ai-and-machine-learning/chai-embarks-post-deployment-monitoring-ai); [Distilinfo](https://distilinfo.com/2026/02/22/chais-ai-healthcare-promise-meets-reality/); [CHAI](https://chai.org/what-are-assurance-labs)
- CHAI model "nutrition labels" / Assurance Standards Guide (June 2024) — [CHAI guide PDF](https://chai.org/wp-content/uploads/2024/06/CHAI-Assurance-Standards-Guide-6-26-2024.pdf); [Becker's](https://www.beckershospitalreview.com/healthcare-information-technology/the-organization-rolling-out-ai-nutrition-labels-for-healthcare.html)
- Redact-Proxy (redact.health): wraps LLM SDK, redacts PHI before leaving the machine, streaming, reversible re-identification; vendor notes BAAs/access controls still required — [Redact-Proxy](https://www.redact.health/redact-proxy)
- nRouter: healthcare LLM gateway, stateless PHI redaction sidecar over mTLS 1.3, zero retention, BAA on request — [nRouter](https://nrouter.ai/solutions/healthcare)
- Concentrate AI: managed gateway, BAA-covered routes only for HIPAA orgs, zero data retention, PII/PHI redaction — [Concentrate AI](https://concentrate.ai/blog/how-to-use-gpt-and-claude-with-phi-through-a-hipaa-compliant-ai-gateway-and-a-baa)
- Tetrate Agent Router Enterprise: in-VPC or on-prem, Envoy AI Gateway based, inline PHI redaction, identity per request, unified audit — [Tetrate](https://tetrate.io/learn/ai/hipaa-ai-gateway-healthcare)
- MintMCP (now Mintive): agent/MCP gateway claiming HIPAA compliance with BAA — [MintMCP healthcare gateways](https://www.mintmcp.com/blog/agent-gateways-healthcare-organizations)
- YC: no YC company found whose core product is PHI redaction for LLMs. Adjacent: Clicks Health (F2025, RCM agents with built-in HIPAA compliance), Adentris (real-time documentation/coding compliance), Verifiable (S2020, listed under healthcare compliance) — [YC Adentris](https://www.ycombinator.com/companies/adentris); [YC healthcare IT directory](https://www.ycombinator.com/companies/industry/healthcare-it)
- Academic: "Towards a HIPAA Compliant Agentic AI System in Healthcare" (2025) uses regex + BERT hybrid PHI redaction inside an agent framework, claims expert-determination alignment; follow-up ACM paper redacts before and after inference (defense in depth) — [arXiv 2504.17669](https://arxiv.org/pdf/2504.17669); [ACM](https://dl.acm.org/doi/full/10.1145/3786335.3813175)

### Inferences
- Two market layers exist with a gap between them: (a) governance/registry/risk platforms that inventory AI and manage policy but are not in the message path (Credo, Censinet, Qualified Health); (b) inline gateways that redact but do not reason about HIPAA (minimum necessary, permitted purpose) and do not score themselves. Axon's design (Tier-1 redaction + LLM HIPAA/Compliance judges + per-trace audit) sits between them.
- CHAI's assurance-lab difficulties suggest third-party "certification" is not yet a reliable buying trigger; a vendor that ships its own reproducible eval numbers can fill that trust gap.

### Gaps
- Holistic AI, Fairly AI, Hippocratic AI safety, Aidoc governance (CARE / aiOS), Vanta/Drata HIPAA modules not researched (call budget).
- No funding or customer data for Redact-Proxy, nRouter, Concentrate, MintMCP.
- Credo AI and Censinet funding not found in this pass.

## 4. Gaps in the market: agent-to-agent traffic, self-hosting, HIPAA-retention audit, measurable recall

### Takeaway
Agent/MCP gateways (SentinelOne, Lasso, Runlayer, PointGuard, Mintive) cover agent-to-tool traffic generically; no source described a healthcare-specific product that gates agent-to-agent (A2A) messages with HIPAA judgement. Self-hosting is offered by Tetrate, Presidio, JSL and Limina. No vendor found publishes blind-holdout PHI recall for its live gateway, or ties audit records explicitly to HIPAA's six-year documentation retention.

### Cited Findings
- No sources describe healthcare-specific multi-agent (agent-to-agent) security products; no healthcare A2A security funding round found — [Check Point agentic roundup](https://www.checkpoint.com/cyber-hub/cyber-security/what-is-ai-security/what-is-agentic-ai-security/top-agentic-ai-security-solutions-in-2026/); [MintMCP](https://www.mintmcp.com/blog/agent-gateways-healthcare-organizations)
- CSA AIUC-1 Q2 2026 refresh added MCP and A2A protocol security controls (authentication, transport security, message integrity, runtime containment) — [CSA research note](https://labs.cloudsecurityalliance.org/research/csa-research-note-aiuc1-agentic-ai-security-standard-q2-2026/)
- Response-side filtering matters: an LLM can surface PHI by inferring, combining or echoing retrieved context — [Tetrate](https://tetrate.io/learn/ai/hipaa-ai-gateway-healthcare)
- Self-hosted/in-VPC options: Tetrate (VPC/on-prem); Presidio (self-hosted, MIT); phi-redactor (open source, hash-chained audit log) — [Tetrate](https://tetrate.io/learn/ai/hipaa-ai-gateway-healthcare); [Beri.net](https://www.beri.net/article/pii-redaction-pricing-comprehend-azure-google-presidio-cost-per-million-characters); [GitHub phi-redactor](https://github.com/DilawarShafiq/phi-redactor)
- Limina offers regional/enterprise deployment options — [Eden AI](https://www.edenai.co/post/best-document-redaction-apis)

### Inferences
- Differentiation candidates for Axon: (1) A2A-native gating (each department-to-department hop gated, both request and reply legs); (2) fully self-hosted including judge LLMs (no PHI leaves the network, not even to a BAA-covered cloud model); (3) per-trace immutable audit stream designed for HIPAA retention and incident records; (4) published, blind-holdout recall AND over-redaction ("clinical text damage") numbers, which no vendor found reports; (5) judges decide, only deterministic Tier-1 redacts — a safety story against LLM rewrite leakage.
- Risk: big security platforms (Palo Alto Prisma AIRS, SentinelOne, Check Point) can add "HIPAA templates" quickly; the moat must be clinical-specific accuracy, eval evidence, and A2A audit semantics rather than generic redaction.

### Gaps
- Not verified whether any vendor explicitly markets 6-year HIPAA audit retention for LLM traffic logs.
- No independent comparison of gateways on agent-to-agent traffic exists in sources found.

## 5. Benchmark context: what typical PHI de-identification recall looks like (to place an 83% holdout recall)

### Takeaway
On the standard i2b2 2014 corpus, the best 2014 challenge system scored 0.936 strict micro F1, and modern commercial tools claim 0.96-0.98 F1 with recall near 0.98. Human single annotators average about 0.81 recall. Out-of-the-box Presidio on real clinical notes reached 0.74-0.81 recall. An 83% blind-holdout recall is roughly at single-human / tuned-open-source level, above out-of-box Presidio and frontier-LLM contact detection, but well below commercial clinical de-id claims; recall is the HIPAA-critical number.

### Cited Findings
- 2014 i2b2/UTHealth shared task: 10 teams, 22 submissions; best micro F1 0.936 (strictest metric); three systems above 0.90; best systems combined CRFs with hand-written rules (older than 2024, flagged) — [PMC4989908 (Stubbs et al. 2015)](https://pmc.ncbi.nlm.nih.gov/articles/PMC4989908)
- Another paper on same corpus reports max 0.964 entity-based micro F1, mean 0.872 across systems (different evaluation setting) — [PMC4988860](https://pmc.ncbi.nlm.nih.gov/articles/PMC4988860)
- Human baselines: Neamatullah et al. 2008, 14 clinicians, recall 0.63-0.94, single annotator average 0.81, two-annotator consensus 0.94; Stubbs & Uzuner 2015 annotators averaged 0.93 token F1; 95% F1 on i2b2 2014 treated as equivalent to manual de-id (Yogarajan 2020) — summarized in [JSL benchmarks 2026](https://www.johnsnowlabs.com/clinical-de-identification-benchmarks-2026-john-snow-labs-against-openai-databricks-presidio-and-llm-apis/)
- Commercial: JSL 0.98 F1 on i2b2 2014 test, 0.98 recall on its private corpus (vendor); AWS Comprehend Medical 0.94-0.96 F1 on 100 i2b2 notes; Azure 0.72-0.81; GCP 0.64 — [JSL benchmarks 2026](https://www.johnsnowlabs.com/clinical-de-identification-benchmarks-2026-john-snow-labs-against-openai-databricks-presidio-and-llm-apis/); [arXiv 2312.08495](https://arxiv.org/pdf/2312.08495)
- Open source: Presidio recall 0.74 (2025 UK neuro, P 0.51) and 0.81 strict / 0.90 relaxed (2022 oncology); Philter recall 0.79 at precision 0.35 — [JSL benchmarks 2026](https://www.johnsnowlabs.com/clinical-de-identification-benchmarks-2026-john-snow-labs-against-openai-databricks-presidio-and-llm-apis/)
- LLM/new entrants: OpenAI Privacy Filter recall 0.64 (vendor-run by JSL); frontier LLM PHI F1 0.86-0.91 — [JSL benchmarks 2026](https://www.johnsnowlabs.com/clinical-de-identification-benchmarks-2026-john-snow-labs-against-openai-databricks-presidio-and-llm-apis/)

### Inferences
- Axon's 83% is on a self-written, blind, small holdout of LLM-traffic messages, not i2b2 discharge summaries; corpora differ, so comparisons are directional only. Still, to be credible against JSL/AWS claims, a target of 0.95+ recall on a blind set (and ideally a run on i2b2 2014 test under a data-use agreement) would be needed.
- Strict vs relaxed scoring swings Presidio from 0.81 to 0.90 recall; Axon should state which it uses.
- Pairing recall with a "clinical text damage" metric is unusual and a differentiator, since precision-only numbers hide over-redaction of doses and drug names.

### Gaps
- Top 2014 i2b2 system's recall (separate from F1) not found.
- No independent (non-vendor) head-to-head of Limina vs JSL vs AWS on the same corpus found.
