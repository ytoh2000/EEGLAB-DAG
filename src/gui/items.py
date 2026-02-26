from PyQt6.QtWidgets import QGraphicsItem, QGraphicsPathItem, QGraphicsRectItem, QGraphicsTextItem
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPen, QBrush, QPainter, QPainterPath, QColor, QFont, QLinearGradient

# Category → color palette
CATEGORY_COLORS = {
    'File':   QColor('#26A69A'),  # Teal
    'Edit':   QColor('#42A5F5'),  # Blue
    'Tools':  QColor('#FFA726'),  # Orange
    'Plot':   QColor('#AB47BC'),  # Purple
}

# Node type overrides (take precedence over category)
TYPE_COLORS = {
    'input':         QColor('#66BB6A'),  # Green
    'output':        QColor('#EF5350'),  # Red
    'visualization': QColor('#AB47BC'),  # Purple
    'placeholder':   QColor('#9E9E9E'),  # Gray — unknown/unavailable
}

HEADER_HEIGHT = 26

class NodeItem(QGraphicsItem):
    def __init__(self, node_id, label="Node", x=0, y=0, step_def=None):
        super().__init__()
        self.node_id = node_id
        self.label_text = label
        self.step_def = step_def or {}
        self.function_name = self.step_def.get('function', '')
        
        self.width = 160
        self.height = 80
        self.radius = 10
        self.port_radius = 6
        
        # Resolve node color from type first, then category, then default grey
        self.step_type = self.step_def.get('type', 'process')
        category = self.step_def.get('category', '')
        self.node_color = TYPE_COLORS.get(self.step_type,
                          CATEGORY_COLORS.get(category, QColor('#90A4AE')))
        
        # Data & Edges (Must init before setPos, which triggers itemChange)
        self.params = {}
        self.edges = []
        self.user_note = ''
        
        # Flags
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        
        self.setPos(x, y)
        
        # Ports
        self.input_port = QPointF(0, self.height / 2)
        self.output_port = QPointF(self.width, self.height / 2)
        
        # Determine port visibility
        self.has_input = self.step_type != 'input'
        self.has_output = self.step_type != 'output'

    def boundingRect(self):
        padding = 45
        # Extra space below for shadow
        return QRectF(-padding, -2, self.width + 2*padding, self.height + 6)
        
    def shape(self):
        # Define the exact hit shape: Body + Ports
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width, self.height, self.radius, self.radius)
        
        # Add port hit areas (larger than visual for easy clicking)
        hit_radius = 45
        if self.has_input:
            path.addEllipse(self.input_port, hit_radius, hit_radius)
        if self.has_output:
            path.addEllipse(self.output_port, hit_radius, hit_radius)
        
        return path
        
    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Drop shadow
        shadow_path = QPainterPath()
        shadow_path.addRoundedRect(2, 2, self.width, self.height, self.radius, self.radius)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 40)))
        painter.drawPath(shadow_path)
        
        # Body background (white with slight tint)
        body = QPainterPath()
        body.addRoundedRect(0, 0, self.width, self.height, self.radius, self.radius)
        
        if self.isSelected():
            painter.setPen(QPen(QColor('#ff9900'), 2.5))
        else:
            painter.setPen(QPen(self.node_color.darker(120), 1))
        painter.setBrush(QBrush(QColor('#fafafa')))
        painter.drawPath(body)
        
        # Colored header bar
        header = QPainterPath()
        header.moveTo(0, self.radius)
        header.arcTo(0, 0, self.radius * 2, self.radius * 2, 180, -90)      # top-left
        header.lineTo(self.width - self.radius, 0)
        header.arcTo(self.width - self.radius * 2, 0, self.radius * 2, self.radius * 2, 90, -90)  # top-right
        header.lineTo(self.width, HEADER_HEIGHT)
        header.lineTo(0, HEADER_HEIGHT)
        header.closeSubpath()
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.node_color))
        painter.drawPath(header)
        
        # Label in header (white text, centered, word-wrapped for long names)
        painter.setPen(QColor('#ffffff'))
        painter.setFont(QFont('Segoe UI', 8, QFont.Weight.Bold))
        header_rect = QRectF(4, 1, self.width - 8, HEADER_HEIGHT)
        painter.drawText(header_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter | Qt.TextFlag.TextWordWrap, self.label_text)
        
        # Function name in body (centered)
        body_y = HEADER_HEIGHT + 2
        if self.function_name:
            painter.setPen(QColor('#888888'))
            painter.setFont(QFont('Segoe UI', 8))
            func_rect = QRectF(6, body_y, self.width - 12, 16)
            painter.drawText(func_rect, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter, self.function_name)
            body_y += 16
        
        # User note (italic, blue, up to 2 lines) 
        if self.user_note:
            painter.setPen(QColor('#5C6BC0'))
            note_font = QFont('Segoe UI', 7)
            note_font.setItalic(True)
            painter.setFont(note_font)
            note_rect = QRectF(6, body_y, self.width - 12, self.height - body_y - 2)
            painter.drawText(note_rect, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter | Qt.TextFlag.TextWordWrap, self.user_note)
        
        # Ports
        painter.setPen(QPen(self.node_color.darker(130), 1.5))
        painter.setBrush(QBrush(self.node_color))
        if self.has_input:
            painter.drawEllipse(self.input_port, self.port_radius, self.port_radius)
        if self.has_output:
            painter.drawEllipse(self.output_port, self.port_radius, self.port_radius)

    def get_port_at(self, pos):
        # pos is in item coordinates
        # Hit radius is larger than visual dot (6px) for easy edge creation
        HIT_RADIUS = 45
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
        
        # Build output label from source node's outputs definition
        outputs = self.source_node.step_def.get('outputs', [])
        names = [o.get('name', '') for o in outputs if o.get('name')]
        self._output_label = ', '.join(names) if names else ''
        self._label_pos = QPointF(0, 0)
        self._insert_hover = False  # Highlight state for node-on-edge insertion
        
        self.adjust()
        
    def adjust(self):
        if not self.source_node or not self.target_node:
            return
            
        start_pos = self.mapFromItem(self.source_node, self.source_node.output_port)
        end_pos = self.mapFromItem(self.target_node, self.target_node.input_port)
        
        path = QPainterPath()
        path.moveTo(start_pos)
        
        # Check if this is a wrap-around edge (target is left of source)
        if end_pos.x() < start_pos.x() - 20:
            # Route between rows: go down from source row, across, then down to target
            drop = 70  # Centers the crossing line between the two rows
            mid_y = start_pos.y() + drop
            
            # Source output → right then down
            path.lineTo(start_pos.x() + 30, start_pos.y())
            path.lineTo(start_pos.x() + 30, mid_y)
            # Across to target column
            path.lineTo(end_pos.x() - 30, mid_y)
            # Down to target input
            path.lineTo(end_pos.x() - 30, end_pos.y())
            path.lineTo(end_pos)
        else:
            # Normal left-to-right: cubic bezier
            ctrl_pt1 = QPointF(start_pos.x() + 50, start_pos.y())
            ctrl_pt2 = QPointF(end_pos.x() - 50, end_pos.y())
            path.cubicTo(ctrl_pt1, ctrl_pt2, end_pos)
        
        self.setPath(path)
        
        # Cache the midpoint of the curve for the label
        self._label_pos = path.pointAtPercent(0.5)
        # Cache the direction at the end for the arrowhead
        self._end_pos = end_pos
        t = 0.97
        self._arrow_dir = path.pointAtPercent(t)

    def shape(self):
        base_path = self.path()
        from PyQt6.QtGui import QPainterPathStroker
        stroker = QPainterPathStroker()
        stroker.setWidth(10)
        return stroker.createStroke(base_path)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if self._insert_hover:
            pen = QPen(QColor('#4CAF50'), 3)  # Green glow
        elif self.isSelected():
            pen = QPen(QColor('#ff9900'), 3)
        else:
            pen = QPen(QColor('#555555'), 2)
            
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(self.path())
        
        # Arrowhead at target end
        import math
        dx = self._end_pos.x() - self._arrow_dir.x()
        dy = self._end_pos.y() - self._arrow_dir.y()
        length = math.hypot(dx, dy)
        if length > 0:
            dx /= length
            dy /= length
            arrow_size = 8
            ax = self._end_pos.x() - arrow_size * dx
            ay = self._end_pos.y() - arrow_size * dy
            # Perpendicular
            px, py = -dy, dx
            p1 = QPointF(ax + arrow_size * 0.5 * px, ay + arrow_size * 0.5 * py)
            p2 = QPointF(ax - arrow_size * 0.5 * px, ay - arrow_size * 0.5 * py)
            
            arrow = QPainterPath()
            arrow.moveTo(self._end_pos)
            arrow.lineTo(p1)
            arrow.lineTo(p2)
            arrow.closeSubpath()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(pen.color()))
            painter.drawPath(arrow)
        
        # Output label at midpoint
        if self._output_label:
            painter.setFont(QFont('Segoe UI', 7))
            fm = painter.fontMetrics()
            text_width = fm.horizontalAdvance(self._output_label)
            text_height = fm.height()
            
            pill_w = text_width + 10
            pill_h = text_height + 4
            pill_x = self._label_pos.x() - pill_w / 2
            pill_y = self._label_pos.y() - pill_h / 2 - 8  # offset above edge
            
            # Pill background — green highlight when insert-hover active
            pill = QPainterPath()
            pill.addRoundedRect(pill_x, pill_y, pill_w, pill_h, 6, 6)
            if self._insert_hover:
                painter.setPen(QPen(QColor('#4CAF50'), 2))
                painter.setBrush(QBrush(QColor(200, 255, 200, 240)))
            else:
                painter.setPen(QPen(QColor('#cccccc'), 0.5))
                painter.setBrush(QBrush(QColor(255, 255, 255, 220)))
            painter.drawPath(pill)
            
            # Text
            painter.setPen(QColor('#333333') if self._insert_hover else QColor('#666666'))
            text_rect = QRectF(pill_x, pill_y, pill_w, pill_h)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self._output_label)

