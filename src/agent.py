import asyncio
import os
from typing import Optional

from dotenv import load_dotenv
from google import genai

load_dotenv()


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
        self._gemini_client = None

        api_key = os.getenv("GEMINI_API_KEY")
        if api_key and use_llm_reranker:
            try:
                self._gemini_client = genai.Client(api_key=api_key)
            except Exception:
                self._gemini_client = None

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
            confidence=0.95 if self._gemini_client else 0.9,
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

        candidates.sort(key=lambda c: c.score, reverse=True)
        top_candidates = candidates[:8]

        if self._gemini_client and len(top_candidates) > 1:
            llm_choice = await self._llm_rerank_career_candidates(
                company_name, company_website_url, top_candidates
            )
            if llm_choice:
                return llm_choice

        return top_candidates[0]

    async def _llm_rerank_career_candidates(
        self,
        company_name: str,
        company_website_url: str,
        candidates: list[CandidateLink],
    ) -> Optional[CandidateLink]:
        if not self._gemini_client:
            return None

        prompt = f"""You are a precise recruiter agent. Your job is to identify the SINGLE best official careers / jobs page for the company "{company_name}".

Company website: {company_website_url}

Here are the candidate links scraped from the homepage:
"""
        for i, c in enumerate(candidates, 1):
            prompt += f"{i}. {c.url}  |  Text: {c.text or '(no text)'}\n"

        prompt += """
Return ONLY valid JSON in this exact format:
{
  "best_url": "URL of the best careers page",
  "reason": "One short sentence explaining why this is the best choice"
}

Strict rules:
- Strongly prefer URLs containing /careers, /jobs, /join, or /hiring
- Strongly avoid /events, /blog, /news, /about, /pricing, /docs
- If multiple good options exist, pick the most official-looking careers page
- Only return a URL from the list above. Do not invent new URLs."""

        try:
            response = await asyncio.to_thread(
                self._gemini_client.models.generate_content,
                model="gemini-1.5-flash",
                contents=prompt
            )
            text = response.text.strip()

            import json
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            data = json.loads(text)
            best_url = data.get("best_url")

            for c in candidates:
                if c.url.rstrip("/") == best_url.rstrip("/"):
                    c.evidence.append(f"LLM selected: {data.get('reason', '')}")
                    return c
            return None
        except Exception:
            return None

    async def _try_common_career_paths(self, company_website_url: str) -> Optional[CandidateLink]:
        common_paths = [
            "/careers", "/jobs", "/careers/", "/jobs/", "/about/careers",
            "/company/careers", "/join-us", "/hiring", "/join",
        ]
        base = company_website_url.rstrip("/")

        for path in common_paths:
            candidate_url = base + path
            validation = validate_career_page(candidate_url, company_website_url)
            if validation.is_valid:
                return CandidateLink(
                    url=candidate_url,
                    text=f"Common career path: {path}",
                    score=15,
                    evidence=["Strong fallback: exact common career path"],
                )
        return None

    async def _find_open_position(
        self,
        career_page_url: str,
        company_name: str,
        company_website_url: str,
    ) -> Optional[CandidateLink]:
        links = await self.crawler.get_links(career_page_url)

        # Try to find a dedicated job search page first
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
        top_candidates = candidates[:6]

        # Use LLM to pick the best job if available
        if self._gemini_client and len(top_candidates) > 1:
            llm_choice = await self._llm_rerank_job_candidates(
                company_name, career_page_url, top_candidates
            )
            if llm_choice:
                return llm_choice

        return top_candidates[0]

    async def _llm_rerank_job_candidates(
        self,
        company_name: str,
        career_page_url: str,
        candidates: list[CandidateLink],
    ) -> Optional[CandidateLink]:
        if not self._gemini_client:
            return None

        prompt = f"""You are selecting the SINGLE best open job position to show from {company_name}'s career page.

Career page: {career_page_url}

Here are the job links found:
"""
        for i, c in enumerate(candidates, 1):
            prompt += f"{i}. {c.url}  |  Text: {c.text or '(no text)'}\n"

        prompt += """
Return ONLY valid JSON:
{
  "best_url": "the best job URL from the list",
  "reason": "short reason why this job is a good example"
}

Rules:
- Prefer engineering, product, design, or other technical roles if available
- Avoid generic or unrelated links
- Only choose from the URLs above"""

        try:
            response = await asyncio.to_thread(
                self._gemini_client.models.generate_content,
                model="gemini-1.5-flash",
                contents=prompt
            )
            text = response.text.strip()

            import json
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            data = json.loads(text)
            best_url = data.get("best_url")

            for c in candidates:
                if c.url.rstrip("/") == best_url.rstrip("/"):
                    c.evidence.append(f"LLM job pick: {data.get('reason', '')}")
                    return c
            return None
        except Exception:
            return None

