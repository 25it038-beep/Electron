/**
 * Aria Voice Coordinator: Handles multilingual voice communication, spoken status, and interrupts.
 */

import { SafetyCoordinator } from './SafetyCoordinator';

export class VoiceCoordinator {
  private safety: SafetyCoordinator;
  private isMuted: boolean = false;
  private currentLanguage: string = 'en-US';

  constructor(safety?: SafetyCoordinator) {
    this.safety = safety || new SafetyCoordinator();
  }

  /**
   * Check if user utterance is an immediate voice interrupt command.
   */
  public isVoiceInterrupt(text: string): boolean {
    const clean = text.trim().toLowerCase();
    return (
      clean === 'stop' ||
      clean === 'stop!' ||
      clean === 'stop everything' ||
      clean === 'halt' ||
      clean === 'cancel' ||
      clean === 'pause' ||
      clean === 'நிறுத்து'
    );
  }

  public handleSpokenInput(text: string): { isInterrupt: boolean; cleanText: string } {
    if (this.isVoiceInterrupt(text)) {
      this.safety.triggerEmergencyStop('Voice interrupt command: ' + text);
      return { isInterrupt: true, cleanText: text };
    }
    return { isInterrupt: false, cleanText: text };
  }

  public toggleMute(): boolean {
    this.isMuted = !this.isMuted;
    return this.isMuted;
  }

  public setLanguage(lang: string): void {
    this.currentLanguage = lang;
  }

  public getLanguage(): string {
    return this.currentLanguage;
  }
}
