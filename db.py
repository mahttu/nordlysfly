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
CREATE TABLE IF NOT EXISTS explore_runs (day TEXT, origin TEXT, PRIMARY KEY (day, origin));
CREATE TABLE IF NOT EXISTS place_names (code TEXT PRIMARY KEY, name TEXT);
CREATE TABLE IF NOT EXISTS serpapi_usage (day TEXT PRIMARY KEY, n INTEGER);
CREATE TABLE IF NOT EXISTS verifications (
    key TEXT PRIMARY KEY, depart_date TEXT, checked_at TEXT, status TEXT, data TEXT
);
CREATE INDEX IF NOT EXISTS idx_key ON observations (origin, destination, depart_date, fetched_at);
"""


def connect(path: str) -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    cols = [r[1] for r in con.execute("PRAGMA table_info(observations)")]
    if "origin_airport" not in cols:
        con.execute("ALTER TABLE observations ADD COLUMN origin_airport TEXT")
    if con.execute("PRAGMA user_version").fetchone()[0] < 2:
        # Versjon 2: Oslo-priser lagret før dette kan være fra Torp/Rygge – slett dem
        con.execute("DELETE FROM observations WHERE origin='OSL'")
        con.execute("PRAGMA user_version = 2")
        con.commit()
    if con.execute("PRAGMA user_version").fetchone()[0] < 3:
        # Versjon 3: avganger fra Oslo er fjernet – slett dem
        con.execute("DELETE FROM observations WHERE origin='OSL'")
        con.execute("PRAGMA user_version = 3")
        con.commit()
    return con


def save(con: sqlite3.Connection, offers: list[Offer]) -> None:
    con.executemany(
        "INSERT INTO observations (origin, destination, depart_date, price, currency, airline,"
        " transfers, via, link, provider, fetched_at, origin_airport) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        [(o.origin, o.destination, o.depart_date, o.price, o.currency, o.airline, o.transfers,
          json.dumps(o.via) if o.via is not None else None, o.link, o.provider, o.fetched_at,
          o.origin_airport)
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


# ---------- SerpApi-forbruk og bekreftelser ----------
def usage_month(con: sqlite3.Connection, month: str) -> int:
    return con.execute("SELECT COALESCE(SUM(n),0) FROM serpapi_usage WHERE day LIKE ?",
                       (month + "%",)).fetchone()[0]


def usage_day(con: sqlite3.Connection, day: str) -> int:
    r = con.execute("SELECT n FROM serpapi_usage WHERE day=?", (day,)).fetchone()
    return r[0] if r else 0


def add_usage(con: sqlite3.Connection, day: str, n: int = 1) -> None:
    con.execute("INSERT INTO serpapi_usage(day, n) VALUES(?, ?) "
                "ON CONFLICT(day) DO UPDATE SET n = n + excluded.n", (day, n))
    con.commit()


def get_verification(con: sqlite3.Connection, key: str) -> dict | None:
    r = con.execute("SELECT status, data, checked_at FROM verifications WHERE key=?", (key,)).fetchone()
    if not r:
        return None
    return {"status": r[0], **json.loads(r[1]), "checked_at": r[2]}


def save_verification(con: sqlite3.Connection, key: str, depart_date: str,
                      checked_at: str, status: str, data: dict) -> None:
    con.execute("INSERT OR REPLACE INTO verifications VALUES (?,?,?,?,?)",
                (key, depart_date, checked_at, status, json.dumps(data)))
    con.commit()


def prune_verifications(con: sqlite3.Connection, today: str) -> None:
    con.execute("DELETE FROM verifications WHERE depart_date < ?", (today,))
    con.commit()


# ---------- Google Utforsk ----------
def explore_done(con: sqlite3.Connection, day: str, origin: str) -> bool:
    return con.execute("SELECT 1 FROM explore_runs WHERE day=? AND origin=?",
                       (day, origin)).fetchone() is not None


def mark_explore(con: sqlite3.Connection, day: str, origin: str) -> None:
    con.execute("INSERT OR IGNORE INTO explore_runs VALUES (?, ?)", (day, origin))
    con.commit()


def explore_offers_today(con: sqlite3.Connection, origin: str, day: str) -> list[Offer]:
    """Utforsk-priser hentet tidligere i dag (gjenbrukes uten nytt søk)."""
    rows = con.execute(
        "SELECT origin, destination, depart_date, price, currency, airline, transfers, link,"
        " provider, origin_airport, fetched_at FROM observations"
        " WHERE provider='google' AND origin=? AND substr(fetched_at,1,10)=? AND depart_date>=?",
        (origin, day, day)).fetchall()
    return [Offer(r[0], r[1], r[2], r[3], r[4], r[5], r[6], None, r[7], r[8], r[9], r[10])
            for r in rows]


def save_names(con: sqlite3.Connection, names: dict) -> None:
    con.executemany("INSERT OR REPLACE INTO place_names VALUES (?, ?)", names.items())
    con.commit()


def all_names(con: sqlite3.Connection) -> dict:
    return dict(con.execute("SELECT code, name FROM place_names"))
