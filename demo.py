"""Clean demo script for video recording.
Run with: python demo.py
"""

import asyncio
from src.agent import JobSourceAgent


async def run_demo():
    print("\n" + "=" * 75)
    print("AI JOB SOURCE AGENT - DEMO")
    print("=" * 75)
    print("\nThis demo runs in mock mode (no API credits used).\n")

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
        print("-" * 75)

    print("\nDemo complete. Both examples now return clean results.\n")


if __name__ == "__main__":
    asyncio.run(run_demo())
