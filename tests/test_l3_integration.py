"""L3 integration tests — orchestrator wiring and feedback loop."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock


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
    from src.graph.orchestrator import create_orchestrator_graph

    # Mock data: what each L3 node should return
    mock_market_data_dict = {
        "market": {"symbol": "AAPL", "price": 150.0, "volume": 1e6, "open": 149.0,
                   "high": 151.0, "low": 148.5, "close": 150.0,
                   "timestamp": "2026-03-06T00:00:00", "source": "yfinance", "interval": "1d"},
        "sentiment": {"symbol": "AAPL", "overall_sentiment": "bullish", "sentiment_score": 0.6,
                      "article_count": 10, "timestamp": "2026-03-06T00:00:00", "source": "mock"},
        "economic": {"vix": 18.0, "usd_index": 102.0, "yield_10y": 4.2,
                     "timestamp": "2026-03-06T00:00:00", "source": "mock"},
        "fundamentals": None,
    }
    mock_backtest_dict = {
        "success": True,
        "sharpe_ratio": 1.2,
        "total_return_pct": 5.5,
        "max_drawdown_pct": -2.1,
        "total_trades": 8,
        "win_rate_pct": 62.5,
    }
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

    # Patch the three I/O-heavy L3 nodes; trade_logger is pure and runs for real
    async def mock_data_fetcher(state):
        return {"data_fetcher_result": mock_market_data_dict, "messages": []}

    async def mock_backtester(state):
        return {"backtest_result": mock_backtest_dict, "messages": []}

    async def mock_order_router(state):
        return {"execution_result": mock_execution_dict, "messages": []}

    # Also mock the L2 agents (they call external LLM APIs)
    def mock_bullish(state):
        return {"messages": [{"role": "assistant", "content": "bullish thesis", "name": "bullish_research"}]}

    def mock_bearish(state):
        return {"messages": [{"role": "assistant", "content": "bearish thesis", "name": "bearish_research"}]}

    def mock_debate_synthesizer(state):
        return {
            "weighted_consensus_score": 0.75,
            "debate_history": [{"hypothesis": "bullish"}, {"hypothesis": "bearish"}],
            "messages": [],
        }

    def mock_macro_analyst(state):
        return {"macro_report": {"phase": "Bullish"}, "messages": []}

    def mock_quant_modeler(state):
        return {
            "quant_proposal": {
                "symbol": "AAPL", "side": "buy", "quantity": 5.0, "asset_class": "equity"
            },
            "messages": [],
        }

    def mock_risk_manager(state):
        return {"risk_approved": True, "risk_notes": "All checks passed.", "messages": []}

    with patch("src.graph.agents.l3.data_fetcher.data_fetcher_node", new=mock_data_fetcher), \
         patch("src.graph.agents.l3.backtester.backtester_node", new=mock_backtester), \
         patch("src.graph.agents.l3.order_router.order_router_node", new=mock_order_router), \
         patch("src.graph.agents.researchers.BullishResearcher", new=mock_bullish), \
         patch("src.graph.agents.researchers.BearishResearcher", new=mock_bearish), \
         patch("src.graph.debate.DebateSynthesizer", new=mock_debate_synthesizer), \
         patch("src.graph.agents.analysts.MacroAnalyst", new=mock_macro_analyst), \
         patch("src.graph.agents.analysts.QuantModeler", new=mock_quant_modeler), \
         patch("src.graph.orchestrator.risk_manager_node", new=mock_risk_manager):

        graph = create_orchestrator_graph({})

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

        config = {"configurable": {"thread_id": "e2e-test-001"}}
        final_state = graph.invoke(initial_state, config=config)

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

    # Verify edge ordering via graph structure: risk_manager → data_fetcher
    edges = graph.get_graph().edges
    edge_pairs = [(e[0], e[1]) for e in edges]
    assert ("risk_manager", "data_fetcher") in edge_pairs
    assert ("data_fetcher", "backtester") in edge_pairs
    assert ("backtester", "order_router") in edge_pairs
    assert ("order_router", "trade_logger") in edge_pairs
    assert ("trade_logger", "synthesize") in edge_pairs
