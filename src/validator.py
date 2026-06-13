from urllib.parse import urlparse

from src.schemas import ValidationResult


KNOWN_ATS_DOMAINS = [
    "lever.co",
    "greenhouse.io",
    "ashbyhq.com",
    "workdayjobs.com",
    "smartrecruiters.com",
    "bamboohr.com",
    "jobvite.com",
]

BLOCKED_JOB_BOARD_DOMAINS = [
    "linkedin.com",
    "indeed.com",
    "glassdoor.com",
    "monster.com",
    "ziprecruiter.com",
]


def normalize_company_name(company_name: str) -> str:
    """
    Convert company names into simple slugs for comparison.

    Example:
    "Stripe Inc." -> "stripeinc"
    """
    return "".join(ch for ch in company_name.lower() if ch.isalnum())


def get_domain(url: str) -> str:
    """
    Extract normalized domain from a URL.

    Example:
    "https://www.stripe.com/jobs" -> "stripe.com"
    """
    return urlparse(url).netloc.lower().replace("www.", "")


def domain_contains(candidate_url: str, expected_url: str) -> bool:
    candidate_domain = get_domain(candidate_url)
    expected_domain = get_domain(expected_url)

    return expected_domain in candidate_domain or candidate_domain in expected_domain


def validate_career_page(url: str, company_website_url: str) -> ValidationResult:
    """
    Career pages should usually live on the company's own domain.

    Example:
    https://stripe.com/jobs is valid for https://stripe.com
    """
    if domain_contains(url, company_website_url):
        return ValidationResult(
            is_valid=True,
            reason="Career page is on the company domain.",
        )

    return ValidationResult(
        is_valid=False,
        reason="Career page is not on the company domain.",
    )


def validate_job_url(
    url: str,
    company_name: str,
    company_website_url: str,
) -> ValidationResult:
    """
    url_lower = url.lower()
    candidate_domain = get_domain(url)
    company_slug = normalize_company_name(company_name)

    for blocked_domain in BLOCKED_JOB_BOARD_DOMAINS:
        if blocked_domain in candidate_domain:
            return ValidationResult(
                is_valid=False,
                reason=f"Rejected generic job board domain: {blocked_domain}.",
            )

    if domain_contains(url, company_website_url):
        return ValidationResult(
            is_valid=True,
            reason="Job URL is on the company domain.",
        )

    is_known_ats = any(ats_domain in candidate_domain for ats_domain in KNOWN_ATS_DOMAINS)

    if is_known_ats and company_slug in url_lower:
        return ValidationResult(
            is_valid=True,
            reason="Job URL is on a known ATS domain and contains the company slug.",
        )

    return ValidationResult(
        is_valid=False,
        reason="Job URL does not match company domain or company-specific ATS path.",
    )
