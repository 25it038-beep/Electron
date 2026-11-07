/**
 * Aria Workflow Memory
 */

export interface WorkflowPattern {
  id: string;
  name: string;
  instructionPattern: string;
  stepCount: number;
  successCount: number;
  lastUsedTimestamp: number;
}

export class WorkflowMemory {
  private workflows: Map<string, WorkflowPattern> = new Map();

  public rememberWorkflow(name: string, instructionPattern: string, stepCount: number): void {
    const key = instructionPattern.toLowerCase();
    const existing = this.workflows.get(key);
    if (existing) {
      existing.successCount += 1;
      existing.lastUsedTimestamp = Date.now();
    } else {
      this.workflows.set(key, {
        id: `wf_${Date.now()}`,
        name,
        instructionPattern,
        stepCount,
        successCount: 1,
        lastUsedTimestamp: Date.now(),
      });
    }
  }

  public findWorkflow(instruction: string): WorkflowPattern | null {
    const clean = instruction.toLowerCase();
    return this.workflows.get(clean) || null;
  }
}
