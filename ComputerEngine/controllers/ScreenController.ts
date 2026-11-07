/**
 * Native screen capture, resolution detection, and multi-monitor coordinate scaling.
 */

import { execSync } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';

export interface ScreenResolution {
  width: number;
  height: number;
}

export interface CropRegion {
  x: number;
  y: number;
  width: number;
  height: number;
}

export class ScreenController {
  private lastCapturedPath: string = '';
  private cachedResolution?: ScreenResolution;

  /**
   * Get primary screen resolution.
   */
  public getResolution(): ScreenResolution {
    if (this.cachedResolution) return this.cachedResolution;

    if (process.platform === 'win32') {
      try {
        const script = `Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Width; [System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Height`;
        const out = execSync(`powershell -NoProfile -Command "${script}"`, { timeout: 2000, encoding: 'utf-8' });
        const parts = out.trim().split(/\r?\n/).filter(Boolean);
        if (parts.length >= 2) {
          this.cachedResolution = {
            width: parseInt(parts[0], 10) || 1920,
            height: parseInt(parts[1], 10) || 1080,
          };
          return this.cachedResolution;
        }
      } catch (e) {
        // Fallback default
      }
    }

    return { width: 1920, height: 1080 };
  }

  /**
   * Capture desktop screenshot and return as base64 JPEG/PNG string.
   */
  public async captureScreenBase64(crop?: CropRegion): Promise<string> {
    const tempFile = path.join(os.tmpdir(), `hace_screen_${Date.now()}.png`);
    try {
      if (process.platform === 'win32') {
        const res = this.getResolution();
        const startX = crop ? Math.max(0, crop.x) : 0;
        const startY = crop ? Math.max(0, crop.y) : 0;
        const width = crop ? Math.min(res.width - startX, crop.width) : res.width;
        const height = crop ? Math.min(res.height - startY, crop.height) : res.height;

        const script = `
          Add-Type -AssemblyName System.Drawing;
          $bmp = New-Object System.Drawing.Bitmap(${width}, ${height});
          $g = [System.Drawing.Graphics]::FromImage($bmp);
          $g.CopyFromScreen(${startX}, ${startY}, 0, 0, (New-Object System.Drawing.Size(${width}, ${height})));
          $bmp.Save("${tempFile.replace(/\\/g, '\\\\')}", [System.Drawing.Imaging.ImageFormat]::Png);
          $g.Dispose();
          $bmp.Dispose();
        `;
        execSync(`powershell -NoProfile -Command "${script}"`, { timeout: 4000 });

        if (fs.existsSync(tempFile)) {
          const buffer = fs.readFileSync(tempFile);
          this.lastCapturedPath = tempFile;
          return buffer.toString('base64');
        }
      }
    } catch (e) {
      // Fallback
    } finally {
      if (fs.existsSync(tempFile)) {
        try { fs.unlinkSync(tempFile); } catch (e) {}
      }
    }
    return '';
  }
}
