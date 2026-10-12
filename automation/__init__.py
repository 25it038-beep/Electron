"""Automation package for Electorn AI: Windows OS, Selenium Browser, Files, and Processes."""

from automation.os_automation import WindowsOSAutomation
from automation.browser_automation import SeleniumBrowserAutomation
from automation.file_automation import FileAutomation
from automation.process_runner import ControlledProcessRunner
from automation.screenshot import ScreenshotCapture

__all__ = [
    "WindowsOSAutomation",
    "SeleniumBrowserAutomation",
    "FileAutomation",
    "ControlledProcessRunner",
    "ScreenshotCapture",
]
