# scripts/scrapers/flood_scraper.py

import requests
import geopandas as gpd
import json
import sys
sys.path.append('../..')
from config.settings import *

class FloodDataAccessor:
    """Access FEMA National Flood Hazard Layer data"""
    
    def __init__(self):
        # Use a simpler, more reliable endpoint
        self.rest_api_url = "https://hazards.fema.gov/gis/nfhl/rest/services/public/NFHL/MapServer/28"
    
    def query_flood_zones(self, bbox, output_format='geojson'):
        """
        Query FEMA flood zones for a bounding box
        """
        query_url = f"{self.rest_api_url}/query"
        
        # Simplified parameters
        params = {
            'where': '1=1',  # Get all features
            'geometry': f"{bbox['min_lon']},{bbox['min_lat']},{bbox['max_lon']},{bbox['max_lat']}",
            'geometryType': 'esriGeometryEnvelope',
            'spatialRel': 'esriSpatialRelIntersects',
            'outFields': '*',
            'returnGeometry': 'true',
            'outSR': '4326',
            'f': 'geojson'
        }
        
        try:
            print(f"  Querying FEMA flood zones...")
            response = requests.get(query_url, params=params, timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'features' in data and len(data['features']) > 0:
                    gdf = gpd.GeoDataFrame.from_features(data['features'])
                    gdf.crs = 'EPSG:4326'
                    return gdf
                else:
                    print("  No flood zone features returned")
                    return gpd.GeoDataFrame()
            else:
                print(f"  Query failed: HTTP {response.status_code}")
                print(f"  Response: {response.text[:200]}")
                return gpd.GeoDataFrame()
                
        except Exception as e:
            print(f"  Error querying flood zones: {str(e)}")
            return gpd.GeoDataFrame()
    
    def save_flood_zones(self, gdf, filename):
        """Save flood zone data to file"""
        if len(gdf) > 0:
            gdf.to_file(filename, driver='GeoJSON')
            return True
        return False

# Test/Usage
if __name__ == "__main__":
    accessor = FloodDataAccessor()
    
    print("Querying Florida flood zones...")
    florida_floods = accessor.query_flood_zones(FLORIDA_BBOX)
    
    if len(florida_floods) > 0:
        accessor.save_flood_zones(
            florida_floods,
            '../../data/geojson/florida_flood_zones.geojson'
        )
        print(f"✓ Saved {len(florida_floods)} flood zone features")
    else:
        print("✗ No flood data retrieved")
