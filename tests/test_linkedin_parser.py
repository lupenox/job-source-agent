import pytest
import os
from src.linkedin_parser import LinkedInCrawlerApi


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
    # Create instance without mock, and force no token
    api = LinkedInCrawlerApi(use_mock=False)
    api.apify_token = None          # Force no token for test
    api.use_mock = False

    result = api.fetch_company_info("https://www.linkedin.com/company/stripe")

    assert result.status == "not_configured"
