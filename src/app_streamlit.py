# --- PATH SHIM (required when Streamlit runs a script) ---
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # project root
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
# ---------------------------------------------------------

import streamlit as st

from src.predict import predict_point
from src.render_map import render_map
from src.config import MAPS_DIR
from src.rag_answer import explain


st.set_page_config(page_title="Local Multi-Hazard Risk", layout="wide")
st.title("Local Multi-Hazard Risk (Open Sample Data + Local RAG)")

left, right = st.columns([1, 1])

with left:
    lon = st.number_input("Longitude", value=-121.7400, format="%.6f")
    lat = st.number_input("Latitude", value=38.5400, format="%.6f")

    if st.button("Analyze"):
        with st.spinner("Analyzing site..."):
            feats, label = predict_point(lon, lat)
            img = MAPS_DIR / f"site_{lon:.4f}_{lat:.4f}.png"
            # NEW: pass the risk label into the map renderer
            render_map(lon, lat, label, str(img))
            st.session_state["feats"] = feats
            st.session_state["label"] = label
            st.session_state["img"] = str(img)


with right:
    if "img" in st.session_state:
        st.image(st.session_state["img"], caption="Hazard overlays", use_column_width=True)

st.markdown("---")

if "feats" in st.session_state:
    feats = st.session_state["feats"]
    label = st.session_state["label"]

    st.subheader(f"Overall risk: **{label}**")

    # ---------- SAFE DRIVER CONTRIBUTIONS ----------
    st.caption("Top drivers (rule contributions, points):")

    # flood
    flood_zone = (feats.get("fema_zone") or "").upper()
    if flood_zone.startswith("A"):
        flood_pts = 40
    elif flood_zone.startswith("X"):
        flood_pts = 15
    else:
        flood_pts = 0

    # fire
    fire_s = (feats.get("fire_class") or "").lower()
    if "very" in fire_s:
        fire_pts = 30
    elif "high" in fire_s:
        fire_pts = 20
    elif "moderate" in fire_s:
        fire_pts = 10
    else:
        fire_pts = 0

    # quake
    pga = float(feats.get("pga_g") or 0.0)
    if pga >= 0.35:
        quake_pts = 25
    elif pga >= 0.20:
        quake_pts = 15
    else:
        quake_pts = 0

    # storms
    storms_n = int(feats.get("storm_count_5km") or 0)
    if storms_n >= 5:
        storm_pts = 10
    elif storms_n >= 2:
        storm_pts = 5
    else:
        storm_pts = 0

    st.write({
        "flood_points": flood_pts,
        "fire_points": fire_pts,
        "quake_points": quake_pts,
        "storm_points": storm_pts,
    })
    # ----------------------------------------------

    st.write("**Raw factors:**")
    st.json(feats)

    if st.button("Explain my risk (local LLM)"):
        with st.spinner("Generating local explanation..."):
            txt = explain(feats, label)
        st.write(txt)
