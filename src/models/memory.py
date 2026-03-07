"""
src.models.memory — Data models for the structured memory registry.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Dict, List, Optional, Literal, Any
import uuid

from pydantic import BaseModel, Field

class MemoryRule(BaseModel):
    """
    A single governed institutional memory rule.
    """
    id: str = Field(default_factory=lambda: f"mem_{str(uuid.uuid4())[:8]}")
    title: str
    type: Literal["risk_adjustment", "strategy_preference", "market_regime", "general"]
    scope: str = "trade_entry" # e.g. "trade_entry", "portfolio", "execution"
    condition: Dict[str, Any] = Field(default_factory=dict)
    action: Dict[str, Any] = Field(default_factory=dict)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    
    status: Literal["proposed", "active", "deprecated", "rejected"] = "proposed"
    version: int = 1
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reviewed_at: Optional[datetime] = None

class MemoryRegistrySchema(BaseModel):
    """
    Schema for the memory_registry.json file.
    """
    rules: List[MemoryRule] = Field(default_factory=list)
