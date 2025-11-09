# --- PATH SHIM (required when Streamlit runs a script) ---
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # project root
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
# ---------------------------------------------------------

# Use ABSOLUTE imports from the 'src' package:
from src.predict import predict_point
from src.render_map import render_map
from src.config import MAPS_DIR
from src.risk_rules import rule_score
from src.rag_answer import explain

import streamlit as st


st.set_page_config(page_title="Local Multi-Hazard Risk", layout="wide")
st.title("Local Multi-Hazard Risk (Open Sample Data + Local RAG)")

left, right = st.columns([1,1])
with left:
    lon = st.number_input("Longitude", value=-121.7400, format="%.6f")
    lat = st.number_input("Latitude",  value=38.5400,  format="%.6f")

    if st.button("Analyze"):
        with st.spinner("Analyzing site..."):
            feats, label = predict_point(lon, lat)
            img = MAPS_DIR / f"site_{lon:.4f}_{lat:.4f}.png"
            render_map(lon, lat, str(img))
            st.session_state["feats"] = feats
            st.session_state["label"] = label
            st.session_state["img"]   = str(img)

with right:
    if "img" in st.session_state:
        st.image(st.session_state["img"], caption="Hazard overlays")

st.markdown("---")

if "feats" in st.session_state:
    feats = st.session_state["feats"]
    label = st.session_state["label"]

    st.subheader(f"Overall risk: **{label}**")
    # show “why” numerically
    st.caption("Top drivers (rule contributions, points):")
    flood_pts  = 40 if feats.get("fema_zone","").upper().startswith("A") else 15 if feats.get("fema_zone","").upper().startswith("X") else 0
    fire_s     = str(feats.get("fire_class","")).lower()
    fire_pts   = 30 if "very" in fire_s else 20 if "high" in fire_s else 10 if "moderate" in fire_s else 0
    pga        = feats.get("pga_g") or 0.0
    quake_pts  = 25 if pga >= 0.35 else 15 if pga >= 0.20 else 0
    storms_n   = feats.get("storm_count_5km",0)
    storm_pts  = 10 if storms_n >= 5 else 5 if storms_n >= 2 else 0
    st.write({
        "flood_points": flood_pts,
        "fire_points": fire_pts,
        "quake_points": quake_pts,
        "storm_points": storm_pts
    })

    st.write("**Raw factors:**")
    st.json(feats)

    if st.button("Explain my risk (local LLM)"):
        with st.spinner("Generating local explanation..."):
            txt = explain(feats, label)
            st.write(txt)
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
