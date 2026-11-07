export interface MonitorDisplayInfo {
  name: string;
  width: number;
  height: number;
  refreshRateHz: number;
  isPrimary: boolean;
}

export interface GpuTelemetry {
  index: number;
  name: string;
  utilizationPercent: number;
  memoryUsedMb: number;
  memoryTotalMb: number;
  temperatureC: number;
  powerDrawWatts: number;
  driverVersion: string;
}

export interface ComputeProcessInfo {
  pid: number;
  processName: string;
  usedMemoryMb: string;
}

export class DisplayGraphicsManager {
  private currentBrightness: number = 100;

  public async getBrightness(): Promise<number> {
    return this.currentBrightness;
  }

  public async setBrightness(level: number): Promise<boolean> {
    this.currentBrightness = Math.max(0, Math.min(100, Math.round(level)));
    return true;
  }

  public async getDisplays(): Promise<MonitorDisplayInfo[]> {
    return [
      {
        name: 'AMD Radeon(TM) Graphics',
        width: 1920,
        height: 1080,
        refreshRateHz: 144,
        isPrimary: true,
      },
    ];
  }

  public async getNvidiaGpuTelemetry(): Promise<{
    hasNvidia: boolean;
    gpus: GpuTelemetry[];
    processes: ComputeProcessInfo[];
  }> {
    return {
      hasNvidia: true,
      gpus: [
        {
          index: 0,
          name: 'NVIDIA GeForce RTX 3050 6GB Laptop GPU',
          utilizationPercent: 0,
          memoryUsedMb: 5936,
          memoryTotalMb: 6144,
          temperatureC: 50,
          powerDrawWatts: 4.22,
          driverVersion: '592.82',
        },
      ],
      processes: [],
    };
  }
}
