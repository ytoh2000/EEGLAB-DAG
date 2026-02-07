import os
import json
import glob

class LibraryManager:
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.steps = {} # name -> definition
        self.library_paths = []
        
        # Default library path
        import sys
        if getattr(sys, 'frozen', False):
            # If frozen, executable is in bin/os/main/main
            # We need to go up to root: ../../../library/nodes
            base_dir = os.path.dirname(sys.executable)
            default_lib = os.path.abspath(os.path.join(base_dir, '..', '..', '..', 'library', 'nodes'))
        else:
            # Dev: src/model/library.py -> root/library/nodes
            # ../../library/nodes
            base_dir = os.path.dirname(os.path.abspath(__file__))
            default_lib = os.path.abspath(os.path.join(base_dir, '..', '..', 'library', 'nodes'))
            
        self.library_paths.append(default_lib)
        
        self.reload()

    def reload(self):
        self.steps = {}
        for path in self.library_paths:
            if not os.path.exists(path):
                continue
                
            json_files = glob.glob(os.path.join(path, '*.json'))
            for json_file in json_files:
                try:
                    with open(json_file, 'r') as f:
                        data = json.load(f)
                        # Handle both single object or list of objects
                        if isinstance(data, list):
                            for step in data:
                                self._add_step(step)
                        else:
                            self._add_step(data)
                except Exception as e:
                    print(f"Error loading {json_file}: {e}")
                    
    def _add_step(self, step_data):
        if 'name' in step_data:
            self.steps[step_data['name']] = step_data

    def get_step(self, name):
        return self.steps.get(name)

    def get_all_steps(self):
        return list(self.steps.values())
