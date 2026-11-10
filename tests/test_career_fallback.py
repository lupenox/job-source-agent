from unittest.mock import AsyncMock, patch

import pytest

from src.agent import JobSourceAgent
from src.schemas import AgentStatus


@pytest.mark.asyncio
async def test_missing_career_pages_are_not_reported_as_found():
    agent = JobSourceAgent(use_llm_reranker=False)
    with patch.object(agent.crawler, "get_links", new=AsyncMock(return_value=[])):
        result = await agent.find_job_source("Example", "https://example.com")
    assert result.status == AgentStatus.NEEDS_REVIEW
    assert result.career_page_url is None


@pytest.mark.asyncio
async def test_fallback_checks_content_before_accepting_a_guessed_path():
    agent = JobSourceAgent(use_llm_reranker=False)

    async def links(url):
        if url == "https://example.com/jobs":
            return [{"url": url + "/engineer", "text": "Software Engineer"}]
        return []

    with patch.object(agent.crawler, "get_links", new=AsyncMock(side_effect=links)):
        result = await agent.find_job_source("Example", "https://example.com")
    assert result.status == AgentStatus.SUCCESS
    assert result.career_page_url == "https://example.com/jobs"
