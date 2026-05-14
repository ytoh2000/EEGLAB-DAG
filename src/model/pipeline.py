import json

class Pipeline:
    def __init__(self):
        self.nodes = []
        self.edges = []
        self.settings = {
            "generate_report": True,
            "error_strategy": "halt",
            "test_mode": False,
            "test_sample_size": 1,
            "parallel_processing": False,
            "pipeline_id": "DAG",
            "use_global_savepath": False,
            "global_savepath": "",
            "bids_dataset_name": "",
            "bids_authors": "",
            "bids_default_task": "",
            "bids_modality": "eeg",
            "bids_anonymize": False
        }
        
    def add_node(self, node_data):
        self.nodes.append(node_data)
        
    def add_edge(self, edge_data):
        self.edges.append(edge_data)
        
    def to_dict(self):
        visual_graph = {
            "settings": self.settings,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges]
        }
        
        # Attempt to compile the execution job
        execution_job = None
        try:
            from src.model.job_exporter import JobExporter
            exporter = JobExporter(self)
            execution_job = exporter.build_job_dict()
        except Exception as e:
            # If validation fails, it's fine. We just save the visual state.
            pass
            
        return {
            "version": "1.0",
            "name": "Pipeline",
            "visual_graph": visual_graph,
            "execution_job": execution_job
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
        
        # Support new unified format, fallback to legacy
        if "visual_graph" in data:
            v_graph = data["visual_graph"]
        else:
            v_graph = data
            
        pipeline.settings = v_graph.get("settings", {
            "generate_report": True,
            "error_strategy": "halt",
            "test_mode": False,
            "test_sample_size": 1,
            "parallel_processing": False,
            "output_folder": "",
            "pipeline_id": "DAG",
            "use_global_savepath": False,
            "global_savepath": "",
            "bids_dataset_name": "",
            "bids_authors": "",
            "bids_default_task": "",
            "bids_modality": "eeg",
            "bids_anonymize": False
        })
        
        # Migrate old settings
        if 'stop_on_error' in pipeline.settings:
            stop = pipeline.settings.pop('stop_on_error')
            pipeline.settings['error_strategy'] = 'halt' if stop else 'skip'
        pipeline.nodes = [NodeData.from_dict(n) for n in v_graph.get("nodes", [])]
        pipeline.edges = [EdgeData.from_dict(e) for e in v_graph.get("edges", [])]
        return pipeline

    def validate(self, check_files=False):
        """
        Validates the pipeline structure and content.
        Args:
            check_files (bool): If True, checks if input nodes have files selected.
        Returns:
            (bool, str): (is_valid, error_message)
        """
        import networkx as nx
        
        # 1. Empty Check
        if not self.nodes:
            return False, "The canvas is empty. Please add nodes before saving."
            
        G = nx.DiGraph()
        node_map = {n.id: n for n in self.nodes}
        for n in self.nodes:
            G.add_node(n.id)
        for e in self.edges:
            G.add_edge(e.source, e.target)

        # 2. Cycle Detection
        if self.edges:
            if not nx.is_directed_acyclic_graph(G):
                return False, "Pipeline contains cycles (loops). Please remove loops before saving."
            
            # 3. Connectivity Check — warn about disconnected nodes
            undirected = G.to_undirected()
            components = list(nx.connected_components(undirected))
            if len(components) > 1:
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
            
        # 4. Source Node Check
        source_nodes = [n for n in G.nodes if G.in_degree(n) == 0]
        valid_sources = []
        importer_funcs = {'pop_loadset', 'pop_mffimport', 'pop_fileio', 'pop_biosig', 'get_files'}
        for nid in source_nodes:
            n = node_map[nid]
            if n.type == 'input' or n.function in importer_funcs:
                valid_sources.append(n)
                
        if not valid_sources:
             return False, "No valid source nodes (e.g. Create File Lists or Load Data) are specified at the start of the pipeline."
             
        # 5. Output/Plotting Node Check (skip transfer nodes)
        output_nodes = [n for n in self.nodes if n.type in ('output', 'visualization')]
        if not output_nodes:
             return False, "No output (Save) or plotting nodes are specified."
             
        # 6. File Check (for Export)
        if check_files:
            for node in valid_sources:
                if node.function == 'get_files':
                    files = node.params.get('file_paths', [])
                    if not files:
                        return False, f"No input files selected in '{node.label}'."
                elif node.function in importer_funcs:
                    if node.function == 'pop_mffimport':
                        filename = node.params.get('mffFile', '')
                    else:
                        filename = node.params.get('filename', '')
                        
                    if not filename:
                        return False, f"No file specified in '{node.label}'."
                    
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
    def __init__(self, node_id, node_type, label, pos=(0,0), params=None, function='', note='', save_output=False, transfer_inputs=None):
        self.id = node_id
        self.type = node_type
        self.function = function
        self.label = label
        self.pos = pos
        self.params = params or {}
        self.note = note
        self.save_output = save_output
        self.transfer_inputs = transfer_inputs or {}
        
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
        if self.save_output:
            d["save_output"] = True
        if self.transfer_inputs:
            d["transfer_inputs"] = self.transfer_inputs
        return d

    @classmethod
    def from_dict(cls, data):
        node = cls(
            node_id=data["id"],
            node_type=data["type"],
            label=data["label"],
            pos=data["position"],
            params=data["parameters"],
            function=data.get("function", ""),
            note=data.get("note", ""),
            save_output=data.get("save_output", False),
            transfer_inputs=data.get("transfer_inputs", {})
        )
        return node

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
