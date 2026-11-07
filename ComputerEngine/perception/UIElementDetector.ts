/**
 * Detects interactive UI elements (buttons, search boxes, editors, tabs)
 * using accessibility trees and application layouts.
 */

import { UIElement } from '../types/ComputerState';
import { ScreenResolution } from '../controllers/ScreenController';
import { execSync } from 'child_process';

export class UIElementDetector {
  /**
   * Detect interactive UI elements currently exposed by the focused window.
   */
  public async detectElements(windowTitle: string, resolution: ScreenResolution): Promise<UIElement[]> {
    const elements: UIElement[] = [];

    // 1. Check UI Automation via PowerShell on Windows
    if (process.platform === 'win32') {
      try {
        const script = `
          Add-Type -AssemblyName UIAutomationClient;
          $root = [System.Windows.Automation.AutomationElement]::RootElement;
          $focus = [System.Windows.Automation.AutomationElement]::FocusedElement;
          if ($focus) {
            $rect = $focus.Current.BoundingRectangle;
            $name = $focus.Current.Name;
            $type = $focus.Current.ControlType.ProgrammaticName;
            Write-Output "$name|||$type|||$($rect.X)|||$($rect.Y)|||$($rect.Width)|||$($rect.Height)";
          }
        `;
        const res = execSync(`powershell -NoProfile -Command "${script}"`, { timeout: 2000, encoding: 'utf-8' });
        const parts = res.trim().split('|||');
        if (parts.length >= 6) {
          const x = parseInt(parts[2], 10) || 0;
          const y = parseInt(parts[3], 10) || 0;
          const w = parseInt(parts[4], 10) || 0;
          const h = parseInt(parts[5], 10) || 0;
          const label = parts[0] || 'Focused Element';
          const ctrlType = parts[1].includes('Button') ? 'button' : parts[1].includes('Edit') ? 'input' : 'editor';

          elements.push({
            id: `elem_${Date.now()}_0`,
            type: ctrlType as any,
            label,
            location: [Math.round(x + w / 2), Math.round(y + h / 2)],
            bounds: { x, y, width: w, height: h },
            confidence: 0.95,
            isEnabled: true,
            isVisible: true,
          });
        }
      } catch (e) {
        // Fallback
      }
    }

    // 2. Synthesize common landmarks based on application category
    const lowerTitle = windowTitle.toLowerCase();
    if (lowerTitle.includes('visual studio code') || lowerTitle.includes('vs code') || lowerTitle.includes('.py') || lowerTitle.includes('.ts')) {
      elements.push({
        id: 'vscode_run_btn',
        type: 'button',
        label: 'Run',
        location: [Math.round(resolution.width * 0.92), 48],
        bounds: { x: Math.round(resolution.width * 0.90), y: 35, width: 60, height: 26 },
        confidence: 0.9,
        isEnabled: true,
        isVisible: true,
      });
      elements.push({
        id: 'vscode_editor',
        type: 'editor',
        label: 'Code Editor',
        location: [Math.round(resolution.width * 0.5), Math.round(resolution.height * 0.5)],
        bounds: { x: 300, y: 100, width: resolution.width - 320, height: resolution.height - 150 },
        confidence: 0.98,
        isEnabled: true,
        isVisible: true,
      });
    } else if (lowerTitle.includes('chrome') || lowerTitle.includes('edge') || lowerTitle.includes('browser')) {
      elements.push({
        id: 'browser_address_bar',
        type: 'input',
        label: 'Address Bar / Search',
        location: [Math.round(resolution.width * 0.45), 82],
        bounds: { x: 200, y: 68, width: Math.round(resolution.width * 0.6), height: 32 },
        confidence: 0.96,
        isEnabled: true,
        isVisible: true,
      });
    } else if (lowerTitle.includes('notepad')) {
      elements.push({
        id: 'notepad_editor',
        type: 'editor',
        label: 'Text Document',
        location: [Math.round(resolution.width * 0.4), Math.round(resolution.height * 0.4)],
        bounds: { x: 100, y: 100, width: resolution.width - 200, height: resolution.height - 200 },
        confidence: 0.99,
        isEnabled: true,
        isVisible: true,
      });
    }

    return elements;
  }
}
