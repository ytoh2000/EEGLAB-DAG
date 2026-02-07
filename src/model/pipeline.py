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
            
        # 2. Input Node Check (Nodes that don't have inputs, should be type 'input')
        # We need to check if there is at least one node of type 'input'
        # OR we check nodes with in-degree 0.
        # User specified: "If no input nodes are specified"
        # We check for node.type == 'input' (e.g. get_files)
        input_nodes = [n for n in self.nodes if n.type == 'input']
        if not input_nodes:
             return False, "No input nodes (e.g. Create File Lists) are specified."
             
        # 3. Output/Plotting Node Check
        # User specified: "no output or plotting nodes"
        # We check for node.type == 'output' (pop_saveset) or 'visualization' (pop_topoplot)
        # Assuming we have these types in our library definitions.
        # We might need to check the library definition if node_type isn't sufficient,
        # but NodeData stores 'type' from the step definition.
        output_nodes = [n for n in self.nodes if n.type in ('output', 'visualization')]
        if not output_nodes:
             return False, "No output (Save) or plotting nodes are specified."
             
        # 4. File Check (for Export)
        if check_files:
            for node in input_nodes:
                # Assuming 'file_paths' is the key for get_files
                files = node.params.get('file_paths', [])
                if not files:
                    return False, f"No input files selected in '{node.label}'."
                    
        return True, ""

class NodeData:
    def __init__(self, node_id, node_type, label, pos=(0,0), params=None):
        self.id = node_id
        self.type = node_type
        self.label = label
        self.pos = pos
        self.params = params or {}
        
    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "label": self.label,
            "position": self.pos,
            "parameters": self.params
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            node_id=data["id"],
            node_type=data["type"],
            label=data["label"],
            pos=data["position"],
            params=data["parameters"]
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
