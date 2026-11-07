/**
 * Aria Action Coordinator: Dispatches physical operations to ComputerEngine and records action memory.
 */

import { ComputerEngine } from '../ComputerEngine';
import { MemoryCoordinator } from './MemoryCoordinator';

export class ActionCoordinator {
  private engine: ComputerEngine;
  private memory: MemoryCoordinator;

  constructor(engine?: ComputerEngine, memory?: MemoryCoordinator) {
    this.engine = engine || new ComputerEngine();
    this.memory = memory || new MemoryCoordinator();
  }

  public async executeDesktopTask(instruction: string): Promise<string> {
    const plan = await this.engine.executeInstruction(instruction);
    const summary = plan.summary || `Executed ${plan.steps.length} steps for: ${instruction}`;

    this.memory.store(
      'computer_action',
      `action_${Date.now()}`,
      summary,
      { taskId: plan.taskId, steps: plan.steps.length, status: plan.status }
    );

    return summary;
  }

  public async click(x?: number, y?: number): Promise<void> {
    await this.engine.click(x, y);
    this.memory.store('computer_action', 'mouse_click', `Clicked at [${x ?? 'current'}, ${y ?? 'current'}]`);
  }

  public async typeText(text: string): Promise<void> {
    await this.engine.typeText(text);
    this.memory.store('computer_action', 'keyboard_type', `Typed: '${text.substring(0, 30)}...'`);
  }

  public stop(reason: string = 'User stopped actions'): void {
    this.engine.stop(reason);
  }

  public pause(): void {
    this.engine.pause();
  }

  public resume(): void {
    this.engine.resume();
  }
}
