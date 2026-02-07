from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPathItem, QMenu
from PyQt6.QtCore import Qt, QPointF, pyqtSignal, QUrl
from PyQt6.QtGui import QPainter, QPen, QColor, QPainterPath, QAction, QDesktopServices
from src.gui.items import NodeItem, EdgeItem
from src.gui.properties import PropertiesDialog
from src.model.pipeline import Pipeline, NodeData, EdgeData
from src.model.library import LibraryManager
import uuid

class CanvasView(QGraphicsView):
    pipeline_changed = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        
        # Visual settings
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setSceneRect(-2000, -2000, 4000, 4000)
        self.setBackgroundBrush(Qt.GlobalColor.white)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setAcceptDrops(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # Connection state
        # Connection state
        self.connecting_node = None
        self.start_port_type = None
        self.temp_line = QGraphicsPathItem()
        self.temp_line.setPen(QPen(Qt.GlobalColor.black, 2, Qt.PenStyle.DashLine))
        self.scene.addItem(self.temp_line)
        self.temp_line.hide()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.pos())
            if isinstance(item, NodeItem):
                # Check for port
                pos_in_item = item.mapFromScene(self.mapToScene(event.pos()))
                port = item.get_port_at(pos_in_item)
                
                if port:
                    self.connecting_node = item
                    self.start_port_type = port
                    self.temp_line.show()
                    self.update_temp_line(self.mapToScene(event.pos()))
                    return # Don't pass to item (which would select/move)
        
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.connecting_node:
            mouse_pos = self.mapToScene(event.pos())
            snap_pos, _ = self.get_snapped_port(mouse_pos)
            self.update_temp_line(snap_pos if snap_pos else mouse_pos)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.connecting_node:
            mouse_pos = self.mapToScene(event.pos())
            snap_pos, target_node = self.get_snapped_port(mouse_pos)
            
            if target_node and target_node != self.connecting_node:
                # Determine source and target based on direction
                if self.start_port_type == 'output':
                    source, target = self.connecting_node, target_node
                else:
                    source, target = target_node, self.connecting_node
                
                edge = EdgeItem(source, target)
                self.scene.addItem(edge)
                self.pipeline_changed.emit()
            
            # Reset state
            self.connecting_node = None
            self.start_port_type = None
            self.temp_line.hide()
        
        super().mouseReleaseEvent(event)
        
        # If we weren't connecting, we might have moved a node. 
        # A simple heuristic: if there are selected items, assume a change occurred on release.
        # This might over-emit (e.g. just selecting), but safer for tracking changes.
        if not self.connecting_node and self.scene.selectedItems():
            self.pipeline_changed.emit()
        
    def mouseDoubleClickEvent(self, event):
        item = self.itemAt(event.pos())
        if isinstance(item, NodeItem):
            self.open_properties(item)
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        if isinstance(item, NodeItem):
            menu = QMenu(self)
            
            # Actions
            action_props = QAction("Properties", self)
            action_props.triggered.connect(lambda: self.open_properties(item))
            menu.addAction(action_props)
            
            # Documentation
            github_url = item.step_def.get('github_url')
            if github_url:
                action_docs = QAction("Documentation (GitHub)", self)
                action_docs.triggered.connect(lambda: self.open_url(github_url))
                menu.addAction(action_docs)
            
            menu.addSeparator()
            
            action_remove = QAction("Remove", self)
            action_remove.triggered.connect(lambda: self.remove_node(item))
            menu.addAction(action_remove)
            
            menu.exec(event.globalPos())
        elif isinstance(item, EdgeItem):
            menu = QMenu(self)
            action_remove = QAction("Remove Edge", self)
            action_remove.triggered.connect(lambda: self.remove_edge(item))
            menu.addAction(action_remove)
            menu.exec(event.globalPos())
        else:
            super().contextMenuEvent(event)

    def open_properties(self, item):
        dialog = PropertiesDialog(item.label_text, item.params, item.step_def, self)
        if dialog.exec():
            item.params = dialog.get_params()
            self.pipeline_changed.emit()

    def open_url(self, url):
        QDesktopServices.openUrl(QUrl(url))
        
    def remove_node(self, node):
        # Remove connected edges
        for item in self.scene.items():
            if isinstance(item, EdgeItem):
                if item.source_node == node or item.target_node == node:
                    self.remove_edge(item)
        
        self.scene.removeItem(node)
        self.pipeline_changed.emit()

    def remove_edge(self, edge):
        if edge.source_node:
            edge.source_node.remove_edge(edge)
        if edge.target_node:
            edge.target_node.remove_edge(edge)
        self.scene.removeItem(edge)
        self.pipeline_changed.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            self.remove_selected_items()
        else:
            super().keyPressEvent(event)

    def remove_selected_items(self):
        # Collect nodes and edges to remove
        items_to_remove = self.scene.selectedItems()
        
        # Separate edges and nodes. Remove edges first? 
        # Actually it's safer to just iterate and remove.
        # But removing a node will automatically remove its edges if we use remove_node logic.
        # However, selectedItems() returns edges too if they are selected.
        
        # Strategy: 
        # 1. Explicitly remove selected edges first.
        # 2. Then remove selected nodes (which handles their connected edges).
        
        items_done = set()
        
        # Filter for Edges
        selected_edges = [i for i in items_to_remove if isinstance(i, EdgeItem)]
        for edge in selected_edges:
            if edge not in items_done:
                self.remove_edge(edge)
                items_done.add(edge)
                
        # Filter for Nodes
        selected_nodes = [i for i in items_to_remove if isinstance(i, NodeItem)]
        for node in selected_nodes:
            if node not in items_done:
                self.remove_node(node)
                items_done.add(node)
                
        if items_done:
            self.pipeline_changed.emit()

    def update_temp_line(self, target_pos):
        if not self.connecting_node:
            return
            
        if self.start_port_type == 'output':
            start_pos = self.connecting_node.mapToScene(self.connecting_node.output_port)
        else:
            start_pos = self.connecting_node.mapToScene(self.connecting_node.input_port)
            
        path = QPainterPath()
        path.moveTo(start_pos)
        path.lineTo(target_pos)
        self.temp_line.setPath(path)
        
    def get_snapped_port(self, mouse_pos):
        SNAP_DISTANCE = 20
        target_port_type = 'input' if self.start_port_type == 'output' else 'output'
        
        for item in self.scene.items():
            if isinstance(item, NodeItem) and item != self.connecting_node:
                # Calculate port position in scene coords
                port_local = item.input_port if target_port_type == 'input' else item.output_port
                port_scene = item.mapToScene(port_local)
                
                dist = (mouse_pos - port_scene).manhattanLength()
                if dist < SNAP_DISTANCE:
                    return port_scene, item
        return None, None
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        if event.mimeData().hasText():
            node_name = event.mimeData().text()
            pos = self.mapToScene(event.position().toPoint())
            
            # Look up definition
            library = LibraryManager.instance()
            step_def = library.get_step(node_name)
            
            node_id = str(uuid.uuid4())
            node = NodeItem(node_id, label=node_name, x=pos.x(), y=pos.y(), step_def=step_def)
            
            # Initialize params with defaults from definition
            if step_def and 'inputs' in step_def:
                for inp in step_def['inputs']:
                    if 'default' in inp:
                        node.params[inp['name']] = inp['default']
                    else:
                        node.params[inp['name']] = None # Or appropriate empty value type
                        
            self.scene.addItem(node)
            self.pipeline_changed.emit()
            event.accept()

    def add_node_from_def(self, step_def):
        if not step_def:
            return
            
        node_name = step_def.get('name', 'Unknown')
        
        # Place at center of view
        center_point = self.mapToScene(self.viewport().rect().center())
        
        # Add some random offset so they don't stack perfectly
        import random
        offset_x = random.randint(-20, 20)
        offset_y = random.randint(-20, 20)
        
        node_id = str(uuid.uuid4())
        node = NodeItem(node_id, label=node_name, x=center_point.x() + offset_x, y=center_point.y() + offset_y, step_def=step_def)
        
        # Initialize params with defaults from definition
        if 'inputs' in step_def:
            for inp in step_def['inputs']:
                if 'default' in inp:
                    node.params[inp['name']] = inp['default']
                else:
                    node.params[inp['name']] = None 
                    
        self.scene.addItem(node)
        self.pipeline_changed.emit()

    def to_pipeline(self):
        pipeline = Pipeline()
        node_map = {} # map id to NodeItem
        
        # Collect nodes
        for item in self.scene.items():
            if isinstance(item, NodeItem):
                # Ensure we pass the correct type from the item/definition
                node_type = item.step_def.get('type', 'process')
                node_data = NodeData(item.node_id, node_type, item.label_text, (item.x(), item.y()), item.params)
                pipeline.add_node(node_data)
                node_map[item.node_id] = item
                
        # Collect edges
        for item in self.scene.items():
            if isinstance(item, EdgeItem):
                edge_data = EdgeData(item.source_node.node_id, item.target_node.node_id)
                pipeline.add_edge(edge_data)
                
        return pipeline
        
    def from_pipeline(self, pipeline):
        self.scene.clear()
        # Add temp line back
        self.temp_line = QGraphicsPathItem()
        self.temp_line.setPen(QPen(Qt.GlobalColor.black, 2, Qt.PenStyle.DashLine))
        self.scene.addItem(self.temp_line)
        self.temp_line.hide()
        
        node_db = {} # id -> NodeItem
        
        # Create Nodes
        for node_data in pipeline.nodes:
            # Look up definition
            library = LibraryManager.instance()
            step_def = library.get_step(node_data.label)
            
            item = NodeItem(node_data.id, node_data.label, node_data.pos[0], node_data.pos[1], step_def=step_def)
            item.params = node_data.params
            self.scene.addItem(item)
            node_db[node_data.id] = item
            
        # Create Edges
        for edge_data in pipeline.edges:
            source = node_db.get(edge_data.source)
            target = node_db.get(edge_data.target)
            if source and target:
                edge = EdgeItem(source, target)
                self.scene.addItem(edge)
