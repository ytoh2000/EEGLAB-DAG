import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTreeView, QPushButton, QToolBar
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFileSystemModel, QIcon

class FileBrowserWidget(QWidget):
    cwd_requested = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Toolbar
        self.toolbar = QToolBar()
        self.toolbar.setIconSize(__import__('PyQt6.QtCore', fromlist=['QSize']).QSize(16, 16))
        
        # 'Up' Button
        self.up_action = self.toolbar.addAction("⇡ Up")
        self.up_action.setToolTip("Go up one directory")
        self.up_action.triggered.connect(self._go_up)
        
        layout.addWidget(self.toolbar)
        
        # File System Model
        self.file_model = QFileSystemModel()
        self.file_model.setRootPath("")
        
        # Tree View
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.file_model)
        
        # Hide extra columns to save space
        self.tree_view.setColumnHidden(1, True)
        self.tree_view.setColumnHidden(2, True)
        self.tree_view.setColumnHidden(3, True)
        self.tree_view.setHeaderHidden(True)
        
        # Drag and Drop settings
        self.tree_view.setDragEnabled(True)
        self.tree_view.setDragDropMode(QTreeView.DragDropMode.DragOnly)
        
        # Connect double click
        self.tree_view.doubleClicked.connect(self._on_double_click)
        
        layout.addWidget(self.tree_view)
        
        self.current_path = ""

    def set_path(self, path):
        if not path or not os.path.isdir(path):
            return
            
        self.current_path = path
        index = self.file_model.setRootPath(path)
        self.tree_view.setRootIndex(index)

    def _go_up(self):
        if not self.current_path:
            return
            
        parent_dir = os.path.dirname(self.current_path)
        if parent_dir and os.path.isdir(parent_dir):
            self.cwd_requested.emit(parent_dir)

    def _on_double_click(self, index):
        path = self.file_model.filePath(index)
        if os.path.isdir(path):
            self.cwd_requested.emit(path)
