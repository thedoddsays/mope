"""
ui/breadcrumb_bar.py — Clickable breadcrumb trail for folder navigation.

Shows a path like "Music › Bad Religion › Recipe for Hate", relative to
the current library root, with each non-leaf segment clickable to jump
back up to that folder. Long paths truncate with "..." in the middle
rather than overflowing the window.
"""

from pathlib import Path

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel

from ui.widgets import ClickableLabel
from ui.theme import ORANGE, TEXT_DIM

MAX_SEGMENTS = 4   # show at most this many trailing segments before truncating


class BreadcrumbBar(QWidget):
    """A row of path segments; non-leaf ones are clickable."""

    def __init__(self):
        super().__init__()

        # Callback: function(path: str), called when a segment is clicked
        self.on_segment_clicked = None

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(8, 6, 8, 6)
        self._layout.setSpacing(4)
        self._layout.addStretch(1)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_path(self, root: str, full_path: str):
        """Show a breadcrumb trail from root down to full_path."""
        self._clear()

        root = (root or "").rstrip("/")
        full_path = (full_path or "").rstrip("/")

        if not root or not full_path.startswith(root):
            # Fallback: root unknown or path doesn't live under it —
            # just show the leaf folder name, non-clickable.
            self._add_segment(Path(full_path).name or full_path, None, is_last=True)
            self._layout.addStretch(1)
            return

        rel = full_path[len(root):].strip("/")
        segments = [Path(root).name or root]
        if rel:
            segments += [p for p in rel.split("/") if p]

        # Cumulative absolute path for each segment, for click targets
        cum_paths = [root]
        cur = root
        for seg in segments[1:]:
            cur = cur + "/" + seg
            cum_paths.append(cur)

        pairs = list(zip(segments, cum_paths))
        truncated = len(pairs) > MAX_SEGMENTS
        if truncated:
            pairs = pairs[:1] + pairs[-(MAX_SEGMENTS - 1):]

        for i, (name, path) in enumerate(pairs):
            if truncated and i == 1:
                self._add_ellipsis()
            is_last = (i == len(pairs) - 1)
            self._add_segment(name, path, is_last=is_last)
            if not is_last:
                self._add_separator()

        self._layout.addStretch(1)

    def set_plain_text(self, text: str):
        """Show plain, non-clickable text (used for playlists, which
        don't correspond to a real folder path)."""
        self._clear()
        self._add_segment(text, None, is_last=True)
        self._layout.addStretch(1)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _clear(self):
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _add_segment(self, text: str, path, is_last: bool):
        if path and not is_last:
            lbl = ClickableLabel(text)
            lbl.setStyleSheet(f"color: {ORANGE};")
            lbl.clicked.connect(lambda p=path: self._on_click(p))
        else:
            lbl = QLabel(text)
            f = lbl.font()
            f.setBold(is_last)
            lbl.setFont(f)
        self._layout.addWidget(lbl)

    def _add_separator(self):
        sep = QLabel("\u203a")
        sep.setStyleSheet(f"color: {TEXT_DIM};")
        self._layout.addWidget(sep)

    def _add_ellipsis(self):
        lbl = QLabel("...")
        lbl.setStyleSheet(f"color: {TEXT_DIM};")
        self._layout.addWidget(lbl)
        self._add_separator()

    def _on_click(self, path: str):
        if self.on_segment_clicked:
            self.on_segment_clicked(path)
