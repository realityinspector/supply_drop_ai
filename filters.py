import json

def from_json(value):
    """Convert a JSON string to a Python object."""
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value 