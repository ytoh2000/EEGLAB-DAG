"""
API key settings for the LLM pipeline builder.

Stores and retrieves the Gemini API key from a local JSON config file.
The key is stored in the user's home directory under ~/.eeglab-dag/config.json.
"""
import json
import os

_CONFIG_DIR = os.path.join(os.path.expanduser('~'), '.eeglab-dag')
_CONFIG_FILE = os.path.join(_CONFIG_DIR, 'config.json')


def _ensure_config_dir():
    os.makedirs(_CONFIG_DIR, exist_ok=True)


def get_api_key() -> str:
    """Retrieve the stored Gemini API key, or empty string if not set."""
    if os.path.exists(_CONFIG_FILE):
        try:
            with open(_CONFIG_FILE, 'r') as f:
                config = json.load(f)
            return config.get('gemini_api_key', '')
        except (json.JSONDecodeError, IOError):
            return ''
    return ''


def save_api_key(key: str):
    """Save the Gemini API key to the local config file."""
    _ensure_config_dir()
    config = {}
    if os.path.exists(_CONFIG_FILE):
        try:
            with open(_CONFIG_FILE, 'r') as f:
                config = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    config['gemini_api_key'] = key
    with open(_CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


def has_api_key() -> bool:
    """Check if an API key is configured."""
    return bool(get_api_key())
