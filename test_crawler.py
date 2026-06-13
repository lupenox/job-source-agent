import asyncio
from src.crawler import WebCrawler


async def main():
    crawler = WebCrawler()
    links = await crawler.get_links("https://stripe.com")

    print(f"Found {len(links)} links")

    for link in links[:20]:
        print(link)


if __name__ == "__main__":
    asyncio.run(main())