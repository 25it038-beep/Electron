/**
 * Aria Intent Understanding Engine
 * Parses natural language instructions into concrete computer operations.
 */

export type ComputerIntentType =
  | 'open_app'
  | 'close_app'
  | 'switch_window'
  | 'browser_search'
  | 'click_element'
  | 'type_text'
  | 'drag_drop'
  | 'scroll'
  | 'system_setting'
  | 'organize_files'
  | 'multi_step_workflow'
  | 'emergency_stop'
  | 'unknown';

export interface ParsedComputerIntent {
  intentType: ComputerIntentType;
  targetApp?: string;
  query?: string;
  targetElement?: string;
  textToType?: string;
  settingName?: string;
  settingValue?: any;
  rawInput: string;
}

export class IntentUnderstanding {
  public parse(input: string): ParsedComputerIntent {
    const clean = input.trim();
    const lower = clean.toLowerCase();

    // Emergency Stop
    if (/^(stop|halt|abort|cancel all|emergency stop)[\s!.]*$/i.test(clean)) {
      return { intentType: 'emergency_stop', rawInput: clean };
    }

    // Browser Search
    if (lower.startsWith('search for') || (lower.includes('chrome') && lower.includes('search'))) {
      const q = lower.replace(/.*search(\s+for)?/i, '').trim();
      return { intentType: 'browser_search', query: q, targetApp: 'chrome', rawInput: clean };
    }

    // Launch Application
    if (lower.startsWith('open ') || lower.startsWith('launch ')) {
      const app = clean.replace(/^(open|launch)\s+/i, '').trim();
      return { intentType: 'open_app', targetApp: app, rawInput: clean };
    }

    // Close Application
    if (lower.startsWith('close ') || lower.startsWith('quit ')) {
      const app = clean.replace(/^(close|quit)\s+/i, '').trim();
      return { intentType: 'close_app', targetApp: app, rawInput: clean };
    }

    // Click
    if (lower.startsWith('click ') || lower.startsWith('press ')) {
      const target = clean.replace(/^(click|press)\s+/i, '').trim();
      return { intentType: 'click_element', targetElement: target, rawInput: clean };
    }

    // Type
    if (lower.startsWith('type ') || lower.startsWith('write ')) {
      const text = clean.replace(/^(type|write)\s+/i, '').replace(/["']/g, '').trim();
      return { intentType: 'type_text', textToType: text, rawInput: clean };
    }

    // Scroll
    if (lower.includes('scroll down') || lower.includes('scroll up')) {
      return { intentType: 'scroll', rawInput: clean };
    }

    // System Settings & Info
    if (lower.includes('brightness')) {
      return { intentType: 'system_setting', settingName: 'brightness', rawInput: clean };
    }
    if (lower.includes('bluetooth') || lower.includes('wi-fi') || lower.includes('wifi') || lower.includes('storage')) {
      return { intentType: 'system_setting', settingName: 'device_or_storage', rawInput: clean };
    }

    // Clean up / Organize files
    if (lower.includes('clean up') || lower.includes('organize')) {
      return { intentType: 'organize_files', rawInput: clean };
    }

    return { intentType: 'multi_step_workflow', rawInput: clean };
  }
}
