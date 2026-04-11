"""
Application theme manager. (Light mode only)

Usage:
    from src.gui.theme import ThemeManager
    ThemeManager.apply(app)
"""
from PyQt6.QtWidgets import QApplication

LIGHT_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #f5f5f5;
    color: #333333;
    font-family: "Segoe UI", "Roboto", "Arial", sans-serif;
    font-size: 13px;
}
QToolBar {
    background-color: #e0e0e0;
    border-bottom: 1px solid #cccccc;
    spacing: 4px;
    padding: 2px;
}
QToolBar QToolButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 4px 8px;
    min-width: 36px;
}
QToolBar QToolButton:hover {
    background-color: #d0d0d0;
    border: 1px solid #bbbbbb;
}
QSplitter::handle {
    background-color: #cccccc;
    width: 2px;
}
QLineEdit {
    background-color: #ffffff;
    border: 1px solid #cccccc;
    border-radius: 3px;
    padding: 3px 6px;
}
QPushButton {
    background-color: #e8e8e8;
    border: 1px solid #cccccc;
    border-radius: 4px;
    padding: 4px 12px;
}
QPushButton:hover {
    background-color: #d8d8d8;
}
QPushButton:pressed {
    background-color: #c8c8c8;
}
QComboBox {
    background-color: #ffffff;
    border: 1px solid #cccccc;
    border-radius: 3px;
    padding: 3px 6px;
}
QTextEdit {
    background-color: #ffffff;
    border: 1px solid #cccccc;
    border-radius: 3px;
}
QLabel {
    background: transparent;
}
QTreeWidget, QTreeView {
    background-color: #ffffff;
    border: 1px solid #cccccc;
    color: #333333;
}
Sidebar {
    min-width: 200px;
}
QTreeWidget::item:hover {
    background-color: #e8e8e8;
}
QTreeWidget::item:selected {
    background-color: #d0d0d0;
    color: #333333;
}
QHeaderView::section {
    background-color: #e0e0e0;
    border: 1px solid #cccccc;
    padding: 3px;
}
QTabWidget::pane {
    border: 1px solid #cccccc;
    background-color: #f5f5f5;
}
QTabBar::tab {
    background-color: #e0e0e0;
    border: 1px solid #cccccc;
    padding: 4px 12px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #f5f5f5;
    border-bottom-color: #f5f5f5;
}
QTabBar::tab:hover {
    background-color: #d8d8d8;
}
QToolBar QToolButton::text {
    padding-left: 4px;
}
"""

class ThemeManager:
    @classmethod
    def apply(cls, app: QApplication):
        app.setStyleSheet(LIGHT_STYLESHEET)

    @classmethod
    def current(cls):
        return 'light'
