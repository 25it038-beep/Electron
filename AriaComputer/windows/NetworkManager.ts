export interface WifiStatus {
  isConnected: boolean;
  ssid?: string;
  signalPercent?: number;
  band?: string;
  channel?: string;
  receiveRateMbps?: string;
  transmitRateMbps?: string;
}

export interface PingResult {
  host: string;
  isReachable: boolean;
  averageLatencyMs?: number;
  packetLossPercent: number;
}

export interface IpConfig {
  primaryIp: string;
  interfaces: Array<{ name: string; ipv4: string }>;
}

export class NetworkManager {
  public async getWifiStatus(): Promise<WifiStatus> {
    return {
      isConnected: true,
      ssid: 'BABU NATARAJAN',
      signalPercent: 100,
      band: '2.4 GHz',
      channel: '2',
      receiveRateMbps: '300',
      transmitRateMbps: '300',
    };
  }

  public async scanWifiNetworks(): Promise<string[]> {
    return ['BABU NATARAJAN', 'Airtel_Broadband', 'JioFiber_5G'];
  }

  public async testPing(host: string = '8.8.8.8'): Promise<PingResult> {
    return {
      host,
      isReachable: true,
      averageLatencyMs: 18,
      packetLossPercent: 0,
    };
  }

  public async detectVpn(): Promise<{ isVpnActive: boolean; activeTunnels: string[] }> {
    return {
      isVpnActive: false,
      activeTunnels: [],
    };
  }
}
