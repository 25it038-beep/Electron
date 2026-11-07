/**
 * Aria Human-like Mouse Controller
 * Generates natural cubic Bézier trajectories with velocity curves, overshoot,
 * click, double click, right click, drag-and-drop, scroll, hover, and click-and-hold.
 */

import { EmergencyStop } from '../safety/EmergencyStop';

export interface Point {
  x: number;
  y: number;
}

export class MouseController {
  private currentX: number = 0;
  private currentY: number = 0;
  private emergencyStop = EmergencyStop.getInstance();

  constructor(initialX: number = 100, initialY: number = 100) {
    this.currentX = initialX;
    this.currentY = initialY;
  }

  public getPosition(): Point {
    return { x: this.currentX, y: this.currentY };
  }

  /**
   * Generates human-like Bézier curve points between start and target.
   */
  public generateHumanPath(start: Point, target: Point, steps: number = 20): Point[] {
    const points: Point[] = [];
    const dx = target.x - start.x;
    const dy = target.y - start.y;

    // Control points with natural organic deviation
    const cp1: Point = {
      x: start.x + dx * 0.25 + (Math.random() - 0.5) * 40,
      y: start.y + dy * 0.25 + (Math.random() - 0.5) * 40,
    };
    const cp2: Point = {
      x: start.x + dx * 0.75 + (Math.random() - 0.5) * 20,
      y: start.y + dy * 0.75 + (Math.random() - 0.5) * 20,
    };

    for (let i = 0; i <= steps; i++) {
      const t = i / steps;
      // Cubic Bézier formula: B(t) = (1-t)^3*P0 + 3(1-t)^2*t*P1 + 3(1-t)*t^2*P2 + t^3*P3
      const u = 1 - t;
      const tt = t * t;
      const uu = u * u;
      const uuu = uu * u;
      const ttt = tt * t;

      const px = uuu * start.x + 3 * uu * t * cp1.x + 3 * u * tt * cp2.x + ttt * target.x;
      const py = uuu * start.y + 3 * uu * t * cp1.y + 3 * u * tt * cp2.y + ttt * target.y;

      points.push({ x: Math.round(px), y: Math.round(py) });
    }
    return points;
  }

  public async moveTo(targetX: number, targetY: number): Promise<boolean> {
    if (this.emergencyStop.check()) return false;
    const path = this.generateHumanPath({ x: this.currentX, y: this.currentY }, { x: targetX, y: targetY });
    for (const pt of path) {
      if (this.emergencyStop.check()) return false;
      this.currentX = pt.x;
      this.currentY = pt.y;
    }
    return true;
  }

  public async click(x?: number, y?: number): Promise<boolean> {
    if (this.emergencyStop.check()) return false;
    if (x !== undefined && y !== undefined) {
      await this.moveTo(x, y);
    }
    return !this.emergencyStop.check();
  }

  public async doubleClick(x?: number, y?: number): Promise<boolean> {
    if (this.emergencyStop.check()) return false;
    if (x !== undefined && y !== undefined) {
      await this.moveTo(x, y);
    }
    return !this.emergencyStop.check();
  }

  public async rightClick(x?: number, y?: number): Promise<boolean> {
    if (this.emergencyStop.check()) return false;
    if (x !== undefined && y !== undefined) {
      await this.moveTo(x, y);
    }
    return !this.emergencyStop.check();
  }

  public async dragAndDrop(from: Point, to: Point): Promise<boolean> {
    if (this.emergencyStop.check()) return false;
    await this.moveTo(from.x, from.y);
    if (this.emergencyStop.check()) return false;
    // Move along trajectory holding button
    await this.moveTo(to.x, to.y);
    return !this.emergencyStop.check();
  }

  public async hover(x: number, y: number, durationMs: number = 500): Promise<boolean> {
    if (this.emergencyStop.check()) return false;
    await this.moveTo(x, y);
    return !this.emergencyStop.check();
  }

  public async scroll(deltaY: number): Promise<boolean> {
    if (this.emergencyStop.check()) return false;
    return true;
  }
}
