/**
 * Aria Computer Action Planner
 * Translates parsed intent into ordered execution steps with expected outcomes.
 */

import { ParsedComputerIntent } from '../intelligence/IntentUnderstanding';
import { InteractionReasoner, PlannedStep } from '../intelligence/InteractionReasoner';
import { AggregateComputerState } from './ComputerStateManager';

export interface ActionPlan {
  id: string;
  originalInstruction: string;
  intent: ParsedComputerIntent;
  steps: PlannedStep[];
  currentStepIndex: number;
  status: 'planned' | 'executing' | 'completed' | 'failed' | 'aborted';
}

export class ActionPlanner {
  private reasoner: InteractionReasoner;

  constructor(reasoner?: InteractionReasoner) {
    this.reasoner = reasoner || new InteractionReasoner();
  }

  public createPlan(
    intent: ParsedComputerIntent,
    state: AggregateComputerState
  ): ActionPlan {
    const steps = this.reasoner.reasonNextSteps(
      intent,
      state.screen,
      state.visibleElements
    );

    return {
      id: `plan_${Date.now()}`,
      originalInstruction: intent.rawInput,
      intent,
      steps,
      currentStepIndex: 0,
      status: 'planned',
    };
  }
}
