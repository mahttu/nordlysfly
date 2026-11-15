"""Innstillinger for feilpris-finneren."""

# Avreiseflyplasser (Nord-Norge)
ORIGINS = {
    "BOO": "Bodø",
    "EVE": "Harstad/Narvik (Evenes)",
    "TOS": "Tromsø",
}

# Steder folk oftest egentlig vil til. «Skjult by»-sjekken ser etter
# billetter som går VIA disse og videre, men er billigere enn å fly hit.
HUBS = {
    "OSL": "Oslo",
    "TRD": "Trondheim",
    "BGO": "Bergen",
}

# Destinasjoner lenger unna (bykoder: LON = alle London-flyplasser osv.)
BEYOND = {
    "LON": "London",
    "CPH": "København",
    "ARN": "Stockholm",
    "AMS": "Amsterdam",
    "BER": "Berlin",
    "PAR": "Paris",
    "BCN": "Barcelona",
    "ROM": "Roma",
    "ALC": "Alicante",
    "AGP": "Málaga",
    "NYC": "New York",
    "BKK": "Bangkok",
}

# Koordinater (brukes til å regne ut kr per km)
COORDS = {
    "BOO": (67.27, 14.37), "EVE": (68.49, 16.68), "TOS": (69.68, 18.92),
    "OSL": (60.19, 11.10), "TRD": (63.46, 10.92), "BGO": (60.29, 5.22),
    "LON": (51.47, -0.45), "CPH": (55.62, 12.65), "ARN": (59.65, 17.92),
    "AMS": (52.31, 4.76), "BER": (52.36, 13.50), "PAR": (49.01, 2.55),
    "BCN": (41.30, 2.08), "ROM": (41.80, 12.25), "ALC": (38.28, -0.56),
    "AGP": (36.67, -4.50), "NYC": (40.64, -73.78), "BKK": (13.69, 100.75),
    "SVG": (58.88, 5.64), "LPA": (27.93, -15.39), "GDN": (54.38, 18.47),
    "KRK": (50.08, 19.78), "HEL": (60.32, 24.95),
}

CURRENCY = "nok"
MONTHS_AHEAD = 3            # hvor mange måneder fram i tid det søkes

# Feilpris: pris må være under denne andelen av normalprisen (0.5 = 50 % rabatt)
ERROR_FARE_RATIO = 0.5
MIN_OBSERVATIONS = 8        # minst så mange priser på ruten før vi stoler på normalprisen
HISTORY_DAYS = 30           # normalpris = median av priser hentet siste N dager; eldre priser slettes

# Når API-et ikke oppgir mellomlanding, antar vi denne (nesten alt fra Nord-Norge går via Oslo)
DEFAULT_HUB = "OSL"

# Skjult by: minste besparelse i kroner for å vise et treff
MIN_HIDDEN_CITY_SAVINGS = 150

# Live-bekreftelse av treff via Google Flights (SerpApi). Krever SERPAPI_KEY.
SERPAPI_MONTHLY_LIMIT = 250          # maks søk per kalendermåned (gratisplanen)
# Nord-Norge hentes fra Google Utforsk (1 søk per flyplass per dag), i denne rekkefølgen
EXPLORE_ORIGINS = ["EVE", "BOO", "TOS"]
# Rekkefølge når det er flere treff enn søk igjen: lavest tall sjekkes først
VERIFY_PRIORITY = {"EVE": 1, "BOO": 1, "TOS": 2}
VERIFY_PRICE_TOLERANCE = 1.15        # bekreftet hvis live pris er maks 15 % over oppgitt pris
# Bykoder fra Travelpayouts → flyplasser i Google Flights
CITY_AIRPORTS = {
    "LON": "LHR,LGW,STN,LTN,LCY,SEN",
    "PAR": "CDG,ORY,BVA",
    "ROM": "FCO,CIA",
    "NYC": "JFK,EWR,LGA",
    "OSL": "OSL,TRF,RYG",            # som reisemål fra Nord-Norge er Torp/Rygge greit
}
# Flyplasser som teller som «går via» hver hub
HUB_AIRPORTS = {"OSL": {"OSL", "TRF", "RYG"}, "TRD": {"TRD"}, "BGO": {"BGO"}}

DB_PATH = "priser.sqlite"
SITE_DIR = "site"
