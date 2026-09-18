"""
ui/widgets.py — Small shared widget helpers for Mope's Qt UI.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QLabel, QTableWidgetItem


class ElidedLabel(QLabel):
    """A QLabel that ellipsizes its text with '…' when too narrow to fit,
    mirroring GTK's Pango ellipsize behaviour used throughout the original."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self._full_text = text
        super().setText(text)

    def setText(self, text: str):
        self._full_text = text or ""
        self._apply_elision()

    def text(self) -> str:
        return self._full_text

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_elision()

    def _apply_elision(self):
        metrics = QFontMetrics(self.font())
        elided = metrics.elidedText(self._full_text, Qt.TextElideMode.ElideRight, self.width())
        super().setText(elided)


class NumericTableWidgetItem(QTableWidgetItem):
    """A QTableWidgetItem that sorts numerically by a stored raw value
    instead of alphabetically by displayed text (e.g. so '2:05' sorts
    after '1:59', and so track numbers sort as numbers not strings)."""

    def __init__(self, display_text: str, raw_value: float):
        super().__init__(display_text)
        self._raw_value = raw_value

    def __lt__(self, other):
        if isinstance(other, NumericTableWidgetItem):
            return self._raw_value < other._raw_value
        return super().__lt__(other)
