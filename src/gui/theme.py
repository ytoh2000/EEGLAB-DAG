"""
Application theme manager with Light and Dark mode stylesheets.

Usage:
    from src.gui.theme import ThemeManager
    ThemeManager.apply(app, 'dark')
"""
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt


LIGHT_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #f5f5f5;
    color: #333333;
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
    padding: 4px;
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
"""

DARK_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #2b2b2b;
    color: #e0e0e0;
}
QToolBar {
    background-color: #333333;
    border-bottom: 1px solid #444444;
    spacing: 4px;
    padding: 2px;
}
QToolBar QToolButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 4px;
    color: #e0e0e0;
}
QToolBar QToolButton:hover {
    background-color: #444444;
    border: 1px solid #555555;
}
QSplitter::handle {
    background-color: #444444;
    width: 2px;
}
QLineEdit {
    background-color: #3c3c3c;
    border: 1px solid #555555;
    border-radius: 3px;
    padding: 3px 6px;
    color: #e0e0e0;
}
QPushButton {
    background-color: #3c3c3c;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 4px 12px;
    color: #e0e0e0;
}
QPushButton:hover {
    background-color: #4a4a4a;
}
QPushButton:pressed {
    background-color: #555555;
}
QComboBox {
    background-color: #3c3c3c;
    border: 1px solid #555555;
    border-radius: 3px;
    padding: 3px 6px;
    color: #e0e0e0;
}
QComboBox QAbstractItemView {
    background-color: #3c3c3c;
    color: #e0e0e0;
    selection-background-color: #555555;
}
QTextEdit {
    background-color: #3c3c3c;
    border: 1px solid #555555;
    border-radius: 3px;
    color: #e0e0e0;
}
QLabel {
    background: transparent;
    color: #e0e0e0;
}
QDialog {
    background-color: #2b2b2b;
    color: #e0e0e0;
}
QCheckBox {
    color: #e0e0e0;
}
QMessageBox {
    background-color: #2b2b2b;
    color: #e0e0e0;
}
QFrame {
    border-color: #555555;
}
"""


class ThemeManager:
    _current = 'light'

    @classmethod
    def apply(cls, app: QApplication, theme: str):
        cls._current = theme
        if theme == 'dark':
            app.setStyleSheet(DARK_STYLESHEET)
        else:
            app.setStyleSheet(LIGHT_STYLESHEET)

    @classmethod
    def current(cls):
        return cls._current

    @classmethod
    def toggle(cls, app: QApplication):
        new_theme = 'dark' if cls._current == 'light' else 'light'
        cls.apply(app, new_theme)
        return new_theme
