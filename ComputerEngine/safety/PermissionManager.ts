/**
 * Permission classification and risk evaluation for desktop automation.
 */

import { ActionPayload, RiskLevel } from '../types/ActionTypes';

export class PermissionManager {
  private allowedCategories: Set<string> = new Set(['mouse', 'keyboard', 'window', 'browser', 'system']);
  private autoApproveLowRisk: boolean = true;
  private blockedPatterns: RegExp[] = [
    /format\s+[a-z]:/i,
    /rmdir\s+\/s\s+\/q\s+c:\\/i,
    /reg\s+delete/i,
    /drop\s+database/i,
  ];

  constructor(autoApproveLowRisk: boolean = true) {
    this.autoApproveLowRisk = autoApproveLowRisk;
  }

  public evaluateRisk(action: ActionPayload): RiskLevel {
    // 1. Check blocked critical threats
    if (action.text) {
      for (const pattern of this.blockedPatterns) {
        if (pattern.test(action.text)) {
          return 'blocked';
        }
      }
    }

    // 2. High-risk actions that require user confirmation
    if (
      action.type === 'delete_file' ||
      action.type === 'purchase' ||
      action.type === 'send_email' ||
      action.type === 'submit_payment' ||
      (action.text && /(sudo|rm -rf|del \/f|format)/i.test(action.text))
    ) {
      return 'high_risk_confirm';
    }

    // 3. Normal safe interactions
    if (
      action.category === 'mouse' ||
      action.category === 'keyboard' ||
      action.category === 'browser' ||
      action.category === 'window'
    ) {
      return this.autoApproveLowRisk ? 'safe' : 'low_risk';
    }

    return 'low_risk';
  }

  public isActionPermitted(action: ActionPayload): boolean {
    const risk = this.evaluateRisk(action);
    return risk !== 'blocked';
  }
}
