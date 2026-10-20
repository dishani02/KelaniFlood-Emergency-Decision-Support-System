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


state = {"feed": load_feed()}


class Location(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


@app.get("/api/zones")
def get_zones():
    return state["feed"]


@app.post("/api/feed")  # the other components will POST their output here
def ingest_feed(feed: dict):
    if "zones" not in feed:
        raise HTTPException(status_code=422, detail="feed must contain 'zones'")
    state["feed"] = feed
    return {"status": "ok", "zones": len(feed["zones"])}

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




# In-memory storage for help requests
help_requests = {}

class HelpRequest(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    help_type: str = Field(min_length=3, max_length=50)  # e.g. "Rescue", "Food"
    urgency: str = Field(min_length=3, max_length=20)     # e.g. "High", "Medium", "Low"
    description: str = Field(max_length=200)              # Additional details

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


# Store the latest sensor data
sensor_data = {"water_level_cm": 18.4, "rate_of_rise_cm_hr": 0.2, "rainfall_mm": 12.5}

@app.post("/api/feed")
def ingest_feed(feed: dict):
    if "water_level_cm" in feed:
        sensor_data.update(feed)
        return {"status": "ok", "message": "Sensor data updated"}
    raise HTTPException(status_code=422, detail="Invalid feed format")

@app.get("/api/latest-sensor")
def get_sensor_data():
    return sensor_data

app.mount("/", StaticFiles(directory=BASE / "web", html=True), name="web")