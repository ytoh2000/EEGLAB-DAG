from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPathItem, QMenu
from PyQt6.QtCore import Qt, QPointF, pyqtSignal, QUrl
from PyQt6.QtGui import QPainter, QPen, QColor, QPainterPath, QAction, QDesktopServices, QUndoStack
from src.gui.items import NodeItem, EdgeItem
from src.gui.properties import PropertiesDialog
from src.gui.undo import AddNodeCommand, RemoveNodeCommand, AddEdgeCommand, RemoveEdgeCommand, MoveNodeCommand, ChangeParamsCommand
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
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        
        # Zoom state
        self._zoom_factor = 1.0
        
        # Connection state
        self.connecting_node = None
        self.start_port_type = None
        self.temp_line = QGraphicsPathItem()
        self.temp_line.setPen(QPen(Qt.GlobalColor.black, 2, Qt.PenStyle.DashLine))
        self.scene.addItem(self.temp_line)
        self.temp_line.hide()
        
        # Undo/Redo
        self.undo_stack = QUndoStack(self)
        
        # Move tracking (for undo)
        self._drag_start_positions = {}
        # Insert-on-edge tracking
        self._dragging_insert_candidate = None  # NodeItem being dragged that could insert
        self._hovered_edge = None  # EdgeItem currently highlighted

    def mousePressEvent(self, event):
        # Middle-button pan
        if event.button() == Qt.MouseButton.MiddleButton:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            fake_event = event.__class__(event.type(), event.localPos(), event.globalPos(),
                                         Qt.MouseButton.LeftButton, event.buttons(),
                                         event.modifiers())
            super().mousePressEvent(fake_event)
            return
        
        if event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.pos())
            
            # Check all items at this position — not just the topmost —
            # so clicking near the edge of a node still counts as "on the node"
            scene_pos = self.mapToScene(event.pos())
            items_at_pos = self.scene.items(scene_pos)
            has_node = any(isinstance(i, NodeItem) for i in items_at_pos)
            has_edge = any(isinstance(i, EdgeItem) for i in items_at_pos)
            
            if isinstance(item, NodeItem):
                # Check for port
                pos_in_item = item.mapFromScene(scene_pos)
                port = item.get_port_at(pos_in_item)
                
                if port:
                    self.connecting_node = item
                    self.start_port_type = port
                    self.temp_line.show()
                    self.update_temp_line(scene_pos)
                    return
            elif not has_node and not has_edge:
                # Strictly empty canvas — no nodes or edges at click position
                self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
                super().mousePressEvent(event)
                return
            
            # Capture start positions BEFORE super (which may change positions)
            self._drag_start_positions = {}
            self._dragging_insert_candidate = None
        
        super().mousePressEvent(event)
        
        # After super() — selection is now finalized
        if event.button() == Qt.MouseButton.LeftButton and not self.connecting_node:
            # Rebuild drag start positions from actual selection
            self._drag_start_positions = {}
            for sel in self.scene.selectedItems():
                if isinstance(sel, NodeItem):
                    self._drag_start_positions[sel] = sel.pos()
            
            # If dragging a single unconnected node with both ports, shrink + fade it
            if len(self._drag_start_positions) == 1:
                node = list(self._drag_start_positions.keys())[0]
                if node.has_input and node.has_output and not node.edges:
                    node.setScale(0.7)
                    node.setOpacity(0.2)
                    self._dragging_insert_candidate = node

    def mouseMoveEvent(self, event):
        if self.connecting_node:
            mouse_pos = self.mapToScene(event.pos())
            snap_pos, _ = self.get_snapped_port(mouse_pos)
            self.update_temp_line(snap_pos if snap_pos else mouse_pos)
        else:
            super().mouseMoveEvent(event)
            
            # Edge hover detection for insert-on-edge (use cursor, not node center)
            if self._dragging_insert_candidate:
                node = self._dragging_insert_candidate
                cursor_scene = self.mapToScene(event.pos())
                found_edge = None
                for item in self.scene.items():
                    if isinstance(item, EdgeItem) and item.source_node != node and item.target_node != node:
                        local_pt = item.mapFromScene(cursor_scene)
                        if item.shape().contains(local_pt):
                            found_edge = item
                            break
                
                # Update highlight state
                if found_edge != self._hovered_edge:
                    if self._hovered_edge:
                        self._hovered_edge._insert_hover = False
                        self._hovered_edge.update()
                    if found_edge:
                        found_edge._insert_hover = True
                        found_edge.update()
                    self._hovered_edge = found_edge

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
                
                # Create edge — constructor registers with source/target nodes.
                # Undo the registrations so AddEdgeCommand.redo() can cleanly add it.
                edge = EdgeItem(source, target)
                source.remove_edge(edge)
                target.remove_edge(edge)
                self.undo_stack.push(AddEdgeCommand(self, edge))
            
            # Reset state
            self.connecting_node = None
            self.start_port_type = None
            self.temp_line.hide()
        
        # Reset drag mode for left-click canvas pan
        if event.button() in (Qt.MouseButton.MiddleButton, Qt.MouseButton.LeftButton):
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
        
        super().mouseReleaseEvent(event)
        
        # Capture cursor position for insertion check before clearing state
        cursor_scene_pos = self.mapToScene(event.pos()) if event.button() == Qt.MouseButton.LeftButton else None
        
        # Restore node scale/opacity and clear edge highlights
        if self._dragging_insert_candidate:
            self._dragging_insert_candidate.setScale(1.0)
            self._dragging_insert_candidate.setOpacity(1.0)
            self._dragging_insert_candidate = None
        if self._hovered_edge:
            self._hovered_edge._insert_hover = False
            self._hovered_edge.update()
            self._hovered_edge = None
        
        # Check if any selected nodes were moved (compare to captured start positions)
        if self._drag_start_positions:
            moved_nodes = []
            for node, old_pos in self._drag_start_positions.items():
                new_pos = node.pos()
                if old_pos != new_pos:
                    moved_nodes.append((node, old_pos, new_pos))
            
            # Single node moved — check for edge insertion
            if len(moved_nodes) == 1:
                node, old_pos, new_pos = moved_nodes[0]
                inserted = self._try_insert_on_edge(node, old_pos, new_pos, cursor_scene_pos)
                if not inserted:
                    self.undo_stack.push(MoveNodeCommand(self, node, old_pos, new_pos))
            else:
                for node, old_pos, new_pos in moved_nodes:
                    self.undo_stack.push(MoveNodeCommand(self, node, old_pos, new_pos))
            
            self._drag_start_positions = {}

    def _try_insert_on_edge(self, node, old_pos, new_pos, cursor_pos=None):
        """If `node` was dropped on an existing edge, split that edge and insert the node.
        Uses cursor_pos (mouse release position) for hit detection.
        Returns True if insertion happened, False otherwise."""
        # Only insert nodes that have both input and output ports
        if not (node.has_input and node.has_output):
            return False
        
        # Don't insert if node is already connected
        if node.edges:
            return False
        
        # Use cursor position for edge hit test (falls back to node center)
        if cursor_pos is None:
            cursor_pos = QPointF(new_pos.x() + node.width / 2, new_pos.y() + node.height / 2)
        
        for item in self.scene.items():
            if not isinstance(item, EdgeItem):
                continue
            if item.source_node == node or item.target_node == node:
                continue
            local_pt = item.mapFromScene(cursor_pos)
            if item.shape().contains(local_pt):
                # Found an edge to split!
                original_source = item.source_node
                original_target = item.target_node
                
                # Build the two new edges (unregistered, commands will register them)
                edge_a = EdgeItem(original_source, node)
                original_source.remove_edge(edge_a)
                node.remove_edge(edge_a)
                
                edge_b = EdgeItem(node, original_target)
                node.remove_edge(edge_b)
                original_target.remove_edge(edge_b)
                
                # Calculate spacing: push source left and target right by 80px
                SPACING = 80
                src_old_pos = original_source.pos()
                tgt_old_pos = original_target.pos()
                src_new_pos = QPointF(src_old_pos.x() - SPACING, src_old_pos.y())
                tgt_new_pos = QPointF(tgt_old_pos.x() + SPACING, tgt_old_pos.y())
                
                # Batch as a single undo macro
                self.undo_stack.beginMacro("Insert Node on Edge")
                self.undo_stack.push(MoveNodeCommand(self, node, old_pos, new_pos))
                self.undo_stack.push(RemoveEdgeCommand(self, item))
                self.undo_stack.push(AddEdgeCommand(self, edge_a))
                self.undo_stack.push(AddEdgeCommand(self, edge_b))
                self.undo_stack.push(MoveNodeCommand(self, original_source, src_old_pos, src_new_pos))
                self.undo_stack.push(MoveNodeCommand(self, original_target, tgt_old_pos, tgt_new_pos))
                self.undo_stack.endMacro()
                return True
        
        return False

    def wheelEvent(self, event):
        """Ctrl+Scroll to zoom in/out."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                factor = 1.15
            else:
                factor = 1 / 1.15
            
            new_zoom = self._zoom_factor * factor
            # Clamp to reasonable range
            if 0.1 <= new_zoom <= 5.0:
                self._zoom_factor = new_zoom
                self.scale(factor, factor)
        else:
            super().wheelEvent(event)

    def fit_to_view(self):
        """Fit all scene content into the current viewport."""
        items = [i for i in self.scene.items() if isinstance(i, (NodeItem, EdgeItem))]
        if not items:
            return
        rect = self.scene.itemsBoundingRect().adjusted(-50, -50, 50, 50)
        self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
        # Update zoom factor to match the new transform
        self._zoom_factor = self.transform().m11()

    def reset_zoom(self):
        """Reset zoom to 1:1."""
        self.resetTransform()
        self._zoom_factor = 1.0
        
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
        old_params = dict(item.params)
        old_note = item.user_note
        dialog = PropertiesDialog(item.label_text, item.params, item.step_def, self, user_note=item.user_note)
        if dialog.exec():
            new_params = dialog.get_params()
            new_note = dialog.note_edit.toPlainText()
            if new_params != old_params or new_note != old_note:
                self.undo_stack.push(ChangeParamsCommand(self, item, old_params, new_params, old_note, new_note))

    def open_url(self, url):
        QDesktopServices.openUrl(QUrl(url))
        
    def remove_node(self, node):
        self.undo_stack.push(RemoveNodeCommand(self, node))

    def remove_edge(self, edge):
        self.undo_stack.push(RemoveEdgeCommand(self, edge))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            self.remove_selected_items()
        else:
            super().keyPressEvent(event)

    def remove_selected_items(self):
        items_to_remove = self.scene.selectedItems()
        if not items_to_remove:
            return
        
        # Use a macro to group all removals into a single undo step
        self.undo_stack.beginMacro("Remove Selected")
        
        # Remove edges first, then nodes
        for item in items_to_remove:
            if isinstance(item, EdgeItem):
                self.undo_stack.push(RemoveEdgeCommand(self, item))
        for item in items_to_remove:
            if isinstance(item, NodeItem):
                self.undo_stack.push(RemoveNodeCommand(self, item))
        
        self.undo_stack.endMacro()

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
        SNAP_DISTANCE = 45
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
                        node.params[inp['name']] = None
            
            # Remove from scene since AddNodeCommand.redo() will add it
            self.undo_stack.push(AddNodeCommand(self, node))
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
        
        self.undo_stack.push(AddNodeCommand(self, node))

    def to_pipeline(self):
        pipeline = Pipeline()
        node_map = {} # map id to NodeItem
        
        # Collect nodes
        for item in self.scene.items():
            if isinstance(item, NodeItem):
                # Store the function identifier directly on NodeData
                node_type = item.step_def.get('type', 'process')
                node_function = item.function_name
                node_data = NodeData(item.node_id, node_type, item.label_text, (item.x(), item.y()), item.params, function=node_function, note=item.user_note)
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
            # Look up definition by function name first, fall back to label for
            # backward compatibility with pipeline files saved before function was added.
            library = LibraryManager.instance()
            step_def = library.get_step_by_function(node_data.function) if node_data.function else None
            if not step_def:
                step_def = library.get_step(node_data.label)
            
            item = NodeItem(node_data.id, node_data.label, node_data.pos[0], node_data.pos[1], step_def=step_def)
            item.params = node_data.params
            item.user_note = node_data.note
            self.scene.addItem(item)
            node_db[node_data.id] = item
            
        # Create Edges
        for edge_data in pipeline.edges:
            source = node_db.get(edge_data.source)
            target = node_db.get(edge_data.target)
            if source and target:
                edge = EdgeItem(source, target)
                self.scene.addItem(edge)
