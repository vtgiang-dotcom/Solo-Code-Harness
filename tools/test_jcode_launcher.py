"""Tests for jcode.ps1's -RepairConfig repair path.

~/.jcode/config.toml is a machine-global file this repo does not own. If it
still pins the retired deepseek-v4-flash tier, any `jcode run` that omits
--model silently executes on it -- the launcher warns, and -RepairConfig
rewrites it on request.

These are source-shape tests, matching test_approve_api_key.py's approach:
PowerShell is not runnable in CI on every platform, so the checks assert the
properties that were actually got wrong during development rather than
re-running the script.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAUNCHER = ROOT / "jcode.ps1"


def _script() -> str:
    return LAUNCHER.read_text(encoding="utf-8")


def test_repair_writes_utf8_without_a_bom():
    """The trap this guards: `Set-Content -Encoding UTF8` emits a UTF-8 BOM on
    PowerShell 5.1. config.toml has no BOM, and a BOM lands inside the first
    key name -- so the "repair" would corrupt the user's whole jcode config.
    Verified by writing a fixture both ways and reading back the raw bytes.
    """
    script = _script()
    assert "UTF8Encoding" in script, "repair must construct an explicit encoding"

    repair = re.search(r"function Repair-JcodeConfig \{.*?\n\}", script, re.S)
    assert repair, "Repair-JcodeConfig not found in jcode.ps1"
    # Strip comments first: the body deliberately *mentions* Set-Content in a
    # comment explaining why it is not used.
    code = "\n".join(
        line for line in repair.group(0).splitlines()
        if not line.strip().startswith("#")
    )
    assert "Set-Content" not in code, (
        "Set-Content -Encoding UTF8 writes a BOM on PowerShell 5.1; "
        "use [System.IO.File]::WriteAllText with UTF8Encoding($false)"
    )
    assert "WriteAllText" in code


def test_repair_backs_up_before_rewriting():
    """It edits a file the user owns, holding settings unrelated to models."""
    body = re.search(r"function Repair-JcodeConfig \{.*?\n\}", _script(), re.S)
    assert body and "Copy-Item" in body.group(0)
    assert ".bak" in body.group(0)


def test_repair_is_opt_in_not_automatic():
    """Rewriting a machine-global file unprompted is the behaviour this
    deliberately avoids: the default path only warns."""
    script = _script()
    assert "[switch]$RepairConfig" in script
    assert "if ($RepairConfig)" in script


def test_the_warning_names_the_flag_that_fixes_it():
    """A warning the reader cannot act on is why this replaced a copy-pasted
    one-liner."""
    script = _script()
    assert "-RepairConfig" in script
    assert "deepseek-v4-flash" in script


def test_prompt_args_survive_the_param_block():
    """Declaring param() stops PowerShell from populating $args, so reading
    $args here would silently drop every prompt the user typed."""
    script = _script()
    assert "ValueFromRemainingArguments" in script
    assert "$rest = @($Rest)" in script
    assert "$rest = @($args)" not in script


def test_launcher_ships_to_deployed_projects():
    """A repair the target project cannot run is not a fix."""
    import sys
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tools import deploy
    assert "jcode.ps1" in deploy.ROOT_FILES
