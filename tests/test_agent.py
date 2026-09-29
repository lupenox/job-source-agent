import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agent import DEFAULT_GEMINI_MODEL, JobSourceAgent
from src.schemas import AgentStatus, CandidateLink


@pytest.mark.asyncio
async def test_find_job_source_success_path():
    # Direct common career paths are tried first (f2c88e1), so the agent goes straight
    # to https://stripe.com/careers without crawling the homepage.
    agent = JobSourceAgent(use_llm_reranker=False)

    links_by_url = {
        "https://stripe.com/careers": [
            {"url": "https://stripe.com/jobs/backend-engineer", "text": "Backend Engineer"},
        ],
    }

    with patch.object(agent.crawler, "get_links", new_callable=AsyncMock) as mock_get_links:
        mock_get_links.side_effect = lambda url: links_by_url[url]

        result = await agent.find_job_source("Stripe", "https://stripe.com")

        assert result.status == AgentStatus.SUCCESS
        assert result.career_page_url == "https://stripe.com/careers"
        assert result.open_position_url == "https://stripe.com/jobs/backend-engineer"
        assert result.confidence >= 0.8
        assert "Direct common career path check" in result.evidence
        assert [call.args[0] for call in mock_get_links.await_args_list] == [
            "https://stripe.com/careers"
        ]


@pytest.mark.asyncio
async def test_find_job_source_follows_open_roles_search_page():
    agent = JobSourceAgent(use_llm_reranker=False)

    links_by_url = {
        "https://stripe.com/careers": [
            {"url": "https://stripe.com/jobs/search", "text": "See open roles"},
        ],
        "https://stripe.com/jobs/search": [
            {"url": "https://stripe.com/jobs/listing/backend-engineer/123", "text": "Backend Engineer"},
        ],
    }

    with patch.object(agent.crawler, "get_links", new_callable=AsyncMock) as mock_get_links:
        mock_get_links.side_effect = lambda url: links_by_url[url]

        result = await agent.find_job_source("Stripe", "https://stripe.com")

        assert result.status == AgentStatus.SUCCESS
        assert result.career_page_url == "https://stripe.com/careers"
        assert result.open_position_url == "https://stripe.com/jobs/listing/backend-engineer/123"


def test_gemini_model_defaults_to_supported_model(monkeypatch):
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    agent = JobSourceAgent(use_llm_reranker=False)
    assert agent.gemini_model == DEFAULT_GEMINI_MODEL
    assert "1.5" not in DEFAULT_GEMINI_MODEL


def test_gemini_model_can_be_overridden(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.8-flash")
    agent = JobSourceAgent(use_llm_reranker=False)
    assert agent.gemini_model == "gemini-3.8-flash"


@pytest.mark.asyncio
async def test_llm_rerankers_use_configured_model(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test-model")
    agent = JobSourceAgent(use_llm_reranker=False)
    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = MagicMock(
        text='{"best_url": "https://stripe.com/careers", "reason": "official"}'
    )
    agent._gemini_client = fake_client

    candidates = [
        CandidateLink(url="https://stripe.com/careers", text="Careers", score=10, evidence=[]),
        CandidateLink(url="https://stripe.com/blog", text="Blog", score=1, evidence=[]),
    ]
    choice = await agent._llm_rerank_career_candidates("Stripe", "https://stripe.com", candidates)

    assert choice is not None and choice.url == "https://stripe.com/careers"
    assert fake_client.models.generate_content.call_args.kwargs["model"] == "gemini-test-model"
