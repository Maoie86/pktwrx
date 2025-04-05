import folium
from geopy.distance import distance

marco = [14.587668055267226, 121.06328237179237]
pktwrx = [14.585643365857278, 121.06352913489893]
richmonde = [14.580052011476228, 121.05901229499412]

m = folium.Map(location=[14.58007111929988, 121.05904209811348], zoom_start=12)

folium.Marker(location=marco, popup="<h1>Marco Polo</h1>", tooltip="Marco ---- Polo").add_to(m)
folium.Marker(location=pktwrx, popup="<h1>PacketWorx --- hello Mu</h1>", tooltip="iSquare").add_to(m)
folium.Marker(location=richmonde, popup="<h1>Richmonde --- hello SFIi</h1>", tooltip="iSquare").add_to(m)

m.save("richmonde.html")

km = distance(pktwrx, richmonde)
miles = distance(pktwrx, richmonde).miles

print("Distance between pktwrx and richmonde:")
print(f"{km}")
print(f"{miles} miles")



