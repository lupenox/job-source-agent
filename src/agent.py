import asyncio
from src.crawler import WebCrawler
from src.schemas import AgentStatus, CandidateLink, JobSourceResult
from src.scoring import score_career_link, score_job_link
from src.validator import validate_career_page, validate_job_url


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
    def __init__(self):
        self.crawler = WebCrawler()
    
    def _looks_like_job_search_page(self, url: str, text: str) -> bool:
        combined = f"{url} {text}".lower()

        signals = [
            "open roles",
            "see open roles",
            "open positions",
            "search jobs",
            "/jobs/search",
            "/careers/search",
        ]

        return any(signal in combined for signal in signals)

    async def find_job_source(
        self,
        company_name: str,
        company_website_url: str,
    ) -> JobSourceResult:
        career_page = await self._find_career_page(company_website_url)

        if career_page is None:
            # Fallback: try common career paths directly
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
            confidence=0.9,
            evidence=career_page.evidence + job_url.evidence,
            status=AgentStatus.SUCCESS,
        )
        # Add the exact challenge format for convenience
        result.evidence.append(f"Challenge format: {result.to_challenge_format()}")
        return result

    @_retry_async(max_attempts=3, delay=0.8)
    async def _find_career_page(self, company_website_url: str) -> CandidateLink | None:
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

        candidates.sort(key=lambda candidate: candidate.score, reverse=True)
        return candidates[0]

    async def _try_common_career_paths(self, company_website_url: str) -> CandidateLink | None:
        """Fallback when link crawling misses the careers page."""
        common_paths = [
            "/careers", "/jobs", "/careers/", "/jobs/", "/about/careers",
            "/company/careers", "/join-us", "/hiring",
        ]
        base = company_website_url.rstrip("/")

        for path in common_paths:
            candidate_url = base + path
            # Quick validation
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
    ) -> CandidateLink | None:
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

            validation = validate_job_url(
                link["url"],
                company_name,
                company_website_url,
            )

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

        candidates.sort(key=lambda candidate: candidate.score, reverse=True)
        return candidates[0]
