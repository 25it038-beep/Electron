/**
 * Aria Computer State Manager
 * Gathers and aggregates current desktop status, active windows, UI tree, and display parameters.
 */

import { LiveScreenAnalyzer, ScreenState } from '../vision/LiveScreenAnalyzer';
import { WindowManager, WindowInfo } from '../windows/WindowManager';
import { WindowsUIAutomation } from '../windows/WindowsUIAutomation';
import { UIElement } from '../vision/UIElementDetector';

export interface AggregateComputerState {
  screen: ScreenState;
  activeWindow: WindowInfo | null;
  openWindows: WindowInfo[];
  visibleElements: UIElement[];
  timestamp: number;
}

export class ComputerStateManager {
  private screenAnalyzer: LiveScreenAnalyzer;
  private windowManager: WindowManager;
  private uia: WindowsUIAutomation;

  constructor(
    screenAnalyzer?: LiveScreenAnalyzer,
    windowManager?: WindowManager,
    uia?: WindowsUIAutomation
  ) {
    this.screenAnalyzer = screenAnalyzer || new LiveScreenAnalyzer();
    this.windowManager = windowManager || new WindowManager();
    this.uia = uia || new WindowsUIAutomation();
  }

  public getAggregateState(): AggregateComputerState {
    const screen = this.screenAnalyzer.captureScreenState();
    const activeWindow = this.windowManager.getActiveWindow();
    const openWindows = this.windowManager.listWindows();
    const tree = this.uia.getDesktopAccessibilityTree();
    const visibleElements = this.uia.extractUIElements(tree);

    return {
      screen,
      activeWindow,
      openWindows,
      visibleElements,
      timestamp: Date.now(),
    };
  }
}
