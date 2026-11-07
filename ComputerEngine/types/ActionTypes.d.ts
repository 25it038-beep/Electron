/**
 * Action types and definitions for HACE Computer Engine.
 */
export type MouseActionType = 'move_cursor' | 'click' | 'right_click' | 'double_click' | 'mouse_down' | 'mouse_up' | 'drag_and_drop' | 'scroll';
export type KeyboardActionType = 'type_text' | 'press_key' | 'key_down' | 'key_up' | 'shortcut' | 'select_all' | 'copy' | 'paste' | 'undo' | 'redo';
export type WindowActionType = 'launch_app' | 'close_app' | 'focus_window' | 'minimize_window' | 'maximize_window';
export type BrowserActionType = 'open_url' | 'click_element' | 'fill_input' | 'get_page_content' | 'take_screenshot' | 'download_file' | 'evaluate_script';
export type ActionCategory = 'mouse' | 'keyboard' | 'window' | 'browser' | 'system';
export type RiskLevel = 'safe' | 'low_risk' | 'high_risk_confirm' | 'blocked';
export interface ActionPayload {
    actionId: string;
    category: ActionCategory;
    type: string;
    target?: string;
    coordinates?: [number, number];
    endCoordinates?: [number, number];
    text?: string;
    keys?: string[];
    deltaX?: number;
    deltaY?: number;
    url?: string;
    selector?: string;
    timeoutMs?: number;
    description: string;
    riskLevel: RiskLevel;
    requiresConfirmation?: boolean;
}
export interface ActionResult {
    actionId: string;
    success: boolean;
    message: string;
    data?: Record<string, unknown>;
    error?: string;
    durationMs: number;
    screenshotBase64?: string;
}
