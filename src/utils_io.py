import geopandas as gpd
from shapely.geometry import box
from .config import TARGET_CRS

def clip_to_bbox(gdf, bbox):
    gdf = gdf.set_crs("EPSG:4326", allow_override=True)
    roi = gpd.GeoDataFrame(geometry=[box(*bbox)], crs="EPSG:4326")
    out = gpd.overlay(gdf, roi, how="intersection")
    return out.to_crs(TARGET_CRS)
