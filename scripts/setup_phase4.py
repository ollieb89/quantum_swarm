import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.core.persistence import setup_persistence

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    try:
        await setup_persistence()
        logger.info("Phase 4 persistence setup successful.")
    except Exception as e:
        logger.error(f"Phase 4 persistence setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
