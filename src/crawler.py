from urllib.parse import urljoin
import random
from playwright.async_api import async_playwright

# Common realistic user agents to reduce blocking
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]


class WebCrawler:
    async def get_links(self, page_url: str) -> list[dict[str, str]]:
        """
        Load page with Playwright + basic stealth and return all anchor links.
        """
        user_agent = random.choice(USER_AGENTS)

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            context = await browser.new_context(
                user_agent=user_agent,
                viewport={"width": 1366, "height": 768},
                locale="en-US",
            )
            page = await context.new_page()

            # Light stealth
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
            """)

            try:
                await page.goto(page_url, wait_until="domcontentloaded", timeout=45000)
                # Give JS frameworks a moment
                await page.wait_for_timeout(1500)
            except Exception as e:
                print(f"[Crawler] Warning: {e}")
                await browser.close()
                return []

            links = await page.locator("a").evaluate_all(
                """
                anchors => anchors.map(a => ({
                    text: (a.innerText || a.textContent || "").trim(),
                    href: a.getAttribute("href") || ""
                }))
                """
            )

            await browser.close()

        cleaned_links = []
        for link in links:
            href = (link.get("href") or "").strip()
            text = (link.get("text") or "").strip()

            if not href or href.startswith(("javascript:", "mailto:", "tel:")):
                continue

            absolute_url = urljoin(page_url, href)
            cleaned_links.append({"url": absolute_url, "text": text})

        return cleaned_links
