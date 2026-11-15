"""Bekrefter treff med live priser fra Google Flights via SerpApi.

- Maks config.SERPAPI_MONTHLY_LIMIT søk per måned, fordelt jevnt på dagene som er igjen.
- Treff fra Evenes/Bodø sjekkes før Tromsø/Oslo (config.VERIFY_PRIORITY).
- Et treff sjekkes bare én gang; resultatet lagres i databasen.
- Uten SERPAPI_KEY gjøres ingenting.
"""
from __future__ import annotations

import calendar
import json
import math
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone

import config
import db

URL = "https://serpapi.com/search.json"


class OutOfSearches(Exception):
    pass


def _airports(code: str, as_departure: bool) -> str:
    if as_departure:
        return code                      # avreise: eksakt flyplass (OSL = bare Gardermoen)
    return config.CITY_AIRPORTS.get(code, code)


def _search(key: str, origin: str, dest: str, day: str) -> list[dict]:
    """Ett søk i Google Flights. Returnerer reiser med pris og mellomlandinger."""
    params = {
        "engine": "google_flights", "type": 2,           # 2 = enveis
        "departure_id": _airports(origin, True),
        "arrival_id": _airports(dest, False),
        "outbound_date": day, "currency": "NOK", "hl": "no", "gl": "no",
        "api_key": key,
    }
    req = urllib.request.Request(f"{URL}?{urllib.parse.urlencode(params)}",
                                 headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        if e.code == 429 or "run out of searches" in body.lower():
            raise OutOfSearches(body[:200]) from e
        raise RuntimeError(f"SerpApi HTTP {e.code}: {body[:200]}") from e
    if data.get("error"):
        if "run out" in data["error"].lower():
            raise OutOfSearches(data["error"])
        # «ingen resultater» er et gyldig svar (og teller som søk hos SerpApi)
        if "hasn't returned any results" not in data["error"]:
            raise RuntimeError(f"SerpApi: {data['error']}")
    trips = []
    for t in data.get("best_flights", []) + data.get("other_flights", []):
        if "price" not in t:
            continue
        trips.append({
            "price": t["price"],
            "layovers": [l.get("id") for l in t.get("layovers", [])],
            "airline": ", ".join(sorted({f.get("airline", "?") for f in t.get("flights", [])})),
        })
    return trips


def _budget(con, today: date) -> int:
    """Søk vi kan bruke nå: det som er igjen av måneden, fordelt jevnt på dagene som er igjen."""
    month = today.strftime("%Y-%m")
    used_month = db.usage_month(con, month)
    used_today = db.usage_day(con, today.isoformat())
    days_left = calendar.monthrange(today.year, today.month)[1] - today.day + 1
    left_at_day_start = config.SERPAPI_MONTHLY_LIMIT - (used_month - used_today)
    allowance_today = math.ceil(max(left_at_day_start, 0) / days_left)
    return max(0, min(allowance_today - used_today, config.SERPAPI_MONTHLY_LIMIT - used_month))


def _key(d: dict) -> str:
    if d["type"] == "skjult_by":
        return f"skjult|{d['origin']}|{d['hub']}|{d['destination']}|{d['date']}"
    return f"feil|{d['origin']}|{d['destination']}|{d['date']}"


def _priority(d: dict) -> tuple:
    tier = config.VERIFY_PRIORITY.get(d["origin"], 9)
    size = d["discount_pct"] if d["type"] == "feilpris" else round(100 * d["savings"] / d["hub_price"])
    return (tier, -size)


def run(con, error_fares: list[dict], hidden: list[dict]) -> dict:
    """Bekrefter treff innenfor budsjettet og legger resultatet på hvert treff (d["live"])."""
    today = date.today()
    db.prune_verifications(con, today.isoformat())
    key = os.environ.get("SERPAPI_KEY", "")
    deals = error_fares + hidden

    # Bruk tidligere resultater
    todo = []
    for d in deals:
        v = db.get_verification(con, _key(d))
        if v:
            d["live"] = v
        else:
            d["live"] = None
            todo.append(d)

    month = today.strftime("%Y-%m")
    info = {"enabled": bool(key), "limit": config.SERPAPI_MONTHLY_LIMIT,
            "used_month": db.usage_month(con, month), "checked_now": 0, "waiting": len(todo)}
    if not key or not todo:
        return info

    budget = _budget(con, today)
    now = datetime.now(timezone.utc).isoformat(timespec="minutes")
    for d in sorted(todo, key=_priority):
        cost = 2 if d["type"] == "skjult_by" else 1
        if cost > budget:
            if budget == 0:
                break
            continue                      # for dyrt akkurat nå – prøv et billigere treff
        try:
            if d["type"] == "feilpris":
                status, data = _verify_error_fare(key, con, d, today)
            else:
                status, data = _verify_hidden(key, con, d, today)
        except OutOfSearches as e:
            print(f"  SerpApi: tom for søk ({e})")
            break
        except Exception as e:            # én feil skal ikke stoppe resten
            print(f"  ! bekreftelse {_key(d)}: {e}")
            continue
        budget -= cost
        info["checked_now"] += 1
        db.save_verification(con, _key(d), d["date"], now, status, data)
        d["live"] = {"status": status, **data, "checked_at": now}
        if d["type"] == "skjult_by" and status == "bekreftet":
            d["via_verified"] = True

    info["used_month"] = db.usage_month(con, month)
    info["waiting"] = sum(1 for d in deals if d["live"] is None)
    return info


def _counted_search(key, con, today, *args):
    trips = _search(key, *args)
    db.add_usage(con, today.isoformat())
    return trips


def _verify_error_fare(key, con, d, today):
    trips = _counted_search(key, con, today, d["origin"], d["destination"], d["date"])
    if not trips:
        return "ikke_funnet", {"price": None}
    best = min(trips, key=lambda t: t["price"])
    ok = best["price"] <= d["price"] * config.VERIFY_PRICE_TOLERANCE
    return ("bekreftet" if ok else "endret"), {"price": best["price"], "airline": best["airline"]}


def _verify_hidden(key, con, d, today):
    hubs = config.HUB_AIRPORTS.get(d["hub"], {d["hub"]})
    via = _counted_search(key, con, today, d["origin"], d["destination"], d["date"])
    via = [t for t in via if any(l in hubs for l in t["layovers"])]
    direct = _counted_search(key, con, today, d["origin"], d["hub"], d["date"])
    if not via or not direct:
        return "ikke_funnet", {"price": min((t["price"] for t in via), default=None),
                               "hub_price": min((t["price"] for t in direct), default=None)}
    best = min(via, key=lambda t: t["price"])
    hub_price = min(t["price"] for t in direct)
    savings = hub_price - best["price"]
    ok = savings >= config.MIN_HIDDEN_CITY_SAVINGS
    return ("bekreftet" if ok else "endret"), {
        "price": best["price"], "hub_price": hub_price, "savings": savings,
        "airline": best["airline"], "via": [l for l in best["layovers"]]}
