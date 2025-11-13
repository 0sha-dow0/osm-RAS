import glob, chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from .config import DOCS_DIR, RAG_INDEX_DIR

def chunks(s, n=800, overlap=120):
    i=0; out=[]
    while i < len(s):
        out.append(s[i:i+n]); i += (n-overlap)
    return out

def main():
    RAG_INDEX_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(RAG_INDEX_DIR), settings=Settings(allow_reset=True))
    col = client.get_or_create_collection("hazards")
    embed = SentenceTransformer("all-MiniLM-L6-v2")
    ids, docs = [], []
    for p in glob.glob(str(DOCS_DIR / "*.txt")):
        text = open(p, "r", encoding="utf-8", errors="ignore").read()
        for j, ch in enumerate(chunks(text)):
            ids.append(f"{p.split('/')[-1]}_{j}")
            docs.append(ch)
    embs = embed.encode(docs, convert_to_numpy=True, show_progress_bar=True)
    col.add(ids=ids, documents=docs, embeddings=embs.tolist())
    print(f"Indexed {len(docs)} chunks.")

if __name__ == "__main__":
    main()
