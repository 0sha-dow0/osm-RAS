# scripts/scrapers/hurricane_scraper.py

import requests
import pandas as pd
import gzip
from io import BytesIO
from datetime import datetime
import sys
sys.path.append('../..')
from config.settings import *

class HurricaneScraper:
    """Scrape NOAA hurricane track data"""
    
    def __init__(self, start_year, end_year):
        self.start_year = start_year
        self.end_year = end_year
        self.base_url = NOAA_HURRICANE_ARCHIVE
        
    def fetch_hurricane_data(self, storm_id, year):
        """
        Fetch hurricane track data for a specific storm
        storm_id format: 'AL092023' for 9th Atlantic storm of 2023
        """
        # Best track data (actual observed path)
        btk_url = f"{self.base_url}{year}/b{storm_id}.dat.gz"
        
        try:
            response = requests.get(btk_url, timeout=30)
            if response.status_code == 200:
                # Decompress gzip data
                with gzip.GzipFile(fileobj=BytesIO(response.content)) as f:
                    lines = f.read().decode('utf-8').split('\n')
                
                # Parse hurricane data
                tracks = []
                for line in lines:
                    if line.strip():
                        fields = [f.strip() for f in line.split(',')]
                        if len(fields) >= 8:
                            tracks.append({
                                'basin': fields[0],
                                'cyclone_number': fields[1],
                                'datetime': fields[2],
                                'record_type': fields[3],
                                'latitude': self._parse_coordinate(fields[4]),
                                'longitude': self._parse_coordinate(fields[5]),
                                'max_wind': int(fields[6]) if fields[6].strip() else None,
                                'min_pressure': int(fields[7]) if fields[7].strip() else None
                            })
                
                return pd.DataFrame(tracks)
            else:
                print(f"Failed to fetch {storm_id}: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error fetching {storm_id}: {str(e)}")
            return None
    
    def _parse_coordinate(self, coord_str):
        """Convert ATCF coordinate format to decimal degrees"""
        coord_str = coord_str.strip()
        if not coord_str:
            return None
        
        # ATCF format: e.g., "280N" or "820W"
        value = float(coord_str[:-1]) / 10.0
        direction = coord_str[-1]
        
        if direction in ['S', 'W']:
            value = -value
        
        return value
    
    def fetch_florida_hurricanes(self, hurricane_list):
        """
        Fetch data for specific hurricanes affecting Florida
        hurricane_list: [('AL102023', 'Idalia', 2023), ...]
        """
        all_data = []
        
        for storm_id, name, year in hurricane_list:
            print(f"Fetching {name} ({storm_id})...")
            df = self.fetch_hurricane_data(storm_id, year)
            if df is not None:
                df['storm_name'] = name
                df['year'] = year
                all_data.append(df)
        
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            # Filter for Florida region
            combined_df = combined_df[
                (combined_df['latitude'] >= FLORIDA_BBOX['min_lat']) &
                (combined_df['latitude'] <= FLORIDA_BBOX['max_lat']) &
                (combined_df['longitude'] >= FLORIDA_BBOX['min_lon']) &
                (combined_df['longitude'] <= FLORIDA_BBOX['max_lon'])
            ]
            return combined_df
        
        return pd.DataFrame()

# Usage example
if __name__ == "__main__":
    scraper = HurricaneScraper(2023, 2025)
    
    # Florida hurricanes from 2023-2024
    florida_hurricanes = [
        ('AL102023', 'Idalia', 2023),
        ('AL092024', 'Helene', 2024),
        ('AL132024', 'Milton', 2024)
    ]
    
    hurricane_df = scraper.fetch_florida_hurricanes(florida_hurricanes)
    hurricane_df.to_csv('../../data/raw/hurricanes_2023_2025.csv', index=False)
    print(f"Saved {len(hurricane_df)} hurricane track points")
