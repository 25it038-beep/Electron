/**
 * Visual Grounding Engine: Resolves natural language UI descriptions
 * (e.g. "Run button", "Search input field", "Submit") into exact pixel coordinates [x, y].
 */

import { ComputerState, UIElement } from '../types/ComputerState';

export interface GroundingResult {
  coordinates: [number, number];
  confidence: number;
  matchedElement?: UIElement;
  source: 'element_detector' | 'ocr' | 'heuristic_fallback';
}

export class VisualGrounding {
  /**
   * Resolve a natural language element descriptor into screen coordinates.
   */
  public resolveTarget(description: string, state: ComputerState): GroundingResult | null {
    const cleanDesc = description.trim().toLowerCase();

    // 1. Check detected UI elements by label and type
    for (const elem of state.visibleElements) {
      if (elem.label.toLowerCase().includes(cleanDesc) || cleanDesc.includes(elem.label.toLowerCase())) {
        return {
          coordinates: elem.location,
          confidence: elem.confidence,
          matchedElement: elem,
          source: 'element_detector',
        };
      }
    }

    // 2. Check OCR tokens
    if (state.ocrTokens) {
      for (const token of state.ocrTokens) {
        if (token.text.toLowerCase().includes(cleanDesc)) {
          return {
            coordinates: token.location,
            confidence: token.confidence,
            source: 'ocr',
          };
        }
      }
    }

    // 3. Common Application Landmarks
    const width = state.screenResolution.width;
    const height = state.screenResolution.height;

    if (cleanDesc.includes('search') || cleanDesc.includes('address bar') || cleanDesc.includes('url')) {
      return {
        coordinates: [Math.round(width * 0.45), 82],
        confidence: 0.85,
        source: 'heuristic_fallback',
      };
    }

    if (cleanDesc.includes('run') || cleanDesc.includes('play')) {
      return {
        coordinates: [Math.round(width * 0.92), 48],
        confidence: 0.8,
        source: 'heuristic_fallback',
      };
    }

    if (cleanDesc.includes('center') || cleanDesc.includes('editor')) {
      return {
        coordinates: [Math.round(width * 0.5), Math.round(height * 0.5)],
        confidence: 0.8,
        source: 'heuristic_fallback',
      };
    }

    return null;
  }
}
