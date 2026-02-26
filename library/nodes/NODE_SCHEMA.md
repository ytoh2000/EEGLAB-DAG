# Node Definition Schema

This document describes the JSON schema for creating custom EEGLAB-DAG node definitions. Each JSON file in `library/nodes/` defines one EEGLAB function that can be used as a node in the pipeline editor.

## Quick Start

Copy this minimal template and save it as `library/nodes/your_function.json`:

```json
{
    "name": "My Function",
    "function": "pop_myfunction",
    "type": "process",
    "category": "Tools",
    "description": "What this function does.",
    "inputs": [
        {
            "name": "EEG",
            "type": "dataset",
            "description": "Input EEG structure",
            "required": true
        },
        {
            "name": "my_param",
            "type": "float",
            "description": "A numeric parameter",
            "required": false,
            "default": 1.0
        }
    ],
    "outputs": [
        {
            "name": "EEG",
            "type": "dataset",
            "description": "Output EEG structure"
        }
    ]
}
```

Restart the DAG Editor and your node will appear in the sidebar.

---

## Field Reference

| Field | Required | Description |
|---|---|---|
| `name` | ✅ | Human-readable display name shown on the canvas (e.g., `"Filter"`) |
| `function` | ✅ | EEGLAB function name used for execution (e.g., `"pop_eegfiltnew"`). Must match the MATLAB function exactly. |
| `type` | ✅ | Controls port visibility. One of: `"input"`, `"process"`, `"output"`, `"visualization"` |
| `category` | ✅ | Sidebar grouping. Standard categories: `"File"`, `"Edit"`, `"Tools"`, `"Plot"` |
| `description` | ✅ | Tooltip text. Briefly describe what the function does. |
| `github_url` | ❌ | Link to the function's source code on GitHub. Shown in right-click menu. |
| `inputs` | ✅ | Array of input parameter definitions (see below) |
| `outputs` | ✅ | Array of output definitions (see below) |

### Node Types

| Type | Input Port | Output Port | Use For |
|---|---|---|---|
| `"input"` | ❌ | ✅ | Data sources (file selectors, importers) |
| `"process"` | ✅ | ✅ | Processing functions (filter, ICA, re-reference) |
| `"output"` | ✅ | ❌ | Data sinks (save to disk) |
| `"visualization"` | ✅ | ❌ | Plotting functions (topoplot, headplot) |

### Input Parameter Types

| Type | GUI Widget | Example |
|---|---|---|
| `"dataset"` | *Hidden* (auto-wired) | `{"name": "EEG", "type": "dataset"}` |
| `"float"` | Text field (decimal) | `{"name": "locutoff", "type": "float", "default": 0}` |
| `"integer"` | Text field (whole number) | `{"name": "filtorder", "type": "integer"}` |
| `"string"` | Text field | `{"name": "setname", "type": "string", "default": ""}` |
| `"bool"` | Checkbox | `{"name": "revfilt", "type": "bool", "default": false}` |
| `"enum"` | Dropdown | `{"name": "icatype", "type": "enum", "options": ["runica", "fastica"]}` |
| `"filepath"` | File picker | `{"name": "filename", "type": "filepath"}` |
| `"directory"` | Folder picker | `{"name": "filepath", "type": "directory"}` |
| `"filelist"` | File list widget | `{"name": "file_paths", "type": "filelist", "default": []}` |
| `"cell"` | Text field (comma-sep) | `{"name": "channels", "type": "cell"}` |

### Input Parameter Fields

| Field | Required | Description |
|---|---|---|
| `name` | ✅ | MATLAB parameter name (passed as name-value pair) |
| `type` | ✅ | One of the types listed above |
| `description` | ✅ | Shown as label/tooltip in the properties dialog |
| `required` | ❌ | If `true`, shown by default. If `false`, hidden under "Show Optional" toggle. Default: `false` |
| `default` | ❌ | Default value pre-filled in the dialog |
| `options` | ❌ | Required for `"enum"` type. Array of string choices. |

---

## Example: Adding `pop_spectopo`

```json
{
    "name": "Spectopo",
    "function": "pop_spectopo",
    "type": "visualization",
    "category": "Plot",
    "description": "Plot channel spectra and scalp maps",
    "github_url": "https://github.com/sccn/eeglab/blob/master/functions/popfunc/pop_spectopo.m",
    "inputs": [
        {
            "name": "EEG",
            "type": "dataset",
            "description": "Input EEG structure",
            "required": true
        },
        {
            "name": "percent",
            "type": "float",
            "description": "Percent of data to use for spectrum computation",
            "required": false,
            "default": 100
        },
        {
            "name": "freq",
            "type": "string",
            "description": "Frequencies to plot scalp maps at (e.g. '[6 10 22]')",
            "required": false,
            "default": ""
        }
    ],
    "outputs": [
        {
            "name": "spectra",
            "type": "dataset",
            "description": "Power spectra values"
        }
    ]
}
```
