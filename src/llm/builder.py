"""
Pipeline builder: converts LLM JSON output into a Pipeline object.

Handles:
- Matching LLM-suggested functions to the node library
- Building NodeData + EdgeData objects
- Auto-layout positioning
- Storing LLM reasoning annotations
"""
from src.model.pipeline import Pipeline, NodeData, EdgeData
from src.model.library import LibraryManager


def build_pipeline_from_llm(llm_data: dict) -> tuple:
    """Convert LLM-generated JSON into a Pipeline object.
    
    Args:
        llm_data: Dict with 'nodes' and 'edges' from the LLM.
    Returns:
        Tuple of (Pipeline, list_of_warnings, reasoning_map).
        reasoning_map maps node_id -> reasoning string.
    """
    pipeline = Pipeline()
    library = LibraryManager.instance()
    warnings = []
    reasoning_map = {}  # node_id -> reasoning text
    
    # Build nodes
    for i, node_info in enumerate(llm_data.get('nodes', [])):
        node_id = str(node_info.get('id', str(i + 1)))
        function = node_info.get('function', '')
        label = node_info.get('label', function)
        node_type = node_info.get('type', 'process')
        params = node_info.get('parameters', {})
        reasoning = node_info.get('reasoning', '')
        
        # Grid layout: 5 columns, wrapping to new rows
        COLS = 5
        H_SPACING = 220
        V_SPACING = 140
        col = i % COLS
        row = i // COLS
        pos = (col * H_SPACING + 50, row * V_SPACING + 50)
        
        # Validate function exists in library
        step_def = library.get_step_by_function(function) if function else None
        if not step_def:
            # Try by label
            step_def = library.get_step(label)
        
        if not step_def:
            # Unknown function → gray placeholder node
            node_type = 'placeholder'
            warnings.append(f"Unknown function '{function}' (labeled '{label}'). "
                          f"Created as gray placeholder — replace with the correct node.")
            note_parts = [f"⚠ Placeholder: '{function}' not in library"]
            if reasoning:
                note_parts.append(f"Paper: {reasoning}")
            note = '\n'.join(note_parts)
        else:
            note = f"LLM: {reasoning}" if reasoning else ''
        
        # Convert parameter values to strings (our params system expects strings)
        clean_params = {}
        for k, v in params.items():
            if v is not None:
                clean_params[k] = str(v)
        
        node_data = NodeData(
            node_id=node_id,
            node_type=node_type,
            label=label,
            pos=pos,
            params=clean_params,
            function=function,
            note=note
        )
        pipeline.add_node(node_data)
        
        if reasoning:
            reasoning_map[node_id] = reasoning
    
    # Build edges
    for edge_info in llm_data.get('edges', []):
        source = str(edge_info.get('source', ''))
        target = str(edge_info.get('target', ''))
        if source and target:
            pipeline.add_edge(EdgeData(source, target))
    
    return pipeline, warnings, reasoning_map
