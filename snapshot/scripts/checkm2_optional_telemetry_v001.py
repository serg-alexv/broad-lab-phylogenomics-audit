"""Optional progress only: preserve a matching cache and return rich diagnostics."""
from pathlib import Path
import json
import traceback


def structured_exception(error, operation_path):
    return {
        'type': type(error).__name__, 'str': str(error), 'repr': repr(error),
        'errno': getattr(error, 'errno', None),
        'filename': getattr(error, 'filename', None),
        'filename2': getattr(error, 'filename2', None),
        'operation_path': str(operation_path),
        'traceback': traceback.format_exc(),
    }


def read_optional_telemetry(path, expected_token, cached=None,
                            token_field='windows_launch_token'):
    """Return (matching snapshot, diagnostic); never use for required evidence."""
    previous = (dict(cached) if isinstance(cached, dict)
                and cached.get(token_field) == expected_token else {})
    try:
        value = json.loads(Path(path).read_text(encoding='utf-8-sig'))
        if not isinstance(value, dict) or value.get(token_field) != expected_token:
            raise ValueError('Optional telemetry owner/schema mismatch')
        return value, None
    except (OSError, json.JSONDecodeError, UnicodeDecodeError, ValueError, TypeError) as error:
        return previous, structured_exception(error, path)
