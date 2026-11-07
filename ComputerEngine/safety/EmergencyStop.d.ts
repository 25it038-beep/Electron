/**
 * Global Emergency Stop mechanism.
 * Instantly halts all active automation, cancels pending actions, and releases keys/mouse.
 */
export type EmergencyStopListener = (reason: string) => void;
export declare class EmergencyStop {
    private static instance;
    private isStopped;
    private stopReason;
    private stopTimestamp;
    private listeners;
    private constructor();
    static getInstance(): EmergencyStop;
    trigger(reason?: string): void;
    reset(): void;
    check(): boolean;
    getReason(): string;
    onEmergencyStop(listener: EmergencyStopListener): () => void;
}
