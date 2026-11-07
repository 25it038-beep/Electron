/**
 * Aria Windows Device Manager
 * Manages Wi-Fi, Bluetooth, audio peripherals, and printers.
 */

import { EmergencyStop } from '../safety/EmergencyStop';

export interface DeviceStatus {
  wifiConnected: boolean;
  currentNetwork: string;
  bluetoothEnabled: boolean;
  connectedDevices: string[];
}

export class DeviceManager {
  private emergencyStop = EmergencyStop.getInstance();
  private status: DeviceStatus = {
    wifiConnected: true,
    currentNetwork: 'Home_WiFi_5G',
    bluetoothEnabled: true,
    connectedDevices: ['Sony WH-1000XM4 (Headphones)', 'Logitech MX Master 3S'],
  };

  public getStatus(): DeviceStatus {
    return { ...this.status };
  }

  public connectBluetooth(deviceName: string): boolean {
    if (this.emergencyStop.check()) return false;
    if (!this.status.connectedDevices.includes(deviceName)) {
      this.status.connectedDevices.push(deviceName);
    }
    return true;
  }

  public openWifiSettings(): boolean {
    return !this.emergencyStop.check();
  }

  public openBluetoothSettings(): boolean {
    return !this.emergencyStop.check();
  }
}
