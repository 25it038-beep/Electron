/**
 * Master Entry Point: HS Autonomous Computer Engine (HACE).
 * Unifies mouse, keyboard, screen perception, browser automation, and task planning.
 */

import { MouseController } from '../controllers/MouseController';
import { KeyboardController } from '../controllers/KeyboardController';
import { ClipboardController } from '../controllers/ClipboardController';
import { ScreenController } from '../controllers/ScreenController';
import { WindowController } from '../controllers/WindowController';

import { ScreenAnalyzer } from '../perception/ScreenAnalyzer';
import { UIElementDetector } from '../perception/UIElementDetector';
import { OCRProcessor } from '../perception/OCRProcessor';
import { VisualGrounding } from '../perception/VisualGrounding';

import { BrowserController } from '../browser/BrowserController';
import { BrowserNavigator } from '../browser/BrowserNavigator';
import { BrowserAgent } from '../browser/BrowserAgent';

import { PermissionManager } from '../safety/PermissionManager';
import { ActionApproval } from '../safety/ActionApproval';
import { EmergencyStop } from '../safety/EmergencyStop';
import { ActionValidator as SafetyValidator } from '../safety/ActionValidator';

import { ActionPlanner } from './ActionPlanner';
import { ActionExecutor } from './ActionExecutor';
import { ActionValidator } from './ActionValidator';
import { TaskManager } from './TaskManager';
import { TaskMemory } from './TaskMemory';

import { ComputerState } from '../types/ComputerState';
import { TaskPlan, TaskStep } from '../types/TaskTypes';
import { ActionResult } from '../types/ActionTypes';

export class ComputerEngine {
  // Subsystem Controllers
  public readonly mouse: MouseController;
  public readonly keyboard: KeyboardController;
  public readonly clipboard: ClipboardController;
  public readonly screen: ScreenController;
  public readonly window: WindowController;

  // Perception Subsystems
  public readonly analyzer: ScreenAnalyzer;
  public readonly elementDetector: UIElementDetector;
  public readonly ocr: OCRProcessor;
  public readonly grounding: VisualGrounding;

  // Browser Automation
  public readonly browser: BrowserController;
  public readonly navigator: BrowserNavigator;
  public readonly browserAgent: BrowserAgent;

  // Safety & Permissions
  public readonly permissions: PermissionManager;
  public readonly approval: ActionApproval;
  public readonly emergencyStop: EmergencyStop;
  public readonly safetyValidator: SafetyValidator;

  // Planning & Lifecycle
  public readonly planner: ActionPlanner;
  public readonly executor: ActionExecutor;
  public readonly validator: ActionValidator;
  public readonly taskManager: TaskManager;
  public readonly memory: TaskMemory;

  private isEnabled: boolean = true;

  constructor() {
    this.emergencyStop = EmergencyStop.getInstance();
    this.permissions = new PermissionManager(true);
    this.approval = new ActionApproval();
    this.safetyValidator = new SafetyValidator();

    this.mouse = new MouseController();
    this.clipboard = new ClipboardController();
    this.keyboard = new KeyboardController(this.clipboard);
    this.screen = new ScreenController();
    this.window = new WindowController();

    this.elementDetector = new UIElementDetector();
    this.ocr = new OCRProcessor();
    this.analyzer = new ScreenAnalyzer(this.screen, this.window, this.mouse, this.elementDetector, this.ocr);
    this.grounding = new VisualGrounding();

    this.browser = new BrowserController();
    this.navigator = new BrowserNavigator();
    this.browserAgent = new BrowserAgent(this.browser, this.navigator);

    this.planner = new ActionPlanner();
    this.executor = new ActionExecutor(
      this.mouse,
      this.keyboard,
      this.window,
      this.browser,
      this.permissions,
      this.approval,
      this.grounding,
      this.analyzer
    );
    this.validator = new ActionValidator();
    this.memory = new TaskMemory();

    this.taskManager = new TaskManager(
      this.planner,
      this.executor,
      this.validator,
      this.analyzer,
      this.memory
    );
  }

  /**
   * Toggle computer control enabled status.
   */
  public setEnabled(enabled: boolean): void {
    this.isEnabled = enabled;
  }

  public isControlEnabled(): boolean {
    return this.isEnabled;
  }

  /**
   * Execute a user instruction with physical computer operations.
   */
  public async executeInstruction(instruction: string): Promise<TaskPlan> {
    if (!this.isEnabled) {
      throw new Error('Computer Control is currently disabled.');
    }
    return this.taskManager.executeInstruction(instruction);
  }

  /**
   * Pause active automation.
   */
  public pause(): void {
    this.taskManager.pause();
  }

  /**
   * Resume paused automation.
   */
  public resume(): void {
    this.taskManager.resume();
  }

  /**
   * Global Emergency Stop.
   */
  public stop(reason: string = 'User triggered emergency stop'): void {
    this.taskManager.stop(reason);
  }

  /**
   * Get current structured perception state of the computer.
   */
  public async getState(): Promise<ComputerState> {
    const state = await this.analyzer.analyzeState(false);
    state.automationEnabled = this.isEnabled;
    state.emergencyStopped = this.emergencyStop.check();
    return state;
  }

  /**
   * Direct Smooth Mouse Click.
   */
  public async click(x?: number, y?: number): Promise<void> {
    await this.mouse.click(x, y);
  }

  /**
   * Direct Natural Text Typing.
   */
  public async typeText(text: string): Promise<void> {
    await this.keyboard.typeText(text);
  }

  /**
   * Subscribe to live task updates.
   */
  public onTaskUpdate(listener: (plan: TaskPlan, currentStep?: TaskStep) => void): () => void {
    return this.taskManager.onTaskUpdate(listener);
  }
}
