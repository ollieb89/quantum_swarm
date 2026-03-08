"""Unit tests for drift evaluation: DriftRule, parse_drift_guard_yaml, evaluate_drift."""
import pytest
from dataclasses import FrozenInstanceError

from src.core.drift_eval import DriftRule, parse_drift_guard_yaml, evaluate_drift


# --- DriftRule dataclass ---

class TestDriftRule:
    def test_drift_rule_is_frozen(self):
        rule = DriftRule(flag_id="test", type="keyword_any", include=("word",))
        with pytest.raises(FrozenInstanceError):
            rule.flag_id = "changed"

    def test_drift_rule_fields(self):
        rule = DriftRule(
            flag_id="my_flag",
            type="regex",
            pattern=r"\bfoo\b",
            include=(),
            threshold=None,
        )
        assert rule.flag_id == "my_flag"
        assert rule.type == "regex"
        assert rule.pattern == r"\bfoo\b"
        assert rule.include == ()
        assert rule.threshold is None

    def test_drift_rule_defaults(self):
        rule = DriftRule(flag_id="x", type="keyword_any")
        assert rule.pattern is None
        assert rule.include == ()
        assert rule.threshold is None


# --- parse_drift_guard_yaml ---

class TestParseDriftGuardYaml:
    def test_empty_string_returns_empty_tuple(self):
        assert parse_drift_guard_yaml("") == ()

    def test_no_yaml_block_returns_empty_tuple(self):
        text = "## Drift Guard\n\nSome prose about drift.\n"
        assert parse_drift_guard_yaml(text) == ()

    def test_valid_yaml_returns_drift_rules(self):
        text = """## Drift Guard

Some prose.

```yaml
drift_guard:
  version: 1
  rules:
    - flag_id: recency_bias
      type: keyword_ratio
      include: ["today", "latest"]
      threshold: 0.08
    - flag_id: narrative_capture
      type: keyword_any
      include: ["consensus expects", "priced in"]
```
"""
        rules = parse_drift_guard_yaml(text)
        assert len(rules) == 2
        assert isinstance(rules, tuple)
        assert all(isinstance(r, DriftRule) for r in rules)
        assert rules[0].flag_id == "recency_bias"
        assert rules[0].type == "keyword_ratio"
        assert rules[0].threshold == 0.08
        assert rules[0].include == ("today", "latest")
        assert rules[1].flag_id == "narrative_capture"
        assert rules[1].type == "keyword_any"

    def test_malformed_yaml_raises_value_error(self):
        text = """## Drift Guard

```yaml
drift_guard:
  rules:
    - flag_id: [invalid
      type: keyword_any
```
"""
        with pytest.raises(ValueError):
            parse_drift_guard_yaml(text)

    def test_duplicate_flag_id_raises_value_error(self):
        text = """## Drift Guard

```yaml
drift_guard:
  version: 1
  rules:
    - flag_id: same_id
      type: keyword_any
      include: ["foo"]
    - flag_id: same_id
      type: keyword_any
      include: ["bar"]
```
"""
        with pytest.raises(ValueError, match="[Dd]uplicate"):
            parse_drift_guard_yaml(text)

    def test_unknown_type_raises_value_error(self):
        text = """## Drift Guard

```yaml
drift_guard:
  version: 1
  rules:
    - flag_id: bad_type
      type: magic_filter
      include: ["x"]
```
"""
        with pytest.raises(ValueError, match="[Tt]ype"):
            parse_drift_guard_yaml(text)

    def test_keyword_ratio_missing_threshold_raises_value_error(self):
        text = """## Drift Guard

```yaml
drift_guard:
  version: 1
  rules:
    - flag_id: no_thresh
      type: keyword_ratio
      include: ["today"]
```
"""
        with pytest.raises(ValueError, match="threshold"):
            parse_drift_guard_yaml(text)

    def test_invalid_regex_raises_value_error(self):
        text = """## Drift Guard

```yaml
drift_guard:
  version: 1
  rules:
    - flag_id: bad_regex
      type: regex
      pattern: "[invalid(("
```
"""
        with pytest.raises(ValueError, match="[Rr]egex|[Pp]attern"):
            parse_drift_guard_yaml(text)

    def test_evaluation_failed_flag_id_rejected(self):
        text = """## Drift Guard

```yaml
drift_guard:
  version: 1
  rules:
    - flag_id: evaluation_failed
      type: keyword_any
      include: ["x"]
```
"""
        with pytest.raises(ValueError, match="evaluation_failed"):
            parse_drift_guard_yaml(text)


# --- evaluate_drift ---

class TestEvaluateDrift:
    def test_no_rules_returns_empty_list(self):
        assert evaluate_drift((), "any text at all") == []

    def test_keyword_ratio_matches_above_threshold(self):
        rule = DriftRule(
            flag_id="recency",
            type="keyword_ratio",
            include=("today", "latest"),
            threshold=0.1,
        )
        # 2 out of 10 words match = 0.2 >= 0.1
        text = "today the latest report shows strong economic data from analysts"
        result = evaluate_drift((rule,), text)
        assert "recency" in result

    def test_keyword_ratio_no_match_below_threshold(self):
        rule = DriftRule(
            flag_id="recency",
            type="keyword_ratio",
            include=("today", "latest"),
            threshold=0.5,
        )
        text = "today the report shows strong economic data from analysts worldwide now"
        result = evaluate_drift((rule,), text)
        assert "recency" not in result

    def test_keyword_any_matches_when_term_present(self):
        rule = DriftRule(
            flag_id="narrative",
            type="keyword_any",
            include=("consensus expects", "priced in"),
        )
        text = "The market consensus expects further rate hikes."
        result = evaluate_drift((rule,), text)
        assert "narrative" in result

    def test_keyword_any_no_match_when_absent(self):
        rule = DriftRule(
            flag_id="narrative",
            type="keyword_any",
            include=("consensus expects", "priced in"),
        )
        text = "The macro regime remains uncertain given mixed signals."
        result = evaluate_drift((rule,), text)
        assert "narrative" not in result

    def test_regex_matches(self):
        rule = DriftRule(
            flag_id="certainty",
            type="regex",
            pattern=r"\b(certainly|guaranteed)\b",
        )
        text = "This outcome is certainly going to happen."
        result = evaluate_drift((rule,), text)
        assert "certainty" in result

    def test_regex_no_match(self):
        rule = DriftRule(
            flag_id="certainty",
            type="regex",
            pattern=r"\b(certainly|guaranteed)\b",
        )
        text = "This outcome is probable given current conditions."
        result = evaluate_drift((rule,), text)
        assert "certainty" not in result

    def test_multiple_rules_returns_all_matching(self):
        rule_a = DriftRule(
            flag_id="recency",
            type="keyword_any",
            include=("today",),
        )
        rule_b = DriftRule(
            flag_id="certainty",
            type="regex",
            pattern=r"\bcertainly\b",
        )
        rule_c = DriftRule(
            flag_id="no_match",
            type="keyword_any",
            include=("xyznonexistent",),
        )
        text = "Today it is certainly the case that rates will rise."
        result = evaluate_drift((rule_a, rule_b, rule_c), text)
        assert "recency" in result
        assert "certainty" in result
        assert "no_match" not in result

    def test_keyword_ratio_case_insensitive(self):
        rule = DriftRule(
            flag_id="recency",
            type="keyword_ratio",
            include=("TODAY", "LATEST"),
            threshold=0.1,
        )
        text = "today the latest data suggests a shift in regime"
        result = evaluate_drift((rule,), text)
        assert "recency" in result

    def test_keyword_any_case_insensitive(self):
        rule = DriftRule(
            flag_id="narrative",
            type="keyword_any",
            include=("CONSENSUS EXPECTS",),
        )
        text = "The consensus expects further rate hikes."
        result = evaluate_drift((rule,), text)
        assert "narrative" in result

    def test_regex_runs_on_original_text(self):
        rule = DriftRule(
            flag_id="caps_check",
            type="regex",
            pattern=r"CERTAINLY",
        )
        # Original text has uppercase CERTAINLY
        text = "This is CERTAINLY the case."
        result = evaluate_drift((rule,), text)
        assert "caps_check" in result

    def test_regex_case_sensitive_by_default(self):
        rule = DriftRule(
            flag_id="caps_check",
            type="regex",
            pattern=r"CERTAINLY",
        )
        # Original text has lowercase certainly
        text = "This is certainly the case."
        result = evaluate_drift((rule,), text)
        assert "caps_check" not in result
