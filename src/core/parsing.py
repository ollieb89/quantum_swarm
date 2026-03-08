import json
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

def parse_quant_proposal(state: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to parse quant_proposal from state, handling raw dict or wrapped JSON text."""
    raw = state.get("quant_proposal") or {}
    
    if isinstance(raw, dict) and "text" in raw:
        content = raw["text"]
        try:
            # Strip markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            parsed = json.loads(content)
            return parsed
        except Exception as e:
            logger.warning("Failed to parse quant_proposal text: %s", e)
            return {}
    
    return raw
