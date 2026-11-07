/**
 * Low-latency keyboard automation supporting natural typing, configurable speed,
 * multilingual Unicode text, and complex shortcut combinations.
 */

import { execSync } from 'child_process';
import { EmergencyStop } from '../safety/EmergencyStop';
import { ClipboardController } from './ClipboardController';

export interface TypingOptions {
  wordsPerMinute?: number;
  delayPerCharMs?: number;
  useClipboardForUnicode?: boolean;
}

export class KeyboardController {
  private clipboard: ClipboardController;
  private emergencyStop = EmergencyStop.getInstance();
  private defaultDelayMs: number = 25;

  constructor(clipboard?: ClipboardController) {
    this.clipboard = clipboard || new ClipboardController();
  }

  /**
   * Set global typing delay per character (in milliseconds).
   */
  public setTypingSpeed(wordsPerMinute: number): void {
    // 1 word ~= 5 characters. WPM -> ms per char: (60,000 / (WPM * 5))
    this.defaultDelayMs = Math.max(5, Math.round(12000 / Math.max(10, wordsPerMinute)));
  }

  /**
   * Type text naturally into the currently focused desktop control.
   */
  public async typeText(text: string, options?: TypingOptions): Promise<void> {
    if (this.emergencyStop.check() || !text) return;

    const delay = options?.delayPerCharMs ?? (options?.wordsPerMinute ? Math.round(12000 / options.wordsPerMinute) : this.defaultDelayMs);
    const hasUnicode = /[^\u0000-\u007F]/.test(text);

    // If text contains complex Unicode or is very long, use instantaneous safe clipboard paste
    if ((hasUnicode || text.length > 80) && options?.useClipboardForUnicode !== false) {
      await this.pasteText(text);
      return;
    }

    if (process.platform === 'win32') {
      // Escape for VBS/PowerShell SendKeys
      const escaped = text
        .replace(/[{}[\]+^%~()]/g, '{$&}')
        .replace(/"/g, '""');

      const script = `
        Add-Type -AssemblyName System.Windows.Forms;
        [System.Windows.Forms.SendKeys]::SendWait("${escaped}");
      `;
      try {
        execSync(`powershell -NoProfile -Command "${script}"`, { timeout: 5000 });
      } catch (e) {
        // Fallback to clipboard paste
        await this.pasteText(text);
      }
    }
  }

  /**
   * Paste text safely via system clipboard.
   */
  public async pasteText(text: string): Promise<void> {
    if (this.emergencyStop.check()) return;
    const previous = await this.clipboard.getText();
    await this.clipboard.setText(text);
    await this.pressShortcut(['Control', 'v']);
    await new Promise(r => setTimeout(r, 80));
    // Optionally restore previous clipboard if needed
  }

  /**
   * Press a single standard key (e.g., 'Enter', 'Escape', 'Tab', 'Backspace', 'F5').
   */
  public async pressKey(key: string): Promise<void> {
    if (this.emergencyStop.check()) return;

    const keyMap: Record<string, string> = {
      enter: '{ENTER}',
      return: '{ENTER}',
      esc: '{ESC}',
      escape: '{ESC}',
      tab: '{TAB}',
      backspace: '{BACKSPACE}',
      space: ' ',
      delete: '{DEL}',
      up: '{UP}',
      down: '{DOWN}',
      left: '{LEFT}',
      right: '{RIGHT}',
      home: '{HOME}',
      end: '{END}',
      f1: '{F1}',
      f2: '{F2}',
      f5: '{F5}',
      f11: '{F11}',
      f12: '{F12}',
    };

    const targetKey = keyMap[key.toLowerCase()] || key;

    if (process.platform === 'win32') {
      const script = `
        Add-Type -AssemblyName System.Windows.Forms;
        [System.Windows.Forms.SendKeys]::SendWait("${targetKey}");
      `;
      try {
        execSync(`powershell -NoProfile -Command "${script}"`, { timeout: 3000 });
      } catch (e) {
        // Suppress
      }
    }
  }

  /**
   * Press a combination of keys together (e.g. ['Control', 's'], ['Alt', 'Tab'], ['Win', 'r']).
   */
  public async pressShortcut(keys: string[]): Promise<void> {
    if (this.emergencyStop.check() || !keys || keys.length === 0) return;

    const lowerKeys = keys.map(k => k.toLowerCase());

    // Native Win32 SendKeys representation:
    // Control = ^, Shift = +, Alt = %
    let modifier = '';
    const mainKeys: string[] = [];

    for (const k of lowerKeys) {
      if (k === 'ctrl' || k === 'control') modifier += '^';
      else if (k === 'alt') modifier += '%';
      else if (k === 'shift') modifier += '+';
      else mainKeys.push(k);
    }

    if (modifier && mainKeys.length > 0) {
      const combined = `${modifier}(${mainKeys.join('')})`;
      if (process.platform === 'win32') {
        const script = `
          Add-Type -AssemblyName System.Windows.Forms;
          [System.Windows.Forms.SendKeys]::SendWait("${combined}");
        `;
        try {
          execSync(`powershell -NoProfile -Command "${script}"`, { timeout: 3000 });
          return;
        } catch (e) {
          // Fallback
        }
      }
    }

    // Special Windows key shortcuts
    if (lowerKeys.includes('win') || lowerKeys.includes('windows')) {
      const other = lowerKeys.filter(k => k !== 'win' && k !== 'windows')[0] || '';
      if (process.platform === 'win32') {
        const script = `
          $wscript = New-Object -ComObject WScript.Shell;
          $wscript.SendKeys("^{ESC}");
        `;
        execSync(`powershell -NoProfile -Command "${script}"`, { timeout: 2000 });
      }
    }
  }

  public async selectAll(): Promise<void> {
    await this.pressShortcut(['Control', 'a']);
  }

  public async copy(): Promise<void> {
    await this.pressShortcut(['Control', 'c']);
  }

  public async paste(): Promise<void> {
    await this.pressShortcut(['Control', 'v']);
  }

  public async undo(): Promise<void> {
    await this.pressShortcut(['Control', 'z']);
  }

  public async redo(): Promise<void> {
    await this.pressShortcut(['Control', 'y']);
  }
}
