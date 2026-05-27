"""
LinkedInService: Playwright-based LinkedIn automation.
Handles all browser interactions with LinkedIn.
"""
import json
import logging
import os
import random
import time
from pathlib import Path
from typing import Optional

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext

logger = logging.getLogger(__name__)

SESSIONS_DIR = Path("data/linkedin_sessions")
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


class LinkedInService:
    """
    Manages a LinkedIn browser session using Playwright.
    Sessions are persisted as cookies to avoid re-login on every run.
    """

    BASE_URL = "https://www.linkedin.com"

    def __init__(
        self,
        email: str,
        password: str,
        profile_id: str,
        proxy_config: dict = None,
        headless: bool = True
    ):
        self.email = email
        self.password = password
        self.profile_id = profile_id
        self.proxy_config = proxy_config
        self.headless = headless
        self.session_file = SESSIONS_DIR / f"{profile_id}_session.json"
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.close()

    def start(self):
        """Start Playwright browser and restore session if available."""
        self._playwright = sync_playwright().start()

        launch_args = {
            "headless": self.headless,
            "args": ["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        }

        if self.proxy_config:
            launch_args["proxy"] = self.proxy_config

        self._browser = self._playwright.chromium.launch(**launch_args)

        context_args = {
            "viewport": {"width": 1280, "height": 800},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        }

        # Restore session cookies if available
        if self.session_file.exists():
            with open(self.session_file) as f:
                cookies = json.load(f)
            context_args["storage_state"] = {"cookies": cookies, "origins": []}

        self._context = self._browser.new_context(**context_args)
        self._page = self._context.new_page()

        # Block unnecessary resources for speed
        self._page.route("**/*.{png,jpg,jpeg,gif,svg,mp4,woff,woff2}", lambda route: route.abort())

    def close(self):
        """Save session and close browser."""
        if self._context:
            # Save cookies for next session
            cookies = self._context.cookies()
            with open(self.session_file, "w") as f:
                json.dump(cookies, f)

        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    def login(self) -> bool:
        """Login to LinkedIn. Returns True if successful."""
        self._page.goto(f"{self.BASE_URL}/login")
        self._human_wait(2, 3)

        # Check if already logged in
        if self._is_logged_in():
            logger.info(f"Already logged in for profile {self.profile_id}")
            return True

        # Fill login form
        self._page.fill("#username", self.email)
        self._human_wait(0.5, 1.5)
        self._page.fill("#password", self.password)
        self._human_wait(0.5, 1)
        self._page.click("[type=submit]")
        self._human_wait(3, 5)

        if self._is_logged_in():
            logger.info(f"Successfully logged in for profile {self.profile_id}")
            return True

        logger.error(f"Login failed for profile {self.profile_id}")
        return False

    def post_content(self, text: str, image_path: str = None) -> Optional[str]:
        """
        Post to LinkedIn feed with optional image.
        Returns post ID if successful, None if failed.
        """
        self._page.goto(f"{self.BASE_URL}/feed/")
        self._human_wait(2, 4)

        # Click "Start a post"
        start_post = self._page.locator('[class*="share-box-feed-entry__trigger"]').first
        start_post.click()
        self._human_wait(1, 2)

        # Type post text (human-like typing)
        text_area = self._page.locator('[class*="ql-editor"]').first
        self._human_type(text_area, text)
        self._human_wait(1, 2)

        # Attach image if provided
        if image_path and os.path.exists(image_path):
            # Click image button
            self._page.locator('[class*="share-creation-state__main-btn--image"]').click()
            self._human_wait(1, 2)

            # Upload file
            file_input = self._page.locator('input[type="file"]')
            file_input.set_input_files(image_path)
            self._human_wait(3, 5)  # Wait for upload

        # Click Post button
        self._page.locator('[class*="share-actions__primary-action"]').click()
        self._human_wait(3, 5)

        logger.info(f"Posted content for profile {self.profile_id}")
        return "posted"

    def search_and_comment(
        self, keywords: list[str], max_comments: int = 10
    ) -> list[dict]:
        """Search for posts by keyword and leave comments."""
        results = []

        for keyword in keywords[:3]:
            self._page.goto(
                f"{self.BASE_URL}/search/results/content/?keywords={keyword}&sortBy=relevance"
            )
            self._human_wait(3, 5)

            # Get post elements (simplified - in production, use more robust selectors)
            posts = self._page.locator('[class*="feed-shared-update-v2"]').all()[:max_comments]

            for post in posts:
                try:
                    # Get post text
                    post_text_elem = post.locator('[class*="feed-shared-text"]').first
                    if not post_text_elem.is_visible():
                        continue

                    post_text = post_text_elem.inner_text()[:500]

                    # Click comment button
                    comment_btn = post.locator('[class*="comment-button"]').first
                    comment_btn.click()
                    self._human_wait(1, 2)

                    results.append({
                        "post_text_snippet": post_text[:100],
                        "status": "commented"
                    })

                    self._human_wait(30, 90)  # Wait between comments

                except Exception as e:
                    logger.warning(f"Failed to comment on post: {e}")
                    continue

        return results

    def send_connection_request(
        self, profile_url: str, message: str
    ) -> bool:
        """Send a connection request with a personalized message."""
        self._page.goto(profile_url)
        self._human_wait(2, 4)

        try:
            connect_btn = self._page.locator('[aria-label*="Connect"]').first
            connect_btn.click()
            self._human_wait(1, 2)

            # Add note
            add_note_btn = self._page.locator('[aria-label="Add a note"]')
            if add_note_btn.is_visible():
                add_note_btn.click()
                self._human_wait(0.5, 1)

                message_input = self._page.locator('#custom-message')
                self._human_type(message_input, message[:300])
                self._human_wait(0.5, 1)

            # Send
            send_btn = self._page.locator('[aria-label="Send now"]')
            send_btn.click()
            self._human_wait(2, 3)

            return True

        except Exception as e:
            logger.error(f"Failed to send connection request: {e}")
            return False

    def search_jobs(
        self, keywords: str, location: str = "", easy_apply_only: bool = True
    ) -> list[dict]:
        """Search for jobs matching criteria."""
        url = (
            f"{self.BASE_URL}/jobs/search/?keywords={keywords}"
            f"&location={location}"
        )
        if easy_apply_only:
            url += "&f_AL=true"  # Easy Apply filter

        self._page.goto(url)
        self._human_wait(3, 5)

        jobs = []
        job_cards = self._page.locator('[class*="job-card-container"]').all()[:20]

        for card in job_cards:
            try:
                title = card.locator('[class*="job-card-list__title"]').inner_text()
                company = card.locator('[class*="job-card-container__company-name"]').inner_text()
                location_elem = card.locator('[class*="job-card-container__metadata-item"]').first
                job_url = card.locator('a').first.get_attribute("href")

                jobs.append({
                    "title": title.strip(),
                    "company": company.strip(),
                    "location": location_elem.inner_text().strip() if location_elem else "",
                    "url": f"{self.BASE_URL}{job_url}" if job_url else "",
                })
            except Exception:
                continue

        return jobs

    def apply_to_job(self, job_url: str, cover_letter: str) -> bool:
        """Apply to an Easy Apply job."""
        self._page.goto(job_url)
        self._human_wait(3, 5)

        try:
            apply_btn = self._page.locator('[class*="jobs-apply-button"]').first
            if "Easy Apply" not in apply_btn.inner_text():
                return False

            apply_btn.click()
            self._human_wait(2, 3)

            # Handle multi-step application (simplified)
            # In production: handle each step (contact info, resume, questions)
            while True:
                next_btn = self._page.locator('[aria-label="Continue to next step"]')
                submit_btn = self._page.locator('[aria-label="Submit application"]')

                if submit_btn.is_visible():
                    submit_btn.click()
                    self._human_wait(2, 3)
                    return True
                elif next_btn.is_visible():
                    next_btn.click()
                    self._human_wait(1, 2)
                else:
                    break

        except Exception as e:
            logger.error(f"Failed to apply to job {job_url}: {e}")

        return False

    def get_profile_data(self) -> dict:
        """Fetch basic profile data for the logged-in user."""
        self._page.goto(f"{self.BASE_URL}/in/me/")
        self._human_wait(3, 5)

        try:
            name = self._page.locator('h1').first.inner_text()
            headline = self._page.locator('[class*="text-body-medium"]').first.inner_text()
            url = self._page.url

            return {
                "name": name.strip(),
                "headline": headline.strip(),
                "url": url,
            }
        except Exception as e:
            logger.error(f"Failed to get profile data: {e}")
            return {}

    def _is_logged_in(self) -> bool:
        """Check if currently logged in to LinkedIn."""
        return "feed" in self._page.url or self._page.locator('[class*="global-nav"]').is_visible()

    def _human_wait(self, min_sec: float, max_sec: float):
        """Wait a random human-like duration."""
        time.sleep(random.uniform(min_sec, max_sec))

    def _human_type(self, element, text: str):
        """Type text with human-like random delays between characters."""
        for char in text:
            element.type(char)
            time.sleep(random.uniform(0.02, 0.08))