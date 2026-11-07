/**
 * HS Autonomous Computer Engine (HACE)
 * Main exports for TypeScript / Electron integration.
 */

export * from './types';
export { PermissionManager, ActionApproval, EmergencyStop, ActionValidator as SafetyActionValidator } from './safety';
export * from './controllers';
export * from './perception';
export * from './browser';
export * from './core';

import { ComputerEngine } from './core/ComputerEngine';
export default ComputerEngine;

