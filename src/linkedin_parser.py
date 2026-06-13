from dataclasses import dataclass

from playwright.async_api import async_playwright


@dataclass
class LinkedInJobInfo:
    company_name: str | None
    company_website_url: str | None
    status: str
    reason: str | None = None


class LinkedInParser:
    async def parse_job_listing(self, linkedin_url: str) -> LinkedInJobInfo:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                await page.goto(linkedin_url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(3000)

                page_text = await page.locator("body").inner_text(timeout=10000)
                title = await page.title()

                # LinkedIn commonly blocks/logs out automated sessions.
                blocked_signals = [
                    "sign in",
                    "join linkedin",
                    "authwall",
                    "security verification",
                    "captcha",
                ]

                combined = f"{title}\n{page_text}".lower()

                if any(signal in combined for signal in blocked_signals):
                    return LinkedInJobInfo(
                        company_name=None,
                        company_website_url=None,
                        status="needs_manual_input",
                        reason="LinkedIn page appears blocked, logged out, or behind verification.",
                    )

                company_name = await self._extract_company_name(page)
                company_website_url = await self._extract_company_website(page)

                if not company_name or not company_website_url:
                    return LinkedInJobInfo(
                        company_name=company_name,
                        company_website_url=company_website_url,
                        status="needs_manual_input",
                        reason="Could not reliably extract both company name and website URL from LinkedIn.",
                    )

                return LinkedInJobInfo(
                    company_name=company_name,
                    company_website_url=company_website_url,
                    status="success",
                )

            finally:
                await browser.close()

    async def _extract_company_name(self, page) -> str | None:
        selectors = [
            ".topcard__org-name-link",
            ".topcard__flavor",
            "a[data-tracking-control-name='public_jobs_topcard-org-name']",
        ]

        for selector in selectors:
            locator = page.locator(selector).first()

            try:
                if await locator.count() > 0:
                    text = await locator.inner_text(timeout=3000)
                    text = text.strip()
                    if text:
                        return text
            except Exception:
                continue

        return None

    async def _extract_company_website(self, page) -> str | None:
        """
        LinkedIn public job pages usually do not expose the company website directly.
        This is intentionally conservative.
        """
        links = await page.locator("a").evaluate_all(
            """
            anchors => anchors.map(a => ({
                text: a.innerText || "",
                href: a.href || ""
            }))
            """
        )

        for link in links:
            text = link.get("text", "").strip().lower()
            href = link.get("href", "").strip()

            if "company website" in text and href:
                return href

        return None