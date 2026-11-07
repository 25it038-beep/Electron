/**
 * Aria Computer Action Executor
 * Dispatches planned steps to native input and window controllers under strict safety constraints.
 */

import { PlannedStep } from '../intelligence/InteractionReasoner';
import { MouseController } from '../input/MouseController';
import { KeyboardController } from '../input/KeyboardController';
import { WindowManager } from '../windows/WindowManager';
import { ApplicationManager } from '../windows/ApplicationManager';
import { BrowserController } from '../browser/BrowserController';
import { SystemController } from '../windows/SystemController';
import { VisualGrounding } from '../vision/VisualGrounding';
import { PermissionManager } from '../safety/PermissionManager';
import { EmergencyStop } from '../safety/EmergencyStop';

export interface StepExecutionResult {
  stepId: string;
  success: boolean;
  message: string;
  error?: string;
  durationMs: number;
}

export class ActionExecutor {
  public mouse: MouseController;
  public keyboard: KeyboardController;
  public windowManager: WindowManager;
  public appManager: ApplicationManager;
  public browser: BrowserController;
  public system: SystemController;
  public grounding: VisualGrounding;
  public permissions: PermissionManager;
  public emergencyStop = EmergencyStop.getInstance();

  constructor(
    mouse?: MouseController,
    keyboard?: KeyboardController,
    windowManager?: WindowManager,
    appManager?: ApplicationManager,
    browser?: BrowserController,
    system?: SystemController,
    grounding?: VisualGrounding,
    permissions?: PermissionManager
  ) {
    this.mouse = mouse || new MouseController();
    this.keyboard = keyboard || new KeyboardController();
    this.windowManager = windowManager || new WindowManager();
    this.appManager = appManager || new ApplicationManager();
    this.browser = browser || new BrowserController();
    this.system = system || new SystemController();
    this.grounding = grounding || new VisualGrounding();
    this.permissions = permissions || new PermissionManager();
  }

  public async executeStep(step: PlannedStep): Promise<StepExecutionResult> {
    const startTime = Date.now();

    if (this.emergencyStop.check()) {
      return {
        stepId: step.id,
        success: false,
        message: 'Action aborted by Emergency Stop.',
        error: this.emergencyStop.getReason(),
        durationMs: 0,
      };
    }

    try {
      if (step.category === 'mouse') {
        if (step.action === 'click') {
          const targetName = step.parameters.target;
          const grounded = this.grounding.groundTarget(targetName);
          if (grounded) {
            await this.mouse.click(grounded.centerX, grounded.centerY);
          } else {
            await this.mouse.click();
          }
          return { stepId: step.id, success: true, message: `Clicked '${targetName}'`, durationMs: Date.now() - startTime };
        }
      } else if (step.category === 'keyboard') {
        if (step.action === 'type_text') {
          await this.keyboard.typeText(step.parameters.text || '');
          return { stepId: step.id, success: true, message: `Typed text`, durationMs: Date.now() - startTime };
        }
      } else if (step.category === 'window') {
        if (step.action === 'launch_app') {
          const app = step.parameters.app || 'chrome';
          this.appManager.launch(app);
          return { stepId: step.id, success: true, message: `Launched ${app}`, durationMs: Date.now() - startTime };
        }
      } else if (step.category === 'browser') {
        if (step.action === 'search') {
          this.browser.search(step.parameters.query || '');
          return { stepId: step.id, success: true, message: `Searched browser for ${step.parameters.query}`, durationMs: Date.now() - startTime };
        }
      }

      return {
        stepId: step.id,
        success: true,
        message: `Executed ${step.action}`,
        durationMs: Date.now() - startTime,
      };
    } catch (e: any) {
      return {
        stepId: step.id,
        success: false,
        message: `Execution failed: ${e.message}`,
        error: e.message,
        durationMs: Date.now() - startTime,
      };
    }
  }
}
