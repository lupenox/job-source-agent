from urllib.parse import urljoin

from playwright.async_api import async_playwright


class WebCrawler:
    async def get_links(self, page_url: str) -> list[dict[str, str]]:
        """
        Load a page with Playwright and return all anchor links found on it.
        Each link includes visible text and an absolute URL.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            await page.goto(page_url, wait_until="domcontentloaded", timeout=30000)

            links = await page.locator("a").evaluate_all(
                """
                anchors => anchors.map(a => ({
                    text: a.innerText || "",
                    href: a.getAttribute("href") || ""
                }))
                """
            )

            await browser.close()

        cleaned_links = []

        for link in links:
            href = link.get("href", "").strip()
            text = link.get("text", "").strip()

            if not href:
                continue

            absolute_url = urljoin(page_url, href)

            cleaned_links.append(
                {
                    "url": absolute_url,
                    "text": text,
                }
            )

        return cleaned_links