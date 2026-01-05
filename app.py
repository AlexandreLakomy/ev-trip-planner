#app.py

from flask import Flask, render_template, request, jsonify, Response, request
from flask_cors import CORS
import requests
import folium
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import os
from dotenv import load_dotenv
from soap_service import soap_wsgi_app


load_dotenv()

app = Flask(__name__)
CORS(app)

ORS_BASE_URL = "https://api.openrouteservice.org"
ORS_API_KEY = os.getenv("ORS_API_KEY")
if not ORS_API_KEY:
    raise RuntimeError("ORS_API_KEY manquante")
CHARGETRIP_CLIENT_ID = os.getenv("CHARGETRIP_CLIENT_ID")
if not CHARGETRIP_CLIENT_ID:
    raise RuntimeError("CHARGETRIP_CLIENT_ID manquante")
CHARGETRIP_APP_ID = os.getenv("CHARGETRIP_APP_ID")
if not CHARGETRIP_APP_ID:
    raise RuntimeError("CHARGETRIP_APP_ID manquante")

# 🔋 MARGE DE SÉCURITÉ : on ne descend pas en dessous de 10% de batterie
BATTERY_SAFETY_MARGIN = 0.10  # 10% de réserve minimale


@app.route("/soap", methods=["GET", "POST"])
def soap():
    response = soap_wsgi_app(request.environ, lambda *args: None)
    return Response(response, content_type="text/xml")


# ---------------------------------------------------------
# 🔥 Utilité de formatage de temps
# ---------------------------------------------------------
def format_time_h_min(time_h):
    """Convertit un temps en heures décimales (float) en chaîne 'Xh Ymin'."""
    # Convertir en minutes, arrondir à l'entier le plus proche pour gérer les flottants
    total_minutes = int(round(time_h * 60))
    
    hours = total_minutes // 60
    minutes = total_minutes % 60
    
    # Gérer le cas où le temps est très court (par exemple, 0h 5min)
    if hours == 0:
        return f"{minutes}min"
        
    return f"{hours}h {minutes}min"

def ors_geocode(city_name):
    """Géocoder une ville via ORS"""
    try:
        url = f"{ORS_BASE_URL}/geocode/search"
        params = {
            "api_key": ORS_API_KEY,
            "text": city_name + ", France",
            "size": 1
        }

        r = requests.get(url, params=params)
        data = r.json()

        features = data.get("features", [])
        if not features:
            return None

        lon, lat = features[0]["geometry"]["coordinates"]
        return (lat, lon)

    except Exception as e:
        print("Erreur géocodage ORS:", e)
        return None


@app.route('/api/geocode')
def api_geocode():
    query = request.args.get("q")
    if not query or len(query) < 2:
        return jsonify([])

    try:
        url = f"{ORS_BASE_URL}/geocode/autocomplete"
        params = {
            "api_key": ORS_API_KEY,
            "text": query,
            "boundary.country": "FR",
            "size": 100,
            "layers": "locality"
        }

        r = requests.get(url, params=params, timeout=5)
        features = r.json().get("features", [])

        results = []
        seen_cities = set()
        q_lower = query.lower()

        for f in features:
            # Arrêter dès qu'on a 5 résultats
            if len(results) >= 5:
                break
                
            props = f.get("properties", {})
            
            city = props.get("locality") or props.get("name")
            if not city:
                continue

            # Nettoyer
            city = " ".join(city.split()).strip()
            
            # Filtrer : doit commencer par la requête
            if not city.lower().startswith(q_lower):
                continue

            # Déduplication stricte
            city_key = city.lower()
            if city_key in seen_cities:
                continue
            seen_cities.add(city_key)

            # Infos pour le label
            department = props.get("county", "")
            region = props.get("region", "")
            
            label_parts = [city]
            if department:
                label_parts.append(department)
            elif region:
                label_parts.append(region)
            
            label = ", ".join(label_parts)

            results.append({
                "label": label,
                "city": city,
                "lat": f["geometry"]["coordinates"][1],
                "lon": f["geometry"]["coordinates"][0]
            })

        # Sécurité : couper à 5 maximum
        return jsonify(results[:5])

    except Exception as e:
        print("Erreur geocode:", e)
        return jsonify([])


def ors_route(coordinates):
    """
    Route via ORS avec plusieurs waypoints
    coordinates: liste de tuples [(lat, lon), ...]
    """
    try:
        url = f"{ORS_BASE_URL}/v2/directions/driving-car/geojson"

        # Convertir en format [lon, lat] pour ORS
        coords_ors = [[coord[1], coord[0]] for coord in coordinates]

        body = {
            "coordinates": coords_ors,
            "radiuses": [500] * len(coords_ors)  # 🔥 snap sur la route
        }

        headers = {
            "Authorization": ORS_API_KEY,
            "Content-Type": "application/json"
        }

        r = requests.post(url, json=body, headers=headers)
        data = r.json()

        coords = data["features"][0]["geometry"]["coordinates"]
        route = [(c[1], c[0]) for c in coords]

        distance_km = data["features"][0]["properties"]["summary"]["distance"] / 1000
        duration_h = data["features"][0]["properties"]["summary"]["duration"] / 3600

        return {
            "coords": route,
            "distance_km": distance_km,
            "duration_h": duration_h
        }

    except Exception as e:
        print("Erreur ORS route:", e)
        if 'r' in locals():
            print("Réponse brute ORS:", r.text)
        return None


# ---------------------------------------------------------
# 🔥 CONFIG Chargetrip (API véhicules)
# ---------------------------------------------------------

VEHICLES_QUERY = """
query vehicleList {
  vehicleList(page: 0, size: 50) {
    id
    naming {
      make
      model
      version
    }
    battery {
      usable_kwh
      full_kwh
    }
    range {
      chargetrip_range {
        best
        worst
      }
    }
  }
}
"""


def get_vehicles_from_chargetrip():
    """Récupérer les véhicules via Chargetrip"""
    try:
        url = "https://api.chargetrip.io/graphql"
        headers = {
            "x-client-id": CHARGETRIP_CLIENT_ID,
            "x-app-id": CHARGETRIP_APP_ID,
            "Content-Type": "application/json"
        }

        response = requests.post(url, headers=headers, json={"query": VEHICLES_QUERY})

        if response.status_code == 200:
            data = response.json().get("data", {}).get("vehicleList", [])
            vehicles = []

            for v in data:
                try:
                    vehicles.append({
                        "id": v["id"],
                        "make": v["naming"]["make"],
                        "model": v["naming"]["model"],
                        "version": v["naming"]["version"],
                        "range": v["range"]["chargetrip_range"]["best"] or 300,
                        "battery": v["battery"]["usable_kwh"] or 50
                    })
                except:
                    continue

            return vehicles

        print("Erreur Chargetrip:", response.text)
        return get_fallback_vehicles()

    except Exception as e:
        print("Erreur Chargetrip:", e)
        return get_fallback_vehicles()


def get_fallback_vehicles():
    """Véhicules par défaut"""
    return [
        {'id': '1', 'make': 'Tesla', 'model': 'Model 3', 'version': 'Long Range', 'range': 580, 'battery': 75},
        {'id': '2', 'make': 'Tesla', 'model': 'Model Y', 'version': 'Long Range', 'range': 533, 'battery': 75},
        {'id': '3', 'make': 'Renault', 'model': 'Zoe', 'version': 'R135', 'range': 395, 'battery': 52},
    ]


# ---------------------------------------------------------
# 🔥 Géocodage fallback si ORS ne répond pas
# ---------------------------------------------------------
def geocode_city(city_name):
    """Fallback Nominatim"""
    try:
        geo = Nominatim(user_agent="ev_planner")
        loc = geo.geocode(city_name + ", France")
        if loc:
            return (loc.latitude, loc.longitude)
        return None
    except:
        return None


# ---------------------------------------------------------
# 🔥 Bornes IRVE (rayon augmenté à 50 km)
# ---------------------------------------------------------
def get_charging_stations(lat, lon, radius=50):
    print(f"🔍 Recherche bornes autour de {lat}, {lon} (rayon {radius}km)...")

    try:
        url = "https://opendata.reseaux-energies.fr/api/explore/v2.1/catalog/datasets/bornes-irve/records"

        where_clause = f"distance(geo_point_borne, geom'POINT({lon} {lat})', {radius}km)"

        params = {
            "where": where_clause,
            "limit": 10  # on en prend plusieurs, on triera ensuite
        }

        r = requests.get(url, params=params, timeout=10)

        if r.status_code != 200:
            print(f"❌ Erreur API ({r.status_code}): {r.text}")
            return []

        data = r.json().get("results", [])
        print(f"✅ API a répondu : {len(data)} stations trouvées brute")

        stations = []
        for s in data:
            geo = s.get("geo_point_borne")
            if geo and "lat" in geo and "lon" in geo:
                dist = geodesic((lat, lon), (geo["lat"], geo["lon"])).km

                stations.append({
                    "name": s.get("n_enseigne") or s.get("n_operateur") or "Borne inconnue",
                    "address": s.get("ad_station") or "Adresse inconnue",
                    "lat": geo["lat"],
                    "lon": geo["lon"],
                    "distance": dist,
                    "power": f"{s.get('puiss_max', 'N/A')} kW",
                    "found": True
                })

        # 🔥 TRI CÔTÉ PYTHON (borne la plus proche en premier)
        stations.sort(key=lambda x: x["distance"])

        print(f"   -> {len(stations)} stations valides après tri")
        return stations

    except Exception as e:
        print(f"❌ Exception critique get_charging_stations: {e}")
        return []

# ---------------------------------------------------------
# 🔥 Calcul avec MARGE DE SÉCURITÉ (10% de batterie restante)
# ---------------------------------------------------------
def calculate_trip_with_stops_and_route(start_coords, end_coords, vehicle_range, charging_time=30):
    """
    Calcule le trajet avec arrêts de recharge ET route réelle
    🔋 NOUVEAU : Marge de sécurité de 10% (on ne descend pas sous 10% de batterie)
    """
    # 1. Calculer une route initiale pour avoir la distance
    initial_route = ors_route([start_coords, end_coords])
    
    if not initial_route:
        # Fallback géodésique
        total_distance = geodesic(start_coords, end_coords).kilometers
    else:
        total_distance = initial_route["distance_km"]

    # 2. 🔋 Autonomie utilisable avec marge de sécurité
    # On garde 10% de réserve au minimum
    usable_range = vehicle_range * (1 - BATTERY_SAFETY_MARGIN)
    
    print(f"🔋 Autonomie véhicule: {vehicle_range} km")
    print(f"🔋 Autonomie utilisable (avec 10% de marge): {usable_range:.1f} km")
    
    # 3. Calculer le nombre d'arrêts nécessaires
    num_stops = max(0, int(total_distance / usable_range))
    
    print(f"📏 Distance totale: {total_distance:.1f} km")
    print(f"⚡ Nombre d'arrêts nécessaires: {num_stops}")

    # 4. Trouver les bornes de recharge sur le trajet
    stops = []
    waypoints = [start_coords]
    
    if num_stops > 0:
        for i in range(1, num_stops + 1):
            # Position interpolée sur le trajet initial
            ratio = i / (num_stops + 1)
            
            if initial_route and initial_route["coords"]:
                # Trouver le point sur la route réelle
                route_length = len(initial_route["coords"])
                index = int(route_length * ratio)
                stop_lat, stop_lon = initial_route["coords"][index]
            else:
                # Fallback interpolation linéaire
                stop_lat = start_coords[0] + (end_coords[0] - start_coords[0]) * ratio
                stop_lon = start_coords[1] + (end_coords[1] - start_coords[1]) * ratio

            # 🔍 Chercher une borne proche (rayon 50 km)
            print(f"🔍 Recherche borne {i} autour de ({stop_lat:.4f}, {stop_lon:.4f})")
            stations = get_charging_stations(stop_lat, stop_lon, radius=50)
            
            print(f"   → {len(stations)} bornes trouvées")

            if stations:
                chosen = stations[0]
                stop_coords = (chosen["lat"], chosen["lon"])
                
                stops.append({
                    "stop_number": i,
                    "lat": chosen["lat"],
                    "lon": chosen["lon"],
                    "name": chosen["name"],
                    "address": chosen["address"],
                    "city": chosen.get("city", ""),
                    "power": chosen["power"],
                    "charging_time": charging_time,
                    "found": True
                })
                print(f"   ✅ Borne trouvée: {chosen['name']} à {chosen.get('city', 'ville inconnue')}")
            else:
                stop_coords = (stop_lat, stop_lon)
                stops.append({
                    "stop_number": i,
                    "lat": stop_lat,
                    "lon": stop_lon,
                    "name": f"Zone de recharge {i}",
                    "address": "⚠️ Aucune borne trouvée dans un rayon de 50 km",
                    "city": "",
                    "power": "N/A",
                    "charging_time": charging_time,
                    "found": False
                })
                print(f"   ⚠️ Aucune borne trouvée dans un rayon de 50 km")
            
            waypoints.append(stop_coords)
    
    waypoints.append(end_coords)

    # 5. Calculer la route FINALE qui passe par toutes les bornes
    final_route = ors_route(waypoints)

    if final_route:
        total_distance = final_route["distance_km"]
        driving_time = final_route["duration_h"]
        route_coords = final_route["coords"]
    else:
        # Fallback
        driving_time = total_distance / 90
        route_coords = None

    charging_total = num_stops * (charging_time / 60)

    return {
        "total_distance": round(total_distance, 2),
        "num_stops": num_stops,
        "stops": stops,
        "driving_time": round(driving_time, 2),
        "charging_time": round(charging_total, 2),
        "total_time": round(driving_time + charging_total, 2),
        "route_coords": route_coords,
        "usable_range": round(usable_range, 1),
        "safety_margin_km": round(vehicle_range * BATTERY_SAFETY_MARGIN, 1)
    }

# ---------------------------------------------------------
# 🔥 Carte Folium
# ---------------------------------------------------------
def create_map(start_coords, end_coords, stops, start_city, end_city, route_coords):
    center_lat = (start_coords[0] + end_coords[0]) / 2
    center_lon = (start_coords[1] + end_coords[1]) / 2

    m = folium.Map(location=[center_lat, center_lon], zoom_start=8)

    # Départ
    folium.Marker(start_coords,
                  popup=f"<b>Départ</b><br>{start_city}",
                  icon=folium.Icon(color="green", icon="play")).add_to(m)

    # Arrivée
    folium.Marker(end_coords,
                  popup=f"<b>Arrivée</b><br>{end_city}",
                  icon=folium.Icon(color="red", icon="stop")).add_to(m)

    # Arrêts de recharge
    for stop in stops:
        # Couleur différente si borne non trouvée
        icon_color = "blue" if stop.get("found", True) else "orange"
        
        popup_text = f"<b>Arrêt {stop['stop_number']}</b><br>{stop['name']}<br>{stop['address']}"
        if stop.get("city"):
            popup_text += f"<br>📍 {stop['city']}"
        popup_text += f"<br>⚡ {stop['power']}<br>⏱️ {stop['charging_time']} min"
        
        folium.Marker(
            [stop["lat"], stop["lon"]],
            popup=popup_text,
            icon=folium.Icon(color=icon_color, icon="bolt")
        ).add_to(m)

    # Route complète (qui passe par les bornes)
    if route_coords:
        folium.PolyLine(route_coords, color="blue", weight=4, opacity=0.8).add_to(m)

    return m._repr_html_()


# =========================================================
#                       ROUTES
# =========================================================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/vehicles')
def api_vehicles():
    vehicles = get_vehicles_from_chargetrip()
    return jsonify({"success": True, "vehicles": vehicles})


@app.route('/plan', methods=['POST'])
def plan_trip():
    try:
        vehicle_id = request.form.get("vehicle")
        start_city = request.form.get("start_city")
        end_city = request.form.get("end_city")

        vehicles = get_vehicles_from_chargetrip()
        vehicle = next((v for v in vehicles if v["id"] == vehicle_id), None)

        if not vehicle:
            return jsonify({"error": "Véhicule introuvable"}), 400

        coords_start = ors_geocode(start_city) or geocode_city(start_city)
        coords_end = ors_geocode(end_city) or geocode_city(end_city)

        if not coords_start or not coords_end:
            return jsonify({"error": "Impossible de géocoder les villes"}), 400

        # 🔥 Calcul avec route adaptée aux bornes + marge de sécurité
        trip = calculate_trip_with_stops_and_route(
            coords_start,
            coords_end,
            vehicle["range"]
        )

        # Carte avec la route complète
        map_html = create_map(
            coords_start, coords_end, trip["stops"],
            start_city, end_city,
            trip["route_coords"]
        )

        return jsonify({
            "success": True, 
            "trip": trip, 
            "map": map_html,
            "vehicle": vehicle
        })

    except Exception as e:
        print("Erreur globale:", e)
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("🚗 Serveur lancé sur http://0.0.0.0:5000")
    print(f"🔋 Marge de sécurité batterie: {BATTERY_SAFETY_MARGIN * 100}%")
    app.run(host="0.0.0.0", port=5000, debug=True)