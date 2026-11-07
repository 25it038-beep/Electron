/**
 * Native Windows application and window lifecycle manager.
 */

import { execSync } from 'child_process';

export interface WindowInfo {
  handle: string;
  title: string;
  processName: string;
  isForeground: boolean;
}

export class WindowController {
  private appAliasMap: Record<string, string> = {
    chrome: 'chrome.exe',
    googlechrome: 'chrome.exe',
    edge: 'msedge.exe',
    msedge: 'msedge.exe',
    browser: 'msedge.exe',
    vscode: 'code.cmd',
    code: 'code.cmd',
    notepad: 'notepad.exe',
    calc: 'calc.exe',
    calculator: 'calc.exe',
    explorer: 'explorer.exe',
    files: 'explorer.exe',
    terminal: 'wt.exe',
    cmd: 'cmd.exe',
    powershell: 'powershell.exe',
    word: 'winword.exe',
    excel: 'excel.exe',
    powerpoint: 'powerpnt.exe',
    ppt: 'powerpnt.exe',
  };

  /**
   * Launch an application using its friendly name or executable path.
   */
  public launchApp(appNameOrPath: string): boolean {
    const clean = appNameOrPath.trim().toLowerCase();
    const exe = this.appAliasMap[clean] || appNameOrPath;

    try {
      if (process.platform === 'win32') {
        execSync(`powershell -NoProfile -Command "Start-Process '${exe}'"`, { timeout: 3000 });
        return true;
      }
    } catch (e) {
      try {
        execSync(`start "" "${exe}"`, { shell: 'cmd.exe', timeout: 3000 });
        return true;
      } catch (err) {
        return false;
      }
    }
    return false;
  }

  /**
   * Close application by executable or process name.
   */
  public closeApp(appName: string, force: boolean = false): boolean {
    const clean = appName.trim().toLowerCase();
    const exe = this.appAliasMap[clean] || (clean.endsWith('.exe') ? clean : `${clean}.exe`);

    try {
      const flag = force ? '/F' : '';
      execSync(`taskkill /IM "${exe}" ${flag}`, { timeout: 3000, stdio: 'ignore' });
      return true;
    } catch (e) {
      return false;
    }
  }

  /**
   * Get title and process of the currently focused active window.
   */
  public getActiveWindow(): { title: string; processName: string } {
    if (process.platform === 'win32') {
      try {
        const script = `
          $sig = @'
[DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
[DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder text, int count);
[DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
'@
          $w = Add-Type -memberDefinition $sig -name "ActiveWin" -namespace "Win32" -passThru
          $hwnd = $w::GetForegroundWindow()
          $sb = New-Object System.Text.StringBuilder 256
          $w::GetWindowText($hwnd, $sb, 256) | Out-Null
          $pid = 0
          $w::GetWindowThreadProcessId($hwnd, [ref]$pid) | Out-Null
          $proc = (Get-Process -Id $pid -ErrorAction SilentlyContinue).ProcessName
          Write-Output "$($sb.ToString())|||$proc"
        `;
        const res = execSync(`powershell -NoProfile -Command "${script}"`, { timeout: 3000, encoding: 'utf-8' });
        const parts = res.trim().split('|||');
        return {
          title: (parts[0] || '').trim(),
          processName: (parts[1] || '').trim(),
        };
      } catch (e) {
        // Fallback
      }
    }
    return { title: '', processName: '' };
  }

  /**
   * List all visible open windows.
   */
  public listWindows(): WindowInfo[] {
    const list: WindowInfo[] = [];
    if (process.platform === 'win32') {
      try {
        const script = `
          Get-Process | Where-Object { $_.MainWindowTitle } | Select-Object Id, MainWindowTitle, ProcessName | ConvertTo-Json -Compress
        `;
        const out = execSync(`powershell -NoProfile -Command "${script}"`, { timeout: 3000, encoding: 'utf-8' });
        const raw = JSON.parse(out);
        const arr = Array.isArray(raw) ? raw : [raw];
        for (const item of arr) {
          if (item && item.MainWindowTitle) {
            list.push({
              handle: String(item.Id),
              title: item.MainWindowTitle,
              processName: item.ProcessName,
              isForeground: false,
            });
          }
        }
      } catch (e) {
        // Return empty or fallback
      }
    }
    return list;
  }

  /**
   * Focus window by title substring.
   */
  public focusWindow(titleSubstr: string): boolean {
    if (process.platform === 'win32') {
      try {
        const script = `
          $w = (Get-Process | Where-Object { $_.MainWindowTitle -like '*${titleSubstr}*' } | Select-Object -First 1)
          if ($w) {
            $sig = @'
[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
[DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
'@
            $u = Add-Type -memberDefinition $sig -name "FocusWin" -namespace "Win32" -passThru
            $u::ShowWindow($w.MainWindowHandle, 9) | Out-Null # SW_RESTORE
            $u::SetForegroundWindow($w.MainWindowHandle) | Out-Null
            return $true
          }
        `;
        execSync(`powershell -NoProfile -Command "${script}"`, { timeout: 3000 });
        return true;
      } catch (e) {
        return false;
      }
    }
    return false;
  }

  /**
   * Minimize all windows and reveal desktop.
   */
  public minimizeAll(): void {
    if (process.platform === 'win32') {
      try {
        const script = `(New-Object -ComObject Shell.Application).MinimizeAll()`;
        execSync(`powershell -NoProfile -Command "${script}"`, { timeout: 2000 });
      } catch (e) {}
    }
  }

  /**
   * Maximize currently focused active window.
   */
  public maximizeActive(): void {
    if (process.platform === 'win32') {
      try {
        const script = `
          $wscript = New-Object -ComObject WScript.Shell;
          $wscript.SendKeys("% x"); # Alt + Space, x
        `;
        execSync(`powershell -NoProfile -Command "${script}"`, { timeout: 2000 });
      } catch (e) {}
    }
  }
}
