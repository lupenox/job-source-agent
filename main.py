import argparse
import asyncio
import json
import logging
from dataclasses import asdict

from dotenv import load_dotenv

from src.agent import JobSourceAgent
from src.linkedin_parser import (
    LinkedInCrawlerApi,
    extract_company_from_linkedin_job_page,
    is_linkedin_job_url,
)

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AI Job Source Agent - Part 2 Take-Home Challenge"
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--linkedin-url", help="LinkedIn job listing or company page URL")
    group.add_argument("--company-name", help="Company name (use with --company-url)")

    parser.add_argument("--company-url", help="Official company website")
    parser.add_argument("--mock", action="store_true", help="Use mock mode for LinkedIn lookup")
    parser.add_argument("--no-llm", action="store_true", help="Disable Gemini LLM reranking")
    parser.add_argument(
        "--output-format",
        choices=["json", "text"],
        default="text",
        help="Output format (default: text)",
    )
    return parser


def print_result(result, output_format: str) -> None:
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

    if output_format == "json":
        print("\nFull JSON:")
        print(json.dumps(asdict(result), indent=2))
    else:
        print(f"\nChallenge Format : {result.to_challenge_format()}")


async def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.linkedin_url:
        logger.info("Starting from LinkedIn URL: %s", args.linkedin_url)
        linkedin_api = LinkedInCrawlerApi(use_mock=args.mock)
        linkedin_result = await linkedin_api.resolve_company(args.linkedin_url)

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

    agent = JobSourceAgent(use_llm_reranker=not args.no_llm)
    result = await agent.find_job_source(company_name, company_website_url)
    print_result(result, args.output_format)


if __name__ == "__main__":
    asyncio.run(main())
