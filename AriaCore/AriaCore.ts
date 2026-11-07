/**
 * ARIA Core Entry Point
 * HS AI Solutions - Project ARIA Unified Autonomous AI Companion
 */

import { AriaCoordinator } from './AriaCoordinator';

export class AriaCore extends AriaCoordinator {
  constructor(userName: string = 'Harshan') {
    super(userName);
  }
}

export default AriaCore;
