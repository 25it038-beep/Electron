/**
 * Task Manager: Executes and monitors autonomous computer tasks with verification and auto-recovery.
 */

import { TaskPlan, TaskStep, TaskStatus } from '../types/TaskTypes';
import { ComputerState } from '../types/ComputerState';
import { ActionPlanner } from './ActionPlanner';
import { ActionExecutor } from './ActionExecutor';
import { ActionValidator } from './ActionValidator';
import { ScreenAnalyzer } from '../perception/ScreenAnalyzer';
import { TaskMemory } from './TaskMemory';
import { EmergencyStop } from '../safety/EmergencyStop';

export type TaskListener = (plan: TaskPlan, currentStep?: TaskStep) => void;

export class TaskManager {
  private planner: ActionPlanner;
  private executor: ActionExecutor;
  private validator: ActionValidator;
  private analyzer: ScreenAnalyzer;
  private memory: TaskMemory;
  private emergencyStop = EmergencyStop.getInstance();

  private activePlan?: TaskPlan;
  private isPaused: boolean = false;
  private listeners: Set<TaskListener> = new Set();

  constructor(
    planner?: ActionPlanner,
    executor?: ActionExecutor,
    validator?: ActionValidator,
    analyzer?: ScreenAnalyzer,
    memory?: TaskMemory
  ) {
    this.planner = planner || new ActionPlanner();
    this.executor = executor || new ActionExecutor();
    this.validator = validator || new ActionValidator();
    this.analyzer = analyzer || new ScreenAnalyzer();
    this.memory = memory || new TaskMemory();
  }

  public onTaskUpdate(listener: TaskListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private notify(plan: TaskPlan, step?: TaskStep): void {
    for (const l of this.listeners) {
      try { l(plan, step); } catch (e) {}
    }
  }

  /**
   * Execute an instruction from end to end.
   */
  public async executeInstruction(instruction: string): Promise<TaskPlan> {
    this.emergencyStop.reset();
    this.isPaused = false;

    // 1. Observe pre-state
    const preState = await this.analyzer.analyzeState(false);

    // 2. Plan task
    const plan = this.planner.planInstruction(instruction, preState);
    this.activePlan = plan;
    plan.status = 'in_progress';
    this.notify(plan);

    // 3. Sequential Step Execution Loop
    for (let i = 0; i < plan.steps.length; i++) {
      plan.currentStepIndex = i;
      const step = plan.steps[i];

      // Handle pause
      while (this.isPaused && !this.emergencyStop.check()) {
        await new Promise(r => setTimeout(r, 200));
      }

      // Handle emergency stop
      if (this.emergencyStop.check()) {
        step.status = 'failed';
        step.error = this.emergencyStop.getReason();
        plan.status = 'cancelled';
        plan.error = 'Emergency Stop triggered.';
        this.notify(plan, step);
        break;
      }

      step.status = 'in_progress';
      this.notify(plan, step);

      const beforeState = await this.analyzer.analyzeState(false);

      // Execute with auto-recovery retry (up to 2 retries)
      let execResult = await this.executor.execute(step.action);

      if (!execResult.success && step.retryCount < 2) {
        step.retryCount++;
        // Recovery: short delay and re-evaluate
        await new Promise(r => setTimeout(r, 500));
        execResult = await this.executor.execute(step.action);
      }

      step.result = execResult;

      // Observe post-action state
      const afterState = await this.analyzer.analyzeState(false);

      // Verify step outcome
      const verifyResult = this.validator.verifyStepOutcome(step, beforeState, afterState);
      step.verificationEvidence = verifyResult.evidence;

      if (execResult.success) {
        step.status = 'completed';
      } else {
        step.status = 'failed';
        step.error = execResult.error || 'Step failed execution';
        plan.status = 'failed';
        plan.error = step.error;
        this.notify(plan, step);
        break;
      }

      this.notify(plan, step);
      await new Promise(r => setTimeout(r, 150));
    }

    if (plan.status === 'in_progress') {
      plan.status = 'completed';
      plan.endTime = Date.now();
      plan.summary = `Successfully executed all ${plan.steps.length} steps for: '${instruction}'`;
      this.memory.rememberPlan(plan);
    }

    this.notify(plan);
    return plan;
  }

  public pause(): void {
    this.isPaused = true;
    if (this.activePlan) {
      this.activePlan.status = 'paused';
      this.notify(this.activePlan);
    }
  }

  public resume(): void {
    this.isPaused = false;
    if (this.activePlan && this.activePlan.status === 'paused') {
      this.activePlan.status = 'in_progress';
      this.notify(this.activePlan);
    }
  }

  public stop(reason: string = 'User stopped task'): void {
    this.emergencyStop.trigger(reason);
    if (this.activePlan) {
      this.activePlan.status = 'cancelled';
      this.activePlan.error = reason;
      this.notify(this.activePlan);
    }
  }

  public getActivePlan(): TaskPlan | undefined {
    return this.activePlan;
  }
}
