"""Self-healing and fallback recovery strategy engine."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class RecoveryStrategy:
    """Provides retry logic, alternate selectors, and fallback pathways when automation steps fail."""

    def __init__(self, max_retries: int = 2) -> None:
        self.max_retries = max_retries

    def attempt_recovery(
        self,
        action: str,
        params: dict[str, Any],
        error_msg: str,
        executor_fn: Callable[[str, dict[str, Any]], dict[str, Any]],
        attempt: int = 1,
    ) -> dict[str, Any]:
        """Attempt to recover from a failed step using known fallbacks."""
        if attempt > self.max_retries:
            return {
                "success": False,
                "recovered": False,
                "message": f"Step failed after {self.max_retries} recovery attempts. Last error: {error_msg}",
            }

        logger.info(f"Attempting recovery {attempt}/{self.max_retries} for '{action}': {error_msg}")

        # Browser selector fallback
        if action == "browser.click" and "selector" in params:
            orig_selector = params["selector"]
            # Fallback 1: Try finding by button text or tag name if selector was an ID/class
            alt_selectors = self._generate_alt_selectors(orig_selector)
            for alt in alt_selectors:
                logger.info(f"Trying alternative selector: {alt}")
                alt_params = dict(params, selector=alt)
                time.sleep(1.0)
                res = executor_fn(action, alt_params)
                if res.get("success", False):
                    res["recovered"] = True
                    res["recovery_note"] = f"Recovered using alternative selector: {alt}"
                    return res

        # File operation path fallback (ensure parent directory exists)
        if action in ("file.create_file", "file.move_file", "file.copy_file"):
            target_path = params.get("path") or params.get("dst")
            if target_path:
                import os
                parent_dir = os.path.dirname(os.path.expanduser(target_path))
                if parent_dir and not os.path.exists(parent_dir):
                    logger.info(f"Auto-creating missing parent directory: {parent_dir}")
                    os.makedirs(parent_dir, exist_ok=True)
                    res = executor_fn(action, params)
                    if res.get("success", False):
                        res["recovered"] = True
                        res["recovery_note"] = f"Auto-created parent directory {parent_dir}"
                        return res

        # Standard retry with backoff for transient issues
        time.sleep(1.0 * attempt)
        res = executor_fn(action, params)
        if res.get("success", False):
            res["recovered"] = True
            res["recovery_note"] = f"Succeeded on retry attempt {attempt}"
            return res

        return self.attempt_recovery(action, params, res.get("message", error_msg), executor_fn, attempt + 1)

    def _generate_alt_selectors(self, selector: str) -> list[str]:
        """Generate alternative CSS selectors based on common element structures."""
        alts = []
        if selector.startswith("#"):
            tag_less = selector[1:]
            alts.append(f"[id='{tag_less}']")
            alts.append(f"[name='{tag_less}']")
        elif selector.startswith("."):
            class_name = selector[1:]
            alts.append(f"[class*='{class_name}']")
            alts.append(f"button.{class_name}")
        alts.append(f"button:contains('{selector}')")
        return alts
