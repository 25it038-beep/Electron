/**
 * Aria Computer Emergency Stop
 * Instantly halts all active automation, mouse/keyboard input, and background processes.
 */

export class EmergencyStop {
  private static instance: EmergencyStop;
  private isHalted: boolean = false;
  private reason: string = '';
  private haltTimestamp: number = 0;

  private constructor() {}

  public static getInstance(): EmergencyStop {
    if (!EmergencyStop.instance) {
      EmergencyStop.instance = new EmergencyStop();
    }
    return EmergencyStop.instance;
  }

  public trigger(reason: string = 'User voice interrupt: STOP'): void {
    this.isHalted = true;
    this.reason = reason;
    this.haltTimestamp = Date.now();
  }

  public reset(): void {
    this.isHalted = false;
    this.reason = '';
    this.haltTimestamp = 0;
  }

  public check(): boolean {
    return this.isHalted;
  }

  public getReason(): string {
    return this.reason;
  }

  public getHaltTimestamp(): number {
    return this.haltTimestamp;
  }
}
