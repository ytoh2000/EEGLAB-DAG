"""
Undo/Redo command system using Qt's QUndoStack framework.

Each user action on the canvas (add/remove node, add/remove edge, move node,
change parameters) is wrapped in a QUndoCommand. This lets the user undo and
redo actions with Ctrl+Z / Ctrl+Shift+Z.

Usage:
    # In CanvasView.__init__:
    self.undo_stack = QUndoStack(self)

    # Instead of directly adding a node:
    self.undo_stack.push(AddNodeCommand(self, node_item))
"""
from PyQt6.QtGui import QUndoCommand
from src.gui.items import NodeItem, EdgeItem


class AddNodeCommand(QUndoCommand):
    """Undoable command for adding a node to the canvas."""

    def __init__(self, canvas, node_item):
        super().__init__(f"Add {node_item.label_text}")
        self.canvas = canvas
        self.node = node_item

    def redo(self):
        self.canvas.scene.addItem(self.node)
        self.canvas.pipeline_changed.emit()

    def undo(self):
        # Remove connected edges first
        for edge in list(self.node.edges):
            self.canvas.scene.removeItem(edge)
            if edge.source_node and edge.source_node != self.node:
                edge.source_node.remove_edge(edge)
            if edge.target_node and edge.target_node != self.node:
                edge.target_node.remove_edge(edge)
        self.canvas.scene.removeItem(self.node)
        self.canvas.pipeline_changed.emit()


class RemoveNodeCommand(QUndoCommand):
    """Undoable command for removing a node (and its connected edges)."""

    def __init__(self, canvas, node_item):
        super().__init__(f"Remove {node_item.label_text}")
        self.canvas = canvas
        self.node = node_item
        # Snapshot the edges connected to this node so we can restore them
        self.removed_edges = []

    def redo(self):
        # Capture edges before removing
        self.removed_edges = list(self.node.edges)
        for edge in self.removed_edges:
            self.canvas.scene.removeItem(edge)
            if edge.source_node and edge.source_node != self.node:
                edge.source_node.remove_edge(edge)
            if edge.target_node and edge.target_node != self.node:
                edge.target_node.remove_edge(edge)
        self.node.edges = []
        self.canvas.scene.removeItem(self.node)
        self.canvas.pipeline_changed.emit()

    def undo(self):
        self.canvas.scene.addItem(self.node)
        for edge in self.removed_edges:
            self.canvas.scene.addItem(edge)
            edge.source_node.add_edge(edge)
            edge.target_node.add_edge(edge)
            edge.adjust()
        self.canvas.pipeline_changed.emit()


class AddEdgeCommand(QUndoCommand):
    """Undoable command for adding an edge between two nodes."""

    def __init__(self, canvas, edge_item):
        src = edge_item.source_node.label_text
        tgt = edge_item.target_node.label_text
        super().__init__(f"Connect {src} → {tgt}")
        self.canvas = canvas
        self.edge = edge_item

    def redo(self):
        self.canvas.scene.addItem(self.edge)
        self.edge.source_node.add_edge(self.edge)
        self.edge.target_node.add_edge(self.edge)
        self.edge.adjust()
        self.canvas.pipeline_changed.emit()

    def undo(self):
        self.edge.source_node.remove_edge(self.edge)
        self.edge.target_node.remove_edge(self.edge)
        self.canvas.scene.removeItem(self.edge)
        self.canvas.pipeline_changed.emit()


class RemoveEdgeCommand(QUndoCommand):
    """Undoable command for removing an edge."""

    def __init__(self, canvas, edge_item):
        src = edge_item.source_node.label_text
        tgt = edge_item.target_node.label_text
        super().__init__(f"Disconnect {src} → {tgt}")
        self.canvas = canvas
        self.edge = edge_item

    def redo(self):
        self.edge.source_node.remove_edge(self.edge)
        self.edge.target_node.remove_edge(self.edge)
        self.canvas.scene.removeItem(self.edge)
        self.canvas.pipeline_changed.emit()

    def undo(self):
        self.canvas.scene.addItem(self.edge)
        self.edge.source_node.add_edge(self.edge)
        self.edge.target_node.add_edge(self.edge)
        self.edge.adjust()
        self.canvas.pipeline_changed.emit()


class MoveNodeCommand(QUndoCommand):
    """Undoable command for moving a node to a new position."""

    def __init__(self, canvas, node_item, old_pos, new_pos):
        super().__init__(f"Move {node_item.label_text}")
        self.canvas = canvas
        self.node = node_item
        self.old_pos = old_pos
        self.new_pos = new_pos

    def redo(self):
        self.node.setPos(self.new_pos)
        self.canvas.pipeline_changed.emit()

    def undo(self):
        self.node.setPos(self.old_pos)
        self.canvas.pipeline_changed.emit()


class ChangeParamsCommand(QUndoCommand):
    """Undoable command for changing node parameters and/or note."""

    def __init__(self, canvas, node_item, old_params, new_params, old_note='', new_note=''):
        super().__init__(f"Edit {node_item.label_text}")
        self.canvas = canvas
        self.node = node_item
        self.old_params = dict(old_params)
        self.new_params = dict(new_params)
        self.old_note = old_note
        self.new_note = new_note

    def redo(self):
        self.node.params = dict(self.new_params)
        self.node.user_note = self.new_note
        self.node.refresh_tooltip()
        self.node.update()
        self.canvas.pipeline_changed.emit()

    def undo(self):
        self.node.params = dict(self.old_params)
        self.node.user_note = self.old_note
        self.node.refresh_tooltip()
        self.node.update()
        self.canvas.pipeline_changed.emit()
