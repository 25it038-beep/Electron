/**
 * Aria Recovery Engine
 * Detects roadblocks, unexpected dialogs (confirmation prompts, error dialogs, UAC),
 * failed clicks, and window movements, and generates recovery tactics.
 */

import { UIElement } from '../vision/UIElementDetector';

export interface RecoveryPlan {
  cause: string;
  strategy: 'dismiss_dialog' | 'retry_with_regrounding' | 're_focus_window' | 'escalate_to_user';
  actionStep?: string;
}

export class RecoveryEngine {
  public diagnoseAndRecover(
    failedAction: string,
    currentElements: UIElement[],
    activeWindowTitle: string
  ): RecoveryPlan {
    // 1. Check for modal dialogs blocking interaction
    const dialogElement = currentElements.find(
      (el) =>
        el.type === 'dialog' ||
        el.label.toLowerCase().includes('confirm') ||
        el.label.toLowerCase().includes('save changes') ||
        el.label.toLowerCase().includes('alert')
    );

    if (dialogElement) {
      return {
        cause: `Blocked by dialog: '${dialogElement.label}'`,
        strategy: 'dismiss_dialog',
        actionStep: 'Click OK or Dismiss on dialog',
      };
    }

    // 2. Check for click target miss / moved window
    if (failedAction.includes('click')) {
      return {
        cause: 'Target element coordinate may have moved or changed scale.',
        strategy: 'retry_with_regrounding',
        actionStep: 'Re-analyze visual grounding and re-attempt click',
      };
    }

    return {
      cause: 'Action failed postcondition verification.',
      strategy: 're_focus_window',
      actionStep: `Re-focus '${activeWindowTitle}' and retry.`,
    };
  }
}
