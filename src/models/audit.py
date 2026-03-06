from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class AuditLogEntry(BaseModel):
    """
    Schema for a single entry in the immutable audit log.
    Used for decision provenance and institutional compliance.
    """
    id: Optional[int] = None
    task_id: str = Field(..., description="Unique ID for the swarm task/thread")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    node_id: str = Field(..., description="ID of the LangGraph node that executed")
    
    # Input/Output data (stored as JSON)
    input_data: Dict[str, Any] = Field(..., description="State snippet received by the node")
    output_data: Dict[str, Any] = Field(..., description="State changes produced by the node")
    
    # Provenance (Hash Chaining)
    # hash = SHA256(timestamp + node_id + input_data + output_data + prev_hash)
    entry_hash: str = Field(..., description="SHA-256 hash of this entry plus previous hash")
    prev_hash: Optional[str] = Field(None, description="Hash of the previous entry in the chain")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
