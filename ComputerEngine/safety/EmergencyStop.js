"use strict";
/**
 * Global Emergency Stop mechanism.
 * Instantly halts all active automation, cancels pending actions, and releases keys/mouse.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.EmergencyStop = void 0;
class EmergencyStop {
    static instance;
    isStopped = false;
    stopReason = '';
    stopTimestamp = 0;
    listeners = new Set();
    constructor() { }
    static getInstance() {
        if (!EmergencyStop.instance) {
            EmergencyStop.instance = new EmergencyStop();
        }
        return EmergencyStop.instance;
    }
    trigger(reason = 'User initiated emergency stop') {
        this.isStopped = true;
        this.stopReason = reason;
        this.stopTimestamp = Date.now();
        for (const listener of this.listeners) {
            try {
                listener(reason);
            }
            catch (e) {
                // Suppress listener errors during emergency shutdown
            }
        }
    }
    reset() {
        this.isStopped = false;
        this.stopReason = '';
        this.stopTimestamp = 0;
    }
    check() {
        return this.isStopped;
    }
    getReason() {
        return this.stopReason;
    }
    onEmergencyStop(listener) {
        this.listeners.add(listener);
        return () => this.listeners.delete(listener);
    }
}
exports.EmergencyStop = EmergencyStop;
