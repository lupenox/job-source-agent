import pytest
from src.crawler import WebCrawler
from src.validator import (
    domain_contains,
    extract_company_slugs,
    get_domain,
    normalize_company_name,
    validate_career_page,
    validate_job_url,
)


def test_get_domain():
    assert get_domain("https://www.stripe.com/jobs") == "stripe.com"
    assert get_domain("https://careers.openai.com") == "openai.com"
    assert get_domain("https://jobs.lever.co/stripe/123") == "lever.co"
    assert get_domain("https://www.acme.co.uk/careers") == "acme.co.uk"


def test_normalize_company_name():
    assert normalize_company_name("Stripe, Inc.") == "stripeinc"
    assert normalize_company_name("OpenAI") == "openai"


def test_domain_contains_rejects_empty_domains():
    assert domain_contains("/relative/path", "https://stripe.com") is False
    assert domain_contains("https://stripe.com", "") is False


def test_validate_career_page_on_company_domain():
    result = validate_career_page("https://stripe.com/jobs", "https://stripe.com")
    assert result.is_valid is True


def test_validate_career_page_on_different_domain():
    result = validate_career_page("https://jobs.lever.co/stripe", "https://stripe.com")
    assert result.is_valid is False


def test_validate_job_url_on_company_domain():
    result = validate_job_url("https://stripe.com/jobs/backend-engineer", "Stripe", "https://stripe.com")
    assert result.is_valid is True


def test_validate_job_url_on_known_ats_with_slug():
    result = validate_job_url("https://jobs.lever.co/stripe/abc123", "Stripe", "https://stripe.com")
    assert result.is_valid is True


def test_validate_job_url_on_known_ats_with_corporate_suffix():
    result = validate_job_url(
        "https://jobs.lever.co/stripe/abc123",
        "Stripe, Inc.",
        "https://stripe.com",
    )
    assert result.is_valid is True
    assert "stripe" in extract_company_slugs("Stripe, Inc.", "https://stripe.com")


def test_validate_job_url_rejects_unrelated_ats_for_co_uk_company():
    slugs = extract_company_slugs("Acme Limited", "https://acme.co.uk")
    assert "co" not in slugs
    assert "acme" in slugs

    unrelated = validate_job_url(
        "https://jobs.lever.co/unrelated-company/engineer",
        "Acme Limited",
        "https://acme.co.uk",
    )
    assert unrelated.is_valid is False

    matching = validate_job_url(
        "https://jobs.lever.co/acme/engineer",
        "Acme Limited",
        "https://acme.co.uk",
    )
    assert matching.is_valid is True


def test_validate_job_url_rejects_generic_job_board():
    result = validate_job_url("https://www.linkedin.com/jobs/123", "Stripe", "https://stripe.com")
    assert result.is_valid is False


def test_crawler_normalize_links_preserves_hash_routes_and_drops_bare_hash():
    raw_links = [
        {"href": "#", "text": "Ignore me"},
        {"href": "#/careers", "text": "Careers"},
        {"href": "javascript:void(0)", "text": "JS"},
    ]
    normalized = WebCrawler._normalize_links("https://example.com", raw_links)
    assert normalized == [{"url": "https://example.com#/careers", "text": "Careers"}]
