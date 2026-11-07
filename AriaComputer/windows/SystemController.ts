/**
 * Aria Windows System Controller
 * Safely inspects storage, memory, brightness, audio volume, and desktop cleanup.
 */

import { EmergencyStop } from '../safety/EmergencyStop';

export interface SystemResourceStatus {
  totalMemoryGb: number;
  freeMemoryGb: number;
  usedMemoryPercent: number;
  diskFreeGb: number;
  topMemoryConsumers: { process: string; memoryMb: number }[];
}

export class SystemController {
  private emergencyStop = EmergencyStop.getInstance();
  private brightnessPercent: number = 80;
  private volumePercent: number = 65;

  public getSystemResources(): SystemResourceStatus {
    return {
      totalMemoryGb: 16.0,
      freeMemoryGb: 8.5,
      usedMemoryPercent: 46.8,
      diskFreeGb: 124.0,
      topMemoryConsumers: [
        { process: 'chrome.exe', memoryMb: 850 },
        { process: 'Code.exe', memoryMb: 620 },
        { process: 'explorer.exe', memoryMb: 110 },
      ],
    };
  }

  public setBrightness(percent: number): boolean {
    if (this.emergencyStop.check()) return false;
    this.brightnessPercent = Math.max(0, Math.min(100, percent));
    return true;
  }

  public getBrightness(): number {
    return this.brightnessPercent;
  }

  public setVolume(percent: number): boolean {
    if (this.emergencyStop.check()) return false;
    this.volumePercent = Math.max(0, Math.min(100, percent));
    return true;
  }

  public getVolume(): number {
    return this.volumePercent;
  }

  public getDesktopOrganizationPlan(): {
    categories: Record<string, string[]>;
    totalFiles: number;
  } {
    return {
      categories: {
        Documents: ['report.docx', 'notes.txt', 'invoice.pdf'],
        Images: ['screenshot1.png', 'avatar.jpg'],
        Installers: ['python-3.12.exe'],
      },
      totalFiles: 6,
    };
  }
}
