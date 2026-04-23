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
        node_map = {nid: n for nid, n in zip([n.id for n in self.pipeline.nodes], self.pipeline.nodes)}
        
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
        get_files_node = None
        for nid in sources:
            node = node_map[nid]
            if node.function == 'get_files' or 'file_paths' in node.params:
                get_files_node = node
                break
                
        if not get_files_node:
            return False, "No 'Get File(s)' source node found. Please add a Get File(s) node to start."
            
        # 5. Check if files are actually selected
        files = get_files_node.params.get("file_paths", [])
        if not files:
            return False, "No files selected in 'Get File(s)' node."
            
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
        cumulative_suffix = ""
        
        from src.model.library import LibraryManager
        lib = LibraryManager.instance()
        
        for nid in ordered_ids:
            node = node_map[nid]
            func_name = node.function
            
            if not func_name:
                continue

            # Special case for source: extract file list
            if func_name == 'get_files':
                files = node.params.get('file_paths', [])
                continue
            
            # Suffix calculation
            step_def = lib.get_step_by_function(func_name)
            node_suffix = step_def.get('suffix', '') if step_def else ''
            if node_suffix:
                cumulative_suffix += "_" + node_suffix
                
            step_info = {
                "function": func_name,
                "label": node.label,
                "parameters": node.params,
                "current_suffix": cumulative_suffix
            }
            
            if node.save_output:
                step_info["save_at_this_step"] = True
                
            steps.append(step_info)
            
        job = {
            "files": files,
            "steps": steps
        }
        
        with open(file_path, 'w') as f:
            json.dump(job, f, indent=4)
            
        return job
