"""
src.tools.data_sources.kaggle_loader — Kaggle dataset acquisition.

Provides:
    download_market_dataset(dataset_handle) -> Path
"""

import logging
import os
from pathlib import Path
import kagglehub

logger = logging.getLogger(__name__)

# Default to project root /data/kaggle_cache
DEFAULT_CACHE_DIR = Path("data/kaggle_cache").absolute()

def download_market_dataset(dataset_handle: str = "jainilsoni00/9000-tickers-of-stock-market-data-full-history") -> Path:
    """Download and cache a market dataset from Kaggle.
    
    Args:
        dataset_handle: Kaggle dataset handle (owner/dataset-name).
        
    Returns:
        Path to the cached dataset directory.
    """
    os.makedirs(DEFAULT_CACHE_DIR, exist_ok=True)
    
    # kagglehub has its own cache logic, but we want to know where it lands
    logger.info("Downloading Kaggle dataset: %s", dataset_handle)
    
    try:
        path = kagglehub.dataset_download(dataset_handle)
        logger.info("Dataset %s downloaded/cached at: %s", dataset_handle, path)
        return Path(path)
    except Exception as e:
        logger.error("Failed to download Kaggle dataset %s: %s", dataset_handle, e)
        raise

if __name__ == "__main__":
    # Quick test
    logging.basicConfig(level=logging.INFO)
    path = download_market_dataset()
    print(f"Dataset cached at: {path}")
