import pytest
from unittest.mock import AsyncMock

from src.linkedin_parser import (
    LinkedInCrawlerApi,
    extract_company_from_linkedin_job_page,
    is_linkedin_job_url,
)


def test_mock_mode_returns_success_for_stripe():
    api = LinkedInCrawlerApi(use_mock=True)
    result = api.fetch_company_info("https://www.linkedin.com/company/stripe")

    assert result.status == "success_mock"
    assert result.company_name == "Stripe"
    assert result.company_website_url == "https://stripe.com"


def test_mock_mode_returns_success_for_openai():
    api = LinkedInCrawlerApi(use_mock=True)
    result = api.fetch_company_info("https://www.linkedin.com/company/openai")

    assert result.status == "success_mock"
    assert result.company_name == "OpenAI"


def test_mock_mode_generic_fallback():
    api = LinkedInCrawlerApi(use_mock=True)
    result = api.fetch_company_info("https://www.linkedin.com/company/random-startup")

    assert result.status == "success_mock"
    assert result.company_name == "Example Corp"


def test_returns_not_configured_when_no_token():
    """Test that the parser reports not_configured when no token is available."""
    api = LinkedInCrawlerApi(use_mock=False)
    api.apify_token = None
    api.use_mock = False

    result = api.fetch_company_info("https://www.linkedin.com/company/stripe")

    assert result.status == "not_configured"


def test_is_linkedin_job_url():
    assert is_linkedin_job_url("https://www.linkedin.com/jobs/view/1234567890") is True
    assert is_linkedin_job_url("https://www.linkedin.com/company/stripe") is False


@pytest.mark.asyncio
async def test_extract_company_from_linkedin_job_page():
    mock_crawler = AsyncMock()
    mock_crawler.get_links.return_value = [
        {"url": "https://www.linkedin.com/company/stripe", "text": "Stripe"},
    ]

    result = await extract_company_from_linkedin_job_page(
        "https://www.linkedin.com/jobs/view/1234567890",
        crawler=mock_crawler,
    )
    assert result["status"] == "success"
    assert result["company_name"] == "Stripe"
    assert result["company_linkedin_url"] == "https://www.linkedin.com/company/stripe"


@pytest.mark.asyncio
async def test_resolve_company_handles_job_url_in_mock_mode():
    api = LinkedInCrawlerApi(use_mock=True)
    result = await api.resolve_company("https://www.linkedin.com/jobs/view/1234567890")
    assert result.status == "success_mock"
    assert result.company_name == "Stripe"
    assert result.company_website_url == "https://stripe.com"
