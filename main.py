import argparse
import asyncio
import json
from dataclasses import asdict

from src.agent import JobSourceAgent


async def main():
    parser = argparse.ArgumentParser(
        description="Browser-based job source discovery agent"
    )

    parser.add_argument("--company-name", required=True)
    parser.add_argument("--company-url", required=True)

    args = parser.parse_args()

    agent = JobSourceAgent()
    result = await agent.find_job_source(
        company_name=args.company_name,
        company_website_url=args.company_url,
    )

    print(json.dumps(asdict(result), indent=2))


if __name__ == "__main__":
    asyncio.run(main())