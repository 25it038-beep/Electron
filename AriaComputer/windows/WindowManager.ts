/**
 * Aria Windows Window Manager
 * Controls opening, closing, minimizing, maximizing, resizing, focusing, and arranging windows.
 */

import { EmergencyStop } from '../safety/EmergencyStop';

export interface WindowInfo {
  handle: number;
  title: string;
  processName: string;
  bounds: { x: number; y: number; width: number; height: number };
  isMinimized: boolean;
  isMaximized: boolean;
  isActive: boolean;
}

export class WindowManager {
  private emergencyStop = EmergencyStop.getInstance();
  private openWindows: WindowInfo[] = [];

  constructor() {
    this.openWindows = [
      {
        handle: 1001,
        title: 'File Explorer',
        processName: 'explorer.exe',
        bounds: { x: 100, y: 100, width: 800, height: 600 },
        isMinimized: false,
        isMaximized: false,
        isActive: true,
      },
    ];
  }

  public listWindows(): WindowInfo[] {
    return [...this.openWindows];
  }

  public getActiveWindow(): WindowInfo | null {
    return this.openWindows.find((w) => w.isActive) || this.openWindows[0] || null;
  }

  public focusWindow(titleOrProcess: string): boolean {
    if (this.emergencyStop.check()) return false;
    const target = this.openWindows.find(
      (w) =>
        w.title.toLowerCase().includes(titleOrProcess.toLowerCase()) ||
        w.processName.toLowerCase().includes(titleOrProcess.toLowerCase())
    );
    if (target) {
      this.openWindows.forEach((w) => (w.isActive = false));
      target.isActive = true;
      return true;
    }
    return false;
  }

  public minimizeWindow(titleOrProcess: string): boolean {
    if (this.emergencyStop.check()) return false;
    const target = this.openWindows.find((w) =>
      w.title.toLowerCase().includes(titleOrProcess.toLowerCase())
    );
    if (target) {
      target.isMinimized = true;
      target.isActive = false;
      return true;
    }
    return false;
  }

  public maximizeWindow(titleOrProcess: string): boolean {
    if (this.emergencyStop.check()) return false;
    const target = this.openWindows.find((w) =>
      w.title.toLowerCase().includes(titleOrProcess.toLowerCase())
    );
    if (target) {
      target.isMaximized = true;
      target.isMinimized = false;
      target.isActive = true;
      return true;
    }
    return false;
  }

  public closeWindow(titleOrProcess: string): boolean {
    if (this.emergencyStop.check()) return false;
    const idx = this.openWindows.findIndex((w) =>
      w.title.toLowerCase().includes(titleOrProcess.toLowerCase())
    );
    if (idx !== -1) {
      this.openWindows.splice(idx, 1);
      return true;
    }
    return false;
  }
}
