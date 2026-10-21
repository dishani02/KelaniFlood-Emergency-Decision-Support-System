import json
from src.shelter_recommender import recommend_shelter
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from src.alert_engine import evaluate_alert
import uuid
from datetime import datetime

BASE = Path(__file__).resolve().parent.parent
app = FastAPI(title="Emergency Decision Support API (IT23367258)")


def load_feed():
    return json.loads((BASE / "data" / "flood_risk_zones.json").read_text(encoding="utf-8"))


# පද්ධතියේ වත්මන් තත්වය තබා ගන්නා state එක
state = {
    "feed": load_feed(),
    # Hewapaulage ගේ component එකෙන් එන අලුත්ම sensor දත්ත මෙහි ගබඩා වේ
    "sensor_data": {
        "station_id": "S01",
        "station_name": "Kelaniya", # මේක අපි පසුව station ID එකට අනුව map කරගමු
        "water_level_cm": 17.8,
        "rain_status": "WET",
        "timestamp": datetime.now().isoformat(),
        "reservoir": {"name": "Norton Bridge", "status": "NORMAL"} # C4 එකෙන් එනකම් dummy data
    }
}


class Location(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


# ===================================================================
# ZONES (C3 - Soysa ගේ component එකෙන් එන flood zones)
# ===================================================================
@app.get("/api/zones")
def get_zones():
    return state["feed"]


@app.post("/api/feed")
def ingest_zones_feed(feed: dict):
    """Flood risk zones update කිරීමට (C3 වෙතින්)"""
    if "zones" not in feed:
        raise HTTPException(status_code=422, detail="feed must contain 'zones'")
    state["feed"] = feed
    return {"status": "ok", "zones": len(feed["zones"])}


# ===================================================================
# SENSOR DATA (C1 - Hewapaulage ගේ component එකෙන් එන දත්ත)
# ===================================================================
@app.post("/api/sensor")
def ingest_sensor_data(payload: dict):
    """
    Hewapaulage ගේ IoT sensor data එක ලබා ගන්නා endpoint එක.
    ඔහුගේ payload එකේ තියෙන දේවල් (water_level_cm, rain_status, etc.) මෙතනට එවිය යුතුයි.
    """
    # අවශ්‍ය දත්ත තියෙනවද පරීක්ෂා කිරීම
    if "water_level_cm" not in payload:
        raise HTTPException(status_code=422, detail="Payload must contain 'water_level_cm'")

    # දත්ත update කිරීම
    state["sensor_data"].update({
        "station_id": payload.get("station_id", state["sensor_data"]["station_id"]),
        "water_level_cm": payload["water_level_cm"],
        "rain_status": payload.get("rain_status", "DRY").upper(),
        "timestamp": datetime.now().isoformat()
    })
    
    return {"status": "ok", "message": "Sensor data updated successfully"}


@app.get("/api/sensor")
def get_latest_sensor_data():
    """
    Frontend (index.html) එකට අලුත්ම sensor දත්ත ලබා දෙන endpoint එක.
    """
    return state["sensor_data"]


# ===================================================================
# SHELTERS & ALERTS
# ===================================================================
@app.get("/api/shelters")
def get_all_shelters():
    shelters = json.loads((BASE / "data" / "shelter_locations.json").read_text(encoding="utf-8"))
    return shelters


@app.post("/api/alert")
def alert(loc: Location):
    return evaluate_alert(loc.lat, loc.lon, state["feed"]["zones"])


@app.post("/api/shelter")
def shelter(loc: Location):
    shelters = json.loads((BASE / "data" / "shelter_locations.json").read_text(encoding="utf-8"))
    return recommend_shelter(loc.lat, loc.lon, state["feed"]["zones"], shelters)


# ===================================================================
# HELP REQUESTS
# ===================================================================
help_requests = {}


class HelpRequest(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    help_type: str = Field(min_length=3, max_length=50)
    urgency: str = Field(min_length=3, max_length=20)
    description: str = Field(max_length=200)


@app.post("/api/help")
def create_help(req: HelpRequest):
    rid = str(uuid.uuid4())[:8]
    help_requests[rid] = {
        "id": rid,
        "status": "OPEN",
        "accepted_by": None,
        "timestamp": datetime.now().isoformat(),
        **req.model_dump()
    }
    return help_requests[rid]


@app.get("/api/help")
def list_help():
    return list(help_requests.values())


@app.post("/api/help/{rid}/accept")
def accept_help(rid: str, responder: str):
    if rid not in help_requests:
        raise HTTPException(status_code=404, detail="request not found")
    help_requests[rid].update(status="ACCEPTED", accepted_by=responder)
    return help_requests[rid]


# Web folder එක mount කිරීම (index.html පෙන්නන්න)
app.mount("/", StaticFiles(directory=BASE / "web", html=True), name="web")