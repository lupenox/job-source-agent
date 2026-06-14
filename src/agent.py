import asyncio
import os
from typing import Optional

import google.generativeai as genai
from dotenv import load_dotenv

from src.crawler import WebCrawler
from src.schemas import AgentStatus, CandidateLink, JobSourceResult
from src.scoring import score_career_link, score_job_link
from src.validator import validate_career_page, validate_job_url

load_dotenv()


def _retry_async(max_attempts: int = 3, delay: float = 1.0):
    """Simple retry decorator for async functions (no extra deps)."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exc = e
                    if attempt < max_attempts:
                        await asyncio.sleep(delay * attempt)
            raise last_exc
        return wrapper
    return decorator


class JobSourceAgent:
    def __init__(self, use_llm_reranker: bool = True):
        self.crawler = WebCrawler()
        self.use_llm_reranker = use_llm_reranker
        self._gemini_model = None

        api_key = os.getenv("GEMINI_API_KEY")
        if api_key and use_llm_reranker:
            try:
                genai.configure(api_key=api_key)
                self._gemini_model = genai.GenerativeModel("gemini-1.5-flash")
            except Exception:
                self._gemini_model = None  # graceful fallback

    def _looks_like_job_search_page(self, url: str, text: str) -> bool:
        combined = f"{url} {text}".lower()
        signals = [
            "open roles", "see open roles", "open positions",
            "search jobs", "/jobs/search", "/careers/search",
        ]
        return any(signal in combined for signal in signals)

    async def find_job_source(
        self,
        company_name: str,
        company_website_url: str,
    ) -> JobSourceResult:
        career_page = await self._find_career_page(company_name, company_website_url)

        if career_page is None:
            career_page = await self._try_common_career_paths(company_website_url)

        if career_page is None:
            return JobSourceResult(
                company_name=company_name,
                company_website_url=company_website_url,
                career_page_url=None,
                open_position_url=None,
                confidence=0.0,
                evidence=["No valid career page found even with common path fallbacks."],
                status=AgentStatus.NEEDS_REVIEW,
            )

        job_url = await self._find_open_position(
            career_page_url=career_page.url,
            company_name=company_name,
            company_website_url=company_website_url,
        )

        if job_url is None:
            return JobSourceResult(
                company_name=company_name,
                company_website_url=company_website_url,
                career_page_url=career_page.url,
                open_position_url=None,
                confidence=0.6,
                evidence=career_page.evidence + ["No valid open position URL found on career page."],
                status=AgentStatus.NEEDS_REVIEW,
            )

        result = JobSourceResult(
            company_name=company_name,
            company_website_url=company_website_url,
            career_page_url=career_page.url,
            open_position_url=job_url.url,
            confidence=0.95 if self._gemini_model else 0.9,
            evidence=career_page.evidence + job_url.evidence,
            status=AgentStatus.SUCCESS,
        )
        result.evidence.append(f"Challenge format: {result.to_challenge_format()}")
        return result

    async def _find_career_page(self, company_name: str, company_website_url: str) -> Optional[CandidateLink]:
        links = await self.crawler.get_links(company_website_url)
        candidates: list[CandidateLink] = []

        for link in links:
            score, evidence = score_career_link(link["url"], link["text"])
            if score <= 0:
                continue
            validation = validate_career_page(link["url"], company_website_url)
            if not validation.is_valid:
                continue
            candidates.append(
                CandidateLink(
                    url=link["url"],
                    text=link["text"],
                    score=score,
                    evidence=evidence + [validation.reason],
                )
            )

        if not candidates:
            return None

        # Sort by keyword score first
        candidates.sort(key=lambda c: c.score, reverse=True)
        top_candidates = candidates[:6]  # limit for LLM cost

        # LLM reranking (if available)
        if self._gemini_model and len(top_candidates) > 1:
            llm_choice = await self._llm_rerank_career_candidates(
                company_name, company_website_url, top_candidates
            )
            if llm_choice:
                return llm_choice

        # Fallback to best keyword score
        return top_candidates[0]

    async def _llm_rerank_career_candidates(
        self,
        company_name: str,
        company_website_url: str,
        candidates: list[CandidateLink],
    ) -> Optional[CandidateLink]:
        """Use Gemini to pick the single best career page from keyword-filtered candidates."""
        if not self._gemini_model:
            return None

        prompt = f"""You are an expert recruiter agent helping find the official careers page for {company_name}.

Company website: {company_website_url}

Here are the top candidate links found on the homepage (with their link text):
"""
        for i, c in enumerate(candidates, 1):
            prompt += f"{i}. URL: {c.url}\n   Text: {c.text or '(no text)'}\n\n"

        prompt += """Return ONLY a JSON object with this exact structure:
{
  "best_url": "the single best career/jobs page URL from the list above",
  "reason": "short explanation why this is the best one (1 sentence)"
}

Rules:
- Only choose from the URLs provided above.
- Prefer official careers, jobs, or "join us" pages over generic pages.
- If none look like a real careers page, return the most relevant one anyway.
- Do not make up URLs."""

        try:
            response = await asyncio.to_thread(
                self._gemini_model.generate_content, prompt
            )
            text = response.text.strip()

            # Simple JSON extraction
            import json
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            data = json.loads(text)
            best_url = data.get("best_url")

            # Find the matching candidate
            for c in candidates:
                if c.url == best_url or c.url.rstrip("/") == best_url.rstrip("/"):
                    c.evidence.append(f"LLM chosen: {data.get('reason', 'Best match')}")
                    return c
            return None
        except Exception:
            return None  # graceful fallback to keyword winner

    async def _try_common_career_paths(self, company_website_url: str) -> Optional[CandidateLink]:
        common_paths = [
            "/careers", "/jobs", "/careers/", "/jobs/", "/about/careers",
            "/company/careers", "/join-us", "/hiring",
        ]
        base = company_website_url.rstrip("/")
        for path in common_paths:
            candidate_url = base + path
            validation = validate_career_page(candidate_url, company_website_url)
            if validation.is_valid:
                return CandidateLink(
                    url=candidate_url,
                    text=f"Common career path: {path}",
                    score=10,
                    evidence=["Fallback common career path"],
                )
        return None

    @_retry_async(max_attempts=3, delay=0.8)
    async def _find_open_position(
        self,
        career_page_url: str,
        company_name: str,
        company_website_url: str,
    ) -> Optional[CandidateLink]:
        links = await self.crawler.get_links(career_page_url)

        search_page_links = [
            link for link in links
            if self._looks_like_job_search_page(link["url"], link["text"])
        ]
        if search_page_links:
            career_page_url = search_page_links[0]["url"]
            links = await self.crawler.get_links(career_page_url)

        candidates: list[CandidateLink] = []
        for link in links:
            score, evidence = score_job_link(link["url"], link["text"])
            if score <= 0:
                continue
            validation = validate_job_url(link["url"], company_name, company_website_url)
            if not validation.is_valid:
                continue
            candidates.append(
                CandidateLink(
                    url=link["url"],
                    text=link["text"],
                    score=score,
                    evidence=evidence + [validation.reason],
                )
            )

        if not candidates:
            return None

        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates[0]
