import json
from pathlib import Path
from src.alert_engine import evaluate_alert

FEED = Path(__file__).resolve().parent.parent / "data" / "flood_risk_zones.json"
ZONES = json.loads(FEED.read_text(encoding="utf-8"))["zones"]


def test_inside_high_zone_is_critical():
    # Point inside the new KLN-DS-01 zone (79.89 to 79.92, 6.91 to 6.935)
    r = evaluate_alert(6.92, 79.90, ZONES)
    assert r["status"] == "INSIDE" and r["severity"] == "CRITICAL"


def test_inside_medium_zone_is_warning():
    # Point inside the new KLN-DS-02 zone (79.91 to 79.94, 6.95 to 6.975)
    r = evaluate_alert(6.96, 79.92, ZONES)
    assert r["status"] == "INSIDE" and r["severity"] == "WARNING"


def test_near_high_zone_is_warning():
    # Point just outside the east edge of KLN-DS-01 (x=79.92). 79.925 is ~500m east.
    r = evaluate_alert(6.92, 79.925, ZONES)
    assert r["status"] == "NEAR" and r["severity"] == "WARNING"
    assert 400 < r["distance_m"] < 600


def test_far_away_is_safe():
    # Point far away (e.g., Galle area)
    r = evaluate_alert(6.03, 80.22, ZONES)
    assert r["severity"] == "SAFE"


def test_no_zones_is_safe():
    assert evaluate_alert(6.9, 79.9, [])["severity"] == "SAFE"