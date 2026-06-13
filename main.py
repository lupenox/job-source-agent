import argparse
import asyncio
import json
import logging
import os
from dataclasses import asdict

from dotenv import load_dotenv

from src.agent import JobSourceAgent
from src.linkedin_parser import LinkedInCrawlerApi

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(
        description="AI Job Source Agent - Part 2 Take-Home Challenge\n"
                    "Starts from LinkedIn \u2192 company website \u2192 career page \u2192 one open position"
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--linkedin-url",
        help="LinkedIn company page URL (e.g. https://www.linkedin.com/company/stripe)"
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
        # Simple CSV line
        print(f"\n{result.company_name},{result.career_page_url or ''},{result.open_position_url or ''}")


if __name__ == "__main__":
    asyncio.run(main())
