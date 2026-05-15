import os
import re

def normalize_path(path):
    """
    Normalizes a path by fixing slashes for the current OS, 
    collapsing redundant separators, and resolving . and ..
    """
    if not path:
        return ""
    
    # Replace all backslashes with forward slashes for internal processing
    path = path.replace('\\', '/')
    
    # Handle multiple slashes
    path = re.sub(r'/+', '/', path)
    
    # Use native separators
    path = os.path.normpath(path)
    
    return path

def is_volumes_path(path):
    """Returns True if the path starts with /Volumes/ (Mac style)"""
    return path.replace('\\', '/').startswith('/Volumes/')
