import pytest
import asyncio
from unittest.mock import AsyncMock, patch

from src.agent import JobSourceAgent
from src.schemas import JobSourceResult, AgentStatus


@pytest.mark.asyncio
async def test_find_job_source_success_path():
    agent = JobSourceAgent()

    # Mock the crawler to return predictable links
    mock_links_career = [
        {"url": "https://stripe.com/jobs", "text": "Open roles"},
    ]
    mock_links_job = [
        {"url": "https://stripe.com/jobs/backend-engineer", "text": "Backend Engineer"},
    ]

    with patch.object(agent.crawler, "get_links", new_callable=AsyncMock) as mock_get_links:
        # First call (homepage) returns career link, second call (career page) returns job link
        mock_get_links.side_effect = [mock_links_career, mock_links_job]

        result = await agent.find_job_source("Stripe", "https://stripe.com")

        assert result.status == AgentStatus.SUCCESS
        assert result.career_page_url == "https://stripe.com/jobs"
        assert result.open_position_url == "https://stripe.com/jobs/backend-engineer"
        assert result.confidence >= 0.8
