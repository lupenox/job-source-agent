import argparse
import asyncio
import json
import logging
from dataclasses import asdict

from dotenv import load_dotenv

from src.agent import JobSourceAgent
from src.crawler import WebCrawler
from src.linkedin_parser import LinkedInCrawlerApi

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def is_linkedin_job_url(url: str) -> bool:
    lowered = url.lower()
    return "linkedin.com/jobs" in lowered


async def extract_company_from_linkedin_job_page(job_url: str) -> dict:
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
        description="AI Job Source Agent - Part 2 Take-Home Challenge"
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--linkedin-url", help="LinkedIn job listing or company page URL")
    group.add_argument("--company-name", help="Company name (use with --company-url)")

    parser.add_argument("--company-url", help="Official company website")
    parser.add_argument("--mock", action="store_true", help="Use mock mode (no API calls)")
    parser.add_argument("--no-llm", action="store_true", help="Disable LLM reranking")
    parser.add_argument("--output-format", choices=["json", "text"], default="text", help="Output format")

    args = parser.parse_args()

    linkedin_api = LinkedInCrawlerApi(use_mock=args.mock)

    if args.linkedin_url:
        logger.info(f"Starting from LinkedIn URL: {args.linkedin_url}")

        if is_linkedin_job_url(args.linkedin_url):
            logger.info("Detected LinkedIn job listing page")
            job_result = await extract_company_from_linkedin_job_page(args.linkedin_url)

            if job_result.get("status") != "success":
                print("Failed to extract company from job listing page.")
                return

            linkedin_result = linkedin_api.fetch_company_info(job_result["company_linkedin_url"])
        else:
            linkedin_result = linkedin_api.fetch_company_info(args.linkedin_url)

        if linkedin_result.status not in ("success", "success_mock"):
            print(json.dumps(asdict(linkedin_result), indent=2))
            return

        company_name = linkedin_result.company_name
        company_website_url = linkedin_result.company_website_url
    else:
        if not args.company_url:
            parser.error("--company-url is required when using --company-name")
        company_name = args.company_name
        company_website_url = args.company_url

    use_llm = not args.no_llm
    agent = JobSourceAgent(use_llm_reranker=use_llm)
    result = await agent.find_job_source(company_name, company_website_url)

    # Clean demo-friendly output
    print("\n" + "=" * 75)
    print("AI JOB SOURCE AGENT - FINAL RESULT")
    print("=" * 75)
    print(f"Company Name       : {result.company_name}")
    print(f"Company Website    : {result.company_website_url}")
    print(f"Career Page URL    : {result.career_page_url or 'NOT FOUND'}")
    print(f"Open Position URL  : {result.open_position_url or 'NOT FOUND'}")
    print(f"Status             : {result.status.value}")
    print(f"Confidence         : {result.confidence}")
    print("=" * 75)

    if args.output_format == "json":
        print("\nFull JSON:")
        print(json.dumps(asdict(result), indent=2))
    else:
        print(f"\nChallenge Format : {result.to_challenge_format()}")


if __name__ == "__main__":
    asyncio.run(main())
