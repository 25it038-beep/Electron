/**
 * Real-time multi-modal screen perception engine.
 * Synthesizes window metadata, visual bounding boxes, and OCR into structured ComputerState.
 */

import { ComputerState, UIElement, OCRToken } from '../types/ComputerState';
import { ScreenController } from '../controllers/ScreenController';
import { WindowController } from '../controllers/WindowController';
import { MouseController } from '../controllers/MouseController';
import { UIElementDetector } from './UIElementDetector';
import { OCRProcessor } from './OCRProcessor';

export class ScreenAnalyzer {
  private screenCtrl: ScreenController;
  private windowCtrl: WindowController;
  private mouseCtrl: MouseController;
  private elementDetector: UIElementDetector;
  private ocrProcessor: OCRProcessor;

  constructor(
    screenCtrl?: ScreenController,
    windowCtrl?: WindowController,
    mouseCtrl?: MouseController,
    elementDetector?: UIElementDetector,
    ocrProcessor?: OCRProcessor
  ) {
    this.screenCtrl = screenCtrl || new ScreenController();
    this.windowCtrl = windowCtrl || new WindowController();
    this.mouseCtrl = mouseCtrl || new MouseController();
    this.elementDetector = elementDetector || new UIElementDetector();
    this.ocrProcessor = ocrProcessor || new OCRProcessor();
  }

  /**
   * Capture and analyze the active computer environment into structured perception state.
   */
  public async analyzeState(includeOcr: boolean = true): Promise<ComputerState> {
    const activeWin = this.windowCtrl.getActiveWindow();
    const resolution = this.screenCtrl.getResolution();
    const cursor = this.mouseCtrl.getPosition();

    // 1. Capture screen base64
    const base64 = await this.screenCtrl.captureScreenBase64();

    // 2. Detect UI elements (buttons, inputs, menus)
    const elements = await this.elementDetector.detectElements(activeWin.title, resolution);

    // 3. Optional OCR tokens
    let ocrTokens: OCRToken[] = [];
    if (includeOcr) {
      ocrTokens = await this.ocrProcessor.extractTokens(activeWin.title, resolution);
    }

    return {
      activeApplication: activeWin.processName || 'Desktop',
      activeWindow: activeWin.title || 'Desktop',
      cursorLocation: [cursor.x, cursor.y],
      screenResolution: resolution,
      visibleElements: elements,
      ocrTokens,
      taskStatus: 'ready',
      automationEnabled: true,
      isPaused: false,
      emergencyStopped: false,
      timestamp: Date.now(),
    };
  }
}
