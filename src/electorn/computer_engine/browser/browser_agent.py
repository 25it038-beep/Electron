"""
Autonomous high-level browser research and navigation agent.
"""

from typing import Optional, Dict, Any
from electorn.computer_engine.browser.browser_controller import BrowserController
from electorn.computer_engine.browser.browser_navigator import BrowserNavigator


class BrowserAgent:
    def __init__(
        self,
        controller: Optional[BrowserController] = None,
        navigator: Optional[BrowserNavigator] = None,
    ) -> None:
        self.controller = controller or BrowserController()
        self.navigator = navigator or BrowserNavigator()

    def research_topic(self, query: str) -> Dict[str, Any]:
        """Search query and extract summary."""
        success = self.controller.search(query)
        if not success:
            return {
                "query": query,
                "success": False,
                "error": "Failed to launch browser search.",
            }

        content = self.controller.get_page_content()
        return {
            "query": query,
            "success": True,
            "page_content": content,
        }

    def open_web_page(self, url: str) -> bool:
        self.navigator.navigate(url)
        return self.controller.open_url(url)
