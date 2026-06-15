"""Clean demo script for video recording.
Run with: python demo.py
"""

import asyncio
from src.agent import JobSourceAgent
from src.linkedin_parser import LinkedInCrawlerApi


async def run_demo():
    print("\n" + "=" * 70)
    print("AI JOB SOURCE AGENT - DEMO")
    print("=" * 70)

    # Using mock mode for reliable demo recording
    linkedin_api = LinkedInCrawlerApi(use_mock=True)
    agent = JobSourceAgent(use_llm_reranker=True)

    companies = [
        ("Stripe", "https://stripe.com"),
        ("Vercel", "https://vercel.com"),
    ]

    for company_name, website in companies:
        print(f"\n>>> Processing: {company_name}")
        result = await agent.find_job_source(company_name, website)

        print(f"Company Name       : {result.company_name}")
        print(f"Career Page        : {result.career_page_url or 'NOT FOUND'}")
        print(f"Open Position      : {result.open_position_url or 'NOT FOUND'}")
        print(f"Challenge Format   : {result.to_challenge_format()}")
        print("-" * 70)

    print("\nDemo complete.\n")


if __name__ == "__main__":
    asyncio.run(run_demo())
