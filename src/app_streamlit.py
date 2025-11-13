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
    lon = st.number_input("Longitude", value=-118.250000, format="%.6f")
    lat = st.number_input("Latitude",  value=34.050000,   format="%.6f")

    if st.button("Analyze"):
        with st.spinner("Analyzing site..."):
            feats, label = predict_point(lon, lat)
            img = MAPS_DIR / f"site_{lon:.4f}_{lat:.4f}.png"
            # pass label into map so marker color matches risk
            render_map(lon, lat, label, str(img))
            st.session_state["feats"] = feats
            st.session_state["label"] = label
            st.session_state["img"] = str(img)

with right:
    if "img" in st.session_state:
        st.image(
            st.session_state["img"],
            caption="Local context around the selected location",
            use_column_width=True,
        )

st.markdown("---")

if "feats" in st.session_state:
    feats = st.session_state["feats"]
    label = st.session_state["label"]

    st.subheader(f"Overall risk: **{label}**")

    st.caption("Main factors contributing to this rating:")

    # Safely unpack features
    flood_zone = (feats.get("fema_zone") or "None").upper()
    fire_class = (feats.get("fire_class") or "None")
    pga = feats.get("pga_g") or 0.0
    storms_n = int(feats.get("storm_count_5km") or 0)

    # Simple human-readable bullets instead of raw dict/JSON
    st.markdown(
        f"""
- **Flood exposure:** `{flood_zone}`
- **Fire exposure class:** `{fire_class}`
- **Estimated shaking (PGA):** `{pga:.2f} g`
- **Storm events within 5 km:** `{storms_n}`
"""
    )

    if st.button("Explain my risk (local LLM)"):
        with st.spinner("Generating local explanation..."):
            txt = explain(feats, label)
        st.write(txt)
