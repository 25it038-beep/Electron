"""Selenium Web Browser Automation Engine for Electorn AI.

Handles real browser automation, element interaction, dynamic DOM waits,
structured table extraction, downloads, and screenshots using Edge/Chrome WebDriver.
"""

from __future__ import annotations

import csv
import io
import json
import os
import pathlib
import re
import time
from typing import Any, Optional
from urllib.parse import quote_plus

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.edge.options import Options as EdgeOptions
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except Exception:
    SELENIUM_AVAILABLE = False


class SeleniumBrowserAutomation:
    """Production Selenium automation engine with robust selectors, waits, and data extraction."""

    def __init__(self, download_dir: Optional[str] = None) -> None:
        self.download_dir = download_dir or str(pathlib.Path.home() / "Downloads")
        self.driver: Optional[Any] = None
        self.browser_name: Optional[str] = None

    def is_available(self) -> bool:
        """Check if Selenium library is installed."""
        return SELENIUM_AVAILABLE

    def get_or_create_driver(self, headless: bool = False, browser_type: str = "edge") -> Any:
        """Ensure active WebDriver session, reusing if still healthy."""
        if not SELENIUM_AVAILABLE:
            raise RuntimeError("Selenium WebDriver is not available in the environment.")

        if self.driver is not None:
            try:
                # Test connection
                _ = self.driver.title
                return self.driver
            except Exception:
                self.driver = None

        pathlib.Path(self.download_dir).mkdir(parents=True, exist_ok=True)
        driver = None

        # Prefer Edge on Windows, fallback to Chrome, or user choice
        browsers_to_try = [browser_type.lower()]
        if "edge" not in browsers_to_try:
            browsers_to_try.append("edge")
        if "chrome" not in browsers_to_try:
            browsers_to_try.append("chrome")

        last_error = None
        for b in browsers_to_try:
            try:
                if b == "edge":
                    opts = EdgeOptions()
                    if headless:
                        opts.add_argument("--headless=new")
                    opts.add_argument("--disable-gpu")
                    opts.add_argument("--no-sandbox")
                    opts.add_argument("--log-level=3")
                    # Set download folder
                    prefs = {"download.default_directory": self.download_dir}
                    opts.add_experimental_option("prefs", prefs)
                    driver = webdriver.Edge(options=opts)
                    self.browser_name = "Microsoft Edge"
                    break
                elif b == "chrome":
                    c_opts = ChromeOptions()
                    if headless:
                        c_opts.add_argument("--headless=new")
                    c_opts.add_argument("--disable-gpu")
                    c_opts.add_argument("--no-sandbox")
                    c_opts.add_argument("--log-level=3")
                    prefs = {"download.default_directory": self.download_dir}
                    c_opts.add_experimental_option("prefs", prefs)
                    driver = webdriver.Chrome(options=c_opts)
                    self.browser_name = "Google Chrome"
                    break
            except Exception as err:
                last_error = err
                continue

        if driver is None:
            raise RuntimeError(f"Could not launch browser (Edge/Chrome). Error: {last_error}")

        driver.implicitly_wait(4)
        self.driver = driver
        return self.driver

    # =========================================================================
    # NAVIGATION & TABS
    # =========================================================================

    def open_url(self, url: str, headless: bool = False) -> dict[str, Any]:
        """Navigate to website URL and wait for page readiness."""
        if not re.match(r"^https?://", url, re.IGNORECASE):
            url = f"https://{url}"

        d = self.get_or_create_driver(headless=headless)
        try:
            d.get(url)
            # Wait for document ready
            WebDriverWait(d, 15).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            title = d.title or url
            return {
                "success": True,
                "url": d.current_url,
                "title": title,
                "browser": self.browser_name,
                "message": f"Successfully opened {url} ({title}).",
            }
        except Exception as err:
            return {
                "success": False,
                "url": url,
                "message": f"Navigation failed: {err}",
            }

    def search(self, query: str, headless: bool = False) -> dict[str, Any]:
        """Perform search on Google and wait for results."""
        search_url = f"https://www.google.com/search?q={quote_plus(query)}"
        return self.open_url(search_url, headless=headless)

    def navigate(self, action: str) -> dict[str, Any]:
        """Navigate backward, forward, or refresh page."""
        if self.driver is None:
            return {"success": False, "message": "No active browser session open."}
        try:
            if action in ("back", "previous"):
                self.driver.back()
            elif action in ("forward", "next"):
                self.driver.forward()
            elif action in ("refresh", "reload"):
                self.driver.refresh()
            else:
                return {"success": False, "message": f"Unknown navigation action: {action}"}

            return {
                "success": True,
                "url": self.driver.current_url,
                "title": self.driver.title,
                "message": f"Browser {action} performed successfully.",
            }
        except Exception as err:
            return {"success": False, "message": f"Navigation error: {err}"}

    def close(self) -> dict[str, Any]:
        """Quit the browser session."""
        if self.driver is not None:
            try:
                self.driver.quit()
            except Exception:
                pass
            finally:
                self.driver = None
            return {"success": True, "message": f"Closed {self.browser_name or 'browser'} session."}
        return {"success": True, "message": "No active browser was running."}

    # =========================================================================
    # DOM INTERACTIONS & ELEMENT CONTROLS
    # =========================================================================

    def click_element(self, selector: str, by: str = "css") -> dict[str, Any]:
        """Locate element and click it with explicit wait."""
        if self.driver is None:
            return {"success": False, "message": "No active browser session."}

        by_type = self._resolve_by_type(by)
        try:
            elem = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((by_type, selector))
            )
            elem.click()
            return {"success": True, "message": f"Clicked element matching '{selector}'."}
        except Exception as err:
            # Fallback JavaScript click
            try:
                raw_elem = self.driver.find_element(by_type, selector)
                self.driver.execute_script("arguments[0].click();", raw_elem)
                return {"success": True, "message": f"Clicked element via JS click '{selector}'."}
            except Exception:
                return {"success": False, "message": f"Could not click '{selector}': {err}"}

    def type_into_field(self, selector: str, text: str, by: str = "css", press_enter: bool = False) -> dict[str, Any]:
        """Type text into an input field."""
        if self.driver is None:
            return {"success": False, "message": "No active browser session."}

        by_type = self._resolve_by_type(by)
        try:
            elem = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((by_type, selector))
            )
            elem.clear()
            elem.send_keys(text)
            if press_enter:
                elem.send_keys(Keys.RETURN)
            return {"success": True, "message": f"Entered text into field '{selector}'."}
        except Exception as err:
            return {"success": False, "message": f"Failed to type into field '{selector}': {err}"}

    def scroll(self, direction: str = "down", amount: int = 600) -> dict[str, Any]:
        """Scroll page window up, down, or to top/bottom."""
        if self.driver is None:
            return {"success": False, "message": "No active browser session."}
        try:
            if direction == "down":
                self.driver.execute_script(f"window.scrollBy(0, {amount});")
            elif direction == "up":
                self.driver.execute_script(f"window.scrollBy(0, -{amount});")
            elif direction == "bottom":
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            elif direction == "top":
                self.driver.execute_script("window.scrollTo(0, 0);")
            return {"success": True, "message": f"Scrolled {direction}."}
        except Exception as err:
            return {"success": False, "message": f"Scroll error: {err}"}

    # =========================================================================
    # DATA EXTRACTION & SCREENSHOTS
    # =========================================================================

    def extract_table(self, table_selector: str = "table") -> dict[str, Any]:
        """Extract structured tabular data from the current webpage."""
        if self.driver is None:
            return {"success": False, "data": [], "message": "No active browser session."}
        try:
            tables = self.driver.find_elements(By.CSS_SELECTOR, table_selector)
            if not tables:
                return {"success": False, "data": [], "message": f"No table found matching '{table_selector}'."}

            table = tables[0]
            rows = table.find_elements(By.TAG_NAME, "tr")
            table_data: list[list[str]] = []
            for row in rows:
                cols = row.find_elements(By.XPATH, "./th|./td")
                row_vals = [c.text.strip() for c in cols if c.text.strip()]
                if row_vals:
                    table_data.append(row_vals)

            return {
                "success": True,
                "row_count": len(table_data),
                "data": table_data,
                "message": f"Extracted {len(table_data)} rows from table.",
            }
        except Exception as err:
            return {"success": False, "data": [], "message": f"Table extraction error: {err}"}

    def export_table_to_csv(self, file_path: str, table_selector: str = "table") -> dict[str, Any]:
        """Extract table and save to CSV file."""
        extracted = self.extract_table(table_selector)
        if not extracted["success"] or not extracted["data"]:
            return {"success": False, "message": extracted["message"]}

        try:
            p = pathlib.Path(file_path).resolve()
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                for row in extracted["data"]:
                    writer.writerow(row)
            return {
                "success": True,
                "file_path": str(p),
                "row_count": len(extracted["data"]),
                "message": f"Successfully exported table to {p}.",
            }
        except Exception as err:
            return {"success": False, "message": f"CSV export error: {err}"}

    def extract_text(self, selector: str = "body") -> dict[str, Any]:
        """Extract visible text content from webpage."""
        if self.driver is None:
            return {"success": False, "text": "", "message": "No active browser session."}
        try:
            elem = self.driver.find_element(By.CSS_SELECTOR, selector)
            text = elem.text.strip()
            return {"success": True, "text": text, "message": f"Extracted {len(text)} characters."}
        except Exception as err:
            return {"success": False, "text": "", "message": f"Text extraction error: {err}"}

    def capture_screenshot(self, filename: str = "browser_screenshot.png") -> dict[str, Any]:
        """Take screenshot of current browser window."""
        if self.driver is None:
            return {"success": False, "message": "No active browser session to screenshot."}
        try:
            p = pathlib.Path(filename).resolve()
            p.parent.mkdir(parents=True, exist_ok=True)
            self.driver.save_screenshot(str(p))
            return {"success": True, "file_path": str(p), "message": f"Saved screenshot to {p}."}
        except Exception as err:
            return {"success": False, "message": f"Screenshot error: {err}"}

    def _resolve_by_type(self, by: str) -> Any:
        mapping = {
            "css": By.CSS_SELECTOR,
            "xpath": By.XPATH,
            "id": By.ID,
            "name": By.NAME,
            "tag": By.TAG_NAME,
            "link_text": By.LINK_TEXT,
        }
        return mapping.get(by.lower(), By.CSS_SELECTOR)
