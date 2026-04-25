import json
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import app


def req(method, path, data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data is not None else None
    request = urllib.request.Request(f"http://127.0.0.1:8765{path}", data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(exc.read().decode("utf-8", errors="replace")) from exc


def main():
    compile(open("app.py", "r", encoding="utf-8").read(), "app.py", "exec")
    app.init_db()
    server = ThreadingHTTPServer(("127.0.0.1", 8765), app.SmartTripHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.2)

    try:
        signup = req(
            "POST",
            "/api/auth/signup",
            {
                "name": "Smoke User",
                "phone": "+91 9000000000",
                "email": f"smoke-{int(time.time())}@example.com",
                "password": "smoketest123",
            },
        )
        token = signup["token"]
        plan = req(
            "POST",
            "/api/plans/recommend",
            {
                "destination": "Kyoto",
                "days": 5,
                "budget": 2800,
                "travelers": 2,
                "companion": "Couple",
                "accommodation": "Balanced premium stay",
                "moods": ["Romantic", "Cultural"],
                "start_date": "2026-06-10",
            },
        )
        req("POST", "/api/trips", {"status": "Saved", "plan": plan["data"]}, token)
        req(
            "POST",
            "/api/expenses",
            {
                "amount": 85.5,
                "description": "Airport transfer",
                "category": "Transport",
                "expense_date": "2026-06-10",
                "trip_label": "Kyoto",
            },
            token,
        )
        bootstrap = req("GET", "/api/bootstrap", None, token)
        summary = {
            "ok": True,
            "planned_days": len(plan["data"]["itinerary"]),
            "trip_count": len(bootstrap["data"]["session"]["trips"]),
            "expense_count": len(bootstrap["data"]["session"]["expenses"]),
        }
        print(json.dumps(summary, indent=2))
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
