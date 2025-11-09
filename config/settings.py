# config/settings.py

# NOAA Hurricane Data
NOAA_HURRICANE_BASE_URL = "https://www.nhc.noaa.gov/gis/"
NOAA_HURRICANE_ARCHIVE = "https://ftp.nhc.noaa.gov/atcf/archive/"

# FEMA Flood Data
FEMA_NFHL_REST_API = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer"
FEMA_MSC_URL = "https://msc.fema.gov"

# USGS Earthquake Data
USGS_EARTHQUAKE_API = "https://earthquake.usgs.gov/fdsnws/event/1/query"
USGS_EARTHQUAKE_FEED = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/"

# U.S. Drought Monitor
DROUGHT_MONITOR_URL = "https://droughtmonitor.unl.edu/data/json/"
DROUGHT_MONITOR_SHAPEFILE = "https://droughtmonitor.unl.edu/data/shapefiles_m/"

# National Weather Service (Tornado/Severe Weather)
NWS_API_BASE = "https://api.weather.gov"

# Florida-specific parameters
FLORIDA_BBOX = {
    'min_lat': 24.5,
    'max_lat': 31.0,
    'min_lon': -87.6,
    'max_lon': -80.0
}

ORLANDO_BBOX = {
    'min_lat': 28.3,
    'max_lat': 28.7,
    'min_lon': -81.6,
    'max_lon': -81.1
}

# Date range for analysis
START_DATE = "2023-01-01"
END_DATE = "2025-10-29"
