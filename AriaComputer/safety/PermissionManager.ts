/**
 * Aria Computer Permission Manager
 * Enforces security gates, risk levels, and protected system operations.
 */

export type RiskLevel = 'safe' | 'low' | 'medium' | 'high' | 'critical' | 'blocked';

export interface ActionSecurityPolicy {
  category: string;
  actionType: string;
  riskLevel: RiskLevel;
  requiresExplicitConfirmation: boolean;
}

export class PermissionManager {
  private computerControlEnabled: boolean = true;
  private policies: Map<string, ActionSecurityPolicy> = new Map();

  constructor() {
    this.initDefaultPolicies();
  }

  private initDefaultPolicies(): void {
    // Critical / Consequential operations
    this.registerPolicy('system', 'delete_file', 'high', true);
    this.registerPolicy('system', 'format_drive', 'blocked', true);
    this.registerPolicy('system', 'install_software', 'high', true);
    this.registerPolicy('system', 'uninstall_software', 'high', true);
    this.registerPolicy('browser', 'financial_checkout', 'critical', true);
    this.registerPolicy('system', 'change_security_settings', 'critical', true);
    this.registerPolicy('system', 'send_email', 'high', true);
    this.registerPolicy('system', 'send_message', 'high', true);

    // Safe human interactions
    this.registerPolicy('mouse', 'click', 'safe', false);
    this.registerPolicy('mouse', 'double_click', 'safe', false);
    this.registerPolicy('mouse', 'right_click', 'safe', false);
    this.registerPolicy('mouse', 'move', 'safe', false);
    this.registerPolicy('mouse', 'scroll', 'safe', false);
    this.registerPolicy('mouse', 'drag_and_drop', 'low', false);
    this.registerPolicy('keyboard', 'type_text', 'safe', false);
    this.registerPolicy('keyboard', 'shortcut', 'safe', false);
    this.registerPolicy('window', 'launch_app', 'low', false);
    this.registerPolicy('window', 'focus_window', 'safe', false);
    this.registerPolicy('window', 'minimize_window', 'safe', false);
    this.registerPolicy('window', 'maximize_window', 'safe', false);
    this.registerPolicy('browser', 'open_url', 'safe', false);
    this.registerPolicy('browser', 'search', 'safe', false);
  }

  public registerPolicy(
    category: string,
    actionType: string,
    riskLevel: RiskLevel,
    requiresExplicitConfirmation: boolean
  ): void {
    this.policies.set(`${category}:${actionType}`, {
      category,
      actionType,
      riskLevel,
      requiresExplicitConfirmation,
    });
  }

  public evaluateRisk(category: string, actionType: string): RiskLevel {
    const policy = this.policies.get(`${category}:${actionType}`);
    return policy ? policy.riskLevel : 'low';
  }

  public requiresConfirmation(category: string, actionType: string): boolean {
    const policy = this.policies.get(`${category}:${actionType}`);
    return policy ? policy.requiresExplicitConfirmation : false;
  }

  public isComputerControlEnabled(): boolean {
    return this.computerControlEnabled;
  }

  public setComputerControlEnabled(enabled: boolean): void {
    this.computerControlEnabled = enabled;
  }
}
