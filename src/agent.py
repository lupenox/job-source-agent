from typing import Callable, Optional

from src.crawler import WebCrawler
from src.llm_ranker import LLMReranker
from src.schemas import AgentStatus, CandidateLink, JobSourceResult, ValidationResult
from src.scoring import (
    looks_like_job_search_page,
    score_career_link,
    score_job_link,
)
from src.validator import validate_career_page, validate_job_url

COMMON_CAREER_PATHS = [
    "/careers",
    "/jobs",
    "/about/careers",
    "/company/careers",
    "/join-us",
    "/hiring",
    "/join",
]

CONFIDENCE_LLM_VERIFIED = 0.95
CONFIDENCE_HEURISTIC = 0.90
CONFIDENCE_CAREER_PAGE_ONLY = 0.60
CONFIDENCE_NONE = 0.0

MAX_CAREER_CANDIDATES_FOR_LLM = 8
MAX_JOB_CANDIDATES_FOR_LLM = 6


class JobSourceAgent:
    """
    Orchestrates the two-phase discovery pipeline:
      Phase 1: Given a company's official website, discover its career page
               (via homepage link scoring + LLM reranking, falling back to probing common paths).
      Phase 2: Given the career page, discover an open job position URL
               (following an intermediate "search roles" directory link if needed).
    """

    def __init__(self, use_llm_reranker: bool = True):
        self.crawler = WebCrawler()
        self.use_llm_reranker = use_llm_reranker
        self.reranker = LLMReranker(enabled=use_llm_reranker)
        self._prefetched_links: dict[str, list[dict[str, str]]] = {}

    async def find_job_source(
        self,
        company_name: str,
        company_website_url: str,
    ) -> JobSourceResult:
        self._prefetched_links.clear()

        # Phase 1: Discover career page (prefer explicit homepage links over guessed paths)
        career_page = await self._find_career_page(company_name, company_website_url)
        if career_page is None:
            career_page = await self._try_common_career_paths(company_website_url)

        if career_page is None:
            return JobSourceResult(
                company_name=company_name,
                company_website_url=company_website_url,
                career_page_url=None,
                open_position_url=None,
                confidence=CONFIDENCE_NONE,
                evidence=["No valid career page found."],
                status=AgentStatus.NEEDS_REVIEW,
            )

        # Phase 2: Discover an open job posting on the career page
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
                confidence=CONFIDENCE_CAREER_PAGE_ONLY,
                evidence=career_page.evidence + ["No valid open position URL found on career page."],
                status=AgentStatus.NEEDS_REVIEW,
            )

        confidence = CONFIDENCE_LLM_VERIFIED if self.reranker.is_available else CONFIDENCE_HEURISTIC
        result = JobSourceResult(
            company_name=company_name,
            company_website_url=company_website_url,
            career_page_url=career_page.url,
            open_position_url=job_url.url,
            confidence=confidence,
            evidence=career_page.evidence + job_url.evidence,
            status=AgentStatus.SUCCESS,
        )
        result.evidence.append(f"Challenge format: {result.to_challenge_format()}")
        return result

    async def _find_career_page(
        self,
        company_name: str,
        company_website_url: str,
    ) -> Optional[CandidateLink]:
        links = await self.crawler.get_links(company_website_url)
        candidates = self._score_and_validate_links(
            links=links,
            scorer=score_career_link,
            validator=lambda url: validate_career_page(url, company_website_url),
        )
        if not candidates:
            return None

        top_candidates = candidates[:MAX_CAREER_CANDIDATES_FOR_LLM]
        llm_choice = await self.reranker.rerank_career_candidates(
            company_name=company_name,
            company_website_url=company_website_url,
            candidates=top_candidates,
        )
        return llm_choice or top_candidates[0]

    async def _try_common_career_paths(
        self,
        company_website_url: str,
    ) -> Optional[CandidateLink]:
        """
        Fallback when the homepage hides career links inside non-anchor menus or footers.
        Each candidate path is only accepted if crawling it reveals actual job or job-search links.
        """
        base = company_website_url.rstrip("/")

        for path in COMMON_CAREER_PATHS:
            candidate_url = base + path
            validation = validate_career_page(candidate_url, company_website_url)
            if not validation.is_valid:
                continue

            links = await self.crawler.get_links(candidate_url)
            has_job_signals = any(
                score_job_link(link["url"], link["text"])[0] > 0
                or looks_like_job_search_page(link["url"], link["text"])
                for link in links
            )
            if not has_job_signals:
                continue

            # Cache links so _find_open_position does not re-crawl the same fallback URL
            self._prefetched_links[candidate_url] = links
            return CandidateLink(
                url=candidate_url,
                text=f"Common career path: {path}",
                score=20,
                evidence=["Common career path contains job or job-search links"],
            )

        return None

    async def _find_open_position(
        self,
        career_page_url: str,
        company_name: str,
        company_website_url: str,
    ) -> Optional[CandidateLink]:
        links = self._prefetched_links.pop(career_page_url, None)
        if links is None:
            links = await self.crawler.get_links(career_page_url)

        # Many career splash pages link to an intermediate "/jobs/search" or "See open roles" page
        search_page_links = [
            link for link in links
            if looks_like_job_search_page(link["url"], link["text"])
        ]
        if search_page_links:
            career_page_url = search_page_links[0]["url"]
            links = await self.crawler.get_links(career_page_url)

        candidates = self._score_and_validate_links(
            links=links,
            scorer=score_job_link,
            validator=lambda url: validate_job_url(url, company_name, company_website_url),
        )
        if not candidates:
            return None

        top_candidates = candidates[:MAX_JOB_CANDIDATES_FOR_LLM]
        llm_choice = await self.reranker.rerank_job_candidates(
            company_name=company_name,
            career_page_url=career_page_url,
            candidates=top_candidates,
        )
        return llm_choice or top_candidates[0]

    @staticmethod
    def _score_and_validate_links(
        links: list[dict[str, str]],
        scorer: Callable[[str, str], tuple[int, list[str]]],
        validator: Callable[[str], ValidationResult],
    ) -> list[CandidateLink]:
        """Filter raw links by positive keyword score and domain/ATS validation, sorted highest-first."""
        candidates: list[CandidateLink] = []
        for link in links:
            url = link.get("url", "")
            text = link.get("text", "")
            score, evidence = scorer(url, text)
            if score <= 0:
                continue

            validation = validator(url)
            if not validation.is_valid:
                continue

            candidates.append(
                CandidateLink(
                    url=url,
                    text=text,
                    score=score,
                    evidence=evidence + [validation.reason],
                )
            )

        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates
