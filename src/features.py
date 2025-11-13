import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from .config import FEMA_GPKG, CALFIRE_GPKG, USGS_PGA_GPKG, NOAA_STORMS_GP
from .schema_map import SCHEMA

def _load():
    return (
        gpd.read_file(FEMA_GPKG),
        gpd.read_file(CALFIRE_GPKG),
        gpd.read_file(USGS_PGA_GPKG),
        gpd.read_file(NOAA_STORMS_GP)
    )

def extract_point(lon: float, lat: float) -> dict:
    fema, cal, usgs, storms = _load()
    pt = gpd.GeoDataFrame(geometry=[Point(lon, lat)], crs="EPSG:4326")

    # FEMA zone
    try:
        j = gpd.sjoin(pt, fema, how="left", predicate="intersects") if not fema.empty else pt.assign(FLD_ZONE=None)
        fema_zone = j.get(SCHEMA["fema"]["zone_col"], pd.Series([None])).iloc[0]
    except Exception:
        fema_zone = None

    # CALFIRE hazard
    try:
        j = gpd.sjoin(pt, cal, how="left", predicate="intersects") if not cal.empty else pt.assign(HAZ_CLASS=None)
        fire_class = j.get(SCHEMA["calfire"]["hazard_col"], pd.Series([None])).iloc[0]
    except Exception:
        fire_class = None

    # USGS PGA
    try:
        j = gpd.sjoin(pt, usgs, how="left", predicate="intersects") if not usgs.empty else pt.assign(PGA_G=None)
        pga = j.get(SCHEMA["usgs_pga"]["value_col"], pd.Series([None])).iloc[0]
        pga = float(pga) if pga is not None and not pd.isna(pga) else None
    except Exception:
        pga = None

    # Storm frequency within 5 km (project to meters for accurate distance)
    try:
        if storms.empty:
            storm_count_5km = 0
        else:
            storms_m = storms.to_crs(3857)
            pt_m = pt.to_crs(3857)
            dists_m = storms_m.geometry.distance(pt_m.geometry.iloc[0])
            storm_count_5km = int((dists_m <= 5000).sum())
    except Exception:
        storm_count_5km = 0

    return {
        "lon": lon,
        "lat": lat,
        "fema_zone": None if pd.isna(fema_zone) else str(fema_zone),
        "fire_class": None if pd.isna(fire_class) else str(fire_class),
        "pga_g": pga,
        "storm_count_5km": storm_count_5km,
    }

