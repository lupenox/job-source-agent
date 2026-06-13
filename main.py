import argparse
import asyncio
import json
import logging
from dataclasses import asdict
from urllib.parse import urlparse

from dotenv import load_dotenv

from src.agent import JobSourceAgent
from src.crawler import WebCrawler
from src.linkedin_parser import LinkedInCrawlerApi

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def is_linkedin_job_url(url: str) -> bool:
    """Check if the URL looks like a LinkedIn job listing page."""
    lowered = url.lower()
    return "linkedin.com/jobs" in lowered


async def extract_company_from_linkedin_job_page(job_url: str) -> dict:
    """
    Try to extract company name and LinkedIn company URL from a job listing page.
    Returns a dict with company_name and company_linkedin_url if successful.
    """
    crawler = WebCrawler()
    links = await crawler.get_links(job_url)

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


async def main():
    parser = argparse.ArgumentParser(
        description="AI Job Source Agent - Part 2 Take-Home Challenge\n"
                    "Supports LinkedIn job listing pages and company pages"
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--linkedin-url",
        help="LinkedIn job listing or company page URL"
    )
    group.add_argument(
        "--company-name",
        help="Company name (use together with --company-url)"
    )

    parser.add_argument(
        "--company-url",
        help="Official company website (required if using --company-name)"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Force mock mode for LinkedIn (no API credits used)"
    )
    parser.add_argument(
        "--output-format",
        choices=["json", "csv"],
        default="json",
        help="Output format (default: json)"
    )

    args = parser.parse_args()

    linkedin_api = LinkedInCrawlerApi(use_mock=args.mock)

    if args.linkedin_url:
        logger.info(f"Starting from LinkedIn URL: {args.linkedin_url}")

        if is_linkedin_job_url(args.linkedin_url):
            logger.info("Detected LinkedIn job listing page. Extracting company info...")
            job_result = await extract_company_from_linkedin_job_page(args.linkedin_url)

            if job_result.get("status") != "success" or not job_result.get("company_linkedin_url"):
                print("Failed to extract company from job listing page.")
                print(json.dumps(job_result, indent=2))
                return

            # Enrich the company using the extracted LinkedIn company URL
            linkedin_result = linkedin_api.fetch_company_info(job_result["company_linkedin_url"])
        else:
            # Normal company page flow
            linkedin_result = linkedin_api.fetch_company_info(args.linkedin_url)

        if linkedin_result.status not in ("success", "success_mock"):
            print(json.dumps(asdict(linkedin_result), indent=2))
            return

        company_name = linkedin_result.company_name
        company_website_url = linkedin_result.company_website_url
        logger.info(f"LinkedIn resolved \u2192 {company_name} | {company_website_url}")
    else:
        if not args.company_url:
            parser.error("--company-url is required when using --company-name")
        company_name = args.company_name
        company_website_url = args.company_url

    # Run the core web agent
    agent = JobSourceAgent()
    result = await agent.find_job_source(
        company_name=company_name,
        company_website_url=company_website_url,
    )

    # Print in the exact format requested by the challenge
    print("\n" + "=" * 70)
    print("AI JOB SOURCE AGENT - FINAL RESULT (Challenge Format)")
    print("=" * 70)
    print(f"Company Name       : {result.company_name}")
    print(f"Career Page URL    : {result.career_page_url or 'NOT FOUND'}")
    print(f"Open Position URL  : {result.open_position_url or 'NOT FOUND'}")
    print("=" * 70)

    if args.output_format == "json":
        print("\nFull structured result:")
        print(json.dumps(asdict(result), indent=2))
    else:
        print(f"\n{result.company_name},{result.career_page_url or ''},{result.open_position_url or ''}")


if __name__ == "__main__":
    asyncio.run(main())
