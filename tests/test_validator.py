import pytest
from src.validator import (
    validate_career_page,
    validate_job_url,
    get_domain,
    normalize_company_name,
)


def test_get_domain():
    assert get_domain("https://www.stripe.com/jobs") == "stripe.com"
    assert get_domain("https://careers.openai.com") == "openai.com"


def test_normalize_company_name():
    assert normalize_company_name("Stripe, Inc.") == "stripeinc"
    assert normalize_company_name("OpenAI") == "openai"


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


def test_validate_job_url_rejects_generic_job_board():
    result = validate_job_url("https://www.linkedin.com/jobs/123", "Stripe", "https://stripe.com")
    assert result.is_valid is False
