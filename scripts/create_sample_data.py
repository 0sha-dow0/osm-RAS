# scripts/create_sample_data.py

import pandas as pd
import os
import sys

print("Creating sample data...")

# Get the script directory
script_dir = os.path.dirname(os.path.abspath(__file__))
data_raw_dir = os.path.join(script_dir, '..', 'data', 'raw')
data_geojson_dir = os.path.join(script_dir, '..', 'data', 'geojson')

# Ensure directories exist
os.makedirs(data_raw_dir, exist_ok=True)
os.makedirs(data_geojson_dir, exist_ok=True)

print(f"Data directory: {data_raw_dir}")

# Create sample hurricane data
hurricane_data = {
    'storm_id': ['AL102023', 'AL092024', 'AL132024'],
    'storm_name': ['IDALIA', 'HELENE', 'MILTON'],
    'year': [2023, 2024, 2024],
    'datetime': ['20230830', '20240926', '20241009'],
    'latitude': [29.0, 30.0, 27.2],
    'longitude': [-83.5, -84.0, -82.7],
    'max_wind': [125, 140, 120],
    'min_pressure': [940, 938, 945]
}

hurricane_file = os.path.join(data_raw_dir, 'hurricanes_2023_2025.csv')
df_hurricane = pd.DataFrame(hurricane_data)
df_hurricane.to_csv(hurricane_file, index=False)
print(f"✓ Created sample hurricane data: {hurricane_file}")
print(f"  File size: {os.path.getsize(hurricane_file)} bytes")

# Create empty but valid earthquake file
earthquake_file = os.path.join(data_raw_dir, 'earthquakes_florida_2023_2025.csv')
df_quake = pd.DataFrame(columns=['id', 'magnitude', 'place', 'time', 'longitude', 'latitude', 'depth', 'type', 'url'])
df_quake.to_csv(earthquake_file, index=False)
print(f"✓ Created earthquake data file: {earthquake_file}")
print(f"  File size: {os.path.getsize(earthquake_file)} bytes")

print("\n✓✓ Sample data created successfully!")
print("You can now run: python3 run_pipeline.py")
