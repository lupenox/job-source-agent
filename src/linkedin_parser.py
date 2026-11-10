import logging
import os
from dataclasses import dataclass
from typing import Optional

from apify_client import ApifyClient
from dotenv import load_dotenv

from src.crawler import WebCrawler

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_APIFY_ACTOR_ID = "johnvc/linkedin-company-api"


def is_linkedin_job_url(url: str) -> bool:
    """Return True if the URL points to a LinkedIn job posting rather than a company profile."""
    return "linkedin.com/jobs" in url.lower()


async def extract_company_from_linkedin_job_page(
    job_url: str,
    crawler: Optional[WebCrawler] = None,
) -> dict[str, str]:
    """
    Extract the company name and LinkedIn company profile URL from a public LinkedIn job page.
    """
    active_crawler = crawler or WebCrawler()
    links = await active_crawler.get_links(job_url)

    for link in links:
        href = link.get("url", "")
        text = link.get("text", "").strip()

        if "linkedin.com/company/" in href and text:
            return {
                "company_name": text,
                "company_linkedin_url": href,
                "status": "success",
            }

    return {
        "status": "failed",
        "reason": "Could not find a LinkedIn company link on the job listing page.",
    }


@dataclass
class LinkedInApiResult:
    company_name: Optional[str] = None
    company_website_url: Optional[str] = None
    status: str = "not_configured"
    reason: Optional[str] = None


class LinkedInCrawlerApi:
    """
    Adapter for extracting official company metadata (name + website URL) from LinkedIn.

    Why use Apify (`johnvc/linkedin-company-api`) instead of scraping LinkedIn directly?
    LinkedIn aggressively blocks headless browsers and requires authenticated sessions for company
    "About" pages. Delegating LinkedIn enrichment to a managed actor isolates anti-bot maintenance
    from our core career-page discovery agent, while `use_mock=True` allows zero-cost local testing.
    """

    def __init__(self, use_mock: bool = False):
        self.apify_token = os.getenv("APIFY_API_TOKEN")
        self.use_mock = use_mock or not self.apify_token
        self.actor_id = os.getenv("APIFY_ACTOR_ID", DEFAULT_APIFY_ACTOR_ID)

    def is_configured(self) -> bool:
        return bool(self.apify_token) and not self.use_mock

    async def resolve_company(
        self,
        linkedin_url: str,
        crawler: Optional[WebCrawler] = None,
    ) -> LinkedInApiResult:
        """
        Resolve either a LinkedIn job listing URL or a LinkedIn company profile URL
        into a `LinkedInApiResult` containing `company_name` and `company_website_url`.
        """
        if is_linkedin_job_url(linkedin_url):
            logger.info("Detected LinkedIn job listing URL: %s", linkedin_url)
            if self.use_mock:
                return self._mock_result(linkedin_url)

            job_result = await extract_company_from_linkedin_job_page(linkedin_url, crawler=crawler)
            if job_result.get("status") != "success":
                return LinkedInApiResult(
                    status="failed",
                    reason=job_result.get("reason", "Failed to extract company from job listing page."),
                )
            linkedin_url = job_result["company_linkedin_url"]

        return self.fetch_company_info(linkedin_url)

    def _mock_result(self, linkedin_url: str) -> LinkedInApiResult:
        """Deterministic mock responses for local testing and demos without spending API credits."""
        url_lower = linkedin_url.lower()

        if "stripe" in url_lower or "1234567890" in url_lower:
            return LinkedInApiResult(
                company_name="Stripe",
                company_website_url="https://stripe.com",
                status="success_mock",
                reason="Mock data for Stripe",
            )
        if "vercel" in url_lower:
            return LinkedInApiResult(
                company_name="Vercel",
                company_website_url="https://vercel.com",
                status="success_mock",
                reason="Mock data for Vercel",
            )
        if "openai" in url_lower:
            return LinkedInApiResult(
                company_name="OpenAI",
                company_website_url="https://openai.com",
                status="success_mock",
                reason="Mock data for OpenAI",
            )
        return LinkedInApiResult(
            company_name="Example Corp",
            company_website_url="https://example.com",
            status="success_mock",
            reason="Generic mock data",
        )

    def fetch_company_info(self, linkedin_url: str) -> LinkedInApiResult:
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
            run_input = {"companyUrls": [linkedin_url]}

            logger.info("Calling Apify actor %s for %s", self.actor_id, linkedin_url)
            run = client.actor(self.actor_id).call(run_input=run_input)

            dataset_id = run.default_dataset_id
            items = list(client.dataset(dataset_id).iterate_items())

            if not items:
                return LinkedInApiResult(
                    status="failed",
                    reason="Apify returned no results. Check the LinkedIn URL.",
                )

            item = items[0]
            if item.get("error_message"):
                return LinkedInApiResult(
                    status="failed",
                    reason=f"Apify error: {item['error_message']}",
                )

            # Support both top-level fields (`johnvc/linkedin-company-api`)
            # and nested `company` objects (`zhorex/linkedin-company-enrichment`).
            company = item.get("company") if isinstance(item.get("company"), dict) else {}
            name = item.get("name") or company.get("name")
            website = item.get("website") or company.get("website")

            if not name or not website:
                return LinkedInApiResult(
                    status="failed",
                    reason="Apify response missing name or website field.",
                )

            normalized_website = website if website.startswith("http") else f"https://{website}"
            return LinkedInApiResult(
                company_name=name,
                company_website_url=normalized_website,
                status="success",
            )

        except Exception as exc:
            logger.exception("Apify call failed")
            return LinkedInApiResult(
                status="failed",
                reason=f"Apify error: {exc}",
            )
