import asyncio
import logging
import random
from urllib.parse import urljoin

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

# Common realistic user agents to reduce basic bot-blocking on marketing/career sites
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

IGNORED_SCHEMES = ("javascript:", "mailto:", "tel:")


def retry_async(max_attempts: int = 2, base_delay: float = 1.0):
    """Retry decorator with linear backoff for transient network/navigation errors."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    if attempt < max_attempts:
                        logger.warning(
                            "Attempt %d/%d failed for %s (%s). Retrying...",
                            attempt,
                            max_attempts,
                            func.__name__,
                            exc,
                        )
                        await asyncio.sleep(base_delay * attempt)
            raise last_exc
        return wrapper
    return decorator


class WebCrawler:
    """
    Playwright-based link extractor.

    Why Playwright instead of `requests` + `BeautifulSoup`?
    Modern career portals (Ashby, Greenhouse embeds, React/Next.js sites) render job
    links client-side via JavaScript. A headless browser ensures those links exist in the DOM.
    """

    def __init__(self, timeout_ms: int = 45_000, settle_delay_ms: int = 1_500):
        self.timeout_ms = timeout_ms
        self.settle_delay_ms = settle_delay_ms

    async def get_links(self, page_url: str) -> list[dict[str, str]]:
        """
        Navigate to `page_url` and return deduplicated absolute anchor links:
        `[{"url": "https://...", "text": "Anchor text"}, ...]`.
        """
        try:
            raw_links = await self._fetch_raw_links(page_url)
        except Exception as exc:
            logger.warning("[Crawler] Failed to load %s: %s", page_url, exc)
            return []

        return self._normalize_links(page_url, raw_links)

    @retry_async(max_attempts=2, base_delay=1.0)
    async def _fetch_raw_links(self, page_url: str) -> list[dict[str, str]]:
        user_agent = random.choice(USER_AGENTS)

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            try:
                context = await browser.new_context(
                    user_agent=user_agent,
                    viewport={"width": 1366, "height": 768},
                    locale="en-US",
                )
                page = await context.new_page()

                # Mask basic automation fingerprints
                await page.add_init_script(
                    """
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
                    """
                )

                await page.goto(page_url, wait_until="domcontentloaded", timeout=self.timeout_ms)
                # Allow client-side SPA routers a brief window to hydrate anchor tags
                await page.wait_for_timeout(self.settle_delay_ms)

                return await page.locator("a").evaluate_all(
                    """
                    anchors => anchors.map(a => ({
                        text: (a.innerText || a.textContent || "").trim(),
                        href: a.getAttribute("href") || ""
                    }))
                    """
                )
            finally:
                await browser.close()

    @staticmethod
    def _normalize_links(page_url: str, raw_links: list[dict[str, str]]) -> list[dict[str, str]]:
        cleaned_links: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()

        for link in raw_links:
            href = (link.get("href") or "").strip()
            text = (link.get("text") or "").strip()

            # Ignore empty hrefs, bare '#' placeholders, and non-HTTP schemes,
            # while preserving hash-routed SPA paths such as '#/careers'.
            if not href or href == "#" or href.lower().startswith(IGNORED_SCHEMES):
                continue

            absolute_url = urljoin(page_url, href)
            key = (absolute_url, text)
            if key in seen:
                continue
            seen.add(key)

            cleaned_links.append({"url": absolute_url, "text": text})

        return cleaned_links
