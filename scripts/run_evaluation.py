#!/usr/bin/env python3
"""Beta Evaluation Script — Structured Confidence Check.

Runs N cycles per asset, scores consensus friction / risk gating / persona
fidelity / merit drift, and prints an actionable report with outlier
deep-dive recommendations.

Usage:
    python scripts/run_evaluation.py run
    python scripts/run_evaluation.py score  data/evaluations/2026-03-09-eval.jsonl
    python scripts/run_evaluation.py report data/evaluations/2026-03-09-eval.jsonl
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console
from rich.table import Table

# Ensure project root is on sys.path so `from src.*` imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ASSETS = ["BTC", "ETH", "SOL"]
CYCLES_PER_ASSET = 10
EXECUTION_MODE = "paper"
EVAL_DIR = Path("data/evaluations")
RETRY_ATTEMPTS = 3
RETRY_BASE_DELAY = 2.0
INTER_CYCLE_SLEEP = 1.0

# Persona keyword clusters for fidelity scoring
PERSONA_KEYWORDS: dict[str, list[str]] = {
    "AXIOM": [
        "regime", "macro", "cycle", "structural", "fiscal", "monetary",
        "geopolitical", "rates", "inflation", "gdp",
    ],
    "MOMENTUM": [
        "flow", "momentum", "breakout", "accumulation", "trend", "volume",
        "price action", "support", "resistance", "rally",
    ],
    "CASSANDRA": [
        "tail", "hedge", "downside", "contagion", "liquidation", "systemic",
        "crash", "risk-off", "drawdown", "capitulation",
    ],
    "SIGMA": [
        "volatility", "correlation", "skew", "quantile", "variance",
        "distribution", "standard deviation", "z-score", "regression", "stochastic",
    ],
}

# Sentiment-polarity: CASSANDRA is bearish, MOMENTUM is bullish
BEARISH_HANDLES = {"CASSANDRA"}
BULLISH_HANDLES = {"MOMENTUM"}

# Thresholds
ECHO_CHAMBER_THRESHOLD = 0.10
BULLY_DELTA_THRESHOLD = 0.05
PERSONA_DRIFT_THRESHOLD = 0.50
POLARITY_BREACH_CONVICTION = 0.80
MERIT_DECAY_THRESHOLD = 0.20

console = Console()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _eval_path(label: str | None = None) -> Path:
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    name = label or datetime.now(timezone.utc).strftime("%Y-%m-%d-eval")
    return EVAL_DIR / f"{name}.jsonl"


def _append_jsonl(path: Path, obj: dict) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, default=str) + "\n")


def _read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _cosine_sim(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    keys = set(vec_a) | set(vec_b)
    dot = sum(vec_a.get(k, 0) * vec_b.get(k, 0) for k in keys)
    mag_a = math.sqrt(sum(v**2 for v in vec_a.values())) or 1e-9
    mag_b = math.sqrt(sum(v**2 for v in vec_b.values())) or 1e-9
    return dot / (mag_a * mag_b)


def _extract_text(agent_output: dict | None) -> str:
    if not agent_output:
        return ""
    parts: list[str] = []
    for key in ("summary", "rationale", "hypothesis", "signal",
                "recommended_action", "supporting_evidence", "refuting_evidence"):
        val = agent_output.get(key)
        if isinstance(val, str):
            parts.append(val)
        elif isinstance(val, list):
            parts.extend(str(v) for v in val)
    return " ".join(parts).lower()


def _keyword_freq(text: str, keywords: list[str]) -> dict[str, float]:
    words = text.split()
    total = len(words) or 1
    freq: dict[str, float] = {}
    for kw in keywords:
        freq[kw] = text.count(kw) / total
    return freq


def _extract_conviction(agent_output: dict | None) -> float | None:
    if not agent_output:
        return None
    return agent_output.get("confidence")


# ---------------------------------------------------------------------------
# Pre-flight check
# ---------------------------------------------------------------------------


def _pre_flight_check() -> dict:
    """Validate environment before starting a batch. Returns status dict."""
    console.print("\n[bold]Pre-flight Diagnostics[/bold]\n")
    errors: list[str] = []
    warnings: list[str] = []
    db_available = False

    # 1. GOOGLE_API_KEY
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        errors.append("GOOGLE_API_KEY not set. Export it or add to .env")
    else:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
            llm.invoke("ping")
            console.print("  [green]Gemini API OK[/green]")
        except Exception as exc:
            errors.append(f"Gemini API call failed: {exc}")

    # 2. PostgreSQL (optional — graceful fallback)
    try:
        from src.core.db import get_pool
        pool = get_pool()
        if pool:
            db_available = True
            console.print("  [green]PostgreSQL OK[/green] (merit scores will persist)")
    except Exception:
        warnings.append("PostgreSQL unavailable — filesystem-only mode (no merit persistence)")
        console.print("  [yellow]PostgreSQL unavailable[/yellow] — filesystem-only mode")

    # 3. Data directory
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    console.print(f"  [green]Output dir OK[/green] ({EVAL_DIR})")

    # Verdict
    if errors:
        console.print()
        for e in errors:
            console.print(f"  [red]FAIL: {e}[/red]")
        console.print("\n[red bold]Pre-flight failed. Fix the above and retry.[/red bold]\n")
        sys.exit(1)

    for w in warnings:
        console.print(f"  [yellow]WARN: {w}[/yellow]")

    console.print("\n  [green bold]All systems nominal.[/green bold]\n")
    return {"db_available": db_available}


# ---------------------------------------------------------------------------
# Phase 1: Run cycles
# ---------------------------------------------------------------------------


async def run_batch(output_path: Path) -> None:
    """Execute 30 cycles (10 per asset) and write raw results to JSONL."""
    # Lazy imports to avoid import-time side effects
    from src.core.cycle_runner import CycleRunner
    from src.core.persistence import setup_persistence
    from src.graph.orchestrator import create_orchestrator_graph

    pool = _try_get_pool()
    if pool:
        from src.core.db import ensure_pool_open
        await ensure_pool_open()
        await setup_persistence(pool)

    graph = create_orchestrator_graph({})
    runner = CycleRunner(graph, db_pool=pool, execution_mode=EXECUTION_MODE)

    console.print(f"\n[bold]Beta Evaluation[/bold] — {len(ASSETS)} assets x {CYCLES_PER_ASSET} cycles")
    console.print(f"Output: {output_path}\n")

    total = len(ASSETS) * CYCLES_PER_ASSET
    done = 0

    for asset in ASSETS:
        symbol = f"{asset}/USDT"
        console.print(f"[cyan]--- {asset} ({CYCLES_PER_ASSET} cycles) ---[/cyan]")

        for i in range(CYCLES_PER_ASSET):
            attempt = 0
            snapshot = None
            while attempt < RETRY_ATTEMPTS:
                try:
                    snapshot = await runner.run_cycle(f"Analyze {asset}", symbol)
                    break
                except Exception as exc:
                    attempt += 1
                    if attempt >= RETRY_ATTEMPTS:
                        console.print(f"  [red]Cycle {i+1} FAILED after {RETRY_ATTEMPTS} retries: {exc}[/red]")
                        snapshot = None
                        break
                    delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    console.print(f"  [yellow]Retry {attempt}/{RETRY_ATTEMPTS} in {delay:.0f}s: {exc}[/yellow]")
                    await asyncio.sleep(delay)

            record = _snapshot_to_record(snapshot, asset, i + 1)
            _append_jsonl(output_path, record)

            done += 1
            status = record.get("status", "unknown")
            tag = "[green]OK[/green]" if status == "completed" else f"[yellow]{status}[/yellow]"
            console.print(f"  Cycle {i+1:>2}/{CYCLES_PER_ASSET} {tag}  ({done}/{total})")

            if i < CYCLES_PER_ASSET - 1:
                await asyncio.sleep(INTER_CYCLE_SLEEP)

    console.print(f"\n[bold green]Batch complete.[/bold green] {done} cycles written to {output_path}")


def _snapshot_to_record(snapshot, asset: str, seq: int) -> dict:
    if snapshot is None:
        return {
            "asset": asset,
            "seq": seq,
            "status": "failed",
            "cycle_id": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    data = snapshot.model_dump(mode="json")
    data["asset"] = asset
    data["seq"] = seq
    return data


def _try_get_pool():
    try:
        from src.core.db import get_pool
        return get_pool()
    except Exception:
        console.print("[yellow]PostgreSQL unavailable — running without DB persistence[/yellow]")
        return None


# ---------------------------------------------------------------------------
# Phase 2: Scorers
# ---------------------------------------------------------------------------


def score_consensus_friction(record: dict) -> dict:
    """Compute consensus friction metrics for a single cycle."""
    convictions: list[float] = []
    for key in ("bullish_thesis", "bearish_thesis", "quant_proposal", "macro_report"):
        c = _extract_conviction(record.get(key))
        if c is not None:
            convictions.append(c)

    if len(convictions) < 2:
        return {"friction": None, "delta": None, "bully_flag": False, "echo_chamber": False}

    mean_c = sum(convictions) / len(convictions)
    variance = sum((c - mean_c) ** 2 for c in convictions) / len(convictions)
    friction = math.sqrt(variance)

    consensus = record.get("weighted_consensus_score")
    delta = abs(mean_c - consensus) if consensus is not None else None

    echo_chamber = friction < ECHO_CHAMBER_THRESHOLD
    bully_flag = (friction >= ECHO_CHAMBER_THRESHOLD
                  and delta is not None
                  and delta < BULLY_DELTA_THRESHOLD)

    return {
        "friction": round(friction, 4),
        "delta": round(delta, 4) if delta is not None else None,
        "bully_flag": bully_flag,
        "echo_chamber": echo_chamber,
        "convictions": convictions,
    }


def score_risk_gates(record: dict) -> dict:
    """Compute risk gating metrics for a single cycle."""
    risk_approved = record.get("risk_approved")
    risk_notes = record.get("risk_notes", "")
    consensus = record.get("weighted_consensus_score")

    blocked = risk_approved is False
    # Classify block reasons from notes
    reasons: list[str] = []
    if blocked and risk_notes:
        notes_lower = risk_notes.lower()
        for tag in ("exposure", "concentration", "drawdown", "conviction", "adversarial", "debate"):
            if tag in notes_lower:
                reasons.append(tag)
        if not reasons:
            reasons.append("unclassified")

    # Outlier flags
    false_positive = blocked and consensus is not None and consensus > 0.8
    min_conviction = None
    for key in ("bullish_thesis", "bearish_thesis", "quant_proposal"):
        c = _extract_conviction(record.get(key))
        if c is not None:
            min_conviction = min(min_conviction, c) if min_conviction is not None else c
    pass_through = (not blocked
                    and min_conviction is not None
                    and min_conviction < 0.3)

    return {
        "blocked": blocked,
        "block_reasons": reasons,
        "false_positive": false_positive,
        "pass_through": pass_through,
        "min_conviction": round(min_conviction, 4) if min_conviction is not None else None,
    }


def score_persona_fidelity(record: dict) -> dict:
    """Compute persona fidelity metrics for a single cycle."""
    agent_map = {
        "AXIOM": "macro_report",
        "MOMENTUM": "bullish_thesis",
        "CASSANDRA": "bearish_thesis",
        "SIGMA": "quant_proposal",
    }

    scores: dict[str, dict] = {}
    for handle, field in agent_map.items():
        text = _extract_text(record.get(field))
        if not text:
            scores[handle] = {"cosine_sim": None, "drift": False, "polarity_breach": False}
            continue

        expected = PERSONA_KEYWORDS[handle]
        actual_freq = _keyword_freq(text, expected)

        # Build expected vector (uniform weight for expected keywords)
        expected_freq = {kw: 1.0 for kw in expected}
        sim = _cosine_sim(actual_freq, expected_freq)

        drift = sim < PERSONA_DRIFT_THRESHOLD

        # Cross-contamination: check if top keyword belongs to another persona
        all_kw_counts: dict[str, int] = {}
        for kw_list in PERSONA_KEYWORDS.values():
            for kw in kw_list:
                all_kw_counts[kw] = text.count(kw)
        top_kw = max(all_kw_counts, key=all_kw_counts.get) if all_kw_counts else None
        cross_contamination = False
        if top_kw and all_kw_counts.get(top_kw, 0) > 0:
            for other_handle, other_kws in PERSONA_KEYWORDS.items():
                if other_handle != handle and top_kw in other_kws:
                    cross_contamination = True
                    break

        # Sentiment-polarity breach
        conviction = _extract_conviction(record.get(field))
        polarity_breach = False
        if conviction is not None:
            if handle in BEARISH_HANDLES and conviction > POLARITY_BREACH_CONVICTION:
                polarity_breach = True
            if handle in BULLISH_HANDLES and conviction < (1 - POLARITY_BREACH_CONVICTION):
                polarity_breach = True

        scores[handle] = {
            "cosine_sim": round(sim, 4),
            "drift": drift,
            "cross_contamination": cross_contamination,
            "top_keyword": top_kw,
            "polarity_breach": polarity_breach,
            "conviction": round(conviction, 4) if conviction is not None else None,
        }

    return scores


def track_merit_drift(records: list[dict]) -> dict:
    """Track merit score trends across a sequence of cycles for one asset."""
    agent_series: dict[str, list[float]] = defaultdict(list)

    for rec in records:
        merits = rec.get("merit_scores") or {}
        for handle in ("AXIOM", "MOMENTUM", "CASSANDRA", "SIGMA", "GUARDIAN"):
            entry = merits.get(handle, {})
            composite = entry.get("composite") if isinstance(entry, dict) else None
            agent_series[handle].append(composite)

    drift_results: dict[str, dict] = {}
    for handle, series in agent_series.items():
        valid = [v for v in series if v is not None]
        if len(valid) < 2:
            drift_results[handle] = {"start": None, "end": None, "delta": None, "decay_alert": False}
            continue

        start, end = valid[0], valid[-1]
        delta = end - start
        # Monotonic decay check
        monotonic_decay = all(valid[i] <= valid[i - 1] for i in range(1, len(valid)))
        decay_alert = monotonic_decay and abs(delta) > MERIT_DECAY_THRESHOLD

        drift_results[handle] = {
            "start": round(start, 4),
            "end": round(end, 4),
            "delta": round(delta, 4),
            "decay_alert": decay_alert,
            "series": [round(v, 4) if v is not None else None for v in series],
        }

    return drift_results


def score_all(records: list[dict]) -> list[dict]:
    """Score all cycle records and return enriched records."""
    scored: list[dict] = []
    for rec in records:
        rec["_scores"] = {
            "consensus": score_consensus_friction(rec),
            "risk": score_risk_gates(rec),
            "persona": score_persona_fidelity(rec),
        }
        scored.append(rec)

    # Merit drift per asset
    by_asset: dict[str, list[dict]] = defaultdict(list)
    for rec in scored:
        by_asset[rec.get("asset", "unknown")].append(rec)

    merit_drift: dict[str, dict] = {}
    for asset, recs in by_asset.items():
        recs_sorted = sorted(recs, key=lambda r: r.get("seq", 0))
        merit_drift[asset] = track_merit_drift(recs_sorted)

    # Attach drift to each record
    for rec in scored:
        rec["_merit_drift"] = merit_drift.get(rec.get("asset", ""), {})

    return scored


# ---------------------------------------------------------------------------
# Phase 3: Report
# ---------------------------------------------------------------------------


def print_report(records: list[dict]) -> None:
    """Print evaluation report with Rich tables."""
    if not records:
        console.print("[red]No records to report.[/red]")
        return

    # Ensure scored
    if "_scores" not in records[0]:
        records = score_all(records)

    by_asset: dict[str, list[dict]] = defaultdict(list)
    for rec in records:
        by_asset[rec.get("asset", "unknown")].append(rec)

    # --- Summary Table ---
    console.print("\n[bold underline]Evaluation Summary[/bold underline]\n")
    summary = Table(title="Per-Asset Averages")
    summary.add_column("Asset", style="cyan")
    summary.add_column("Cycles")
    summary.add_column("Completed")
    summary.add_column("Avg Friction")
    summary.add_column("Block Rate")
    summary.add_column("Avg Persona Sim")
    summary.add_column("Echo Chambers")
    summary.add_column("Bully Flags")

    for asset in ASSETS:
        recs = by_asset.get(asset, [])
        n = len(recs)
        completed = sum(1 for r in recs if r.get("status") == "completed")

        frictions = [r["_scores"]["consensus"]["friction"] for r in recs
                     if r.get("_scores", {}).get("consensus", {}).get("friction") is not None]
        avg_friction = sum(frictions) / len(frictions) if frictions else 0

        blocked = sum(1 for r in recs if r.get("_scores", {}).get("risk", {}).get("blocked"))
        block_rate = blocked / n if n else 0

        sims: list[float] = []
        for r in recs:
            persona = r.get("_scores", {}).get("persona", {})
            for handle_data in persona.values():
                if isinstance(handle_data, dict) and handle_data.get("cosine_sim") is not None:
                    sims.append(handle_data["cosine_sim"])
        avg_sim = sum(sims) / len(sims) if sims else 0

        echoes = sum(1 for r in recs
                     if r.get("_scores", {}).get("consensus", {}).get("echo_chamber"))
        bullies = sum(1 for r in recs
                      if r.get("_scores", {}).get("consensus", {}).get("bully_flag"))

        summary.add_row(
            asset, str(n), str(completed),
            f"{avg_friction:.3f}", f"{block_rate:.0%}",
            f"{avg_sim:.3f}", str(echoes), str(bullies),
        )

    console.print(summary)

    # --- Outlier Table ---
    console.print("\n[bold underline]Outliers[/bold underline]\n")
    outliers: list[dict] = []
    for rec in records:
        reasons: list[str] = []
        cs = rec.get("_scores", {}).get("consensus", {})
        rs = rec.get("_scores", {}).get("risk", {})
        ps = rec.get("_scores", {}).get("persona", {})

        if cs.get("echo_chamber"):
            reasons.append("echo-chamber")
        if cs.get("bully_flag"):
            reasons.append("bully-agent")
        if rs.get("false_positive"):
            reasons.append("false-positive-block")
        if rs.get("pass_through"):
            reasons.append("weak-signal-passed")
        for handle, data in ps.items():
            if isinstance(data, dict):
                if data.get("drift"):
                    reasons.append(f"persona-drift:{handle}")
                if data.get("polarity_breach"):
                    reasons.append(f"polarity-breach:{handle}")
                if data.get("cross_contamination"):
                    reasons.append(f"cross-contamination:{handle}")

        if reasons:
            outliers.append({
                "asset": rec.get("asset"),
                "seq": rec.get("seq"),
                "cycle_id": rec.get("cycle_id"),
                "status": rec.get("status"),
                "reasons": reasons,
            })

    if outliers:
        ot = Table(title="Flagged Cycles")
        ot.add_column("Asset", style="cyan")
        ot.add_column("Seq")
        ot.add_column("Cycle ID")
        ot.add_column("Status")
        ot.add_column("Flags", style="yellow")
        for o in outliers:
            ot.add_row(
                o["asset"], str(o["seq"]),
                str(o["cycle_id"] or "-"),
                o["status"] or "-",
                ", ".join(o["reasons"]),
            )
        console.print(ot)
    else:
        console.print("  [green]No outliers detected.[/green]")

    # --- Merit Drift ---
    console.print("\n[bold underline]Merit Drift[/bold underline]\n")
    for asset in ASSETS:
        recs = by_asset.get(asset, [])
        if not recs:
            continue
        drift = recs[0].get("_merit_drift", {})
        if not drift:
            continue

        dt = Table(title=f"{asset} Merit Drift")
        dt.add_column("Agent", style="cyan")
        dt.add_column("Start")
        dt.add_column("End")
        dt.add_column("Delta")
        dt.add_column("Alert", style="red")
        dt.add_column("Sparkline")

        for handle in ("AXIOM", "MOMENTUM", "CASSANDRA", "SIGMA", "GUARDIAN"):
            d = drift.get(handle, {})
            series = d.get("series", [])
            spark = _sparkline(series) if series else "-"
            dt.add_row(
                handle,
                str(d.get("start", "-")),
                str(d.get("end", "-")),
                str(d.get("delta", "-")),
                "DECAY" if d.get("decay_alert") else "",
                spark,
            )
        console.print(dt)

    # --- Deep-Dive Recommendations ---
    console.print("\n[bold underline]Recommended Deep-Dives[/bold underline]\n")
    if outliers:
        ranked = sorted(outliers, key=lambda o: len(o["reasons"]), reverse=True)[:3]
        for i, o in enumerate(ranked, 1):
            cid = o["cycle_id"]
            if cid:
                console.print(f"  {i}. [bold]{o['asset']}[/bold] cycle {o['seq']} "
                              f"({', '.join(o['reasons'])})")
                console.print(f"     [dim]python -m src.main replay show {cid}[/dim]")
            else:
                console.print(f"  {i}. [bold]{o['asset']}[/bold] cycle {o['seq']} "
                              f"({', '.join(o['reasons'])}) — no cycle_id (failed)")
    else:
        console.print("  No outliers — consider increasing cycle count for more signal.")

    console.print()


def _sparkline(series: list[float | None]) -> str:
    blocks = " _.-~*"
    vals = [v for v in series if v is not None]
    if not vals:
        return "-"
    lo, hi = min(vals), max(vals)
    spread = hi - lo or 1e-9
    return "".join(
        blocks[min(int((v - lo) / spread * (len(blocks) - 1)), len(blocks) - 1)]
        if v is not None else "?"
        for v in series
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Beta Evaluation — Structured Confidence Check",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Execute evaluation batch (30 cycles)")
    run_p.add_argument("--output", "-o", type=str, default=None,
                       help="Output JSONL path (default: auto-dated)")

    score_p = sub.add_parser("score", help="Re-score an existing batch")
    score_p.add_argument("file", type=str, help="Path to JSONL file")

    report_p = sub.add_parser("report", help="Print report from scored data")
    report_p.add_argument("file", type=str, help="Path to JSONL file")

    args = parser.parse_args()

    if args.command == "run":
        _pre_flight_check()
        path = Path(args.output) if args.output else _eval_path()
        asyncio.run(run_batch(path))
        # Auto-score and report after run
        records = _read_jsonl(path)
        scored = score_all(records)
        # Rewrite with scores
        scored_path = path.with_suffix(".scored.jsonl")
        for rec in scored:
            _append_jsonl(scored_path, rec)
        console.print(f"\nScored data: {scored_path}")
        print_report(scored)

    elif args.command == "score":
        path = Path(args.file)
        records = _read_jsonl(path)
        scored = score_all(records)
        scored_path = path.with_suffix(".scored.jsonl")
        for rec in scored:
            _append_jsonl(scored_path, rec)
        console.print(f"Scored {len(scored)} records → {scored_path}")
        print_report(scored)

    elif args.command == "report":
        path = Path(args.file)
        records = _read_jsonl(path)
        if records and "_scores" not in records[0]:
            records = score_all(records)
        print_report(records)


if __name__ == "__main__":
    main()
