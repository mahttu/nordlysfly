"""Finner feilpriser og «skjult by»-billetter."""
from collections import defaultdict
from datetime import date
from statistics import median

import config
import db
from providers import Offer, distance_km


def find_error_fares(con, offers: list[Offer]) -> list[dict]:
    """En pris er en mulig feilpris hvis den er langt under normalprisen
    (median av alle priser på samme rute hentet siste HISTORY_DAYS dager)."""
    # Samme rute/dato kan komme flere ganger (flere avganger/selskaper): behold billigste
    cheapest = {}
    for o in offers:
        k = (o.origin, o.destination, o.depart_date)
        if k not in cheapest or o.price < cheapest[k].price:
            cheapest[k] = o
    deals, baselines = [], {}
    for o in cheapest.values():
        key = (o.origin, o.destination)
        if key not in baselines:
            prices = db.route_prices(con, *key, config.HISTORY_DAYS)
            baselines[key] = median(prices) if len(prices) >= config.MIN_OBSERVATIONS else None
        normal = baselines[key]
        if normal and o.price <= normal * config.ERROR_FARE_RATIO:
            km = distance_km(o.origin, o.destination) if o.destination in config.COORDS else None
            deals.append({
                "type": "feilpris",
                "origin": o.origin, "destination": o.destination,
                "date": o.depart_date, "price": o.price, "currency": o.currency,
                "normal_price": round(normal),
                "discount_pct": round(100 * (1 - o.price / normal)),
                "kr_per_km": round(o.price / km, 2) if km else None,
                "airline": o.airline, "transfers": o.transfers,
                "link": o.link, "provider": o.provider,
            })
    return sorted(deals, key=lambda d: -d["discount_pct"])


def find_hidden_city(offers: list[Offer]) -> list[dict]:
    """Skjult by: billett O → (via HUB) → D er billigere enn O → HUB samme dag.
    Da kan man bestille til D og gå av i HUB."""
    cheapest = {}  # (origin, dest, date) -> billigste Offer
    for o in offers:
        k = (o.origin, o.destination, o.depart_date)
        if k not in cheapest or o.price < cheapest[k].price:
            cheapest[k] = o

    by_day = defaultdict(dict)
    for (orig, dest, day), o in cheapest.items():
        by_day[(orig, day)][dest] = o

    deals = []
    for (orig, day), dests in by_day.items():
        if orig not in config.ORIGINS:   # skjult by gjelder bare reiser fra Nord-Norge
            continue
        for hub in config.HUBS:
            hub_offer = dests.get(hub)
            if not hub_offer:
                continue
            for dest, o in dests.items():
                if dest in config.HUBS or o.transfers < 1:
                    continue
                savings = hub_offer.price - o.price
                if savings < config.MIN_HIDDEN_CITY_SAVINGS:
                    continue
                if o.via is not None:
                    if hub not in o.via:
                        continue          # vi vet at den ikke går via denne hubben
                    verified = True
                else:
                    # Ukjent mellomlanding: sammenlign bare med den mest sannsynlige
                    # hubben, ellers vinner hubben med høyest pris (f.eks. BGO).
                    if hub != config.DEFAULT_HUB:
                        continue
                    verified = False      # må sjekkes manuelt
                deals.append({
                    "type": "skjult_by",
                    "origin": orig, "hub": hub, "destination": dest, "date": day,
                    "price": o.price, "hub_price": hub_offer.price, "savings": round(savings),
                    "currency": o.currency, "airline": o.airline,
                    "via_verified": verified, "link": o.link, "hub_link": hub_offer.link,
                    "provider": o.provider,
                })
    # Uverifiserte treff kan komme fra flere hubber for samme billett; behold beste
    best = {}
    for d in deals:
        k = (d["origin"], d["destination"], d["date"], d["hub"] if d["via_verified"] else "?")
        if k not in best or d["savings"] > best[k]["savings"]:
            best[k] = d
    return sorted(best.values(), key=lambda d: -d["savings"])


def add_trend(con, deals: list[dict], before: str) -> None:
    """Legger til prisen ved forrige henting (prev_price), så siden kan vise opp/ned."""
    for d in deals:
        d["prev_price"] = db.previous_price(con, d["origin"], d["destination"], d["date"], before)


def search_index(con, offers: list[Offer], before: str) -> dict:
    """Billigste pris per rute og dato, til søket på nettsiden.
    Format: {"BOO-LON": {"n": normalpris, "d": {"2026-12-01": [pris, selskap, bytter, forrige]}}}"""
    prev = db.previous_run_prices(con, before)
    index = {}
    for o in offers:
        route = index.setdefault(f"{o.origin}-{o.destination}", {"n": None, "d": {}})
        cur = route["d"].get(o.depart_date)
        if cur is None or o.price < cur[0]:
            route["d"][o.depart_date] = [round(o.price), o.airline, o.transfers,
                                         prev.get((o.origin, o.destination, o.depart_date))]
    for key, route in index.items():
        prices = db.route_prices(con, *key.split("-"), config.HISTORY_DAYS)
        if len(prices) >= config.MIN_OBSERVATIONS:
            route["n"] = round(median(prices))
    return index
