# AI Job Source Agent – Part 2 Take-Home Challenge

Hey! This is my implementation of the **AI Job Source agent** for Jobnova’s take-home challenge.

The goal was to build an agent that can start from a LinkedIn company page and automatically discover a company’s career page + one open job posting.

## What It Does

1. Takes a LinkedIn company URL (or company name + website)
2. Extracts the official company website using a third-party LinkedIn enrichment API
3. Intelligently finds the most relevant career/jobs page on the company website
4. Pulls one open position URL from the career page
5. Returns everything in a clean, structured format

The agent includes fallback logic, domain validation, and scoring so it works reasonably well even on messy company sites.

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

### Get an Apify Token (Recommended)

1. Sign up at [apify.com](https://apify.com) (free tier is enough)
2. Go to Settings → API tokens and create one
3. Add it to your `.env` file as `APIFY_API_TOKEN=...`

### Run It

**Using LinkedIn (recommended):**

```bash
python main.py --linkedin-url "https://www.linkedin.com/company/stripe" --mock
```

Remove `--mock` once you have a real token.

**Direct mode (for testing):**

```bash
python main.py --company-name "OpenAI" --company-url "https://openai.com"
```

## Key Features

- Starts from LinkedIn (bypasses direct LinkedIn scraping issues)
- Uses Apify for reliable company data extraction
- Smart career page detection with scoring + validation
- Common path fallbacks (`/careers`, `/jobs`, etc.)
- Clean separation of concerns (crawler, validator, scoring, agent)
- Full test suite (16 tests passing)
- Mock mode for easy development and demo recording

## Project Structure

```
job-source-agent/
├── main.py                 # CLI entrypoint
├── src/
│   ├── agent.py            # Main orchestration logic
│   ├── crawler.py          # Playwright-based link extraction
│   ├── linkedin_parser.py  # Apify integration + mock mode
│   ├── validator.py        # Domain & ATS validation
│   ├── scoring.py          # Keyword-based link scoring
│   ├── schemas.py          # Data models
└── tests/                  # Pytest suite (16 tests)
```

## Testing

All core logic is covered by tests:

```bash
pytest tests/ -v
```

Currently **16/16 tests passing**.

## Why I Built It This Way

- Used a third-party LinkedIn API instead of trying to scrape LinkedIn directly (more reliable + avoids blocks)
- Kept the web crawling logic simple but added validation and scoring so it’s not too brittle
- Added mock mode so I could develop and record demos without burning API credits
- Wrote tests early so I could refactor confidently

## Future Improvements (If I Had More Time)

- Add LLM-based link ranking instead of pure keyword scoring
- Support more LinkedIn input types (job listing pages directly)
- Better error messages and retry logic on flaky company sites

---

Thanks for checking it out! This was a fun challenge and I learned a lot building it.
