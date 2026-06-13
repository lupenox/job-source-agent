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


def keyword_matches(keyword: str, text: str) -> bool:
    pattern = r"\b" + re.escape(keyword) + r"\b"
    return re.search(pattern, text, re.IGNORECASE) is not None


def score_career_link(url: str, text: str) -> tuple[int, list[str]]:
    score = 0
    evidence = []

    combined = f"{url} {text}".lower()

    for keyword in CAREER_KEYWORDS:
        if keyword_matches(keyword, combined):
            score += 5
            evidence.append(f"Matched career keyword: {keyword}")

    return score, evidence


def score_job_link(url: str, text: str) -> tuple[int, list[str]]:
    score = 0
    evidence = []

    combined = f"{url} {text}".lower()

    for keyword in JOB_KEYWORDS:
        if keyword_matches(keyword, combined):
            score += 3
            evidence.append(f"Matched job keyword: {keyword}")

    return score, evidence
