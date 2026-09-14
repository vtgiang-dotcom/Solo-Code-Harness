"""Stable import surface for the shared Claude guard predicates."""
import importlib.util
from pathlib import Path

_path = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "guard.py"
_spec = importlib.util.spec_from_file_location("solocode_claude_guard", _path)
if _spec is None or _spec.loader is None:
    raise ImportError(f"cannot load guard: {_path}")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
find_destructive = _module.find_destructive
find_secret = _module.find_secret
