"""Henter priser fra Nord-Norge med Google Travel Explore (via SerpApi).

Travelpayouts har svært få lagrede priser fra Bodø, Evenes og Tromsø. Ett Utforsk-søk
gir billigste enveispris (neste 6 måneder) til mange reisemål fra én flyplass.
Hver flyplass i config.EXPLORE_ORIGINS søkes maks én gang per dag, i prioritert rekkefølge,
innenfor samme månedsbudsjett som bekreftelsene (verify.py).
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone

import config
import db
import verify
from providers import Offer

PROVIDER = "google"


def _city(code: str) -> str:
    """Flyplasskode → vår kode (LHR → LON, TRF → OSL osv.)."""
    for city, airports in config.CITY_AIRPORTS.items():
        if code in airports.split(","):
            return city
    return code


def _search(key: str, origin: str) -> list[dict]:
    params = {
        "engine": "google_travel_explore", "departure_id": origin,
        "type": 2, "month": 0, "travel_mode": 1,          # enveis, neste 6 mnd, bare fly
        "currency": "NOK", "hl": "no", "gl": "no", "api_key": key,
    }
    req = urllib.request.Request(f"{verify.URL}?{urllib.parse.urlencode(params)}",
                                 headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        if e.code == 429 or "run out of searches" in body.lower():
            raise verify.OutOfSearches(body[:200]) from e
        raise RuntimeError(f"SerpApi HTTP {e.code}: {body[:200]}") from e
    if data.get("error"):
        if "run out" in data["error"].lower():
            raise verify.OutOfSearches(data["error"])
        if "hasn't returned any results" not in data["error"]:
            raise RuntimeError(f"SerpApi: {data['error']}")
    return data.get("destinations", [])


def _to_offers(origin: str, dests: list[dict], today: str) -> tuple[list[Offer], dict]:
    offers, names, best = [], {}, {}
    for d in dests:
        airport = (d.get("destination_airport") or {}).get("code")
        price, day = d.get("flight_price"), d.get("start_date")
        if not airport or price is None or not day or day < today:
            continue
        code = _city(airport)
        if code == origin:
            continue
        names.setdefault(code, d.get("name") or code)
        o = Offer(origin=origin, destination=code, depart_date=day, price=float(price),
                  currency="NOK", airline=d.get("airline") or d.get("airline_code") or "?",
                  transfers=int(d.get("number_of_stops") or 0), via=None,
                  link=d.get("link") or "", provider=PROVIDER, origin_airport=origin)
        if code not in best or o.price < best[code].price:   # flere flyplasser i samme by
            best[code] = o
    offers = list(best.values())
    return offers, names


def fetch(con) -> tuple[list[Offer], list[Offer], dict]:
    """Returnerer (nye tilbud som skal lagres, dagens tidligere tilbud, info)."""
    key = os.environ.get("SERPAPI_KEY", "")
    today = date.today()
    info = {"searched": [], "reused": [], "skipped": []}
    if not key:
        return [], [], info
    new, reused = [], []
    for origin in config.EXPLORE_ORIGINS:
        if db.explore_done(con, today.isoformat(), origin):
            reused += db.explore_offers_today(con, origin, today.isoformat())
            info["reused"].append(origin)
            continue
        if verify._budget(con, today) < 1:
            info["skipped"].append(origin)
            continue
        try:
            dests = _search(key, origin)
        except verify.OutOfSearches as e:
            print(f"  SerpApi: tom for søk ({e})")
            info["skipped"] += [o for o in config.EXPLORE_ORIGINS if o not in info["searched"]
                                and o not in info["reused"] and o not in info["skipped"]]
            break
        except Exception as e:
            print(f"  ! Utforsk {origin}: {e}")
            info["skipped"].append(origin)
            continue
        db.add_usage(con, today.isoformat())
        db.mark_explore(con, today.isoformat(), origin)
        offers, names = _to_offers(origin, dests, today.isoformat())
        db.save_names(con, names)
        new += offers
        info["searched"].append(origin)
    return new, reused, info
