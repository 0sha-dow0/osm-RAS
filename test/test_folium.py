import folium

# Create a simple test map
m = folium.Map(location=[28.5, -81.38], zoom_start=10)
m.save('test_map.html')
print("Test map saved successfully!")
