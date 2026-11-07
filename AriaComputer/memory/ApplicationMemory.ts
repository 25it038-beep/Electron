/**
 * Aria Application Memory
 */

export class ApplicationMemory {
  private preferences: Map<string, any> = new Map();

  constructor() {
    this.preferences.set('default_projects_dir', 'C:\\Users\\BS.Harshan seliyan\\Documents\\antigravity');
    this.preferences.set('default_browser', 'chrome');
    this.preferences.set('preferred_editor', 'vscode');
  }

  public getPreference(key: string): any {
    return this.preferences.get(key);
  }

  public setPreference(key: string, value: any): void {
    this.preferences.set(key, value);
  }
}
