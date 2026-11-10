# AI Job Source Agent – Part 2 Take-Home Challenge

An autonomous web discovery agent that starts from a **LinkedIn job listing URL** or **LinkedIn company profile URL**, resolves the company's official website, locates its official career portal, and extracts a validated open job position URL.

---

## What It Does

1. **Resolves LinkedIn Input** (`src/linkedin_parser.py`): Accepts either a LinkedIn job listing URL (`linkedin.com/jobs/view/...`) or a company profile URL (`linkedin.com/company/...`), extracting the official company name and website via Apify (or deterministic mock mode for zero-cost testing).
2. **Discovers the Official Career Page** (`src/agent.py`):
   - Crawls the company homepage with headless Chromium (`src/crawler.py`).
   - Filters and scores links using word-boundary career heuristics (`src/scoring.py`) and domain validation (`src/validator.py`).
   - Uses **Gemini 1.5 Flash** (`src/llm_ranker.py`) to rerank the top heuristic candidates and disambiguate true career portals from blog/news pages.
   - Falls back to probing common career paths (`/careers`, `/jobs`, etc.) if the homepage hides career links behind non-anchor menus.
3. **Extracts a Validated Open Position URL**:
   - Follows intermediate job-directory links (`"See open roles"`, `/jobs/search`) if the career page is a splash page.
   - Validates candidate job URLs against the company's primary domain or a company-scoped ATS board (`lever.co`, `greenhouse.io`, `ashbyhq.com`, `workdayjobs.com`, etc.) while blocking third-party job boards (`linkedin.com`, `indeed.com`, `glassdoor.com`).
4. **Formats Output**: Returns structured metadata (`JobSourceResult`) plus the exact CSV string required by the challenge (`company_name,career_page_url,open_position_url`).

---

## Project Structure

```text
job-source-agent/
├── main.py                  # Thin CLI entrypoint & argument parsing
├── demo.py                  # Standalone live demo script
├── demo.sh                  # Interactive step-by-step walkthrough script
├── src/
│   ├── agent.py             # Two-phase orchestration pipeline (JobSourceAgent)
│   ├── crawler.py           # Playwright link extractor with retry & link deduplication
│   ├── linkedin_parser.py   # LinkedIn job/company resolver (Apify adapter + mock mode)
│   ├── llm_ranker.py        # Gemini 1.5 Flash candidate reranker (LLMReranker)
│   ├── scoring.py           # Keyword & job-search-page heuristics
│   ├── validator.py         # Domain matching, corporate suffix normalization, ATS allowlist
│   └── schemas.py           # Dataclasses (CandidateLink, ValidationResult, JobSourceResult)
└── tests/                   # Pytest unit & async test suite
```

---

## Quick Start

```bash
git clone https://github.com/lupenox/job-source-agent.git
cd job-source-agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### Environment Variables (`.env`)

1. **`APIFY_API_TOKEN`** – Used by `LinkedInCrawlerApi` to enrich LinkedIn company URLs without fragile cookie/session scraping. (Optional when running with `--mock` or `--company-name` / `--company-url`).
2. **`GEMINI_API_KEY`** – Used by `LLMReranker` (`gemini-1.5-flash`) to rerank top candidate URLs. Automatically falls back to deterministic heuristic ranking if omitted.

### Usage

```bash
# Run from a LinkedIn job or company URL (live API mode)
python main.py --linkedin-url "https://www.linkedin.com/company/stripe"

# Run in mock mode (no Apify credits required)
python main.py --linkedin-url "https://www.linkedin.com/jobs/view/1234567890" --mock

# Run directly from a company name and website
python main.py --company-name "Stripe" --company-url "https://stripe.com"

# Run test suite
pytest tests/ -v
```

---

## Architecture & Interview Defense Guide

### 1. Why a Two-Stage Ranking Pipeline (Heuristics First, LLM Second)?
- **Problem**: A company homepage can have 150–400 `<a href>` links. Sending every link to an LLM on every page load increases latency, token cost, and hallucination risk. Conversely, pure keyword scoring can confuse `/blog/careers-at-acme` with `/careers`.
- **Solution**:
  1. **Stage 1 (Deterministic Filter & Score)**: `score_career_link` and `validate_career_page` narrow hundreds of links down to the top 6–8 valid candidates in sub-millisecond time.
  2. **Stage 2 (LLM Reranker)**: `LLMReranker` passes only those top candidates to `gemini-1.5-flash` and constrains the model to pick a URL strictly from the provided candidate list. If the API key is missing, rate-limited, or returns an unlisted URL, the agent gracefully falls back to `top_candidates[0]`.

### 2. Why Playwright Instead of `requests` + `BeautifulSoup`?
- Modern career sites and embedded ATS boards (Ashby, Greenhouse, Workday, React/Next.js frontends) hydrate job links client-side via JavaScript. Static HTML fetching returns an empty `<div id="root"></div>`.
- `WebCrawler` uses headless Chromium via Playwright with `domcontentloaded` + a brief hydration delay and `@retry_async` backoff to reliably extract rendered DOM anchor tags.

### 3. Why Apify for LinkedIn Instead of Direct Scraping?
- LinkedIn enforces strict anti-bot protections, authwalls, and IP rate limits on `/company/` pages. Building a brittle HTML scraper for LinkedIn couples the take-home challenge to anti-bot cat-and-mouse games.
- Wrapping LinkedIn resolution behind `LinkedInCrawlerApi` (using Apify's `johnvc/linkedin-company-api` actor + a deterministic `--mock` mode) follows the **Adapter Pattern**, keeping LinkedIn ingestion cleanly separated from the core web-crawling agent.
- **Real-World Proof of the Adapter Pattern (Issue #3 / PR #4 & #6)**: When the original Apify actor (`zhorex/linkedin-company-enrichment`) was deprecated, an external contributor (`@johnisanerd`) opened an issue and PR to migrate to `johnvc/linkedin-company-api`, which returns top-level `name`/`website` fields and an `error_message` field instead of a nested `company` object. Because LinkedIn enrichment was isolated inside `LinkedInCrawlerApi`, supporting both actor schemas and adding unit tests took ~15 lines in a single file (`src/linkedin_parser.py`) with zero changes to `JobSourceAgent`, `scoring.py`, or `validator.py`.

### 4. How Does URL Validation Prevent False Positives?
- **Career Page Validation (`validate_career_page`)**: Requires the discovered career link to match the company's base domain (e.g., `careers.openai.com` or `stripe.com/jobs`), preventing social media or partner links in the footer from being mistaken for the company's career page.
- **Job Posting Validation (`validate_job_url`)**:
  - Explicitly blocks generic job aggregators (`linkedin.com`, `indeed.com`, `glassdoor.com`, `monster.com`, `ziprecruiter.com`).
  - Accepts job links on the company's own domain **or** on a known ATS domain (`lever.co`, `greenhouse.io`, `ashbyhq.com`, etc.) **only if** the URL contains the company's normalized slug.
  - Handles legal entity suffixes (`"Stripe, Inc."` → `"stripe"` and `"stripeinc"`) via `extract_company_slugs()` so ATS boards like `jobs.lever.co/stripe/...` validate cleanly even when LinkedIn provides a formal legal name.

### 5. How Does the Agent Handle Multi-Hop Career Pages & Hidden Links?
- **Intermediate Splash Pages**: Many companies have a culture page at `/careers` with a button linking to `/jobs/search` ("See open roles"). `_find_open_position` detects job-search directory signals (`looks_like_job_search_page`) and follows that hop before scoring individual job postings.
- **Fallback Probing with Content Verification**: If the homepage has no discoverable career links (e.g., hidden inside a JS button menu), `_try_common_career_paths` probes standard paths (`/careers`, `/jobs`, `/join-us`), but **only accepts a guessed URL if crawling it yields actual job links**, preventing soft-404 pages from being reported as valid career pages. It also caches the prefetched links so Phase 2 does not re-crawl the same page.
