import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point
from shapely.ops import unary_union
from .config import FEMA_GPKG, CALFIRE_GPKG, USGS_PGA_GPKG, NOAA_STORMS_GP, MAPS_DIR

COLORS = {"flood":"#2c7fb8", "fire":"#d7301f", "quake":"#feb24c", "storm":"#31a354"}

def _union_or_none(gdf):
    if gdf is None or gdf.empty:
        return None
    return unary_union(gdf.geometry)

def _tight_bounds_with_padding(geoms_4326, pad_m=1200):
    """Compute bounds around given geometries (EPSG:4326), pad in meters, return (minx,miny,maxx,maxy) in EPSG:4326."""
    # collect non-empty geoms
    geoms_4326 = [g for g in geoms_4326 if g is not None and not g.is_empty]
    if not geoms_4326:
        return None
    gs = gpd.GeoSeries(geoms_4326, crs="EPSG:4326").to_crs(3857)  # meters
    merged = unary_union(gs)
    padded = gpd.GeoSeries([merged.buffer(pad_m)], crs=3857).to_crs(4326).geometry.iloc[0]
    return padded.bounds  # (minx, miny, maxx, maxy)

def render_map(lon, lat, outfile):
    fema = gpd.read_file(FEMA_GPKG)
    cal  = gpd.read_file(CALFIRE_GPKG)
    usgs = gpd.read_file(USGS_PGA_GPKG)
    storms = gpd.read_file(NOAA_STORMS_GP)

    site = gpd.GeoDataFrame(geometry=[Point(lon, lat)], crs="EPSG:4326")

    # unions (for extent calc)
    fema_u   = _union_or_none(fema)
    cal_u    = _union_or_none(cal)
    usgs_u   = _union_or_none(usgs)
    # storms are points; buffer a little in meters to include them in extent if present
    storms_u = None
    if not storms.empty:
        storms_m = storms.to_crs(3857)              # project to meters
        storms_buf = storms_m.buffer(300)           # 300 m buffer
        storms_u_m = unary_union(storms_buf)        # shapely geometry in 3857
        if storms_u_m is not None and not storms_u_m.is_empty:
            storms_u = (
                gpd.GeoSeries([storms_u_m], crs=3857)
                .to_crs(4326)
                .geometry.iloc[0]
            )

    extent_geoms = [
        geom
        for geom in (fema_u, cal_u, usgs_u, storms_u, site.geometry.iloc[0])
        if geom is not None and not geom.is_empty
    ]
    extent = _tight_bounds_with_padding(extent_geoms)
    if extent is None:
        # fall back to +/- 0.1 deg around site
        extent = (lon-0.1, lat-0.1, lon+0.1, lat+0.1)

    MAPS_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.5, 8.5), facecolor="white")

    # Draw in consistent order (polygons first, points last)
    if not fema.empty:
        fema.plot(ax=ax, facecolor=COLORS["flood"], edgecolor="#1d4e89",
                  alpha=0.35, linewidth=0.6, zorder=1, label="Flood-like (near water)")
    if not cal.empty:
        cal.plot(ax=ax, facecolor=COLORS["fire"], edgecolor="#7f1d1d",
                 alpha=0.25, linewidth=0.6, zorder=2, label="Fire (recent/fire-prone)")
    if not usgs.empty:
        usgs.plot(ax=ax, facecolor=COLORS["quake"], edgecolor="#8c5800",
                  alpha=0.25, linewidth=0.6, zorder=3, label="Quake (proxy)")

    if not storms.empty:
        storms.plot(ax=ax, markersize=16, color=COLORS["storm"],
                    alpha=0.8, zorder=4, label="Storm proxy points")

    site.plot(ax=ax, color="black", markersize=60, zorder=10, label="Selected site")

    ax.set_xlim(extent[0], extent[2]); ax.set_ylim(extent[1], extent[3])
    ax.set_title("Overlapping Hazard Layers (Open Sample Data)", pad=12)
    leg = ax.legend(loc="lower left", frameon=True, framealpha=0.9, borderpad=0.6)
    for lh in leg.legendHandles:
        try:
            lh.set_alpha(0.9)
        except Exception:
            pass
    ax.grid(True, alpha=0.15, linewidth=0.5)
    fig.tight_layout()
    fig.savefig(outfile, dpi=220)
    plt.close(fig)
