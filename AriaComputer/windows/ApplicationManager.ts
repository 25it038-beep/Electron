/**
 * Aria Windows Application Manager
 * Launches and tracks applications: Chrome, VS Code, Word, Excel, PowerShell, File Explorer.
 */

import { EmergencyStop } from '../safety/EmergencyStop';

export interface AppDefinition {
  name: string;
  command: string;
  category: 'browser' | 'editor' | 'office' | 'system' | 'media';
  defaultPaths?: string[];
}

export class ApplicationManager {
  private emergencyStop = EmergencyStop.getInstance();
  private registeredApps: Map<string, AppDefinition> = new Map();

  constructor() {
    this.register('chrome', { name: 'Google Chrome', command: 'chrome', category: 'browser' });
    this.register('edge', { name: 'Microsoft Edge', command: 'msedge', category: 'browser' });
    this.register('vscode', { name: 'Visual Studio Code', command: 'code', category: 'editor' });
    this.register('word', { name: 'Microsoft Word', command: 'winword', category: 'office' });
    this.register('excel', { name: 'Microsoft Excel', command: 'excel', category: 'office' });
    this.register('powerpoint', { name: 'PowerPoint', command: 'powerpnt', category: 'office' });
    this.register('explorer', { name: 'File Explorer', command: 'explorer', category: 'system' });
    this.register('terminal', { name: 'Windows Terminal', command: 'wt', category: 'system' });
    this.register('powershell', { name: 'PowerShell', command: 'powershell', category: 'system' });
    this.register('notepad', { name: 'Notepad', command: 'notepad', category: 'editor' });
  }

  public register(alias: string, app: AppDefinition): void {
    this.registeredApps.set(alias.toLowerCase(), app);
  }

  public getApp(aliasOrName: string): AppDefinition | null {
    const key = aliasOrName.toLowerCase();
    if (this.registeredApps.has(key)) {
      return this.registeredApps.get(key)!;
    }
    for (const app of this.registeredApps.values()) {
      if (app.name.toLowerCase().includes(key)) return app;
    }
    return null;
  }

  public launch(aliasOrName: string): boolean {
    if (this.emergencyStop.check()) return false;
    const app = this.getApp(aliasOrName);
    return app !== null;
  }
}
