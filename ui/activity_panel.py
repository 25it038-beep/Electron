"""Activity and Audit Log Panel displaying real-time events and telemetry."""

from __future__ import annotations

import time
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ActivityPanel(QWidget):
    """Real-time scrolling event feed recording all agent actions, warnings, and system events."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Header
        header = QHBoxLayout()
        title = QLabel("Activity & Event Log")
        title.setObjectName("sectionHeader")
        header.addWidget(title)
        header.addStretch()

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setFixedHeight(26)
        self.clear_btn.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        self.clear_btn.clicked.connect(self.clear_logs)
        header.addWidget(self.clear_btn)

        layout.addLayout(header)

        # Log List
        self.log_list = QListWidget()
        self.log_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.log_list.setStyleSheet("""
            QListWidget {
                background-color: #0F172A;
                border: 1px solid #1E293B;
                border-radius: 8px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
            }
            QListWidget::item {
                border-bottom: 1px solid #1E293B;
                padding: 4px 8px;
            }
        """)
        layout.addWidget(self.log_list)

    def log(self, message: str, level: str = "INFO") -> None:
        """Append a timestamped log entry."""
        ts = time.strftime("%H:%M:%S")
        color = "#94A3B8"
        if level == "INFO":
            color = "#38BDF8"
        elif level == "SUCCESS":
            color = "#34D399"
        elif level == "WARN":
            color = "#FBBF24"
        elif level == "ERROR":
            color = "#F87171"
        elif level == "SECURITY":
            color = "#F43F5E"

        item = QListWidgetItem(f"[{ts}] [{level}] {message}")
        item.setForeground(Qt.GlobalColor.white)
        self.log_list.addItem(item)
        self.log_list.scrollToBottom()

    def clear_logs(self) -> None:
        self.log_list.clear()
