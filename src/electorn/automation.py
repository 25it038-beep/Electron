"""Full OS Automation & Selenium Browser Control Engine for Electorn AI."""

from __future__ import annotations

import ctypes
import os
import pathlib
import platform
import re
import shutil
import subprocess
import sys
from typing import Any, Optional
from urllib.parse import quote_plus

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.edge.options import Options as EdgeOptions
    SELENIUM_AVAILABLE = True
except Exception:
    SELENIUM_AVAILABLE = False

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0.05
    PYAUTOGUI_AVAILABLE = True
except Exception:
    PYAUTOGUI_AVAILABLE = False

try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except Exception:
    PYPERCLIP_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except Exception:
    PSUTIL_AVAILABLE = False


class AutomationEngine:
    """Full desktop OS automation & autonomous Selenium browser control."""

    def __init__(self) -> None:
        self.active_driver: Optional[Any] = None
        self.browser_name: Optional[str] = None

    def is_selenium_available(self) -> bool:
        """Check if Selenium is available."""
        return SELENIUM_AVAILABLE

    # =========================================================================
    # 1. SELENIUM BROWSER AUTOMATION
    # =========================================================================

    def get_or_create_driver(self, headless: bool = False) -> Any:
        """Get or initialize active Selenium WebDriver (prefers Edge on Windows, then Chrome)."""
        if not SELENIUM_AVAILABLE:
            raise RuntimeError("Selenium is not installed in the environment.")

        if self.active_driver is not None:
            try:
                _ = self.active_driver.title
                return self.active_driver
            except Exception:
                self.active_driver = None

        driver = None
        try:
            edge_opts = EdgeOptions()
            if headless:
                edge_opts.add_argument("--headless=new")
            edge_opts.add_argument("--disable-gpu")
            edge_opts.add_argument("--no-sandbox")
            edge_opts.add_argument("--log-level=3")
            driver = webdriver.Edge(options=edge_opts)
            self.browser_name = "Microsoft Edge"
        except Exception:
            try:
                chrome_opts = ChromeOptions()
                if headless:
                    chrome_opts.add_argument("--headless=new")
                chrome_opts.add_argument("--disable-gpu")
                chrome_opts.add_argument("--no-sandbox")
                chrome_opts.add_argument("--log-level=3")
                driver = webdriver.Chrome(options=chrome_opts)
                self.browser_name = "Google Chrome"
            except Exception as chrome_err:
                raise RuntimeError(f"Could not launch Edge or Chrome WebDriver: {chrome_err}")

        self.active_driver = driver
        return self.active_driver

    def open_url(self, url: str, headless: bool = False) -> str:
        """Open a website URL in the browser via Selenium."""
        if not re.match(r"^https?://", url, re.IGNORECASE):
            url = f"https://{url}"

        driver = self.get_or_create_driver(headless=headless)
        driver.get(url)
        title = driver.title or url
        return f"Navigated to {url} ({title}) using {self.browser_name}"

    def search_web(self, query: str, headless: bool = False) -> str:
        """Search Google via Selenium and open results."""
        search_url = f"https://www.google.com/search?q={quote_plus(query)}"
        driver = self.get_or_create_driver(headless=headless)
        driver.get(search_url)
        title = driver.title or f"Search for {query}"
        return f"Searched Google for '{query}' ({title}) using {self.browser_name}"

    def close_browser(self) -> str:
        """Close active Selenium browser session."""
        if self.active_driver is not None:
            try:
                self.active_driver.quit()
            except Exception:
                pass
            finally:
                self.active_driver = None
            return f"Closed {self.browser_name or 'browser'} session."
        return "No active browser session was open."

    def scroll_page(self, direction: str = "down", amount: int = 600) -> str:
        """Scroll active browser window."""
        if self.active_driver is None:
            return "No active browser window to scroll."
        try:
            if direction == "down":
                self.active_driver.execute_script(f"window.scrollBy(0, {amount});")
                return "Scrolled down the page."
            elif direction == "up":
                self.active_driver.execute_script(f"window.scrollBy(0, -{amount});")
                return "Scrolled up the page."
            elif direction == "bottom":
                self.active_driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                return "Scrolled to the bottom of the page."
            elif direction == "top":
                self.active_driver.execute_script("window.scrollTo(0, 0);")
                return "Scrolled to the top of the page."
            return "Unknown scroll direction."
        except Exception as err:
            return f"Failed to scroll page: {err}"

    def browser_navigate(self, action: str) -> str:
        """Navigate active browser (back, forward, refresh)."""
        if self.active_driver is None:
            return "No active browser session open."
        try:
            if action in ("back", "previous"):
                self.active_driver.back()
                return f"Navigated back to {self.active_driver.title or 'previous page'}."
            elif action in ("forward", "next"):
                self.active_driver.forward()
                return f"Navigated forward to {self.active_driver.title or 'next page'}."
            elif action in ("refresh", "reload"):
                self.active_driver.refresh()
                return f"Refreshed page {self.active_driver.title}."
            return "Unknown navigation action."
        except Exception as err:
            return f"Browser navigation error: {err}"

    def take_screenshot(self, filename: str = "electorn_screenshot.png") -> str:
        """Capture screenshot of the active browser or entire screen."""
        if self.active_driver is not None:
            try:
                self.active_driver.save_screenshot(filename)
                return f"Saved browser screenshot to {filename}."
            except Exception:
                pass
        if PYAUTOGUI_AVAILABLE:
            try:
                img = pyautogui.screenshot()
                img.save(filename)
                return f"Captured screen and saved to {filename}."
            except Exception as err:
                return f"Screenshot error: {err}"
        return "Screenshot tools unavailable."

    # =========================================================================
    # 2. DESKTOP & WINDOW MANAGEMENT
    # =========================================================================

    def minimize_all_windows(self) -> str:
        """Minimize all open windows and show the desktop."""
        if PYAUTOGUI_AVAILABLE:
            pyautogui.hotkey("win", "d")
            return "Minimized all open windows."
        if sys.platform == "win32":
            try:
                import win32com.client
                shell = win32com.client.Dispatch("Shell.Application")
                shell.MinimizeAll()
                return "Minimized all open windows."
            except Exception as err:
                return f"Failed to minimize windows: {err}"
        return "Window control not supported on this platform."

    def maximize_window(self) -> str:
        """Maximize the currently active window."""
        if PYAUTOGUI_AVAILABLE:
            pyautogui.hotkey("win", "up")
            return "Maximized active window."
        return "Window maximize unavailable."

    def switch_window(self) -> str:
        """Switch to the next window (Alt + Tab)."""
        if PYAUTOGUI_AVAILABLE:
            pyautogui.hotkey("alt", "tab")
            return "Switched active window."
        return "Window switch unavailable."

    def close_active_window(self) -> str:
        """Close the currently focused window (Alt + F4)."""
        if PYAUTOGUI_AVAILABLE:
            pyautogui.hotkey("alt", "f4")
            return "Closed active window."
        return "Close active window unavailable."

    def lock_workstation(self) -> str:
        """Lock the computer workstation."""
        if sys.platform == "win32":
            try:
                ctypes.windll.user32.LockWorkStation()
                return "Computer workstation locked."
            except Exception as err:
                return f"Could not lock computer: {err}"
        return "Lock workstation is only supported on Windows."

    # =========================================================================
    # 3. AUDIO & MEDIA CONTROL
    # =========================================================================

    def control_volume(self, action: str) -> str:
        """Adjust system volume (up, down, mute)."""
        if not PYAUTOGUI_AVAILABLE:
            return "Volume control requires pyautogui."
        try:
            if action == "up":
                pyautogui.press("volumeup", presses=5)
                return "Turned volume up."
            elif action == "down":
                pyautogui.press("volumedown", presses=5)
                return "Turned volume down."
            elif action in ("mute", "unmute"):
                pyautogui.press("volumemute")
                return "Toggled volume mute."
            return "Unknown volume action."
        except Exception as err:
            return f"Error controlling volume: {err}"

    def control_media(self, action: str) -> str:
        """Control media playback (play/pause, next, previous)."""
        if not PYAUTOGUI_AVAILABLE:
            return "Media playback control requires pyautogui."
        try:
            if action in ("play", "pause", "playpause"):
                pyautogui.press("playpause")
                return "Toggled media playback."
            elif action in ("next", "nexttrack"):
                pyautogui.press("nexttrack")
                return "Skipped to next media track."
            elif action in ("prev", "previous", "prevtrack"):
                pyautogui.press("prevtrack")
                return "Skipped to previous media track."
            return "Unknown media action."
        except Exception as err:
            return f"Media control error: {err}"

    # =========================================================================
    # 4. SYSTEM HEALTH & TELEMETRY
    # =========================================================================

    def get_system_health(self) -> dict[str, Any]:
        """Fetch real-time CPU, RAM, Disk, and Battery diagnostics."""
        health: dict[str, Any] = {
            "os": f"{platform.system()} {platform.release()}",
            "arch": platform.machine(),
            "cpu_percent": 0.0,
            "ram_percent": 0.0,
            "ram_free_gb": 0.0,
            "disk_free_gb": 0.0,
            "battery_percent": None,
            "battery_charging": None,
        }
        if PSUTIL_AVAILABLE:
            try:
                health["cpu_percent"] = psutil.cpu_percent(interval=0.1)
                mem = psutil.virtual_memory()
                health["ram_percent"] = mem.percent
                health["ram_free_gb"] = round(mem.available / (1024 ** 3), 1)

                root_drive = "C:" if sys.platform == "win32" else "/"
                disk = psutil.disk_usage(root_drive)
                health["disk_free_gb"] = round(disk.free / (1024 ** 3), 1)

                bat = psutil.sensors_battery()
                if bat is not None:
                    health["battery_percent"] = bat.percent
                    health["battery_charging"] = bat.power_plugged
            except Exception:
                pass
        return health

    def get_system_specs(self) -> str:
        """Format system diagnostics into a readable string."""
        h = self.get_system_health()
        specs = (
            f"OS: {h['os']} ({h['arch']})\n"
            f"CPU Usage: {h['cpu_percent']}%\n"
            f"Memory: {h['ram_percent']}% used ({h['ram_free_gb']} GB available)\n"
            f"Disk Free: {h['disk_free_gb']} GB"
        )
        if h["battery_percent"] is not None:
            charging_str = "Plugged in" if h["battery_charging"] else "On battery"
            specs += f"\nBattery: {h['battery_percent']}% ({charging_str})"
        return specs

    def list_top_processes(self, count: int = 5) -> str:
        """List top memory-consuming processes."""
        if not PSUTIL_AVAILABLE:
            return "Process inspection requires psutil."
        try:
            procs = []
            for p in psutil.process_iter(["pid", "name", "memory_percent"]):
                try:
                    info = p.info
                    if info and info["name"]:
                        procs.append((info["name"], info["memory_percent"] or 0.0))
                except Exception:
                    continue
            procs.sort(key=lambda x: x[1], reverse=True)
            top = procs[:count]
            lines = [f"• {name}: {round(mem, 1)}% RAM" for name, mem in top]
            return "Top Memory Processes:\n" + "\n".join(lines)
        except Exception as err:
            return f"Error listing processes: {err}"

    # =========================================================================
    # 5. FILESYSTEM & DIRECTORY SHORTCUTS
    # =========================================================================

    def open_special_folder(self, folder_name: str) -> str:
        """Open popular user directories (Downloads, Documents, Desktop, etc.)."""
        home = pathlib.Path.home()
        mapping = {
            "downloads": home / "Downloads",
            "documents": home / "Documents",
            "desktop": home / "Desktop",
            "pictures": home / "Pictures",
            "photos": home / "Pictures",
            "music": home / "Music",
            "videos": home / "Videos",
            "c drive": pathlib.Path("C:\\") if sys.platform == "win32" else pathlib.Path("/"),
            "workspace": pathlib.Path(".").resolve(),
            "folder": pathlib.Path(".").resolve(),
        }
        target = mapping.get(folder_name.strip().lower(), pathlib.Path(".").resolve())
        return self.open_path(str(target))

    def open_path(self, target_path: str = ".") -> str:
        """Open a local folder or file in the default OS file explorer."""
        abs_path = os.path.abspath(target_path)
        try:
            if sys.platform == "win32":
                os.startfile(abs_path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", abs_path])
            else:
                subprocess.Popen(["xdg-open", abs_path])
            return f"Opened folder: {abs_path}"
        except Exception as err:
            return f"Error opening folder: {err}"

    def create_directory(self, folder_path: str) -> str:
        """Create a new folder on the filesystem."""
        try:
            p = pathlib.Path(folder_path)
            p.mkdir(parents=True, exist_ok=True)
            return f"Created directory: {p.resolve()}"
        except Exception as err:
            return f"Error creating folder: {err}"

    def create_file(self, file_path: str, content: str = "") -> str:
        """Create a new text file."""
        try:
            p = pathlib.Path(file_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return f"Created file: {p.resolve()} ({len(content)} characters)"
        except Exception as err:
            return f"Error creating file: {err}"

    def empty_recycle_bin(self) -> str:
        """Empty the Windows Recycle Bin."""
        if sys.platform == "win32":
            try:
                subprocess.run(
                    ["powershell", "-NoProfile", "-Command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return "Recycle Bin emptied successfully."
            except Exception as err:
                return f"Could not empty Recycle Bin: {err}"
        return "Recycle Bin operations only supported on Windows."

    # =========================================================================
    # 6. APPLICATION MANAGEMENT
    # =========================================================================

    def launch_application(self, app_name: str) -> str:
        """Launch desktop applications (Notepad, Calc, Terminal, Explorer, VS Code, etc.)."""
        name_clean = app_name.strip().lower()
        app_map = {
            "notepad": ["notepad.exe"],
            "calc": ["calc.exe"],
            "calculator": ["calc.exe"],
            "explorer": ["explorer.exe"],
            "files": ["explorer.exe"],
            "file explorer": ["explorer.exe"],
            "terminal": ["wt.exe", "powershell.exe", "cmd.exe"],
            "powershell": ["powershell.exe"],
            "cmd": ["cmd.exe"],
            "vscode": ["code"],
            "vs code": ["code"],
            "code": ["code"],
            "paint": ["mspaint.exe"],
            "task manager": ["taskmgr.exe"],
            "taskmgr": ["taskmgr.exe"],
            "settings": ["control.exe"],
            "spotify": ["spotify.exe"],
            "chrome": ["chrome.exe"],
            "edge": ["msedge.exe"],
        }
        executables = app_map.get(name_clean, [name_clean])
        for exe in executables:
            try:
                if sys.platform == "win32":
                    subprocess.Popen(exe, shell=True)
                else:
                    subprocess.Popen([exe])
                return f"Successfully opened {app_name.capitalize()} on your system."
            except Exception:
                continue
        return f"Could not find or launch application: {app_name}."

    def close_application(self, app_name: str) -> str:
        """Close running desktop application by name."""
        name_clean = app_name.strip().lower()
        proc_map = {
            "notepad": "notepad.exe",
            "calc": "CalculatorApp.exe",
            "calculator": "CalculatorApp.exe",
            "paint": "mspaint.exe",
            "cmd": "cmd.exe",
            "terminal": "WindowsTerminal.exe",
            "chrome": "chrome.exe",
            "edge": "msedge.exe",
            "spotify": "Spotify.exe",
        }
        proc_name = proc_map.get(name_clean, f"{name_clean}.exe")
        try:
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/f", "/im", proc_name], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return f"Closed {app_name.capitalize()}."
            else:
                subprocess.run(["pkill", "-f", name_clean], check=False)
                return f"Closed {app_name.capitalize()}."
        except Exception as err:
            return f"Error closing {app_name}: {err}"

    # =========================================================================
    # 7. KEYBOARD, TYPING & CLIPBOARD
    # =========================================================================

    def type_text(self, text: str) -> str:
        """Type text into active focused desktop window."""
        if not PYAUTOGUI_AVAILABLE:
            return "Typing automation requires pyautogui."
        try:
            pyautogui.write(text, interval=0.02)
            return f"Typed text: '{text}'"
        except Exception as err:
            return f"Error typing text: {err}"

    def press_key(self, key_name: str) -> str:
        """Press a specific keyboard key (enter, space, esc, tab, etc.)."""
        if not PYAUTOGUI_AVAILABLE:
            return "Key press requires pyautogui."
        try:
            pyautogui.press(key_name.lower())
            return f"Pressed key '{key_name}'"
        except Exception as err:
            return f"Error pressing key: {err}"

    def click_mouse(self, button: str = "left", clicks: int = 1) -> str:
        """Click mouse button at current position or focus."""
        if not PYAUTOGUI_AVAILABLE:
            return "Mouse control requires pyautogui."
        try:
            pyautogui.click(button=button, clicks=clicks)
            btn_str = "Double-clicked" if clicks == 2 else f"Clicked {button} mouse button"
            return btn_str
        except Exception as err:
            return f"Error clicking mouse: {err}"

    def right_click_mouse(self) -> str:
        """Right-click mouse button."""
        return self.click_mouse(button="right", clicks=1)

    def double_click_mouse(self) -> str:
        """Double-click mouse button."""
        return self.click_mouse(button="left", clicks=2)

    def move_mouse(self, direction_or_target: str, distance: int = 200) -> str:
        """Move mouse cursor smoothly (up, down, left, right, center)."""
        if not PYAUTOGUI_AVAILABLE:
            return "Mouse control requires pyautogui."
        try:
            curr_x, curr_y = pyautogui.position()
            screen_w, screen_h = pyautogui.size()
            d = direction_or_target.strip().lower()
            if d == "center":
                target_x, target_y = screen_w // 2, screen_h // 2
            elif d in ("up", "top"):
                target_x, target_y = curr_x, max(0, curr_y - distance)
            elif d in ("down", "bottom"):
                target_x, target_y = curr_x, min(screen_h - 1, curr_y + distance)
            elif d == "left":
                target_x, target_y = max(0, curr_x - distance), curr_y
            elif d == "right":
                target_x, target_y = min(screen_w - 1, curr_x + distance), curr_y
            else:
                return f"Unknown move direction: {direction_or_target}"

            pyautogui.moveTo(target_x, target_y, duration=0.25)
            return f"Moved mouse cursor to ({target_x}, {target_y})."
        except Exception as err:
            return f"Error moving mouse: {err}"

    def execute_hotkey(self, *keys: str) -> str:
        """Trigger complex keyboard shortcut (e.g. ctrl+c, ctrl+v, win+d, alt+tab)."""
        if not PYAUTOGUI_AVAILABLE:
            return "Keyboard hotkeys require pyautogui."
        try:
            pyautogui.hotkey(*keys)
            return f"Triggered hotkey: {' + '.join(keys).upper()}"
        except Exception as err:
            return f"Error executing hotkey: {err}"

    def select_all(self) -> str:
        """Select all content in focused application (Ctrl+A)."""
        return self.execute_hotkey("ctrl", "a")

    def copy_selection(self) -> str:
        """Copy selected text/item (Ctrl+C)."""
        return self.execute_hotkey("ctrl", "c")

    def paste_selection(self) -> str:
        """Paste from clipboard (Ctrl+V)."""
        return self.execute_hotkey("ctrl", "v")

    def undo_action(self) -> str:
        """Undo last action (Ctrl+Z)."""
        return self.execute_hotkey("ctrl", "z")

    def save_file_hotkey(self) -> str:
        """Save file in focused application (Ctrl+S)."""
        return self.execute_hotkey("ctrl", "s")

    def new_tab_or_file(self) -> str:
        """Open new tab or document (Ctrl+T or Ctrl+N)."""
        return self.execute_hotkey("ctrl", "t")

    def close_tab(self) -> str:
        """Close current browser tab or document (Ctrl+W)."""
        return self.execute_hotkey("ctrl", "w")

    def reopen_tab(self) -> str:
        """Reopen last closed browser tab (Ctrl+Shift+T)."""
        return self.execute_hotkey("ctrl", "shift", "t")

    def open_start_menu(self) -> str:
        """Open Windows Start Menu (Win key)."""
        return self.press_key("win")

    def get_clipboard(self) -> str:
        """Read text from system clipboard."""
        if PYPERCLIP_AVAILABLE:
            try:
                content = pyperclip.paste()
                return f"Clipboard: {content}" if content else "Clipboard is empty."
            except Exception as err:
                return f"Error reading clipboard: {err}"
        return "Clipboard tool unavailable."

    def set_clipboard(self, text: str) -> str:
        """Copy text to system clipboard."""
        if PYPERCLIP_AVAILABLE:
            try:
                pyperclip.copy(text)
                return f"Copied '{text}' to clipboard."
            except Exception as err:
                return f"Error copying to clipboard: {err}"
        return "Clipboard tool unavailable."

    # =========================================================================
    # 8. INTENT PARSER & AUTONOMOUS DISPATCH
    # =========================================================================

    def execute_intent(self, text: str) -> Optional[dict[str, Any]]:
        """Parse natural speech or text query for Full OS or Browser automation."""
        raw = text.strip()
        lower = raw.lower()

        # 1. Close browser
        if any(lower == phrase for phrase in ["close browser", "quit browser", "exit browser", "close chrome", "close edge"]):
            msg = self.close_browser()
            return {
                "action": "close_browser",
                "success": True,
                "message": msg,
                "spoken_response": "I have closed the browser window.",
            }

        # 2. Browser Search Intent: "search for X on google", "google X"
        search_patterns = [
            r"^(?:search\s+for|google|search\s+google\s+for|look\s+up)\s+(.+?)(?:\s+on\s+(?:google|web|internet))?$",
            r"^(?:search\s+web\s+for|find)\s+(.+?)\s+online$",
        ]
        for pattern in search_patterns:
            m = re.match(pattern, lower)
            if m:
                start, end = m.span(1)
                query = raw[start:end].strip()
                if query:
                    try:
                        msg = self.search_web(query, headless=False)
                        return {
                            "action": "search_web",
                            "success": True,
                            "message": msg,
                            "spoken_response": f"I've searched Google for '{query}' and opened the results in your browser.",
                        }
                    except Exception as err:
                        return {
                            "action": "search_web",
                            "success": False,
                            "message": str(err),
                            "spoken_response": f"I could not open the browser search: {err}",
                        }

        # 3. Direct Website Navigation: "open youtube", "open github", "browse to https://..."
        open_site_patterns = [
            r"^(?:open|go\s+to|navigate\s+to|browse\s+to|visit)\s+(?:website\s+)?(https?://\S+|www\.\S+|\S+\.(?:com|org|io|dev|net|edu|gov|ai))\b",
            r"^(?:open|go\s+to|launch)\s+(youtube|google|github|reddit|twitter|x|linkedin|wikipedia|huggingface)\b",
        ]
        for pattern in open_site_patterns:
            m = re.match(pattern, lower)
            if m:
                target = m.group(1).strip()
                popular = {
                    "youtube": "https://www.youtube.com",
                    "google": "https://www.google.com",
                    "github": "https://github.com",
                    "reddit": "https://www.reddit.com",
                    "twitter": "https://x.com",
                    "x": "https://x.com",
                    "linkedin": "https://www.linkedin.com",
                    "wikipedia": "https://www.wikipedia.org",
                    "huggingface": "https://huggingface.co",
                }
                target_url = popular.get(target, target)
                try:
                    msg = self.open_url(target_url, headless=False)
                    return {
                        "action": "open_url",
                        "success": True,
                        "message": msg,
                        "spoken_response": f"I have opened {target.capitalize()} for you in the browser.",
                    }
                except Exception as err:
                    return {
                        "action": "open_url",
                        "success": False,
                        "message": str(err),
                        "spoken_response": f"Failed to open {target}: {err}",
                    }

        # 4. Desktop Windows Control: Minimize, Maximize, Switch, Close Window
        if any(lower == phrase for phrase in ["minimize all", "minimize windows", "show desktop", "minimize everything"]):
            msg = self.minimize_all_windows()
            return {
                "action": "minimize_windows",
                "success": True,
                "message": msg,
                "spoken_response": "I've minimized all open windows.",
            }
        if any(lower == phrase for phrase in ["maximize window", "maximize"]):
            msg = self.maximize_window()
            return {
                "action": "maximize_window",
                "success": True,
                "message": msg,
                "spoken_response": "Maximized active window.",
            }
        if any(lower == phrase for phrase in ["switch window", "alt tab", "next window"]):
            msg = self.switch_window()
            return {
                "action": "switch_window",
                "success": True,
                "message": msg,
                "spoken_response": "Switched window.",
            }
        if any(lower == phrase for phrase in ["close window", "close active window"]):
            msg = self.close_active_window()
            return {
                "action": "close_active_window",
                "success": True,
                "message": msg,
                "spoken_response": "Closed active window.",
            }
        if any(lower == phrase for phrase in ["lock computer", "lock pc", "lock screen", "lock workstation"]):
            msg = self.lock_workstation()
            return {
                "action": "lock_workstation",
                "success": True,
                "message": msg,
                "spoken_response": "Locking your computer.",
            }

        # 5. Volume & Media Controls
        if any(lower == phrase for phrase in ["volume up", "increase volume", "turn volume up", "louder"]):
            msg = self.control_volume("up")
            return {"action": "volume", "success": True, "message": msg, "spoken_response": "Increased volume."}
        if any(lower == phrase for phrase in ["volume down", "decrease volume", "turn volume down", "quieter"]):
            msg = self.control_volume("down")
            return {"action": "volume", "success": True, "message": msg, "spoken_response": "Decreased volume."}
        if any(lower == phrase for phrase in ["mute", "mute volume", "unmute", "mute audio"]):
            msg = self.control_volume("mute")
            return {"action": "volume", "success": True, "message": msg, "spoken_response": "Muted audio."}
        if any(lower == phrase for phrase in ["play music", "pause music", "play pause", "pause"]):
            msg = self.control_media("playpause")
            return {"action": "media", "success": True, "message": msg, "spoken_response": "Toggled media playback."}
        if any(lower == phrase for phrase in ["next song", "next track", "skip song"]):
            msg = self.control_media("next")
            return {"action": "media", "success": True, "message": msg, "spoken_response": "Skipped to next track."}
        if any(lower == phrase for phrase in ["previous song", "previous track"]):
            msg = self.control_media("prev")
            return {"action": "media", "success": True, "message": msg, "spoken_response": "Skipped to previous track."}

        # 6. Open Popular Folders: "open downloads", "open documents", "open desktop", "open c drive"
        folder_match = re.match(r"^open\s+(downloads|documents|desktop|pictures|photos|music|videos|c\s+drive|folder|workspace)\b", lower)
        if folder_match:
            folder_target = folder_match.group(1).strip()
            msg = self.open_special_folder(folder_target)
            return {
                "action": "open_folder",
                "success": True,
                "message": msg,
                "spoken_response": f"I've opened {folder_target.capitalize()} in File Explorer.",
            }

        # 7. OS Application Launch: "open notepad", "open calculator", "launch terminal", etc.
        app_match = re.match(r"^(?:open|launch|start|run)\s+(notepad|calculator|calc|explorer|files|terminal|powershell|cmd|vscode|vs\s+code|code|paint|task\s+manager|spotify|chrome|edge)\b", lower)
        if app_match:
            app_target = app_match.group(1).strip()
            msg = self.launch_application(app_target)
            return {
                "action": "launch_app",
                "success": True,
                "message": msg,
                "spoken_response": f"I've launched {app_target.capitalize()} on your computer.",
            }

        # 8. Close / Kill Desktop App: "close notepad", "close calculator", "kill chrome"
        close_app_match = re.match(r"^(?:close|kill|terminate|stop)\s+(notepad|calculator|calc|paint|terminal|cmd|chrome|edge|spotify)\b", lower)
        if close_app_match:
            app_target = close_app_match.group(1).strip()
            msg = self.close_application(app_target)
            return {
                "action": "close_app",
                "success": True,
                "message": msg,
                "spoken_response": f"Closed {app_target.capitalize()}.",
            }

        # 9. System Status, Specs, Battery & Health
        if any(phrase in lower for phrase in ["system info", "system information", "system specs", "computer specs", "system status", "check system", "battery status", "check battery"]):
            specs = self.get_system_specs()
            h = self.get_system_health()
            spoken = f"Your system has {h['cpu_percent']} percent CPU usage and {h['ram_percent']} percent memory usage."
            if h["battery_percent"] is not None:
                spoken += f" Battery is at {h['battery_percent']} percent."
            return {
                "action": "system_specs",
                "success": True,
                "message": specs,
                "spoken_response": spoken,
            }

        if any(phrase in lower for phrase in ["top processes", "what is using ram", "show processes", "what is using memory"]):
            proc_info = self.list_top_processes(5)
            return {
                "action": "list_processes",
                "success": True,
                "message": proc_info,
                "spoken_response": "Here are the top memory processes displayed on screen.",
            }

        # 10. Browser Scrolling
        if "scroll" in lower:
            if "up" in lower or "top" in lower:
                direction = "top" if "top" in lower else "up"
                msg = self.scroll_page(direction)
                return {"action": "scroll_page", "success": True, "message": msg, "spoken_response": "Scrolled up the page."}
            else:
                direction = "bottom" if "bottom" in lower else "down"
                msg = self.scroll_page(direction)
                return {"action": "scroll_page", "success": True, "message": msg, "spoken_response": "Scrolled down the page."}

        # 11. Browser Navigation
        if any(lower.startswith(p) or lower == p for p in ["go back", "back page", "previous page"]):
            msg = self.browser_navigate("back")
            return {"action": "browser_navigate", "success": True, "message": msg, "spoken_response": "Navigated back."}
        if any(lower.startswith(p) or lower == p for p in ["go forward", "forward page"]):
            msg = self.browser_navigate("forward")
            return {"action": "browser_navigate", "success": True, "message": msg, "spoken_response": "Navigated forward."}
        if any(lower.startswith(p) or lower == p for p in ["refresh", "reload", "refresh page", "reload page"]):
            msg = self.browser_navigate("refresh")
            return {"action": "browser_navigate", "success": True, "message": msg, "spoken_response": "Page refreshed."}

        # 12. Screenshot
        if any(phrase in lower for phrase in ["take screenshot", "capture screen", "screenshot"]):
            msg = self.take_screenshot("electorn_screenshot.png")
            return {"action": "screenshot", "success": True, "message": msg, "spoken_response": "Screenshot captured and saved to workspace."}

        # 13. Empty Recycle Bin
        if any(phrase in lower for phrase in ["empty recycle bin", "clean recycle bin", "clear recycle bin"]):
            msg = self.empty_recycle_bin()
            return {"action": "recycle_bin", "success": True, "message": msg, "spoken_response": "Recycle bin emptied."}

        # 14. Clipboard Automation
        if any(phrase in lower for phrase in ["read clipboard", "what is on my clipboard", "show clipboard"]):
            msg = self.get_clipboard()
            return {"action": "clipboard", "success": True, "message": msg, "spoken_response": "Here is the content of your clipboard."}

        # 15. Typing Automation: "type Hello World"
        if lower.startswith("type "):
            text_to_type = raw[5:].strip()
            msg = self.type_text(text_to_type)
            return {"action": "type_text", "success": True, "message": msg, "spoken_response": f"Typed '{text_to_type}'."}

        # 16. Key Press: "press enter", "press space", "press escape"
        press_match = re.match(r"^(?:press|hit|type)\s+(enter|space|spacebar|escape|esc|tab|backspace|delete|up|down|left|right)\b", lower)
        if press_match:
            k = press_match.group(1).strip()
            if k == "spacebar":
                k = "space"
            msg = self.press_key(k)
            return {"action": "press_key", "success": True, "message": msg, "spoken_response": f"Pressed {k} key."}

        # 17. Hands-Free Mouse Clicking & Interaction
        if any(lower == phrase for phrase in ["click", "left click", "click here", "press click", "click mouse"]):
            msg = self.click_mouse("left", 1)
            return {"action": "click", "success": True, "message": msg, "spoken_response": "Clicked."}

        if any(lower == phrase for phrase in ["double click", "double click here", "open this"]):
            msg = self.double_click_mouse()
            return {"action": "double_click", "success": True, "message": msg, "spoken_response": "Double clicked."}

        if any(lower == phrase for phrase in ["right click", "context menu"]):
            msg = self.right_click_mouse()
            return {"action": "right_click", "success": True, "message": msg, "spoken_response": "Right clicked."}

        # 18. Hands-Free Cursor Movement: "move mouse up", "cursor down", "move cursor center"
        move_match = re.match(r"^(?:move\s+(?:mouse|cursor)|cursor|mouse)\s+(up|down|left|right|center|top|bottom)\b", lower)
        if move_match:
            dir_target = move_match.group(1).strip()
            msg = self.move_mouse(dir_target, distance=250)
            return {"action": "move_mouse", "success": True, "message": msg, "spoken_response": f"Moved cursor {dir_target}."}

        # 19. Hands-Free Editing & Document Shortcuts: Select All, Copy, Paste, Undo, Save
        if any(lower == phrase for phrase in ["select all", "highlight all"]):
            msg = self.select_all()
            return {"action": "select_all", "success": True, "message": msg, "spoken_response": "Selected all content."}

        if any(lower == phrase for phrase in ["copy", "copy this", "copy text"]):
            msg = self.copy_selection()
            return {"action": "copy", "success": True, "message": msg, "spoken_response": "Copied to clipboard."}

        if any(lower == phrase for phrase in ["paste", "paste text", "paste here"]):
            msg = self.paste_selection()
            return {"action": "paste", "success": True, "message": msg, "spoken_response": "Pasted."}

        if any(lower == phrase for phrase in ["undo", "undo that", "revert"]):
            msg = self.undo_action()
            return {"action": "undo", "success": True, "message": msg, "spoken_response": "Undone."}

        if any(lower == phrase for phrase in ["save", "save file", "save document"]):
            msg = self.save_file_hotkey()
            return {"action": "save_file", "success": True, "message": msg, "spoken_response": "Saved document."}

        # 20. Hands-Free Browser Tab Management
        if any(lower == phrase for phrase in ["new tab", "open new tab", "create tab"]):
            msg = self.new_tab_or_file()
            return {"action": "new_tab", "success": True, "message": msg, "spoken_response": "Opened new tab."}

        if any(lower == phrase for phrase in ["close tab", "kill tab", "exit tab"]):
            msg = self.close_tab()
            return {"action": "close_tab", "success": True, "message": msg, "spoken_response": "Closed tab."}

        if any(lower == phrase for phrase in ["reopen tab", "restore tab", "undo close tab"]):
            msg = self.reopen_tab()
            return {"action": "reopen_tab", "success": True, "message": msg, "spoken_response": "Reopened previous tab."}

        # 21. Start Menu & Windows Shell
        if any(lower == phrase for phrase in ["start menu", "open start", "windows menu", "press windows"]):
            msg = self.open_start_menu()
            return {"action": "start_menu", "success": True, "message": msg, "spoken_response": "Opened Start menu."}

        # 22. Autonomous Entertainment / Media: "play X on youtube", "play X on spotify"
        yt_play_match = re.match(r"^play\s+(.+?)(?:\s+on\s+youtube)?$", lower)
        if yt_play_match and not any(lower == p for p in ["play music", "play pause", "play"]):
            yt_query = yt_play_match.group(1).strip()
            yt_url = f"https://www.youtube.com/results?search_query={quote_plus(yt_query)}"
            msg = self.open_url(yt_url, headless=False)
            return {
                "action": "play_youtube",
                "success": True,
                "message": msg,
                "spoken_response": f"Playing '{yt_query}' on YouTube in your browser.",
            }

        return None
