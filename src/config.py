from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

DATA_RAW       = BASE / "data" / "raw"
DATA_PROCESSED = BASE / "data" / "processed"
DOCS_DIR       = BASE / "data" / "docs"
RAG_INDEX_DIR  = BASE / "rag_index"
MODELS_DIR     = BASE / "models"
OUTPUT_DIR     = BASE / "output"
MAPS_DIR       = OUTPUT_DIR / "maps"

# Processed files used by the app
FEMA_GPKG      = DATA_PROCESSED / "fema_nfhl.gpkg"     # flood-like polygons (FLD_ZONE)
CALFIRE_GPKG   = DATA_PROCESSED / "calfire_fhsz.gpkg"  # fire polygons (HAZ_CLASS)
USGS_PGA_GPKG  = DATA_PROCESSED / "usgs_pga.gpkg"      # quake polygon(s) (PGA_G)
NOAA_STORMS_GP = DATA_PROCESSED / "noaa_storms.gpkg"   # storm points

MODEL_PKL = MODELS_DIR / "model.pkl"

# Davis bbox: (minx, miny, maxx, maxy)
DAVIS_BBOX = (-122.0, 38.35, -121.50, 38.70)

TARGET_CRS = "EPSG:4326"
