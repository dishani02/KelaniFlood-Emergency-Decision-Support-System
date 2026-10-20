import json
from pathlib import Path
from src.shelter_recommender import recommend_shelter

D = Path(__file__).resolve().parent.parent / "data"
ZONES = json.loads((D / "flood_risk_zones.json").read_text(encoding="utf-8"))["zones"]
SHELTERS = json.loads((D / "shelter_locations.json").read_text(encoding="utf-8"))


def test_full_shelter_is_skipped():
    # S2 is full (occupied = capacity)
    r = recommend_shelter(6.92, 79.90, ZONES, SHELTERS)
    ids = [r["recommended"]["shelter"]["id"]] + [a["shelter"]["id"] for a in r["alternatives"]]
    assert "S2" not in ids


def test_recommended_is_valid_and_has_distance():
    r = recommend_shelter(6.92, 79.90, ZONES, SHELTERS)
    assert r["recommended"] is not None
    assert r["recommended"]["distance_m"] > 0


def test_no_shelters_gives_safe_message():
    r = recommend_shelter(6.92, 79.90, ZONES, [])
    assert r["recommended"] is None


def test_crosses_flood_zone_field_exists():
    r = recommend_shelter(6.92, 79.90, ZONES, SHELTERS)
    assert "crosses_flood_zone" in r["recommended"]
    assert isinstance(r["recommended"]["crosses_flood_zone"], bool)