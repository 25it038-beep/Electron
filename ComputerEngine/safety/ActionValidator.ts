/**
 * Pre-execution validation for screen coordinates, parameters, and application boundaries.
 */

import { ActionPayload } from '../types/ActionTypes';
import { ComputerState } from '../types/ComputerState';

export interface ValidationReport {
  isValid: boolean;
  errors: string[];
  sanitizedAction: ActionPayload;
}

export class ActionValidator {
  public validateAction(action: ActionPayload, state?: ComputerState): ValidationReport {
    const errors: string[] = [];
    const sanitized: ActionPayload = { ...action };

    // 1. Validate Mouse Coordinates
    if (action.category === 'mouse' && action.coordinates) {
      const [x, y] = action.coordinates;
      const maxWidth = state?.screenResolution.width || 3840;
      const maxHeight = state?.screenResolution.height || 2160;

      if (isNaN(x) || isNaN(y)) {
        errors.push(`Invalid coordinates [${x}, ${y}]: must be numbers.`);
      } else if (x < 0 || x > maxWidth || y < 0 || y > maxHeight) {
        errors.push(`Coordinates [${x}, ${y}] are out of screen bounds [0..${maxWidth}, 0..${maxHeight}].`);
      } else {
        // Clamp safely
        sanitized.coordinates = [
          Math.max(0, Math.min(maxWidth, Math.round(x))),
          Math.max(0, Math.min(maxHeight, Math.round(y))),
        ];
      }
    }

    // 2. Validate Keyboard Input
    if (action.category === 'keyboard') {
      if (action.type === 'type_text' && typeof action.text !== 'string') {
        errors.push('Keyboard type_text action requires a valid string in "text".');
      }
      if (action.type === 'shortcut' && (!action.keys || !Array.isArray(action.keys) || action.keys.length === 0)) {
        errors.push('Keyboard shortcut action requires an array of keys.');
      }
    }

    // 3. Validate Browser Input
    if (action.category === 'browser') {
      if (action.type === 'open_url') {
        if (!action.url || !/^https?:\/\//i.test(action.url)) {
          errors.push(`Invalid URL '${action.url}': must begin with http:// or https://.`);
        }
      }
    }

    return {
      isValid: errors.length === 0,
      errors,
      sanitizedAction: sanitized,
    };
  }
}
