import os

def create_map_with_marker(latitude, longitude, marker_color='blue', marker_size='medium'):
    # Set your Mapbox access token
    # access_token = os.environ.get('MAPBOX_ACCESS_TOKEN')  # You can also directly provide your access token here
    access_token = "sk.eyJ1IjoibWFvaWU4NiIsImEiOiJjbHUweDd6M24wZmlsMmpxc2dpbHU4bmpkIn0.5pRUVhVvh3Y5a-XVcT8gbQ"

    # Construct the Mapbox Static Images API URL
    mapbox_base_url = "https://api.mapbox.com/styles/v1/mapbox/streets-v11/static/"
    marker_coordinates = f"{longitude},{latitude}"
    mapbox_static_image_url = f"{mapbox_base_url}{marker_coordinates},15,0,0/"
    marker_properties = f"url-https%3A%2F%2Fdocs.mapbox.com%2Fmapbox-gl-js%2Fassets%2Fmarker-icon.png({longitude},{latitude})"
    # mapbox_static_image_url += f"{marker_properties}/"

    # Add access token to the URL
    mapbox_static_image_url += f"?access_token={access_token}"

    return mapbox_static_image_url


latitude = 14.580581561052316
longitude = 121.05885136304306

# Create the map with a marker
map_url = create_map_with_marker(latitude, longitude)

print("Map URL:", map_url)


