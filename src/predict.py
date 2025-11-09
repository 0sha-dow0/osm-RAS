import pickle
import pandas as pd
from pathlib import Path

from src.config import MODEL_PKL
from src.features import extract_point

# Load trained model (RandomForest pipeline or DummyClassifier)
with open(MODEL_PKL, "rb") as f:
    MODEL = pickle.load(f)

COLUMNS = ["fema_zone", "fire_class", "pga_g", "storm_count_5km"]

def _coerce_features_for_model(feat: dict) -> pd.DataFrame:
    # Ensure correct types and no None values that would break the pipeline
    row = {
        "fema_zone": (feat.get("fema_zone") or "None"),
        "fire_class": (feat.get("fire_class") or "None"),
        "pga_g": float(feat.get("pga_g") or 0.0),
        "storm_count_5km": int(feat.get("storm_count_5km") or 0),
    }
    return pd.DataFrame([row], columns=COLUMNS)

def predict_point(lon: float, lat: float):
    # Extract raw geospatial features
    feat = extract_point(lon, lat)
    # Build a single-row DataFrame with the exact columns the model expects
    X = _coerce_features_for_model(feat)

    # Some models (DummyClassifier) may not support .predict_proba; label only is fine
    label = MODEL.predict(X)[0]
    return feat, label
