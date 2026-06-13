# AI Job Source Agent (Part 2 - Jobnova Take-Home)

Production-ready implementation of the **AI Job Source agent** for the Jobnova AI Engineer take-home challenge.

## Features
- Starts from **LinkedIn company page** (or direct company name + website)
- Uses reliable third-party LinkedIn data (Apify) to bypass LinkedIn blocking
- Intelligent web agent finds career page → extracts one open position URL
- Clean output in the exact format requested by the challenge
- Mock mode for testing without spending API credits
- Solid validation + scoring logic

## Quick Start

### 1. Setup
```bash
git clone https://github.com/lupenox/job-source-agent.git
cd job-source-agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
```

### 2. Get Apify Token (Recommended)
1. Go to https://apify.com and sign up (free)
2. Go to Settings → API tokens → Create new token
3. Paste it into `.env` as `APIFY_API_TOKEN=...`

You get starter credits — enough for many demo runs.

### 3. Run the Agent

**From LinkedIn (recommended for the challenge):**
```bash
python main.py --linkedin-url "https://www.linkedin.com/company/stripe" --mock
```

Remove `--mock` once you have a real token.

**Direct mode (for testing):**
```bash
python main.py --company-name "Stripe" --company-url "https://stripe.com"
```

### Output Example
```
======================================================================
AI JOB SOURCE AGENT - FINAL RESULT (Challenge Format)
======================================================================
Company Name       : Stripe
Career Page URL    : https://stripe.com/jobs
Open Position URL  : https://stripe.com/jobs/software-engineer-backend
======================================================================
```

## Architecture
- `main.py` — CLI entrypoint + LinkedIn ingestion
- `src/linkedin_parser.py` — Apify integration (with mock fallback)
- `src/agent.py` — Orchestrates career page + job discovery
- `src/crawler.py` — Playwright-based link extractor
- `src/validator.py` + `src/scoring.py` — Smart filtering

## Tips for Strong Demo Video
- Use `--mock` first to show the full happy path quickly
- Then run with real token on a real company
- Show both the clean challenge-format output and the rich JSON with evidence
- Mention that the LinkedIn step uses a compliant third-party API to avoid blocks

Good luck with the application! This should be a very solid submission for Part 2.
