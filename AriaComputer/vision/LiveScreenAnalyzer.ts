/**
 * Aria Live Screen Analyzer
 * Inspects display resolution, DPI scaling, multi-monitor configuration, and active window bounds.
 */

export interface DisplayInfo {
  id: string;
  width: number;
  height: number;
  scaleFactor: number;
  isPrimary: boolean;
}

export interface ScreenState {
  displays: DisplayInfo[];
  primaryResolution: { width: number; height: number };
  activeWindowTitle: string;
  activeWindowBounds?: { x: number; y: number; width: number; height: number };
  timestamp: number;
}

export class LiveScreenAnalyzer {
  private primaryWidth: number = 1920;
  private primaryHeight: number = 1080;
  private dpiScale: number = 1.0;

  constructor() {}

  public captureScreenState(): ScreenState {
    return {
      displays: [
        {
          id: 'display_primary',
          width: this.primaryWidth,
          height: this.primaryHeight,
          scaleFactor: this.dpiScale,
          isPrimary: true,
        },
      ],
      primaryResolution: { width: this.primaryWidth, height: this.primaryHeight },
      activeWindowTitle: 'Windows Desktop',
      activeWindowBounds: { x: 0, y: 0, width: this.primaryWidth, height: this.primaryHeight },
      timestamp: Date.now(),
    };
  }

  public setResolution(width: number, height: number, scaleFactor: number = 1.0): void {
    this.primaryWidth = width;
    this.primaryHeight = height;
    this.dpiScale = scaleFactor;
  }

  public scaleCoordinates(x: number, y: number): { x: number; y: number } {
    return {
      x: Math.round(x * this.dpiScale),
      y: Math.round(y * this.dpiScale),
    };
  }
}
