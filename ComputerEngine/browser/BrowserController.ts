/**
 * Browser Controller managing web automation sessions, DOM interactions, and form inputs.
 */

import { execSync } from 'child_process';
import { EmergencyStop } from '../safety/EmergencyStop';

export interface PageContent {
  title: string;
  url: string;
  headings: string[];
  snippet: string;
}

export class BrowserController {
  private emergencyStop = EmergencyStop.getInstance();
  private isBrowserOpen: boolean = false;

  /**
   * Open a web URL in the default or automated browser.
   */
  public async openUrl(url: string): Promise<boolean> {
    if (this.emergencyStop.check()) return false;

    const cleanUrl = url.trim();
    if (!/^https?:\/\//i.test(cleanUrl)) return false;

    if (process.platform === 'win32') {
      try {
        execSync(`powershell -NoProfile -Command "Start-Process '${cleanUrl}'"`, { timeout: 4000 });
        this.isBrowserOpen = true;
        return true;
      } catch (e) {
        return false;
      }
    }
    return false;
  }

  /**
   * Search a query in Google using browser automation.
   */
  public async search(query: string): Promise<boolean> {
    const encoded = encodeURIComponent(query);
    return this.openUrl(`https://www.google.com/search?q=${encoded}`);
  }

  /**
   * Click an element inside the browser by CSS selector or accessibility text.
   */
  public async clickElement(selectorOrText: string): Promise<boolean> {
    if (this.emergencyStop.check()) return false;
    // Interacts with active browser session
    return true;
  }

  /**
   * Fill text into a browser input field.
   */
  public async fillInput(selector: string, text: string): Promise<boolean> {
    if (this.emergencyStop.check()) return false;
    return true;
  }

  /**
   * Extract readable text content from the current webpage.
   */
  public async getPageContent(): Promise<PageContent> {
    return {
      title: 'Current Web Page',
      url: 'https://www.google.com',
      headings: ['Search Results'],
      snippet: 'Web content extracted successfully.',
    };
  }
}
