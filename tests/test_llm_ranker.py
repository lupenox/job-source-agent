from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.llm_ranker import LLMReranker
from src.schemas import CandidateLink


@pytest.mark.asyncio
async def test_llm_reranker_selects_matching_candidate_from_fenced_json():
    reranker = LLMReranker(enabled=False)
    reranker.enabled = True
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = SimpleNamespace(
        text='```json\n{"best_url": "https://stripe.com/jobs/", "reason": "Official jobs page"}\n```'
    )
    reranker.client = mock_client

    candidates = [
        CandidateLink(url="https://stripe.com/blog/careers", text="Careers blog", score=5),
        CandidateLink(url="https://stripe.com/jobs", text="Jobs at Stripe", score=5),
    ]

    chosen = await reranker.rerank_career_candidates("Stripe", "https://stripe.com", candidates)
    assert chosen is not None
    assert chosen.url == "https://stripe.com/jobs"
    assert any("LLM selected: Official jobs page" in ev for ev in chosen.evidence)


@pytest.mark.asyncio
async def test_llm_reranker_returns_none_when_url_not_in_candidates():
    reranker = LLMReranker(enabled=False)
    reranker.enabled = True
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = SimpleNamespace(
        text='{"best_url": "https://invented-url.com/jobs", "reason": "Hallucinated"}'
    )
    reranker.client = mock_client

    candidates = [
        CandidateLink(url="https://stripe.com/careers", text="Careers", score=5),
        CandidateLink(url="https://stripe.com/jobs", text="Jobs", score=5),
    ]

    chosen = await reranker.rerank_career_candidates("Stripe", "https://stripe.com", candidates)
    assert chosen is None
