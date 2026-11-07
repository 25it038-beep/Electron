/**
 * Aria Computer Approval Manager
 * Manages user confirmation dialogs and approvals for consequential actions.
 */

export interface PendingApproval {
  approvalId: string;
  actionDescription: string;
  riskLevel: string;
  timestamp: number;
  status: 'pending' | 'approved' | 'rejected';
}

export class ApprovalManager {
  private pendingApprovals: Map<string, PendingApproval> = new Map();

  public requestApproval(actionDescription: string, riskLevel: string = 'high'): string {
    const approvalId = `appr_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;
    this.pendingApprovals.set(approvalId, {
      approvalId,
      actionDescription,
      riskLevel,
      timestamp: Date.now(),
      status: 'pending',
    });
    return approvalId;
  }

  public approve(approvalId: string): boolean {
    const item = this.pendingApprovals.get(approvalId);
    if (item && item.status === 'pending') {
      item.status = 'approved';
      return true;
    }
    return false;
  }

  public reject(approvalId: string): boolean {
    const item = this.pendingApprovals.get(approvalId);
    if (item && item.status === 'pending') {
      item.status = 'rejected';
      return true;
    }
    return false;
  }

  public getStatus(approvalId: string): 'pending' | 'approved' | 'rejected' | 'unknown' {
    const item = this.pendingApprovals.get(approvalId);
    return item ? item.status : 'unknown';
  }
}
