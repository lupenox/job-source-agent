import argparse
import asyncio
import json
import logging
from dataclasses import asdict

from dotenv import load_dotenv

from src.agent import JobSourceAgent
from src.linkedin_parser import LinkedInCrawlerApi

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(
        description="AI Job Source Agent - Jobnova Take-Home Challenge (Part 2)"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--linkedin-url", help="LinkedIn company page URL")
    group.add_argument("--company-name", help="Company name (with --company-url)")

    parser.add_argument("--company-url", help="Company website URL")
    parser.add_argument("--mock", action="store_true", help="Use mock mode (no API calls)")
    parser.add_argument("--quiet", action="store_true", help="Only show final result")

    args = parser.parse_args()

    if not args.quiet:
        print("\n" + "="*70)
        print("🚀 AI JOB SOURCE AGENT - Starting...")
        print("="*70)

    linkedin_api = LinkedInCrawlerApi(use_mock=args.mock)

    if args.linkedin_url:
        if not args.quiet:
            print(f"\n📍 Step 1: Fetching company info from LinkedIn...")
        linkedin_result = linkedin_api.fetch_company_info(args.linkedin_url)

        if linkedin_result.status not in ("success", "success_mock"):
            print(json.dumps(asdict(linkedin_result), indent=2))
            return

        company_name = linkedin_result.company_name
        company_website_url = linkedin_result.company_website_url
    else:
        if not args.company_url:
            parser.error("--company-url is required with --company-name")
        company_name = args.company_name
        company_website_url = args.company_url

    if not args.quiet:
        print(f"✅ Company: {company_name}")
        print(f"✅ Website: {company_website_url}\n")

    # Run the agent
    agent = JobSourceAgent()
    result = await agent.find_job_source(company_name, company_website_url)

    print("\n" + "="*70)
    print("✅ FINAL RESULT (Challenge Format)")
    print("="*70)
    print(f"Company Name       : {result.company_name}")
    print(f"Career Page URL    : {result.career_page_url or 'NOT FOUND'}")
    print(f"Open Position URL  : {result.open_position_url or 'NOT FOUND'}")
    print(f"Status             : {result.status.value.upper()}")
    print(f"Confidence         : {result.confidence:.0%}")
    print("="*70 + "\n")

    if not args.quiet:
        print("📋 Full structured result:")
        print(json.dumps(asdict(result), indent=2))


if __name__ == "__main__":
    asyncio.run(main())