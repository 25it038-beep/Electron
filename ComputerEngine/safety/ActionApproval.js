"use strict";
/**
 * Action approval manager requesting explicit user confirmation before consequential actions.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.ActionApproval = void 0;
class ActionApproval {
    pendingRequests = new Map();
    approvalHandler;
    setApprovalHandler(handler) {
        this.approvalHandler = handler;
    }
    async requestApproval(action, reason, timeoutMs = 30000) {
        const requestId = `req_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
        const request = {
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
            }
            catch (err) {
                request.status = 'denied';
                this.pendingRequests.delete(requestId);
                return false;
            }
        }
        // Default: require explicit approval, don't execute automatically without handler
        return false;
    }
    getPendingRequests() {
        return Array.from(this.pendingRequests.values());
    }
    resolveRequest(requestId, approved) {
        const req = this.pendingRequests.get(requestId);
        if (!req)
            return false;
        req.status = approved ? 'approved' : 'denied';
        this.pendingRequests.delete(requestId);
        return true;
    }
}
exports.ActionApproval = ActionApproval;
