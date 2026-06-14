# AI Job Source Agent – Part 2 Take-Home Challenge

Hey! This is my implementation of the **AI Job Source agent** for Jobnova’s take-home challenge.

The goal was to build an agent that can start from a **LinkedIn job listing page** (or company page), extract the company’s official website, find their career page, and return one open job posting.

## What It Does

1. Accepts a LinkedIn job listing URL or company page URL
2. Extracts company name + official website (via Apify)
3. **Intelligently finds the best career page** using keyword scoring + **LLM reranking (Gemini)**
4. Extracts one open position URL from the career page
5. Returns everything cleanly (including exact challenge format string)

The agent includes retry logic, domain validation, scoring, common-path fallbacks, and graceful LLM fallback.

## LLM-Powered Career Page Ranking (New!)

When you provide a `GEMINI_API_KEY`, the agent uses **Gemini 1.5 Flash** to rerank the top keyword candidates and pick the single best careers page. This dramatically improves accuracy on companies with non-obvious career page links.

- Falls back gracefully to keyword scoring if no key or LLM fails
- You can disable it with `use_llm_reranker=False`

## Quick Start

```bash
git clone https://github.com/lupenox/job-source-agent.git
cd job-source-agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
```

### Required API Keys

1. **Apify** (for LinkedIn data)
   - Sign up at [apify.com](https://apify.com)
   - Add `APIFY_API_TOKEN` to `.env`

2. **Gemini** (recommended for best career page accuracy)
   - Get a free key at [aistudio.google.com](https://aistudio.google.com/app/apikey)
   - Add `GEMINI_API_KEY` to `.env`

### Run It

```bash
python main.py --linkedin-url "https://www.linkedin.com/jobs/view/1234567890"
```

With mock mode (no API calls):
```bash
python main.py --linkedin-url "https://www.linkedin.com/jobs/view/1234567890" --mock
```

## Key Features

- Supports both LinkedIn job listings and company pages
- Apify for reliable LinkedIn data (no direct scraping)
- **Keyword scoring + Gemini LLM reranking** for career page detection
- Retry logic on network calls
- Exact challenge output format via `result.to_challenge_format()`
- Full test suite + mock mode
- Clean, modular, production-minded code

## Project Structure

```
job-source-agent/
├── main.py
├── src/
│   ├── agent.py            # Main orchestration + LLM reranker
│   ├── crawler.py
│   ├── linkedin_parser.py
│   ├── validator.py
│   ├── scoring.py
│   ├── schemas.py
└── tests/
```

## Testing

```bash
pytest tests/ -v
```

All tests still pass.

## Why This Architecture

- Third-party API (Apify) instead of fragile LinkedIn scraping
- Hybrid keyword + LLM approach = fast + smart
- Built-in retries and fallbacks for reliability
- Easy to extend or integrate into larger agent systems

---

Thanks for checking it out!