import json, time
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import geopandas as gpd
import requests
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
import io
from shapely.geometry import MultiPolygon




from .config import (
    DATA_RAW, DATA_PROCESSED, DAVIS_BBOX,
    FEMA_GPKG, CALFIRE_GPKG, USGS_PGA_GPKG, NOAA_STORMS_GP
)

DATA_RAW.mkdir(parents=True, exist_ok=True)
DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

def _bbox_str(b):
    minx, miny, maxx, maxy = b
    return f"{miny},{minx},{maxy},{maxx}"  # south,west,north,east

# ----- OSM water -> flood-like polygons -----
def build_fema_like_from_osm():
    q = f"""
    [out:json][timeout:60];
    (
      way["waterway"~"river|stream"]({_bbox_str(DAVIS_BBOX)});
      relation["waterway"~"river|stream"]({_bbox_str(DAVIS_BBOX)});
      way["natural"="water"]({_bbox_str(DAVIS_BBOX)});
      relation["natural"="water"]({_bbox_str(DAVIS_BBOX)});
    );
    out geom;
    """
    r = requests.post("https://overpass-api.de/api/interpreter", data=q, timeout=90)
    r.raise_for_status()
    data = r.json()

    geoms = []
    for el in data.get("elements", []):
        if "geometry" not in el:
            continue
        coords = [(pt["lon"], pt["lat"]) for pt in el["geometry"]]
        # Try polygon; if it's a line, we’ll buffer after reprojection
        try:
            if coords[0] != coords[-1]:
                coords.append(coords[0])
            poly = Polygon(coords)
            if poly.is_valid:
                geoms.append(poly)
        except Exception:
            try:
                line = gpd.GeoSeries([Point(c) for c in coords], crs="EPSG:4326").unary_union
                geoms.append(line)
            except Exception:
                pass

    if not geoms:
        gpd.GeoDataFrame({"FLD_ZONE":[]}, geometry=[], crs="EPSG:4326").to_file(FEMA_GPKG, driver="GPKG")
        return

    water = gpd.GeoDataFrame(geometry=geoms, crs="EPSG:4326").to_crs(3857)  # meters
    # buffer in meters (approx 300 m and 600 m rings)
    near_m = unary_union(water.buffer(300))
    far_m  = unary_union(water.buffer(600))

    a = gpd.GeoDataFrame({"FLD_ZONE":["A"]}, geometry=[near_m], crs=3857)
    x = gpd.GeoDataFrame({"FLD_ZONE":["X"]}, geometry=[far_m.difference(near_m)], crs=3857)

    out = pd.concat([a, x], ignore_index=True).to_crs(4326)
    out.to_file(FEMA_GPKG, driver="GPKG")
def _try_download(url):
    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        return resp
    except Exception:
        return None

def _firms_dataframe_or_none():
    candidates = [
        # VIIRS 7-day global (NRT)
        "https://firms.modaps.eosdis.nasa.gov/active_fire/c2/csv/VNP14IMGTDL_NRT_Global_7d.csv",
        # MODIS 7-day global (alt)
        "https://firms.modaps.eosdis.nasa.gov/active_fire/c1/csv/MODIS_C6_1_Global_7d.csv",
        # VIIRS USA (sometimes open)
        "https://firms.modaps.eosdis.nasa.gov/active_fire/c2/csv/country/USA_VNP14IMGTDL_NRT.csv",
    ]
    for url in candidates:
        r = _try_download(url)
        if r is not None and r.status_code == 200 and len(r.content) > 0:
            try:
                return pd.read_csv(io.BytesIO(r.content))
            except Exception:
                continue
    return None

def _fire_from_osm_forest_proxy():
    # fallback: forest/wood polygons → “High” exposure
    q = f"""
    [out:json][timeout:60];
    (
      way["landuse"="forest"]({_bbox_str(DAVIS_BBOX)});
      relation["landuse"="forest"]({_bbox_str(DAVIS_BBOX)});
      way["natural"="wood"]({_bbox_str(DAVIS_BBOX)});
      relation["natural"="wood"]({_bbox_str(DAVIS_BBOX)});
    );
    out geom;
    """
    r = requests.post("https://overpass-api.de/api/interpreter", data=q, timeout=90)
    r.raise_for_status()
    data = r.json()
    geoms = []
    for el in data.get("elements", []):
        if "geometry" not in el: continue
        coords = [(pt["lon"], pt["lat"]) for pt in el["geometry"]]
        try:
            if coords[0] != coords[-1]: coords.append(coords[0])
            poly = Polygon(coords)
            if poly.is_valid: geoms.append(poly)
        except Exception:
            pass
    if not geoms:
        return gpd.GeoDataFrame({"HAZ_CLASS":[]}, geometry=[], crs="EPSG:4326")
    gdf = gpd.GeoDataFrame(geometry=geoms, crs="EPSG:4326").to_crs(3857)
    poly = unary_union(gdf.buffer(100))  # small edge buffer, meters
    if isinstance(poly, (Polygon, MultiPolygon)):
        out = gpd.GeoDataFrame({"HAZ_CLASS":["High"]}, geometry=[poly], crs=3857).to_crs(4326)
        return out
    return gpd.GeoDataFrame({"HAZ_CLASS":[]}, geometry=[], crs="EPSG:4326")

# ----- NASA FIRMS -> fire polygons -----
def build_fire_from_firms():
    df = _firms_dataframe_or_none()
    minx, miny, maxx, maxy = DAVIS_BBOX

    if df is None or not {"longitude","latitude"}.issubset(df.columns):
        # FIRMS not reachable or unexpected schema → fallback to OSM forest proxy
        out = _fire_from_osm_forest_proxy()
        out.to_file(CALFIRE_GPKG, driver="GPKG")
        return

    # filter to bbox
    df = df[(df["longitude"]>=minx)&(df["longitude"]<=maxx)&
            (df["latitude"] >=miny)&(df["latitude"] <=maxy)]

    if df.empty:
        # no recent fires → write empty but valid layer
        gpd.GeoDataFrame({"HAZ_CLASS":[]}, geometry=[], crs="EPSG:4326").to_file(CALFIRE_GPKG, driver="GPKG")
        return

    g = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.longitude, df.latitude), crs="EPSG:4326").to_crs(3857)

    # buffer in meters (scale 300–800 m if brightness exists; else constant 500 m)
    if "bright_ti4" in df.columns and df["bright_ti4"].notna().any():
        b = df["bright_ti4"].fillna(df["bright_ti4"].median())
        rad_m = np.interp(b, (b.min(), b.max()), (300, 800))
    else:
        rad_m = np.full(len(g), 500.0)
    polys = [pt.buffer(r) for pt, r in zip(g.geometry, rad_m)]
    unioned = unary_union(polys)

    area_km2 = gpd.GeoSeries([unioned], crs=3857).area.iloc[0] / 1e6
    level = "Very High" if area_km2 > 5 else "High"
    out = gpd.GeoDataFrame({"HAZ_CLASS":[level]}, geometry=[unioned], crs=3857).to_crs(4326)
    out.to_file(CALFIRE_GPKG, driver="GPKG")


# ----- USGS quakes -> quake polygon + PGA proxy -----
def build_quake_from_usgs():
    url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_month.geojson"
    gj = requests.get(url).json()
    feats = gj.get("features", [])
    rows = []
    minx,miny,maxx,maxy = DAVIS_BBOX
    for f in feats:
        lon, lat = f["geometry"]["coordinates"][:2]
        if not (minx<=lon<=maxx and miny<=lat<=maxy): continue
        mag = f["properties"].get("mag", 2.5)
        rows.append((lon,lat,mag))
    if not rows:
        gpd.GeoDataFrame({"PGA_G":[]}, geometry=[], crs="EPSG:4326").to_file(USGS_PGA_GPKG, driver="GPKG"); return
    g = gpd.GeoDataFrame(rows, columns=["lon","lat","mag"],
                         geometry=gpd.points_from_xy([r[0] for r in rows],[r[1] for r in rows]),
                         crs="EPSG:4326")
    g["PGA_G"] = np.clip(10**(0.5*g["mag"] - 3.2), 0.05, 0.6)
    km = np.clip((g["mag"]-2.5)*8, 5, 40)   # 5–40 km
    deg = km / 111.0
    poly = unary_union([pt.buffer(r) for pt,r in zip(g.geometry, deg)])
    gpd.GeoDataFrame({"PGA_G":[float(g["PGA_G"].max())]}, geometry=[poly], crs="EPSG:4326").to_file(USGS_PGA_GPKG, driver="GPKG")

# ----- Open-Meteo heavy-rain proxy -> storm points -----
def build_storm_points_from_openmeteo():
    end = datetime.utcnow().date()
    start = end - timedelta(days=365)
    minx, miny, maxx, maxy = DAVIS_BBOX
    lons = np.linspace(minx, maxx, 6)
    lats = np.linspace(miny, maxy, 6)
    rows = []
    for la in lats:
        for lo in lons:
            url = ("https://archive-api.open-meteo.com/v1/archive?"
                   f"latitude={la:.4f}&longitude={lo:.4f}&start_date={start}&end_date={end}"
                   "&daily=precipitation_sum&timezone=UTC")
            try:
                d = requests.get(url, timeout=30).json()
                pr = d.get("daily", {}).get("precipitation_sum", [])
                cnt = sum(1 for x in pr if x is not None and x >= 25)
                if cnt > 0: rows.append((lo, la, cnt))
            except Exception:
                pass
            time.sleep(0.15)
    if not rows:
        gpd.GeoDataFrame(columns=["lon","lat","storm_days"], geometry=[], crs="EPSG:4326").to_file(NOAA_STORMS_GP, driver="GPKG"); return
    df = pd.DataFrame(rows, columns=["lon","lat","storm_days"])
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat), crs="EPSG:4326")
    gdf.to_file(NOAA_STORMS_GP, driver="GPKG")

def main():
    print("Building flood-like layer from OSM water ...");   build_fema_like_from_osm()
    print("Building fire layer from NASA FIRMS ...");       build_fire_from_firms()
    print("Building quake layer from USGS quakes ...");     build_quake_from_usgs()
    print("Building storm points from Open-Meteo ...");     build_storm_points_from_openmeteo()
    print("Done. Files saved to data/processed/")

if __name__ == "__main__":
    main()
