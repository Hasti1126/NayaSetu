__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import chromadb
from loguru import logger
from pathlib import Path
import chromadb
# DB_PATH = Path(__file__).parent.parent / "db" / "chroma"
COLLECTION_NAME = "indian_law"

# def get_db():
#     DB_PATH.mkdir(parents=True, exist_ok=True)
#     return chromadb.PersistentClient(path=str(DB_PATH))


def get_db():
    return chromadb.CloudClient(
        api_key=os.environ["CHROMA_API_KEY"],
        tenant=os.environ["CHROMA_TENANT"],
        database=os.environ["CHROMA_DATABASE"],
    )

def get_collection():
    client = get_db()
    # Uses ChromaDB's built-in embeddings — no sentence_transformers needed
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    return collection

def upsert_documents(documents: list[dict]):
    if not documents:
        logger.warning("No documents to upsert")
        return
    collection = get_collection()
    batch_size = 100
    total = 0
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        ids, texts, metadatas = [], [], []
        for doc in batch:
            url = doc["metadata"].get("url", "unknown")
            chunk_idx = doc["metadata"].get("chunk_index", 0)
            ids.append(f"{abs(hash(url))}_{chunk_idx}")
            texts.append(doc["text"])
            metadatas.append(doc["metadata"])
        collection.upsert(ids=ids, documents=texts, metadatas=metadatas)
        total += len(batch)
    logger.info(f"✅ Upserted {total} chunks. Total in DB: {collection.count()}")

def retrieve(query: str, n_results: int = 5, doc_type: str = None) -> list[dict]:
    collection = get_collection()
    if collection.count() == 0:
        logger.warning("ChromaDB is empty!")
        return []
    where = {"type": doc_type} if doc_type else None
    results = collection.query(
        query_texts=[query],
        n_results=min(n_results, collection.count()),
        where=where,
        include=["documents", "metadatas", "distances"],
    )
    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        chunks.append({
            "text": doc,
            "source": meta.get("title", "Unknown"),
            "url": meta.get("url", ""),
            "type": meta.get("type", ""),
            "scraped_at": meta.get("scraped_at", ""),
            "similarity": round((1 - dist) * 100, 1),
        })
    return chunks

# def get_stats() -> dict:
#     try:
#         collection = get_collection()
#         return {
#             "total_chunks": collection.count(),
#             "collection": COLLECTION_NAME,
#             "embedding_model": "ChromaDB Built-in",
#             "db_path": str(DB_PATH),
#         }
#     except Exception as e:
#         return {"error": str(e), "total_chunks": 0}
def get_stats() -> dict:
    try:
        collection = get_collection()
        return {
            "total_chunks": collection.count(),
            "collection": COLLECTION_NAME,
            "embedding_model": "ChromaDB Built-in",
            "db_path": "Chroma Cloud",  # no local path anymore
        }
    except Exception as e:
        return {"error": str(e), "total_chunks": 0}
