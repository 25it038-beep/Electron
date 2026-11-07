/**
 * Permission classification and risk evaluation for desktop automation.
 */
import { ActionPayload, RiskLevel } from '../types/ActionTypes';
export declare class PermissionManager {
    private allowedCategories;
    private autoApproveLowRisk;
    private blockedPatterns;
    constructor(autoApproveLowRisk?: boolean);
    evaluateRisk(action: ActionPayload): RiskLevel;
    isActionPermitted(action: ActionPayload): boolean;
}
