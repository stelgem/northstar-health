# Research notes (gathered 2026-10-26)

## Model pricing — gpt-6-luna (official: https://developers.openai.com/api/docs/pricing)
- $0.10 / 1M input, $0.01 / 1M cached input, $0.50 / 1M output (≤272K context)
- web_search tool: $10 / 1K calls; search content tokens billed at model rates
- Comparison: gpt-5-mini $0.25 in / $2.00 out; gpt-5.4-mini $0.75 / $4.50

## Existing products (prices: third-party estimates unless noted)
| Product | What it does | Price | Gap vs NorthStar |
|---|---|---|---|
| PitchBook | Private-market deals/valuations DB | ~$12K–$40K+/user/yr (Vendr median ~$30K) | Expensive for a student fund; generic tags; thin pre-seed; no thesis/impact scoring |
| Crunchbase Pro/Business (+ Crunchbase AI) | Company/funding DB, AI search, alerts | ~$49–99/mo Pro; ~$199/mo Business | Self-reported, spotty pre-seed; no fund-thesis scoring or impact lens |
| CB Insights | Market maps, analyst research | ~$30K–$100K/yr | Corporate-strategy oriented, cost-prohibitive |
| Harmonic.ai | Stealth/early startup discovery from founder & hiring signals | Quote-only, Vendr median ~$36K/yr | Generic filters; no impact/women's-health rubric |
| Specter | Signal-based sourcing (talent, traffic, investor interest) | Not public | Raw signal feed; analysts still screen + write outreach manually |
| Affinity | Relationship-intelligence CRM | ~$2,000–2,700/user/yr | Manages known deals; no discovery or thesis scoring |
| Grata (Datasite) | AI search on private companies | Quote-only | PE/M&A focus, not pre-seed femtech/biotech |
| Tracxn | Sector-taxonomy startup DB incl. femtech | From ~$500/mo | Generic taxonomy; no custom thesis/impact rubric |
| Dealroom | Startup/ecosystem DB | €12,500/yr, 3 seats (official) | Europe-centric; expensive |
| Galen Growth / Rock Health | Digital-health databases & reports | Quote-only / reports | Market intelligence, not sourcing; no scoring/outreach |
| ChatGPT / Perplexity deep research | Ad hoc web research | ~$20/mo | Not repeatable; no rubric; can hallucinate startups; no pipeline |

Sources: vendr.com/marketplace/pitchbook, /harmonic-ai, /affinity; costbench.com (CB Insights); pipeline.zoominfo.com/sales/crunchbase-pricing; dealroom.co/pricing-usd; capterra.com/p/204090/Tracxn; tryspecter.com/features/vs-harmonic; tomba.io/blog/grata-pricing-reviews-pros-and-cons; vcbeast.com/affinity-crm-vc-pricing-features-comparison

## Motivation facts
- Rock Health: US digital health raised $14.2B across 482 deals in 2025, fewest deals since 2020 — https://rockhealth.com/rock-weekly/2025-year-end-funding-14-2b-raised-across-482-deals/
- Femtech 2024 funding estimates disagree: PitchBook $1.2B, Galen Growth $2.2B, SVB $2.6B — https://www.businesswire.com/news/home/20250609461378/en/Galen-Growth-Report-Reveals-Next-Chapter-for-Femtech-Growth-Gaps-and-New-Potential-in-Womens-Health
- Gompers et al. survey: VCs spend ~22 hrs/week networking & sourcing out of ~55-hr week — https://corpgov.law.harvard.edu/2019/08/20/how-do-venture-capitalists-make-decisions
- Acuity (2022): sourcing + due diligence ≈ 42% of VC time — https://acuitykp.com/blog/how-venture-capitalists-spend-their-time
