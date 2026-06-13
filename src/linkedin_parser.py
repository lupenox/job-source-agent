import os
import logging
from dataclasses import dataclass
from typing import Optional

from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class LinkedInApiResult:
    company_name: Optional[str] = None
    company_website_url: Optional[str] = None
    status: str = "not_configured"
    reason: Optional[str] = None


class LinkedInCrawlerApi:
    """
    Production-ready adapter for LinkedIn company data extraction.

    Supports:
    - Apify zhorex/linkedin-company-enrichment (recommended, no login needed)
    - Mock mode for testing without API credits
    - Easy to swap in Bright Data or other providers later
    """

    def __init__(self, use_mock: bool = False):
        self.apify_token = os.getenv("APIFY_API_TOKEN")
        self.use_mock = use_mock or not self.apify_token
        self.actor_id = "zhorex/linkedin-company-enrichment"  # Excellent no-login actor

    def is_configured(self) -> bool:
        return bool(self.apify_token) and not self.use_mock

    def _mock_result(self, linkedin_url: str) -> LinkedInApiResult:
        """Safe mock for demo / testing the full pipeline without spending credits."""
        # Common test companies
        if "stripe" in linkedin_url.lower():
            return LinkedInApiResult(
                company_name="Stripe",
                company_website_url="https://stripe.com",
                status="success_mock",
                reason="Mock data for Stripe (demo mode)",
            )
        if "openai" in linkedin_url.lower():
            return LinkedInApiResult(
                company_name="OpenAI",
                company_website_url="https://openai.com",
                status="success_mock",
                reason="Mock data for OpenAI (demo mode)",
            )
        # Generic fallback mock
        return LinkedInApiResult(
            company_name="Example Corp",
            company_website_url="https://example.com",
            status="success_mock",
            reason="Generic mock data - replace with real LinkedIn URL + API token",
        )

    def fetch_company_info(self, linkedin_url: str) -> LinkedInApiResult:
        """
        Extract company name + official website from a LinkedIn company page.
        Input example: https://www.linkedin.com/company/stripe
        """
        if self.use_mock:
            logger.info("Using MOCK mode for LinkedIn (no API token or use_mock=True)")
            return self._mock_result(linkedin_url)

        if not self.is_configured():
            return LinkedInApiResult(
                status="not_configured",
                reason="APIFY_API_TOKEN not set. Get one free at https://apify.com",
            )

        try:
            client = ApifyClient(self.apify_token)

            run_input = {
                "companyUrls": [linkedin_url],
                "extractEmployees": False,      # keep cost low for demo
                "enableAiEnrichment": False,
            }

            logger.info(f"Calling Apify actor {self.actor_id} for {linkedin_url}")
            run = client.actor(self.actor_id).call(run_input=run_input)

            items = list(client.dataset(run["defaultDatasetId"]).iterate_items())

            if not items:
                return LinkedInApiResult(
                    status="failed",
                    reason="Apify returned no results. Check the LinkedIn URL.",
                )

            item = items[0]
            company = item.get("company", {})

            name = company.get("name")
            website = company.get("website")

            if not name or not website:
                return LinkedInApiResult(
                    status="failed",
                    reason="Apify response missing name or website field.",
                )

            return LinkedInApiResult(
                company_name=name,
                company_website_url=website if website.startswith("http") else f"https://{website}",
                status="success",
            )

        except Exception as e:
            logger.exception("Apify call failed")
            return LinkedInApiResult(
                status="failed",
                reason=f"Apify error: {str(e)}",
            )


# Backwards-compatible alias (old method name used in early scaffolding)
class LinkedInCrawlerApiOld(LinkedInCrawlerApi):
    def fetch_job_info(self, linkedin_url: str) -> LinkedInApiResult:
        return self.fetch_company_info(linkedin_url)
