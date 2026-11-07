/**
 * Action approval manager requesting explicit user confirmation before consequential actions.
 */

import { ActionPayload } from '../types/ActionTypes';

export interface ApprovalRequest {
  requestId: string;
  action: ActionPayload;
  reason: string;
  timestamp: number;
  timeoutMs: number;
  status: 'pending' | 'approved' | 'denied' | 'timeout';
}

export type ApprovalHandler = (request: ApprovalRequest) => Promise<boolean>;

export class ActionApproval {
  private pendingRequests: Map<string, ApprovalRequest> = new Map();
  private approvalHandler?: ApprovalHandler;

  public setApprovalHandler(handler: ApprovalHandler): void {
    this.approvalHandler = handler;
  }

  public async requestApproval(action: ActionPayload, reason: string, timeoutMs: number = 30000): Promise<boolean> {
    const requestId = `req_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
    const request: ApprovalRequest = {
      requestId,
      action,
      reason,
      timestamp: Date.now(),
      timeoutMs,
      status: 'pending',
    };

    this.pendingRequests.set(requestId, request);

    if (this.approvalHandler) {
      try {
        const approved = await this.approvalHandler(request);
        request.status = approved ? 'approved' : 'denied';
        this.pendingRequests.delete(requestId);
        return approved;
      } catch (err) {
        request.status = 'denied';
        this.pendingRequests.delete(requestId);
        return false;
      }
    }

    // Default: require explicit approval, don't execute automatically without handler
    return false;
  }

  public getPendingRequests(): ApprovalRequest[] {
    return Array.from(this.pendingRequests.values());
  }

  public resolveRequest(requestId: string, approved: boolean): boolean {
    const req = this.pendingRequests.get(requestId);
    if (!req) return false;
    req.status = approved ? 'approved' : 'denied';
    this.pendingRequests.delete(requestId);
    return true;
  }
}
