import re
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

CORPORATE_SUFFIXES = (
    "incorporated",
    "corporation",
    "company",
    "limited",
    "inc",
    "llc",
    "ltd",
    "corp",
    "co",
    "ai",
    "hq",
)


def normalize_company_name(company_name: str) -> str:
    """
    Convert company names into simple alphanumeric slugs for comparison.

    Example:
    "Stripe, Inc." -> "stripeinc"
    """
    return "".join(ch for ch in company_name.lower() if ch.isalnum())


def extract_company_slugs(company_name: str, company_website_url: str = "") -> set[str]:
    """
    Produce candidate slugs for matching company-specific ATS URLs.

    Why multiple slugs?
    LinkedIn often returns legal entity names like "Stripe, Inc." or "Vercel Inc.".
    Normalizing naively gives "stripeinc", whereas the ATS board URL is
    `https://jobs.lever.co/stripe/...`. Generating both the full slug ("stripeinc"),
    the suffix-stripped slug ("stripe"), and the website domain root ("stripe")
    prevents false negatives while staying strict against unrelated companies.
    """
    slugs: set[str] = set()

    full_slug = normalize_company_name(company_name)
    if full_slug:
        slugs.add(full_slug)

    # Strip common legal suffixes at word boundaries (e.g. "Stripe, Inc." -> "stripe")
    tokens = [tok for tok in re.split(r"[^a-z0-9]+", company_name.lower()) if tok]
    while len(tokens) > 1 and tokens[-1] in CORPORATE_SUFFIXES:
        tokens.pop()
    core_slug = "".join(tokens)
    if len(core_slug) >= 2:
        slugs.add(core_slug)

    # Also include the root label of the official domain (e.g., "stripe.com" -> "stripe")
    if company_website_url:
        domain = get_domain(company_website_url)
        domain_root = domain.split(".")[0] if domain else ""
        if len(domain_root) >= 2:
            slugs.add(domain_root)

    return slugs


def get_domain(url: str) -> str:
    """
    Extract normalized base domain from a URL (strips `www.` and subdomains).

    Examples:
    "https://www.stripe.com/jobs" -> "stripe.com"
    "https://careers.openai.com" -> "openai.com"
    """
    netloc = urlparse(url).netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    parts = [part for part in netloc.split(".") if part]
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return netloc


def domain_contains(candidate_url: str, expected_url: str) -> bool:
    """Return True if both URLs have non-empty domains that match."""
    candidate_domain = get_domain(candidate_url)
    expected_domain = get_domain(expected_url)

    if not candidate_domain or not expected_domain:
        return False

    return expected_domain in candidate_domain or candidate_domain in expected_domain


def validate_career_page(url: str, company_website_url: str) -> ValidationResult:
    """
    Career pages discovered on the homepage should live on the company's own domain.

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
    Validate that an open job position URL belongs to the target company.

    Accepts:
    1. Links on the company's official domain (e.g. `stripe.com/jobs/engineer`)
    2. Links on a known Applicant Tracking System (ATS) domain (Lever, Greenhouse, Ashby, etc.)
       whose URL contains the company's slug (e.g. `jobs.lever.co/stripe/123`).

    Rejects:
    - Third-party aggregator job boards (LinkedIn, Indeed, Glassdoor, etc.)
    - Unrelated external domains
    """
    url_lower = url.lower()
    candidate_domain = get_domain(url)
    if not candidate_domain:
        return ValidationResult(
            is_valid=False,
            reason="Job URL is missing a valid domain.",
        )

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
    company_slugs = extract_company_slugs(company_name, company_website_url)

    if is_known_ats and any(slug in url_lower for slug in company_slugs):
        return ValidationResult(
            is_valid=True,
            reason="Job URL is on a known ATS domain and contains the company slug.",
        )

    return ValidationResult(
        is_valid=False,
        reason="Job URL does not match company domain or company-specific ATS path.",
    )
