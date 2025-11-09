# scripts/scrapers/earthquake_scraper.py

import requests
import pandas as pd
from datetime import datetime
import sys
sys.path.append('../..')
from config.settings import *

class EarthquakeScraper:
    """Fetch USGS earthquake data via API"""
    
    def __init__(self):
        self.base_url = USGS_EARTHQUAKE_API
    
    def fetch_earthquakes(self, start_date, end_date, min_magnitude=2.0, bbox=None):
        """
        Fetch earthquake data for specified date range and region
        bbox: [minlon, minlat, maxlon, maxlat]
        """
        params = {
            'format': 'geojson',
            'starttime': start_date,
            'endtime': end_date,
            'minmagnitude': min_magnitude,
            'orderby': 'time'
        }
        
        if bbox:
            params['minlatitude'] = bbox['min_lat']
            params['maxlatitude'] = bbox['max_lat']
            params['minlongitude'] = bbox['min_lon']
            params['maxlongitude'] = bbox['max_lon']
        
        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Parse GeoJSON features
                earthquakes = []
                for feature in data['features']:
                    props = feature['properties']
                    coords = feature['geometry']['coordinates']
                    
                    earthquakes.append({
                        'id': feature['id'],
                        'magnitude': props.get('mag'),
                        'place': props.get('place'),
                        'time': datetime.fromtimestamp(props['time']/1000),
                        'longitude': coords[0],
                        'latitude': coords[1],
                        'depth': coords[2],
                        'type': props.get('type'),
                        'url': props.get('url')
                    })
                
                return pd.DataFrame(earthquakes)
            else:
                print(f"API request failed: HTTP {response.status_code}")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"Error fetching earthquake data: {str(e)}")
            return pd.DataFrame()

# Usage example
if __name__ == "__main__":
    scraper = EarthquakeScraper()
    
    # Fetch Florida earthquakes
    florida_quakes = scraper.fetch_earthquakes(
        START_DATE, 
        END_DATE,
        min_magnitude=2.0,
        bbox=FLORIDA_BBOX
    )
    
    florida_quakes.to_csv('../../data/raw/earthquakes_florida_2023_2025.csv', index=False)
    print(f"Saved {len(florida_quakes)} earthquake events")
