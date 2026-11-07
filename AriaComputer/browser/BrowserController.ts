/**
 * Aria Browser Controller
 * Interacts with Chrome/Edge browsers for navigation, search, and tab management.
 */

import { EmergencyStop } from '../safety/EmergencyStop';

export class BrowserController {
  private emergencyStop = EmergencyStop.getInstance();
  private activeUrl: string = 'about:blank';
  private openTabs: string[] = ['about:blank'];

  public openUrl(url: string): boolean {
    if (this.emergencyStop.check()) return false;
    this.activeUrl = url;
    if (!this.openTabs.includes(url)) {
      this.openTabs.push(url);
    }
    return true;
  }

  public search(query: string): boolean {
    if (this.emergencyStop.check()) return false;
    const url = `https://www.google.com/search?q=${encodeURIComponent(query)}`;
    return this.openUrl(url);
  }

  public getActiveUrl(): string {
    return this.activeUrl;
  }

  public getOpenTabs(): string[] {
    return [...this.openTabs];
  }

  public closeCurrentTab(): boolean {
    if (this.emergencyStop.check()) return false;
    if (this.openTabs.length > 0) {
      this.openTabs.pop();
      this.activeUrl = this.openTabs[this.openTabs.length - 1] || 'about:blank';
      return true;
    }
    return false;
  }
}
