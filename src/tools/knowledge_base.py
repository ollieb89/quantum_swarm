"""
src.tools.knowledge_base — Local knowledge base interface.

Queries local ChromaDB for sentiment and DuckDB for historical price data.
"""

import logging
from typing import Any
import chromadb
from chromadb.utils import embedding_functions
import duckdb

logger = logging.getLogger(__name__)

CHROMA_PATH = "data/chroma_db"
DUCKDB_PATH = "data/market_data.duckdb"

class KnowledgeBase:
    """Interface to local financial knowledge stores."""
    
    def __init__(self):
        self.chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        self.collection = self.chroma_client.get_or_create_collection(
            name="financial_sentiment", 
            embedding_function=self.embedding_function
        )
        self.duck_con = duckdb.connect(DUCKDB_PATH)

    def query_sentiment_context(self, query: str, n_results: int = 5) -> list[str]:
        """Perform semantic search for sentiment context related to query."""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            return results['documents'][0] if results['documents'] else []
        except Exception as e:
            logger.error("Error querying ChromaDB: %s", e)
            return []

    def query_historical_stats(self, symbol: str) -> dict[str, Any]:
        """Fetch basic historical stats from DuckDB for a symbol."""
        try:
            # Query for stats over the available history
            res = self.duck_con.execute(f"""
                SELECT 
                    COUNT(*) as data_points,
                    AVG(close) as avg_price,
                    MIN(low) as 5y_low,
                    MAX(high) as 5y_high,
                    STDDEV(close) as vol_std
                FROM historical_ohlcv
                WHERE symbol = '{symbol.upper()}'
            """).df()
            
            if res.empty or res.iloc[0]['data_points'] == 0:
                return {"error": f"No historical data for {symbol}"}
                
            return res.iloc[0].to_dict()
        except Exception as e:
            logger.error("Error querying DuckDB: %s", e)
            return {"error": str(e)}

    def __del__(self):
        self.duck_con.close()

# Global singleton
kb = KnowledgeBase()
