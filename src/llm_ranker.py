import asyncio
import json
import logging
import os
from typing import Optional

from dotenv import load_dotenv
from google import genai

from src.schemas import CandidateLink

load_dotenv()

logger = logging.getLogger(__name__)


class LLMReranker:
    """
    Optional Gemini-backed reranker that selects the single best candidate link
    from the top heuristic-scored links.

    Using a two-stage pipeline (fast keyword filtering -> LLM reranking on top-K)
    keeps token usage tiny while disambiguating links like `/careers` vs `/blog/careers-story`.
    """

    def __init__(self, enabled: bool = True, model_name: str = "gemini-1.5-flash"):
        self.enabled = enabled
        self.model_name = model_name
        self.client: Optional[genai.Client] = None

        api_key = os.getenv("GEMINI_API_KEY")
        if self.enabled and api_key:
            try:
                self.client = genai.Client(api_key=api_key)
            except Exception as exc:
                logger.warning("Failed to initialize Gemini client: %s", exc)
                self.client = None

    @property
    def is_available(self) -> bool:
        return self.enabled and self.client is not None

    async def rerank_career_candidates(
        self,
        company_name: str,
        company_website_url: str,
        candidates: list[CandidateLink],
    ) -> Optional[CandidateLink]:
        """Pick the most authoritative official careers page from top candidates."""
        if not self.is_available or len(candidates) <= 1:
            return None

        candidate_lines = self._format_candidates(candidates)
        prompt = f"""You are a precise recruiter agent. Identify the SINGLE best official careers / jobs page for the company "{company_name}".

Company website: {company_website_url}

Candidate links scraped from the homepage:
{candidate_lines}

Return ONLY valid JSON in this exact format:
{{
  "best_url": "URL of the best careers page",
  "reason": "One short sentence explaining why this is the best choice"
}}

Strict rules:
- Strongly prefer URLs containing /careers, /jobs, /join, or /hiring
- Strongly avoid /events, /blog, /news, /about, /pricing, /docs
- If multiple good options exist, pick the most official-looking careers page
- Only return a URL from the list above. Do not invent new URLs."""

        return await self._select_candidate(
            prompt=prompt,
            candidates=candidates,
            evidence_prefix="LLM selected",
        )

    async def rerank_job_candidates(
        self,
        company_name: str,
        career_page_url: str,
        candidates: list[CandidateLink],
    ) -> Optional[CandidateLink]:
        """Pick the single best open job posting URL from top candidates."""
        if not self.is_available or len(candidates) <= 1:
            return None

        candidate_lines = self._format_candidates(candidates)
        prompt = f"""You are selecting the SINGLE best open job position to show from {company_name}'s career page.

Career page: {career_page_url}

Job links found:
{candidate_lines}

Return ONLY valid JSON:
{{
  "best_url": "the best job URL from the list",
  "reason": "short reason why this job is a good example"
}}

Rules:
- Prefer engineering, product, design, or other concrete role postings if available
- Avoid generic navigation or unrelated links
- Only choose from the URLs above"""

        return await self._select_candidate(
            prompt=prompt,
            candidates=candidates,
            evidence_prefix="LLM job pick",
        )

    @staticmethod
    def _format_candidates(candidates: list[CandidateLink]) -> str:
        return "\n".join(
            f"{i}. {c.url}  |  Text: {c.text or '(no text)'}"
            for i, c in enumerate(candidates, 1)
        )

    @staticmethod
    def _parse_json_response(raw_text: str) -> dict:
        """Strip optional Markdown code fences and parse JSON."""
        text = raw_text.strip()
        if "```json" in text:
            text = text.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in text:
            text = text.split("```", 1)[1].split("```", 1)[0].strip()
        return json.loads(text)

    async def _select_candidate(
        self,
        prompt: str,
        candidates: list[CandidateLink],
        evidence_prefix: str,
    ) -> Optional[CandidateLink]:
        if not self.client:
            return None

        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt,
            )
            data = self._parse_json_response(response.text or "")
            best_url = (data.get("best_url") or "").rstrip("/")
            if not best_url:
                return None

            for candidate in candidates:
                if candidate.url.rstrip("/") == best_url:
                    reason = data.get("reason", "Selected by LLM reranker")
                    candidate.evidence.append(f"{evidence_prefix}: {reason}")
                    return candidate
            return None
        except Exception as exc:
            logger.debug("LLM reranking fallback triggered: %s", exc)
            return None
