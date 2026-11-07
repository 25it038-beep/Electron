/**
 * Native clipboard management with context saving, restoration, and Unicode support.
 */

import { execSync } from 'child_process';

export class ClipboardController {
  private savedHistory: string[] = [];

  /**
   * Read text currently stored in the system clipboard.
   */
  public async getText(): Promise<string> {
    if (process.platform === 'win32') {
      try {
        const script = `Get-Clipboard -Raw`;
        const res = execSync(`powershell -NoProfile -Command "${script}"`, { timeout: 2000, encoding: 'utf-8' });
        return res ?? '';
      } catch (e) {
        return '';
      }
    }
    return '';
  }

  /**
   * Set text into the system clipboard with full Unicode compatibility.
   */
  public async setText(text: string): Promise<void> {
    if (process.platform === 'win32') {
      try {
        // Use Set-Clipboard with UTF8 stdin pipeline
        const child = require('child_process').spawn('powershell', ['-NoProfile', '-Command', 'Set-Clipboard'], {
          stdio: ['pipe', 'ignore', 'ignore'],
        });
        child.stdin.setDefaultEncoding('utf-8');
        child.stdin.write(text);
        child.stdin.end();
        await new Promise(r => child.on('close', r));
      } catch (e) {
        // Fallback
      }
    }
  }

  /**
   * Clear the clipboard contents.
   */
  public async clear(): Promise<void> {
    if (process.platform === 'win32') {
      try {
        execSync(`powershell -NoProfile -Command "Clear-Clipboard"`, { timeout: 2000 });
      } catch (e) {
        // Suppress
      }
    }
  }

  /**
   * Backup active clipboard content before an automation task.
   */
  public async backup(): Promise<void> {
    const text = await this.getText();
    this.savedHistory.push(text);
  }

  /**
   * Restore previously backed up clipboard content.
   */
  public async restore(): Promise<void> {
    const text = this.savedHistory.pop();
    if (text !== undefined) {
      await this.setText(text);
    }
  }
}
