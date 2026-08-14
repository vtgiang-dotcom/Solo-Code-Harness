#!/usr/bin/env python3
"""Guard Hook Test Suite - validates safety patterns"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / ".claude" / "hooks"))
import guard

def test_normalize_command():
    """Test command normalization strips wrappers."""
    assert guard.normalize_command("sudo ls") == "ls"
    assert guard.normalize_command("env FOO=bar ls") == "ls"
    
def test_protected_files():
    """Test protected config files list."""
    assert ".ruff.toml" in guard.PROTECTED_FILES
    assert "eslint.config.js" in guard.PROTECTED_FILES
    assert "biome.json" in guard.PROTECTED_FILES
    
def test_executor_mode():
    """Test executor mode exemptions."""
    assert guard.executor_mode_exempt(".solocode/executor-mode")
    assert guard.executor_mode_exempt(".gemini/antigravity/handoff/inbox/task.md")
    assert not guard.executor_mode_exempt("tools/test.py")

def run_self_test():
    """Run basic validation tests."""
    print("Guard hook self-test...")
    tests = [
        ("Command normalization", test_normalize_command),
        ("Protected files", test_protected_files),
        ("Executor mode", test_executor_mode),
    ]
    
    passed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  [OK] {name}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
    
    print(f"\n{passed}/{len(tests)} passed")
    return passed == len(tests)

if __name__ == "__main__":
    sys.exit(0 if run_self_test() else 1)
