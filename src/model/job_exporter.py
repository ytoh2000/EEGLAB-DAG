import json
import networkx as nx
from src.model.pipeline import Pipeline

class JobExporter:
    def __init__(self, pipeline: Pipeline):
        self.pipeline = pipeline

    def validate(self):
        """
        Validates the pipeline for export.
        Returns (is_valid, error_message)
        """
        # 1. Build NetworkX graph
        G = nx.DiGraph()
        node_map = {n.id: n for n in self.pipeline.nodes}
        
        for n in self.pipeline.nodes:
            G.add_node(n.id)
            
        for e in self.pipeline.edges:
            G.add_edge(e.source, e.target)
            
        # 2. Check for cycles
        if not nx.is_directed_acyclic_graph(G):
            return False, "Pipeline contains cycles (loops). Please remove loops."
            
        # 3. Find source nodes (indegree 0)
        sources = [n for n in G.nodes if G.in_degree(n) == 0]
        if not sources:
            return False, "No source node found."
            
        # 4. Check if source is 'get_files' (primary input)
        # We assume single primary input for now, or we look for the one with type 'input'
        # based on our convention from library definitions
        get_files_node = None
        for nid in sources:
            node = node_map[nid]
            # We can check specific function name or type 'input' if we stored the definition
            # But here we only have NodeData which has params. 
            # We rely on the label or we need to access the library definition again.
            # Assuming labels are unique-ish or we check the function name if we stored it?
            # NodeData only has label. But label usually matches name.
            # Ideally NodeData should store the 'function' identifier. 
            # Let's assume the label "Get File(s)" or check if it has file_paths param
            if "file_paths" in node.params:
                get_files_node = node
                break
                
        if not get_files_node:
            return False, "No 'Get File(s)' source node found. Please add a Get File(s) node to start."
            
        # 5. Check if files are actually selected
        files = get_files_node.params.get("file_paths", [])
        if not files:
            return False, "No files selected in 'Get File(s)' node."
            
        # 6. Check flow connectivity (can we reach a sink?)
        # For this simple linear/branching flow, just ensuring it's a sorted list is enough.
        
        return True, ""

    def export(self, file_path):
        """
        Exports the pipeline validation and processing information to a JSON file.
        """
        valid, msg = self.validate()
        if not valid:
            raise ValueError(msg)
            
        # Topological sort to get execution order
        G = nx.DiGraph()
        node_map = {n.id: n for n in self.pipeline.nodes}
        for n in self.pipeline.nodes:
            G.add_node(n.id)
        for e in self.pipeline.edges:
            G.add_edge(e.source, e.target)
            
        ordered_ids = list(nx.topological_sort(G))
        
        # Build step list
        steps = []
        files = []
        
        # Identify library definition to get function names
        # We need the LibraryManager to look up definitions by label (or store function name in NodeData)
        from src.model.library import LibraryManager
        library = LibraryManager.instance()
        
        for nid in ordered_ids:
            node = node_map[nid]
            step_def = library.get_step(node.label) # This relies on label matching. 
            # TODO: Robustness improvement: Store 'function' in NodeData.
            
            if not step_def:
                continue

            # Special case for source
            if step_def.get('function') == 'get_files':
                files = node.params.get('file_paths', [])
                continue
                
            step_info = {
                "function": step_def.get('function'),
                "label": node.label,
                "parameters": node.params
            }
            steps.append(step_info)
            
        job = {
            "files": files,
            "steps": steps
        }
        
        with open(file_path, 'w') as f:
            json.dump(job, f, indent=4)
            
        return job
