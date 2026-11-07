/**
 * Aria Context Resolver
 * Resolves conversational pronouns and spatial references ("this", "that", "there", "the previous window",
 * "the second button", "the same application") to actual screen entities and history.
 */

import { UIElement } from '../vision/UIElementDetector';
import { WindowInfo } from '../windows/WindowManager';

export interface InteractionHistoryItem {
  timestamp: number;
  type: string;
  target?: string;
  element?: UIElement;
  window?: WindowInfo;
}

export class ContextResolver {
  private history: InteractionHistoryItem[] = [];

  public recordInteraction(item: InteractionHistoryItem): void {
    this.history.push(item);
    if (this.history.length > 50) this.history.shift();
  }

  public resolveReference(
    phrase: string,
    currentElements: UIElement[],
    activeWindow: WindowInfo | null
  ): UIElement | WindowInfo | null {
    const clean = phrase.toLowerCase().trim();

    // 1. "this" / "current window" / "the same application"
    if (clean.includes('this') || clean.includes('current window') || clean.includes('same application')) {
      if (activeWindow) return activeWindow;
    }

    // 2. "previous window" / "earlier window"
    if (clean.includes('previous window') || clean.includes('earlier window')) {
      const prevWin = [...this.history].reverse().find((h) => h.window && h.window.title !== activeWindow?.title);
      if (prevWin && prevWin.window) return prevWin.window;
    }

    // 3. Ordinal element: "second button", "first result"
    const ordinalMatch = clean.match(/(first|second|third|fourth|1st|2nd|3rd|4th)\s+(button|link|item|result)/);
    if (ordinalMatch) {
      const ord = ordinalMatch[1];
      const type = ordinalMatch[2];
      const matching = currentElements.filter((el) =>
        type === 'button' ? el.type === 'button' : el.isClickable
      );
      const indexMap: Record<string, number> = {
        first: 0,
        '1st': 0,
        second: 1,
        '2nd': 1,
        third: 2,
        '3rd': 2,
        fourth: 3,
        '4th': 3,
      };
      const idx = indexMap[ord] ?? 0;
      if (idx < matching.length) return matching[idx];
    }

    // 4. "that button" / "that file"
    if (clean.includes('that') || clean.includes('there')) {
      const prevEl = [...this.history].reverse().find((h) => h.element);
      if (prevEl && prevEl.element) return prevEl.element;
    }

    return null;
  }
}
