"""Phase 3 smoke tests — environment and import verification."""
import pytest


def test_nautilus_trader_imports():
    import nautilus_trader
    assert nautilus_trader.__version__


def test_data_models_import():
    from src.models.data_models import MarketData, SentimentData, FundamentalsData, TradeRecord, EconomicData
    assert MarketData
    assert TradeRecord
