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
export declare class ActionApproval {
    private pendingRequests;
    private approvalHandler?;
    setApprovalHandler(handler: ApprovalHandler): void;
    requestApproval(action: ActionPayload, reason: string, timeoutMs?: number): Promise<boolean>;
    getPendingRequests(): ApprovalRequest[];
    resolveRequest(requestId: string, approved: boolean): boolean;
}
