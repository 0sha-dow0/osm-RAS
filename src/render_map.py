import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point
import contextily as cx
from shapely.ops import unary_union

from .config import FEMA_GPKG, CALFIRE_GPKG, USGS_PGA_GPKG, NOAA_STORMS_GP, MAPS_DIR

COLORS = {
    "flood": "#2c7fb8",
    "fire": "#d7301f",
    "quake": "#feb24c",
    "storm": "#31a354",
}

RISK_COLORS = {
    "Low": "#2ca02c",
    "Moderate": "#ff7f0e",
    "High": "#d62728",
    "Very High": "#8b0000",
}


def _bounds_union(*gdfs_m, pad=1000.0):
    boxes = []
    for g in gdfs_m:
        if g is None or getattr(g, "empty", True):
            continue
        minx, miny, maxx, maxy = g.total_bounds
        boxes.append((minx, miny, maxx, maxy))
    if not boxes:
        return None
    arr = np.array(boxes)
    return (
        arr[:, 0].min() - pad,
        arr[:, 1].min() - pad,
        arr[:, 2].max() + pad,
        arr[:, 3].max() + pad,
    )


def render_map(lon: float, lat: float, risk_label: str, outfile: str):
    # Load layers
    fema = gpd.read_file(FEMA_GPKG)
    cal = gpd.read_file(CALFIRE_GPKG)
    usgs = gpd.read_file(USGS_PGA_GPKG)
    storms = gpd.read_file(NOAA_STORMS_GP)

    site = gpd.GeoDataFrame(geometry=[Point(lon, lat)], crs="EPSG:4326")

    # Reproject to Web Mercator
    fema_m = fema.to_crs(3857) if not fema.empty else fema
    cal_m = cal.to_crs(3857) if not cal.empty else cal
    usgs_m = usgs.to_crs(3857) if not usgs.empty else usgs
    storms_m = storms.to_crs(3857) if not storms.empty else storms
    site_m = site.to_crs(3857)

    # Determine extent
    extent = _bounds_union(fema_m, cal_m, usgs_m, storms_m, site_m, pad=1200.0)
    if extent is None:
        sx = site_m.geometry.x.iloc[0]
        sy = site_m.geometry.y.iloc[0]
        pad = 2000
        extent = (sx - pad, sy - pad, sx + pad, sy + pad)

    minx, miny, maxx, maxy = extent

    MAPS_DIR.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8.5, 8.5))
    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)

    # Basemap
    try:
        cx.add_basemap(ax, crs=site_m.crs, source=cx.providers.OpenStreetMap.Mapnik, alpha=0.9)
    except Exception:
        ax.set_facecolor("white")

    # Flood-like
    if not fema_m.empty:
        fema_m.boundary.plot(ax=ax, color=COLORS["flood"], linewidth=0.8, alpha=0.9, zorder=3)
        fema_m.plot(ax=ax, facecolor=COLORS["flood"], alpha=0.15, edgecolor="none", zorder=2)

    # Fire
    if not cal_m.empty:
        cal_m.boundary.plot(ax=ax, color=COLORS["fire"], linewidth=0.8, alpha=0.9, zorder=3)

    # Quake
    if not usgs_m.empty:
        usgs_m.plot(ax=ax, facecolor=COLORS["quake"], edgecolor="#8c5800", linewidth=0.6, alpha=0.25, zorder=3)

    # Storm
    if not storms_m.empty:
        storms_m.plot(ax=ax, color=COLORS["storm"], markersize=18, alpha=0.9, zorder=4)

    # Site marker
    risk_color = RISK_COLORS.get(risk_label, "black")
    site_m.plot(ax=ax, color=risk_color, markersize=70, edgecolor="white", linewidth=1.2, zorder=10)

    # Label
    sx = site_m.geometry.x.iloc[0]
    sy = site_m.geometry.y.iloc[0]
    ax.annotate(
        risk_label,
        xy=(sx, sy),
        xytext=(sx + 400, sy + 400),
        textcoords="data",
        fontsize=9,
        weight="bold",
        color=risk_color,
        bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.8),
        zorder=11,
    )

    ax.set_title("Overlapping Hazard Layers with Basemap", pad=12)
    ax.grid(False)

    fig.tight_layout()
    fig.savefig(outfile, dpi=220)
    plt.close(fig)
