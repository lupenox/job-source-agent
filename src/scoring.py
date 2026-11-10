import re

CAREER_KEYWORDS = [
    "careers",
    "career",
    "jobs",
    "job",
    "open roles",
    "open positions",
    "join us",
    "join our team",
    "work with us",
]

JOB_KEYWORDS = [
    "software engineer",
    "engineer",
    "developer",
    "intern",
    "apply",
    "role",
    "position",
]

JOB_SEARCH_PAGE_SIGNALS = [
    "open roles",
    "see open roles",
    "open positions",
    "search jobs",
    "/jobs/search",
    "/careers/search",
]

CAREER_KEYWORD_WEIGHT = 5
JOB_KEYWORD_WEIGHT = 3


def keyword_matches(keyword: str, text: str) -> bool:
    """Return True if `keyword` appears as a whole word/phrase in `text` (case-insensitive)."""
    pattern = r"\b" + re.escape(keyword) + r"\b"
    return re.search(pattern, text, re.IGNORECASE) is not None


def looks_like_job_search_page(url: str, text: str) -> bool:
    """
    Detect intermediate "See Open Roles" / "/jobs/search" directory links
    that sit between a marketing careers splash page and individual job postings.
    """
    combined = f"{url} {text}".lower()
    return any(signal in combined for signal in JOB_SEARCH_PAGE_SIGNALS)


def _score_by_keywords(
    url: str,
    text: str,
    keywords: list[str],
    weight: int,
    label: str,
) -> tuple[int, list[str]]:
    score = 0
    evidence: list[str] = []
    combined = f"{url} {text}".lower()

    for keyword in keywords:
        if keyword_matches(keyword, combined):
            score += weight
            evidence.append(f"Matched {label} keyword: {keyword}")

    return score, evidence


def score_career_link(url: str, text: str) -> tuple[int, list[str]]:
    """Score how likely a link points to a company's careers page."""
    return _score_by_keywords(url, text, CAREER_KEYWORDS, CAREER_KEYWORD_WEIGHT, "career")


def score_job_link(url: str, text: str) -> tuple[int, list[str]]:
    """Score how likely a link points to an individual open job posting."""
    return _score_by_keywords(url, text, JOB_KEYWORDS, JOB_KEYWORD_WEIGHT, "job")
