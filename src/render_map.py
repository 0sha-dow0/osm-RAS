import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point
import contextily as cx

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


def render_map(lon: float, lat: float, risk_label: str, outfile: str):
    """Render a zoomed-in (~2km) map with OSM basemap, hazards, and legend."""
    # Load hazard layers
    fema = gpd.read_file(FEMA_GPKG)
    cal = gpd.read_file(CALFIRE_GPKG)
    usgs = gpd.read_file(USGS_PGA_GPKG)
    storms = gpd.read_file(NOAA_STORMS_GP)

    # Site
    site = gpd.GeoDataFrame(geometry=[Point(lon, lat)], crs="EPSG:4326")

    # Project to Web Mercator
    fema_m = fema.to_crs(3857) if not fema.empty else fema
    cal_m = cal.to_crs(3857) if not cal.empty else cal
    usgs_m = usgs.to_crs(3857) if not usgs.empty else usgs
    storms_m = storms.to_crs(3857) if not storms.empty else storms
    site_m = site.to_crs(3857)

    # 2 km zoom window
    sx = site_m.geometry.x.iloc[0]
    sy = site_m.geometry.y.iloc[0]
    pad = 2000
    minx, miny, maxx, maxy = sx - pad, sy - pad, sx + pad, sy + pad

    MAPS_DIR.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(7.0, 7.0))

    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)

    # Basemap
    try:
        cx.add_basemap(ax, crs=site_m.crs, source=cx.providers.OpenStreetMap.Mapnik, alpha=0.9)
    except Exception:
        ax.set_facecolor("white")

    # ----- Hazard overlays -----
    if not fema_m.empty:
        fema_m.boundary.plot(ax=ax, color=COLORS["flood"], linewidth=0.8, alpha=0.9, zorder=3)
        fema_m.plot(ax=ax, facecolor=COLORS["flood"], alpha=0.18, edgecolor="none", zorder=2)

    if not cal_m.empty:
        cal_m.boundary.plot(ax=ax, color=COLORS["fire"], linewidth=0.8, alpha=0.9, zorder=3)

    if not usgs_m.empty:
        usgs_m.plot(
            ax=ax,
            facecolor=COLORS["quake"],
            alpha=0.25,
            edgecolor="#8c5800",
            linewidth=0.6,
            zorder=3,
        )

    if not storms_m.empty:
        storms_m.plot(ax=ax, color=COLORS["storm"], markersize=18, alpha=0.9, zorder=4)

    # ----- Site marker -----
    risk_color = RISK_COLORS.get(risk_label, "black")
    site_m.plot(
        ax=ax,
        color=risk_color,
        markersize=70,
        edgecolor="white",
        linewidth=1.2,
        zorder=10,
    )

    # Title
    ax.set_title("Local Hazard Context (≈2 km around site)", pad=10)
    ax.grid(False)

    # ----- Legend -----
    import matplotlib.patches as mpatches

    legend_items = [
        mpatches.Patch(facecolor=COLORS["flood"], edgecolor="none", alpha=0.4, label="Flood-like (near water)"),
        mpatches.Patch(facecolor=COLORS["fire"], edgecolor="none", alpha=0.6, label="Fire-prone areas"),
        mpatches.Patch(facecolor=COLORS["quake"], edgecolor="none", alpha=0.6, label="Quake proxy"),
        mpatches.Patch(facecolor=COLORS["storm"], edgecolor="none", alpha=0.9, label="Storm proxy points"),
        mpatches.Patch(facecolor=risk_color, edgecolor="white", alpha=1.0, label=f"Site (Risk: {risk_label})"),
    ]

    ax.legend(
        handles=legend_items,
        loc="lower left",
        frameon=True,
        framealpha=0.92,
        fontsize=8,
        borderpad=0.5,
    )

    fig.tight_layout()
    fig.savefig(outfile, dpi=220)
    plt.close(fig)
