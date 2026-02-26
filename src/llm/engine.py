"""
Google Gemini LLM engine for the pipeline builder.

Sends extracted methods text to Gemini along with the available node library,
and receives a structured pipeline JSON response.
"""
import json
from src.llm.settings import get_api_key
from src.model.library import LibraryManager


def _build_node_catalog() -> str:
    """Build a human-readable catalog of available EEGLAB nodes for the prompt."""
    library = LibraryManager.instance()
    steps = library.get_all_steps()
    
    lines = []
    for step in steps:
        name = step.get('name', '')
        func = step.get('function', '')
        desc = step.get('description', '')
        step_type = step.get('type', 'process')
        
        # Gather input params
        inputs = step.get('inputs', [])
        param_parts = []
        for inp in inputs:
            if inp.get('type') == 'dataset':
                continue
            p_name = inp.get('name', '')
            p_type = inp.get('type', 'string')
            p_default = inp.get('default', '')
            p_desc = inp.get('description', '')
            required = '(required)' if inp.get('required', False) else ''
            param_parts.append(f"    - {p_name}: {p_type} {required} — {p_desc} (default: {p_default})")
        
        outputs = step.get('outputs', [])
        out_parts = [f"    - {o.get('name', '')}: {o.get('type', '')}" for o in outputs]
        
        lines.append(f"• {name} [function: {func}, type: {step_type}]")
        lines.append(f"  Description: {desc}")
        if param_parts:
            lines.append("  Parameters:")
            lines.extend(param_parts)
        if out_parts:
            lines.append("  Outputs:")
            lines.extend(out_parts)
        lines.append("")
    
    return '\n'.join(lines)


def _build_prompt(methods_text: str) -> str:
    """Build the full prompt for Gemini."""
    catalog = _build_node_catalog()
    
    return f"""You are an expert EEG researcher who constructs EEGLAB processing pipelines.

Given a Methods section from a scientific paper, construct an EEGLAB processing pipeline using ONLY the available nodes listed below.

## Available EEGLAB Nodes

{catalog}

## Output Format

Return a JSON object with this exact structure:
{{
    "nodes": [
        {{
            "id": "1",
            "type": "<node type from catalog: input/process/output/visualization>",
            "function": "<function name from catalog>",
            "label": "<display name from catalog>",
            "position": [x, y],
            "parameters": {{<parameter_name>: <value_from_paper>}},
            "reasoning": "<quote or paraphrase from the paper that justifies this step>"
        }}
    ],
    "edges": [
        {{"source": "1", "target": "2"}}
    ]
}}

## Rules

1. Always start with a "get_files" node (type: input) as the first node.
2. Always end with a "pop_saveset" node (type: output) as the last node.
3. Connect nodes sequentially in the order described in the paper.
4. Set parameter values to match what the paper describes (e.g., filter cutoffs, re-reference type).
5. If a parameter is mentioned in the paper, set it. If not mentioned, omit it (defaults will be used).
6. Use sequential IDs ("1", "2", "3", ...).
7. Space nodes horizontally: position = [x * 200, 100] where x is the node index (0-based).
8. The "reasoning" field should quote or paraphrase the specific sentence from the paper.
9. Prefer functions from the catalog. If the paper describes a step that has NO matching function in the catalog, still include it as a node with type "placeholder", the label should be a brief title (e.g. "ICLabel"), and the reasoning should explain what it does. Do NOT skip steps.
10. Return ONLY valid JSON, no markdown fences, no extra text.

## Methods Section

{methods_text}
"""


# Preference order: Flash first (better free-tier quotas)
_MODEL_PREFERENCES = [
    'gemini-2.5-flash',
    'gemini-3-pro-preview',
    'gemini-2.0-flash',
    'gemini-2.5-pro',
]
_cached_model = None

def _get_best_model(client) -> str:
    """Pick the best available Gemini model from the API."""
    global _cached_model
    if _cached_model:
        return _cached_model
    try:
        available = [m.name.replace('models/', '') for m in client.models.list()]
        for pref in _MODEL_PREFERENCES:
            if pref in available:
                _cached_model = pref
                return pref
        for name in available:
            if 'flash' in name and 'tts' not in name and 'image' not in name:
                _cached_model = name
                return name
    except Exception:
        pass
    return 'gemini-2.5-flash'


def _get_models_to_try(client):
    """Return ordered list of models to try (best first, with fallbacks)."""
    best = _get_best_model(client)
    models = [best]
    try:
        available = {m.name.replace('models/', '') for m in client.models.list()}
    except Exception:
        available = set(_MODEL_PREFERENCES)
    for pref in _MODEL_PREFERENCES:
        if pref != best and pref in available:
            models.append(pref)
    return models


def generate_pipeline_json(methods_text: str) -> dict:
    """Send methods text to Gemini and get a pipeline JSON response.
    
    Auto-selects the best available model and retries with fallbacks
    if a model hits quota limits (429).
    """
    api_key = get_api_key()
    if not api_key:
        raise ValueError("Gemini API key not configured. Go to Settings to add your key.")
    
    from google import genai
    
    client = genai.Client(api_key=api_key)
    prompt = _build_prompt(methods_text)
    models = _get_models_to_try(client)
    
    last_error = None
    for model_name in models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            
            # Success — cache this model
            global _cached_model
            _cached_model = model_name
            
            text = response.text.strip()
            
            # Strip markdown code fences if present
            if text.startswith('```'):
                lines = text.split('\n')
                if lines[0].startswith('```'):
                    lines = lines[1:]
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                text = '\n'.join(lines)
            
            pipeline_data = json.loads(text)
            
            if 'nodes' not in pipeline_data or 'edges' not in pipeline_data:
                raise RuntimeError("LLM response missing 'nodes' or 'edges' fields.")
            
            return pipeline_data
            
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Could not parse LLM response as JSON: {e}\n\nRaw response:\n{text[:500]}")
        except Exception as e:
            err_str = str(e)
            if '429' in err_str or 'RESOURCE_EXHAUSTED' in err_str:
                last_error = e
                _cached_model = None
                continue  # Try next model
            raise RuntimeError(f"Gemini API error ({model_name}): {e}")
    
    raise RuntimeError(f"All models hit quota limits. Please try again later.\n\nLast error: {last_error}")

