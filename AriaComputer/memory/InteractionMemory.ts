/**
 * Aria Interaction Log Memory
 * Records recent clicks, keystrokes, application focuses, and session context.
 */

export interface InteractionLog {
  timestamp: number;
  action: string;
  target?: string;
  success: boolean;
}

export class InteractionMemory {
  private logs: InteractionLog[] = [];

  public log(action: string, target?: string, success: boolean = true): void {
    this.logs.push({ timestamp: Date.now(), action, target, success });
    if (this.logs.length > 200) this.logs.shift();
  }

  public getRecent(limit: number = 10): InteractionLog[] {
    return this.logs.slice(-limit);
  }
}
