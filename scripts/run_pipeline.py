# scripts/run_pipeline.py

import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append('..')

# Import all components
from scrapers.hurricane_scraper import HurricaneScraper
from scrapers.earthquake_scraper import EarthquakeScraper
from scrapers.flood_scraper import FloodDataAccessor
from processors.data_processor import DisasterDataProcessor
from visualization.map_generator import DisasterMapGenerator
from config.settings import *

def run_full_pipeline():
    """Execute complete disaster mapping pipeline"""
    
    print("="*80)
    print("DISASTER MAPPING PIPELINE - STARTED")
    print(f"Timestamp: {datetime.now()}")
    print("="*80)
    
    # Phase 1: Data Acquisition
    print("\n[PHASE 1] Data Acquisition")
    print("-"*40)
    
    # Hurricane data
    print("Fetching hurricane data...")
    hurricane_scraper = HurricaneScraper(2023, 2025)
    florida_hurricanes = [
        ('AL102023', 'Idalia', 2023),
        ('AL092024', 'Helene', 2024),
        ('AL132024', 'Milton', 2024)
    ]
    hurricane_df = hurricane_scraper.fetch_florida_hurricanes(florida_hurricanes)
    hurricane_df.to_csv('../data/raw/hurricanes_2023_2025.csv', index=False)
    print(f"✓ Saved {len(hurricane_df)} hurricane track points")
    
    # Earthquake data
    print("Fetching earthquake data...")
    eq_scraper = EarthquakeScraper()
    florida_quakes = eq_scraper.fetch_earthquakes(
        START_DATE, END_DATE, min_magnitude=2.0, bbox=FLORIDA_BBOX
    )
    florida_quakes.to_csv('../data/raw/earthquakes_florida_2023_2025.csv', index=False)
    print(f"✓ Saved {len(florida_quakes)} earthquake events")
    
    # Flood zone data
    print("Fetching flood zone data...")
    flood_accessor = FloodDataAccessor()
    florida_floods = flood_accessor.query_flood_zones(FLORIDA_BBOX)
    if florida_floods is not None:
        flood_accessor.save_flood_zones(
            florida_floods, '../data/geojson/florida_flood_zones.geojson'
        )
        print(f"✓ Saved {len(florida_floods)} flood zone features")
    
    orlando_floods = flood_accessor.query_flood_zones(ORLANDO_BBOX)
    if orlando_floods is not None:
        flood_accessor.save_flood_zones(
            orlando_floods, '../data/geojson/orlando_flood_zones.geojson'
        )
        print(f"✓ Saved {len(orlando_floods)} Orlando flood zones")
    
    # Phase 2: Data Processing
    print("\n[PHASE 2] Data Processing")
    print("-"*40)
    
    # Process Florida data
    print("Processing Florida data...")
    florida_processor = DisasterDataProcessor('florida', FLORIDA_BBOX)
    florida_processor.load_and_process_hurricanes('../data/raw/hurricanes_2023_2025.csv')
    florida_processor.load_and_process_earthquakes('../data/raw/earthquakes_florida_2023_2025.csv')
    florida_processor.process_flood_zones('../data/geojson/florida_flood_zones.geojson')
    florida_processor.save_processed_data()
    print("✓ Florida data processed")
    
    # Process Orlando data (subset of Florida)
    print("Processing Orlando data...")
    orlando_processor = DisasterDataProcessor('orlando', ORLANDO_BBOX)
    # Filter hurricane data for Orlando region
    orlando_hurricanes = hurricane_df[
        (hurricane_df['latitude'] >= ORLANDO_BBOX['min_lat']) &
        (hurricane_df['latitude'] <= ORLANDO_BBOX['max_lat']) &
        (hurricane_df['longitude'] >= ORLANDO_BBOX['min_lon']) &
        (hurricane_df['longitude'] <= ORLANDO_BBOX['max_lon'])
    ]
    orlando_hurricanes.to_csv('../data/raw/hurricanes_orlando_2023_2025.csv', index=False)
    orlando_processor.load_and_process_hurricanes('../data/raw/hurricanes_orlando_2023_2025.csv')
    orlando_processor.process_flood_zones('../data/geojson/orlando_flood_zones.geojson')
    orlando_processor.save_processed_data()
    print("✓ Orlando data processed")
    
    # Phase 3: Map Generation
    print("\n[PHASE 3] Map Generation")
    print("-"*40)
    
    # Generate Florida map
    print("Generating Florida disaster map...")
    florida_map = DisasterMapGenerator('florida', 27.8, -81.5, zoom_start=7)
    florida_map.create_base_map()
    florida_map.add_all_disasters()
    florida_map.add_layer_control()
    florida_map.add_legend()
    florida_map.save_map('../maps/output/florida_disaster_map.html')
    print("✓ Florida map generated")
    
    # Generate Orlando map
    print("Generating Orlando disaster map...")
    orlando_map = DisasterMapGenerator('orlando', 28.5, -81.38, zoom_start=10)
    orlando_map.create_base_map()
    orlando_map.add_all_disasters()
    orlando_map.add_layer_control()
    orlando_map.add_legend()
    orlando_map.save_map('../maps/output/orlando_disaster_map.html')
    print("✓ Orlando map generated")
    
    print("\n" + "="*80)
    print("PIPELINE COMPLETED SUCCESSFULLY")
    print(f"Timestamp: {datetime.now()}")
    print("="*80)
    print("\nOutput files:")
    print("  - ../maps/output/florida_disaster_map.html")
    print("  - ../maps/output/orlando_disaster_map.html")

if __name__ == "__main__":
    try:
        run_full_pipeline()
    except Exception as e:
        print(f"\n❌ Pipeline failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
