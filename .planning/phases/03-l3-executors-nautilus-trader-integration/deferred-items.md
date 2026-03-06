# Deferred Items — Phase 03 L3 Executors

## Cross-test event loop contamination (test_order_router.py)

**Found during:** Plan 03-04 full suite run

**Issue:** `test_order_router.py` uses `asyncio.get_event_loop().run_until_complete()` (deprecated Python 3.10+ pattern). When run AFTER async test files that call `asyncio.run()` (test_data_fetcher.py, test_backtester.py, test_dexter_bridge.py, test_l3_integration.py), the event loop is closed and `get_event_loop()` raises `RuntimeError: There is no current event loop`.

**Impact:** 6 test_order_router.py tests fail when run in the full suite but pass in isolation.

**Fix needed:** Update test_order_router.py to use `asyncio.run(order_router_node(state))` instead of `asyncio.get_event_loop().run_until_complete(...)`. This is the same pattern already used in test_data_fetcher.py.

**Scope:** Pre-existing issue introduced in Plan 03-03. Out of scope for 03-04 per deviation Rule boundary.
