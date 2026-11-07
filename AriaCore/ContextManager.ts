/**
 * Aria Unified Context Manager: Maintains shared multi-turn session state.
 */

export interface AriaSessionContext {
  userId: string;
  userName: string;
  sessionId: string;
  activeMode: string;
  activeApplication: string;
  activeWindow: string;
  activeTask?: string;
  lastUserUtterance?: string;
  lastAriaResponse?: string;
  recentConversation: Array<{ role: 'user' | 'aria'; text: string; timestamp: number }>;
  workingMemory: Record<string, unknown>;
  startTime: number;
  lastInteractionTime: number;
}

export class ContextManager {
  private context: AriaSessionContext;

  constructor(userName: string = 'Harshan') {
    this.context = {
      userId: 'user_harshan',
      userName,
      sessionId: `aria_${Date.now()}`,
      activeMode: 'COMPANION',
      activeApplication: 'Desktop',
      activeWindow: 'Desktop',
      recentConversation: [],
      workingMemory: {},
      startTime: Date.now(),
      lastInteractionTime: Date.now(),
    };
  }

  public getContext(): AriaSessionContext {
    return { ...this.context };
  }

  public updateActiveWindow(appName: string, windowTitle: string): void {
    this.context.activeApplication = appName;
    this.context.activeWindow = windowTitle;
    this.context.lastInteractionTime = Date.now();
  }

  public recordInteraction(role: 'user' | 'aria', text: string): void {
    this.context.recentConversation.push({
      role,
      text,
      timestamp: Date.now(),
    });
    if (this.context.recentConversation.length > 30) {
      this.context.recentConversation.shift();
    }
    if (role === 'user') this.context.lastUserUtterance = text;
    if (role === 'aria') this.context.lastAriaResponse = text;
    this.context.lastInteractionTime = Date.now();
  }

  public setWorkingMemory(key: string, value: unknown): void {
    this.context.workingMemory[key] = value;
  }

  public getWorkingMemory<T>(key: string): T | undefined {
    return this.context.workingMemory[key] as T;
  }
}
