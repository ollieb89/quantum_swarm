#!/usr/bin/env python3
"""
Quantum Swarm Order Router
Maps TradeAction JSON to Binance/OKX via CCXT, enforcing hard safety limits.
"""
import os
from datetime import datetime, timezone
_exchange = None


def _get_exchange():
    """Lazy init exchange -- no connection at import time."""
    global _exchange
    if _exchange is None:
        import ccxt as _ccxt
        exchange_id = os.getenv("EXCHANGE_ID", "binance")
        api_key = os.getenv("API_KEY")
        api_secret = os.getenv("API_SECRET")
        exchange_class = getattr(_ccxt, exchange_id)
        _exchange = exchange_class({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
        })
    return _exchange


def route_order(pipeline_payload: dict, agent_action: dict):
    """
    Routes the trade action to the exchange after hard-validating 
    against the original pipeline payload.
    """
    exchange = _get_exchange()
    symbol = agent_action.get("target_asset")
    action = agent_action.get("action")
    print(f"[{datetime.now(timezone.utc).isoformat()}] Processing {action} for {symbol}")

    # ==========================================
    # 1. HARD VALIDATION: Security Veto
    # ==========================================
    security = pipeline_payload.get("security_clearance", {})
    recommendation = pipeline_payload.get("swarm_recommendation", {})

    if not security.get("is_safe", False) or recommendation.get("action") == "DO_NOT_TRADE":
        print("🚨 SECURITY VETO: Asset is not safe or macro is invalid. Halting execution.")
        return {"status": "halted", "reason": "security_veto"}

    # ==========================================
    # 2. HARD VALIDATION: Allocation Ceiling
    # ==========================================
    max_alloc = recommendation.get("max_portfolio_allocation_pct", 0.0)
    requested_alloc = agent_action.get("position_size_pct", 0.0)
    
    if requested_alloc > max_alloc:
        print(f"⚠️ ALLOCATION BREACH: Agent requested {requested_alloc}%, but ceiling is {max_alloc}%. Throttling down.")
        requested_alloc = max_alloc

    if requested_alloc <= 0 and action not in ["SELL_MARKET", "SELL_LIMIT", "CANCEL_ORDERS"]:
        print("ℹ️ Allocation is 0%. No buy orders to route.")
        return {"status": "skipped", "reason": "zero_allocation"}

    # ==========================================
    # 3. POSITION SIZING
    # ==========================================
    try:
        # Fetch balance to calculate actual order size
        balance = exchange.fetch_balance()
        quote_currency = symbol.split('/')[1]  # e.g., 'USDT' from 'BTC/USDT'
        base_currency = symbol.split('/')[0]   # e.g., 'BTC'
        
        available_capital = balance['free'].get(quote_currency, 0.0)
        trade_usdt_value = available_capital * (requested_alloc / 100)
        
        # Fetch current ticker for sizing math
        ticker = exchange.fetch_ticker(symbol)
        current_price = ticker['last']
        
        # Calculate amount in base currency (e.g., how much BTC to buy)
        amount = trade_usdt_value / current_price

    except Exception as e:
        print(f"❌ Failed to calculate position size: {str(e)}")
        return {"status": "error", "reason": "sizing_calculation_failed"}

    # ==========================================
    # 4. EXECUTION ROUTING
    # ==========================================
    target_price = agent_action.get("execution_price_target")
    order_result = None

    try:
        if action == "BUY_MARKET":
            print(f"📈 Routing MARKET BUY for {amount:.6f} {symbol} (~${trade_usdt_value:.2f})")
            order_result = exchange.create_market_buy_order(symbol, amount)
            
        elif action == "BUY_LIMIT":
            print(f"🎯 Routing LIMIT BUY for {amount:.6f} {symbol} at ${target_price}")
            order_result = exchange.create_limit_buy_order(symbol, amount, target_price)
            
        elif action == "SELL_MARKET":
            # If selling, check how much we actually hold
            held_amount = balance['free'].get(base_currency, 0.0)
            sell_amount = held_amount * (requested_alloc / 100) if requested_alloc else held_amount
            print(f"📉 Routing MARKET SELL for {sell_amount:.6f} {symbol}")
            order_result = exchange.create_market_sell_order(symbol, sell_amount)
            
        elif action == "SELL_LIMIT":
            held_amount = balance['free'].get(base_currency, 0.0)
            sell_amount = held_amount * (requested_alloc / 100) if requested_alloc else held_amount
            print(f"🎯 Routing LIMIT SELL for {sell_amount:.6f} {symbol} at ${target_price}")
            order_result = exchange.create_limit_sell_order(symbol, sell_amount, target_price)
            
        elif action == "CANCEL_ORDERS":
            print(f"🧹 Canceling all open orders for {symbol}")
            order_result = exchange.cancel_all_orders(symbol)
            
        elif action == "HOLD":
            print("⏸️ Action is HOLD. No orders placed.")
            return {"status": "success", "action": "HOLD"}
            
        else:
            print(f"❌ Unknown action received from agent: {action}")
            return {"status": "error", "reason": "invalid_action_format"}

        print(f"✅ Execution successful. Order ID: {order_result.get('id')}")
        return {"status": "success", "data": order_result}

    except Exception as e:
        # Check if this is an InsufficientFunds error
        import ccxt as _ccxt
        if isinstance(e, _ccxt.InsufficientFunds):
            print(f"Insufficient funds: {str(e)}")
            return {"status": "error", "reason": "insufficient_funds"}
        print(f"Exchange routing failed: {str(e)}")
        return {"status": "error", "reason": str(e)}

if __name__ == "__main__":
    print("Quantum Swarm Order Router Initialized.")
    # Example integration point for your swarm controller:
    # route_order(pipeline_json, execution_agent_json)
