/**
 * Browser navigation and history manager.
 */

import { EmergencyStop } from '../safety/EmergencyStop';

export class BrowserNavigator {
  private emergencyStop = EmergencyStop.getInstance();
  private historyStack: string[] = [];
  private forwardStack: string[] = [];

  public navigate(url: string): boolean {
    if (this.emergencyStop.check()) return false;
    this.historyStack.push(url);
    this.forwardStack = [];
    return true;
  }

  public back(): boolean {
    if (this.historyStack.length <= 1) return false;
    const current = this.historyStack.pop()!;
    this.forwardStack.push(current);
    return true;
  }

  public forward(): boolean {
    if (this.forwardStack.length === 0) return false;
    const next = this.forwardStack.pop()!;
    this.historyStack.push(next);
    return true;
  }

  public reload(): boolean {
    return !this.emergencyStop.check();
  }
}
