/**
 * Real-time structured computer perception state.
 */

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface UIElement {
  id: string;
  type: 'button' | 'input' | 'text' | 'editor' | 'menu' | 'dialog' | 'tab' | 'icon' | 'window';
  label: string;
  location: [number, number]; // [centerX, centerY]
  bounds?: BoundingBox;
  confidence: number;
  isEnabled: boolean;
  isVisible: boolean;
}

export interface OCRToken {
  text: string;
  location: [number, number];
  bounds: BoundingBox;
  confidence: number;
}

export interface ComputerState {
  activeApplication: string;
  activeWindow: string;
  cursorLocation: [number, number];
  screenResolution: {
    width: number;
    height: number;
  };
  visibleElements: UIElement[];
  ocrTokens?: OCRToken[];
  taskStatus: 'ready' | 'busy' | 'paused' | 'error';
  automationEnabled: boolean;
  isPaused: boolean;
  emergencyStopped: boolean;
  lastAction?: string;
  timestamp: number;
}
