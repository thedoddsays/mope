"""
ui/theme.py — Gray + orange visual theme for Mope (Qt port).

Applied once, globally, via app.setStyleSheet(STYLESHEET) in main.py.
Color constants are exported too so individual widgets (like player_bar's
active-state highlighting) can stay visually consistent without duplicating
hex values everywhere.
"""

# --- Palette ---------------------------------------------------------
BG_WINDOW   = "#2b2b2b"   # main window / default widget background
BG_PANEL    = "#262626"   # list/tree/table backgrounds (slightly darker)
BG_RAISED   = "#323232"   # headers, toolbars, buttons at rest
BG_HOVER    = "#3f3f3f"   # hover state for raised elements
BORDER      = "#3a3a3a"   # subtle borders/dividers
TEXT        = "#e0e0e0"   # primary text
TEXT_DIM    = "#9a9a9a"   # secondary/dim text

ORANGE       = "#ff9800"  # primary accent
ORANGE_HOVER = "#ffa726"  # lighter, for hover states
ORANGE_DARK  = "#f57c00"  # darker, for pressed states
ON_ORANGE    = "#1b1b1b"  # text/icon color when sitting on an orange fill


STYLESHEET = f"""
QWidget {{
    background-color: {BG_WINDOW};
    color: {TEXT};
}}

QMainWindow, QDialog {{
    background-color: {BG_WINDOW};
}}

QStatusBar {{
    background-color: {BG_RAISED};
    color: {TEXT_DIM};
    border-top: 1px solid {BORDER};
}}

QToolTip {{
    background-color: {BG_RAISED};
    color: {TEXT};
    border: 1px solid {ORANGE};
    padding: 3px;
}}

/* --- Splitters --- */
QSplitter::handle {{
    background-color: {BORDER};
}}
QSplitter::handle:hover {{
    background-color: {ORANGE};
}}

/* --- Buttons --- */
QPushButton {{
    background-color: {BG_RAISED};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 5px 12px;
    color: {TEXT};
}}
QPushButton:hover {{
    background-color: {BG_HOVER};
    border-color: {ORANGE};
}}
QPushButton:pressed {{
    background-color: {ORANGE_DARK};
    color: {ON_ORANGE};
}}
QPushButton:checkable:checked {{
    background-color: {ORANGE};
    color: {ON_ORANGE};
    border-color: {ORANGE};
}}

/* --- Lists / Trees / Tables --- */
QTreeView, QTableWidget, QListWidget {{
    background-color: {BG_PANEL};
    alternate-background-color: {BG_WINDOW};
    color: {TEXT};
    border: 1px solid {BORDER};
    gridline-color: {BORDER};
    selection-background-color: {ORANGE};
    selection-color: {ON_ORANGE};
}}
QTreeView::item:selected, QTableWidget::item:selected, QListWidget::item:selected {{
    background-color: {ORANGE};
    color: {ON_ORANGE};
}}
QTreeView::item:hover, QTableWidget::item:hover, QListWidget::item:hover {{
    background-color: {BG_HOVER};
}}

QHeaderView::section {{
    background-color: {BG_RAISED};
    color: {TEXT_DIM};
    padding: 4px 6px;
    border: none;
    border-right: 1px solid {BORDER};
    border-bottom: 1px solid {BORDER};
}}

/* --- Scrollbars --- */
QScrollBar:vertical, QScrollBar:horizontal {{
    background: {BG_PANEL};
    border: none;
    margin: 0;
}}
QScrollBar::handle {{
    background: {BORDER};
    border-radius: 4px;
}}
QScrollBar::handle:hover {{
    background: {ORANGE};
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    background: none;
    border: none;
    width: 0;
    height: 0;
}}

/* --- Sliders (seek/volume) --- */
QSlider::groove:horizontal {{
    height: 4px;
    background: {BORDER};
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: {ORANGE};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {ORANGE};
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}
QSlider::handle:horizontal:hover {{
    background: {ORANGE_HOVER};
}}

/* --- Menus --- */
QMenu {{
    background-color: {BG_WINDOW};
    color: {TEXT};
    border: 1px solid {BORDER};
}}
QMenu::item {{
    padding: 5px 20px;
}}
QMenu::item:selected {{
    background-color: {ORANGE};
    color: {ON_ORANGE};
}}

/* --- Inputs --- */
QLineEdit, QComboBox, QTextEdit {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 3px 5px;
    color: {TEXT};
}}
QLineEdit:focus, QComboBox:focus {{
    border-color: {ORANGE};
}}

/* --- Checkboxes --- */
QCheckBox::indicator:checked {{
    background-color: {ORANGE};
    border: 1px solid {ORANGE};
}}
"""
