from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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


def test_fetch_company_info_parses_top_level_fields_and_error_message():
    api = LinkedInCrawlerApi(use_mock=False)
    api.apify_token = "fake-token"
    api.use_mock = False

    mock_client = MagicMock()
    mock_client.actor.return_value.call.return_value = SimpleNamespace(default_dataset_id="ds-1")
    mock_client.dataset.return_value.iterate_items.return_value = [
        {"name": "Stripe", "website": "stripe.com"}
    ]

    with patch("src.linkedin_parser.ApifyClient", return_value=mock_client):
        result = api.fetch_company_info("https://www.linkedin.com/company/stripe")

    assert result.status == "success"
    assert result.company_name == "Stripe"
    assert result.company_website_url == "https://stripe.com"
    mock_client.actor.assert_called_once_with("johnvc/linkedin-company-api")

    mock_client.dataset.return_value.iterate_items.return_value = [
        {"error_message": "Company profile not found"}
    ]
    with patch("src.linkedin_parser.ApifyClient", return_value=mock_client):
        err_result = api.fetch_company_info("https://www.linkedin.com/company/unknown")

    assert err_result.status == "failed"
    assert "Company profile not found" in (err_result.reason or "")


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
