"""Henter priser, finner feilpriser og skjult by-billetter, og bygger nettsiden.

Bruk:
    python run.py                       # testdata
    python run.py --provider travelpayouts
"""
import argparse
import json
import os
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import config
import db
import detect
import site_builder
import verify
import explore
from providers import get_provider


def load_env(path: str = ".env") -> None:
    """Leser NØKKEL=verdi fra .env inn i miljøvariabler (uten ekstra pakker)."""
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def months_ahead(n: int) -> list[str]:
    t = date.today()
    return [f"{t.year + (t.month - 1 + i) // 12}-{(t.month - 1 + i) % 12 + 1:02d}" for i in range(n)]


def main() -> None:
    load_env()
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default=os.environ.get("PROVIDER", "mock"),
                    choices=["mock", "travelpayouts"])
    ap.add_argument("--months", type=int, default=config.MONTHS_AHEAD)
    args = ap.parse_args()

    provider = get_provider(args.provider)
    con = db.connect(config.DB_PATH)
    destinations = list(config.HUBS) + list(config.BEYOND)
    routes = [(o, d) for o in config.ORIGINS for d in destinations]
    # Alle priser i én kjøring får samme tidsstempel, så vi kan sammenligne med forrige henting
    run_ts = datetime.now(timezone.utc).isoformat(timespec="seconds")

    offers = []
    for origin, dest in routes:
        for month in months_ahead(args.months):
            try:
                offers += provider.search(origin, dest, month)
            except Exception as e:  # én rute som feiler skal ikke stoppe resten
                print(f"  ! {origin}-{dest} {month}: {e}")
                if "API-nøkkelen ble avvist" in str(e):
                    sys.exit(str(e))   # ingen vits å prøve de andre rutene
            if args.provider != "mock":
                time.sleep(0.3)     # snill mot API-et
    today = date.today().isoformat()
    offers = [o for o in offers if o.depart_date >= today]   # bufrede priser kan være passert
    print(f"Hentet {len(offers)} priser fra {provider.name}")
    # Nord-Norge: Google Utforsk (maks ett søk per flyplass per dag)
    g_new, g_reused, g_info = explore.fetch(con)
    if g_info["searched"] or g_info["reused"] or g_info["skipped"]:
        print(f"Google Utforsk: {len(g_new)} nye priser fra {', '.join(g_info['searched']) or '–'}, "
              f"gjenbrukt fra i dag: {', '.join(g_info['reused']) or '–'}, "
              f"hoppet over: {', '.join(g_info['skipped']) or '–'}")
    offers += g_new
    for o in offers:
        o.fetched_at = run_ts
    to_save = offers
    offers = offers + g_reused            # dagens tidligere Utforsk-priser lagres ikke på nytt
    if not offers:
        # Typisk feil nøkkel eller API-et er nede. Avbryt, så den forrige siden
        # og prishistorikken ikke blir erstattet med en tom versjon.
        sys.exit("Fikk ingen priser – avbryter uten å oppdatere siden.")

    db.save(con, to_save)
    db.prune(con, config.HISTORY_DAYS)
    error_fares = detect.find_error_fares(con, offers)
    hidden = detect.find_hidden_city(offers)
    detect.add_trend(con, error_fares, run_ts)
    detect.add_trend(con, hidden, run_ts)
    search = detect.search_index(con, offers, run_ts)
    live = verify.run(con, error_fares, hidden)
    if live["enabled"]:
        print(f"SerpApi: sjekket {live['checked_now']} treff nå, "
              f"{live['used_month']}/{live['limit']} søk brukt denne måneden, {live['waiting']} venter")
    print(f"Fant {len(error_fares)} mulige feilpriser og {len(hidden)} skjult by-billetter")

    result = {
        "updated": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "provider": provider.name,
        "origins": config.ORIGINS,
        "names": {**db.all_names(con), **config.ORIGINS, **config.HUBS, **config.BEYOND},
        "error_fares": error_fares,
        "hidden_city": hidden,
        "search": search,
        "live": live,
        "marker": os.environ.get("TRAVELPAYOUTS_MARKER") or None,
    }
    Path(config.SITE_DIR).mkdir(exist_ok=True)
    Path(config.SITE_DIR, "deals.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    site_builder.build(result, Path(config.SITE_DIR, "index.html"))
    print(f"Nettside skrevet til {config.SITE_DIR}/index.html")


if __name__ == "__main__":
    main()
