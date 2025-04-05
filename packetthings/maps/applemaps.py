def generate_map_html(latitude, longitude, zoom=10):
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Apple Maps</title>
        <meta name="viewport" content="initial-scale=1.0, user-scalable=no">
        <meta charset="utf-8">
        <style>
            #map {{
                height: 100vh;
            }}
        </style>
    </head>
    <body>
        <div id="map"></div>
        <script src="https://cdn.apple-mapkit.com/mk/5.x.x/mapkit.js"></script>
        <script>
            var map = new mapkit.Map("map", {{
                center: new mapkit.Coordinate({}, {}),
                showsUserLocation: true,
                showsPointsOfInterest: true,
                mapType: mapkit.Map.MapType.Standard,
                zoomEnabled: true,
                showsCompass: true,
                showsZoomControl: true,
                showsMapTypeControl: true,
                zoomLevel: {}
            }});

            var annotation = new mapkit.MarkerAnnotation(new mapkit.Coordinate({}, {}));
            map.addAnnotation(annotation);
        </script>
    </body>
    </html>
    """.format(latitude, longitude, latitude, longitude, zoom)

    return html_template


# Example coordinates for a location in San Francisco
latitude = 14.580789226949928
longitude = 121.05889427785439

# Generate the HTML code for the map
html_code = generate_map_html(latitude, longitude)

print(html_code)

# Write the HTML code to a file
with open("apple_map.html", "w") as file:
    file.write(html_code)

