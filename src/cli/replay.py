"""
src.cli.replay — Replay subcommand handlers with rich rendering.

Provides list, show, and compare commands for inspecting persisted
CycleSnapshot data. Uses rich for terminal formatting and supports
--json for machine-parseable output.

Exported functions:
    register_replay_parser — Wire replay subcommands into argparse
    handle_replay          — Top-level dispatch for replay subcommand
    handle_list            — List cycles as table or JSON
    handle_show            — Show a single cycle with rich panels
    handle_compare         — Compare two cycles with delta arrows
"""

from __future__ import annotations

import asyncio
import json
import sys
from argparse import Namespace, _SubParsersAction
from typing import IO, Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from src.core.cycle_snapshot import CycleSnapshot
from src.core.cycle_store import list_cycles, load_cycle

# ---------------------------------------------------------------------------
# Colour / status helpers
# ---------------------------------------------------------------------------

_STATUS_COLOURS = {
    "completed": "green",
    "rejected": "yellow",
    "failed": "red",
}


def _status_style(status: str) -> str:
    return _STATUS_COLOURS.get(status, "white")


# ---------------------------------------------------------------------------
# Parser registration
# ---------------------------------------------------------------------------


def register_replay_parser(sub: _SubParsersAction) -> None:
    """Add the 'replay' subcommand group to *sub*."""
    replay_parser = sub.add_parser("replay", help="Inspect persisted cycle data")
    replay_sub = replay_parser.add_subparsers(dest="replay_command")

    # -- list --
    list_parser = replay_sub.add_parser("list", help="List cycles")
    list_parser.add_argument("--symbol", default=None, help="Filter by symbol")
    list_parser.add_argument("--status", default=None, help="Filter by status")
    list_parser.add_argument("--limit", type=int, default=None, help="Max results")
    list_parser.add_argument(
        "--json", action="store_true", default=False, help="JSON output"
    )

    # -- show --
    show_parser = replay_sub.add_parser("show", help="Show a single cycle")
    show_parser.add_argument("cycle_id", type=int, help="Cycle ID to display")
    show_parser.add_argument(
        "--json", action="store_true", default=False, help="JSON output"
    )

    # -- compare --
    cmp_parser = replay_sub.add_parser("compare", help="Compare two cycles")
    cmp_parser.add_argument("cycle_id_1", type=int, help="First cycle ID")
    cmp_parser.add_argument("cycle_id_2", type=int, help="Second cycle ID")
    cmp_parser.add_argument(
        "--json", action="store_true", default=False, help="JSON output"
    )


# ---------------------------------------------------------------------------
# Top-level dispatch
# ---------------------------------------------------------------------------


def handle_replay(args: Namespace) -> int:
    """Dispatch to the correct replay subcommand handler. Returns exit code."""
    cmd = getattr(args, "replay_command", None)
    if cmd == "list":
        return handle_list(args)
    if cmd == "show":
        return handle_show(args)
    if cmd == "compare":
        return handle_compare(args)

    # No subcommand — print help
    Console(stderr=True).print("[red]Usage: replay {list|show|compare}[/red]")
    return 1


# ---------------------------------------------------------------------------
# handle_list
# ---------------------------------------------------------------------------


def handle_list(
    args: Namespace,
    *,
    base_dir: str = "data/cycles",
    console: Console | None = None,
    stdout: IO[str] | None = None,
) -> int:
    """List cycles as a rich table or JSON array."""
    limit = args.limit if args.limit is not None else 20
    cycles = asyncio.run(
        list_cycles(
            pool=None,
            base_dir=base_dir,
            symbol=args.symbol,
            status=args.status,
            limit=limit,
        )
    )

    if getattr(args, "json", False):
        out = stdout or sys.stdout
        out.write(json.dumps(cycles, indent=2, default=str))
        return 0

    con = console or Console()
    table = Table(title="Cycles", show_lines=False)
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Symbol", style="bold")
    table.add_column("Status")
    table.add_column("Timestamp")
    table.add_column("Score", justify="right")

    for c in cycles:
        status = c.get("status", "unknown")
        table.add_row(
            str(c.get("cycle_id", "")),
            str(c.get("symbol", "")),
            Text(status, style=_status_style(status)),
            str(c.get("timestamp", "")),
            f"{c.get('consensus_score', 'N/A')}",
        )

    con.print(table)
    return 0


# ---------------------------------------------------------------------------
# handle_show
# ---------------------------------------------------------------------------


def _render_memo_panel(title: str, data: Optional[dict]) -> Panel:
    """Render an agent memo dict as a rich Panel."""
    if data is None:
        return Panel("No data", title=title, border_style="dim")

    # Try to extract 'analysis' key, else dump first value
    text = data.get("analysis")
    if text is None:
        first_key = next(iter(data), None)
        text = str(data[first_key]) if first_key else json.dumps(data, indent=2)

    return Panel(str(text), title=title, border_style="blue")


def _render_merit_bars(
    merit_scores: dict[str, dict],
    soul_sync_context: Optional[dict],
    console: Console,
) -> None:
    """Render merit weight bar charts with optional drift annotations."""
    if not merit_scores:
        console.print("  No merit scores available", style="dim")
        return

    max_bar_width = 30
    for agent, scores in merit_scores.items():
        composite = scores.get("composite", 0.0)
        bar_width = int(composite * max_bar_width)
        bar = "\u2588" * bar_width
        line = Text()
        line.append(f"  {agent:<12}", style="bold")
        line.append(bar, style="green")
        line.append(f" {composite:.2f}", style="white")

        # Drift annotation
        if soul_sync_context and agent in soul_sync_context:
            line.append("  DRIFT", style="yellow bold")

        console.print(line)


def _render_debate(
    history: Optional[list[dict]],
    resolution: Optional[dict],
    console: Console,
) -> None:
    """Render debate history and resolution."""
    if not history:
        console.print("  No debate history", style="dim")
        return

    for entry in history:
        rnd = entry.get("round", "?")
        speaker = entry.get("speaker", "unknown")
        argument = entry.get("argument", "")
        console.print(f"  Round {rnd} [{speaker}]: {argument}")

    if resolution:
        summary = resolution.get("summary", json.dumps(resolution))
        console.print(f"\n  Resolution: {summary}", style="bold")


def _render_decision_card(card: Optional[dict], console: Console) -> None:
    """Render decision card as key-value pairs."""
    if not card:
        console.print("  No decision card", style="dim")
        return

    for key, value in card.items():
        console.print(f"  {key}: {value}")


def handle_show(
    args: Namespace,
    *,
    base_dir: str = "data/cycles",
    console: Console | None = None,
    stdout: IO[str] | None = None,
) -> int:
    """Show a single cycle with rich panels or JSON."""
    try:
        snapshot = load_cycle(args.cycle_id, base_dir=base_dir)
    except FileNotFoundError as exc:
        err = console or Console(stderr=True)
        err.print(f"[red]Error:[/red] {exc}")
        return 1

    if getattr(args, "json", False):
        out = stdout or sys.stdout
        out.write(
            json.dumps(snapshot.model_dump(mode="json"), indent=2, default=str)
        )
        return 0

    con = console or Console()

    # -- Header --
    header = (
        f"Cycle {snapshot.cycle_id}  |  {snapshot.symbol}  |  "
        f"{snapshot.status}  |  {snapshot.timestamp}"
    )
    con.print(
        Panel(header, title="Cycle Overview", border_style=_status_style(snapshot.status))
    )

    # -- Agent Memos --
    con.print()
    con.print("[bold]Agent Memos[/bold]")
    con.print(_render_memo_panel("Macro Report", snapshot.macro_report))
    con.print(_render_memo_panel("Quant Proposal", snapshot.quant_proposal))
    con.print(_render_memo_panel("Bullish Thesis", snapshot.bullish_thesis))
    con.print(_render_memo_panel("Bearish Thesis", snapshot.bearish_thesis))

    # -- Debate --
    con.print()
    con.print("[bold]Debate[/bold]")
    _render_debate(snapshot.debate_history, snapshot.debate_resolution, con)

    # -- Consensus & Merit --
    con.print()
    score_str = (
        f"{snapshot.weighted_consensus_score:.2f}"
        if snapshot.weighted_consensus_score is not None
        else "N/A"
    )
    con.print(f"[bold]Consensus Score:[/bold] {score_str}")
    con.print("[bold]Merit Weights:[/bold]")
    _render_merit_bars(
        snapshot.merit_scores or {},
        snapshot.soul_sync_context,
        con,
    )

    # -- Decision Card --
    con.print()
    con.print("[bold]Decision Card[/bold]")
    _render_decision_card(snapshot.decision_card, con)

    # -- Error context (failed cycles) --
    if snapshot.status == "failed" and snapshot.error_context:
        con.print()
        con.print(
            Panel(
                json.dumps(snapshot.error_context, indent=2),
                title="Error Context",
                border_style="red",
            )
        )

    return 0


# ---------------------------------------------------------------------------
# handle_compare
# ---------------------------------------------------------------------------


def _compute_deltas(
    snap_a: CycleSnapshot, snap_b: CycleSnapshot
) -> dict[str, Any]:
    """Compute structured delta dict between two snapshots."""
    consensus_from = snap_a.weighted_consensus_score or 0.0
    consensus_to = snap_b.weighted_consensus_score or 0.0

    result: dict[str, Any] = {
        "from_cycle": snap_a.cycle_id,
        "to_cycle": snap_b.cycle_id,
        "symbol": snap_a.symbol,
        "consensus": {
            "from": consensus_from,
            "to": consensus_to,
            "delta": round(consensus_to - consensus_from, 4),
        },
        "merit_shifts": {},
    }

    all_agents = set()
    if snap_a.merit_scores:
        all_agents.update(snap_a.merit_scores.keys())
    if snap_b.merit_scores:
        all_agents.update(snap_b.merit_scores.keys())

    for agent in sorted(all_agents):
        from_val = (
            snap_a.merit_scores.get(agent, {}).get("composite", 0.0)
            if snap_a.merit_scores
            else 0.0
        )
        to_val = (
            snap_b.merit_scores.get(agent, {}).get("composite", 0.0)
            if snap_b.merit_scores
            else 0.0
        )
        result["merit_shifts"][agent] = {
            "from": from_val,
            "to": to_val,
            "delta": round(to_val - from_val, 4),
        }

    return result


def _delta_text(delta: float) -> Text:
    """Format a delta value with directional arrow."""
    if delta > 0:
        return Text(f"\u25b2 +{delta:.2f}", style="green")
    if delta < 0:
        return Text(f"\u25bc {delta:.2f}", style="red")
    return Text(f"  {delta:.2f}", style="dim")


def handle_compare(
    args: Namespace,
    *,
    base_dir: str = "data/cycles",
    console: Console | None = None,
    err_console: Console | None = None,
    stdout: IO[str] | None = None,
) -> int:
    """Compare two cycles and show deltas."""
    err = err_console or Console(stderr=True)

    try:
        snap_a = load_cycle(args.cycle_id_1, base_dir=base_dir)
    except FileNotFoundError as exc:
        err.print(f"[red]Error:[/red] {exc}")
        return 1

    try:
        snap_b = load_cycle(args.cycle_id_2, base_dir=base_dir)
    except FileNotFoundError as exc:
        err.print(f"[red]Error:[/red] {exc}")
        return 1

    # Same-symbol enforcement
    if snap_a.symbol != snap_b.symbol:
        err.print(
            f"[red]Error:[/red] Cannot compare cycles with different symbols "
            f"({snap_a.symbol} vs {snap_b.symbol})"
        )
        return 1

    deltas = _compute_deltas(snap_a, snap_b)

    if getattr(args, "json", False):
        out = stdout or sys.stdout
        out.write(json.dumps(deltas, indent=2, default=str))
        return 0

    con = console or Console()

    # -- Header --
    con.print(
        Panel(
            f"Comparing Cycle {snap_a.cycle_id} vs Cycle {snap_b.cycle_id}  "
            f"({snap_a.symbol})",
            title="Cycle Comparison",
            border_style="cyan",
        )
    )

    # -- Consensus delta --
    cd = deltas["consensus"]
    con.print()
    line = Text("Consensus Score: ")
    line.append(f"{cd['from']:.2f}", style="dim")
    line.append(" -> ")
    line.append(f"{cd['to']:.2f}", style="bold")
    line.append("  ")
    line.append_text(_delta_text(cd["delta"]))
    con.print(line)

    # -- Merit shifts table --
    con.print()
    table = Table(title="Merit Weight Shifts")
    table.add_column("Agent", style="bold")
    table.add_column("From", justify="right")
    table.add_column("To", justify="right")
    table.add_column("Delta", justify="right")

    for agent, shift in deltas["merit_shifts"].items():
        table.add_row(
            agent,
            f"{shift['from']:.2f}",
            f"{shift['to']:.2f}",
            _delta_text(shift["delta"]),
        )

    con.print(table)

    # -- Agent reasoning summary --
    con.print()
    con.print("[bold]Agent Reasoning Summary[/bold]")
    memo_fields = [
        ("macro_report", "Macro"),
        ("quant_proposal", "Quant"),
        ("bullish_thesis", "Bullish"),
        ("bearish_thesis", "Bearish"),
    ]
    for field, label in memo_fields:
        a_data = getattr(snap_a, field)
        b_data = getattr(snap_b, field)
        a_summary = _extract_memo_summary(a_data)
        b_summary = _extract_memo_summary(b_data)
        con.print(f"  {label}:")
        con.print(f"    Cycle {snap_a.cycle_id}: {a_summary}", style="dim")
        con.print(f"    Cycle {snap_b.cycle_id}: {b_summary}")

    return 0


def _extract_memo_summary(data: Optional[dict]) -> str:
    """Extract first line / 'analysis' key from a memo dict."""
    if data is None:
        return "No data"
    text = data.get("analysis")
    if text is None:
        first_key = next(iter(data), None)
        text = str(data[first_key]) if first_key else "No data"
    # Truncate to first line
    return str(text).split("\n")[0][:120]
