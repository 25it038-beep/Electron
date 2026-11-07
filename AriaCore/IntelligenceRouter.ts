/**
 * Aria Intelligence Router: Automatically classifies user intent without requiring mode switching.
 */

export type IntentCategory =
  | 'emergency_stop'
  | 'greeting_or_special_day'
  | 'continue_previous'
  | 'learn_procedure'
  | 'desktop_automation'
  | 'code_or_app_build'
  | 'web_research'
  | 'explain_screen_error'
  | 'casual_conversation';

export interface RoutedIntent {
  category: IntentCategory;
  cleanInput: string;
  extractedParameters?: Record<string, string>;
}

export class IntelligenceRouter {
  public route(userInput: string): RoutedIntent {
    const clean = userInput.trim();
    const lower = clean.toLowerCase();

    // 1. EMERGENCY STOP
    if (
      lower === 'stop' ||
      lower === 'stop!' ||
      lower === 'stop everything' ||
      lower === 'halt' ||
      lower === 'cancel all' ||
      lower === 'நிறுத்து'
    ) {
      return { category: 'emergency_stop', cleanInput: clean };
    }

    // 2. GREETINGS & SPECIAL OCCASIONS
    if (
      lower.includes('good morning') ||
      lower.includes('what is special today') ||
      lower.includes('special today') ||
      lower.includes('diwali') ||
      lower.includes('pongal') ||
      lower.includes('puthandu') ||
      lower.includes('happy new year') ||
      lower.includes('christmas')
    ) {
      return { category: 'greeting_or_special_day', cleanInput: clean };
    }

    // 3. CONTINUITY & PAST RECALL
    if (
      lower.includes('continue what we did') ||
      lower.includes('what did we do') ||
      lower.includes('previous project') ||
      lower.includes('continue yesterday') ||
      lower.includes('last week')
    ) {
      return { category: 'continue_previous', cleanInput: clean };
    }

    // 4. LEARN & STORE REUSABLE PROCEDURE
    if (
      lower.includes('remember how you completed') ||
      lower.includes('remember this workflow') ||
      lower.includes('save this procedure')
    ) {
      return { category: 'learn_procedure', cleanInput: clean };
    }

    // 5. SCREEN ERROR EXPLANATION & REPAIR
    if (
      lower.includes('what is this error') ||
      lower.includes('explain this error') ||
      lower.includes('fix this error') ||
      lower.includes('fix it')
    ) {
      return { category: 'explain_screen_error', cleanInput: clean };
    }

    // 6. CODE APPLICATION BUILD & TEST
    if (
      lower.includes('create a python application') ||
      lower.includes('create a python project') ||
      lower.includes('build an application and test it')
    ) {
      return { category: 'code_or_app_build', cleanInput: clean };
    }

    // 7. WEB RESEARCH
    if (
      lower.startsWith('search for') ||
      lower.startsWith('google ') ||
      lower.includes('search online') ||
      lower.includes('research the latest')
    ) {
      return { category: 'web_research', cleanInput: clean };
    }

    // 8. DESKTOP PHYSICAL AUTOMATION
    if (
      lower.startsWith('open ') ||
      lower.startsWith('click ') ||
      lower.startsWith('type ') ||
      lower.startsWith('scroll ') ||
      lower.startsWith('move mouse ') ||
      lower.includes('minimize') ||
      lower.includes('maximize')
    ) {
      return { category: 'desktop_automation', cleanInput: clean };
    }

    // 9. DEFAULT CASUAL CONVERSATION
    return { category: 'casual_conversation', cleanInput: clean };
  }
}
