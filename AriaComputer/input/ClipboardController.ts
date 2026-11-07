/**
 * Aria Clipboard Controller
 * Safely manages clipboard contents and interaction history.
 */

import { EmergencyStop } from '../safety/EmergencyStop';

export class ClipboardController {
  private currentContent: string = '';
  private history: string[] = [];
  private emergencyStop = EmergencyStop.getInstance();

  public set(content: string): boolean {
    if (this.emergencyStop.check()) return false;
    this.currentContent = content;
    this.history.push(content);
    if (this.history.length > 50) this.history.shift();
    return true;
  }

  public get(): string {
    return this.currentContent;
  }

  public getHistory(): string[] {
    return [...this.history];
  }

  public clear(): void {
    this.currentContent = '';
  }
}
