import os
import json
import requests
import numpy as np
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from src.config import RAG_INDEX_DIR  # ABSOLUTE import, not relative
from typing import Optional

# Embedder (small model; loaded once)
EMB = SentenceTransformer("all-MiniLM-L6-v2")

def _retrieve(query: str, k: int = 4) -> str:
    client = chromadb.PersistentClient(
        path=str(RAG_INDEX_DIR),
        settings=Settings(anonymized_telemetry=False),
    )
    col = client.get_or_create_collection("hazards")
    qemb = EMB.encode([query], convert_to_numpy=True)
    res = col.query(query_embeddings=qemb.tolist(), n_results=k)
    docs = res.get("documents", [[]])[0]
    return "\n\n".join(docs) if docs else ""

def _ollama_generate_http(prompt: str, model: Optional[str] = None, timeout: int = 60) -> str:
    model = model or os.environ.get("HAZARD_LLM_MODEL", "phi3:mini")
    try:
        r = requests.post(
            "http://127.0.0.1:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_ctx": 1024,
                    "num_predict": 160,
                    "temperature": 0.4,
                },
            },
            timeout=timeout,
        )
        r.raise_for_status()
        js = r.json()
        return js.get("response", "").strip() or "(No response)"
    except Exception as e:
        return f"(Local LLM unavailable: {e})"

def explain(feats: dict, label: str) -> str:
    """Return a short explanation from the local LLM; fall back to a rule-based text if needed."""
    q = (
        f"flood={feats.get('fema_zone')}, "
        f"fire={feats.get('fire_class')}, "
        f"pga={feats.get('pga_g')}, "
        f"storms5km={feats.get('storm_count_5km')}"
    )
    ctx = _retrieve(q, k=4)
    prompt = f"""
Write 3–5 clear sentences for a homeowner.

Overall risk: {label}
Data (JSON):
{json.dumps(feats, indent=2)}

Use the reference notes when helpful:
{ctx}

Explain the main drivers of the risk and give one or two practical mitigation steps.
"""
    resp = _ollama_generate_http(prompt)

    # If Ollama is not available, return a deterministic explanation
    if resp.lower().startswith("(local llm unavailable"):
        flood = feats.get("fema_zone") or "None"
        fire = feats.get("fire_class") or "None"
        pga = feats.get("pga_g") or 0.0
        storms = int(feats.get("storm_count_5km") or 0)

        tips = []
        if str(flood).upper().startswith("A"):
            tips.append("elevating the foundation and improving site drainage")
        if "high" in str(fire).lower():
            tips.append("using ember-resistant vents and keeping defensible space clear")
        if (pga or 0) >= 0.2:
            tips.append("adding basic seismic anchoring and securing heavy furnishings")
        if storms >= 2:
            tips.append("upsizing gutters and adding overflow paths for heavy rain")

        tiptext = "; ".join(tips) if tips else "following local building codes and standard site preparation"
        return (
            f"Overall risk is {label}. Flood zone={flood}, fire class={fire}, "
            f"estimated shaking (PGA)≈{pga}, and storm events within 5 km={storms}. "
            f"These factors together drive the rating. Consider mitigation steps such as {tiptext}."
        )

    return resp
