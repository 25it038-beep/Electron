/**
 * Aria Interaction Reasoner
 * Determines the logical sequence of operations to achieve a user goal based on screen observations.
 */

import { ParsedComputerIntent } from './IntentUnderstanding';
import { ScreenState } from '../vision/LiveScreenAnalyzer';
import { UIElement } from '../vision/UIElementDetector';

export interface PlannedStep {
  id: string;
  category: 'mouse' | 'keyboard' | 'window' | 'browser' | 'system';
  action: string;
  parameters: Record<string, any>;
  expectedOutcome: string;
}

export class InteractionReasoner {
  public reasonNextSteps(
    intent: ParsedComputerIntent,
    screen: ScreenState,
    elements: UIElement[]
  ): PlannedStep[] {
    const steps: PlannedStep[] = [];

    switch (intent.intentType) {
      case 'open_app':
        steps.push({
          id: 'step_open_app',
          category: 'window',
          action: 'launch_app',
          parameters: { app: intent.targetApp },
          expectedOutcome: `Application '${intent.targetApp}' is launched and active.`,
        });
        break;

      case 'browser_search':
        steps.push({
          id: 'step_launch_browser',
          category: 'window',
          action: 'launch_app',
          parameters: { app: 'chrome' },
          expectedOutcome: 'Browser is focused.',
        });
        steps.push({
          id: 'step_search_query',
          category: 'browser',
          action: 'search',
          parameters: { query: intent.query || 'latest news' },
          expectedOutcome: 'Search results page is loaded.',
        });
        break;

      case 'click_element':
        steps.push({
          id: 'step_click',
          category: 'mouse',
          action: 'click',
          parameters: { target: intent.targetElement },
          expectedOutcome: `Element '${intent.targetElement}' is activated.`,
        });
        break;

      case 'type_text':
        steps.push({
          id: 'step_type',
          category: 'keyboard',
          action: 'type_text',
          parameters: { text: intent.textToType },
          expectedOutcome: `Text entered into active field.`,
        });
        break;

      default:
        steps.push({
          id: 'step_general',
          category: 'system',
          action: 'execute_workflow',
          parameters: { instruction: intent.rawInput },
          expectedOutcome: 'Operation completed.',
        });
        break;
    }

    return steps;
  }
}
