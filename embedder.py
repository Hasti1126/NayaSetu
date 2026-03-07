# pipeline/embedder.py
# Converts text chunks → embeddings → stores in ChromaDB vector database

import chromadb
from chromadb.utils import embedding_functions
from loguru import logger
from pathlib import Path

# ── ChromaDB setup ───────────────────────────────────────────────────────────
DB_PATH = Path(__file__).parent.parent / "db" / "chroma"
COLLECTION_NAME = "indian_law"

# Use sentence-transformers locally — no API key, runs offline
# "multi-qa-MiniLM-L6-cos-v1" is small (80MB), fast, and great for Q&A retrieval
EMBEDDING_MODEL = "multi-qa-MiniLM-L6-cos-v1"


def get_db():
    """Get or create ChromaDB client."""
    DB_PATH.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(DB_PATH))
    return client


def get_collection():
    """Get or create the law collection with sentence-transformer embeddings."""
    client = get_db()
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"},  # cosine similarity for legal text
    )
    return collection


def upsert_documents(documents: list[dict]):
    """
    Insert or update documents in ChromaDB.
    Uses URL + chunk_index as unique ID so re-scraping updates existing entries.
    """
    if not documents:
        logger.warning("No documents to upsert")
        return

    collection = get_collection()

    # Batch in groups of 100 (ChromaDB limit)
    batch_size = 100
    total_upserted = 0

    for i in range(0, len(documents), batch_size):
        batch = documents[i : i + batch_size]

        ids = []
        texts = []
        metadatas = []

        for doc in batch:
            # Stable ID: hash of URL + chunk index
            url = doc["metadata"].get("url", "unknown")
            chunk_idx = doc["metadata"].get("chunk_index", 0)
            doc_id = f"{hash(url)}_{chunk_idx}"

            ids.append(doc_id)
            texts.append(doc["text"])
            metadatas.append(doc["metadata"])

        collection.upsert(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
        )
        total_upserted += len(batch)
        logger.info(f"  Upserted batch {i // batch_size + 1}: {len(batch)} chunks")

    logger.info(f"✅ Total upserted: {total_upserted} chunks into ChromaDB")
    logger.info(f"📊 Collection size: {collection.count()} total documents")


def retrieve(query: str, n_results: int = 5, doc_type: str = None) -> list[dict]:
    """
    Retrieve most relevant law chunks for a query.
    
    Args:
        query: User's legal question or document clause
        n_results: Number of chunks to retrieve
        doc_type: Optional filter by type (statute, judgement, news)
    
    Returns:
        List of relevant chunks with text + metadata
    """
    collection = get_collection()

    if collection.count() == 0:
        logger.warning("ChromaDB is empty — run the scraper first!")
        return []

    # Build where filter if doc_type specified
    where = {"type": doc_type} if doc_type else None

    results = collection.query(
        query_texts=[query],
        n_results=min(n_results, collection.count()),
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    # Format results
    chunks = []
    for i, (doc, meta, dist) in enumerate(
        zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        )
    ):
        # Convert cosine distance to similarity score (0-100)
        similarity = round((1 - dist) * 100, 1)

        chunks.append({
            "text": doc,
            "source": meta.get("title", "Unknown"),
            "url": meta.get("url", ""),
            "type": meta.get("type", ""),
            "scraped_at": meta.get("scraped_at", ""),
            "similarity": similarity,
            "rank": i + 1,
        })

    return chunks


def get_stats() -> dict:
    """Get DB statistics for the status endpoint."""
    try:
        collection = get_collection()
        count = collection.count()
        return {
            "total_chunks": count,
            "collection": COLLECTION_NAME,
            "embedding_model": EMBEDDING_MODEL,
            "db_path": str(DB_PATH),
        }
    except Exception as e:
        return {"error": str(e), "total_chunks": 0}
