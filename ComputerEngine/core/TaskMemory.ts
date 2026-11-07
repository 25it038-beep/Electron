/**
 * Persistent task memory and interaction workflow cache.
 * Learns successful action sequences, UI patterns, and recovery paths.
 */

import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import { TaskPlan, WorkflowPattern } from '../types/TaskTypes';

export class TaskMemory {
  private storagePath: string;
  private workflows: Map<string, WorkflowPattern> = new Map();

  constructor(customPath?: string) {
    const dir = customPath || path.join(os.homedir(), '.electorn');
    if (!fs.existsSync(dir)) {
      try { fs.mkdirSync(dir, { recursive: true }); } catch (e) {}
    }
    this.storagePath = path.join(dir, 'hace_task_memory.json');
    this.load();
  }

  /**
   * Remember a successfully completed task plan.
   */
  public rememberPlan(plan: TaskPlan): void {
    if (plan.status !== 'completed' || plan.steps.length === 0) return;

    const patternId = `wf_${plan.goal.toLowerCase().replace(/[^a-z0-9]+/g, '_')}`;
    const existing = this.workflows.get(patternId);

    const pattern: WorkflowPattern = {
      workflowId: patternId,
      triggerPhrase: plan.originalInstruction,
      targetApp: plan.targetApplication || 'Desktop',
      steps: plan.steps.map(s => ({
        category: s.action.category,
        type: s.action.type,
        targetPattern: s.action.target,
        parameters: {
          url: s.action.url,
          text: s.action.text,
          keys: s.action.keys,
        },
      })),
      successCount: (existing?.successCount || 0) + 1,
      lastExecuted: Date.now(),
    };

    this.workflows.set(patternId, pattern);
    this.save();
  }

  /**
   * Find a previously learned matching workflow for an instruction.
   */
  public findMatchingWorkflow(instruction: string): WorkflowPattern | null {
    const lower = instruction.toLowerCase().trim();
    for (const wf of this.workflows.values()) {
      if (wf.triggerPhrase.toLowerCase() === lower || lower.includes(wf.triggerPhrase.toLowerCase())) {
        return wf;
      }
    }
    return null;
  }

  public getAllWorkflows(): WorkflowPattern[] {
    return Array.from(this.workflows.values());
  }

  private load(): void {
    try {
      if (fs.existsSync(this.storagePath)) {
        const raw = fs.readFileSync(this.storagePath, 'utf-8');
        const data = JSON.parse(raw);
        for (const it of data) {
          this.workflows.set(it.workflowId, it);
        }
      }
    } catch (e) {
      // Ignore load error
    }
  }

  private save(): void {
    try {
      const arr = Array.from(this.workflows.values());
      fs.writeFileSync(this.storagePath, JSON.stringify(arr, null, 2), 'utf-8');
    } catch (e) {
      // Ignore write error
    }
  }
}
