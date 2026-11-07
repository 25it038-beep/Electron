/**
 * Aria Computer Orchestrator
 * Master integration coordinator unifying vision, input, windows, browser, intelligence, memory, and safety.
 */

import { LiveScreenAnalyzer } from '../vision/LiveScreenAnalyzer';
import { VisualGrounding } from '../vision/VisualGrounding';
import { OCRProcessor } from '../vision/OCRProcessor';
import { UIElementDetector } from '../vision/UIElementDetector';

import { MouseController } from '../input/MouseController';
import { KeyboardController } from '../input/KeyboardController';
import { ClipboardController } from '../input/ClipboardController';

import { WindowsUIAutomation } from '../windows/WindowsUIAutomation';
import { WindowManager } from '../windows/WindowManager';
import { ApplicationManager } from '../windows/ApplicationManager';
import { SystemController } from '../windows/SystemController';
import { DeviceManager } from '../windows/DeviceManager';

import { BrowserController } from '../browser/BrowserController';
import { BrowserAutomation } from '../browser/BrowserAutomation';

import { ContextResolver } from '../intelligence/ContextResolver';
import { IntentUnderstanding } from '../intelligence/IntentUnderstanding';
import { InteractionReasoner } from '../intelligence/InteractionReasoner';
import { RecoveryEngine } from '../intelligence/RecoveryEngine';

import { InteractionMemory, WorkflowMemory, ApplicationMemory } from '../memory';

import { PermissionManager } from '../safety/PermissionManager';
import { ApprovalManager } from '../safety/ApprovalManager';
import { EmergencyStop } from '../safety/EmergencyStop';

import { ComputerStateManager } from './ComputerStateManager';
import { ActionPlanner, ActionPlan } from './ActionPlanner';
import { ActionExecutor } from './ActionExecutor';
import { ActionVerifier } from './ActionVerifier';
import { HumanInteractionEngine } from './HumanInteractionEngine';

export class ComputerOrchestrator {
  public readonly vision: LiveScreenAnalyzer;
  public readonly grounding: VisualGrounding;
  public readonly ocr: OCRProcessor;
  public readonly uiDetector: UIElementDetector;

  public readonly mouse: MouseController;
  public readonly keyboard: KeyboardController;
  public readonly clipboard: ClipboardController;

  public readonly uia: WindowsUIAutomation;
  public readonly windows: WindowManager;
  public readonly apps: ApplicationManager;
  public readonly system: SystemController;
  public readonly devices: DeviceManager;

  public readonly browser: BrowserController;
  public readonly browserAuto: BrowserAutomation;

  public readonly contextResolver: ContextResolver;
  public readonly intentParser: IntentUnderstanding;
  public readonly reasoner: InteractionReasoner;
  public readonly recovery: RecoveryEngine;

  public readonly interactionMemory: InteractionMemory;
  public readonly workflowMemory: WorkflowMemory;
  public readonly appMemory: ApplicationMemory;

  public readonly permissions: PermissionManager;
  public readonly approval: ApprovalManager;
  public readonly emergencyStop: EmergencyStop;

  public readonly stateManager: ComputerStateManager;
  public readonly planner: ActionPlanner;
  public readonly executor: ActionExecutor;
  public readonly verifier: ActionVerifier;
  public readonly engine: HumanInteractionEngine;

  constructor() {
    this.vision = new LiveScreenAnalyzer();
    this.ocr = new OCRProcessor();
    this.uiDetector = new UIElementDetector();
    this.grounding = new VisualGrounding(this.vision);

    this.mouse = new MouseController();
    this.keyboard = new KeyboardController();
    this.clipboard = new ClipboardController();

    this.uia = new WindowsUIAutomation();
    this.windows = new WindowManager();
    this.apps = new ApplicationManager();
    this.system = new SystemController();
    this.devices = new DeviceManager();

    this.browser = new BrowserController();
    this.browserAuto = new BrowserAutomation(this.browser);

    this.contextResolver = new ContextResolver();
    this.intentParser = new IntentUnderstanding();
    this.reasoner = new InteractionReasoner();
    this.recovery = new RecoveryEngine();

    this.interactionMemory = new InteractionMemory();
    this.workflowMemory = new WorkflowMemory();
    this.appMemory = new ApplicationMemory();

    this.permissions = new PermissionManager();
    this.approval = new ApprovalManager();
    this.emergencyStop = EmergencyStop.getInstance();

    this.stateManager = new ComputerStateManager(this.vision, this.windows, this.uia);
    this.planner = new ActionPlanner(this.reasoner);
    this.verifier = new ActionVerifier();
    this.executor = new ActionExecutor(
      this.mouse,
      this.keyboard,
      this.windows,
      this.apps,
      this.browser,
      this.system,
      this.grounding,
      this.permissions
    );
    this.engine = new HumanInteractionEngine(
      this.stateManager,
      this.intentParser,
      this.planner,
      this.executor,
      this.verifier,
      this.recovery,
      this.interactionMemory,
      this.workflowMemory
    );
  }

  public async executeNaturalInstruction(instruction: string): Promise<ActionPlan> {
    return this.engine.executeInstruction(instruction);
  }

  public stopAll(reason: string = 'User Emergency Stop'): void {
    this.emergencyStop.trigger(reason);
  }

  public resetSafety(): void {
    this.emergencyStop.reset();
  }
}
