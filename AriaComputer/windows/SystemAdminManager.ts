export interface ServiceStatus {
  name: string;
  displayName: string;
  isRunning: boolean;
}

export class SystemAdminManager {
  public async getServices(): Promise<ServiceStatus[]> {
    return [
      { name: 'Audiosrv', displayName: 'Windows Audio', isRunning: true },
      { name: 'Spooler', displayName: 'Print Spooler', isRunning: true },
      { name: 'wuauserv', displayName: 'Windows Update', isRunning: false },
    ];
  }

  public async restartService(serviceName: string): Promise<{ success: boolean; message: string }> {
    const allowed = ['audiosrv', 'spooler'];
    if (!allowed.includes(serviceName.toLowerCase())) {
      return { success: false, message: `Restart not permitted for ${serviceName}` };
    }
    return { success: true, message: `Service ${serviceName} restarted successfully.` };
  }
}
