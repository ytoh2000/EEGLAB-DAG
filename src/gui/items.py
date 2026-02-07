from PyQt6.QtWidgets import QGraphicsItem, QGraphicsPathItem, QGraphicsRectItem, QGraphicsTextItem
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPen, QBrush, QPainter, QPainterPath, QColor, QFont

class NodeItem(QGraphicsItem):
    def __init__(self, node_id, label="Node", x=0, y=0, step_def=None):
        super().__init__()
        self.node_id = node_id
        self.label_text = label
        self.step_def = step_def or {}
        
        self.width = 150
        self.height = 60
        self.radius = 10
        self.port_radius = 6
        
        # Data & Edges (Must init before setPos, which triggers itemChange)
        self.params = {}
        self.edges = []
        
        # Flags
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        
        self.setPos(x, y)
        
        # Ports
        self.input_port = QPointF(0, self.height / 2)
        self.output_port = QPointF(self.width, self.height / 2)
        
        # Determine port visibility
        self.step_type = self.step_def.get('type', 'process')
        self.has_input = self.step_type != 'input'
        self.has_output = self.step_type != 'output'

    def boundingRect(self):
        # Allow sufficient padding for the ports (radius 30)
        padding = 30
        return QRectF(-padding, 0, self.width + 2*padding, self.height)
        
    def shape(self):
        # Define the exact hit shape: Body + Ports
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width, self.height, self.radius, self.radius)
        
        # Add port hit areas
        hit_radius = 30
        if self.has_input:
            path.addEllipse(self.input_port, hit_radius, hit_radius)
        if self.has_output:
            path.addEllipse(self.output_port, hit_radius, hit_radius)
        
        return path
        
    def paint(self, painter, option, widget):
        # Body
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width, self.height, self.radius, self.radius)
        
        # Selection highlight
        if self.isSelected():
            painter.setPen(QPen(QColor("#ff9900"), 2))
            painter.setBrush(QBrush(QColor("#f0f0f0")))
        else:
            painter.setPen(QPen(Qt.GlobalColor.black, 1))
            painter.setBrush(QBrush(QColor("#ffffff")))
            
        painter.drawPath(path)
        
        # Label
        painter.setPen(Qt.GlobalColor.black)
        painter.setFont(QFont("Arial", 10))
        painter.drawText(self.boundingRect(), Qt.AlignmentFlag.AlignCenter, self.label_text)
        
        # Ports
        painter.setBrush(QBrush(Qt.GlobalColor.black))
        if self.has_input:
            painter.drawEllipse(self.input_port, self.port_radius, self.port_radius)
        if self.has_output:
            painter.drawEllipse(self.output_port, self.port_radius, self.port_radius)

    def get_port_at(self, pos):
        # pos is in item coordinates
        # Use a larger hit radius (e.g., 30) than the visual radius (6) for easier clicking
        HIT_RADIUS = 30
        if self.has_input:
            if (pos - self.input_port).manhattanLength() < HIT_RADIUS:
                return 'input'
        if self.has_output:
            if (pos - self.output_port).manhattanLength() < HIT_RADIUS:
                return 'output'
        return None

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for edge in self.edges:
                edge.adjust()
        return super().itemChange(change, value)
    
    def add_edge(self, edge):
        self.edges.append(edge)

    def remove_edge(self, edge):
        if edge in self.edges:
            self.edges.remove(edge)

class EdgeItem(QGraphicsPathItem):
    def __init__(self, source_node, target_node):
        super().__init__()
        self.source_node = source_node
        self.target_node = target_node
        
        self.source_node.add_edge(self)
        self.target_node.add_edge(self)
        
        self.setZValue(-1) # Send to back
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        
        pen = QPen(QColor("#333333"), 2)
        self.setPen(pen)
        
        self.adjust()
        
    def adjust(self):
        if not self.source_node or not self.target_node:
            return
            
        start_pos = self.mapFromItem(self.source_node, self.source_node.output_port)
        end_pos = self.mapFromItem(self.target_node, self.target_node.input_port)
        
        path = QPainterPath()
        path.moveTo(start_pos)
        
        # Cubic Bezier
        ctrl_pt1 = QPointF(start_pos.x() + 50, start_pos.y())
        ctrl_pt2 = QPointF(end_pos.x() - 50, end_pos.y())
        
        path.cubicTo(ctrl_pt1, ctrl_pt2, end_pos)
        
        self.setPath(path)

    def shape(self):
        # Create a wider path for collision detection (easier to click)
        path_stroker = QPainterPath()
        # Use the current path as base
        base_path = self.path()
        
        # Stroke it to create a wide area
        stroker = QPainterPath()
        stroker.addPath(base_path)
        
        # We need to simulate a stroke width. QPainterPathStroker is needed here?
        # Or simpler implementation:
        from PyQt6.QtGui import QPainterPathStroker
        stroker = QPainterPathStroker()
        stroker.setWidth(10) # 10px wide hit area
        return stroker.createStroke(base_path)

    def paint(self, painter, option, widget):
        if self.isSelected():
            pen = QPen(QColor("#ff9900"), 3) # Highlight color
        else:
            pen = QPen(QColor("#333333"), 2)
            
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(self.path())
