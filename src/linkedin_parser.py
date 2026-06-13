import os
from dataclasses import dataclass

import requests


@dataclass
class LinkedInApiResult:
    company_name: str | None
    company_website_url: str | None
    status: str
    reason: str | None = None


class LinkedInCrawlerApi:
    """
    Adapter for a third-party LinkedIn crawler API.

    This is intentionally generic so the project can support services like
    Bright Data, Apify, Proxycurl, RapidAPI providers, etc. without locking
    the core agent to one vendor.
    """

    def __init__(self):
        self.api_url = os.getenv("LINKEDIN_CRAWLER_API_URL")
        self.api_key = os.getenv("LINKEDIN_CRAWLER_API_KEY")

    def is_configured(self) -> bool:
        return bool(self.api_url and self.api_key)

    def fetch_job_info(self, linkedin_url: str) -> LinkedInApiResult:
        if not self.is_configured():
            return LinkedInApiResult(
                company_name=None,
                company_website_url=None,
                status="not_configured",
                reason="Third-party LinkedIn crawler API is not configured.",
            )

        response = requests.post(
            self.api_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={"url": linkedin_url},
            timeout=30,
        )

        if response.status_code >= 400:
            return LinkedInApiResult(
                company_name=None,
                company_website_url=None,
                status="failed",
                reason=f"LinkedIn crawler API returned HTTP {response.status_code}.",
            )

        data = response.json()

        return LinkedInApiResult(
            company_name=data.get("company_name"),
            company_website_url=data.get("company_website_url") or data.get("company_url"),
            status="success",
        )