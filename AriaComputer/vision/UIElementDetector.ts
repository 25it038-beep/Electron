/**
 * Aria UI Element Detector
 * Classifies buttons, text inputs, menus, tabs, icons, and dialogs.
 */

export type UIElementType =
  | 'button'
  | 'input'
  | 'menu'
  | 'menu_item'
  | 'tab'
  | 'icon'
  | 'dialog'
  | 'checkbox'
  | 'link'
  | 'window';

export interface UIElement {
  id: string;
  type: UIElementType;
  label: string;
  x: number;
  y: number;
  width: number;
  height: number;
  isClickable: boolean;
  isEnabled: boolean;
  isFocused?: boolean;
}

export class UIElementDetector {
  public detectElements(elements: UIElement[] = []): UIElement[] {
    return elements;
  }

  public findButton(label: string, elements: UIElement[]): UIElement | null {
    const clean = label.toLowerCase();
    return (
      elements.find(
        (el) => el.type === 'button' && el.label.toLowerCase().includes(clean)
      ) || null
    );
  }

  public findInput(elements: UIElement[]): UIElement | null {
    return elements.find((el) => el.type === 'input') || null;
  }

  public findDialog(elements: UIElement[]): UIElement | null {
    return elements.find((el) => el.type === 'dialog') || null;
  }
}
