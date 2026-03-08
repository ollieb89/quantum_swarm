"""Unit tests for memory_writer_node (EVOL-01 + Plan 19-02 suspension gate).

Tests use tmp_path to isolate all MEMORY.md I/O from real souls/ directories.
"""
from __future__ import annotations

import asyncio
import inspect
import logging
import re
import stat
import textwrap
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import src.graph.nodes.memory_writer as mw_mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_state(
    macro_report=None,
    bullish_thesis=None,
    bearish_thesis=None,
    quant_proposal=None,
    risk_approval=None,
    merit_scores=None,
    active_persona=None,
):
    return {
        "macro_report": macro_report,
        "bullish_thesis": bullish_thesis,
        "bearish_thesis": bearish_thesis,
        "quant_proposal": quant_proposal,
        "risk_approval": risk_approval,
        "merit_scores": merit_scores or {},
        "active_persona": active_persona,
    }


def _count_entries(memory_path: Path) -> int:
    """Count the number of === timestamp === headers in a MEMORY.md file."""
    if not memory_path.exists():
        return 0
    content = memory_path.read_text()
    return len(re.findall(r"^=== .+ ===$", content, re.MULTILINE))


def _seed_entries(memory_path: Path, n: int) -> None:
    """Pre-seed MEMORY.md with n structured entries."""
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for i in range(n):
        lines.append(f"=== 2026-01-{i+1:02d}T00:00:00Z ===")
        lines.append("[AGENT:] AXIOM")
        lines.append("[KAMI_DELTA:] +0.00")
        lines.append(f"[MERIT_SCORE:] {0.50 + i * 0.001:.4f}")
        lines.append("[DRIFT_FLAGS:] none")
        lines.append("[THESIS_SUMMARY:] Seeded entry.")
        lines.append("")
    memory_path.write_text("\n".join(lines))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def patch_souls_dir(tmp_path, monkeypatch):
    """Redirect _get_souls_dir to tmp_path for all tests in this module."""
    monkeypatch.setattr(mw_mod, "_get_souls_dir", lambda: tmp_path)
    yield tmp_path


# ---------------------------------------------------------------------------
# Test 1: Entry is written with all required labeled fields
# ---------------------------------------------------------------------------

def test_memory_entry_written(tmp_path):
    """After calling memory_writer_node with macro_report, MEMORY.md for
    macro_analyst has exactly one entry with all required labeled fields."""
    state = _make_state(macro_report={"content": "Inflation is elevated."})
    asyncio.run(mw_mod.memory_writer_node(state))

    memory_path = tmp_path / "macro_analyst" / "MEMORY.md"
    assert memory_path.exists(), "MEMORY.md was not created for macro_analyst"

    content = memory_path.read_text()
    assert re.search(r"^=== .+ ===$", content, re.MULTILINE), "Missing timestamp header"
    assert "[AGENT:] AXIOM" in content
    assert "[KAMI_DELTA:]" in content
    assert "[MERIT_SCORE:]" in content
    assert "[DRIFT_FLAGS:] none" in content
    assert "[THESIS_SUMMARY:] Inflation is elevated." in content


# ---------------------------------------------------------------------------
# Test 2: Cap enforcement — 51st write results in exactly 50 entries
# ---------------------------------------------------------------------------

def test_memory_cap_enforced(tmp_path):
    """A MEMORY.md pre-seeded with 50 entries gains a 51st entry but the file
    still has exactly 50 entries after (oldest dropped)."""
    memory_path = tmp_path / "macro_analyst" / "MEMORY.md"
    _seed_entries(memory_path, 50)
    assert _count_entries(memory_path) == 50

    state = _make_state(macro_report={"content": "New cycle signal."})
    asyncio.run(mw_mod.memory_writer_node(state))

    assert _count_entries(memory_path) == 50, (
        f"Expected 50 entries after cap; got {_count_entries(memory_path)}"
    )
    # Confirm the new entry is present (newest at bottom)
    content = memory_path.read_text()
    assert "New cycle signal." in content


# ---------------------------------------------------------------------------
# Test 3: Skip-on-no-output — no files created when all fields are None
# ---------------------------------------------------------------------------

def test_skip_on_no_output(tmp_path):
    """Calling memory_writer_node with all canonical fields None leaves all
    MEMORY.md files unchanged (no new files created)."""
    state = _make_state()  # all canonical fields default to None
    asyncio.run(mw_mod.memory_writer_node(state))

    for agent_id in mw_mod.HANDLE_TO_AGENT_ID.values():
        memory_path = tmp_path / agent_id / "MEMORY.md"
        assert not memory_path.exists(), (
            f"MEMORY.md should NOT have been created for {agent_id} on empty state"
        )


# ---------------------------------------------------------------------------
# Test 4: KAMI delta computed correctly from prev score
# ---------------------------------------------------------------------------

def test_kami_delta_computed(tmp_path):
    """If previous MEMORY entry has [MERIT_SCORE:] 0.70 and current merit_scores
    has composite 0.74, the new entry's [KAMI_DELTA:] is '+0.04'."""
    memory_path = tmp_path / "macro_analyst" / "MEMORY.md"
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    # Seed one entry with MERIT_SCORE 0.70
    memory_path.write_text(textwrap.dedent("""\
        === 2026-03-07T10:00:00Z ===
        [AGENT:] AXIOM
        [KAMI_DELTA:] +0.00
        [MERIT_SCORE:] 0.70
        [DRIFT_FLAGS:] none
        [THESIS_SUMMARY:] Prior cycle baseline.
    """))

    state = _make_state(
        macro_report={"content": "Current cycle analysis."},
        merit_scores={"AXIOM": {"composite": 0.74}},
    )
    asyncio.run(mw_mod.memory_writer_node(state))

    content = memory_path.read_text()
    assert "[KAMI_DELTA:] +0.04" in content, (
        f"Expected [KAMI_DELTA:] +0.04 in content:\n{content}"
    )


# ---------------------------------------------------------------------------
# Test 5: memory_writer_node always returns {}
# ---------------------------------------------------------------------------

def test_memory_writer_silent(tmp_path):
    """memory_writer_node returns {} for any state."""
    state = _make_state(macro_report={"content": "Test."})
    result = asyncio.run(mw_mod.memory_writer_node(state))
    assert result == {}, f"Expected empty dict, got {result!r}"

    # Also test with empty state
    state2 = _make_state()
    result2 = asyncio.run(mw_mod.memory_writer_node(state2))
    assert result2 == {}, f"Expected empty dict for empty state, got {result2!r}"


# ---------------------------------------------------------------------------
# Test 6: Non-blocking on write failure
# ---------------------------------------------------------------------------

def test_memory_writer_nonblocking(tmp_path):
    """If MEMORY.md parent dir is not writable, memory_writer_node does not
    raise — it logs and continues; returned dict is still {}."""
    # Create the agent dir and chmod 000 to prevent writes
    agent_dir = tmp_path / "macro_analyst"
    agent_dir.mkdir(parents=True, exist_ok=True)
    agent_dir.chmod(0o000)

    state = _make_state(macro_report={"content": "Should be blocked."})
    try:
        result = asyncio.run(mw_mod.memory_writer_node(state))
        assert result == {}, f"Expected {{}}, got {result!r}"
    finally:
        # Restore permissions so tmp_path cleanup can succeed
        agent_dir.chmod(stat.S_IRWXU)


# ---------------------------------------------------------------------------
# Test 7: evolution_suspended=True skips MEMORY.md write and proposal emission
# ---------------------------------------------------------------------------

class TestEvolutionSuspendedGate:
    """Plan 19-02: memory_writer_node checks evolution_suspended from DB."""

    @pytest.fixture(autouse=True)
    def _mock_db(self, monkeypatch):
        """Mock _check_evolution_suspended for suspension gate tests."""
        # Default: no agents suspended (tests override per-case)
        self._suspended_handles: set = set()

        async def _fake_check(handle: str) -> bool:
            return handle in self._suspended_handles

        monkeypatch.setattr(mw_mod, "_check_evolution_suspended", _fake_check)

    def test_suspended_agent_skips_memory_write(self, tmp_path):
        """When evolution_suspended=True for AXIOM, no MEMORY.md is written."""
        self._suspended_handles.add("AXIOM")
        state = _make_state(macro_report={"content": "Should be skipped."})
        asyncio.run(mw_mod.memory_writer_node(state))

        memory_path = tmp_path / "macro_analyst" / "MEMORY.md"
        assert not memory_path.exists(), (
            "MEMORY.md should NOT be created for a suspended agent"
        )

    def test_non_suspended_agent_writes_normally(self, tmp_path):
        """When evolution_suspended=False, MEMORY.md write proceeds."""
        # _suspended_handles is empty → all agents are non-suspended
        state = _make_state(macro_report={"content": "Should be written."})
        asyncio.run(mw_mod.memory_writer_node(state))

        memory_path = tmp_path / "macro_analyst" / "MEMORY.md"
        assert memory_path.exists(), (
            "MEMORY.md should be created for a non-suspended agent"
        )
        content = memory_path.read_text()
        assert "Should be written." in content

    def test_absent_suspension_key_proceeds_normally(self, tmp_path):
        """Backward compat: if _check_evolution_suspended returns False
        (default/absent), memory write proceeds normally."""
        state = _make_state(macro_report={"content": "Backward compat."})
        asyncio.run(mw_mod.memory_writer_node(state))

        memory_path = tmp_path / "macro_analyst" / "MEMORY.md"
        assert memory_path.exists()

    def test_suspended_agent_logs_warning(self, tmp_path, caplog):
        """Suspended agent produces a log line containing
        'memory_writer skipped due to evolution_suspended'."""
        self._suspended_handles.add("AXIOM")
        state = _make_state(macro_report={"content": "Should be skipped."})
        with caplog.at_level(logging.WARNING):
            asyncio.run(mw_mod.memory_writer_node(state))

        assert any(
            "memory_writer skipped due to evolution_suspended" in rec.message
            for rec in caplog.records
        ), f"Expected suspension log line; got: {[r.message for r in caplog.records]}"


# ---------------------------------------------------------------------------
# Test 8: Negative assertions — evolution_suspended NOT in trade paths
# ---------------------------------------------------------------------------

class TestTradePathIsolation:
    """ARS-02: evolution_suspended must NEVER appear in trade execution code."""

    def test_order_router_no_evolution_suspended(self):
        """order_router.py source does NOT contain 'evolution_suspended'."""
        source_path = Path(__file__).parents[2] / "src" / "graph" / "agents" / "l3" / "order_router.py"
        source = source_path.read_text()
        assert "evolution_suspended" not in source, (
            "order_router.py must NOT reference evolution_suspended"
        )

    def test_route_after_institutional_guard_no_evolution_suspended(self):
        """route_after_institutional_guard function does NOT contain
        'evolution_suspended'."""
        from src.graph.orchestrator import route_after_institutional_guard
        source = inspect.getsource(route_after_institutional_guard)
        assert "evolution_suspended" not in source, (
            "route_after_institutional_guard must NOT reference evolution_suspended"
        )


# ---------------------------------------------------------------------------
# Test 9: _build_entry drift_flags parameter (Plan 20-02)
# ---------------------------------------------------------------------------

class TestBuildEntryDriftFlags:
    """Plan 20-02: _build_entry accepts drift_flags and writes them to the entry."""

    def test_build_entry_default_none(self):
        """_build_entry with no drift_flags kwarg writes [DRIFT_FLAGS:] none."""
        entry = mw_mod._build_entry("AXIOM", 0.01, 0.80, "Test thesis.")
        assert "[DRIFT_FLAGS:] none" in entry

    def test_build_entry_with_flags(self):
        """_build_entry with drift_flags='recency_bias,narrative_capture' writes them."""
        entry = mw_mod._build_entry(
            "AXIOM", 0.01, 0.80, "Test thesis.",
            drift_flags="recency_bias,narrative_capture",
        )
        assert "[DRIFT_FLAGS:] recency_bias,narrative_capture" in entry

    def test_build_entry_evaluation_failed(self):
        """_build_entry with drift_flags='evaluation_failed' writes the sentinel."""
        entry = mw_mod._build_entry(
            "AXIOM", 0.01, 0.80, "Test thesis.",
            drift_flags="evaluation_failed",
        )
        assert "[DRIFT_FLAGS:] evaluation_failed" in entry


# ---------------------------------------------------------------------------
# Test 10: _evaluate_drift_flags helper (Plan 20-02)
# ---------------------------------------------------------------------------

class TestEvaluateDriftFlags:
    """Plan 20-02: _evaluate_drift_flags returns correct flag strings."""

    def test_matching_rules_return_flag_ids(self, monkeypatch):
        """Agent with drift rules that match text returns comma-separated flag_ids."""
        from src.core.drift_eval import DriftRule
        from src.core.soul_loader import AgentSoul

        mock_soul = AgentSoul(
            agent_id="macro_analyst",
            identity="# AXIOM",
            soul="test soul",
            agents="test agents",
            drift_rules=(
                DriftRule(flag_id="recency_bias", type="keyword_any", include=("latest",)),
            ),
        )
        monkeypatch.setattr(mw_mod, "load_soul", lambda _: mock_soul)

        result = mw_mod._evaluate_drift_flags("macro_analyst", "The latest data shows growth.")
        assert result == "recency_bias"

    def test_no_match_returns_none(self, monkeypatch):
        """Agent with drift rules that don't match returns 'none'."""
        from src.core.drift_eval import DriftRule
        from src.core.soul_loader import AgentSoul

        mock_soul = AgentSoul(
            agent_id="macro_analyst",
            identity="# AXIOM",
            soul="test soul",
            agents="test agents",
            drift_rules=(
                DriftRule(flag_id="recency_bias", type="keyword_any", include=("latest",)),
            ),
        )
        monkeypatch.setattr(mw_mod, "load_soul", lambda _: mock_soul)

        result = mw_mod._evaluate_drift_flags("macro_analyst", "Structural regime analysis.")
        assert result == "none"

    def test_no_drift_rules_returns_none(self, monkeypatch):
        """Agent with empty drift_rules returns 'none'."""
        from src.core.soul_loader import AgentSoul

        mock_soul = AgentSoul(
            agent_id="bullish_researcher",
            identity="# MOMENTUM",
            soul="test soul",
            agents="test agents",
            drift_rules=(),
        )
        monkeypatch.setattr(mw_mod, "load_soul", lambda _: mock_soul)

        result = mw_mod._evaluate_drift_flags("bullish_researcher", "Some output text.")
        assert result == "none"

    def test_exception_returns_evaluation_failed(self, monkeypatch):
        """If load_soul raises, _evaluate_drift_flags returns 'evaluation_failed'."""
        monkeypatch.setattr(
            mw_mod, "load_soul",
            MagicMock(side_effect=RuntimeError("broken")),
        )

        result = mw_mod._evaluate_drift_flags("macro_analyst", "Some text.")
        assert result == "evaluation_failed"


# ---------------------------------------------------------------------------
# Test 11: _process_agent drift integration (Plan 20-02)
# ---------------------------------------------------------------------------

class TestProcessAgentDrift:
    """Plan 20-02: _process_agent computes drift flags from soul rules."""

    @pytest.fixture(autouse=True)
    def _mock_db(self, monkeypatch):
        """Disable evolution suspension check for drift integration tests."""
        async def _fake_check(handle: str) -> bool:
            return False
        monkeypatch.setattr(mw_mod, "_check_evolution_suspended", _fake_check)

    def test_axiom_matching_output_writes_flags(self, tmp_path, monkeypatch):
        """AXIOM with output matching drift rules writes non-empty drift flags."""
        from src.core.drift_eval import DriftRule
        from src.core.soul_loader import AgentSoul

        mock_soul = AgentSoul(
            agent_id="macro_analyst",
            identity="# AXIOM",
            soul="test soul",
            agents="test agents",
            drift_rules=(
                DriftRule(flag_id="narrative_capture", type="keyword_any",
                          include=("consensus expects",)),
            ),
        )
        monkeypatch.setattr(mw_mod, "load_soul", lambda _: mock_soul)

        state = _make_state(
            macro_report={"content": "The consensus expects inflation to fall."},
            merit_scores={"AXIOM": {"composite": 0.75}},
        )
        asyncio.run(mw_mod.memory_writer_node(state))

        memory_path = tmp_path / "macro_analyst" / "MEMORY.md"
        content = memory_path.read_text()
        assert "[DRIFT_FLAGS:] narrative_capture" in content

    def test_axiom_clean_output_writes_none(self, tmp_path, monkeypatch):
        """AXIOM with clean output text writes [DRIFT_FLAGS:] none."""
        from src.core.drift_eval import DriftRule
        from src.core.soul_loader import AgentSoul

        mock_soul = AgentSoul(
            agent_id="macro_analyst",
            identity="# AXIOM",
            soul="test soul",
            agents="test agents",
            drift_rules=(
                DriftRule(flag_id="narrative_capture", type="keyword_any",
                          include=("consensus expects",)),
            ),
        )
        monkeypatch.setattr(mw_mod, "load_soul", lambda _: mock_soul)

        state = _make_state(
            macro_report={"content": "Structural regime analysis shows credit tightening."},
            merit_scores={"AXIOM": {"composite": 0.75}},
        )
        asyncio.run(mw_mod.memory_writer_node(state))

        memory_path = tmp_path / "macro_analyst" / "MEMORY.md"
        content = memory_path.read_text()
        assert "[DRIFT_FLAGS:] none" in content

    def test_skeleton_agent_writes_none(self, tmp_path, monkeypatch):
        """Agent with no drift rules (skeleton) writes [DRIFT_FLAGS:] none."""
        from src.core.soul_loader import AgentSoul

        mock_soul = AgentSoul(
            agent_id="bullish_researcher",
            identity="# MOMENTUM",
            soul="test soul",
            agents="test agents",
            drift_rules=(),
        )
        monkeypatch.setattr(mw_mod, "load_soul", lambda _: mock_soul)

        state = _make_state(
            bullish_thesis="Momentum is building in tech sector.",
            merit_scores={"MOMENTUM": {"composite": 0.60}},
        )
        asyncio.run(mw_mod.memory_writer_node(state))

        memory_path = tmp_path / "bullish_researcher" / "MEMORY.md"
        content = memory_path.read_text()
        assert "[DRIFT_FLAGS:] none" in content

    def test_drift_eval_exception_writes_evaluation_failed(self, tmp_path, monkeypatch):
        """If drift evaluation throws, _process_agent writes evaluation_failed."""
        monkeypatch.setattr(
            mw_mod, "load_soul",
            MagicMock(side_effect=RuntimeError("soul broken")),
        )

        state = _make_state(
            macro_report={"content": "Some output."},
            merit_scores={"AXIOM": {"composite": 0.75}},
        )
        asyncio.run(mw_mod.memory_writer_node(state))

        memory_path = tmp_path / "macro_analyst" / "MEMORY.md"
        content = memory_path.read_text()
        assert "[DRIFT_FLAGS:] evaluation_failed" in content


# ---------------------------------------------------------------------------
# Test 12: DRIFT_STREAK with real flags (Plan 20-02)
# ---------------------------------------------------------------------------

class TestDriftStreakWithRealFlags:
    """Plan 20-02: DRIFT_STREAK fires when 3+ consecutive entries have flags."""

    def test_drift_streak_fires_with_flagged_entries(self, tmp_path):
        """3 consecutive entries with non-empty drift flags triggers DRIFT_STREAK."""
        memory_path = tmp_path / "macro_analyst" / "MEMORY.md"
        memory_path.parent.mkdir(parents=True, exist_ok=True)

        # Seed 3 entries with drift flags (not "none")
        lines = []
        for i in range(3):
            lines.append(f"=== 2026-03-0{i+1}T00:00:00Z ===")
            lines.append("[AGENT:] AXIOM")
            lines.append("[KAMI_DELTA:] +0.01")
            lines.append(f"[MERIT_SCORE:] 0.{70+i:02d}00")
            lines.append("[DRIFT_FLAGS:] recency_bias")
            lines.append("[THESIS_SUMMARY:] Seeded entry with drift.")
            lines.append("")
        memory_path.write_text("\n".join(lines))

        config = {"drift_streak_n": 3}
        triggers = mw_mod._check_triggers("AXIOM", 0.01, memory_path, config)
        assert "DRIFT_STREAK" in triggers

    def test_drift_streak_does_not_fire_with_none_flags(self, tmp_path):
        """3 consecutive entries with [DRIFT_FLAGS:] none does NOT fire DRIFT_STREAK."""
        memory_path = tmp_path / "macro_analyst" / "MEMORY.md"
        _seed_entries(memory_path, 3)  # _seed_entries writes "none" flags

        config = {"drift_streak_n": 3}
        triggers = mw_mod._check_triggers("AXIOM", 0.01, memory_path, config)
        assert "DRIFT_STREAK" not in triggers


# ---------------------------------------------------------------------------
# Test 13: _extract_drift_flags handles evaluation_failed (Plan 20-02)
# ---------------------------------------------------------------------------

class TestExtractDriftFlagsEvalFailed:
    """Plan 20-02: _extract_drift_flags treats evaluation_failed as non-empty."""

    def test_evaluation_failed_returns_nonempty(self):
        """_extract_drift_flags returns non-empty for 'evaluation_failed'."""
        entry = "[DRIFT_FLAGS:] evaluation_failed"
        result = mw_mod._extract_drift_flags(entry)
        assert result != ""
        assert result == "evaluation_failed"

    def test_none_returns_empty(self):
        """_extract_drift_flags returns empty string for 'none'."""
        entry = "[DRIFT_FLAGS:] none"
        result = mw_mod._extract_drift_flags(entry)
        assert result == ""
