import os
from pathlib import Path
from chromadb import PersistentClient
import chromadb


def load_kb(kb_dir: str) -> list[dict]:
    """Read every file in data/kb/. Return [{'source': filename, 'text': ...}]. TODO."""
    documents: list[dict] = []
    for file in Path(kb_dir).iterdir():
        # print(file.name)
        content = file.read_text(encoding="utf-8")
        documents.append({
            "source": file.name,
            "text":content
        })
        
    return documents    

def chunk(docs: list[dict], size: int, overlap: int) -> list[dict]:
    """Split docs into chunks, keeping the source in metadata.
    TODO start with fixed-size. On the upgrade pass, try structure-aware (split on headings)."""
    
    if overlap >= size:
        raise ValueError("Overlap must be less than the size")
    
    chunks : list[dict] = []
    for doc in docs:
        text = doc["text"]
        start = 0
        while start < len(text):
            chunk_text = text[start: start + size]
            chunks.append({
                "source": doc["source"],
                "text": chunk_text
            })
            start = start + size - overlap
            
    return chunks
            
            
def build_index(chunks: list[dict]):
    """Embed chunks and store in Chroma (persistent). TODO: create collection, add texts+metadata."""
    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[str] = []
    
    client = chromadb.PersistentClient(path="data/chroma")
    
    collection = client.get_or_create_collection(name="Knowledge_base")
    
    for i, c in enumerate(chunks):
        ids.append(f"{c['source']} - {i}")
        documents.append(c["text"])
        metadatas.append({"source": c["source"]})
        
    collection.add(
        ids = ids,
        documents=documents,
        metadatas=metadatas
    )
    
if __name__ == "__main__":
    docs = load_kb("data/kb")
    chunks = chunk(docs,500,50)
    build_index(chunks)