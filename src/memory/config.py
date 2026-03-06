# Chunking configuration constants for MemoryService.
# Tune these after real usage; do not hard-code elsewhere.

# Documents shorter than this (in approx tokens) are stored as a single chunk.
CHUNK_SINGLE_THRESHOLD_TOKENS: int = 512

# Maximum tokens per chunk when splitting.
CHUNK_MAX_TOKENS: int = 400

# Token overlap between adjacent chunks.
CHUNK_OVERLAP_TOKENS: int = 50

# Token approximation: 1 token ≈ 4 characters (rough GPT-style estimate).
CHARS_PER_TOKEN: int = 4

# ChromaDB collection name.
COLLECTION_NAME: str = "quantum_swarm_memory"

# Default number of results for search queries.
DEFAULT_SEARCH_K: int = 5

# Max content length (chars) per MemoryHit returned to callers.
MAX_HIT_CONTENT_CHARS: int = 2000

# Recency window for L1 routing enrichment (days).
L1_RECENCY_DAYS: int = 30
