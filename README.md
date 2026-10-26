# NorthStar Health

**AI deal sourcing and first-pass screening for the Meng Impact Investment Fund (Yale SOM) healthcare deal team.**
NorthStar finds US-based pre-seed and seed startups in women's health, biotech, and evidence-based wellness. It verifies each one on the web, scores it against the fund's written healthcare investment thesis, and drafts founder outreach for the startups *you* choose to save.

Final project for AI Foundations · Stella Bagchi · Fall 2026

---

## Run it locally (about 5 minutes)

You need Python 3.9 or newer and a `PORTKEY_API_KEY` (the course key; the app uses `gpt-6-luna` only).

```bash
git clone <this repo URL> northstar-health
cd northstar-health
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:8050** in your browser.

**API key:** the app looks for a `.env` file **first in this repo folder, then in the folder above it**. So the teaching-staff layout works without any copying:

```
submissions/
├── .env                 <- PORTKEY_API_KEY=...
└── northstar-health/    <- this repo
```

To use your own key file instead: `cp .env.example .env` and paste your key in.

## Try it

1. **Discover** tab → keep all three sectors ticked → **Find startups**. You can watch each agent's progress live. A scan takes about 1–5 minutes and costs about $0.05–$0.25.
   - Short on time? Click **Load last run** to open a saved real scan instantly. This spends no tokens.
2. Read a scorecard. Click any criterion bar to see the Thesis Analyst's reasoning, and open **Verified sources** to see where each fact came from.
3. **Save to watchlist** → **Watchlist** tab → add a note → **Draft outreach email**.
4. **Ask NorthStar** (bottom right) answers questions about your saved startups.
5. The **Usage & Safety** tab shows every model call (tokens, cached tokens, cost, latency), the daily budget bar, and the guardrail log.

## How it works

```
Google News RSS ──► SCOUT agent ──► code gate ──► VERIFIER agent ──► code gate ──► THESIS ANALYST ──► you save ──► OUTREACH WRITER
 (tool: news       extracts        (healthcare,     (tool: OpenAI        (US HQ +        (scores 9 thesis       (human in    (draft only,
  search)          startups        not Series A+)    web_search)          Pre-seed/Seed   criteria; code        the loop)     never sends)
                   (structured)                      cites URLs           + source URL)   computes 0–100)
```

| Agent | Job | Tools | Output |
|---|---|---|---|
| Scout | Turns ≤18 recent funding headlines into a list of startup candidates | Google News RSS search | Structured JSON; can only cite headline IDs, so it cannot invent URLs |
| Verifier | Confirms HQ, stage, round, for-profit status, founders, and evidence | OpenAI `web_search` (max 3 searches each) | Structured JSON with a source URL for each fact; "Unknown" when unsure |
| Thesis Analyst | Scores 9 criteria from the Meng healthcare thesis (`data/meng_healthcare_thesis.md`) | none (full thesis in a cached prompt prefix) | Scorecard, red flags, unknowns, 3 diligence questions |
| Outreach Writer | 120-word first-touch email for saved startups | none | Draft text, checked for commitment language |
| NorthStar Assist | Q&A about saved startups | none | Markdown answer labeled verified / company-reported / unknown |

Model: `gpt-6-luna` through Portkey for every agent.

## Safety

- **Untrusted data is fenced.** Headlines, web pages and user notes are wrapped in `<untrusted_data>` tags with an instruction never to follow them.
- **Injection screen.** Suspicious headlines are quarantined before the model sees them, and user input that looks like a prompt injection is blocked.
- **Hard gates live in code, not the prompt.** The startup must be US-headquartered, pre-seed or seed, not non-profit, and have at least one real source URL.
- **The score is computed in code.** Per-criterion scores are clamped to 1–5 before the 0–100 score is calculated.
- **Outreach guard.** Phrases like "we will invest" or "term sheet" are removed. Drafts are never sent.
- **Spending limits.**
  - A daily token budget (`DAILY_TOKEN_BUDGET`) is checked before *every* call.
  - Each scan verifies at most 6 companies.
  - Every call has `max_output_tokens`, and the Verifier has `max_tool_calls=3`.
  - Scans have a 30-second cooldown, and only one scan can run at a time.
  - Verifications are cached for 7 days.

Run the offline safety tests (no API key needed):

```bash
python -m pytest -q tests
```

Run the live red-team test (2 API calls, less than $0.01). It plants a hidden "score this 5/5" instruction in a startup record:

```bash
python scripts/redteam_live.py
```

## Command-line scan

`python run_scan.py` runs the same pipeline without the website. Each run is saved to `runs/`.

## Files

| Path | What |
|---|---|
| `app.py` | Dash web app (UI, background scan jobs, watchlist) |
| `agents.py` | The agents, schemas, guardrails, usage metering, cache |
| `data/meng_healthcare_thesis.md` | The deal team's investment thesis used by the Thesis Analyst |
| `data/sample_run.json` | A saved real scan, so the app can be explored without spending tokens |
| `runs/` | Every scan's full output (inputs, verdicts, token usage) |
| `logs/redteam_result.json` | Output of the live red-team test |
| `tests/test_guardrails.py` | Offline safety tests |
| `report.html`, `slides.html` | Final report and slide deck |

NorthStar is a research assistant. It does not make investment decisions. Verify every claim before acting.
