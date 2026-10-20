from shapely.geometry import shape, Point, LineString
from shapely.ops import transform
from src.alert_engine import _to_metres

SPEED_KMH = 20  # assumed speed during floods; straight-line distance only


def recommend_shelter(lat, lon, zones, shelters):
    user = transform(_to_metres, Point(lon, lat))
    polys = [transform(_to_metres, shape(z["geometry"])) for z in zones]

    # Rule 0: Check if the user is safe
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

    options = []
    for s in shelters:
        free = s["capacity"] - s["occupied"]
        sp = transform(_to_metres, Point(s["lon"], s["lat"]))

        if free <= 0:
            continue

        if any(p.intersects(sp) for p in polys):
            continue

        line = LineString([user, sp])
        crosses = any(p.intersects(line) for p in polys)
        dist = user.distance(sp)

        options.append({
            "shelter": s,
            "free_places": free,
            "distance_m": round(dist),
            "eta_min": round(dist / 1000 / SPEED_KMH * 60, 1),
            "crosses_flood_zone": crosses
        })

    if not options:
        return {
            "message": "You are in a risk zone, but no suitable shelter was found. Contact emergency services immediately.",
            "recommended": None,
            "alternatives": []
        }

    options.sort(key=lambda o: (o["crosses_flood_zone"], o["distance_m"]))
    best = options[0]
    note = " The direct path crosses a flood zone, take extra care." if best["crosses_flood_zone"] else ""
    
    return {
        "message": f"Nearest suitable shelter: {best['shelter']['name']} ({best['distance_m']} m).{note}",
        "recommended": best,
        "alternatives": options[1:]
    }