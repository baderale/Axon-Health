# Seed Funding Landscape and Fundraising Odds: Solo-Founder Healthcare AI Gatekeeper (PHI redaction + AI compliance judges + audit trail)

Research date: 2026-11-11. US focus. Many pages in this space are secondary blogs or vendor marketing; source quality is flagged inline. Carta pages returned HTTP 403 to direct fetch, so Carta figures below come from search snippets of Carta pages, not full reads.

## 1. Comparable pre-seed/seed rounds (2024-2026): healthcare AI infra, AI security/guardrails, AI governance, PHI/de-identification

### Takeaway
AI agent security/governance is one of the hottest seed categories of late 2026: horizontal seeds cluster at $4.5M-$8.6M, Series A at $20M-$40M. Healthcare-specific AI governance has one breakout comp (Qualified Health: $5M seed 2024 -> $125M Series B 2026), but I found no 2025-2026 seed for a pure healthcare PHI-redaction/LLM-gateway company, which means both "open lane" and "unproven as standalone venture category".

### Cited Findings
**Horizontal AI agent security/governance (Sep-Nov 2026, from an aggregator tracker; verify against press releases)** — [NewMarketPitch AI governance funding news](https://newmarketpitch.com/blogs/news/ai-governance-funding-news)
- Mintive, $7M seed (29 Oct 2026), led by Cowboy Ventures; Operator Collective, Burst Capital; existing Coatue, Hustle Fund, Maven. Scoped revocable credentials per agent, logs actions through gateways (closest architectural analog to a gateway + audit trail).
- Asymptote Labs, $5.5M seed (20 Oct 2026), led by Tower Research Ventures; Lytical, 1984 Ventures, South Park Commons. Agent runtime infra with policy guardrails.
- Beltic, $7.3M seed (30 Sep 2026), led by Norwest.
- AI Score, $5.4M seed (3 Sep 2026), led by Fuel Ventures. AI governance: inventory, controls, audit visibility.
- Eve Security, $4.5M seed extension (15 Sep 2026).
- Later stage in same window: WhiteMatter $20M Series A (Blumberg; customer Sentara Health), Pluto Security ~$34M A (Jump Capital; customer Oscar Health), Rein Security $25M A, Raindrop $35M A (CRV), AIUC $40M A, Lasso Security $30M A, Harmonic Security $50M B, HiddenLayer $100M B, Opsin $21M.
- Same tracker notes no pre-seed rounds listed and no company described as health-focused; healthcare appears only as customer vertical (Sentara, Oscar).
- Guardrail Technologies $3M seed (Oct 2026), general AI-agent control — [Dealroom](https://dealroom.co/news/160457-guardrail-technologies-raises-3m-seed-to-keep-enterprises-in-control-of/)
- Iridius $8.6M seed (Apr 2026), compliance-by-design AI; Modicus Prime $4.5M additional seed (May 2026), pharma AI compliance/audit readiness; ALIGNMT AI $6.5M seed (Aug 2025), healthcare-specific AI governance (risk monitoring, compliance workflows, audit-ready reporting); Alinia AI $7.5M seed (Dec 2025), real-time guardrails — via search summaries of [NewMarketPitch funding analysis](https://newmarketpitch.com/blogs/news/ai-governance-funding-analysis) and [AI Safety Funding Tracker](https://newmarketpitch.com/blogs/news/ai-safety-list-deals) (aggregator; round labels inconsistent).

**Healthcare AI governance / infra**
- Qualified Health (health-system AI governance/orchestration): ~$5M seed Apr 2024 (SignalFire-led per some reports), $25M Series A Aug 2024 (announced Jan 2025 as $30M combined; investors incl. SignalFire, Frist Cressey, Town Hall, Healthier Capital, Intermountain Ventures, Flare Capital), $125M Series B Mar 2026 led by NEA with Transformation Capital, GreatPoint, Cathay Innovation, Anthology (Anthropic/Menlo); ~$155M total. Says new capital funds "governance, monitoring, and infrastructure required for mission-critical AI in healthcare" — [Fierce Healthcare (Series B)](https://fiercehealthcare.com/ai-and-machine-learning/qualified-health-locks-125m-fresh-funding-scale-ai-health-systems); [Fierce Healthcare (launch $30M)](https://www.fiercehealthcare.com/ai-and-machine-learning/new-startup-qualified-health-aims-build-infrastructure-generative-ai-armed); [Axios Pro](https://www.axios.com/pro/health-tech-deals/2026/03/12/qualified-health-series-a-100m); [Healthcare IT Today](https://www.healthcareittoday.com/2026/04/09/qualified-health-raises-125m-series-b-avo-raises-10-million-series-a/). Sources conflict on round labels (Axios called it a ~$100M Series A).
- Alterra Labs $12.5M seed (Nov 2026), led by Oak HC/FT; simulated medical environments to test/train medical AI — [Fortune](https://fortune.com/2026/11/10/alterra-labs-12-5-million-seed-round-training-environments-medical-ai)

**PHI / de-identification**
- Integral ~$7M seed (Sep 2023, OLDER), automated de-identification + compliance certification for datasets; led by Haystack, The General Partnership, Virtue Ventures — [MedCity News](https://medcitynews.com/2023/09/data-privacy-healthcare/)
- Limina (formerly Private AI): de-identifies clinical notes and ambient-listening data; Series A stage; targets re-identification risk below 0.04% — [HLTH podcast](https://hlth.com/insights/podcasts/how-limina-is-making-sensitive-health-data-safe-for-ai)
- BioStack $9.5M seed led by Peak XV, de-identified linked clinical records for AI/biotech (single-source; date unconfirmed) — [TechRound](https://techround.co.uk/artificial-intelligence/your-patient-records-could-become-ai-training-data-what-do-privacy-rules-say-about-de-identified-health-data/)
- Direct product competitors (healthcare LLM gateway with PHI redaction) exist: Scrub AI (redacts PHI before ChatGPT/Claude/Gemini; states no system catches 100% of PHI) — [scrub.health](https://scrub.health/); nRouter Cortex PHI redaction gateway — [nrouter.ai](https://nrouter.ai/solutions/healthcare); Maxim Bifrost healthcare gateway — [getmaxim.ai](https://getmaxim.ai/bifrost/industry-pages/healthcare-life-sciences); Tetrate HIPAA AI gateway — [tetrate.io](https://tetrate.io/learn/ai/hipaa-ai-gateway-healthcare); Concentrate (PHI redaction + BAA routes) — [concentrate.ai](https://concentrate.ai/). Funding for these not found.

### Inferences
- A plausible "good outcome" comp set for a healthcare AI gatekeeper seed is $3M-$7M (horizontal agent-security seeds), with healthcare compliance angle as differentiator. Qualified Health shows the healthcare-governance category can scale fast once health-system buyers adopt.
- Many horizontal agent-security players (Harmonic, Pluto, WhiteMatter) already sell into health systems/payers; investors will ask "why won't a horizontal AI-security vendor add a HIPAA module?" Healthcare-specific judges, Safe Harbor coverage and audit trail need to be the answer.
- Competing commodity PHI-redaction gateways mean 83% holdout recall alone is not a moat; benchmarks vs Presidio/commercial tools would matter.

### Gaps
- No YC 2025-2026 batch company found that is specifically a healthcare PHI-redaction/LLM gateway (search of directory not done; YC directory with W26/S26/X25 + "HIPAA" filter recommended).
- Valuations for the seed comps above not disclosed in sources.
- Funding history for Scrub AI, nRouter, Concentrate not found.

## 2. Median pre-seed/seed round sizes and valuations; healthcare funding trends (2025-2026)

### Takeaway
Pre-seed checks are at record highs (avg SAFE $276K in Q2 2026); priced seed medians are roughly $3M at ~$15-18M pre-money. Digital health VC is up (H1 2026 $7.4B, median deal $14M) but highly concentrated in mega-rounds and AI.

### Cited Findings
- Carta Q2 2026 pre-seed: $3.19B raised across 11,500+ SAFEs/notes in the US; average instrument $276K (record high); ~91% of SAFEs post-money — [Carta State of Pre-Seed Q2 2026](https://carta.com/data/state-of-pre-seed-q2-2026/) (via search snippet; full page 403)
- Carta reports pre-seed SAFE valuation caps "keep getting bigger" in Q2 2026 — [Carta](https://carta.com/data/safe-valuation-caps-q2-2026/) (figures not retrieved)
- Carta Q2 2025: median pre-money on primary seed rounds $15.6M, then a record — [Carta Q2 2025 State of Private Markets](https://carta.com/sg/en/data/state-of-private-markets-q2-2025-full-report/) (2025 data)
- PitchBook-NVCA Q1 2026: median seed pre-money $18.4M, median round $3.0M — cited by [Causo H1 2026 seed report](https://hub.causo.ai/guides/h1-2026-state-of-seed-report) (secondary; NOT verified against PitchBook)
- Rock Health H1 2026: US digital health $7.4B across 244 deals (vs $6.4B/245 H1 2025); Q1 $4.2B, Q2 $3.2B; 20 rounds of $100M+ took 45% of capital; median deal $14M (up from $12M in 2025); 115 acquisitions; no digital health IPO yet in 2026; Rock Health stopped tagging AI as distinct because it is ubiquitous — [Rock Health H1 2026](https://rockhealth.com/insights/h1-2026-funding-and-market-overview/); [Healthcare Dive](https://healthcaredive.com/news/digital-health-funding-first-half-2026-rock-health/825215/); [HIT Consultant](https://hitconsultant.net/2026/07/13/rock-health-h1-2026-digital-health-funding-report/)
- Health Management Solutions: $5.6B in 2025, 83% to AI ventures; procurement teams are now product gatekeepers for health system contracts — [Galen Growth](https://www.galengrowth.com/investor-thesis-health-management-solutions-funding-2026/)
- 2026 healthcare VC described as "flight to quality", favoring AI integration — [HIT Consultant Jan 2026](https://hitconsultant.net/2026/01/09/the-flight-to-quality-why-2026-healthcare-vc-is-betting-on-ai-integration-over-innovation/)

### Inferences
- Rock Health's $14M median deal is across all stages and inflated by later rounds; not a seed benchmark.
- Capital concentration (45% in 20 rounds) means a pre-revenue solo founder competes for a shrinking slice of non-mega capital; generic pre-seed SAFE ($250K-$1M) is the realistic first check.

### Gaps
- Carta Q2/Q3 2026 seed medians (round size, pre-money) not retrieved due to 403; Carta healthcare-specific seed medians not found.
- Rock Health Q3 2026 data not searched.

## 3. Y Combinator and other accelerators

### Takeaway
YC: $500K standard deal (7% for $125K + $375K uncapped MFN SAFE), four batches/year since 2025, acceptance under ~1-2% (unofficial), solo founders ~11% of W26. Alternatives: a16z speedrun ($500K for 10%, plus up to $500K follow-on), Techstars ($220K for 5% in many cities), Cedars-Sinai (~$100K).

### Cited Findings
- YC deal: $500K committed at acceptance; $125K post-money SAFE for fixed 7%; $375K uncapped MFN SAFE converting on lowest-cap SAFE terms issued between batch start and priced round (example: $15M post cap -> 2.5%); pro rata right; no fees; invests in US, Canada, Cayman, Singapore corps — [YC Deal page](https://www.ycombinator.com/deal)
- YC moved from two to four batches per year starting 2025, total companies per year roughly unchanged — [search summary of TechCrunch](https://techcrunch.com/?p=2255659) (secondary summary)
- W27 application deadline reported as Nov 2, 2026 — [BuildMVPFast](https://www.buildmvpfast.com/blog/yc-w27-application-deadline-november-2-2026) (secondary)
- YC does not publish acceptance rates; one blog estimates ~1-1.5% for solo technical founders, ~0.2-0.4% solo non-technical (unofficial estimate) — [YC Insight](https://ycinsight.com/answers/yc-acceptance-rate); [Zyner](https://zyner.io/blog/yc-solo-founders)
- YC W26: 22 solo-founder companies of 199 (~11%); devtools 22% solo, fintech 0% — [Pancake blog](https://pancake.ai/blog/yc-w26-solo-founders), citing Extruct's breakdown (extruct.ai/research/ycw26/, not verified)
- YC 2026 Request for Startups includes vertical AI for healthcare and law — [YC Insight 2026 batch](https://ycinsight.com/yc-2026-batch) (secondary)
- a16z speedrun: $500K for 10% at entry plus $500K in next round within 18 months (up to $1M); no board seat; SR008 applications closed Nov 1, 2026, residency Feb 1-Apr 18, 2027 — [a16z SR008 post](https://a16z.com/applications-for-a16z-speedrun-sr008-are-now-open/); [Superscout](https://superscout.co/program/a16z-speedrun) (terms secondary; instrument SAFE vs common stock conflicts across sources); official [speedrun deal page](https://speedrun.a16z.com/the-deal)
- Techstars: $220K for 5% (Boston, Chicago, London); $120K for 6% (NYC, Anywhere) — [Slidebean](https://slidebean.com/startup-accelerator-program/y-combinator) (single aggregator; unverified)
- Cedars-Sinai Accelerator: ~$100K per company, 3-month LA program, access to 300+ clinicians/executives; Cedars-Sinai Technology Ventures made a $1.4M strategic investment in an Accelerator+ company (Mar 2026) — [Becker's](https://www.beckershospitalreview.com/healthcare-information-technology/digital-health/cedars-sinai-to-invest-1m-in-10-startups/); [Startup Luxembourg](https://startupluxembourg.com/news/exobiosphere-joins-cedars-sinai-accelerator-with-$1-4m) (terms may be dated)

### Inferences
- YC's healthcare-AI RFS and comfort with solo technical founders (11% of W26) make YC the single highest-leverage application; with the next deadline past (W27 Nov 2), the following batch (likely Spring 2027) is the target.
- Health-system accelerators (Cedars-Sinai, Mayo) are less about money and more about a design partner and pilot data, which directly addresses the "no customers" gap.

### Gaps
- No verified data on Rock Health, StartX, Plug and Play Health, Mayo Clinic Platform_Accelerate, AWS Activate or NVIDIA Inception terms (not reached within search budget). Known general facts (AWS Activate up to ~$100K credits; NVIDIA Inception is non-equity) were not verified this session.
- No examples found of solo-founder YC healthcare companies.

## 4. Probability data: raising rates, conversion, solo vs team, traction effect

### Takeaway
Solo founders are ~36% of new startups but only ~17-20% of funded ones and ~15% of priced-round cash. Seed-to-Series-A graduation within 2 years fell from ~26-31% (2018 cohort) to ~15% (2022 cohort). No reliable stat quantifies how LOIs/pilots change odds.

### Cited Findings
- Solo-founder share of new US startups: 23.7% (2019) -> 36.3% (H1 2025) — [Carta Solo Founders Report 2025](https://carta.com/data/solo-founders-report) (search snippet)
- Of startups founded 2024: solo-led were 30% of cohort but received 14.7% of cash raised in priced equity rounds — [Carta Solo Founders Report 2025](https://carta.com/data/solo-founders-report)
- Of 2024-founded startups on Carta that raised capital, ~17% had a solo founder — [Carta Founder Ownership Report 2025](https://carta.com/uk/en/data/founder-ownership/); same 17% cited from Carta Winter 2025 State of Seed — [SaaStr](https://www.saastr.com/the-state-of-seed-today-10-key-learnings-from-cartas-latest-data)
- ~36% of startups founded on Carta in 2025 were solo-led (up from 31% in 2024); among VC-backed companies that drops to ~20% — [Carta Founder Ownership 2026](https://carta.com/data/founder-ownership-2026/); [Sierra Ventures interview with Carta's Peter Walker](https://www.sierraventures.com/ascend/what-the-data-actually-says-about-pre-seed-right-now-with-peter-walker)
- Note: Carta reports use different cohort definitions, so 30/31/35/36% are not directly comparable (flag).
- Seed -> Series A within 2 years: 25.9% for Q2 2018 priced-seed cohort (Carta); others cite 30.6% (2018) and 15.4% (2022 cohort); median seed-to-A interval 616 days in Q2 2025 (down from 774 in Q4 2024); decline across all sectors incl. biotech — [Carta graduation rates](https://carta.com/data/linkedin-seed-to-series-a-graduation-rates/); [Carta: hard in every sector](https://carta.com/data/linkedin-seed-to-series-a-hard-in-every-sector/); [The 15% Truth](https://hsep.substack.com/p/the-15-truth)

### Inferences
- Rough relative odds: solo founders are ~36% of new startups but ~17-20% of funded ones, implying a solo founder is roughly half as likely to raise as the average startup (inference from ratios, not a measured conversion rate).
- Absolute probability that a given pre-revenue solo founder raises an institutional seed is not measurable from public data; single-digit-to-low-teens percent is a reasonable prior, rising materially with a YC/speedrun admit, a technical co-founder, or a paid pilot (judgment, not cited).
- In healthcare, investors weigh distribution: a signed design partner/LOI from a health system or digital-health company handling PHI is likely the single biggest odds lever (consistent with Galen Growth's point that procurement teams are the gatekeepers).

### Gaps
- No public data on the share of all applicants/pitching founders who raise a seed.
- No reliable quantitative data on pre-revenue vs LOI/pilot fundraising success rates.
- No Carta solo-founder data broken out for healthcare.
- Reddit r/startups / r/ycombinator anecdotes not collected.

## 5. Non-dilutive options

### Takeaway
SBIR/STTR is back (reauthorized Apr 13, 2026 through Sep 30, 2031 after a ~6-month lapse); NIH Phase I is ~$314K-$336K, Phase II ~$2.15M. A health-AI privacy/PHI tool fits NIH (e.g., NLM/NCATS-type topics) and NSF SBIR.

### Cited Findings
- SBIR/STTR authority lapsed Oct 1, 2025; restored by Public Law 119-83 on Apr 13, 2026, through Sep 30, 2031 — [GrantProbe NIH SBIR 2026](https://grantprobe.com/articles/nih-sbir-sttr-grants-2026); [GovDash](https://www.govdash.com/blog/sbir-funding-guide) (secondary)
- NIH Phase I guideline $323,090, Phase II $2,153,927; older guides cite $314,363 cap; one source says SBA raised Phase I to $335,937 from Oct 16, 2026 (single-source, unconfirmed) — [GrantProbe](https://grantprobe.com/articles/nih-sbir-sttr-grants-2026); [GrantProbe Phase I](https://grantprobe.com/articles/sbir-phase-i-2026); [Precision Federal](https://precisionfederal.com/resources/sbir-phase-i-guide)
- NIH standard due dates (PA-27-100): Sep 5, 2026; Jan 5, 2027; Apr 5, 2027 — [GrantProbe](https://grantprobe.com/articles/nih-sbir-sttr-grants-2026) (verify on grants.nih.gov)

### Inferences
- Jan 5, 2027 NIH deadline is the nearest realistic SBIR target; awards typically land ~6-9 months after submission (general knowledge, not verified this session), so SBIR is a 2027 bridge, not immediate runway.
- An SBIR Phase I paired with a health-system research partner also manufactures the "validation" evidence investors want.

### Gaps
- NSF SBIR current amounts/status, ARPA-H open solicitations relevant to AI privacy, and cloud credit programs (AWS Activate, Google for Startups, Microsoft Founders Hub, NVIDIA Inception) not verified this session.

## 6. Capital needs for 18-24 months

### Takeaway
Compliance artifacts are a real line item: SOC 2 Type II roughly $20K-$110K first year, HITRUST r2 roughly $60K-$160K+ (plus interim/recurring). A lean solo-plus-2 team for 18-24 months likely needs ~$1.5M-$3M; a typical $3M seed fits.

### Cited Findings
- SOC 2 first engagement for startups $30K-$110K — [Agency blog](https://blog.getagency.com/articles/soc-2-audit-cost-for-startups); auditor fees $20K-$40K for <50 employees — [Scrut](https://www.scrut.io/soc-2/cost-of-soc-2-audit); Drata models a 25-person startup at ~$28K first-year total — [Drata](https://drata.com/blog/soc-2-audit-cost); low-end $7K-$15K audit fees — [Klaay](https://www.klaay.com/blog/soc-2-compliance-cost-2026). Type II requires an observation window (often 3-6 months) — [Beancount](https://beancount.io/blog/2026/05/11/soc-2-type-ii-saas-startups-trust-services-criteria-audit-cost-six-month-observation-window-first-examination-guide). All vendor-sourced (conflict of interest).
- HITRUST r2: total $70K-$160K incl. assessor, HITRUST fee, MyCSF — [Accountable HQ](https://www.accountablehq.com/post/hitrust-certification-cost-in-2026-price-ranges-key-factors-and-how-to-budget); $60K-$150K — [Sprinto](https://sprinto.com/blog/hitrust-certification-cost/); assessor fees $60K-$250K+ — [SecurityMetrics](https://www.securitymetrics.com/blog/calculating-your-hitrust-cost); r2 requires interim assessment at one year — [Accountable HQ r2](https://www.accountablehq.com/post/hitrust-r2-assessment-requirements-process-timeline-and-cost)

### Inferences (budget sketch, not cited)
- Illustrative 24-month plan: founder + 2 engineers (~$450K-$600K/yr loaded) = ~$0.9M-$1.2M; GTM/clinical-compliance advisor or hire ~$0.2M-$0.4M; SOC 2 Type II + HIPAA program ~$50K-$100K; HITRUST e1/i1 or r2 when a large health system demands it ~$60K-$160K; legal (BAA templates, incorporation, IP, regulatory counsel) ~$50K-$100K; cloud/GPU for judge models (a 35B judge needs a GPU instance; credits can offset) ~$50K-$200K; insurance (cyber/E&O, which health systems require) ~$20K-$50K. Total ~$1.5M-$2.5M; ~$3M gives buffer. Salary and cloud figures are my estimates, not sourced.
- Sequencing: SOC 2 Type I/Type II first (most digital-health buyers accept it); HITRUST only when a hospital buyer requires it (per SMB guidance that HITRUST is customer-driven — [Hudson Valley compliance blog](https://sm911.github.io/compliance-blog/healthcare/hitrust-csf-healthcare-smbs.html)).

### Gaps
- No sourced 2026 salary benchmarks or GPU cost figures gathered.
- HIPAA-specific program costs (risk assessment, policies) not separately sourced.

## 7. Investors backing healthcare AI security/governance; public theses

### Takeaway
Confirmed active: Oak HC/FT (Alterra seed), SignalFire, Flare Capital, Frist Cressey, Town Hall, Intermountain Ventures, NEA, Transformation Capital, Anthology fund (Qualified Health); horizontal AI security seeds from Cowboy, Norwest, Tower Research, South Park Commons, 1984 Ventures, Hustle Fund, Operator Collective. Giant Ventures publicly names "AI governance and deployment" in its 2026 US healthcare pre-seed/seed thesis.

### Cited Findings
- Giant Ventures 2026 US Healthcare Thesis: especially interested in AI governance and deployment, payment integrity, provider data/credentialing, pharmacy infra; focus pre-seed to seed — [Giant Ventures](https://www.giant.vc/notebook/call-for-startups-our-2026-us-healthcare-thesis)
- Qualified Health investors (governance/monitoring for health-system AI): SignalFire, Frist Cressey Ventures, Town Hall Ventures, Healthier Capital, Intermountain Ventures, Flare Capital (seed/A); NEA (lead B), Transformation Capital, GreatPoint, Cathay Innovation, Anthology — [Fierce Healthcare](https://fiercehealthcare.com/ai-and-machine-learning/qualified-health-locks-125m-fresh-funding-scale-ai-health-systems); [Healthcare IT Today](https://www.healthcareittoday.com/2026/04/09/qualified-health-raises-125m-series-b-avo-raises-10-million-series-a/)
- Oak HC/FT led Alterra Labs' $12.5M seed (medical AI testing) — [Fortune](https://fortune.com/2026/11/10/alterra-labs-12-5-million-seed-round-training-environments-medical-ai)
- Horizontal AI security seed leads (Sep-Oct 2026): Cowboy Ventures (Mintive), Norwest (Beltic), Tower Research Ventures (Asymptote; with South Park Commons, 1984 Ventures), Fuel Ventures (AI Score) — [NewMarketPitch](https://newmarketpitch.com/blogs/news/ai-governance-funding-news)
- EU AI Act high-risk enforcement from March 2026 cited as a "binary filter" for HealthTech AI investment, favoring explainable systems — [healthcare.digital](https://www.healthcare.digital/single-post/european-healthtech-and-medtech-venture-capital-outlook-2026) (EU-focused)
- Health-system procurement teams as product gatekeepers — [Galen Growth](https://www.galengrowth.com/investor-thesis-health-management-solutions-funding-2026/)

### Inferences
- Best-fit target list: healthcare seed specialists that backed Qualified Health (SignalFire, Flare, Frist Cressey, Town Hall, Intermountain Ventures as strategic) plus Oak HC/FT, Giant Ventures (explicit thesis), and horizontal AI-security seed funds (Cowboy, South Park Commons, 1984, Hustle Fund) for a "healthcare wedge of agent security" pitch.
- Health-system venture arms (Intermountain, Cedars-Sinai Technology Ventures) double as design partners.

### Gaps
- No public theses found from General Catalyst, a16z Bio+Health, 7wireVentures, Define Ventures, Lux or Bessemer specifically on "AI governance in healthcare" (one search returned nothing; not exhaustively checked).
- Flare Capital's role in Qualified Health's 2026 round is conflicting (Galen lists Flare; others list NEA as lead).
