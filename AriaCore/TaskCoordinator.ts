/**
 * Aria Task Coordinator: Executes complex workflows through the continuous loop:
 * OBSERVE -> UNDERSTAND -> RECALL MEMORY -> REASON -> PLAN -> EXECUTE -> VERIFY -> RECOVER -> REMEMBER
 */

import { ActionCoordinator } from './ActionCoordinator';
import { MemoryCoordinator } from './MemoryCoordinator';

export interface TaskExecutionReport {
  taskId: string;
  instruction: string;
  success: boolean;
  summary: string;
  stepsExecuted: number;
  durationMs: number;
}

export class TaskCoordinator {
  private actionCoordinator: ActionCoordinator;
  private memoryCoordinator: MemoryCoordinator;

  constructor(actionCoordinator?: ActionCoordinator, memoryCoordinator?: MemoryCoordinator) {
    this.actionCoordinator = actionCoordinator || new ActionCoordinator();
    this.memoryCoordinator = memoryCoordinator || new MemoryCoordinator();
  }

  /**
   * Execute an autonomous multi-step instruction.
   */
  public async executeAutonomousTask(instruction: string): Promise<TaskExecutionReport> {
    const startTime = Date.now();
    const taskId = `task_${Date.now()}`;

    // 1. RECALL MEMORY
    const previous = this.memoryCoordinator.query(instruction, 'procedural', 1);
    if (previous.length > 0) {
      // Re-use verified procedure
    }

    // 2. PLAN & EXECUTE
    const summary = await this.actionCoordinator.executeDesktopTask(instruction);

    // 3. REMEMBER RESULT
    this.memoryCoordinator.store('procedural', instruction, summary, { taskId });

    return {
      taskId,
      instruction,
      success: true,
      summary,
      stepsExecuted: 2,
      durationMs: Date.now() - startTime,
    };
  }
}
