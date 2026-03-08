"""Drift evaluation: DriftRule dataclass, YAML parser, and rule evaluator.

Provides the data model and evaluation logic for detecting persona drift
in agent-generated text. Rules are defined in SOUL.md YAML blocks and
evaluated at runtime against agent output.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import yaml


SUPPORTED_TYPES: frozenset[str] = frozenset({"keyword_ratio", "keyword_any", "regex"})

_RESERVED_FLAG_IDS: frozenset[str] = frozenset({"evaluation_failed"})


@dataclass(frozen=True)
class DriftRule:
    """A single drift detection rule. Frozen for immutability and hashability."""

    flag_id: str
    type: str  # one of SUPPORTED_TYPES
    pattern: str | None = None  # regex pattern (for type=regex)
    include: tuple[str, ...] = ()  # keyword list (for keyword_ratio / keyword_any)
    threshold: float | None = None  # ratio threshold (for keyword_ratio)


def parse_drift_guard_yaml(soul_text: str) -> tuple[DriftRule, ...]:
    """Extract and parse a YAML drift_guard block from a SOUL.md text.

    Scans for a fenced ```yaml ... ``` block within the ## Drift Guard section.
    Returns an empty tuple if no YAML block is found.

    Raises:
        ValueError: On malformed YAML, duplicate flag_ids, unknown types,
            missing required fields, invalid regex, or reserved flag_ids.
    """
    if not soul_text:
        return ()

    # Find the ## Drift Guard section
    drift_section_match = re.search(
        r"## Drift Guard\b(.*?)(?=\n## |\Z)", soul_text, re.DOTALL
    )
    if not drift_section_match:
        return ()

    section_text = drift_section_match.group(1)

    # Find fenced yaml block within the section
    yaml_match = re.search(r"```yaml\s*\n(.*?)```", section_text, re.DOTALL)
    if not yaml_match:
        return ()

    yaml_text = yaml_match.group(1)

    try:
        parsed = yaml.safe_load(yaml_text)
    except yaml.YAMLError as e:
        raise ValueError(f"Malformed YAML in drift_guard block: {e}") from e

    if not isinstance(parsed, dict) or "drift_guard" not in parsed:
        raise ValueError("YAML block must contain a top-level 'drift_guard' key")

    guard = parsed["drift_guard"]
    if not isinstance(guard, dict) or "rules" not in guard:
        raise ValueError("drift_guard must contain a 'rules' list")

    raw_rules = guard["rules"]
    if not isinstance(raw_rules, list):
        raise ValueError("drift_guard.rules must be a list")

    seen_ids: set[str] = set()
    rules: list[DriftRule] = []

    for entry in raw_rules:
        flag_id = entry.get("flag_id", "")
        rule_type = entry.get("type", "")

        # Validate flag_id
        if flag_id in _RESERVED_FLAG_IDS:
            raise ValueError(
                f"Reserved flag_id '{flag_id}' cannot be used in drift rules"
            )
        if flag_id in seen_ids:
            raise ValueError(f"Duplicate flag_id: '{flag_id}'")
        seen_ids.add(flag_id)

        # Validate type
        if rule_type not in SUPPORTED_TYPES:
            raise ValueError(
                f"Unknown type '{rule_type}' for flag_id '{flag_id}'. "
                f"Supported types: {sorted(SUPPORTED_TYPES)}"
            )

        # Type-specific validation
        include_raw = entry.get("include", [])
        include = tuple(include_raw) if isinstance(include_raw, list) else ()
        threshold = entry.get("threshold")
        pattern = entry.get("pattern")

        if rule_type == "keyword_ratio":
            if threshold is None:
                raise ValueError(
                    f"keyword_ratio rule '{flag_id}' requires a threshold"
                )

        if rule_type == "regex":
            if pattern is None:
                raise ValueError(
                    f"regex rule '{flag_id}' requires a pattern"
                )
            try:
                re.compile(pattern)
            except re.error as e:
                raise ValueError(
                    f"Invalid regex pattern for '{flag_id}': {e}"
                ) from e

        rules.append(
            DriftRule(
                flag_id=flag_id,
                type=rule_type,
                pattern=pattern,
                include=include,
                threshold=threshold,
            )
        )

    return tuple(rules)


def evaluate_drift(
    drift_rules: tuple[DriftRule, ...], text: str
) -> list[str]:
    """Evaluate text against drift rules and return matched flag_ids.

    Args:
        drift_rules: Tuple of DriftRule instances to evaluate.
        text: The text to check for drift indicators.

    Returns:
        List of flag_id strings for rules that matched.
    """
    if not drift_rules:
        return []

    matched: list[str] = []
    text_lower = text.lower()

    for rule in drift_rules:
        if rule.type == "keyword_ratio":
            tokens = text_lower.split()
            if not tokens:
                continue
            terms_lower = {t.lower() for t in rule.include}
            count = sum(1 for tok in tokens if tok in terms_lower)
            ratio = count / len(tokens)
            if rule.threshold is not None and ratio >= rule.threshold:
                matched.append(rule.flag_id)

        elif rule.type == "keyword_any":
            terms_lower = [t.lower() for t in rule.include]
            if any(term in text_lower for term in terms_lower):
                matched.append(rule.flag_id)

        elif rule.type == "regex":
            if rule.pattern and re.search(rule.pattern, text):
                matched.append(rule.flag_id)

    return matched
