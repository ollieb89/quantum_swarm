"""ARS Drift Auditor — deterministic test suite.

Phase 19, Plan 01.

Tests cover:
  - Config loading from swarm_config.yaml
  - ars_state DDL presence in persistence.py
  - Import boundary compliance
  - All 5 drift metrics (Task 2)
  - Warm-up enforcement
  - Flag-then-suspend escalation
  - CLI flags
  - Audit event schema
"""
from __future__ import annotations

import asyncio
import inspect
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml


# ---------------------------------------------------------------------------
# Task 1 tests: Config + DDL + import boundaries
# ---------------------------------------------------------------------------


class TestARSConfig:
    """Verify ars: config section in swarm_config.yaml."""

    def _load_config(self) -> dict:
        from pathlib import Path
        config_path = Path(__file__).parents[2] / "config" / "swarm_config.yaml"
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_ars_section_exists(self):
        cfg = self._load_config()
        assert "ars" in cfg, "swarm_config.yaml must have an 'ars:' section"

    def test_warmup_min_entries(self):
        ars = self._load_config()["ars"]
        assert ars["warmup_min_entries"] == 30

    def test_consecutive_breaches_to_suspend(self):
        ars = self._load_config()["ars"]
        assert ars["consecutive_breaches_to_suspend"] == 3

    def test_proposal_rejection_rate_threshold(self):
        ars = self._load_config()["ars"]
        assert ars["proposal_rejection_rate_threshold"] == 0.5

    def test_drift_flag_frequency_threshold(self):
        ars = self._load_config()["ars"]
        assert ars["drift_flag_frequency_threshold"] == 0.3

    def test_kami_variance_threshold(self):
        ars = self._load_config()["ars"]
        assert ars["kami_variance_threshold"] == 0.04

    def test_alignment_mutation_count_threshold(self):
        ars = self._load_config()["ars"]
        assert ars["alignment_mutation_count_threshold"] == 3

    def test_sentiment_distance_threshold(self):
        ars = self._load_config()["ars"]
        assert ars["sentiment_distance_threshold"] == 0.3

    def test_sentiment_polarity_threshold(self):
        ars = self._load_config()["ars"]
        assert ars["sentiment_polarity_threshold"] == 0.15

    def test_role_boundary_score_threshold(self):
        ars = self._load_config()["ars"]
        assert ars["role_boundary_score_threshold"] == 0.02

    def test_role_boundary_min_hits(self):
        ars = self._load_config()["ars"]
        assert ars["role_boundary_min_hits"] == 3

    def test_sentiment_baseline_window(self):
        ars = self._load_config()["ars"]
        assert ars["sentiment_baseline_window"] == 10

    def test_trailing_window(self):
        ars = self._load_config()["ars"]
        assert ars["trailing_window"] == 20

    def test_bullish_terms_lexicon(self):
        ars = self._load_config()["ars"]
        assert "rally" in ars["bullish_terms"]
        assert len(ars["bullish_terms"]) >= 10

    def test_bearish_terms_lexicon(self):
        ars = self._load_config()["ars"]
        assert "capitulation" in ars["bearish_terms"]
        assert len(ars["bearish_terms"]) >= 10

    def test_uncertainty_terms_lexicon(self):
        ars = self._load_config()["ars"]
        assert "uncertain" in ars["uncertainty_terms"]

    def test_assertion_markers(self):
        ars = self._load_config()["ars"]
        assert "likely" in ars["assertion_markers"]

    def test_negation_markers(self):
        ars = self._load_config()["ars"]
        assert "not" in ars["negation_markers"]

    def test_forbidden_vocabulary_cassandra(self):
        ars = self._load_config()["ars"]
        fv = ars["forbidden_vocabulary"]
        assert "breakout" in fv["CASSANDRA"]
        assert "opportunity" in fv["CASSANDRA"]

    def test_forbidden_vocabulary_momentum(self):
        ars = self._load_config()["ars"]
        fv = ars["forbidden_vocabulary"]
        assert "capitulation" in fv["MOMENTUM"]

    def test_forbidden_vocabulary_neutral_agents_empty(self):
        ars = self._load_config()["ars"]
        fv = ars["forbidden_vocabulary"]
        assert fv["AXIOM"] == []
        assert fv["SIGMA"] == []
        assert fv["GUARDIAN"] == []


class TestARSStateDDL:
    """Verify ars_state table DDL in persistence.py."""

    def test_ars_state_in_setup_persistence(self):
        import src.core.persistence as mod
        source = inspect.getsource(mod.setup_persistence)
        assert "ars_state" in source, "setup_persistence must include ars_state DDL"

    def test_ars_state_columns(self):
        import src.core.persistence as mod
        source = inspect.getsource(mod.setup_persistence)
        assert "soul_handle" in source
        assert "metric_name" in source
        assert "breach_count" in source
        assert "last_audit_ts" in source

    def test_ars_state_primary_key(self):
        import src.core.persistence as mod
        source = inspect.getsource(mod.setup_persistence)
        assert "PRIMARY KEY (soul_handle, metric_name)" in source


# ---------------------------------------------------------------------------
# Task 2 tests: 5 drift metrics, warm-up, flag-then-suspend, CLI, audit events
# ---------------------------------------------------------------------------


def _make_memory_entry(
    handle: str = "AXIOM",
    merit_score: float = 0.81,
    kami_delta: str = "+0.04",
    drift_flags: str = "none",
    thesis: str = "Inflation surprise risk remains underpriced.",
    ts: str = "2026-03-08T12:34:56Z",
) -> str:
    """Build a single MEMORY.md entry string for testing."""
    return (
        f"=== {ts} ===\n"
        f"[AGENT:] {handle}\n"
        f"[KAMI_DELTA:] {kami_delta}\n"
        f"[MERIT_SCORE:] {merit_score:.4f}\n"
        f"[DRIFT_FLAGS:] {drift_flags}\n"
        f"[THESIS_SUMMARY:] {thesis}\n\n"
    )


def _make_memory_content(n: int, **kwargs) -> str:
    """Build MEMORY.md content with n entries."""
    entries = []
    for i in range(n):
        ts = f"2026-03-{8 + i // 24:02d}T{i % 24:02d}:00:00Z"
        entries.append(_make_memory_entry(ts=ts, **kwargs))
    return "".join(entries)


def _make_proposal_json(
    agent_id: str = "AXIOM",
    status: str = "rejected",
    target_section: str = "## Core Beliefs",
    proposed_at: str = "2026-03-08T12:00:00+00:00",
) -> dict:
    """Build a soul proposal dict for testing."""
    return {
        "proposal_id": f"test_{agent_id}_{status}",
        "agent_id": agent_id,
        "target_section": target_section,
        "proposed_content": "test content",
        "proposal_reasons": ["KAMI_SPIKE"],
        "rationale": "test",
        "proposed_at": proposed_at,
        "status": status,
        "rejection_reason": None,
    }


class TestProposalRejectionRate:
    """Metric 1a: proposal rejection rate."""

    def test_returns_ratio(self, tmp_path):
        import src.core.ars_auditor as mod

        # Create 4 proposals: 2 rejected, 1 approved, 1 pending
        for i, status in enumerate(["rejected", "rejected", "approved", "pending"]):
            p = _make_proposal_json(agent_id="AXIOM", status=status)
            p["proposal_id"] = f"test_{i}"
            (tmp_path / f"test_{i}.json").write_text(json.dumps(p))

        rate = mod._compute_proposal_rejection_rate("AXIOM", tmp_path, window=100)
        # 2 rejected / 4 total = 0.5
        assert rate == pytest.approx(0.5)

    def test_no_proposals_returns_zero(self, tmp_path):
        import src.core.ars_auditor as mod
        rate = mod._compute_proposal_rejection_rate("AXIOM", tmp_path, window=100)
        assert rate == 0.0

    def test_filters_by_agent(self, tmp_path):
        import src.core.ars_auditor as mod

        # AXIOM: 1 rejected, 1 approved
        for i, status in enumerate(["rejected", "approved"]):
            p = _make_proposal_json(agent_id="AXIOM", status=status)
            p["proposal_id"] = f"axiom_{i}"
            (tmp_path / f"axiom_{i}.json").write_text(json.dumps(p))

        # MOMENTUM: 1 rejected (should not count for AXIOM)
        p = _make_proposal_json(agent_id="MOMENTUM", status="rejected")
        p["proposal_id"] = "mom_0"
        (tmp_path / "mom_0.json").write_text(json.dumps(p))

        rate = mod._compute_proposal_rejection_rate("AXIOM", tmp_path, window=100)
        assert rate == pytest.approx(0.5)  # 1/2, not 2/3


class TestDriftFlagFrequency:
    """Metric 1b: drift flag frequency over trailing window."""

    def test_returns_ratio(self):
        import src.core.ars_auditor as mod

        # 10 entries: 3 with drift flags
        entries = []
        for i in range(10):
            flags = "KAMI_SPIKE" if i < 3 else "none"
            entries.append(_make_memory_entry(drift_flags=flags, ts=f"2026-03-08T{i:02d}:00:00Z"))

        freq = mod._compute_drift_flag_frequency(entries, window=10)
        assert freq == pytest.approx(0.3)

    def test_trailing_window_slice(self):
        import src.core.ars_auditor as mod

        # 30 entries: first 10 all have flags, last 20 clean
        entries = []
        for i in range(30):
            flags = "KAMI_SPIKE" if i < 10 else "none"
            entries.append(_make_memory_entry(drift_flags=flags, ts=f"2026-03-{8 + i // 24:02d}T{i % 24:02d}:00:00Z"))

        freq = mod._compute_drift_flag_frequency(entries, window=20)
        # Only last 20 entries: all clean
        assert freq == pytest.approx(0.0)

    def test_all_flagged(self):
        import src.core.ars_auditor as mod
        entries = [_make_memory_entry(drift_flags="DRIFT_STREAK", ts=f"2026-03-08T{i:02d}:00:00Z") for i in range(5)]
        freq = mod._compute_drift_flag_frequency(entries, window=5)
        assert freq == pytest.approx(1.0)


class TestKAMIDimensionVariance:
    """Metric 2: KAMI dimension variance."""

    def test_uniform_dimensions_zero_variance(self):
        import src.core.ars_auditor as mod
        dims = {"accuracy": 0.5, "recovery": 0.5, "consensus": 0.5, "fidelity": 0.5}
        var = mod._compute_kami_dimension_variance(dims)
        assert var == pytest.approx(0.0)

    def test_varied_dimensions(self):
        import src.core.ars_auditor as mod
        dims = {"accuracy": 0.9, "recovery": 0.1, "consensus": 0.5, "fidelity": 0.5}
        var = mod._compute_kami_dimension_variance(dims)
        # variance of [0.9, 0.1, 0.5, 0.5] = var of mean 0.5
        import statistics
        expected = statistics.variance([0.9, 0.1, 0.5, 0.5])
        assert var == pytest.approx(expected)


class TestAlignmentMutationCount:
    """Metric 3: alignment section mutation count."""

    def test_counts_identity_critical_only(self, tmp_path):
        import src.core.ars_auditor as mod

        # 2 approved identity-critical, 1 approved operational, 1 rejected identity
        proposals = [
            {"target_section": "## Core Beliefs", "status": "approved", "agent_id": "AXIOM"},
            {"target_section": "## Drift Guard", "status": "approved", "agent_id": "AXIOM"},
            {"target_section": "## Workflow Rules", "status": "approved", "agent_id": "AXIOM"},
            {"target_section": "## Core Wounds", "status": "rejected", "agent_id": "AXIOM"},
        ]
        for i, p_data in enumerate(proposals):
            p = _make_proposal_json(**p_data)
            p["proposal_id"] = f"test_{i}"
            (tmp_path / f"test_{i}.json").write_text(json.dumps(p))

        count = mod._compute_alignment_mutation_count("AXIOM", tmp_path)
        assert count == 2  # Core Beliefs + Drift Guard approved

    def test_filters_by_agent(self, tmp_path):
        import src.core.ars_auditor as mod

        p1 = _make_proposal_json(agent_id="AXIOM", status="approved", target_section="## Core Beliefs")
        p1["proposal_id"] = "axiom_0"
        (tmp_path / "axiom_0.json").write_text(json.dumps(p1))

        p2 = _make_proposal_json(agent_id="MOMENTUM", status="approved", target_section="## Core Beliefs")
        p2["proposal_id"] = "mom_0"
        (tmp_path / "mom_0.json").write_text(json.dumps(p2))

        count = mod._compute_alignment_mutation_count("AXIOM", tmp_path)
        assert count == 1


class TestSentimentShift:
    """Metric 4: self-reflection sentiment shift."""

    def _get_config(self) -> dict:
        return {
            "bullish_terms": ["rally", "breakout", "opportunity", "upside", "acceleration",
                              "momentum", "bullish", "growth", "outperform", "surge"],
            "bearish_terms": ["capitulation", "structural impairment", "downside spiral", "crash",
                              "collapse", "bearish", "deterioration", "weakness", "underperform", "plunge"],
            "uncertainty_terms": ["uncertain", "unclear", "volatile", "ambiguous", "mixed",
                                   "conflicting", "unpredictable"],
            "sentiment_baseline_window": 10,
        }

    def test_stable_sentiment_low_distance(self):
        """Entries with identical thesis => distance ~0, polarity_delta ~0."""
        import src.core.ars_auditor as mod

        entries = [
            _make_memory_entry(thesis="Market rally continues with bullish momentum and growth.", ts=f"2026-03-08T{i:02d}:00:00Z")
            for i in range(12)
        ]
        dist, polarity_delta = mod._compute_sentiment_shift(entries, self._get_config())
        assert dist < 0.1
        assert abs(polarity_delta) < 0.1

    def test_sentiment_reversal_high_distance(self):
        """Baseline bullish entries + sudden bearish entry => high distance."""
        import src.core.ars_auditor as mod

        # 10 bullish entries for baseline
        entries = [
            _make_memory_entry(thesis="Rally breakout opportunity upside bullish growth surge.", ts=f"2026-03-08T{i:02d}:00:00Z")
            for i in range(10)
        ]
        # 1 bearish entry as latest
        entries.append(_make_memory_entry(
            thesis="Capitulation crash collapse bearish deterioration weakness plunge.",
            ts="2026-03-08T10:00:00Z",
        ))
        dist, polarity_delta = mod._compute_sentiment_shift(entries, self._get_config())
        assert dist > 0.3  # should be a large cosine distance
        assert polarity_delta < -0.1  # shifted from bullish to bearish

    def test_too_few_entries_returns_zero(self):
        """Fewer entries than baseline window => (0.0, 0.0)."""
        import src.core.ars_auditor as mod

        entries = [_make_memory_entry(thesis="Rally momentum.", ts="2026-03-08T00:00:00Z")]
        dist, polarity = mod._compute_sentiment_shift(entries, self._get_config())
        assert dist == 0.0
        assert polarity == 0.0


class TestRoleBoundaryViolations:
    """Metric 5: role boundary vocabulary violations."""

    def _get_config(self) -> dict:
        return {
            "forbidden_vocabulary": {
                "CASSANDRA": ["breakout", "opportunity", "upside", "acceleration", "rally", "surge", "outperform"],
                "MOMENTUM": ["capitulation", "structural impairment", "downside spiral", "crash", "collapse", "plunge", "underperform"],
                "AXIOM": [], "SIGMA": [], "GUARDIAN": [],
            },
            "assertion_markers": ["is", "likely", "expect", "suggests", "indicates", "confirms", "signals", "remains"],
            "negation_markers": ["not", "unlikely", "despite", "however", "risk", "but", "although", "without", "neither"],
            "trailing_window": 20,
        }

    def test_no_forbidden_terms_score_zero(self):
        import src.core.ars_auditor as mod
        entries = [_make_memory_entry(
            handle="CASSANDRA", thesis="Deterioration weakness bearish outlook persists.",
            ts=f"2026-03-08T{i:02d}:00:00Z",
        ) for i in range(5)]
        score = mod._compute_role_boundary_violations(entries, "CASSANDRA", self._get_config())
        assert score == pytest.approx(0.0)

    def test_forbidden_with_assertion_context_flags(self):
        import src.core.ars_auditor as mod
        # CASSANDRA says "rally is likely" — forbidden term + assertion context
        entries = [_make_memory_entry(
            handle="CASSANDRA",
            thesis="Market rally is likely and breakout indicates upside acceleration suggests surge.",
            ts=f"2026-03-08T{i:02d}:00:00Z",
        ) for i in range(5)]
        score = mod._compute_role_boundary_violations(entries, "CASSANDRA", self._get_config())
        assert score > 0.0

    def test_forbidden_with_negation_context_not_flagged(self):
        import src.core.ars_auditor as mod
        # CASSANDRA says "not a breakout" — forbidden term but negation context
        entries = [_make_memory_entry(
            handle="CASSANDRA",
            thesis="This is not a breakout despite opportunity claims.",
            ts=f"2026-03-08T{i:02d}:00:00Z",
        ) for i in range(5)]
        score = mod._compute_role_boundary_violations(entries, "CASSANDRA", self._get_config())
        assert score == pytest.approx(0.0)

    def test_agent_with_empty_forbidden_list(self):
        import src.core.ars_auditor as mod
        entries = [_make_memory_entry(
            handle="AXIOM", thesis="Rally breakout bullish surge.",
            ts=f"2026-03-08T{i:02d}:00:00Z",
        ) for i in range(5)]
        score = mod._compute_role_boundary_violations(entries, "AXIOM", self._get_config())
        assert score == pytest.approx(0.0)


class TestWarmUpEnforcement:
    """Agents with <30 MEMORY.md entries never trigger alerts."""

    def test_29_entries_no_alerts(self, tmp_path, monkeypatch):
        import src.core.ars_auditor as mod

        # Setup: 29 entries with high drift — would flag if warm-up not enforced
        souls_dir = tmp_path / "souls"
        agent_dir = souls_dir / "macro_analyst"
        agent_dir.mkdir(parents=True)
        memory = _make_memory_content(29, handle="AXIOM", drift_flags="KAMI_SPIKE")
        (agent_dir / "MEMORY.md").write_text(memory)

        monkeypatch.setattr(mod, "_get_souls_dir", lambda: souls_dir)
        monkeypatch.setattr(mod, "_get_proposals_dir", lambda: tmp_path / "proposals")
        (tmp_path / "proposals").mkdir()

        config = mod._load_ars_config()
        result = asyncio.run(mod.audit_agent("AXIOM", config, dry_run=True))
        assert result["status"] == "warmup"
        assert result["entries"] == 29

    def test_30_entries_can_alert(self, tmp_path, monkeypatch):
        import src.core.ars_auditor as mod

        souls_dir = tmp_path / "souls"
        agent_dir = souls_dir / "macro_analyst"
        agent_dir.mkdir(parents=True)
        memory = _make_memory_content(30, handle="AXIOM", drift_flags="KAMI_SPIKE")
        (agent_dir / "MEMORY.md").write_text(memory)

        monkeypatch.setattr(mod, "_get_souls_dir", lambda: souls_dir)
        monkeypatch.setattr(mod, "_get_proposals_dir", lambda: tmp_path / "proposals")
        monkeypatch.setattr(mod, "_get_audit_path", lambda: tmp_path / "audit.jsonl")
        monkeypatch.setattr(mod, "_load_merit_dimensions", AsyncMock(return_value={"accuracy": 0.5, "recovery": 0.5, "consensus": 0.5, "fidelity": 0.5}))
        (tmp_path / "proposals").mkdir()

        config = mod._load_ars_config()
        result = asyncio.run(mod.audit_agent("AXIOM", config, dry_run=True))
        assert result["status"] != "warmup"


class TestFlagThenSuspend:
    """Breach escalation: WARNING at 1, CRITICAL+suspend at 3 consecutive."""

    def _setup_agent(self, tmp_path, monkeypatch, n_entries=35):
        """Create an agent with enough entries to pass warm-up."""
        import src.core.ars_auditor as mod

        souls_dir = tmp_path / "souls"
        agent_dir = souls_dir / "macro_analyst"
        agent_dir.mkdir(parents=True)
        # All entries have drift flags => drift_flag_frequency will be 1.0 (above 0.3 threshold)
        memory = _make_memory_content(n_entries, handle="AXIOM", drift_flags="KAMI_SPIKE")
        (agent_dir / "MEMORY.md").write_text(memory)

        proposals_dir = tmp_path / "proposals"
        proposals_dir.mkdir()
        monkeypatch.setattr(mod, "_get_souls_dir", lambda: souls_dir)
        monkeypatch.setattr(mod, "_get_proposals_dir", lambda: proposals_dir)

        audit_file = tmp_path / "audit.jsonl"
        monkeypatch.setattr(mod, "_get_audit_path", lambda: audit_file)

        return mod

    def test_first_breach_is_warning(self, tmp_path, monkeypatch):
        mod = self._setup_agent(tmp_path, monkeypatch)
        # Mock DB calls
        monkeypatch.setattr(mod, "_load_breach_counts", AsyncMock(return_value={}))
        monkeypatch.setattr(mod, "_update_breach_count", AsyncMock())
        monkeypatch.setattr(mod, "_suspend_agent", AsyncMock())
        monkeypatch.setattr(mod, "_load_merit_dimensions", AsyncMock(return_value={"accuracy": 0.5, "recovery": 0.5, "consensus": 0.5, "fidelity": 0.5}))

        config = mod._load_ars_config()
        result = asyncio.run(mod.audit_agent("AXIOM", config, dry_run=False))

        # At least one metric should have breached (drift_flag_frequency = 1.0 > 0.3)
        metrics = result.get("metrics", {})
        dff = metrics.get("drift_flag_frequency", {})
        assert dff.get("breached") is True
        assert dff.get("action") == "flag"

        # suspend_agent should NOT have been called
        mod._suspend_agent.assert_not_called()

    def test_three_consecutive_breaches_suspend(self, tmp_path, monkeypatch):
        mod = self._setup_agent(tmp_path, monkeypatch)
        # Simulate 2 previous consecutive breaches
        monkeypatch.setattr(mod, "_load_breach_counts", AsyncMock(return_value={"drift_flag_frequency": 2}))
        monkeypatch.setattr(mod, "_update_breach_count", AsyncMock())
        monkeypatch.setattr(mod, "_suspend_agent", AsyncMock())
        monkeypatch.setattr(mod, "_load_merit_dimensions", AsyncMock(return_value={"accuracy": 0.5, "recovery": 0.5, "consensus": 0.5, "fidelity": 0.5}))

        config = mod._load_ars_config()
        result = asyncio.run(mod.audit_agent("AXIOM", config, dry_run=False))

        metrics = result.get("metrics", {})
        dff = metrics.get("drift_flag_frequency", {})
        assert dff.get("breached") is True
        assert dff.get("action") == "suspend"
        assert dff.get("breach_count") == 3

        # suspend_agent SHOULD have been called
        mod._suspend_agent.assert_called_once_with("AXIOM")

    def test_clean_cycle_resets_breach_counter(self, tmp_path, monkeypatch):
        import src.core.ars_auditor as mod

        souls_dir = tmp_path / "souls"
        agent_dir = souls_dir / "macro_analyst"
        agent_dir.mkdir(parents=True)
        # All clean entries — no drift flags
        memory = _make_memory_content(35, handle="AXIOM", drift_flags="none")
        (agent_dir / "MEMORY.md").write_text(memory)

        proposals_dir = tmp_path / "proposals"
        proposals_dir.mkdir()
        monkeypatch.setattr(mod, "_get_souls_dir", lambda: souls_dir)
        monkeypatch.setattr(mod, "_get_proposals_dir", lambda: proposals_dir)

        audit_file = tmp_path / "audit.jsonl"
        monkeypatch.setattr(mod, "_get_audit_path", lambda: audit_file)

        # Had 2 breaches before, now clean
        monkeypatch.setattr(mod, "_load_breach_counts", AsyncMock(return_value={"drift_flag_frequency": 2}))
        update_mock = AsyncMock()
        monkeypatch.setattr(mod, "_update_breach_count", update_mock)
        monkeypatch.setattr(mod, "_suspend_agent", AsyncMock())
        monkeypatch.setattr(mod, "_load_merit_dimensions", AsyncMock(return_value={"accuracy": 0.5, "recovery": 0.5, "consensus": 0.5, "fidelity": 0.5}))

        config = mod._load_ars_config()
        result = asyncio.run(mod.audit_agent("AXIOM", config, dry_run=False))

        # drift_flag_frequency should not be breached
        metrics = result.get("metrics", {})
        dff = metrics.get("drift_flag_frequency", {})
        assert dff.get("breached") is False

        # Breach counter should have been reset to 0
        # Find the call for drift_flag_frequency reset
        reset_calls = [c for c in update_mock.call_args_list if c.args[1] == "drift_flag_frequency" and c.args[2] == 0]
        assert len(reset_calls) >= 1, "breach counter should reset to 0 on clean cycle"


class TestAgentFilterAndDryRun:
    """CLI-style --agent and --dry-run behavior."""

    def test_agent_filter(self, tmp_path, monkeypatch):
        import src.core.ars_auditor as mod

        souls_dir = tmp_path / "souls"
        # Only create MOMENTUM agent dir
        (souls_dir / "bullish_researcher").mkdir(parents=True)
        memory = _make_memory_content(10, handle="MOMENTUM")
        (souls_dir / "bullish_researcher" / "MEMORY.md").write_text(memory)

        proposals_dir = tmp_path / "proposals"
        proposals_dir.mkdir()
        monkeypatch.setattr(mod, "_get_souls_dir", lambda: souls_dir)
        monkeypatch.setattr(mod, "_get_proposals_dir", lambda: proposals_dir)
        monkeypatch.setattr(mod, "_get_audit_path", lambda: tmp_path / "audit.jsonl")
        monkeypatch.setattr(mod, "_load_breach_counts", AsyncMock(return_value={}))
        monkeypatch.setattr(mod, "_update_breach_count", AsyncMock())
        monkeypatch.setattr(mod, "_suspend_agent", AsyncMock())
        monkeypatch.setattr(mod, "_load_merit_dimensions", AsyncMock(return_value={"accuracy": 0.5, "recovery": 0.5, "consensus": 0.5, "fidelity": 0.5}))

        config = mod._load_ars_config()
        result = asyncio.run(mod.audit_all(config, agent_filter="MOMENTUM", dry_run=True))

        # Only MOMENTUM should be in results
        assert "MOMENTUM" in result
        assert len(result) == 1

    def test_dry_run_skips_db_writes(self, tmp_path, monkeypatch):
        import src.core.ars_auditor as mod

        souls_dir = tmp_path / "souls"
        agent_dir = souls_dir / "macro_analyst"
        agent_dir.mkdir(parents=True)
        memory = _make_memory_content(35, handle="AXIOM", drift_flags="KAMI_SPIKE")
        (agent_dir / "MEMORY.md").write_text(memory)

        proposals_dir = tmp_path / "proposals"
        proposals_dir.mkdir()
        monkeypatch.setattr(mod, "_get_souls_dir", lambda: souls_dir)
        monkeypatch.setattr(mod, "_get_proposals_dir", lambda: proposals_dir)
        monkeypatch.setattr(mod, "_get_audit_path", lambda: tmp_path / "audit.jsonl")

        # These should NOT be called in dry_run
        load_mock = AsyncMock(return_value={})
        update_mock = AsyncMock()
        suspend_mock = AsyncMock()
        monkeypatch.setattr(mod, "_load_breach_counts", load_mock)
        monkeypatch.setattr(mod, "_update_breach_count", update_mock)
        monkeypatch.setattr(mod, "_suspend_agent", suspend_mock)
        monkeypatch.setattr(mod, "_load_merit_dimensions", AsyncMock(return_value={"accuracy": 0.5, "recovery": 0.5, "consensus": 0.5, "fidelity": 0.5}))

        config = mod._load_ars_config()
        result = asyncio.run(mod.audit_agent("AXIOM", config, dry_run=True))

        # DB writes should be skipped
        update_mock.assert_not_called()
        suspend_mock.assert_not_called()


class TestAuditEventSchema:
    """Audit events appended to audit.jsonl with correct schema."""

    def test_audit_event_fields(self, tmp_path, monkeypatch):
        import src.core.ars_auditor as mod

        souls_dir = tmp_path / "souls"
        agent_dir = souls_dir / "macro_analyst"
        agent_dir.mkdir(parents=True)
        memory = _make_memory_content(35, handle="AXIOM", drift_flags="KAMI_SPIKE")
        (agent_dir / "MEMORY.md").write_text(memory)

        proposals_dir = tmp_path / "proposals"
        proposals_dir.mkdir()
        audit_path = tmp_path / "audit.jsonl"

        monkeypatch.setattr(mod, "_get_souls_dir", lambda: souls_dir)
        monkeypatch.setattr(mod, "_get_proposals_dir", lambda: proposals_dir)
        monkeypatch.setattr(mod, "_get_audit_path", lambda: audit_path)
        monkeypatch.setattr(mod, "_load_breach_counts", AsyncMock(return_value={}))
        monkeypatch.setattr(mod, "_update_breach_count", AsyncMock())
        monkeypatch.setattr(mod, "_suspend_agent", AsyncMock())
        monkeypatch.setattr(mod, "_load_merit_dimensions", AsyncMock(return_value={"accuracy": 0.5, "recovery": 0.5, "consensus": 0.5, "fidelity": 0.5}))

        config = mod._load_ars_config()
        asyncio.run(mod.audit_agent("AXIOM", config, dry_run=False))

        # Check audit.jsonl was written
        assert audit_path.exists()
        lines = audit_path.read_text().strip().split("\n")
        assert len(lines) >= 1

        event = json.loads(lines[0])
        required_fields = {"event", "agent", "metric", "value", "threshold", "breach_count", "action", "ts"}
        assert required_fields.issubset(set(event.keys())), f"Missing fields: {required_fields - set(event.keys())}"
        assert event["event"] == "ARS_BREACH"
        assert event["agent"] == "AXIOM"
