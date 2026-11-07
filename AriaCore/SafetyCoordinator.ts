/**
 * Aria Safety Coordinator: Enforces strict user controls, emergency stops, and action approvals.
 */

import { EmergencyStop } from '../ComputerEngine/safety/EmergencyStop';
import { PermissionManager } from '../ComputerEngine/safety/PermissionManager';
import { ActionApproval } from '../ComputerEngine/safety/ActionApproval';

export class SafetyCoordinator {
  public readonly emergencyStop = EmergencyStop.getInstance();
  public readonly permissions = new PermissionManager(true);
  public readonly approval = new ActionApproval();

  /**
   * Instantly halt all active computer actions, tasks, and speech playback.
   */
  public triggerEmergencyStop(reason: string = 'User triggered emergency stop'): void {
    this.emergencyStop.trigger(reason);
  }

  public resetEmergencyStop(): void {
    this.emergencyStop.reset();
  }

  public isEmergencyStopped(): boolean {
    return this.emergencyStop.check();
  }
}
