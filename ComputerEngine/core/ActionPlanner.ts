/**
 * Action Planner: Deconstructs natural language instructions into ordered, verified TaskPlans.
 */

import { TaskPlan, TaskStep } from '../types/TaskTypes';
import { ComputerState } from '../types/ComputerState';
import { ActionPayload } from '../types/ActionTypes';

export class ActionPlanner {
  /**
   * Plan a step-by-step sequence of actions to fulfill an instruction.
   */
  public planInstruction(instruction: string, currentState?: ComputerState): TaskPlan {
    const clean = instruction.trim();
    const lower = clean.toLowerCase();
    const taskId = `task_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;

    const steps: TaskStep[] = [];
    let goal = clean;
    let targetApp = 'Desktop';

    // 1. Browser Search Workflows
    if (lower.includes('chrome') || lower.includes('edge') || lower.includes('browser') || lower.includes('search')) {
      targetApp = 'Google Chrome';
      const searchMatch = lower.match(/search(?:\s+for|\s+online)?\s+([^.]+)/i);
      const query = searchMatch ? searchMatch[1].trim() : 'latest technology';

      steps.push({
        stepId: 'step_launch_browser',
        order: 1,
        description: 'Launch web browser',
        action: {
          actionId: 'act_1',
          category: 'window',
          type: 'launch_app',
          target: 'chrome',
          description: 'Launch Google Chrome',
          riskLevel: 'safe',
        },
        status: 'pending',
        expectedOutcome: 'Browser window is focused on screen',
        retryCount: 0,
      });

      steps.push({
        stepId: 'step_browser_search',
        order: 2,
        description: `Search for '${query}'`,
        action: {
          actionId: 'act_2',
          category: 'browser',
          type: 'open_url',
          url: `https://www.google.com/search?q=${encodeURIComponent(query)}`,
          description: `Navigate to Google search for '${query}'`,
          riskLevel: 'safe',
        },
        status: 'pending',
        expectedOutcome: 'Search results page is loaded',
        retryCount: 0,
      });
    }

    // 2. VS Code & Python Project Workflows
    else if (lower.includes('vs code') || lower.includes('vscode') || lower.includes('code') || lower.includes('python project')) {
      targetApp = 'Visual Studio Code';
      steps.push({
        stepId: 'step_launch_vscode',
        order: 1,
        description: 'Launch Visual Studio Code',
        action: {
          actionId: 'act_code_1',
          category: 'window',
          type: 'launch_app',
          target: 'vscode',
          description: 'Open VS Code editor',
          riskLevel: 'safe',
        },
        status: 'pending',
        expectedOutcome: 'VS Code window is active',
        retryCount: 0,
      });

      steps.push({
        stepId: 'step_create_file',
        order: 2,
        description: 'Open new file in editor',
        action: {
          actionId: 'act_code_2',
          category: 'keyboard',
          type: 'shortcut',
          keys: ['Control', 'n'],
          description: 'Press Ctrl+N to create new file',
          riskLevel: 'safe',
        },
        status: 'pending',
        expectedOutcome: 'New untitled file tab is open',
        retryCount: 0,
      });
    }

    // 3. Excel & Table Workflows
    else if (lower.includes('excel') || lower.includes('table') || lower.includes('spreadsheet')) {
      targetApp = 'Microsoft Excel';
      steps.push({
        stepId: 'step_launch_excel',
        order: 1,
        description: 'Launch Microsoft Excel or Spreadsheet',
        action: {
          actionId: 'act_excel_1',
          category: 'window',
          type: 'launch_app',
          target: 'excel',
          description: 'Launch Excel application',
          riskLevel: 'safe',
        },
        status: 'pending',
        expectedOutcome: 'Excel is running',
        retryCount: 0,
      });
    }

    // 4. General Typing / Click fallback
    else if (lower.startsWith('click')) {
      const target = clean.replace(/^click\s+/i, '').trim();
      steps.push({
        stepId: 'step_click_target',
        order: 1,
        description: `Click target '${target}'`,
        action: {
          actionId: 'act_click_1',
          category: 'mouse',
          type: 'click',
          target,
          description: `Locate and click '${target}'`,
          riskLevel: 'safe',
        },
        status: 'pending',
        expectedOutcome: `Element '${target}' is clicked`,
        retryCount: 0,
      });
    } else if (lower.startsWith('type')) {
      const textToType = clean.replace(/^type\s+/i, '').replace(/["']/g, '').trim();
      steps.push({
        stepId: 'step_type_text',
        order: 1,
        description: `Type '${textToType}'`,
        action: {
          actionId: 'act_type_1',
          category: 'keyboard',
          type: 'type_text',
          text: textToType,
          description: `Type text into focused element`,
          riskLevel: 'safe',
        },
        status: 'pending',
        expectedOutcome: 'Text is typed into control',
        retryCount: 0,
      });
    }

    // Default fallback single atomic step
    if (steps.length === 0) {
      steps.push({
        stepId: 'step_execute_instruction',
        order: 1,
        description: clean,
        action: {
          actionId: 'act_default_1',
          category: 'system',
          type: 'custom_command',
          description: clean,
          riskLevel: 'safe',
        },
        status: 'pending',
        expectedOutcome: 'Operation completed successfully',
        retryCount: 0,
      });
    }

    return {
      taskId,
      originalInstruction: clean,
      goal,
      targetApplication: targetApp,
      steps,
      currentStepIndex: 0,
      status: 'planned',
      startTime: Date.now(),
    };
  }
}
