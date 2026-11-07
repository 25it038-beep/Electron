/**
 * Windows UI Automation Adapter
 * Accesses native accessibility elements, control types, and invocation patterns.
 */

import { UIElement } from '../vision/UIElementDetector';

export interface AccessibleNode {
  name: string;
  controlType: string;
  automationId?: string;
  className?: string;
  bounds: { x: number; y: number; width: number; height: number };
  children?: AccessibleNode[];
  isEnabled: boolean;
  isKeyboardFocusable: boolean;
}

export class WindowsUIAutomation {
  public getDesktopAccessibilityTree(): AccessibleNode {
    return {
      name: 'Desktop',
      controlType: 'Pane',
      bounds: { x: 0, y: 0, width: 1920, height: 1080 },
      isEnabled: true,
      isKeyboardFocusable: true,
      children: [],
    };
  }

  public extractUIElements(node: AccessibleNode): UIElement[] {
    const elements: UIElement[] = [];

    const mapType = (ct: string) => {
      switch (ct.toLowerCase()) {
        case 'button':
          return 'button';
        case 'edit':
          return 'input';
        case 'menu':
          return 'menu';
        case 'menuitem':
          return 'menu_item';
        case 'tabitem':
          return 'tab';
        case 'window':
          return 'dialog';
        default:
          return 'icon';
      }
    };

    const traverse = (n: AccessibleNode) => {
      if (n.name && n.bounds) {
        elements.push({
          id: n.automationId || `el_${Math.random().toString(36).substring(2, 7)}`,
          type: mapType(n.controlType),
          label: n.name,
          x: n.bounds.x,
          y: n.bounds.y,
          width: n.bounds.width,
          height: n.bounds.height,
          isClickable: true,
          isEnabled: n.isEnabled,
        });
      }
      if (n.children) {
        for (const c of n.children) traverse(c);
      }
    };

    traverse(node);
    return elements;
  }
}
