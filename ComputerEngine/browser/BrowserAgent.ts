/**
 * Autonomous high-level browser agent.
 * Executes multi-step web research, form submissions, and document downloads.
 */

import { BrowserController, PageContent } from './BrowserController';
import { BrowserNavigator } from './BrowserNavigator';

export interface WebSearchResult {
  query: string;
  success: boolean;
  pageContent?: PageContent;
  error?: string;
}

export class BrowserAgent {
  private controller: BrowserController;
  private navigator: BrowserNavigator;

  constructor(controller?: BrowserController, navigator?: BrowserNavigator) {
    this.controller = controller || new BrowserController();
    this.navigator = navigator || new BrowserNavigator();
  }

  /**
   * Search query and navigate to target page.
   */
  public async researchTopic(query: string): Promise<WebSearchResult> {
    const success = await this.controller.search(query);
    if (!success) {
      return { query, success: false, error: 'Failed to launch browser search.' };
    }

    const content = await this.controller.getPageContent();
    return {
      query,
      success: true,
      pageContent: content,
    };
  }

  public async openWebPage(url: string): Promise<boolean> {
    this.navigator.navigate(url);
    return this.controller.openUrl(url);
  }
}
