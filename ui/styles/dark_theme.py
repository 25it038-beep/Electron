"""Obsidian Dark Cinematic Theme stylesheet for Electorn AI PyQt6 GUI."""

DARK_THEME_QSS = """
/* Base Window and Dialogs */
QMainWindow, QDialog, QWidget {
    background-color: #0B0F19;
    color: #E2E8F0;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
}

/* Scrollbars */
QScrollBar:vertical {
    background: #0B0F19;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #1E293B;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #334155;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Group Boxes / Frames / Cards */
QFrame#card {
    background-color: #111827;
    border: 1px solid #1F2937;
    border-radius: 10px;
}

QFrame#statusCard {
    background-color: #111827;
    border: 1px solid #06B6D4;
    border-radius: 10px;
}

/* Headings and Labels */
QLabel {
    color: #E2E8F0;
}
QLabel#titleLabel {
    font-size: 20px;
    font-weight: bold;
    color: #06B6D4;
    letter-spacing: 0.5px;
}
QLabel#sectionHeader {
    font-size: 14px;
    font-weight: bold;
    color: #94A3B8;
    text-transform: uppercase;
    letter-spacing: 1px;
}
QLabel#mutedLabel {
    color: #64748B;
    font-size: 12px;
}

/* Buttons */
QPushButton {
    background-color: #1E293B;
    color: #F8FAFC;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #334155;
    border-color: #06B6D4;
}
QPushButton:pressed {
    background-color: #0F172A;
}
QPushButton:disabled {
    background-color: #0F172A;
    color: #475569;
    border-color: #1E293B;
}

/* Primary Cyan Action Buttons */
QPushButton#primaryBtn {
    background-color: #06B6D4;
    color: #090D16;
    border: none;
    font-weight: 700;
}
QPushButton#primaryBtn:hover {
    background-color: #22D3EE;
}
QPushButton#primaryBtn:pressed {
    background-color: #0891B2;
}

/* Danger / Interrupt Buttons */
QPushButton#dangerBtn {
    background-color: #EF4444;
    color: #FFFFFF;
    border: none;
}
QPushButton#dangerBtn:hover {
    background-color: #DC2626;
}
QPushButton#dangerBtn:pressed {
    background-color: #B91C1C;
}

/* Voice Mic Button */
QPushButton#micBtn {
    background-color: #1E293B;
    border: 2px solid #06B6D4;
    border-radius: 28px;
    min-width: 56px;
    min-height: 56px;
    max-width: 56px;
    max-height: 56px;
}
QPushButton#micBtn:checked {
    background-color: #EF4444;
    border-color: #F87171;
}

/* Text Inputs */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #0F172A;
    color: #F8FAFC;
    border: 1px solid #1E293B;
    border-radius: 6px;
    padding: 8px 12px;
    selection-background-color: #06B6D4;
    selection-color: #090D16;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #06B6D4;
}

/* List Views and Tree Views */
QListWidget, QTableWidget {
    background-color: #0F172A;
    border: 1px solid #1E293B;
    border-radius: 8px;
    color: #E2E8F0;
    outline: none;
}
QListWidget::item {
    padding: 8px 10px;
    border-bottom: 1px solid #1E293B;
    border-radius: 4px;
}
QListWidget::item:selected {
    background-color: #1E293B;
    border-left: 3px solid #06B6D4;
    color: #FFFFFF;
}

/* Status Bar */
QStatusBar {
    background-color: #090D16;
    color: #94A3B8;
    border-top: 1px solid #1E293B;
    font-size: 11px;
}

/* Tab Bar */
QTabWidget::pane {
    border: 1px solid #1E293B;
    background-color: #0B0F19;
}
QTabBar::tab {
    background: #0F172A;
    color: #94A3B8;
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background: #1E293B;
    color: #06B6D4;
    border-bottom: 2px solid #06B6D4;
}
"""
