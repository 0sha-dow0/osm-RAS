# At the start of load_and_process_hurricanes method
def load_and_process_hurricanes(self, csv_path):
    """Process hurricane track data"""
    import os
    
    # Check if file exists and has content
    if not os.path.exists(csv_path):
        print(f"  Warning: {csv_path} does not exist")
        return gpd.GeoDataFrame()
    
    if os.path.getsize(csv_path) == 0:
        print(f"  Warning: {csv_path} is empty")
        return gpd.GeoDataFrame()
    
    try:
        df = pd.read_csv(csv_path)
        
        if len(df) == 0:
            print(f"  Warning: No data in {csv_path}")
            return gpd.GeoDataFrame()
        
        # Rest of your existing code...
