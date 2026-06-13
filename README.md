# AI Job Source Agent – Part 2 Take-Home Challenge

Hey! This is my implementation of the **AI Job Source agent** for Jobnova’s take-home challenge.

The goal was to build an agent that can start from a **LinkedIn job listing page** (or company page), extract the company’s official website, find their career page, and return one open job posting.

## What It Does

1. Accepts a LinkedIn job listing URL or company page URL
2. If given a job listing, it extracts the company name and LinkedIn company profile from the page
3. Enriches the company to get the official website using a third-party LinkedIn API
4. Intelligently finds the most relevant career/jobs page on the company website
5. Extracts one open position URL from the career page
6. Returns everything in a clean, structured format

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

**Using a LinkedIn job listing page (recommended):**

```bash
python main.py --linkedin-url "https://www.linkedin.com/jobs/view/1234567890" --mock
```

**Using a LinkedIn company page:**

```bash
python main.py --linkedin-url "https://www.linkedin.com/company/stripe" --mock
```

Remove `--mock` once you have a real token.

**Direct mode (for testing):**

```bash
python main.py --company-name "OpenAI" --company-url "https://openai.com"
```

## Key Features

- Supports both **LinkedIn job listing pages** and company pages
- Uses Apify for reliable company data extraction (avoids LinkedIn blocking)
- Smart career page detection with scoring + validation
- Common path fallbacks (`/careers`, `/jobs`, etc.)
- Clean separation of concerns
- Full test suite (16 tests passing)
- Mock mode for easy development and demo recording

## Project Structure

```
job-source-agent/
├── main.py                 # CLI entrypoint + LinkedIn job/company handling
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

- Used a third-party LinkedIn API instead of trying to scrape LinkedIn directly (more reliable)
- Added proper validation and scoring instead of blindly taking the first link
- Built in fallback logic for when career pages aren’t obviously linked
- Added mock mode so I could develop and record demos without burning API credits
- Wrote tests so I could refactor confidently

## Future Improvements (If I Had More Time)

- Add LLM-based link ranking instead of pure keyword scoring
- Improve company extraction from job listing pages (better selectors / handling of different LinkedIn layouts)
- Add better error messages and retry logic

---

Thanks for checking it out! This was a fun challenge and I learned a lot building it.