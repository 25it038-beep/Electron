"""History Dialog displaying stored tasks, steps, and audit logs."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from storage.database import TaskDatabase


class HistoryDialog(QDialog):
    """Inspects SQLite stored task sessions and multi-step execution logs."""

    def __init__(self, database: TaskDatabase, parent=None) -> None:
        super().__init__(parent)
        self.db = database
        self.setWindowTitle("Electorn AI — Workflow Execution History")
        self.resize(780, 480)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Recorded Task History & Verification Log")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #06B6D4; margin-bottom: 6px;")
        layout.addWidget(title)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Timestamp", "Task Objective", "Status", "Steps", "Error / Result"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        self._load_data()

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btn_box.rejected.connect(self.accept)
        layout.addWidget(btn_box)

    def _load_data(self) -> None:
        tasks = self.db.get_recent_tasks(limit=50)
        self.table.setRowCount(len(tasks))
        for row, t in enumerate(tasks):
            self.table.setItem(row, 0, QTableWidgetItem(str(t.get("created_at", ""))))
            self.table.setItem(row, 1, QTableWidgetItem(str(t.get("transcript", ""))))
            self.table.setItem(row, 2, QTableWidgetItem(str(t.get("status", "")).upper()))
            steps_info = f"{t.get('completed_steps', 0)}/{t.get('total_steps', 0)}"
            self.table.setItem(row, 3, QTableWidgetItem(steps_info))
            self.table.setItem(row, 4, QTableWidgetItem(str(t.get("error_msg") or "Success")))
