"""Task Timeline Widget showing structured workflow stages, status, and verification."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from agent.action_schema import TaskPlan, TaskStep


class StepCard(QFrame):
    """Visual card representing a single atomic action step in the timeline."""

    def __init__(self, step: TaskStep, index: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.step = step
        self.index = index
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        header_layout = QHBoxLayout()

        # Step Number + Action Name
        self.title_lbl = QLabel(f"<b>#{self.index + 1}</b>  {self.step.action}")
        self.title_lbl.setStyleSheet("color: #38BDF8; font-weight: bold; font-size: 13px;")
        header_layout.addWidget(self.title_lbl)

        header_layout.addStretch()

        # Status badge
        self.badge_lbl = QLabel(self.step.status.upper())
        self._update_badge_style(self.step.status)
        header_layout.addWidget(self.badge_lbl)

        layout.addLayout(header_layout)

        # Description
        self.desc_lbl = QLabel(self.step.description or self.step.action)
        self.desc_lbl.setStyleSheet("color: #E2E8F0; font-size: 12px;")
        self.desc_lbl.setWordWrap(True)
        layout.addWidget(self.desc_lbl)

        # Evidence / Result
        self.evidence_lbl = QLabel("")
        self.evidence_lbl.setStyleSheet("color: #10B981; font-size: 11px; font-family: monospace;")
        self.evidence_lbl.setWordWrap(True)
        self.evidence_lbl.setVisible(False)
        layout.addWidget(self.evidence_lbl)

        # Error
        self.error_lbl = QLabel("")
        self.error_lbl.setStyleSheet("color: #EF4444; font-size: 11px;")
        self.error_lbl.setWordWrap(True)
        self.error_lbl.setVisible(False)
        layout.addWidget(self.error_lbl)

    def _update_badge_style(self, status: str) -> None:
        styles = {
            "pending": "background-color: #334155; color: #94A3B8; border-radius: 4px; padding: 2px 6px; font-size: 10px;",
            "in_progress": "background-color: #0369A1; color: #E0F2FE; border-radius: 4px; padding: 2px 6px; font-size: 10px;",
            "completed": "background-color: #065F46; color: #A7F3D0; border-radius: 4px; padding: 2px 6px; font-size: 10px;",
            "failed": "background-color: #991B1B; color: #FECACA; border-radius: 4px; padding: 2px 6px; font-size: 10px;",
            "skipped": "background-color: #475569; color: #CBD5E1; border-radius: 4px; padding: 2px 6px; font-size: 10px;",
        }
        self.badge_lbl.setStyleSheet(styles.get(status, styles["pending"]))
        self.badge_lbl.setText(status.upper())

    def update_step(self, step: TaskStep) -> None:
        self.step = step
        self._update_badge_style(step.status)
        if step.verification_evidence:
            self.evidence_lbl.setText(f"✓ Verified: {step.verification_evidence}")
            self.evidence_lbl.setVisible(True)
        if step.error:
            self.error_lbl.setText(f"✗ Error: {step.error}")
            self.error_lbl.setVisible(True)


class TaskTimeline(QWidget):
    """Vertical list container displaying all steps of the active workflow."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.cards: list[StepCard] = []
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Header with title & progress bar
        header = QHBoxLayout()
        title = QLabel("Execution Plan Timeline")
        title.setObjectName("sectionHeader")
        header.addWidget(title)
        header.addStretch()

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setFixedWidth(160)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background-color: #1E293B; border-radius: 4px; border: none; }
            QProgressBar::chunk { background-color: #06B6D4; border-radius: 4px; }
        """)
        header.addWidget(self.progress_bar)
        layout.addLayout(header)

        # Scrollable container for step cards
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(8)
        self.container_layout.addStretch()

        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

    def load_plan(self, plan: TaskPlan) -> None:
        """Clear previous steps and render new plan cards."""
        # Clear existing
        while self.container_layout.count() > 1:
            child = self.container_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.cards.clear()

        # Add new cards
        for i, step in enumerate(plan.steps):
            card = StepCard(step, i)
            self.cards.append(card)
            self.container_layout.insertWidget(i, card)

        self.progress_bar.setValue(0)

    def update_step(self, step: TaskStep) -> None:
        """Update the specific card for the modified step."""
        for card in self.cards:
            if card.step.step_id == step.step_id:
                card.update_step(step)
                break

        # Update progress
        total = len(self.cards)
        if total > 0:
            completed = sum(1 for c in self.cards if c.step.status == "completed")
            pct = int((completed / total) * 100)
            self.progress_bar.setValue(pct)
