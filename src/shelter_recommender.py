from shapely.geometry import shape, Point, LineString
from shapely.ops import transform
from src.alert_engine import _to_metres
import random

SPEED_KMH = 20


def recommend_shelter(lat, lon, zones, shelters):
    user = transform(_to_metres, Point(lon, lat))
    polys = [transform(_to_metres, shape(z["geometry"])) for z in zones]

    # --- RULE 0: Check if the user is inside or near a flood zone ---
    user_is_at_risk = False
    for p in polys:
        if p.intersects(user) or p.distance(user) < 200:
            user_is_at_risk = True
            break

    if not user_is_at_risk:
        return {
            "message": "You are in a safe zone. No shelter recommendation is needed at this moment.",
            "recommended": None,
            "alternatives": []
        }

    # --- If user is at risk, find the best shelter ---
    options = []
    for s in shelters:
        free = s["capacity"] - s["occupied"]
        sp = transform(_to_metres, Point(s["lon"], s["lat"]))

        if free <= 0:
            continue  # Rule 1: skip full shelters

        if any(p.intersects(sp) for p in polys):
            continue  # Rule 2: skip shelters inside a flood zone

        line = LineString([user, sp])
        crosses = any(p.intersects(line) for p in polys)  # Does the direct path cross a flood zone?
        dist = user.distance(sp)

        # --- CREATE A MOCK TURN-BY-TURN ROUTE (CURVED PATH) ---
        # We add intermediate points to simulate road curves (like Google Maps)
        # The route goes slightly off the direct line to avoid looking like a straight line
        
        mid1_lat = lat + (s["lat"] - lat) * 0.3 + random.uniform(-0.002, 0.002)
        mid1_lon = lon + (s["lon"] - lon) * 0.3 + random.uniform(-0.002, 0.002)
        
        mid2_lat = lat + (s["lat"] - lat) * 0.6 + random.uniform(-0.002, 0.002)
        mid2_lon = lon + (s["lon"] - lon) * 0.6 + random.uniform(-0.002, 0.002)

        route_coords = [
            [lat, lon],
            [mid1_lat, mid1_lon],
            [mid2_lat, mid2_lon],
            [s["lat"], s["lon"]]
        ]

        options.append({
            "shelter": s,
            "free_places": free,
            "distance_m": round(dist),
            "eta_min": round(dist / 1000 / SPEED_KMH * 60, 1),
            "crosses_flood_zone": crosses,
            "route_coords": route_coords  # Send the curve points to the frontend
        })

    if not options:
        return {
            "message": "You are in a risk zone, but no suitable shelter was found. Contact emergency services immediately.",
            "recommended": None,
            "alternatives": []
        }

    # Sort: avoid crossing flood zones first, then by distance
    options.sort(key=lambda o: (o["crosses_flood_zone"], o["distance_m"]))
    best = options[0]
    note = " The direct path crosses a flood zone, take extra care." if best["crosses_flood_zone"] else ""
    
    return {
        "message": f"Nearest suitable shelter: {best['shelter']['name']} ({best['distance_m']} m).{note}",
        "recommended": best,
        "alternatives": options[1:]
    }