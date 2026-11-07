/**
 * Aria Human Interaction Engine
 * Executes the continuous observe-act-verify loop with proactive error recovery.
 */

import { ComputerStateManager } from './ComputerStateManager';
import { IntentUnderstanding, ParsedComputerIntent } from '../intelligence/IntentUnderstanding';
import { ActionPlanner, ActionPlan } from './ActionPlanner';
import { ActionExecutor } from './ActionExecutor';
import { ActionVerifier } from './ActionVerifier';
import { RecoveryEngine } from '../intelligence/RecoveryEngine';
import { InteractionMemory, WorkflowMemory } from '../memory';
import { EmergencyStop } from '../safety/EmergencyStop';

export class HumanInteractionEngine {
  private stateManager: ComputerStateManager;
  private intentParser: IntentUnderstanding;
  private planner: ActionPlanner;
  private executor: ActionExecutor;
  private verifier: ActionVerifier;
  private recovery: RecoveryEngine;
  private interactionMemory: InteractionMemory;
  private workflowMemory: WorkflowMemory;
  private emergencyStop = EmergencyStop.getInstance();

  constructor(
    stateManager?: ComputerStateManager,
    intentParser?: IntentUnderstanding,
    planner?: ActionPlanner,
    executor?: ActionExecutor,
    verifier?: ActionVerifier,
    recovery?: RecoveryEngine,
    interactionMemory?: InteractionMemory,
    workflowMemory?: WorkflowMemory
  ) {
    this.stateManager = stateManager || new ComputerStateManager();
    this.intentParser = intentParser || new IntentUnderstanding();
    this.planner = planner || new ActionPlanner();
    this.executor = executor || new ActionExecutor();
    this.verifier = verifier || new ActionVerifier();
    this.recovery = recovery || new RecoveryEngine();
    this.interactionMemory = interactionMemory || new InteractionMemory();
    this.workflowMemory = workflowMemory || new WorkflowMemory();
  }

  /**
   * Run the full Observe -> Understand -> Reason -> Plan -> Act -> Verify -> Recover loop.
   */
  public async executeInstruction(instruction: string): Promise<ActionPlan> {
    // Check Emergency Stop
    if (this.emergencyStop.check()) {
      const intent: ParsedComputerIntent = { intentType: 'emergency_stop', rawInput: instruction };
      return {
        id: `plan_aborted`,
        originalInstruction: instruction,
        intent,
        steps: [],
        currentStepIndex: 0,
        status: 'aborted',
      };
    }

    // 1. OBSERVE
    const beforeState = this.stateManager.getAggregateState();

    // 2. UNDERSTAND
    const intent = this.intentParser.parse(instruction);
    if (intent.intentType === 'emergency_stop') {
      this.emergencyStop.trigger('User invoked emergency stop.');
      return {
        id: `plan_stopped`,
        originalInstruction: instruction,
        intent,
        steps: [],
        currentStepIndex: 0,
        status: 'aborted',
      };
    }

    // 3. PLAN
    const plan = this.planner.createPlan(intent, beforeState);
    plan.status = 'executing';

    // 4. STEP-BY-STEP ACT -> OBSERVE AGAIN -> VERIFY -> RECOVER
    for (let i = 0; i < plan.steps.length; i++) {
      if (this.emergencyStop.check()) {
        plan.status = 'aborted';
        break;
      }

      const step = plan.steps[i];
      plan.currentStepIndex = i;

      // ACT
      const execResult = await this.executor.executeStep(step);
      this.interactionMemory.log(step.action, JSON.stringify(step.parameters), execResult.success);

      if (!execResult.success) {
        // RECOVER
        const recoveryPlan = this.recovery.diagnoseAndRecover(
          step.action,
          beforeState.visibleElements,
          beforeState.activeWindow?.title || 'Unknown'
        );
        // Retry step once after recovery
        const retryResult = await this.executor.executeStep(step);
        if (!retryResult.success) {
          plan.status = 'failed';
          break;
        }
      }

      // OBSERVE AGAIN
      const afterState = this.stateManager.getAggregateState();

      // VERIFY
      const verification = this.verifier.verifyStep(step, beforeState, afterState);
      if (!verification.verified) {
        plan.status = 'failed';
        break;
      }
    }

    if (plan.status === 'executing') {
      plan.status = 'completed';
      this.workflowMemory.rememberWorkflow(instruction, instruction, plan.steps.length);
    }

    return plan;
  }
}
