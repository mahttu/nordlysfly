"""Prisleverandører. Alle returnerer en liste med Offer.

- MockProvider:          testdata, trenger ingen nøkkel
- TravelpayoutsProvider: ekte (bufrede) priser fra Aviasales/Travelpayouts
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

import config


@dataclass
class Offer:
    origin: str
    destination: str
    depart_date: str            # YYYY-MM-DD
    price: float
    currency: str
    airline: str
    transfers: int
    via: list[str] | None       # mellomlandinger hvis kjent, ellers None
    link: str
    provider: str
    origin_airport: str | None = None   # faktisk avreiseflyplass, f.eks. OSL eller TRF
    fetched_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))


def distance_km(a: str, b: str) -> float:
    (lat1, lon1), (lat2, lon2) = config.COORDS[a], config.COORDS[b]
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


# --------------------------------------------------------------------------
# Travelpayouts (Aviasales)
# --------------------------------------------------------------------------
class TravelpayoutsProvider:
    """Bruker Aviasales Data API v3 «prices_for_dates».

    Prisene er bufret fra ekte søk de siste dagene, så de må alltid
    sjekkes på nytt før de publiseres som feilpris.
    API-et oppgir ikke hvilken flyplass det mellomlandes på (via=None),
    derfor merkes «skjult by»-treff herfra som «må sjekkes».
    """
    URL = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"
    name = "travelpayouts"

    def __init__(self, token: str, marker: str | None = None):
        if not token:
            raise ValueError("Mangler TRAVELPAYOUTS_TOKEN (se .env.example)")
        self.token = token
        self.marker = marker

    def search(self, origin: str, destination: str, month: str) -> list[Offer]:
        params = {
            "origin": origin,
            "destination": destination,
            "departure_at": month,       # YYYY-MM gir hele måneden
            "one_way": "true",
            "direct": "false",
            "sorting": "price",
            "currency": config.CURRENCY,
            "limit": 1000,
        }
        url = f"{self.URL}?{urllib.parse.urlencode(params)}"
        # Nøkkelen sendes i en header, ikke i URL-en, så den ikke havner i logger.
        req = urllib.request.Request(url, headers={
            "X-Access-Token": self.token,
            "Accept": "application/json",
        })
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    payload = json.load(resp)
                break
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < 2:   # for mange kall, vent litt
                    time.sleep(2 * (attempt + 1))
                    continue
                if e.code in (401, 403):
                    raise RuntimeError("API-nøkkelen ble avvist – sjekk TRAVELPAYOUTS_TOKEN") from e
                raise
        if not payload.get("success", False):
            raise RuntimeError(f"Feil fra Travelpayouts: {payload.get('error')}")

        offers = []
        for row in payload.get("data", []):
            link = "https://www.aviasales.com" + row.get("link", "")
            if self.marker:
                link += ("&" if "?" in link else "?") + f"marker={self.marker}"
            offers.append(Offer(
                origin=origin,
                destination=destination,
                depart_date=row["departure_at"][:10],
                price=float(row["price"]),
                currency=config.CURRENCY.upper(),
                airline=row.get("airline", "?"),
                transfers=int(row.get("transfers", 0)),
                via=None,
                link=link,
                provider=self.name,
                origin_airport=row.get("origin_airport"),
            ))
        return offers


# --------------------------------------------------------------------------
# Testdata
# --------------------------------------------------------------------------
class MockProvider:
    """Lager realistiske, deterministiske priser med noen innplantede
    feilpriser og skjult by-billetter, så hele løypa kan testes uten nøkkel."""
    name = "mock"
    AIRLINES = ["SK", "DY", "WF"]

    def __init__(self, seed: int = 42):
        self.seed = seed

    def _rng(self, *parts) -> random.Random:
        key = "|".join(map(str, (self.seed, *parts)))
        return random.Random(int(hashlib.md5(key.encode()).hexdigest()[:12], 16))

    def _leg_price(self, a: str, b: str, d: date) -> float:
        km = distance_km(a, b)
        base = 450 + 0.75 * km if km < 3000 else 1200 + 0.45 * km
        season = 1.35 if d.month in (6, 7, 12) else 1.0
        weekday = 1.15 if d.weekday() in (4, 6) else 1.0
        # Liten endring fra time til time, så testdata også viser pris opp/ned
        hour = datetime.now(timezone.utc).strftime("%Y%m%d%H")
        drift = self._rng("drift", a, b, d, hour).uniform(0.93, 1.07)
        return base * season * weekday * drift * self._rng("leg", a, b, d).uniform(0.8, 1.3)

    def _hub_for(self, origin: str, dest: str) -> str:
        # Det aller meste fra Nord-Norge går via Oslo
        return "TRD" if self._rng("hub", origin, dest).random() < 0.1 else "OSL"

    def search(self, origin: str, destination: str, month: str) -> list[Offer]:
        y, m = map(int, month.split("-"))
        d = date(y, m, 1)
        offers = []
        while d.month == m:
            if d >= date.today():
                r = self._rng("offer", origin, destination, d)
                airline = r.choice(self.AIRLINES)
                if destination in config.HUBS or origin in config.HUBS:
                    price, via, transfers = self._leg_price(origin, destination, d), [], 0
                else:
                    hub = self._hub_for(origin, destination)
                    hub_price = self._leg_price(origin, hub, d)
                    price = hub_price + 0.85 * self._leg_price(hub, destination, d)
                    via, transfers = [hub], 1
                    if r.random() < 0.012:    # innplantet skjult by
                        price = hub_price * r.uniform(0.55, 0.8)
                if r.random() < 0.004:        # innplantet feilpris
                    price *= r.uniform(0.15, 0.35)
                airport = origin
                if origin == "OSL" and r.random() < 0.25:   # noen avganger fra Torp
                    airport, price, airline = "TRF", price * 0.6, "FR"
                q = urllib.parse.urlencode({"o": origin, "d": destination, "date": d.isoformat()})
                offers.append(Offer(origin, destination, d.isoformat(), round(price),
                                    "NOK", airline, transfers, via,
                                    f"https://example.com/sok?{q}", self.name, airport))
            d += timedelta(days=1)
        return offers


def get_provider(name: str):
    if name == "mock":
        return MockProvider()
    if name == "travelpayouts":
        return TravelpayoutsProvider(os.environ.get("TRAVELPAYOUTS_TOKEN", ""),
                                     os.environ.get("TRAVELPAYOUTS_MARKER") or None)
    raise ValueError(f"Ukjent leverandør: {name}")
