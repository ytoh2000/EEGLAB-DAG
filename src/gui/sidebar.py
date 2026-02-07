from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem
from PyQt6.QtCore import Qt, QMimeData, pyqtSignal
from PyQt6.QtGui import QDrag

from src.model.library import LibraryManager

class Sidebar(QWidget):
    node_requested = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Use DraggableTreeWidget for categorized list
        self.tree = DraggableTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        layout.addWidget(self.tree)
        
        # Categories mapping: Display Name -> [internal types]
        self.categories_map = {
            "Import/Load": ["input", "io"],
            "Processing": ["process"],
            "Plotting": ["visualization"],
            "Other": [] 
        }
        
        self.refresh_items()
        
    def refresh_items(self):
        self.tree.clear()
        
        # We'll build categories dynamically based on what's in the library
        # plus a fixed order for known main menus
        known_menus = ["File", "Edit", "Tools", "Plot"]
        self.category_items = {}
        
        # Helper to get or create root
        def get_root(name):
            if name not in self.category_items:
                root = QTreeWidgetItem(self.tree)
                root.setText(0, name)
                font = root.font(0)
                font.setBold(True)
                root.setFont(0, font)
                self.category_items[name] = root
            return self.category_items[name]

        # Pre-create known menus in order
        for menu in known_menus:
            get_root(menu)
            
        library = LibraryManager.instance()
        steps = library.get_all_steps()
        
        # Sort by name
        steps.sort(key=lambda x: x.get('name', ''))
        
        for step in steps:
            # Use 'category' field if present, otherwise 'Other'
            category = step.get('category', 'Other')
            
            parent_item = get_root(category)
            
            item = QTreeWidgetItem(parent_item)
            item.setText(0, step['name'])
            item.setData(0, Qt.ItemDataRole.UserRole, step)
            item.setToolTip(0, step.get('description', ''))
        
        # Remove empty roots if we pre-created them but didn't use them (optional, 
        # but cleaner to keep them if we want to show structure, or remove if empty. 
        # Let's remove empty ones for cleanliness)
        roots_to_remove = []
        for i in range(self.tree.topLevelItemCount()):
            root = self.tree.topLevelItem(i)
            if root.childCount() == 0:
                roots_to_remove.append(root)
        for root in roots_to_remove:
            # Safe removal? 
            # simplest way is to rebuild logic to only create if used, 
            # or just iterate and take from dict. 
            # Actually, standardizing order is nice.
            pass

        self.tree.expandAll()

    def on_item_double_clicked(self, item, column):
        # Only handle leaf nodes (definitions)
        step_def = item.data(0, Qt.ItemDataRole.UserRole)
        if step_def:
            self.node_requested.emit(step_def)

class DraggableTreeWidget(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setDragDropMode(QTreeWidget.DragDropMode.DragOnly)

    def startDrag(self, supportedActions):
        item = self.currentItem()
        if not item:
            return
            
        # Only allow dragging leaf nodes (those with step definitions)
        # Checking if it has user data is a good way
        step_def = item.data(0, Qt.ItemDataRole.UserRole)
        if not step_def:
            return
            
        mime_data = QMimeData()
        name = item.text(0)
        mime_data.setText(name)
        
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec(Qt.DropAction.CopyAction)
