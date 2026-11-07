/**
 * Task planning, step state, and lifecycle definitions.
 */

import { ActionPayload, ActionResult } from './ActionTypes';

export type TaskStatus =
  | 'idle'
  | 'planned'
  | 'planning'
  | 'in_progress'
  | 'waiting_approval'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface TaskStep {
  stepId: string;
  order: number;
  description: string;
  action: ActionPayload;
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'skipped';
  expectedOutcome: string;
  verificationEvidence?: string;
  result?: ActionResult;
  retryCount: number;
  error?: string;
}

export interface TaskPlan {
  taskId: string;
  originalInstruction: string;
  goal: string;
  targetApplication?: string;
  steps: TaskStep[];
  currentStepIndex: number;
  status: TaskStatus;
  startTime: number;
  endTime?: number;
  error?: string;
  summary?: string;
}

export interface WorkflowPattern {
  workflowId: string;
  triggerPhrase: string;
  targetApp: string;
  steps: Array<{
    category: string;
    type: string;
    targetPattern?: string;
    parameters: Record<string, unknown>;
  }>;
  successCount: number;
  lastExecuted: number;
}
