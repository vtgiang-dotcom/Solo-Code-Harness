"""Tests for tools/check_lint_budget.py — the S/BLE ratchet.

The gate exists because `ruff check .` reports "All checks passed" while
security findings sit in the tree: `.ruff.toml`'s `select` omits the `S` and
`BLE` families, and `.ruff.toml` is protected config. So these tests care most
about the two ways such a gate fails silently -- counting wrong, and passing
when it should fail.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import check_lint_budget as budget  # noqa: E402

# --- load_budget -------------------------------------------------------------


def test_load_budget_reads_max_findings(tmp_path):
    f = tmp_path / "b.json"
    f.write_text(json.dumps({"maxFindings": 12}), encoding="utf-8")
    assert budget.load_budget(f) == 12


@pytest.mark.parametrize("payload", [
    {},                          # key absent
    {"maxFindings": -1},         # negative
    {"maxFindings": "12"},       # string, not int
    {"maxFindings": 1.5},        # float
    {"maxFindings": True},       # bool is an int subclass -- must still fail
])
def test_load_budget_rejects_malformed(tmp_path, payload):
    """A budget that silently defaults to a large number is a gate that passes
    for the wrong reason, so every malformed shape must raise."""
    f = tmp_path / "b.json"
    f.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError):
        budget.load_budget(f)


def test_load_budget_raises_on_missing_file(tmp_path):
    with pytest.raises(OSError):
        budget.load_budget(tmp_path / "absent.json")


# --- count_findings ----------------------------------------------------------


def test_count_findings_counts_one_line_per_finding(tmp_path):
    """The default `full` output format adds source-context lines, which
    counted 381 for the same 38 findings. One line per finding is the whole
    contract of this function."""
    src = tmp_path / "m.py"
    src.write_text(
        "import subprocess\n"
        "def f():\n"
        "    try:\n"
        "        subprocess.run(['ls'])\n"
        "    except Exception:\n"
        "        pass\n",
        encoding="utf-8",
    )

    count, raw = budget.count_findings(tmp_path)

    non_empty = [ln for ln in raw.splitlines() if ln.strip()]
    assert count == len(non_empty)
    assert count > 0, raw
    # Every line must be a finding, i.e. carry a rule code -- not context.
    assert all(":" in ln for ln in non_empty), raw


def test_count_findings_ignores_test_asserts(tmp_path):
    """S101 flags every `assert`, of which this repo has ~324 in pytest files.
    Counting them would add noise that can never reach zero."""
    src = tmp_path / "t.py"
    src.write_text("def test_x():\n    assert True\n", encoding="utf-8")

    count, raw = budget.count_findings(tmp_path)

    assert count == 0, raw


def test_count_findings_sees_rules_absent_from_ruff_toml(tmp_path):
    """The reason this gate exists: these findings are invisible to
    `ruff check .` because `select` omits their families."""
    src = tmp_path / "m.py"
    src.write_text(
        "def f():\n    try:\n        pass\n    except Exception:\n        return 1\n",
        encoding="utf-8",
    )

    _, raw = budget.count_findings(tmp_path)

    assert "BLE001" in raw, raw


def test_count_findings_zero_on_clean_tree(tmp_path):
    (tmp_path / "m.py").write_text("x = 1\n", encoding="utf-8")
    count, raw = budget.count_findings(tmp_path)
    assert count == 0, raw


# --- main (the ratchet itself) -----------------------------------------------


def _patch(monkeypatch, actual, budget_value):
    monkeypatch.setattr(budget, "count_findings", lambda root=None: (actual, ""))
    monkeypatch.setattr(budget, "load_budget", lambda *a, **k: budget_value)
    monkeypatch.setattr(sys, "argv", ["check_lint_budget.py"])


def test_main_fails_when_over_budget(monkeypatch, capsys):
    """The one behaviour that makes this a gate rather than a report."""
    _patch(monkeypatch, actual=40, budget_value=39)
    assert budget.main() == 1
    assert "over budget" in capsys.readouterr().out


def test_main_passes_at_budget(monkeypatch, capsys):
    _patch(monkeypatch, actual=39, budget_value=39)
    assert budget.main() == 0
    assert "At budget" in capsys.readouterr().out


def test_main_passes_under_budget_and_asks_for_a_ratchet(monkeypatch, capsys):
    """Under budget must not just pass quietly: an un-lowered budget lets the
    gain be silently lost the next time someone adds a finding."""
    _patch(monkeypatch, actual=30, budget_value=39)
    assert budget.main() == 0
    out = capsys.readouterr().out
    assert "Lower maxFindings to 30" in out


def test_main_fails_on_malformed_budget(monkeypatch, capsys):
    def boom(*a, **k):
        raise ValueError("bad budget")
    monkeypatch.setattr(budget, "load_budget", boom)
    monkeypatch.setattr(sys, "argv", ["check_lint_budget.py"])
    assert budget.main() == 1
    assert "bad budget" in capsys.readouterr().out


# --- the shipped budget ------------------------------------------------------


def test_shipped_budget_matches_reality():
    """Guards against the budget and the tree drifting apart -- a budget set
    well above the real count is a gate that can never fail."""
    actual, raw = budget.count_findings(ROOT)
    shipped = budget.load_budget()
    assert actual <= shipped, f"{actual} findings vs budget {shipped}:\n{raw}"
    assert actual == shipped, (
        f"budget is {shipped} but only {actual} findings remain -- "
        f"lower maxFindings to {actual}"
    )
