import pickle, numpy as np, pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.dummy import DummyClassifier
from sklearn.utils import resample

from .config import DAVIS_BBOX, MODEL_PKL, MODELS_DIR
from .features import extract_point
from .risk_rules import rule_score, label_from_score

MIN_PER_CLASS = 6  # upsample target per class to avoid stratify failures

def sample_grid(bbox, nx=14, ny=14):
    """Slightly denser grid to increase samples."""
    minx,miny,maxx,maxy = bbox
    lons = np.linspace(minx, maxx, nx)
    lats = np.linspace(miny, maxy, ny)
    return [(float(lon), float(lat)) for lon in lons for lat in lats]

def build_dataset(bbox):
    rows=[]
    for lon,lat in sample_grid(bbox):
        f = extract_point(lon, lat)
        s = rule_score(f)
        f["rule_score"] = s
        f["risk_label"] = label_from_score(s)
        rows.append(f)
    df = pd.DataFrame(rows)
    # Drop rows with all-None critical features (very rare)
    if {"fema_zone","fire_class","pga_g","storm_count_5km"}.issubset(df.columns):
        if df[["fema_zone","fire_class","pga_g","storm_count_5km"]].isna().all(axis=1).any():
            df = df[~df[["fema_zone","fire_class","pga_g","storm_count_5km"]].isna().all(axis=1)]
    return df.reset_index(drop=True)

def upsample_min_classes(df, label_col="risk_label", min_count=MIN_PER_CLASS, random_state=42):
    classes = df[label_col].value_counts()
    frames = []
    rng = np.random.RandomState(random_state)
    for cls, cnt in classes.items():
        sub = df[df[label_col] == cls]
        if cnt < min_count:
            sub_up = resample(sub, replace=True, n_samples=min_count, random_state=rng.randint(0, 1_000_000))
            frames.append(sub_up)
        else:
            frames.append(sub)
    return pd.concat(frames, ignore_index=True)

def train(df):
    X = df[["fema_zone","fire_class","pga_g","storm_count_5km"]]
    y = df["risk_label"]

    # If only one class → fallback to DummyClassifier
    unique_classes = y.unique()
    if len(unique_classes) == 1:
        print(f"Only one class present ({unique_classes[0]}). Using DummyClassifier.")
        pipe = DummyClassifier(strategy="most_frequent")
        pipe.fit(np.zeros((len(y), 1)), y)  # fit on dummy feature
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        with open(MODEL_PKL, "wb") as f:
            pickle.dump(pipe, f)
        print("Saved DummyClassifier to model.pkl")
        return

    # Upsample rare classes to ensure stratify works
    df_bal = upsample_min_classes(df, label_col="risk_label", min_count=MIN_PER_CLASS)
    Xb = df_bal[["fema_zone","fire_class","pga_g","storm_count_5km"]]
    yb = df_bal["risk_label"]

    pre = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), ["fema_zone","fire_class"]),
        ("num", "passthrough", ["pga_g","storm_count_5km"]),
    ])

    clf = RandomForestClassifier(n_estimators=220, random_state=42)
    pipe = Pipeline([("pre", pre), ("clf", clf)])

    # Try stratified split; if it still fails, do non-stratified
    try:
        Xtr, Xte, ytr, yte = train_test_split(Xb, yb, test_size=0.2, stratify=yb, random_state=42)
    except ValueError as e:
        print("Stratified split failed, falling back to non-stratified:", e)
        Xtr, Xte, ytr, yte = train_test_split(Xb, yb, test_size=0.2, random_state=42)

    pipe.fit(Xtr, ytr)
    acc = pipe.score(Xte, yte)
    print(f"Validation accuracy: {acc:.3f} on {len(yte)} samples (balanced training size={len(Xtr)})")

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    with open(MODEL_PKL, "wb") as f:
        pickle.dump(pipe, f)
    print("Saved model to", MODEL_PKL)

if __name__ == "__main__":
    df = build_dataset(DAVIS_BBOX)
    print("Label distribution before balancing:\n", df["risk_label"].value_counts())
    train(df)
