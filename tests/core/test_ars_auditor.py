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

import inspect
import re

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
