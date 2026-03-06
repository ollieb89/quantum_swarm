"""
scripts.index_financial_datasets — Index financial datasets into local databases.

This script:
1. Loads downloaded Hugging Face and Kaggle datasets.
2. Embeds sentiment text and stores in ChromaDB.
3. Loads structured market data CSVs into DuckDB.
"""

import logging
import os
from pathlib import Path
import pandas as pd
import chromadb
from chromadb.utils import embedding_functions
import duckdb
from src.tools.data_sources.hf_loader import download_sentiment_dataset
from src.tools.data_sources.kaggle_loader import download_market_dataset

logger = logging.getLogger(__name__)

# Constants
CHROMA_PATH = "data/chroma_db"
DUCKDB_PATH = "data/market_data.duckdb"

def index_hf_sentiment():
    """Download and index HF sentiment data into ChromaDB."""
    logger.info("Indexing HF sentiment data...")
    dataset_path = download_sentiment_dataset()
    
    # Actually, datasets.load_dataset returns the dataset object
    from datasets import load_dataset
    ds = load_dataset("takala/financial_phrasebank", "sentences_allagree", split="train")
    
    df = ds.to_pandas()
    
    # Initialize Chroma
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    
    # Default embedding function (all-MiniLM-L6-v2 via sentence-transformers)
    default_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    
    collection = client.get_or_create_collection(name="financial_sentiment", embedding_function=default_ef)
    
    # Chunk and index (Chroma prefers batches)
    batch_size = 500
    for i in range(0, len(df), batch_size):
        batch = df.iloc[i:i+batch_size]
        ids = [str(idx) for idx in batch.index]
        documents = batch['sentence'].tolist()
        metadatas = [{"label": int(row['label'])} for _, row in batch.iterrows()]
        
        collection.add(ids=ids, documents=documents, metadatas=metadatas)
    
    logger.info("Indexed %d sentiment sentences into ChromaDB.", len(df))

def index_kaggle_market_data():
    """Download and index Kaggle market data into DuckDB."""
    logger.info("Indexing Kaggle market data into DuckDB...")
    # NOTE: The 9000-tickers dataset is LARGE. We'll start with a small subset or just setup the table.
    dataset_path = download_market_dataset()
    
    con = duckdb.connect(DUCKDB_PATH)
    
    # Find CSV files in the downloaded path
    csv_files = list(dataset_path.glob("**/*.csv"))
    if not csv_files:
        logger.warning("No CSV files found in Kaggle dataset at %s", dataset_path)
        return

    # For this implementation, we'll index the first few files to prove the concept
    # In a full run, we would iterate all or use DuckDB's glob import
    logger.info("Found %d CSV files. Indexing subset...", len(csv_files))
    
    # Create table schema based on expected OHLCV
    con.execute("""
        CREATE TABLE IF NOT EXISTS historical_ohlcv (
            symbol VARCHAR,
            date DATE,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            volume BIGINT,
            adj_close DOUBLE
        )
    """)
    
    # DuckDB is very fast at reading CSVs
    # We'll assume the files are in 'stocks' subdir and named SYMBOL.csv
    # This is a common Kaggle structure
    stock_dir = dataset_path / "stocks"
    if stock_dir.exists():
        logger.info("Importing from %s", stock_dir)
        # We can use a single SQL command to import all CSVs if they share a schema
        # We'll add the filename as 'symbol'
        try:
            # This is a powerful DuckDB feature: reading multiple files and injecting the filename as a column
            con.execute(f"""
                INSERT INTO historical_ohlcv
                SELECT 
                    regexp_extract(filename, '([^/]+)\.csv$', 1) as symbol,
                    Date as date,
                    Open as open,
                    High as high,
                    Low as low,
                    Close as close,
                    Volume as volume,
                    "Adj Close" as adj_close
                FROM read_csv_auto('{stock_dir}/*.csv', filename=True)
                LIMIT 1000000 -- limit to 1M rows for safety in this task
            """)
            logger.info("Successfully indexed market data into DuckDB.")
        except Exception as e:
            logger.error("Error importing CSVs: %s", e)
    else:
        logger.warning("No 'stocks' directory found in dataset.")
    
    con.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Ensure data dir exists
    Path("data").mkdir(exist_ok=True)
    
    index_hf_sentiment()
    index_kaggle_market_data()
