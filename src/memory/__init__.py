"""
Quantum Swarm memory subsystem.

Public API: import from here, not from submodules directly.
"""

from src.memory.service import (
    DeduplicationResult,
    MemoryHit,
    MemoryService,
    MemorySource,
    StoredDocument,
)

__all__ = [
    "DeduplicationResult",
    "MemoryHit",
    "MemoryService",
    "MemorySource",
    "StoredDocument",
]
