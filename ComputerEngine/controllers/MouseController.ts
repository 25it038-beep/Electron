/**
 * Low-latency, human-like mouse automation with Bézier curve trajectory smoothing.
 */

import { execSync, spawn } from 'child_process';
import { EmergencyStop } from '../safety/EmergencyStop';

export interface MousePosition {
  x: number;
  y: number;
}

export class MouseController {
  private currentX: number = 0;
  private currentY: number = 0;
  private emergencyStop = EmergencyStop.getInstance();

  constructor() {
    this.refreshPosition();
  }

  /**
   * Get current cursor coordinates on the screen.
   */
  public getPosition(): MousePosition {
    this.refreshPosition();
    return { x: this.currentX, y: this.currentY };
  }

  private refreshPosition(): void {
    if (process.platform === 'win32') {
      try {
        const script = `Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Cursor]::Position.X; [System.Windows.Forms.Cursor]::Position.Y`;
        const output = execSync(`powershell -NoProfile -Command "${script}"`, { timeout: 2000, encoding: 'utf-8' });
        const lines = output.trim().split(/\r?\n/).filter(Boolean);
        if (lines.length >= 2) {
          this.currentX = parseInt(lines[0], 10) || this.currentX;
          this.currentY = parseInt(lines[1], 10) || this.currentY;
        }
      } catch (e) {
        // Fallback retain last known
      }
    }
  }

  /**
   * Instantly move cursor to (x, y).
   */
  public setPosition(x: number, y: number): void {
    if (this.emergencyStop.check()) return;
    this.currentX = Math.round(x);
    this.currentY = Math.round(y);

    if (process.platform === 'win32') {
      try {
        const script = `Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point(${this.currentX}, ${this.currentY})`;
        execSync(`powershell -NoProfile -Command "${script}"`, { timeout: 2000 });
      } catch (e) {
        // Suppress or handle
      }
    }
  }

  /**
   * Human-like smooth mouse movement using cubic Bézier curve easing.
   */
  public async smoothMove(targetX: number, targetY: number, durationMs: number = 300): Promise<void> {
    if (this.emergencyStop.check()) return;
    this.refreshPosition();

    const startX = this.currentX;
    const startY = this.currentY;
    const endX = Math.round(targetX);
    const endY = Math.round(targetY);

    if (startX === endX && startY === endY) return;

    // Generate random Bézier control points for natural curvature
    const deltaX = endX - startX;
    const deltaY = endY - startY;
    const ctrl1X = startX + deltaX * (0.2 + Math.random() * 0.2);
    const ctrl1Y = startY + deltaY * (0.05 + Math.random() * 0.2);
    const ctrl2X = startX + deltaX * (0.6 + Math.random() * 0.2);
    const ctrl2Y = startY + deltaY * (0.7 + Math.random() * 0.2);

    const steps = Math.max(10, Math.round(durationMs / 16));
    const stepDelay = durationMs / steps;

    for (let i = 1; i <= steps; i++) {
      if (this.emergencyStop.check()) break;

      const t = i / steps;
      // Cubic Bézier calculation
      const x = Math.round(
        Math.pow(1 - t, 3) * startX +
        3 * Math.pow(1 - t, 2) * t * ctrl1X +
        3 * (1 - t) * Math.pow(t, 2) * ctrl2X +
        Math.pow(t, 3) * endX
      );
      const y = Math.round(
        Math.pow(1 - t, 3) * startY +
        3 * Math.pow(1 - t, 2) * t * ctrl1Y +
        3 * (1 - t) * Math.pow(t, 2) * ctrl2Y +
        Math.pow(t, 3) * endY
      );

      this.setPosition(x, y);
      await new Promise(r => setTimeout(r, stepDelay));
    }

    this.setPosition(endX, endY);
  }

  /**
   * Left-click at target or current location.
   */
  public async click(x?: number, y?: number): Promise<void> {
    if (this.emergencyStop.check()) return;
    if (x !== undefined && y !== undefined) {
      await this.smoothMove(x, y);
    }

    if (process.platform === 'win32') {
      const script = `
        $sig = @'
[DllImport("user32.dll",CharSet=CharSet.Auto,CallingConvention=CallingConvention.StdCall)]
public static extern void mouse_event(long dwFlags, long dx, long dy, long cButtons, long dwExtraInfo);
'@
        $m = Add-Type -memberDefinition $sig -name "MouseEvent" -namespace "Win32" -passThru
        $m::mouse_event(0x0002, 0, 0, 0, 0) # MOUSEEVENTF_LEFTDOWN
        Start-Sleep -Milliseconds 40
        $m::mouse_event(0x0004, 0, 0, 0, 0) # MOUSEEVENTF_LEFTUP
      `;
      execSync(`powershell -NoProfile -Command "${script}"`, { timeout: 3000 });
    }
  }

  /**
   * Right-click at target or current location.
   */
  public async rightClick(x?: number, y?: number): Promise<void> {
    if (this.emergencyStop.check()) return;
    if (x !== undefined && y !== undefined) {
      await this.smoothMove(x, y);
    }

    if (process.platform === 'win32') {
      const script = `
        $sig = @'
[DllImport("user32.dll",CharSet=CharSet.Auto,CallingConvention=CallingConvention.StdCall)]
public static extern void mouse_event(long dwFlags, long dx, long dy, long cButtons, long dwExtraInfo);
'@
        $m = Add-Type -memberDefinition $sig -name "MouseEventR" -namespace "Win32" -passThru
        $m::mouse_event(0x0008, 0, 0, 0, 0) # MOUSEEVENTF_RIGHTDOWN
        Start-Sleep -Milliseconds 40
        $m::mouse_event(0x0010, 0, 0, 0, 0) # MOUSEEVENTF_RIGHTUP
      `;
      execSync(`powershell -NoProfile -Command "${script}"`, { timeout: 3000 });
    }
  }

  /**
   * Double-click at target or current location.
   */
  public async doubleClick(x?: number, y?: number): Promise<void> {
    if (this.emergencyStop.check()) return;
    await this.click(x, y);
    await new Promise(r => setTimeout(r, 90));
    await this.click();
  }

  /**
   * Click and drag from source to destination.
   */
  public async dragAndDrop(fromX: number, fromY: number, toX: number, toY: number, durationMs: number = 600): Promise<void> {
    if (this.emergencyStop.check()) return;
    await this.smoothMove(fromX, fromY);

    if (process.platform === 'win32') {
      const downScript = `
        $sig = @'
[DllImport("user32.dll")] public static extern void mouse_event(long dwFlags, long dx, long dy, long cButtons, long dwExtraInfo);
'@
        $m = Add-Type -memberDefinition $sig -name "MDD" -namespace "Win32" -passThru
        $m::mouse_event(0x0002, 0, 0, 0, 0)
      `;
      execSync(`powershell -NoProfile -Command "${downScript}"`, { timeout: 2000 });
    }

    await new Promise(r => setTimeout(r, 100));
    await this.smoothMove(toX, toY, durationMs);
    await new Promise(r => setTimeout(r, 100));

    if (process.platform === 'win32') {
      const upScript = `
        $sig = @'
[DllImport("user32.dll")] public static extern void mouse_event(long dwFlags, long dx, long dy, long cButtons, long dwExtraInfo);
'@
        $m = Add-Type -memberDefinition $sig -name "MDU" -namespace "Win32" -passThru
        $m::mouse_event(0x0004, 0, 0, 0, 0)
      `;
      execSync(`powershell -NoProfile -Command "${upScript}"`, { timeout: 2000 });
    }
  }

  /**
   * Scroll vertically and horizontally.
   */
  public async scroll(deltaY: number, deltaX: number = 0): Promise<void> {
    if (this.emergencyStop.check()) return;
    if (process.platform === 'win32') {
      const script = `
        $sig = @'
[DllImport("user32.dll")] public static extern void mouse_event(long dwFlags, long dx, long dy, long cButtons, long dwExtraInfo);
'@
        $m = Add-Type -memberDefinition $sig -name "MScroll" -namespace "Win32" -passThru
        $m::mouse_event(0x0800, 0, 0, ${Math.round(deltaY * 120)}, 0) # MOUSEEVENTF_WHEEL
      `;
      execSync(`powershell -NoProfile -Command "${script}"`, { timeout: 2000 });
    }
  }
}
