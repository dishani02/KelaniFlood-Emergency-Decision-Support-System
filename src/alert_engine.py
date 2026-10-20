from shapely.geometry import shape, Point
from shapely.ops import transform
from pyproj import Transformer

# lat/lon (EPSG:4326) -> metres (UTM zone 44N, covers Colombo)
_to_metres = Transformer.from_crs("EPSG:4326", "EPSG:32644", always_xy=True).transform

# distance (m) from a zone that still counts as "NEAR", depending on the zone's risk
NEAR_DISTANCE_M = {"LOW": 200, "MEDIUM": 500, "HIGH": 1000}

# (status, zone risk) -> alert severity
SEVERITY = {
    ("INSIDE", "HIGH"): "CRITICAL",
    ("INSIDE", "MEDIUM"): "WARNING",
    ("INSIDE", "LOW"): "ADVISORY",
    ("NEAR", "HIGH"): "WARNING",
    ("NEAR", "MEDIUM"): "ADVISORY",
    ("NEAR", "LOW"): "INFO",
}
SEVERITY_RANK = {"CRITICAL": 4, "WARNING": 3, "ADVISORY": 2, "INFO": 1, "SAFE": 0}


def _message(status, zone, dist):
    name, risk = zone["name"], zone["risk_level"]
    if status == "INSIDE":
        return f"You are inside {name} ({risk} flood risk). Move to a shelter now."
    return f"You are {round(dist)} m from {name} ({risk} flood risk). Stay alert and prepare to move."


def evaluate_alert(lat, lon, zones):
    user = transform(_to_metres, Point(lon, lat))  # NOTE: lon first, then lat
    best = None
    nearest_zone, nearest_dist = None, None

    for z in zones:
        poly = transform(_to_metres, shape(z["geometry"]))
        dist = 0.0 if poly.intersects(user) else poly.distance(user)
        risk = z["risk_level"]

        if nearest_dist is None or dist < nearest_dist:
            nearest_zone, nearest_dist = z, dist

        if dist == 0.0:
            status = "INSIDE"
        elif dist <= NEAR_DISTANCE_M[risk]:
            status = "NEAR"
        else:
            continue

        severity = SEVERITY[(status, risk)]
        if best is None or SEVERITY_RANK[severity] > SEVERITY_RANK[best["severity"]]:
            best = {
                "severity": severity,
                "status": status,
                "zone_id": z["zone_id"],
                "zone_name": z["name"],
                "risk_level": risk,
                "distance_m": round(dist),
                "confidence": z.get("confidence"),
                "message": _message(status, z, dist),
            }

    if best:
        return best
    if nearest_zone is None:
        return {"severity": "SAFE", "status": "OUTSIDE", "distance_m": None,
                "message": "No flood-risk zones are currently reported."}
    return {
        "severity": "SAFE", "status": "OUTSIDE",
        "zone_id": nearest_zone["zone_id"], "distance_m": round(nearest_dist),
        "message": f"You are outside all flood-risk zones. Nearest: {nearest_zone['name']}, {round(nearest_dist)} m away.",
    }