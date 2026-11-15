"""Lagrer alle prisobservasjoner i SQLite, så normalprisen blir bedre over tid."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone

from providers import Offer

SCHEMA = """
CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY,
    origin TEXT, destination TEXT, depart_date TEXT,
    price REAL, currency TEXT, airline TEXT, transfers INTEGER,
    via TEXT, link TEXT, provider TEXT, fetched_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_route ON observations (origin, destination, fetched_at);
CREATE INDEX IF NOT EXISTS idx_key ON observations (origin, destination, depart_date, fetched_at);
"""


def connect(path: str) -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    if con.execute("PRAGMA user_version").fetchone()[0] < 2:
        # Versjon 2: Oslo-priser lagret før dette kan være fra Torp/Rygge – slett dem
        con.execute("DELETE FROM observations WHERE origin='OSL'")
        con.execute("PRAGMA user_version = 2")
        con.commit()
    return con


def save(con: sqlite3.Connection, offers: list[Offer]) -> None:
    con.executemany(
        "INSERT INTO observations (origin, destination, depart_date, price, currency, airline,"
        " transfers, via, link, provider, fetched_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [(o.origin, o.destination, o.depart_date, o.price, o.currency, o.airline, o.transfers,
          json.dumps(o.via) if o.via is not None else None, o.link, o.provider, o.fetched_at)
         for o in offers])
    con.commit()


def prune(con: sqlite3.Connection, days: int) -> int:
    """Sletter observasjoner eldre enn `days` dager, så databasen ikke vokser uendelig."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")
    n = con.execute("DELETE FROM observations WHERE fetched_at < ?", (since,)).rowcount
    con.commit()
    if n:
        con.execute("VACUUM")
    return n


def route_prices(con: sqlite3.Connection, origin: str, destination: str, days: int) -> list[float]:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")
    rows = con.execute(
        "SELECT price FROM observations WHERE origin=? AND destination=? AND fetched_at>=?",
        (origin, destination, since))
    return [r[0] for r in rows]


def _window_start(ts: str, minutes: int = 30) -> str:
    """Én henting tar noen minutter; priser innenfor dette vinduet regnes som samme henting."""
    return (datetime.fromisoformat(ts) - timedelta(minutes=minutes)).isoformat(timespec="seconds")


def previous_price(con: sqlite3.Connection, origin: str, destination: str,
                   depart_date: str, before: str) -> float | None:
    """Billigste pris for samme rute og dato ved forrige henting (før `before`)."""
    last = con.execute(
        "SELECT MAX(fetched_at) FROM observations WHERE origin=? AND destination=?"
        " AND depart_date=? AND fetched_at<?", (origin, destination, depart_date, before)).fetchone()[0]
    if not last:
        return None
    return con.execute(
        "SELECT MIN(price) FROM observations WHERE origin=? AND destination=? AND depart_date=?"
        " AND fetched_at BETWEEN ? AND ?",
        (origin, destination, depart_date, _window_start(last), last)).fetchone()[0]


def previous_route_min(con: sqlite3.Connection, origin: str, destination: str,
                       before: str, from_date: str) -> float | None:
    """Billigste pris på hele ruten (avganger fra og med `from_date`) ved forrige henting."""
    last = con.execute(
        "SELECT MAX(fetched_at) FROM observations WHERE origin=? AND destination=? AND fetched_at<?",
        (origin, destination, before)).fetchone()[0]
    if not last:
        return None
    return con.execute(
        "SELECT MIN(price) FROM observations WHERE origin=? AND destination=? AND depart_date>=?"
        " AND fetched_at BETWEEN ? AND ?",
        (origin, destination, from_date, _window_start(last), last)).fetchone()[0]


def previous_run_prices(con: sqlite3.Connection, before: str) -> dict:
    """Billigste pris per (rute, dato) ved forrige henting, hentet i én spørring."""
    last = con.execute("SELECT MAX(fetched_at) FROM observations WHERE fetched_at<?",
                       (before,)).fetchone()[0]
    if not last:
        return {}
    rows = con.execute(
        "SELECT origin, destination, depart_date, MIN(price) FROM observations"
        " WHERE fetched_at BETWEEN ? AND ? GROUP BY origin, destination, depart_date",
        (_window_start(last), last))
    return {(o, d, day): p for o, d, day, p in rows}
