# scripts/scrapers/flood_scraper.py

import requests
import geopandas as gpd
from shapely.geometry import box
import sys
sys.path.append('../..')
from config.settings import *

class FloodDataAccessor:
    """Access FEMA National Flood Hazard Layer data"""
    
    def __init__(self):
        self.rest_api_url = FEMA_NFHL_REST_API
    
    def query_flood_zones(self, bbox, output_format='geojson'):
        """
        Query FEMA flood zones for a bounding box
        bbox: dict with min_lat, max_lat, min_lon, max_lon
        """
        # Construct query endpoint
        query_url = f"{self.rest_api_url}/query"
        
        # Create bounding box geometry for spatial query
        geometry_envelope = {
            'xmin': bbox['min_lon'],
            'ymin': bbox['min_lat'],
            'xmax': bbox['max_lon'],
            'ymax': bbox['max_lat'],
            'spatialReference': {'wkid': 4326}
        }
        
        params = {
            'geometry': str(geometry_envelope),
            'geometryType': 'esriGeometryEnvelope',
            'inSR': 4326,
            'spatialRel': 'esriSpatialRelIntersects',
            'outFields': '*',
            'returnGeometry': 'true',
            'f': output_format
        }
        
        try:
            response = requests.get(query_url, params=params, timeout=60)
            
            if response.status_code == 200:
                if output_format == 'geojson':
                    data = response.json()
                    # Convert to GeoDataFrame
                    gdf = gpd.GeoDataFrame.from_features(data['features'])
                    return gdf
                else:
                    return response.json()
            else:
                print(f"Query failed: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error querying flood zones: {str(e)}")
            return None
    
    def save_flood_zones(self, gdf, filename, format='geojson'):
        """Save flood zone data to file"""
        if format == 'geojson':
            gdf.to_file(filename, driver='GeoJSON')
        elif format == 'shapefile':
            gdf.to_file(filename, driver='ESRI Shapefile')

# Usage example
if __name__ == "__main__":
    accessor = FloodDataAccessor()
    
    # Query Florida flood zones
    print("Querying Florida flood zones...")
    florida_floods = accessor.query_flood_zones(FLORIDA_BBOX)
    
    if florida_floods is not None:
        accessor.save_flood_zones(
            florida_floods,
            '../../data/geojson/florida_flood_zones.geojson'
        )
        print(f"Saved {len(florida_floods)} flood zone features")
    
    # Query Orlando flood zones
    print("Querying Orlando flood zones...")
    orlando_floods = accessor.query_flood_zones(ORLANDO_BBOX)
    
    if orlando_floods is not None:
        accessor.save_flood_zones(
            orlando_floods,
            '../../data/geojson/orlando_flood_zones.geojson'
        )
        print(f"Saved {len(orlando_floods)} Orlando flood zone features")
