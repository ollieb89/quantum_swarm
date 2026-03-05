"""
conftest.py — project-root pytest configuration.

Adds the repository root to sys.path so that 'src.*' imports resolve
correctly when pytest is invoked from any working directory.
"""

import sys
import pathlib

# Insert repo root at the front of sys.path
sys.path.insert(0, str(pathlib.Path(__file__).parent))
