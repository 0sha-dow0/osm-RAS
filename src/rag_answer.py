import json, requests, chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from .config import RAG_INDEX_DIR

EMB = SentenceTransformer("all-MiniLM-L6-v2")

def _retrieve(query, k=4):
    client = chromadb.PersistentClient(path=str(RAG_INDEX_DIR),
                                       settings=Settings(anonymized_telemetry=False))
    col = client.get_or_create_collection("hazards")
    qemb = EMB.encode([query], convert_to_numpy=True)
    res = col.query(query_embeddings=qemb.tolist(), n_results=k)
    docs = res.get("documents", [[]])[0]
    return "\n\n".join(docs) if docs else ""

def _ollama_generate_http(prompt, model="phi3:mini", timeout=60):
    try:
        r = requests.post(
            "http://127.0.0.1:11434/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=timeout,
        )
        r.raise_for_status()
        js = r.json()
        return js.get("response", "").strip() or "(No response)"
    except Exception as e:
        return f"(Local LLM unavailable: {e})"

def explain(feats: dict, label: str) -> str:
    q = f"flood={feats.get('fema_zone')}, fire={feats.get('fire_class')}, pga={feats.get('pga_g')}, storms5km={feats.get('storm_count_5km')}"
    ctx = _retrieve(q, k=4)
    prompt = f"""
Write 3–5 clear sentences for a homeowner.

Overall risk: {label}
Data:
{json.dumps(feats, indent=2)}

Use the reference notes when helpful:
{ctx}

Explain the main drivers and give 1–2 practical mitigation steps.
"""
    return _ollama_generate_http(prompt)
