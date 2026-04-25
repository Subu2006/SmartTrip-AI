from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import mimetypes
import os
import secrets
import sqlite3
import tempfile
import traceback
import urllib.error
import urllib.parse
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TEMPLATE_DIR = ROOT / "templates"
STATIC_DIR = ROOT / "static"
DATA_DIR = ROOT / "data"
RUNTIME_DIR = Path(tempfile.gettempdir()) / "SmartTripAI"
DB_PATH = RUNTIME_DIR / "smarttrip.sqlite3"
LOG_PATH = RUNTIME_DIR / "server.log"
HOST = "127.0.0.1"
PORT = 8000


DATA_DIR.mkdir(parents=True, exist_ok=True)
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


FALLBACK_RATES = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "INR": 83.20,
    "JPY": 149.50,
    "AUD": 1.53,
    "CAD": 1.36,
    "CHF": 0.90,
    "SGD": 1.34,
    "THB": 35.10,
}


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def today_iso() -> str:
    return dt.date.today().isoformat()


def iso_after(days: int) -> str:
    return (dt.date.today() + dt.timedelta(days=days)).isoformat()


DESTINATIONS = [
    {
        "slug": "kyoto-japan",
        "name": "Kyoto, Japan",
        "country": "Japan",
        "coords": {"lat": 35.0116, "lng": 135.7681},
        "season": "March-May and October-November",
        "cost_index": 1.18,
        "summary": "Kyoto balances serene temples, tea houses, sakura-season beauty, and refined culinary culture.",
        "tags": ["peaceful", "cultural", "romantic", "spiritual", "nature", "foodie"],
        "stay_area": "Gion and Higashiyama",
        "travel_tips": [
            "Reserve tea ceremonies and premium kaiseki meals at least a week ahead.",
            "Start temple visits early to avoid tour-bus crowds by 10 AM.",
            "Buy an IC transit card for smooth bus and rail transfers across the city.",
            "Carry cash for smaller shrines, markets, and neighborhood eateries.",
            "Respect quiet zones and photo rules in temple compounds.",
        ],
        "foods": ["kaiseki tasting", "matcha desserts", "yudofu", "izakaya small plates"],
        "hotels": [
            {"name": "Gion Heritage Suites", "price": 340, "rating": 4.8, "location": "Gion"},
            {"name": "Kyoto Central Garden Hotel", "price": 220, "rating": 4.5, "location": "Downtown Kyoto"},
            {"name": "Sakura Budget Stay", "price": 110, "rating": 4.1, "location": "Near Kyoto Station"},
        ],
        "flights": [
            {"name": "Premium Kansai Non-Stop", "price": 980, "type": "Non-stop", "duration": "8h 20m", "airline": "ANA"},
            {"name": "Value Saver via Tokyo", "price": 640, "type": "1 stop", "duration": "11h 45m", "airline": "JAL Connect"},
        ],
        "activities": [
            {"name": "Fushimi Inari sunrise walk", "price": 30, "duration": "3h", "category": "Culture", "description": "Early-morning torii gate trail with guide"},
            {"name": "Arashiyama bamboo district tour", "price": 45, "duration": "4h", "category": "Nature", "description": "Bamboo grove, riverfront, and artisan stops"},
            {"name": "Tea ceremony and wagashi class", "price": 58, "duration": "2h", "category": "Food", "description": "Hands-on local tea experience"},
        ],
        "nearby_places": [
            {"name": "Fushimi Inari Shrine", "lat": 34.9671, "lng": 135.7727, "kind": "Shrine"},
            {"name": "Kiyomizu-dera", "lat": 34.9948, "lng": 135.7850, "kind": "Temple"},
            {"name": "Arashiyama Bamboo Grove", "lat": 35.0170, "lng": 135.6713, "kind": "Nature"},
            {"name": "Nishiki Market", "lat": 35.0051, "lng": 135.7645, "kind": "Food"},
            {"name": "Philosopher's Path", "lat": 35.0269, "lng": 135.7955, "kind": "Walk"},
        ],
    },
    {
        "slug": "bali-indonesia",
        "name": "Bali, Indonesia",
        "country": "Indonesia",
        "coords": {"lat": -8.4095, "lng": 115.1889},
        "season": "April-October",
        "cost_index": 0.84,
        "summary": "Bali brings together surf beaches, wellness escapes, rice terraces, temples, and vibrant nightlife.",
        "tags": ["nature", "beach", "party", "romantic", "adventure", "peaceful"],
        "stay_area": "Seminyak and Ubud",
        "travel_tips": [
            "Split your stay between Ubud for culture and Seminyak or Canggu for beaches.",
            "Use licensed drivers or ride-hailing instead of informal taxi bargaining.",
            "Pack a light rain layer even in dry season for inland evenings.",
            "Book water activities with operators that clearly include safety gear and insurance.",
            "Dress modestly when entering temple compounds.",
        ],
        "foods": ["nasi goreng", "satay", "smoothie bowls", "seafood grill"],
        "hotels": [
            {"name": "Seminyak Sky Villas", "price": 250, "rating": 4.7, "location": "Seminyak"},
            {"name": "Ubud Forest Escape", "price": 180, "rating": 4.6, "location": "Ubud"},
            {"name": "Canggu Surf Hostel", "price": 70, "rating": 4.2, "location": "Canggu"},
        ],
        "flights": [
            {"name": "Bali Direct Select", "price": 760, "type": "Non-stop", "duration": "7h 50m", "airline": "Singapore Airlines"},
            {"name": "Value Hopper via Kuala Lumpur", "price": 480, "type": "1 stop", "duration": "10h 35m", "airline": "AirAsia Mix"},
        ],
        "activities": [
            {"name": "Nusa Penida island day cruise", "price": 92, "duration": "Full day", "category": "Adventure", "description": "Cliff viewpoints, snorkel stops, and transfers"},
            {"name": "Tegalalang and waterfall circuit", "price": 55, "duration": "6h", "category": "Nature", "description": "Rice terraces plus jungle waterfall stops"},
            {"name": "Balinese cooking workshop", "price": 48, "duration": "3h", "category": "Food", "description": "Farm market visit and traditional lunch"},
        ],
        "nearby_places": [
            {"name": "Uluwatu Temple", "lat": -8.8291, "lng": 115.0849, "kind": "Temple"},
            {"name": "Tegallalang Rice Terrace", "lat": -8.4316, "lng": 115.2781, "kind": "Nature"},
            {"name": "Seminyak Beach", "lat": -8.6900, "lng": 115.1560, "kind": "Beach"},
            {"name": "Tirta Empul", "lat": -8.4157, "lng": 115.3153, "kind": "Temple"},
            {"name": "Canggu", "lat": -8.6478, "lng": 115.1385, "kind": "Town"},
        ],
    },
    {
        "slug": "paris-france",
        "name": "Paris, France",
        "country": "France",
        "coords": {"lat": 48.8566, "lng": 2.3522},
        "season": "April-June and September-October",
        "cost_index": 1.26,
        "summary": "Paris is a polished blend of art, architecture, cafés, riverfront romance, and iconic landmarks.",
        "tags": ["romantic", "cultural", "shopping", "foodie", "city", "peaceful"],
        "stay_area": "Le Marais and Saint-Germain",
        "travel_tips": [
            "Pre-book Eiffel Tower, Louvre, and Musée d'Orsay tickets to skip long queues.",
            "Use Navigo or metro carnet options for affordable transit across the city.",
            "Plan one early-morning landmark slot each day for quieter photos.",
            "Dinner reservations matter in popular bistros, especially on weekends.",
            "Keep valuables secure in crowded tourist corridors and metro transfers.",
        ],
        "foods": ["croissants", "bistro classics", "macarons", "Seine dinner cruise"],
        "hotels": [
            {"name": "Seine Signature Hotel", "price": 360, "rating": 4.8, "location": "Saint-Germain"},
            {"name": "Le Marais Boutique Stay", "price": 240, "rating": 4.5, "location": "Le Marais"},
            {"name": "Montmartre Smart Rooms", "price": 130, "rating": 4.0, "location": "Montmartre"},
        ],
        "flights": [
            {"name": "Paris Direct Premier", "price": 890, "type": "Non-stop", "duration": "8h 10m", "airline": "Air France"},
            {"name": "Euro Saver via Doha", "price": 620, "type": "1 stop", "duration": "11h 10m", "airline": "Qatar Connect"},
        ],
        "activities": [
            {"name": "Skip-the-line Louvre highlights", "price": 68, "duration": "3h", "category": "Culture", "description": "Curated route through the museum's major works"},
            {"name": "Seine evening cruise", "price": 39, "duration": "1.5h", "category": "Romance", "description": "Illuminated city views from the river"},
            {"name": "Montmartre food and art walk", "price": 54, "duration": "3h", "category": "Food", "description": "Pastries, cheese, and atelier districts"},
        ],
        "nearby_places": [
            {"name": "Eiffel Tower", "lat": 48.8584, "lng": 2.2945, "kind": "Landmark"},
            {"name": "Louvre Museum", "lat": 48.8606, "lng": 2.3376, "kind": "Museum"},
            {"name": "Montmartre", "lat": 48.8867, "lng": 2.3431, "kind": "District"},
            {"name": "Notre-Dame", "lat": 48.8530, "lng": 2.3499, "kind": "Cathedral"},
            {"name": "Luxembourg Gardens", "lat": 48.8462, "lng": 2.3372, "kind": "Park"},
        ],
    },
    {
        "slug": "swiss-alps",
        "name": "Swiss Alps, Switzerland",
        "country": "Switzerland",
        "coords": {"lat": 46.8182, "lng": 8.2275},
        "season": "June-September and December-February",
        "cost_index": 1.45,
        "summary": "The Swiss Alps deliver cinematic train rides, alpine villages, glacier views, and outdoor adventure.",
        "tags": ["adventure", "nature", "peaceful", "luxury", "romantic"],
        "stay_area": "Interlaken and Lauterbrunnen",
        "travel_tips": [
            "Mountain weather changes quickly, so keep a warm layer in your day pack.",
            "Swiss Travel Pass can pay for itself if you are taking multiple scenic trains.",
            "Book mountain excursions with clear cancellation options if weather shifts.",
            "Stay in Lauterbrunnen or Interlaken for easier regional train access.",
            "Carry refillable water bottles because public fountains are common and safe.",
        ],
        "foods": ["fondue", "rosti", "artisan chocolate", "mountain café brunch"],
        "hotels": [
            {"name": "Alpine Crest Lodge", "price": 390, "rating": 4.8, "location": "Interlaken"},
            {"name": "Lauterbrunnen Valley Stay", "price": 260, "rating": 4.6, "location": "Lauterbrunnen"},
            {"name": "Trailbase Hostel", "price": 120, "rating": 4.1, "location": "Grindelwald"},
        ],
        "flights": [
            {"name": "Zurich Direct Access", "price": 940, "type": "Non-stop", "duration": "8h 40m", "airline": "SWISS"},
            {"name": "Budget Alps via Istanbul", "price": 660, "type": "1 stop", "duration": "11h 55m", "airline": "Turkish Saver"},
        ],
        "activities": [
            {"name": "Jungfraujoch high-altitude rail day", "price": 160, "duration": "Full day", "category": "Adventure", "description": "Iconic rail journey and glacier panorama"},
            {"name": "Lauterbrunnen waterfall valley hike", "price": 42, "duration": "4h", "category": "Nature", "description": "Guided scenic route through alpine valley"},
            {"name": "Lake Brienz sunset cruise", "price": 38, "duration": "2h", "category": "Peaceful", "description": "Slow scenic cruise with mountain backdrop"},
        ],
        "nearby_places": [
            {"name": "Jungfraujoch", "lat": 46.5475, "lng": 7.9850, "kind": "Peak"},
            {"name": "Lauterbrunnen", "lat": 46.5935, "lng": 7.9091, "kind": "Village"},
            {"name": "Interlaken", "lat": 46.6863, "lng": 7.8632, "kind": "Town"},
            {"name": "Lake Brienz", "lat": 46.7367, "lng": 7.9657, "kind": "Lake"},
            {"name": "Grindelwald", "lat": 46.6242, "lng": 8.0414, "kind": "Village"},
        ],
    },
    {
        "slug": "manali-india",
        "name": "Manali, India",
        "country": "India",
        "coords": {"lat": 32.2396, "lng": 77.1887},
        "season": "March-June and October-December",
        "cost_index": 0.65,
        "summary": "Manali offers mountain escapes, pine forests, river views, and adventure-filled Himalayan energy.",
        "tags": ["adventure", "nature", "peaceful", "romantic", "budget"],
        "stay_area": "Old Manali and Vashisht",
        "travel_tips": [
            "Keep buffer time for mountain-road delays, especially after rain.",
            "Pack warm layers even if daytime weather looks mild.",
            "Book Solang or Atal Tunnel day trips early in peak season.",
            "Choose riverside cafés for slower evenings away from traffic-heavy stretches.",
            "Carry enough cash for remote scenic stops and roadside vendors.",
        ],
        "foods": ["siddu", "trout dishes", "Tibetan momos", "mountain café coffee"],
        "hotels": [
            {"name": "Himalayan Pine Retreat", "price": 130, "rating": 4.5, "location": "Old Manali"},
            {"name": "River View Residency", "price": 95, "rating": 4.3, "location": "Vashisht"},
            {"name": "Backpacker Basecamp", "price": 38, "rating": 4.0, "location": "Model Town"},
        ],
        "flights": [
            {"name": "Flight plus Volvo bundle", "price": 320, "type": "1 stop", "duration": "6h 20m", "airline": "Air India + Coach"},
            {"name": "Rail and road saver", "price": 180, "type": "Budget route", "duration": "11h 30m", "airline": "Train/Coach Mix"},
        ],
        "activities": [
            {"name": "Solang Valley adventure day", "price": 54, "duration": "Full day", "category": "Adventure", "description": "Ropeway, scenic stops, and alpine activities"},
            {"name": "Old Manali cultural walk", "price": 18, "duration": "2h", "category": "Culture", "description": "Cafés, local stories, and temple stops"},
            {"name": "Jogini waterfall hike", "price": 22, "duration": "3h", "category": "Nature", "description": "Short moderate trek with waterfall views"},
        ],
        "nearby_places": [
            {"name": "Hadimba Temple", "lat": 32.2482, "lng": 77.1771, "kind": "Temple"},
            {"name": "Old Manali", "lat": 32.2432, "lng": 77.1892, "kind": "Town"},
            {"name": "Solang Valley", "lat": 32.3167, "lng": 77.1567, "kind": "Adventure"},
            {"name": "Jogini Falls", "lat": 32.2662, "lng": 77.1738, "kind": "Nature"},
            {"name": "Atal Tunnel Viewpoint", "lat": 32.3853, "lng": 77.1338, "kind": "Scenic"},
        ],
    },
]


BUDDIES = [
    {
        "id": 1,
        "name": "Rahul Verma",
        "destination": "Manali, India",
        "match": 97,
        "rating": 4.8,
        "age": 27,
        "style": "Adventure",
        "avatar": "RV",
        "interests": ["trekking", "road trips", "budget travel"],
        "bio": "Weekend mountain chaser who likes balancing adventure with practical budgeting.",
    },
    {
        "id": 2,
        "name": "Sara Kim",
        "destination": "Kyoto, Japan",
        "match": 94,
        "rating": 4.9,
        "age": 29,
        "style": "Cultural",
        "avatar": "SK",
        "interests": ["photography", "tea houses", "heritage walks"],
        "bio": "Cultural traveler who builds photo-friendly, low-stress city itineraries.",
    },
    {
        "id": 3,
        "name": "Meera Shah",
        "destination": "Bali, Indonesia",
        "match": 91,
        "rating": 4.7,
        "age": 26,
        "style": "Wellness",
        "avatar": "MS",
        "interests": ["yoga", "beaches", "healthy cafés"],
        "bio": "Planning a slow Bali trip with wellness sessions, cafés, and easy day trips.",
    },
    {
        "id": 4,
        "name": "Leo Martin",
        "destination": "Paris, France",
        "match": 88,
        "rating": 4.6,
        "age": 31,
        "style": "City Explorer",
        "avatar": "LM",
        "interests": ["museums", "architecture", "food tours"],
        "bio": "City explorer focused on efficient routes, art museums, and solid restaurant picks.",
    },
]


def db_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def init_db() -> None:
    with db_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                phone TEXT,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                avatar TEXT,
                prefs TEXT DEFAULT '',
                city TEXT DEFAULT '',
                language TEXT DEFAULT 'en',
                currency TEXT DEFAULT 'USD',
                dark_mode INTEGER DEFAULT 1,
                role TEXT DEFAULT 'user',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS trips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                destination TEXT NOT NULL,
                start_date TEXT,
                duration_days INTEGER NOT NULL,
                budget REAL DEFAULT 0,
                travelers INTEGER DEFAULT 1,
                companion TEXT DEFAULT 'Solo',
                status TEXT DEFAULT 'Saved',
                booking_total REAL DEFAULT 0,
                plan_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                expense_date TEXT NOT NULL,
                trip_label TEXT DEFAULT '',
                receipt_name TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS wishlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                destination TEXT NOT NULL,
                meta_json TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                icon TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                unread INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                destination TEXT NOT NULL,
                rating INTEGER NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                photos_json TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                buddy_id INTEGER NOT NULL,
                sender TEXT NOT NULL,
                message TEXT NOT NULL,
                attachment_type TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS packing_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                destination TEXT NOT NULL,
                category TEXT NOT NULL,
                item TEXT NOT NULL,
                checked INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt_bytes = bytes.fromhex(salt) if salt else os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, 120_000)
    return salt_bytes.hex(), digest.hex()


def verify_password(password: str, salt: str, password_hash: str) -> bool:
    _, digest = hash_password(password, salt)
    return secrets.compare_digest(digest, password_hash)


def http_json(url: str, headers: dict[str, str] | None = None, timeout: int = 8) -> dict | list | None:
    request = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        logging.warning("External request failed: %s", url)
        return None


def get_weather_snapshot(lat: float, lng: float) -> dict:
    data = http_json(
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&current_weather=true&daily=temperature_2m_max,temperature_2m_min&timezone=auto"
    )
    if isinstance(data, dict) and data.get("current_weather"):
        current = data["current_weather"]
        code = current.get("weathercode", 0)
        if code <= 1:
            summary = "Clear"
            icon = "sun"
        elif code <= 3:
            summary = "Partly cloudy"
            icon = "cloud-sun"
        elif code <= 67:
            summary = "Rain"
            icon = "cloud-rain"
        else:
            summary = "Storm / snow"
            icon = "cloud-bolt"
        return {
            "temperature_c": current.get("temperature"),
            "windspeed_kmh": current.get("windspeed"),
            "summary": summary,
            "icon": icon,
            "source": "open-meteo",
        }
    return {"temperature_c": 24, "windspeed_kmh": 12, "summary": "Stable", "icon": "cloud", "source": "fallback"}


def get_exchange_rate(from_code: str, to_code: str) -> dict:
    from_code = (from_code or "USD").upper()
    to_code = (to_code or "USD").upper()
    if from_code == to_code:
        return {"rate": 1.0, "source": "identity", "base": from_code, "target": to_code}
    data = http_json(f"https://api.frankfurter.app/latest?from={from_code}&to={to_code}")
    if isinstance(data, dict) and data.get("rates", {}).get(to_code):
        return {"rate": float(data["rates"][to_code]), "source": "frankfurter", "base": from_code, "target": to_code}
    base_rate = FALLBACK_RATES.get(to_code, 1.0) / FALLBACK_RATES.get(from_code, 1.0)
    return {"rate": base_rate, "source": "fallback", "base": from_code, "target": to_code}


TRANSLATION_FALLBACKS = {
    "hi": {
        "Plan smarter trips with live data, realistic costs, and AI-backed decisions.": "Live data, realistic kharch aur AI-backed decisions ke saath smart trip plan banaiye.",
        "No active recommendation yet. Use the planner to generate one.": "Abhi koi active recommendation nahi hai. Planner se naya plan banaiye.",
    }
}


def translate_text(text: str, target_lang: str) -> dict:
    clean_text = (text or "").strip()
    target = (target_lang or "en").lower()
    if not clean_text:
        return {"translated_text": "", "target_lang": target, "source": "empty"}
    if target in {"en", "en-us", "en-gb"}:
        return {"translated_text": clean_text, "target_lang": "en", "source": "identity"}
    data = http_json(
        f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(clean_text)}&langpair=en|{urllib.parse.quote(target)}"
    )
    translated = None
    if isinstance(data, dict):
        translated = data.get("responseData", {}).get("translatedText")
    if translated:
        return {"translated_text": translated, "target_lang": target, "source": "mymemory"}
    fallback = TRANSLATION_FALLBACKS.get(target, {}).get(clean_text)
    return {"translated_text": fallback or clean_text, "target_lang": target, "source": "fallback"}


def social_demo_profile(provider: str, email: str, phone: str) -> tuple[str, str, str]:
    name_map = {
        "google": "Google Explorer",
        "otp": "Phone Traveler",
    }
    provider_key = (provider or "google").lower()
    final_email = (email or f"{provider_key}.demo@smarttrip.local").strip().lower()
    final_phone = (phone or "+910000000000").strip()
    return name_map.get(provider_key, "SmartTrip Demo User"), final_email, final_phone


def ensure_demo_user(conn: sqlite3.Connection, provider: str, email: str, phone: str) -> sqlite3.Row:
    name, final_email, final_phone = social_demo_profile(provider, email, phone)
    existing = conn.execute("SELECT * FROM users WHERE email = ?", (final_email,)).fetchone()
    if existing:
        return existing
    salt, password_hash = hash_password(secrets.token_urlsafe(12))
    role = "admin" if final_email.startswith("admin@") else "user"
    cursor = conn.execute(
        """
        INSERT INTO users (name, email, phone, password_hash, salt, avatar, role, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (name, final_email, final_phone, password_hash, salt, name[:1].upper(), role, utc_now().isoformat()),
    )
    user_id = cursor.lastrowid
    create_notification(conn, user_id, "sparkles", "Demo account ready", f"Signed in with {provider.title()} demo flow.")
    return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def search_place_live(query: str) -> list[dict]:
    encoded = urllib.parse.quote(query)
    data = http_json(
        f"https://nominatim.openstreetmap.org/search?q={encoded}&format=jsonv2&limit=6",
        headers={"User-Agent": "SmartTripAI/1.0"},
    )
    if isinstance(data, list):
        return [
            {
                "name": item.get("display_name"),
                "lat": float(item.get("lat", 0)),
                "lng": float(item.get("lon", 0)),
                "type": item.get("type", "place"),
            }
            for item in data
        ]
    return []


def resolve_destination(query: str) -> dict:
    normalized = (query or "").strip().lower()
    if not normalized:
        raise ValueError("Destination is required.")
    for item in DESTINATIONS:
        if normalized in item["name"].lower():
            return item
    for item in DESTINATIONS:
        haystack = " ".join([item["name"], item["country"], " ".join(item["tags"])]).lower()
        if normalized in haystack or any(word in haystack for word in normalized.split()):
            return item
    live = search_place_live(query)
    if live:
        first = live[0]
        return {
            "slug": normalized.replace(" ", "-"),
            "name": first["name"].split(",")[0],
            "country": first["name"].split(",")[-1].strip(),
            "coords": {"lat": first["lat"], "lng": first["lng"]},
            "season": "Peak season varies by destination",
            "cost_index": 1.0,
            "summary": f"{first['name']} has been resolved from live search. SmartTrip generated a flexible plan using geocoded location data.",
            "tags": ["explore", "city", "culture"],
            "stay_area": "Central district",
            "travel_tips": [
                "Confirm transport timings locally once your trip dates are fixed.",
                "Review weather again 48 hours before departure.",
                "Save offline maps for smoother navigation.",
                "Keep some local cash for small vendors and transit.",
                "Double-check opening days of major attractions.",
            ],
            "foods": ["local specialties", "market food", "regional desserts"],
            "hotels": [
                {"name": "City Centre Premium Hotel", "price": 210, "rating": 4.5, "location": "Central district"},
                {"name": "Business Stay Select", "price": 145, "rating": 4.2, "location": "Transit-friendly zone"},
                {"name": "Budget Urban Hostel", "price": 70, "rating": 4.0, "location": "Downtown"},
            ],
            "flights": [
                {"name": f"Best route to {first['name'].split(',')[0]}", "price": 650, "type": "Best available", "duration": "Varies", "airline": "Mixed carriers"},
            ],
            "activities": [
                {"name": "Landmark orientation tour", "price": 35, "duration": "3h", "category": "Explore", "description": "Curated walk through key districts"},
                {"name": "Local food trail", "price": 42, "duration": "2h", "category": "Food", "description": "Popular local dining stops"},
                {"name": "Flexible day pass", "price": 50, "duration": "Full day", "category": "Explore", "description": "Use for museums or sights depending on interest"},
            ],
            "nearby_places": live[:5],
        }
    return DESTINATIONS[0]


def destination_search(query: str) -> list[dict]:
    q = (query or "").strip().lower()
    if not q:
        return []
    local_results = [
        item
        for item in public_bootstrap()["destinations"]
        if q in item["name"].lower()
        or q in item["country"].lower()
        or any(q in tag for tag in item["tags"])
    ]
    if local_results:
        return local_results[:8]
    live_results = search_place_live(query)
    return [
        {
            "slug": (item["name"] or "place").lower().replace(" ", "-")[:80],
            "name": item["name"],
            "country": item["name"].split(",")[-1].strip() if "," in item["name"] else "Live result",
            "summary": f"Live geocoded result from OpenStreetMap/Nominatim. Use this to build a flexible SmartTrip plan.",
            "season": "Season varies by destination",
            "coords": {"lat": item["lat"], "lng": item["lng"]},
            "tags": [item.get("type") or "place", "live-search"],
        }
        for item in live_results[:8]
    ]


def fit_budget_items(items: list[dict], multiplier: float) -> list[dict]:
    fitted = []
    for item in items:
        clone = dict(item)
        clone["price"] = round(float(item["price"]) * multiplier)
        fitted.append(clone)
    return fitted


def daily_title(index: int, total: int, tags: list[str]) -> str:
    titles = [
        "Arrival and Neighborhood Orientation",
        "Signature Landmarks and Local Culture",
        "Scenic Exploration and Hidden Gems",
        "Food Trail and Flexible Discovery",
        "Adventure Day and Sunset Views",
        "Leisure, Shopping, and Slow Travel",
        "Wellness, Reflection, and Photo Spots",
    ]
    if index == 0:
        return "Arrival, Check-in, and First Impressions"
    if index == total - 1:
        return "Departure Day and Final Highlights"
    if "romantic" in tags and index % 3 == 0:
        return "Romantic Spots and Golden Hour Experiences"
    if "adventure" in tags and index % 2 == 0:
        return "Adventure Circuits and Scenic Routes"
    return titles[index % len(titles)]


def itinerary_for_destination(destination: dict, days: int, moods: list[str], start_date: str) -> list[dict]:
    nearby = destination.get("nearby_places", [])
    foods = destination.get("foods", [])
    itinerary = []
    try:
        base_date = dt.date.fromisoformat(start_date)
    except Exception:
        base_date = dt.date.today() + dt.timedelta(days=14)
    mood_tags = [m.lower() for m in moods]
    for index in range(days):
        place = nearby[index % len(nearby)] if nearby else {"name": "City centre", "lat": destination["coords"]["lat"], "lng": destination["coords"]["lng"], "kind": "Explore"}
        next_place = nearby[(index + 1) % len(nearby)] if nearby else place
        activities = [
            f"Morning: explore {place['name']} with enough time for photos and light local discovery.",
            f"Midday: lunch focused on {foods[index % len(foods)] if foods else 'regional cuisine'} near {place['name']}.",
            f"Afternoon: continue to {next_place['name']} for a {next_place.get('kind', 'local')} experience matched to your {', '.join(moods[:2]) or 'travel'} vibe.",
            f"Evening: unwind around {destination.get('stay_area', 'central district')} with a flexible dinner and rest window.",
        ]
        if index == 0:
            activities[0] = f"Arrival: transfer into {destination.get('stay_area', 'your hotel district')} and settle in without overloading the first day."
        if index == days - 1:
            activities[-1] = "Evening: departure transfer or a calm final dinner depending on your outbound timing."
        itinerary.append(
            {
                "day": index + 1,
                "date": (base_date + dt.timedelta(days=index)).isoformat(),
                "title": daily_title(index, days, mood_tags),
                "activities": activities,
                "accommodation": destination.get("hotels", [{}])[0].get("name", "Recommended stay"),
                "food_highlight": foods[index % len(foods)] if foods else "local specialties",
                "transport_note": "Use public transit and short cab hops for efficiency.",
                "route_point": {"lat": place.get("lat", destination["coords"]["lat"]), "lng": place.get("lng", destination["coords"]["lng"]), "name": place["name"]},
            }
        )
    return itinerary


def smart_recommendations(destination: dict, moods: list[str], budget: float, days: int, travelers: int) -> list[str]:
    notes = [
        f"{destination['name']} fits a {', '.join(moods) if moods else 'balanced'} travel style especially well.",
        f"With {days} days and {travelers} traveler(s), the plan keeps each day busy without becoming rushed.",
        "Transport and activity pacing have been tuned to reduce unnecessary backtracking.",
        "The itinerary intentionally mixes must-see highlights with lower-crowd recovery windows.",
        "Weather, cost range, and local transport practicality are all factored into this recommendation.",
    ]
    if budget < 1200:
        notes.append("Budget-sensitive picks lean toward high-value stays, local transit, and selective paid activities.")
    elif budget > 5000:
        notes.append("Your budget supports premium stays, private transfers, and higher-end food experiences without overspending.")
    return notes[:5]


PACKING_BASE = {
    "Essentials": [
        "Passport or government ID",
        "Travel insurance documents",
        "Booking confirmations and offline copies",
        "Credit/debit cards and some local cash",
        "Phone, charger, and power bank",
        "Universal travel adapter",
    ],
    "Clothing": [
        "Comfortable walking shoes",
        "Layered tops for changing weather",
        "One smart outfit for nicer dinners",
        "Sleepwear and daily undergarments",
        "Light rain jacket or compact umbrella",
    ],
    "Toiletries": [
        "Toothbrush and toothpaste",
        "Sunscreen and lip balm",
        "Personal medication with prescription",
        "Hand sanitizer and wet wipes",
        "Small first-aid kit",
    ],
    "Tech": [
        "Offline maps downloaded",
        "Charging cables",
        "Headphones",
        "Camera or phone storage backup",
        "Two-factor authentication backup codes",
    ],
}


def generate_packing_items(destination: str, days: int, trip_type: str, weather: dict | None = None) -> list[dict]:
    days = max(1, min(30, int(days or 7)))
    trip_type_l = (trip_type or "city").lower()
    items: list[dict] = []
    for category, names in PACKING_BASE.items():
        for name in names:
            items.append({"category": category, "item": name, "checked": False})
    if days >= 7:
        items.extend(
            [
                {"category": "Laundry and Long Stay", "item": "Laundry bag and quick-dry detergent sheets", "checked": False},
                {"category": "Laundry and Long Stay", "item": "Extra socks and innerwear buffer", "checked": False},
            ]
        )
    if "beach" in trip_type_l:
        items.extend(
            [
                {"category": "Beach", "item": "Swimwear and quick-dry towel", "checked": False},
                {"category": "Beach", "item": "Waterproof phone pouch", "checked": False},
                {"category": "Beach", "item": "Reef-safe sunscreen", "checked": False},
            ]
        )
    if "adventure" in trip_type_l or "hiking" in trip_type_l:
        items.extend(
            [
                {"category": "Adventure", "item": "Trail shoes or hiking boots", "checked": False},
                {"category": "Adventure", "item": "Headlamp or small flashlight", "checked": False},
                {"category": "Adventure", "item": "Reusable water bottle", "checked": False},
            ]
        )
    if weather and (weather.get("summary") or "").lower() in {"rain", "storm / snow"}:
        items.append({"category": "Weather", "item": "Water-resistant outer layer and dry bag", "checked": False})
    items.append({"category": "Destination", "item": f"Local SIM/eSIM and emergency numbers for {destination}", "checked": False})
    return items


def money(value: float, currency: str = "USD") -> str:
    symbols = {"USD": "$", "EUR": "€", "GBP": "£", "INR": "₹", "JPY": "¥", "AUD": "A$", "CAD": "C$", "CHF": "CHF ", "SGD": "S$", "THB": "฿"}
    return f"{symbols.get(currency, currency + ' ')}{value:,.0f}"


def generate_plan(payload: dict, user: sqlite3.Row | None = None) -> dict:
    destination_query = (payload.get("destination") or "").strip()
    days = max(1, min(30, int(payload.get("days") or 5)))
    budget = max(300.0, float(payload.get("budget") or 2500))
    travelers = max(1, min(12, int(payload.get("travelers") or 1)))
    moods = payload.get("moods") or []
    moods = moods if isinstance(moods, list) else []
    companion = payload.get("companion") or "Solo"
    accommodation = payload.get("accommodation") or "Smart balanced stay"
    notes = payload.get("notes") or ""
    start_date = payload.get("start_date") or iso_after(14)
    destination = resolve_destination(destination_query)
    currency = (user["currency"] if user else payload.get("currency") or "USD").upper()
    fx = get_exchange_rate("USD", currency)
    cost_multiplier = destination.get("cost_index", 1.0)
    base_total_usd = max(budget, days * travelers * 140 * cost_multiplier)
    hotel_ratio, transport_ratio, food_ratio, activity_ratio = 0.36, 0.22, 0.18, 0.14
    misc_ratio = 1 - (hotel_ratio + transport_ratio + food_ratio + activity_ratio)
    converted_total = base_total_usd * fx["rate"]
    itinerary = itinerary_for_destination(destination, days, moods, start_date)
    hotels = fit_budget_items(destination.get("hotels", []), fx["rate"] * max(0.85, travelers * 0.55))
    flights = fit_budget_items(destination.get("flights", []), fx["rate"] * max(0.9, travelers * 0.75))
    activities = fit_budget_items(destination.get("activities", []), fx["rate"] * max(1.0, travelers * 0.55))
    weather = get_weather_snapshot(destination["coords"]["lat"], destination["coords"]["lng"])
    total_low = converted_total * 0.9
    total_high = converted_total * 1.08
    return {
        "destination": destination["name"],
        "country": destination["country"],
        "coordinates": destination["coords"],
        "best_season": destination["season"],
        "description": destination["summary"],
        "budget_currency": currency,
        "budget_range": f"{money(total_low, currency)} - {money(total_high, currency)}",
        "budget_total": round(converted_total, 2),
        "weather": weather,
        "companion": companion,
        "travelers": travelers,
        "days": days,
        "start_date": start_date,
        "accommodation_style": accommodation,
        "notes": notes,
        "recommendations": smart_recommendations(destination, moods, budget, days, travelers),
        "travel_tips": destination["travel_tips"],
        "budget_breakdown": [
            {"category": "Accommodation", "amount": money(converted_total * hotel_ratio, currency), "pct": int(hotel_ratio * 100)},
            {"category": "Transport", "amount": money(converted_total * transport_ratio, currency), "pct": int(transport_ratio * 100)},
            {"category": "Food and dining", "amount": money(converted_total * food_ratio, currency), "pct": int(food_ratio * 100)},
            {"category": "Activities", "amount": money(converted_total * activity_ratio, currency), "pct": int(activity_ratio * 100)},
            {"category": "Miscellaneous", "amount": money(converted_total * misc_ratio, currency), "pct": int(misc_ratio * 100)},
        ],
        "itinerary": itinerary,
        "hotels": hotels,
        "flights": flights,
        "activities": activities,
        "nearby_places": destination["nearby_places"],
        "route_points": [item["route_point"] for item in itinerary],
        "moods": moods,
        "engine": {
            "planner": "SmartTrip Intelligence Engine",
            "rates_source": fx["source"],
            "weather_source": weather["source"],
            "exact_day_count": len(itinerary) == days,
        },
    }


def row_to_user(row: sqlite3.Row | None) -> dict | None:
    if not row:
        return None
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "phone": row["phone"] or "",
        "avatar": row["avatar"] or (row["name"][:1].upper()),
        "prefs": row["prefs"] or "",
        "city": row["city"] or "",
        "language": row["language"] or "en",
        "currency": row["currency"] or "USD",
        "dark_mode": bool(row["dark_mode"]),
        "role": row["role"],
        "created_at": row["created_at"],
    }


def create_notification(conn: sqlite3.Connection, user_id: int, icon: str, title: str, description: str) -> None:
    conn.execute(
        "INSERT INTO notifications (user_id, icon, title, description, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, icon, title, description, utc_now().isoformat()),
    )


def ensure_user_welcome(conn: sqlite3.Connection, user_id: int) -> None:
    count = conn.execute("SELECT COUNT(*) FROM notifications WHERE user_id = ?", (user_id,)).fetchone()[0]
    if count == 0:
        create_notification(conn, user_id, "wave", "Welcome to SmartTrip AI", "Your travel workspace is ready. Start planning your next trip.")


def query_all(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    return list(conn.execute(sql, params).fetchall())


def user_bootstrap(conn: sqlite3.Connection, user_id: int) -> dict:
    user_row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    ensure_user_welcome(conn, user_id)
    trips = []
    for row in query_all(conn, "SELECT * FROM trips WHERE user_id = ? ORDER BY created_at DESC", (user_id,)):
        trips.append(
            {
                "id": row["id"],
                "destination": row["destination"],
                "start_date": row["start_date"],
                "days": row["duration_days"],
                "budget": row["budget"],
                "travelers": row["travelers"],
                "companion": row["companion"],
                "status": row["status"],
                "booking_total": row["booking_total"],
                "plan": json.loads(row["plan_json"]),
                "created_at": row["created_at"],
            }
        )
    expenses = [
        {
            "id": row["id"],
            "amount": row["amount"],
            "description": row["description"],
            "category": row["category"],
            "expense_date": row["expense_date"],
            "trip_label": row["trip_label"],
            "receipt_name": row["receipt_name"],
            "created_at": row["created_at"],
        }
        for row in query_all(conn, "SELECT * FROM expenses WHERE user_id = ? ORDER BY expense_date DESC, id DESC", (user_id,))
    ]
    wishlist = [
        {
            "id": row["id"],
            "destination": row["destination"],
            "meta": json.loads(row["meta_json"] or "{}"),
            "created_at": row["created_at"],
        }
        for row in query_all(conn, "SELECT * FROM wishlist WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    ]
    notifications = [
        {
            "id": row["id"],
            "icon": row["icon"],
            "title": row["title"],
            "description": row["description"],
            "unread": bool(row["unread"]),
            "created_at": row["created_at"],
        }
        for row in query_all(conn, "SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 30", (user_id,))
    ]
    reviews = [
        {
            "id": row["id"],
            "destination": row["destination"],
            "rating": row["rating"],
            "title": row["title"],
            "body": row["body"],
            "photos": json.loads(row["photos_json"] or "[]"),
            "created_at": row["created_at"],
        }
        for row in query_all(conn, "SELECT * FROM reviews WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    ]
    chat = {}
    for buddy in BUDDIES:
        messages = [
            {
                "id": row["id"],
                "sender": row["sender"],
                "message": row["message"],
                "attachment_type": row["attachment_type"],
                "created_at": row["created_at"],
            }
            for row in query_all(
                conn,
                "SELECT * FROM chat_messages WHERE user_id = ? AND buddy_id = ? ORDER BY created_at ASC",
                (user_id, buddy["id"]),
            )
        ]
        if not messages:
            messages = [
                {
                    "id": 0,
                    "sender": "buddy",
                    "message": f"Hi! I saw you're exploring {buddy['destination']}. Happy to coordinate plans.",
                    "attachment_type": "",
                    "created_at": utc_now().isoformat(),
                }
            ]
        chat[str(buddy["id"])] = messages
    packing = [
        {
            "id": row["id"],
            "destination": row["destination"],
            "category": row["category"],
            "item": row["item"],
            "checked": bool(row["checked"]),
            "created_at": row["created_at"],
        }
        for row in query_all(conn, "SELECT * FROM packing_items WHERE user_id = ? ORDER BY category, id", (user_id,))
    ]
    unread = sum(1 for item in notifications if item["unread"])
    total_spend = sum(item["amount"] for item in expenses)
    analytics = {
        "trip_count": len(trips),
        "expense_total": total_spend,
        "wishlist_count": len(wishlist),
        "unread_notifications": unread,
        "category_totals": {},
    }
    for item in expenses:
        analytics["category_totals"][item["category"]] = analytics["category_totals"].get(item["category"], 0) + item["amount"]
    return {
        "user": row_to_user(user_row),
        "trips": trips,
        "expenses": expenses,
        "wishlist": wishlist,
        "notifications": notifications,
        "reviews": reviews,
        "chat": chat,
        "packing": packing,
        "analytics": analytics,
    }


def public_bootstrap() -> dict:
    return {
        "destinations": [
            {
                "slug": item["slug"],
                "name": item["name"],
                "country": item["country"],
                "summary": item["summary"],
                "season": item["season"],
                "coords": item["coords"],
                "tags": item["tags"],
            }
            for item in DESTINATIONS
        ],
        "buddies": BUDDIES,
        "feature_flags": {
            "live_weather": True,
            "live_currency": True,
            "live_geocoding": True,
            "offline_cache": True,
            "voice_input": True,
            "voice_output": True,
            "packing_lists": True,
        },
    }


def create_session(conn: sqlite3.Connection, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    now = utc_now()
    expires = now + dt.timedelta(days=7)
    conn.execute(
        "INSERT INTO sessions (user_id, token, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (user_id, token, now.isoformat(), expires.isoformat()),
    )
    return token


class SmartTripHandler(BaseHTTPRequestHandler):
    server_version = "SmartTripHTTP/1.0"

    def log_message(self, format: str, *args) -> None:
        logging.info("%s - %s", self.address_string(), format % args)

    def _send(self, status: int, body: bytes, content_type: str = "application/json; charset=utf-8") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, data: dict | list, status: int = 200) -> None:
        self._send(status, json.dumps(data).encode("utf-8"))

    def send_error_json(self, status: int, message: str) -> None:
        self.send_json({"ok": False, "error": message}, status)

    def parse_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        try:
            raw = self.rfile.read(length).decode("utf-8")
            return json.loads(raw or "{}")
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON body")

    def get_token(self) -> str | None:
        header = self.headers.get("Authorization", "")
        if header.startswith("Bearer "):
            return header.split(" ", 1)[1].strip()
        custom = self.headers.get("X-Auth-Token")
        return custom.strip() if custom else None

    def current_user(self) -> sqlite3.Row | None:
        token = self.get_token()
        if not token:
            return None
        with db_conn() as conn:
            row = conn.execute(
                """
                SELECT u.* FROM sessions s
                JOIN users u ON u.id = s.user_id
                WHERE s.token = ? AND s.expires_at > ?
                """,
                (token, utc_now().isoformat()),
            ).fetchone()
            return row

    def require_user(self) -> sqlite3.Row | None:
        user = self.current_user()
        if not user:
            self.send_error_json(401, "Authentication required")
            return None
        return user

    def serve_static(self, path: str) -> None:
        candidate = (ROOT / path.lstrip("/")).resolve()
        if not str(candidate).startswith(str(ROOT.resolve())) or not candidate.exists():
            self.send_error_json(404, "File not found")
            return
        content_type = mimetypes.guess_type(str(candidate))[0] or "application/octet-stream"
        self._send(200, candidate.read_bytes(), content_type)

    def do_GET(self) -> None:
        self.dispatch("GET")

    def do_POST(self) -> None:
        self.dispatch("POST")

    def do_PUT(self) -> None:
        self.dispatch("PUT")

    def do_DELETE(self) -> None:
        self.dispatch("DELETE")

    def dispatch(self, method: str) -> None:
        try:
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            query = urllib.parse.parse_qs(parsed.query)
            if path == "/":
                self._send(200, (TEMPLATE_DIR / "index.html").read_bytes(), "text/html; charset=utf-8")
                return
            if path.startswith("/static/"):
                self.serve_static(path)
                return
            if path == "/api/health":
                self.send_json({"ok": True, "status": "healthy", "time": utc_now().isoformat()})
                return
            if path == "/api/bootstrap":
                user = self.current_user()
                payload = public_bootstrap()
                if user:
                    with db_conn() as conn:
                        payload["session"] = user_bootstrap(conn, user["id"])
                else:
                    payload["session"] = {"user": None, "trips": [], "expenses": [], "wishlist": [], "notifications": [], "reviews": [], "chat": {}, "analytics": {"trip_count": 0, "expense_total": 0, "wishlist_count": 0, "unread_notifications": 0, "category_totals": {}}}
                self.send_json({"ok": True, "data": payload})
                return
            if path == "/api/weather":
                lat = float(query.get("lat", [0])[0])
                lng = float(query.get("lng", [0])[0])
                self.send_json({"ok": True, "data": get_weather_snapshot(lat, lng)})
                return
            if path == "/api/currency":
                amount = float(query.get("amount", [100])[0])
                from_code = query.get("from", ["USD"])[0]
                to_code = query.get("to", ["INR"])[0]
                fx = get_exchange_rate(from_code, to_code)
                self.send_json({"ok": True, "data": {"amount": amount, "from": from_code, "to": to_code, "rate": fx["rate"], "converted": round(amount * fx["rate"], 2), "source": fx["source"]}})
                return
            if path == "/api/translate":
                text_value = query.get("text", [""])[0]
                target_lang = query.get("target", ["hi"])[0]
                self.send_json({"ok": True, "data": translate_text(text_value, target_lang)})
                return
            if path == "/api/search/destinations":
                q = query.get("q", [""])[0]
                self.send_json({"ok": True, "data": destination_search(q)})
                return
            if path == "/api/location/search":
                q = query.get("q", [""])[0]
                if not q:
                    self.send_json({"ok": True, "data": []})
                    return
                live = search_place_live(q)
                if not live:
                    live = [
                        {
                            "name": item["name"],
                            "lat": item["coords"]["lat"],
                            "lng": item["coords"]["lng"],
                            "type": item["country"],
                        }
                        for item in DESTINATIONS
                        if q.lower() in item["name"].lower() or q.lower() in item["country"].lower()
                    ]
                self.send_json({"ok": True, "data": live[:8]})
                return
            if path == "/api/buddies":
                self.send_json({"ok": True, "data": BUDDIES})
                return
            if path.startswith("/api/buddies/"):
                buddy_id = int(path.rsplit("/", 1)[-1])
                buddy = next((item for item in BUDDIES if item["id"] == buddy_id), None)
                if not buddy:
                    self.send_error_json(404, "Buddy not found")
                    return
                self.send_json({"ok": True, "data": buddy})
                return
            if path == "/api/admin/overview":
                user = self.require_user()
                if not user:
                    return
                if user["role"] != "admin":
                    self.send_error_json(403, "Admin access required")
                    return
                with db_conn() as conn:
                    overview = {
                        "users": conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
                        "trips": conn.execute("SELECT COUNT(*) FROM trips").fetchone()[0],
                        "expenses": conn.execute("SELECT COALESCE(SUM(amount),0) FROM expenses").fetchone()[0],
                        "reviews": conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0],
                    }
                self.send_json({"ok": True, "data": overview})
                return

            if path == "/api/auth/logout" and method == "POST":
                token = self.get_token()
                if token:
                    with db_conn() as conn:
                        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
                self.send_json({"ok": True})
                return

            if path == "/api/auth/signup" and method == "POST":
                data = self.parse_json()
                name = (data.get("name") or "").strip()
                email = (data.get("email") or "").strip().lower()
                phone = (data.get("phone") or "").strip()
                password = data.get("password") or ""
                avatar = data.get("avatar") or ""
                if len(name) < 2 or "@" not in email or len(password) < 6:
                    self.send_error_json(400, "Please provide a valid name, email, and password.")
                    return
                salt, password_hash = hash_password(password)
                role = "admin" if email.startswith("admin@") else "user"
                with db_conn() as conn:
                    try:
                        cursor = conn.execute(
                            """
                            INSERT INTO users (name, email, phone, password_hash, salt, avatar, role, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (name, email, phone, password_hash, salt, avatar, role, utc_now().isoformat()),
                        )
                        user_id = cursor.lastrowid
                        create_notification(conn, user_id, "sparkles", "Account created", "Your workspace is live. Start with a destination search or AI planner.")
                        token = create_session(conn, user_id)
                        payload = user_bootstrap(conn, user_id)
                        self.send_json({"ok": True, "token": token, "data": payload}, 201)
                        return
                    except sqlite3.IntegrityError:
                        self.send_error_json(409, "An account with this email already exists.")
                        return

            if path == "/api/auth/login" and method == "POST":
                data = self.parse_json()
                email = (data.get("email") or "").strip().lower()
                password = data.get("password") or ""
                with db_conn() as conn:
                    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
                    if not user or not verify_password(password, user["salt"], user["password_hash"]):
                        self.send_error_json(401, "Invalid email or password.")
                        return
                    token = create_session(conn, user["id"])
                    create_notification(conn, user["id"], "shield", "Login successful", "You have securely signed in to SmartTrip AI.")
                    self.send_json({"ok": True, "token": token, "data": user_bootstrap(conn, user["id"])})
                    return

            if path == "/api/auth/social-demo" and method == "POST":
                data = self.parse_json()
                provider = (data.get("provider") or "google").lower()
                with db_conn() as conn:
                    user = ensure_demo_user(conn, provider, data.get("email") or "", data.get("phone") or "")
                    token = create_session(conn, user["id"])
                    create_notification(conn, user["id"], "shield", "Demo login successful", f"You are signed in using the {provider.title()} demo flow.")
                    self.send_json({"ok": True, "token": token, "data": user_bootstrap(conn, user["id"])})
                    return

            if path == "/api/auth/otp-demo" and method == "POST":
                data = self.parse_json()
                phone = (data.get("phone") or "").strip()
                if len(phone) < 8:
                    self.send_error_json(400, "Enter a valid phone number for OTP demo login.")
                    return
                with db_conn() as conn:
                    user = ensure_demo_user(conn, "otp", f"otp-{phone[-6:]}@smarttrip.local", phone)
                    token = create_session(conn, user["id"])
                    create_notification(conn, user["id"], "mobile", "OTP login successful", "Phone verification demo completed successfully.")
                    self.send_json({"ok": True, "token": token, "data": user_bootstrap(conn, user["id"])})
                    return

            if path == "/api/auth/password-reset-demo" and method == "POST":
                data = self.parse_json()
                email = (data.get("email") or "").strip().lower()
                if "@" not in email:
                    self.send_error_json(400, "Enter a valid email address.")
                    return
                with db_conn() as conn:
                    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
                    if user:
                        create_notification(
                            conn,
                            user["id"],
                            "key",
                            "Password reset requested",
                            "A secure reset link would be emailed in production. This local build logged the request.",
                        )
                    self.send_json({"ok": True, "data": {"message": "If the account exists, reset instructions were prepared."}})
                    return

            if path == "/api/profile" and method == "PUT":
                user = self.require_user()
                if not user:
                    return
                data = self.parse_json()
                name = (data.get("name") or user["name"]).strip()
                phone = (data.get("phone") or "").strip()
                prefs = (data.get("prefs") or "").strip()
                city = (data.get("city") or "").strip()
                language = (data.get("language") or "en").lower()
                currency = (data.get("currency") or "USD").upper()
                avatar = data.get("avatar") or user["avatar"]
                dark_mode = 1 if data.get("dark_mode", True) else 0
                with db_conn() as conn:
                    conn.execute(
                        """
                        UPDATE users SET name=?, phone=?, prefs=?, city=?, language=?, currency=?, avatar=?, dark_mode=?
                        WHERE id = ?
                        """,
                        (name, phone, prefs, city, language, currency, avatar, dark_mode, user["id"]),
                    )
                    create_notification(conn, user["id"], "gear", "Profile updated", "Your account preferences were saved successfully.")
                    self.send_json({"ok": True, "data": user_bootstrap(conn, user["id"])})
                    return

            if path == "/api/plans/recommend" and method == "POST":
                user = self.current_user()
                data = self.parse_json()
                plan = generate_plan(data, user)
                self.send_json({"ok": True, "data": plan})
                return

            if path == "/api/trips" and method == "POST":
                user = self.require_user()
                if not user:
                    return
                data = self.parse_json()
                plan = data.get("plan")
                if not isinstance(plan, dict):
                    self.send_error_json(400, "Trip plan payload is required.")
                    return
                with db_conn() as conn:
                    cursor = conn.execute(
                        """
                        INSERT INTO trips (user_id, destination, start_date, duration_days, budget, travelers, companion, status, booking_total, plan_json, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            user["id"],
                            plan.get("destination"),
                            plan.get("start_date"),
                            int(plan.get("days") or 1),
                            float(plan.get("budget_total") or 0),
                            int(plan.get("travelers") or 1),
                            plan.get("companion") or "Solo",
                            data.get("status") or "Saved",
                            float(data.get("booking_total") or 0),
                            json.dumps(plan),
                            utc_now().isoformat(),
                        ),
                    )
                    create_notification(conn, user["id"], "bookmark", "Trip saved", f"{plan.get('destination')} was added to your trips list.")
                    self.send_json({"ok": True, "trip_id": cursor.lastrowid, "data": user_bootstrap(conn, user["id"])}, 201)
                    return

            if path.startswith("/api/trips/") and method == "DELETE":
                user = self.require_user()
                if not user:
                    return
                trip_id = int(path.rsplit("/", 1)[-1])
                with db_conn() as conn:
                    conn.execute("DELETE FROM trips WHERE id = ? AND user_id = ?", (trip_id, user["id"]))
                    self.send_json({"ok": True, "data": user_bootstrap(conn, user["id"])})
                    return

            if path == "/api/expenses" and method == "POST":
                user = self.require_user()
                if not user:
                    return
                data = self.parse_json()
                amount = float(data.get("amount") or 0)
                description = (data.get("description") or "").strip()
                category = (data.get("category") or "Misc").strip()
                if amount <= 0 or not description:
                    self.send_error_json(400, "A positive amount and description are required.")
                    return
                with db_conn() as conn:
                    conn.execute(
                        """
                        INSERT INTO expenses (user_id, amount, description, category, expense_date, trip_label, receipt_name, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            user["id"],
                            amount,
                            description,
                            category,
                            data.get("expense_date") or today_iso(),
                            (data.get("trip_label") or "").strip(),
                            (data.get("receipt_name") or "").strip(),
                            utc_now().isoformat(),
                        ),
                    )
                    self.send_json({"ok": True, "data": user_bootstrap(conn, user["id"])}, 201)
                    return

            if path.startswith("/api/expenses/") and method == "DELETE":
                user = self.require_user()
                if not user:
                    return
                expense_id = int(path.rsplit("/", 1)[-1])
                with db_conn() as conn:
                    conn.execute("DELETE FROM expenses WHERE id = ? AND user_id = ?", (expense_id, user["id"]))
                    self.send_json({"ok": True, "data": user_bootstrap(conn, user["id"])})
                    return

            if path == "/api/wishlist" and method == "POST":
                user = self.require_user()
                if not user:
                    return
                data = self.parse_json()
                destination = (data.get("destination") or "").strip()
                if not destination:
                    self.send_error_json(400, "Destination is required.")
                    return
                with db_conn() as conn:
                    exists = conn.execute("SELECT 1 FROM wishlist WHERE user_id = ? AND destination = ?", (user["id"], destination)).fetchone()
                    if not exists:
                        conn.execute(
                            "INSERT INTO wishlist (user_id, destination, meta_json, created_at) VALUES (?, ?, ?, ?)",
                            (user["id"], destination, json.dumps(data.get("meta") or {}), utc_now().isoformat()),
                        )
                        create_notification(conn, user["id"], "heart", "Wishlist updated", f"{destination} was added to your wishlist.")
                    self.send_json({"ok": True, "data": user_bootstrap(conn, user["id"])}, 201)
                    return

            if path.startswith("/api/wishlist/") and method == "DELETE":
                user = self.require_user()
                if not user:
                    return
                wish_id = int(path.rsplit("/", 1)[-1])
                with db_conn() as conn:
                    conn.execute("DELETE FROM wishlist WHERE id = ? AND user_id = ?", (wish_id, user["id"]))
                    self.send_json({"ok": True, "data": user_bootstrap(conn, user["id"])})
                    return

            if path == "/api/notifications/read-all" and method == "POST":
                user = self.require_user()
                if not user:
                    return
                with db_conn() as conn:
                    conn.execute("UPDATE notifications SET unread = 0 WHERE user_id = ?", (user["id"],))
                    self.send_json({"ok": True, "data": user_bootstrap(conn, user["id"])})
                    return

            if path == "/api/notifications" and method == "DELETE":
                user = self.require_user()
                if not user:
                    return
                with db_conn() as conn:
                    conn.execute("DELETE FROM notifications WHERE user_id = ?", (user["id"],))
                    self.send_json({"ok": True, "data": user_bootstrap(conn, user["id"])})
                    return

            if path == "/api/reviews" and method == "POST":
                user = self.require_user()
                if not user:
                    return
                data = self.parse_json()
                rating = int(data.get("rating") or 0)
                title = (data.get("title") or "").strip()
                body = (data.get("body") or "").strip()
                destination = (data.get("destination") or "").strip()
                if rating < 1 or rating > 5 or not title or not body or not destination:
                    self.send_error_json(400, "Review destination, title, body, and rating are required.")
                    return
                with db_conn() as conn:
                    conn.execute(
                        """
                        INSERT INTO reviews (user_id, destination, rating, title, body, photos_json, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (user["id"], destination, rating, title, body, json.dumps(data.get("photos") or []), utc_now().isoformat()),
                    )
                    create_notification(conn, user["id"], "star", "Review submitted", f"Thanks for reviewing {destination}.")
                    self.send_json({"ok": True, "data": user_bootstrap(conn, user["id"])}, 201)
                    return

            if path == "/api/packing/generate" and method == "POST":
                user = self.require_user()
                if not user:
                    return
                data = self.parse_json()
                destination = (data.get("destination") or "").strip()
                if not destination:
                    self.send_error_json(400, "Destination is required for a packing list.")
                    return
                days = max(1, min(30, int(data.get("days") or 7)))
                trip_type = (data.get("trip_type") or "City").strip()
                weather = None
                try:
                    resolved = resolve_destination(destination)
                    weather = get_weather_snapshot(resolved["coords"]["lat"], resolved["coords"]["lng"])
                except Exception:
                    weather = None
                items = generate_packing_items(destination, days, trip_type, weather)
                with db_conn() as conn:
                    conn.execute("DELETE FROM packing_items WHERE user_id = ?", (user["id"],))
                    conn.executemany(
                        """
                        INSERT INTO packing_items (user_id, destination, category, item, checked, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        [
                            (
                                user["id"],
                                destination,
                                item["category"],
                                item["item"],
                                1 if item.get("checked") else 0,
                                utc_now().isoformat(),
                            )
                            for item in items
                        ],
                    )
                    create_notification(conn, user["id"], "bag", "Packing list ready", f"Smart packing list generated for {destination}.")
                    self.send_json({"ok": True, "data": user_bootstrap(conn, user["id"])}, 201)
                    return

            if path == "/api/packing/toggle" and method == "POST":
                user = self.require_user()
                if not user:
                    return
                data = self.parse_json()
                item_id = int(data.get("id") or 0)
                checked = 1 if data.get("checked") else 0
                with db_conn() as conn:
                    conn.execute(
                        "UPDATE packing_items SET checked = ? WHERE id = ? AND user_id = ?",
                        (checked, item_id, user["id"]),
                    )
                    self.send_json({"ok": True, "data": user_bootstrap(conn, user["id"])})
                    return

            if path == "/api/packing" and method == "DELETE":
                user = self.require_user()
                if not user:
                    return
                with db_conn() as conn:
                    conn.execute("DELETE FROM packing_items WHERE user_id = ?", (user["id"],))
                    self.send_json({"ok": True, "data": user_bootstrap(conn, user["id"])})
                    return

            if path == "/api/chat/send" and method == "POST":
                user = self.require_user()
                if not user:
                    return
                data = self.parse_json()
                buddy_id = int(data.get("buddy_id") or 0)
                message = (data.get("message") or "").strip()
                attachment_type = (data.get("attachment_type") or "").strip()
                if not buddy_id or not message:
                    self.send_error_json(400, "Buddy and message are required.")
                    return
                buddy = next((item for item in BUDDIES if item["id"] == buddy_id), None)
                if not buddy:
                    self.send_error_json(404, "Buddy not found.")
                    return
                with db_conn() as conn:
                    conn.execute(
                        "INSERT INTO chat_messages (user_id, buddy_id, sender, message, attachment_type, created_at) VALUES (?, ?, 'user', ?, ?, ?)",
                        (user["id"], buddy_id, message, attachment_type, utc_now().isoformat()),
                    )
                    buddy_reply = chat_reply(message, buddy)
                    conn.execute(
                        "INSERT INTO chat_messages (user_id, buddy_id, sender, message, attachment_type, created_at) VALUES (?, ?, 'buddy', ?, '', ?)",
                        (user["id"], buddy_id, buddy_reply, utc_now().isoformat()),
                    )
                    self.send_json({"ok": True, "data": user_bootstrap(conn, user["id"])})
                    return

            if path == "/api/bookings/confirm" and method == "POST":
                user = self.require_user()
                if not user:
                    return
                data = self.parse_json()
                plan = data.get("plan")
                total = float(data.get("total") or 0)
                if not isinstance(plan, dict) or total <= 0:
                    self.send_error_json(400, "Valid booking plan and total are required.")
                    return
                with db_conn() as conn:
                    cursor = conn.execute(
                        """
                        INSERT INTO trips (user_id, destination, start_date, duration_days, budget, travelers, companion, status, booking_total, plan_json, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 'Booked', ?, ?, ?)
                        """,
                        (
                            user["id"],
                            plan.get("destination"),
                            plan.get("start_date"),
                            int(plan.get("days") or 1),
                            float(plan.get("budget_total") or 0),
                            int(plan.get("travelers") or 1),
                            plan.get("companion") or "Solo",
                            total,
                            json.dumps(plan),
                            utc_now().isoformat(),
                        ),
                    )
                    conn.execute(
                        """
                        INSERT INTO expenses (user_id, amount, description, category, expense_date, trip_label, receipt_name, created_at)
                        VALUES (?, ?, ?, 'Booking', ?, ?, ?, ?)
                        """,
                        (
                            user["id"],
                            total,
                            f"Booking confirmed for {plan.get('destination')}",
                            today_iso(),
                            plan.get("destination"),
                            "booking-confirmation",
                            utc_now().isoformat(),
                        ),
                    )
                    create_notification(conn, user["id"], "credit-card", "Payment confirmed", f"Booking for {plan.get('destination')} is confirmed.")
                    self.send_json({"ok": True, "trip_id": cursor.lastrowid, "data": user_bootstrap(conn, user["id"])}, 201)
                    return

            if path == "/api/chat/assistant" and method == "POST":
                data = self.parse_json()
                message = (data.get("message") or "").strip()
                plan = data.get("plan") if isinstance(data.get("plan"), dict) else None
                self.send_json({"ok": True, "data": {"reply": assistant_reply(message, plan)}})
                return

            if path == "/api/settings" and method == "PUT":
                user = self.require_user()
                if not user:
                    return
                data = self.parse_json()
                with db_conn() as conn:
                    conn.execute(
                        "UPDATE users SET language = ?, currency = ?, dark_mode = ? WHERE id = ?",
                        (
                            (data.get("language") or user["language"] or "en").lower(),
                            (data.get("currency") or user["currency"] or "USD").upper(),
                            1 if data.get("dark_mode", True) else 0,
                            user["id"],
                        ),
                    )
                    self.send_json({"ok": True, "data": user_bootstrap(conn, user["id"])})
                    return

            if path == "/api/logs/client" and method == "POST":
                data = self.parse_json()
                logging.error("CLIENT %s", json.dumps(data))
                self.send_json({"ok": True})
                return

            self.send_error_json(404, "Route not found")
        except ValueError as exc:
            self.send_error_json(400, str(exc))
        except Exception as exc:
            logging.error("Unhandled server error: %s\n%s", exc, traceback.format_exc())
            self.send_error_json(500, "Unexpected server error")


def chat_reply(message: str, buddy: dict) -> str:
    text = message.lower()
    if "hotel" in text or "stay" in text:
        return f"I found a couple of good stay options around {buddy['destination']}. Want me to share the best-value one?"
    if "budget" in text or "cost" in text:
        return "I usually split the trip into transport, stay, food, and buffer money. That keeps plans realistic."
    if "day" in text or "itinerary" in text:
        return "Let us lock the high-priority spots first, then we can keep one flexible evening open."
    if "location" in text:
        return "Nice spot. That would fit well as a morning anchor before the city gets crowded."
    if "photo" in text or "image" in text:
        return "That looks great. We should add it as a saved stop in the map view."
    return f"That works for me. Since I'm also planning around {buddy['destination']}, we can coordinate a smarter route."


def assistant_reply(message: str, plan: dict | None) -> str:
    text = message.lower()
    if not message:
        return "Ask me about trip strategy, budgeting, weather, route planning, or destination fit."
    if plan and ("itinerary" in text or "day" in text):
        return f"Your current {plan.get('days')} day itinerary is already balanced. If you want, I can help compress it, slow it down, or make it more food-focused."
    if "visa" in text:
        return "Visa rules change often, so use embassy or airline travel advisories as the final source. I can still help you build a checklist around passport validity, insurance, bookings, and funds."
    if "budget" in text:
        return "A reliable travel budget usually uses five buckets: stay, transport, food, activities, and a 10-15% contingency. SmartTrip already breaks those out so you can track overruns early."
    if "weather" in text:
        return "Use live weather for final packing, but let seasonality guide destination choice and daily pacing. Outdoor-heavy days should stay flexible until 48 hours before departure."
    if "saf" in text:
        return "Safety planning works best when you combine transport timing, neighborhood choice, backup payment options, and offline maps. I can help you turn that into a destination-specific checklist."
    return "I can help with destination fit, smarter routing, exact-day itineraries, cost planning, and travel readiness. If you want better advice, ask with your destination, number of days, budget, and travel style."


def run() -> None:
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), SmartTripHandler)
    print(f"SmartTrip AI running on http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        server.server_close()


if __name__ == "__main__":
    run()
