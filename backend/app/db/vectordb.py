import os
import chromadb

CHROMA_DATA_PATH = os.getenv("CHROMA_DATA_PATH", "./chroma_data")
client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
collection = client.get_or_create_collection(name="prospects")

def upsert_prospect(url: str, context: str):
    """Upsert a prospect URL and its BI context into ChromaDB."""
    collection.upsert(
        documents=[context],
        metadatas=[{"url": url}],
        ids=[url]
    )

def query_prospects(context: str, n_results: int = 1):
    """Query prospects based on context."""
    results = collection.query(
        query_texts=[context],
        n_results=n_results
    )
    return results
