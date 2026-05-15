import json
import re
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
            
        # 4. Check if source is 'get_files' or an importer (primary input)
        source_node = None
        for nid in sources:
            node = node_map[nid]
            if node.function == 'get_files' or 'file_paths' in node.params or node.function in ['pop_loadset', 'pop_mffimport', 'pop_fileio', 'pop_biosig']:
                source_node = node
                break
                
        if not source_node:
            return False, "No data source node found. Please start with 'Get File(s)' or an Import node."
            
        # 5. Check if files are actually selected
        import os
        files = source_node.params.get("file_paths", [])
        if not files:
            if source_node.function == 'pop_loadset':
                 f_name = source_node.params.get("filename", "")
                 f_path = source_node.params.get("filepath", "")
                 if f_name and f_path:
                      files = [os.path.join(f_path, f_name)]
                 elif f_name:
                      files = [f_name]
            elif source_node.function in ['pop_mffimport']:
                 files = [source_node.params.get("mffFile", "")]
            elif source_node.function in ['pop_fileio', 'pop_biosig']:
                 files = [source_node.params.get("filename", "")]
                 
            files = [f for f in files if f]

        if not files:
            return False, "No files selected in the data source node."
            
        return True, ""

    def build_job_dict(self):
        """
        Compiles the pipeline validation and processing information into a dictionary.
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
        
        # Extract files from source
        import os
        sources = [n for n in G.nodes if G.in_degree(n) == 0]
        source_node = None
        for nid in sources:
            node = node_map[nid]
            if node.function == 'get_files' or 'file_paths' in node.params or node.function in ['pop_loadset', 'pop_mffimport', 'pop_fileio', 'pop_biosig']:
                source_node = node
                break
                
        files = source_node.params.get("file_paths", [])
        if not files:
            if source_node.function == 'pop_loadset':
                 f_name = source_node.params.get("filename", "")
                 f_path = source_node.params.get("filepath", "")
                 if f_name and f_path:
                      files = [os.path.join(f_path, f_name)]
                 elif f_name:
                      files = [f_name]
            elif source_node.function in ['pop_mffimport']:
                 files = [source_node.params.get("mffFile", "")]
            elif source_node.function in ['pop_fileio', 'pop_biosig']:
                 files = [source_node.params.get("filename", "")]
                 
            files = [f for f in files if f]
            
        # Identify all transfer nodes and their connections
        transfer_nodes = {n.id: n for n in self.pipeline.nodes if n.type == 'transfer'}
        
        # S_id -> list of {var_id, field}
        extraction_map = {}
        for e in self.pipeline.edges:
            if e.target in transfer_nodes:
                T_id = e.target
                S_id = e.source
                field = transfer_nodes[T_id].params.get('field', 'chanlocs')
                var_name = f"trans_v_{T_id[:8].replace('-', '_')}"
                if S_id not in extraction_map: extraction_map[S_id] = []
                extraction_map[S_id].append({"var_name": var_name, "field": field})
        
        # Target_id -> list of {param, var_name}
        injection_map = {}
        for n in self.pipeline.nodes:
            if hasattr(n, 'transfer_inputs') and n.transfer_inputs:
                for param_name, info in n.transfer_inputs.items():
                    T_id = info.get('source_node_id')
                    if T_id in transfer_nodes:
                        var_name = f"trans_v_{T_id[:8].replace('-', '_')}"
                        if n.id not in injection_map: injection_map[n.id] = []
                        injection_map[n.id].append({"param": param_name, "var_name": var_name})

        # Build step list
        steps = []
        cumulative_suffix = ""
        
        from src.model.library import LibraryManager
        lib = LibraryManager.instance()
        
        for nid in ordered_ids:
            node = node_map[nid]
            func_name = node.function
            
            if not func_name:
                continue

            # Special case for source: get_files is just a data provider, skip it in steps
            if func_name == 'get_files':
                continue
            
            # Suffix calculation
            step_def = lib.get_step_by_function(func_name)
            node_suffix = step_def.get('suffix', '') if step_def else ''
            if node_suffix:
                cumulative_suffix += "_" + node_suffix
                
            arguments = []
            if step_def and 'inputs' in step_def:
                for inp in step_def['inputs']:
                    if inp.get('type') == 'dataset':
                        continue
                    name = inp.get('name')
                    arg_type = inp.get('arg_type', 'name-value')
                    val = node.params.get(name, inp.get('default'))
                    
                    if val == 'off' or val == '':
                        if arg_type == 'positional':
                            arguments.append([])
                        continue
                        
                    formatted_val = self._format_value(name, val, inp)
                    
                    if arg_type == 'positional':
                        arguments.append(formatted_val)
                    else:
                        if inp.get('type') == 'key_value_list' and isinstance(formatted_val, list):
                            # Flatten key-value pairs directly into arguments
                            arguments.extend(formatted_val)
                        else:
                            arguments.extend([name, formatted_val])
                
                # Trim trailing empties for positional args
                while arguments and arguments[-1] == []:
                    arguments.pop()
            else:
                for k, v in node.params.items():
                    if v != 'off' and v != '':
                        formatted_val = self._format_value(k, v, None)
                        arguments.extend([k, formatted_val])
                
            step_info = {
                "function": func_name,
                "label": node.label,
                "parameters": node.params,
                "arguments": arguments,
                "current_suffix": cumulative_suffix
            }
            
            if node.save_output:
                step_info["save_at_this_step"] = True
                
            if nid in extraction_map:
                step_info["transfer_out"] = extraction_map[nid]
            if nid in injection_map:
                step_info["transfer_in"] = injection_map[nid]
                
            steps.append(step_info)
            
        job = {
            "files": files,
            "steps": steps
        }
        
        return job
    def _format_value(self, name, val, inp_def):
        list_params = {'rmchannel', 'channel', 'badchans', 'chanind', 'exclude', 'ref', 'components', 'electrodes', 'icacomps', 'trials', 'items', 'chan'}
        
        # 1. Handle Key-Value list (options)
        if inp_def and inp_def.get('type') == 'key_value_list':
             # If it's a list of pairs [[k,v], ...]
             if isinstance(val, list) and val and isinstance(val[0], list) and len(val[0]) == 2:
                 flattened = []
                 for k, v in val:
                     flattened.extend([k, v])
                 return flattened
             return val

        # 2. Handle space-separated strings for known list parameters
        if name in list_params and isinstance(val, str):
            val = val.strip()
            if val.startswith('[') and val.endswith(']'):
                val = val[1:-1].strip()
            if not val:
                return []
            
            # Split by space or comma
            parts = [p.strip() for p in re.split(r'[,\s]+', val) if p.strip()]
            
            if not parts:
                return []
            
            # Try to convert to numbers if possible
            try:
                numeric = []
                for p in parts:
                    n = float(p)
                    if n == int(n):
                        numeric.append(int(n))
                    else:
                        numeric.append(n)
                return numeric
            except:
                # Return as list of strings
                return [p.strip("'\"") for p in parts]
        
        return val
