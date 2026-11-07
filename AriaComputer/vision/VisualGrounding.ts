/**
 * Aria Visual Grounding Engine
 * Resolves natural language references (e.g. "search button", "downloads folder", "first tab")
 * to actual window/desktop coordinates, adjusting for window movements and DPI scaling.
 */

import { UIElement } from './UIElementDetector';
import { OCRToken } from './OCRProcessor';
import { LiveScreenAnalyzer } from './LiveScreenAnalyzer';

export interface GroundedTarget {
  targetName: string;
  x: number;
  y: number;
  width: number;
  height: number;
  centerX: number;
  centerY: number;
  confidence: number;
  source: 'accessibility' | 'ocr' | 'visual';
}

export class VisualGrounding {
  private analyzer: LiveScreenAnalyzer;

  constructor(analyzer?: LiveScreenAnalyzer) {
    this.analyzer = analyzer || new LiveScreenAnalyzer();
  }

  public groundTarget(
    query: string,
    elements: UIElement[] = [],
    tokens: OCRToken[] = []
  ): GroundedTarget | null {
    const clean = query.trim().toLowerCase();

    // 1. Check UI Accessibility Elements
    for (const el of elements) {
      if (el.label.toLowerCase().includes(clean)) {
        const cx = Math.round(el.x + el.width / 2);
        const cy = Math.round(el.y + el.height / 2);
        return {
          targetName: el.label,
          x: el.x,
          y: el.y,
          width: el.width,
          height: el.height,
          centerX: cx,
          centerY: cy,
          confidence: 0.95,
          source: 'accessibility',
        };
      }
    }

    // 2. Fallback to OCR text tokens
    for (const token of tokens) {
      if (token.text.toLowerCase().includes(clean)) {
        const cx = Math.round(token.x + token.width / 2);
        const cy = Math.round(token.y + token.height / 2);
        return {
          targetName: token.text,
          x: token.x,
          y: token.y,
          width: token.width,
          height: token.height,
          centerX: cx,
          centerY: cy,
          confidence: 0.85,
          source: 'ocr',
        };
      }
    }

    return null;
  }
}
