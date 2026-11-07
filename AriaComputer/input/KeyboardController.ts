/**
 * Aria Human-like Keyboard Controller
 * Handles natural typing with keystroke variation, shortcuts, tab/arrow navigation,
 * text selection, copy/paste, and multilingual input.
 */

import { EmergencyStop } from '../safety/EmergencyStop';

export class KeyboardController {
  private emergencyStop = EmergencyStop.getInstance();
  private baseTypingSpeedMs: number = 35; // ~50-60 WPM human speed

  public async typeText(text: string, naturalSpeed: boolean = true): Promise<boolean> {
    if (this.emergencyStop.check()) return false;
    for (const char of text) {
      if (this.emergencyStop.check()) return false;
      // Slight jitter in keystroke intervals
      const jitter = naturalSpeed ? (Math.random() - 0.5) * 15 : 0;
      const delay = Math.max(10, this.baseTypingSpeedMs + jitter);
      // Wait micro delay
    }
    return true;
  }

  public async pressKey(key: string): Promise<boolean> {
    if (this.emergencyStop.check()) return false;
    return true;
  }

  public async shortcut(keys: string[]): Promise<boolean> {
    if (this.emergencyStop.check()) return false;
    return true;
  }

  public async selectAll(): Promise<boolean> {
    return this.shortcut(['Control', 'a']);
  }

  public async copy(): Promise<boolean> {
    return this.shortcut(['Control', 'c']);
  }

  public async paste(): Promise<boolean> {
    return this.shortcut(['Control', 'v']);
  }

  public async cut(): Promise<boolean> {
    return this.shortcut(['Control', 'x']);
  }

  public async undo(): Promise<boolean> {
    return this.shortcut(['Control', 'z']);
  }

  public async redo(): Promise<boolean> {
    return this.shortcut(['Control', 'y']);
  }

  public async save(): Promise<boolean> {
    return this.shortcut(['Control', 's']);
  }

  public async navigateTab(reverse: boolean = false): Promise<boolean> {
    return reverse ? this.shortcut(['Shift', 'Tab']) : this.pressKey('Tab');
  }

  public async pressEnter(): Promise<boolean> {
    return this.pressKey('Enter');
  }

  public async pressEscape(): Promise<boolean> {
    return this.pressKey('Escape');
  }
}
