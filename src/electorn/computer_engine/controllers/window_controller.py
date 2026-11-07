"""Windows desktop application lifecycle and window focus manager."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional


class WindowController:
    """Manages launching, focusing, minimizing, and closing desktop applications."""

    APP_MAP = {
        "chrome": ["chrome.exe"],
        "edge": ["msedge.exe"],
        "browser": ["msedge.exe", "chrome.exe"],
        "vscode": ["code.cmd", "code.exe"],
        "code": ["code.cmd", "code.exe"],
        "notepad": ["notepad.exe"],
        "calc": ["calc.exe"],
        "calculator": ["calc.exe"],
        "explorer": ["explorer.exe"],
        "terminal": ["wt.exe", "powershell.exe"],
        "cmd": ["cmd.exe"],
        "excel": ["excel.exe"],
        "word": ["winword.exe"],
        "powerpoint": ["powerpnt.exe"],
        "ppt": ["powerpnt.exe"],
    }

    def launch_app(self, app_name: str, wait_seconds: float = 0.5) -> bool:
        """Launch desktop application by friendly name or path."""
        clean = app_name.strip().lower()
        executables = self.APP_MAP.get(clean, [clean if clean.endswith(".exe") else f"{clean}.exe"])

        for exe in executables:
            try:
                if sys.platform == "win32":
                    subprocess.Popen(f"start {exe}", shell=True)
                else:
                    subprocess.Popen([exe])
                time.sleep(wait_seconds)
                return True
            except Exception:
                continue
        return False

    def launch_application(self, app_name: str, wait_seconds: float = 0.5) -> bool:
        """Alias for launch_app."""
        return self.launch_app(app_name, wait_seconds)

    def close_app(self, app_name: str, force: bool = True) -> bool:
        """Close an application process."""
        clean = app_name.strip().lower()
        target = clean if clean.endswith(".exe") else f"{clean}.exe"

        if sys.platform == "win32":
            cmd = ["taskkill", "/IM", target]
            if force:
                cmd.append("/F")
            res = subprocess.run(cmd, capture_output=True, check=False)
            # return true if killed or if process wasn't found (already closed)
            return res.returncode in (0, 128)
        return True

    def close_window(self, app_name: str, force: bool = True) -> bool:
        """Alias for close_app."""
        return self.close_app(app_name, force)

    def get_active_window(self) -> Dict[str, str]:
        """Inspect the currently focused active window."""
        if sys.platform == "win32":
            try:
                script = """
                $sig = @'
[DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
[DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder text, int count);
'@
                $u = Add-Type -memberDefinition $sig -name "Win32ActiveWin" -namespace "Win32" -passThru
                $h = $u::GetForegroundWindow()
                $sb = New-Object System.Text.StringBuilder 256
                $u::GetWindowText($h, $sb, 256) | Out-Null
                $title = $sb.ToString()
                $p = (Get-Process | Where-Object { $_.MainWindowHandle -eq $h } | Select-Object -First 1).ProcessName
                @{ Title = $title; ProcessName = $p } | ConvertTo-Json -Compress
                """
                res = subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True, text=True, check=False, timeout=3)
                import json
                data = json.loads(res.stdout)
                return {
                    "title": data.get("Title", "Desktop"),
                    "process_name": data.get("ProcessName", "explorer"),
                }
            except Exception:
                pass
        return {"title": "Desktop", "process_name": "explorer"}

    def list_windows(self) -> List[Dict[str, str]]:
        """List open desktop windows."""
        windows: List[Dict[str, str]] = []
        if sys.platform == "win32":
            try:
                script = "Get-Process | Where-Object { $_.MainWindowTitle } | Select-Object Id, MainWindowTitle, ProcessName | ConvertTo-Json -Compress"
                res = subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True, text=True, check=False, timeout=3)
                import json
                if res.stdout.strip():
                    raw = json.loads(res.stdout)
                    arr = raw if isinstance(raw, list) else [raw]
                    for item in arr:
                        if item and item.get("MainWindowTitle"):
                            windows.append({
                                "id": str(item.get("Id")),
                                "title": item.get("MainWindowTitle"),
                                "process_name": item.get("ProcessName", ""),
                            })
            except Exception:
                pass

        if not windows:
            windows.append({
                "id": "1",
                "title": "Windows File Explorer",
                "process_name": "explorer.exe",
            })
        return windows

    def focus_window(self, title_substring: str) -> bool:
        """Focus window by title match."""
        if sys.platform == "win32":
            try:
                script = f"""
                $w = (Get-Process | Where-Object {{ $_.MainWindowTitle -like '*{title_substring}*' }} | Select-Object -First 1)
                if ($w) {{
                    $sig = @'
[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
[DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
'@
                    $u = Add-Type -memberDefinition $sig -name "FocusWinPy" -namespace "Win32" -passThru
                    $u::ShowWindow($w.MainWindowHandle, 9) | Out-Null
                    $u::SetForegroundWindow($w.MainWindowHandle) | Out-Null
                }}
                """
                subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True, check=False, timeout=3)
                return True
            except Exception:
                return False
        return False

    def minimize_all(self) -> None:
        """Minimize all windows."""
        if sys.platform == "win32":
            try:
                subprocess.run(["powershell", "-NoProfile", "-Command", "(New-Object -ComObject Shell.Application).MinimizeAll()"], capture_output=True, check=False)
            except Exception:
                pass

    def maximize_active(self) -> None:
        """Maximize focused window."""
        try:
            import pyautogui
            pyautogui.hotkey("alt", "space")
            time.sleep(0.05)
            pyautogui.press("x")
        except Exception:
            pass
