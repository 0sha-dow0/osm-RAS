# scripts/processors/data_processor.py

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, Polygon
from datetime import datetime
import sys
sys.path.append('../..')
from config.settings import *

class DisasterDataProcessor:
    """Process and integrate multi-hazard disaster data"""
    
    def __init__(self, region_name, bbox):
        self.region_name = region_name
        self.bbox = bbox
        self.processed_data = {}
    
    def load_and_process_hurricanes(self, csv_path):
        """Process hurricane track data"""
        df = pd.read_csv(csv_path)
        
        # Create GeoDataFrame
        geometry = [Point(xy) for xy in zip(df['longitude'], df['latitude'])]
        gdf = gpd.GeoDataFrame(df, geometry=geometry, crs='EPSG:4326')
        
        # Classify intensity
        def classify_hurricane(wind_speed):
            if wind_speed >= 157:
                return 'Category 5'
            elif wind_speed >= 130:
                return 'Category 4'
            elif wind_speed >= 111:
                return 'Category 3'
            elif wind_speed >= 96:
                return 'Category 2'
            elif wind_speed >= 74:
                return 'Category 1'
            else:
                return 'Tropical Storm'
        
        gdf['intensity'] = gdf['max_wind'].apply(classify_hurricane)
        gdf['disaster_type'] = 'Hurricane'
        gdf['color'] = 'purple'
        
        self.processed_data['hurricanes'] = gdf
        return gdf
    
    def load_and_process_earthquakes(self, csv_path):
        """Process earthquake data"""
        df = pd.read_csv(csv_path)
        
        if len(df) > 0:
            geometry = [Point(xy) for xy in zip(df['longitude'], df['latitude'])]
            gdf = gpd.GeoDataFrame(df, geometry=geometry, crs='EPSG:4326')
            
            # Classify intensity
            def classify_earthquake(magnitude):
                if magnitude >= 7.0:
                    return 'Major'
                elif magnitude >= 5.0:
                    return 'Moderate'
                else:
                    return 'Minor'
            
            gdf['intensity'] = gdf['magnitude'].apply(classify_earthquake)
            gdf['disaster_type'] = 'Earthquake'
            gdf['color'] = 'gray'
            
            self.processed_data['earthquakes'] = gdf
            return gdf
        else:
            return gpd.GeoDataFrame()
    
    def process_flood_zones(self, geojson_path):
        """Process FEMA flood zone data"""
        gdf = gpd.read_file(geojson_path)
        
        # Add disaster classification
        gdf['disaster_type'] = 'Flood Zone'
        gdf['color'] = 'red'
        
        # Classify flood hazard zones
        if 'FLD_ZONE' in gdf.columns:
            def classify_flood_zone(zone):
                if zone in ['A', 'AE', 'AH', 'AO', 'AR', 'A99']:
                    return 'High Risk'
                elif zone in ['X', 'X500']:
                    return 'Moderate to Low Risk'
                elif zone in ['V', 'VE']:
                    return 'High Risk (Coastal)'
                else:
                    return 'Unknown'
            
            gdf['intensity'] = gdf['FLD_ZONE'].apply(classify_flood_zone)
        
        self.processed_data['floods'] = gdf
        return gdf
    
    def create_disaster_inventory(self):
        """Combine all disaster types into single inventory"""
        all_disasters = []
        
        for disaster_type, gdf in self.processed_data.items():
            if len(gdf) > 0:
                # Ensure consistent columns
                required_cols = ['disaster_type', 'intensity', 'color', 'geometry']
                gdf_subset = gdf[required_cols + [col for col in gdf.columns 
                                                   if col not in required_cols]]
                all_disasters.append(gdf_subset)
        
        if all_disasters:
            combined = gpd.GeoDataFrame(pd.concat(all_disasters, ignore_index=True))
            combined.crs = 'EPSG:4326'
            return combined
        else:
            return gpd.GeoDataFrame()
    
    def save_processed_data(self, output_dir='../../data/processed'):
        """Save processed data to files"""
        for disaster_type, gdf in self.processed_data.items():
            if len(gdf) > 0:
                filename = f"{output_dir}/{self.region_name}_{disaster_type}.geojson"
                gdf.to_file(filename, driver='GeoJSON')
                print(f"Saved {disaster_type}: {len(gdf)} features")
        
        # Save combined inventory
        combined = self.create_disaster_inventory()
        if len(combined) > 0:
            combined.to_file(
                f"{output_dir}/{self.region_name}_all_disasters.geojson",
                driver='GeoJSON'
            )
            print(f"Saved combined inventory: {len(combined)} total features")

# Usage example
if __name__ == "__main__":
    # Process Florida data
    florida_processor = DisasterDataProcessor('florida', FLORIDA_BBOX)
    florida_processor.load_and_process_hurricanes('../../data/raw/hurricanes_2023_2025.csv')
    florida_processor.load_and_process_earthquakes('../../data/raw/earthquakes_florida_2023_2025.csv')
    florida_processor.process_flood_zones('../../data/geojson/florida_flood_zones.geojson')
    florida_processor.save_processed_data()
