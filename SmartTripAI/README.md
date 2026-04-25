# SmartTrip AI

SmartTrip AI is a full-stack travel planning application built with:

- Frontend: HTML, CSS, JavaScript, Bootstrap, Leaflet
- Backend: Python standard library HTTP server
- Database: SQLite

## What is included

- Secure signup/login with password hashing and session tokens
- Dashboard analytics, trip history, notifications, wishlist, reviews
- Exact-day AI-style itinerary generation with practical travel logic
- Live weather, currency conversion, geocoding, and interactive maps
- Travel buddy matching, profile view, and persistent chat threads
- Smart packing list generation with persistent checklist state
- Booking flow, payment confirmation workflow, and expense tracking
- Settings, offline cache support, service worker, export/share helpers
- Admin overview page for admin users (`admin@...` emails get admin role)

## Run locally

```bash
python app.py
```

Then open:

```text
http://127.0.0.1:8000
```

## Smoke test

```bash
python smoke_test.py
```

## Runtime notes

- The app stores the SQLite database and log file in the local temp runtime folder to avoid OneDrive file-lock issues.
- Public live integrations are used when available:
  - Weather: Open-Meteo
  - Currency: Frankfurter
  - Geocoding / place search: Nominatim
- If those services are unavailable, the app falls back gracefully to built-in logic.
