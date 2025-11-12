# scripts/scrapers/hurricane_scraper.py

import requests
import pandas as pd
from datetime import datetime
import sys
sys.path.append('../..')
from config.settings import *

class HurricaneScraper:
    """Scrape NOAA hurricane track data"""
    
    def __init__(self, start_year, end_year):
        self.start_year = start_year
        self.end_year = end_year
        # Correct NOAA best track archive URL
        self.base_url = "https://www.nhc.noaa.gov/data/hurdat/"
        
    def fetch_atlantic_hurricanes(self, year):
        """
        Fetch all Atlantic hurricane data for a year from HURDAT2
        """
        # HURDAT2 database URL (contains all Atlantic storms)
        hurdat_url = "https://www.nhc.noaa.gov/data/hurdat/hurdat2-1851-2023-051124.txt"
        
        try:
            print(f"  Downloading HURDAT2 database...")
            response = requests.get(hurdat_url, timeout=30)
            
            if response.status_code == 200:
                lines = response.text.split('\n')
                
                storms = []
                current_storm = None
                
                for line in lines:
                    if not line.strip():
                        continue
                    
                    # Header line: storm ID, name, number of records
                    if line[0:2] == 'AL':
                        parts = line.split(',')
                        storm_id = parts[0].strip()
                        storm_name = parts[1].strip()
                        storm_year = int(storm_id[4:8])
                        
                        if storm_year == year:
                            current_storm = {'id': storm_id, 'name': storm_name, 'year': storm_year}
                    
                    # Data line: track point
                    elif current_storm is not None:
                        parts = [p.strip() for p in line.split(',')]
                        if len(parts) >= 7:
                            storms.append({
                                'storm_id': current_storm['id'],
                                'storm_name': current_storm['name'],
                                'year': current_storm['year'],
                                'datetime': parts[0],
                                'record_type': parts[2],
                                'latitude': self._parse_hurdat_coord(parts[4]),
                                'longitude': self._parse_hurdat_coord(parts[5]),
                                'max_wind': int(parts[6]) if parts[6].strip() and parts[6].strip() != '-999' else None,
                                'min_pressure': int(parts[7]) if len(parts) > 7 and parts[7].strip() and parts[7].strip() != '-999' else None
                            })
                
                return pd.DataFrame(storms)
            else:
                print(f"  Failed to fetch HURDAT2: HTTP {response.status_code}")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"  Error fetching hurricane data: {str(e)}")
            return pd.DataFrame()
    
    def _parse_hurdat_coord(self, coord_str):
        """Convert HURDAT2 coordinate format to decimal degrees"""
        coord_str = coord_str.strip()
        if not coord_str or coord_str == '-999':
            return None
        
        # HURDAT2 format: e.g., "28.0N" or "82.0W"
        value = float(coord_str[:-1])
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
        
        # Get unique years
        years = set([year for _, _, year in hurricane_list])
        
        for year in years:
            print(f"Fetching {year} hurricane data...")
            df = self.fetch_atlantic_hurricanes(year)
            
            if df is not None and len(df) > 0:
                # Filter for requested storms
                storm_names = [name for _, name, y in hurricane_list if y == year]
                df_filtered = df[df['storm_name'].str.upper().isin([n.upper() for n in storm_names])]
                
                if len(df_filtered) > 0:
                    all_data.append(df_filtered)
        
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

# Test/Usage
if __name__ == "__main__":
    scraper = HurricaneScraper(2023, 2025)
    
    florida_hurricanes = [
        ('AL102023', 'Idalia', 2023),
        ('AL092024', 'Helene', 2024),
        ('AL132024', 'Milton', 2024)
    ]
    
    hurricane_df = scraper.fetch_florida_hurricanes(florida_hurricanes)
    
    if len(hurricane_df) > 0:
        hurricane_df.to_csv('../../data/raw/hurricanes_2023_2025.csv', index=False)
        print(f"✓ Saved {len(hurricane_df)} hurricane track points")
    else:
        print("✗ No hurricane data retrieved")
