/**
 * Global Emergency Stop mechanism.
 * Instantly halts all active automation, cancels pending actions, and releases keys/mouse.
 */

export type EmergencyStopListener = (reason: string) => void;

export class EmergencyStop {
  private static instance: EmergencyStop;
  private isStopped: boolean = false;
  private stopReason: string = '';
  private stopTimestamp: number = 0;
  private listeners: Set<EmergencyStopListener> = new Set();

  private constructor() {}

  public static getInstance(): EmergencyStop {
    if (!EmergencyStop.instance) {
      EmergencyStop.instance = new EmergencyStop();
    }
    return EmergencyStop.instance;
  }

  public trigger(reason: string = 'User initiated emergency stop'): void {
    this.isStopped = true;
    this.stopReason = reason;
    this.stopTimestamp = Date.now();

    for (const listener of this.listeners) {
      try {
        listener(reason);
      } catch (e) {
        // Suppress listener errors during emergency shutdown
      }
    }
  }

  public reset(): void {
    this.isStopped = false;
    this.stopReason = '';
    this.stopTimestamp = 0;
  }

  public check(): boolean {
    return this.isStopped;
  }

  public getReason(): string {
    return this.stopReason;
  }

  public onEmergencyStop(listener: EmergencyStopListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }
}
