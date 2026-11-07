/**
 * Action Executor: Dispatches validated actions to physical controllers with safety gates.
 */

import { ActionPayload, ActionResult } from '../types/ActionTypes';
import { MouseController } from '../controllers/MouseController';
import { KeyboardController } from '../controllers/KeyboardController';
import { WindowController } from '../controllers/WindowController';
import { BrowserController } from '../browser/BrowserController';
import { PermissionManager } from '../safety/PermissionManager';
import { ActionApproval } from '../safety/ActionApproval';
import { EmergencyStop } from '../safety/EmergencyStop';
import { VisualGrounding } from '../perception/VisualGrounding';
import { ScreenAnalyzer } from '../perception/ScreenAnalyzer';

export class ActionExecutor {
  private mouse: MouseController;
  private keyboard: KeyboardController;
  private window: WindowController;
  private browser: BrowserController;
  private permission: PermissionManager;
  private approval: ActionApproval;
  private emergencyStop = EmergencyStop.getInstance();
  private grounding: VisualGrounding;
  private analyzer: ScreenAnalyzer;

  constructor(
    mouse?: MouseController,
    keyboard?: KeyboardController,
    window?: WindowController,
    browser?: BrowserController,
    permission?: PermissionManager,
    approval?: ActionApproval,
    grounding?: VisualGrounding,
    analyzer?: ScreenAnalyzer
  ) {
    this.mouse = mouse || new MouseController();
    this.keyboard = keyboard || new KeyboardController();
    this.window = window || new WindowController();
    this.browser = browser || new BrowserController();
    this.permission = permission || new PermissionManager();
    this.approval = approval || new ActionApproval();
    this.grounding = grounding || new VisualGrounding();
    this.analyzer = analyzer || new ScreenAnalyzer();
  }

  /**
   * Execute a single action on the real operating system.
   */
  public async execute(action: ActionPayload): Promise<ActionResult> {
    const startTime = Date.now();

    // 1. Check Emergency Stop
    if (this.emergencyStop.check()) {
      return {
        actionId: action.actionId,
        success: false,
        message: 'Action aborted by Emergency Stop.',
        error: this.emergencyStop.getReason(),
        durationMs: 0,
      };
    }

    // 2. Permission and Risk Gate
    const risk = this.permission.evaluateRisk(action);
    if (risk === 'blocked') {
      return {
        actionId: action.actionId,
        success: false,
        message: `Action '${action.description}' is blocked for safety.`,
        error: 'Security Policy Violation',
        durationMs: Date.now() - startTime,
      };
    }

    if (risk === 'high_risk_confirm' || action.requiresConfirmation) {
      const approved = await this.approval.requestApproval(action, `Action requires confirmation: ${action.description}`);
      if (!approved) {
        return {
          actionId: action.actionId,
          success: false,
          message: 'Action was denied by the user.',
          error: 'User Denied',
          durationMs: Date.now() - startTime,
        };
      }
    }

    // 3. Dispatch to Controller
    try {
      let message = '';

      // MOUSE ACTIONS
      if (action.category === 'mouse') {
        let targetCoords = action.coordinates;

        // If target label given without fixed coordinates, use Visual Grounding!
        if (!targetCoords && action.target) {
          const state = await this.analyzer.analyzeState(false);
          const grounded = this.grounding.resolveTarget(action.target, state);
          if (grounded) {
            targetCoords = grounded.coordinates;
          }
        }

        if (action.type === 'move_cursor' && targetCoords) {
          await this.mouse.smoothMove(targetCoords[0], targetCoords[1]);
          message = `Moved cursor to [${targetCoords[0]}, ${targetCoords[1]}].`;
        } else if (action.type === 'click') {
          if (targetCoords) {
            await this.mouse.click(targetCoords[0], targetCoords[1]);
            message = `Clicked at [${targetCoords[0]}, ${targetCoords[1]}].`;
          } else {
            await this.mouse.click();
            message = 'Clicked current mouse position.';
          }
        } else if (action.type === 'right_click') {
          await this.mouse.rightClick(targetCoords?.[0], targetCoords?.[1]);
          message = 'Right-clicked at location.';
        } else if (action.type === 'double_click') {
          await this.mouse.doubleClick(targetCoords?.[0], targetCoords?.[1]);
          message = 'Double-clicked at location.';
        } else if (action.type === 'drag_and_drop' && targetCoords && action.endCoordinates) {
          await this.mouse.dragAndDrop(targetCoords[0], targetCoords[1], action.endCoordinates[0], action.endCoordinates[1]);
          message = `Dragged from [${targetCoords}] to [${action.endCoordinates}].`;
        } else if (action.type === 'scroll') {
          await this.mouse.scroll(action.deltaY ?? 5, action.deltaX ?? 0);
          message = `Scrolled deltaY=${action.deltaY ?? 5}.`;
        }
      }

      // KEYBOARD ACTIONS
      else if (action.category === 'keyboard') {
        if (action.type === 'type_text' && action.text) {
          await this.keyboard.typeText(action.text);
          message = `Typed text into active control.`;
        } else if (action.type === 'press_key' && action.keys?.[0]) {
          await this.keyboard.pressKey(action.keys[0]);
          message = `Pressed key '${action.keys[0]}'.`;
        } else if (action.type === 'shortcut' && action.keys) {
          await this.keyboard.pressShortcut(action.keys);
          message = `Pressed shortcut '${action.keys.join('+')}'.`;
        } else if (action.type === 'select_all') {
          await this.keyboard.selectAll();
          message = 'Selected all.';
        } else if (action.type === 'copy') {
          await this.keyboard.copy();
          message = 'Copied to clipboard.';
        } else if (action.type === 'paste') {
          await this.keyboard.paste();
          message = 'Pasted from clipboard.';
        } else if (action.type === 'undo') {
          await this.keyboard.undo();
          message = 'Undo performed.';
        } else if (action.type === 'redo') {
          await this.keyboard.redo();
          message = 'Redo performed.';
        }
      }

      // WINDOW ACTIONS
      else if (action.category === 'window') {
        if (action.type === 'launch_app' && action.target) {
          const success = this.window.launchApp(action.target);
          message = success ? `Launched ${action.target}.` : `Failed to launch ${action.target}.`;
        } else if (action.type === 'close_app' && action.target) {
          const success = this.window.closeApp(action.target);
          message = success ? `Closed ${action.target}.` : `Could not close ${action.target}.`;
        } else if (action.type === 'focus_window' && action.target) {
          this.window.focusWindow(action.target);
          message = `Focused window '${action.target}'.`;
        } else if (action.type === 'minimize_window') {
          this.window.minimizeAll();
          message = 'Minimized windows.';
        } else if (action.type === 'maximize_window') {
          this.window.maximizeActive();
          message = 'Maximized active window.';
        }
      }

      // BROWSER ACTIONS
      else if (action.category === 'browser') {
        if (action.type === 'open_url' && action.url) {
          const ok = await this.browser.openUrl(action.url);
          message = ok ? `Opened ${action.url}.` : `Failed to open ${action.url}.`;
        } else if (action.type === 'click_element' && action.selector) {
          await this.browser.clickElement(action.selector);
          message = `Clicked browser element '${action.selector}'.`;
        }
      }

      return {
        actionId: action.actionId,
        success: true,
        message: message || `Executed ${action.description}.`,
        durationMs: Date.now() - startTime,
      };
    } catch (err: any) {
      return {
        actionId: action.actionId,
        success: false,
        message: `Execution failed: ${err?.message || err}`,
        error: String(err),
        durationMs: Date.now() - startTime,
      };
    }
  }
}
