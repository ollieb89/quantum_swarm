"""
conftest.py — project-root pytest configuration.

Adds the repository root to sys.path so that 'src.*' imports resolve
correctly when pytest is invoked from any working directory.
"""

import sys
import pathlib
from unittest.mock import MagicMock

# Insert repo root at the front of sys.path
sys.path.insert(0, str(pathlib.Path(__file__).parent))

# Mock ccxt to prevent collection errors due to missing submodules in some environments
# (e.g., ccxt.static_dependencies.lighter_client).
# This is required for test collection when graph nodes import ccxt at module level.
mock_ccxt = MagicMock()
sys.modules["ccxt"] = mock_ccxt
sys.modules["ccxt.async_support"] = mock_ccxt
sys.modules["ccxt.base"] = mock_ccxt
sys.modules["ccxt.base.exchange"] = mock_ccxt
