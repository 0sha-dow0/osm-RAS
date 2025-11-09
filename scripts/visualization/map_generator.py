# scripts/visualization/map_generator.py

import folium
from folium.plugins import MarkerCluster, HeatMap
import geopandas as gpd
import pandas as pd
import sys
sys.path.append('../..')
from config.settings import *

class DisasterMapGenerator:
    """Generate interactive disaster maps using Folium"""
    
    def __init__(self, region_name, center_lat, center_lon, zoom_start=7):
        self.region_name = region_name
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.zoom_start = zoom_start
        self.map = None
        
        # Color scheme for disaster types
        self.color_map = {
            'Hurricane': 'purple',
            'Flood': 'red',
            'Flood Zone': 'red',
            'Tornado': 'green',
            'Drought': 'yellow',
            'Wildfire': 'orange',
            'Earthquake': 'gray'
        }
    
    def create_base_map(self):
        """Initialize base map with OpenStreetMap tiles"""
        self.map = folium.Map(
            location=[self.center_lat, self.center_lon],
            zoom_start=self.zoom_start,
            tiles='OpenStreetMap',
            control_scale=True
        )
        return self.map
    
    def add_disaster_layer(self, gdf, disaster_type, use_clusters=False):
        """Add a disaster type layer to the map"""
        if len(gdf) == 0:
            return
        
        color = self.color_map.get(disaster_type, 'blue')
        
        # Create feature group for layer control
        feature_group = folium.FeatureGroup(name=disaster_type)
        
        if use_clusters:
            marker_cluster = MarkerCluster().add_to(feature_group)
        
        # Add features based on geometry type
        for idx, row in gdf.iterrows():
            geom_type = row.geometry.geom_type
            
            # Create popup content
            popup_html = f"""
            <div style="font-family: Arial; font-size: 12px;">
                <b>{disaster_type}</b><br>
                <b>Intensity:</b> {row.get('intensity', 'N/A')}<br>
            """
            
            # Add additional info based on disaster type
            if disaster_type == 'Hurricane' and 'storm_name' in row:
                popup_html += f"<b>Storm:</b> {row['storm_name']}<br>"
                popup_html += f"<b>Max Wind:</b> {row.get('max_wind', 'N/A')} mph<br>"
            elif disaster_type == 'Earthquake' and 'magnitude' in row:
                popup_html += f"<b>Magnitude:</b> {row['magnitude']}<br>"
                popup_html += f"<b>Place:</b> {row.get('place', 'N/A')}<br>"
            
            popup_html += "</div>"
            
            if geom_type == 'Point':
                coords = [row.geometry.y, row.geometry.x]
                marker = folium.CircleMarker(
                    location=coords,
                    radius=6,
                    popup=folium.Popup(popup_html, max_width=300),
                    color=color,
                    fill=True,
                    fillColor=color,
                    fillOpacity=0.6,
                    weight=2
                )
                
                if use_clusters:
                    marker.add_to(marker_cluster)
                else:
                    marker.add_to(feature_group)
            
            elif geom_type in ['Polygon', 'MultiPolygon']:
                folium.GeoJson(
                    row.geometry,
                    style_function=lambda x, color=color: {
                        'fillColor': color,
                        'color': color,
                        'weight': 2,
                        'fillOpacity': 0.3
                    },
                    popup=folium.Popup(popup_html, max_width=300)
                ).add_to(feature_group)
        
        feature_group.add_to(self.map)
    
    def add_all_disasters(self, processed_data_dir='../../data/processed'):
        """Add all disaster types from processed data directory"""
        import os
        
        for filename in os.listdir(processed_data_dir):
            if filename.startswith(self.region_name) and filename.endswith('.geojson'):
                if 'all_disasters' in filename:
                    continue  # Skip combined file
                
                filepath = os.path.join(processed_data_dir, filename)
                gdf = gpd.read_file(filepath)
                
                # Extract disaster type from filename or data
                if 'disaster_type' in gdf.columns:
                    disaster_type = gdf['disaster_type'].iloc[0]
                else:
                    # Parse from filename
                    disaster_type = filename.replace(f"{self.region_name}_", "").replace(".geojson", "")
                
                print(f"Adding layer: {disaster_type} ({len(gdf)} features)")
                self.add_disaster_layer(gdf, disaster_type, use_clusters=True)
    
    def add_layer_control(self):
        """Add layer control widget"""
        folium.LayerControl(position='topright', collapsed=False).add_to(self.map)
    
    def add_legend(self):
        """Add custom legend to map"""
        legend_html = '''
        <div style="position: fixed; 
                    bottom: 50px; right: 50px; width: 200px; height: auto; 
                    background-color: white; z-index:9999; font-size:14px;
                    border:2px solid grey; border-radius:5px; padding: 10px">
        <p style="margin-bottom:5px; font-weight: bold;">Disaster Types</p>
        '''
        
        for disaster_type, color in self.color_map.items():
            legend_html += f'''
            <p style="margin:3px 0">
                <i style="background:{color}; width:15px; height:15px; 
                   display:inline-block; border:1px solid black; margin-right:5px;"></i>
                {disaster_type}
            </p>
            '''
        
        legend_html += '</div>'
        self.map.get_root().html.add_child(folium.Element(legend_html))
    
    def save_map(self, output_path):
        """Save map to HTML file"""
        self.map.save(output_path)
        print(f"Map saved to: {output_path}")

# Usage example
if __name__ == "__main__":
    # Generate Florida map
    florida_map = DisasterMapGenerator('florida', 27.8, -81.5, zoom_start=7)
    florida_map.create_base_map()
    florida_map.add_all_disasters()
    florida_map.add_layer_control()
    florida_map.add_legend()
    florida_map.save_map('../../maps/output/florida_disaster_map.html')
    
    # Generate Orlando map
    orlando_map = DisasterMapGenerator('orlando', 28.5, -81.38, zoom_start=10)
    orlando_map.create_base_map()
    orlando_map.add_all_disasters()
    orlando_map.add_layer_control()
    orlando_map.add_legend()
    orlando_map.save_map('../../maps/output/orlando_disaster_map.html')
