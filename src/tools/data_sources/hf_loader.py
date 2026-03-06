"""
src.tools.data_sources.hf_loader — Hugging Face dataset acquisition.

Provides:
    download_sentiment_dataset() -> Path
"""

import logging
import os
from pathlib import Path
from datasets import load_dataset

logger = logging.getLogger(__name__)

# Default to project root /data/hf_cache
DEFAULT_CACHE_DIR = Path("data/hf_cache").absolute()

def download_sentiment_dataset(dataset_name: str = "takala/financial_phrasebank", subset: str = "sentences_allagree") -> Path:
    """Download and cache a sentiment dataset from Hugging Face.
    
    Args:
        dataset_name: Name of the dataset on HF.
        subset: Specific subset/config of the dataset.
        
    Returns:
        Path to the cached dataset directory.
    """
    os.makedirs(DEFAULT_CACHE_DIR, exist_ok=True)
    
    logger.info("Downloading HF dataset: %s (%s) to %s", dataset_name, subset, DEFAULT_CACHE_DIR)
    
    try:
        dataset = load_dataset(dataset_name, subset, cache_dir=str(DEFAULT_CACHE_DIR))
        logger.info("Successfully loaded %s", dataset_name)
        return DEFAULT_CACHE_DIR
    except Exception as e:
        logger.error("Failed to download HF dataset %s: %s", dataset_name, e)
        raise

if __name__ == "__main__":
    # Quick test
    logging.basicConfig(level=logging.INFO)
    path = download_sentiment_dataset()
    print(f"Dataset cached at: {path}")
