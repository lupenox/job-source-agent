from dataclasses import dataclass, field
from enum import Enum


class AgentStatus(str, Enum):
    SUCCESS = "success"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"


@dataclass
class CandidateLink:
    """
    A link discovered by the crawler.

    Example:
    - company careers page candidate
    - open job posting candidate
    """

    url: str
    text: str = ""
    score: int = 0
    evidence: list[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """
    Result returned by the validator after checking whether
    a discovered URL matches the expected company/job source.
    """

    is_valid: bool
    reason: str


@dataclass
class JobSourceResult:
    """
    Final output for Task 2.

    Required challenge output:
    - company name
    - career page URL
    - open position URL

    Extra fields:
    - confidence
    - evidence
    - status
    """

    company_name: str
    company_website_url: str
    career_page_url: str | None
    open_position_url: str | None
    confidence: float
    evidence: list[str] = field(default_factory=list)
    status: AgentStatus = AgentStatus.NEEDS_REVIEW