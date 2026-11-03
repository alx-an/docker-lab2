from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
import os
import httpx

from app.database import engine, get_db
from app.models import Base
from app import crud

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Personal Assist")

OWNER = os.getenv("APP_OWNER", "anonymous")
SECRET_KEY = os.getenv("APP_SECRET", "default_secret")


class NoteCreate(BaseModel):
    text: str


@app.get("/")
async def root():
    return {
        "message": f"👋 Привет, {OWNER}!",
        "service": "personal-assistant",
        "version": "2.0",
        "endpoints": ["/me", "/notes", "/weather/{city}", "/secret/{key}"],
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "owner": OWNER}


@app.get("/me")
async def me():
    return {
        "owner": OWNER,
        "secret_prefix": SECRET_KEY[:6]
        if SECRET_KEY != "default_secret"
        else "NOT_SET",
    }


@app.get("/secret/{key}")
async def secret(key: str):
    if key == SECRET_KEY:
        return {
            "flag": f"LAB2_SUCCESS_{OWNER.upper()}",
            "message": "The secret key is correct!",
        }
    return {
        "error": "The secret key is incorrect",
        "hint": "Check the APP_SECRET environment variable",
    }


WEATHER_CODES: dict[int, str] = {
    0: "☀️ Ясно", 1: "🌤 Малооблачно", 2: "⛅ Переменная облачность",
    3: "☁️ Пасмурно", 45: "🌫 Туман", 48: "🌫 Изморозь",
    51: "🌦 Лёгкая морось", 53: "🌦 Морось", 55: "🌧 Сильная морось",
    61: "🌧 Небольшой дождь", 63: "🌧 Дождь", 65: "🌧 Сильный дождь",
    71: "🌨 Небольшой снег", 73: "🌨 Снег", 75: "❄️ Сильный снег",
    80: "🌦 Ливень", 81: "🌧 Сильный ливень", 82: "⛈ Штормовой ливень",
    95: "⛈ Гроза", 96: "⛈ Гроза с градом", 99: "⛈ Сильная гроза с градом",
}


@app.get("/weather/{city}")
async def weather(city: str):
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            geo_resp = await client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": city, "count": 1, "language": "ru"},
            )
            geo_data = geo_resp.json()

            if not geo_data.get("results"):
                return {"error": f"City «{city}» not found"}

            location = geo_data["results"][0]
            lat = location["latitude"]
            lon = location["longitude"]
            city_name = location.get("name", city)
            country = location.get("country", "")

            weather_resp = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
                },
            )
            weather_data = weather_resp.json()["current"]

            code = weather_data.get("weather_code", -1)

            return {
                "city": city_name,
                "country": country,
                "coordinates": {"lat": lat, "lon": lon},
                "temperature_c": weather_data["temperature_2m"],
                "humidity_pct": weather_data["relative_humidity_2m"],
                "wind_km_h": weather_data["wind_speed_10m"],
                "condition": WEATHER_CODES.get(code, f"Code {code}"),
            }
    except Exception as e:
        return {"error": f"Failed to get weather: {type(e).__name__}: {e}"}


@app.post("/notes")
async def create_note(note: NoteCreate, db: Session = Depends(get_db)):
    db_note = crud.create_note(db=db, text=note.text, owner=OWNER)
    return {
        "status": "saved",
        "note_id": db_note.id,
        "owner": db_note.owner,
        "text": db_note.text[:50],
    }


@app.get("/notes")
async def list_notes(db: Session = Depends(get_db)):
    db_notes = crud.get_notes(db=db, owner=OWNER)
    return {
        "owner": OWNER,
        "count": len(db_notes),
        "notes": [
            {
                "id": n.id,
                "text": n.text,
                "owner": n.owner,
                "created_at": n.created_at.isoformat(),
            }
            for n in db_notes
        ],
    }


@app.get("/notes/{note_id}")
async def get_note(note_id: int, db: Session = Depends(get_db)):
    note = crud.get_note_by_id(db=db, note_id=note_id)
    if not note:
        return {"error": f"Note {note_id} not found"}
    return {
        "id": note.id,
        "text": note.text,
        "owner": note.owner,
        "created_at": note.created_at.isoformat(),
    }


@app.delete("/notes/{note_id}")
async def delete_note(note_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_note(db=db, note_id=note_id)
    if not deleted:
        return {"error": f"Note {note_id} not found"}
    return {"status": "deleted", "note_id": note_id}
