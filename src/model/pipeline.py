import json

class Pipeline:
    def __init__(self):
        self.nodes = []
        self.edges = []
        
    def add_node(self, node_data):
        self.nodes.append(node_data)
        
    def add_edge(self, edge_data):
        self.edges.append(edge_data)
        
    def to_dict(self):
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges]
        }
        
    def save(self, filepath):
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath):
        with open(filepath, 'r') as f:
            data = json.load(f)
            return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data):
        pipeline = cls()
        pipeline.nodes = [NodeData.from_dict(n) for n in data.get("nodes", [])]
        pipeline.edges = [EdgeData.from_dict(e) for e in data.get("edges", [])]
        return pipeline

    def validate(self, check_files=False):
        """
        Validates the pipeline structure and content.
        Args:
            check_files (bool): If True, checks if input nodes have files selected.
        Returns:
            (bool, str): (is_valid, error_message)
        """
        # 1. Empty Check
        if not self.nodes:
            return False, "The canvas is empty. Please add nodes before saving."
        
        import networkx as nx
        
        # 2. Cycle Detection
        if self.edges:
            G = nx.DiGraph()
            node_map = {n.id: n for n in self.nodes}
            for n in self.nodes:
                G.add_node(n.id)
            for e in self.edges:
                G.add_edge(e.source, e.target)
            
            if not nx.is_directed_acyclic_graph(G):
                return False, "Pipeline contains cycles (loops). Please remove loops before saving."
            
            # 3. Connectivity Check — warn about disconnected nodes
            # Convert to undirected to check if all nodes are reachable
            undirected = G.to_undirected()
            components = list(nx.connected_components(undirected))
            if len(components) > 1:
                # Find the smaller disconnected groups
                components.sort(key=len, reverse=True)
                disconnected_labels = []
                for comp in components[1:]:
                    for nid in comp:
                        if nid in node_map:
                            disconnected_labels.append(node_map[nid].label)
                if disconnected_labels:
                    names = ", ".join(disconnected_labels[:3])
                    suffix = f" (and {len(disconnected_labels)-3} more)" if len(disconnected_labels) > 3 else ""
                    return False, f"Some nodes are disconnected from the pipeline: {names}{suffix}. Connect or remove them."
            
        # 4. Input Node Check
        input_nodes = [n for n in self.nodes if n.type == 'input']
        if not input_nodes:
             return False, "No input nodes (e.g. Create File Lists) are specified."
             
        # 5. Output/Plotting Node Check
        output_nodes = [n for n in self.nodes if n.type in ('output', 'visualization')]
        if not output_nodes:
             return False, "No output (Save) or plotting nodes are specified."
             
        # 6. File Check (for Export)
        if check_files:
            for node in input_nodes:
                files = node.params.get('file_paths', [])
                if not files:
                    return False, f"No input files selected in '{node.label}'."
                    
        return True, ""

class NodeData:
    """
    Represents a single node in the pipeline.
    
    Attributes:
        id (str):       Unique identifier (UUID) for the node.
        type (str):     Category type from the node definition (e.g. 'input', 'process',
                        'output', 'visualization'). Controls port visibility.
        function (str): The EEGLAB function name (e.g. 'pop_eegfiltnew'). This is the
                        canonical identifier used for export and execution — never rely
                        on 'label' for logic.
        label (str):    Human-readable display name (e.g. 'Filter'). Shown on the canvas.
        pos (tuple):    (x, y) position on the canvas.
        params (dict):  User-configured parameters for this node.
    """
    def __init__(self, node_id, node_type, label, pos=(0,0), params=None, function='', note=''):
        self.id = node_id
        self.type = node_type
        self.function = function
        self.label = label
        self.pos = pos
        self.params = params or {}
        self.note = note
        
    def to_dict(self):
        d = {
            "id": self.id,
            "type": self.type,
            "function": self.function,
            "label": self.label,
            "position": self.pos,
            "parameters": self.params
        }
        if self.note:
            d["note"] = self.note
        return d

    @classmethod
    def from_dict(cls, data):
        return cls(
            node_id=data["id"],
            node_type=data["type"],
            label=data["label"],
            pos=data["position"],
            params=data["parameters"],
            function=data.get("function", ""),
            note=data.get("note", "")
        )

class EdgeData:
    def __init__(self, source_id, target_id):
        self.source = source_id
        self.target = target_id
        
    def to_dict(self):
        return {
            "source": self.source,
            "target": self.target
        }
        
    @classmethod
    def from_dict(cls, data):
        return cls(data["source"], data["target"])
