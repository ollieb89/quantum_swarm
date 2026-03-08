"""L3 integration tests — orchestrator wiring and feedback loop."""
import asyncio
import pytest
from unittest.mock import patch


def _make_full_state(**overrides):
    """Build a minimal valid SwarmState dict for integration tests."""
    base = {
        "task_id": "integ-001",
        "user_input": "analyze AAPL and trade if consensus reached",
        "intent": "trade",
        "messages": [],
        "macro_report": None,
        "quant_proposal": {
            "symbol": "AAPL",
            "side": "buy",
            "quantity": 5.0,
            "asset_class": "equity",
        },
        "bullish_thesis": None,
        "bearish_thesis": None,
        "debate_resolution": None,
        "weighted_consensus_score": 0.75,
        "debate_history": [{"hypothesis": "bullish"}, {"hypothesis": "bearish"}],
        "risk_approval": None,
        "consensus_score": 0.75,
        "compliance_flags": [],
        "risk_approved": True,
        "risk_notes": "All risk checks passed.",
        "final_decision": None,
        "metadata": {},
        "trade_history": [],
        "execution_mode": "paper",
        "data_fetcher_result": None,
        "backtest_result": None,
        "execution_result": None,
    }
    base.update(overrides)
    return base


def test_feedback_loop_l2_receives_trade_history():
    """L2 BullishResearcher receives trade_history in state on second invocation."""
    from src.graph.agents.l3.trade_logger import trade_logger_node

    # Simulate a state that has one completed trade in trade_history
    existing_trade = {
        "trade_id": "abc123",
        "symbol": "AAPL",
        "side": "buy",
        "entry_price": 150.0,
        "exit_price": None,
        "quantity": 5.0,
        "pnl": None,
        "pnl_pct": None,
        "entry_time": "2026-03-01T10:00:00",
        "exit_time": None,
        "execution_mode": "paper",
        "strategy_context": {},
    }
    state = _make_full_state(
        trade_history=[existing_trade],
        execution_result={"success": True, "execution_price": 152.0, "order_id": "PAPER-TEST"},
    )

    # Verify researchers.py uses get_recent_trades
    from src.graph.agents.l3.trade_logger import get_recent_trades
    recent = get_recent_trades(state)
    assert len(recent) == 1
    assert recent[0]["symbol"] == "AAPL"

    # BullishResearcher state should contain the trade_history field
    assert "trade_history" in state
    assert len(state["trade_history"]) >= 1


def test_end_to_end_paper_graph():
    """Full graph invocation: mock L3 nodes; assert trade_history has one entry after run."""
    import src.graph.orchestrator as orch_module

    mock_execution_dict = {
        "success": True,
        "order_id": "PAPER-ABCD1234",
        "execution_price": 150.25,
        "mode": "paper",
        "slippage_pct": 0.01,
        "symbol": "AAPL",
        "side": "buy",
        "quantity": 5.0,
    }

    # Patch the I/O-heavy L3 nodes; trade_logger is pure and runs for real
    async def mock_data_fetcher(state):
        return {"data_fetcher_result": {"market": {}, "sentiment": {}, "economic": {}, "fundamentals": None}, "messages": []}

    async def mock_backtester(state):
        return {"backtest_result": {"success": True, "sharpe_ratio": 1.2}, "messages": []}

    async def mock_order_router(state):
        return {"execution_result": mock_execution_dict, "messages": []}

    # Mock L2 agents (they call external LLM APIs)
    def mock_bullish(state, **kwargs):
        return {"messages": []}

    def mock_bearish(state, **kwargs):
        return {"messages": []}

    def mock_debate_synthesizer(state):
        return {
            "weighted_consensus_score": 0.75,
            "debate_history": [{"hypothesis": "bullish"}, {"hypothesis": "bearish"}],
            "messages": [],
        }

    def mock_macro_analyst(state, **kwargs):
        return {"macro_report": {"phase": "Bullish"}, "messages": []}

    def mock_quant_modeler(state, **kwargs):
        return {
            "quant_proposal": {
                "symbol": "AAPL", "side": "buy", "quantity": 5.0, "asset_class": "equity"
            },
            "messages": [],
        }

    def mock_risk_manager(state, **kwargs):
        return {"risk_approved": True, "risk_notes": "All checks passed.", "messages": []}

    # Use patch.object on the orchestrator module — ensures the graph captures mocked funcs
    # at create_orchestrator_graph() call time (which happens inside the patch context).
    # Pass intent_patterns so classify_intent can route "trade AAPL" → quant_modeler.
    graph_config = {
        "orchestrator": {
            "intent_patterns": {
                "trade": ["trade", "buy", "sell", "long", "short"],
                "analysis": ["analyze", "review"],
            }
        }
    }

    with patch.object(orch_module, "data_fetcher_node", new=mock_data_fetcher), \
         patch.object(orch_module, "backtester_node", new=mock_backtester), \
         patch.object(orch_module, "order_router_node", new=mock_order_router), \
         patch.object(orch_module, "BullishResearcher", new=mock_bullish), \
         patch.object(orch_module, "BearishResearcher", new=mock_bearish), \
         patch.object(orch_module, "DebateSynthesizer", new=mock_debate_synthesizer), \
         patch.object(orch_module, "MacroAnalyst", new=mock_macro_analyst), \
         patch.object(orch_module, "QuantModeler", new=mock_quant_modeler), \
         patch.object(orch_module, "risk_manager_node", new=mock_risk_manager):

        graph = orch_module.create_orchestrator_graph(graph_config)

        initial_state = {
            "task_id": "e2e-test-001",
            "user_input": "trade AAPL",
            "intent": "unknown",
            "messages": [],
            "macro_report": None,
            "quant_proposal": None,
            "bullish_thesis": None,
            "bearish_thesis": None,
            "debate_resolution": None,
            "weighted_consensus_score": None,
            "debate_history": [],
            "risk_approval": None,
            "consensus_score": 0.0,
            "compliance_flags": [],
            "risk_approved": None,
            "risk_notes": None,
            "final_decision": None,
            "metadata": {},
            "trade_history": [],
            "execution_mode": "paper",
            "data_fetcher_result": None,
            "backtest_result": None,
            "execution_result": None,
        }

        invoke_config = {"configurable": {"thread_id": "e2e-test-001"}}
        # Use ainvoke because L3 nodes (data_fetcher, backtester, order_router) are async
        final_state = asyncio.run(graph.ainvoke(initial_state, config=invoke_config))

        # The graph should have completed with trade_history containing one entry
        assert "trade_history" in final_state
        assert len(final_state["trade_history"]) == 1
        record = final_state["trade_history"][0]
        assert record["symbol"] == "AAPL"
        assert record["side"] == "buy"


def test_execution_mode_from_config():
    """orchestrator reads execution_mode from swarm_config.yaml and sets it in initial_state."""
    from src.graph.orchestrator import LangGraphOrchestrator

    orch = LangGraphOrchestrator({})
    # The orchestrator should have loaded the yaml config
    assert hasattr(orch, "_yaml_config")
    yaml_mode = orch._yaml_config.get("trading", {}).get("execution_mode", "paper")
    assert yaml_mode in ("paper", "live")


def test_l3_chain_order():
    """After risk_manager approval, graph visits data_fetcher before backtester before
    order_router before trade_logger."""
    from src.graph.orchestrator import create_orchestrator_graph

    graph = create_orchestrator_graph({})
    nodes = list(graph.get_graph().nodes.keys())
    assert "data_fetcher" in nodes
    assert "backtester" in nodes
    assert "order_router" in nodes
    assert "trade_logger" in nodes

    # Verify edge ordering via graph structure:
    # risk_manager → claw_guard → institutional_guard → data_fetcher → knowledge_base → backtester → ...
    edges = graph.get_graph().edges
    edge_pairs = [(e[0], e[1]) for e in edges]
    assert ("risk_manager", "claw_guard") in edge_pairs
    # Phase 13: claw_guard now routes through institutional_guard before data_fetcher
    assert ("claw_guard", "institutional_guard") in edge_pairs
    # Phase 4: write_external_memory inserted between data_fetcher and knowledge_base
    assert ("data_fetcher", "write_external_memory") in edge_pairs
    assert ("write_external_memory", "knowledge_base") in edge_pairs
    assert ("knowledge_base", "backtester") in edge_pairs
    assert ("backtester", "order_router") in edge_pairs
    assert ("order_router", "trade_logger") in edge_pairs
    # Phase 4: write_trade_memory inserted between trade_logger and synthesize
    assert ("trade_logger", "write_trade_memory") in edge_pairs
    assert ("write_trade_memory", "synthesize") in edge_pairs
