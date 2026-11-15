# Nordlys Fly – feilpris-finner for Nord-Norge

Finner to typer billige billetter fra **Bodø (BOO)**, **Evenes (EVE)** og **Tromsø (TOS)**:

1. **Feilpriser** – priser langt under normalprisen på ruten (standard: 50 % eller mer under medianen).
2. **Skjult by** – billetten til f.eks. London via Oslo er billigere enn billetten til Oslo
   samme dag. Man bestiller til London og går av i Oslo.
3. **Fra Oslo** – billigste pris på de 20 mest populære reisene fra Oslo (OSL). Disse rutene
   sjekkes også for feilpriser.

Hver pris viser om den har gått **ned (grønn ▼)** eller **opp (rød ▲)** siden forrige prissjekk.

Ingen ekstra pakker trengs, bare Python 3.10+.

## Kom i gang (testdata)

```bash
python run.py
```
Åpne `site/index.html` i nettleseren.

## Koble til ekte priser (API-nøkkel)

1. Lag en gratis konto på **travelpayouts.com** og bli med i Aviasales-programmet.
2. Finn nøkkelen i profilen din (**API token**, under API-innstillingene) (og eventuelt partner-ID-en din, «marker»).
3. Kopier `.env.example` til `.env` og lim inn nøkkelen:
   ```
   PROVIDER=travelpayouts
   TRAVELPAYOUTS_TOKEN=din_nøkkel
   ```
4. Kjør `python run.py`.

`.env` står i `.gitignore` – nøkkelen skal aldri inn i koden eller på GitHub.
Koden sender nøkkelen i en HTTP-header (`X-Access-Token`), ikke i URL-en.

### Kjøre automatisk hver time (gratis på GitHub)

1. Last opp mappen til et GitHub-repo.
2. **Settings → Secrets and variables → Actions → New repository secret**: `TRAVELPAYOUTS_TOKEN`.
3. **Settings → Pages → Source: GitHub Actions**.
4. `.github/workflows/oppdater.yml` henter priser hver time og publiserer siden.

## Slik virker det

| Fil | Gjør |
|---|---|
| `config.py` | Flyplasser, destinasjoner, Oslo-topp 20 og terskler |
| `providers.py` | Henter priser (testdata eller Travelpayouts) |
| `db.py` | Lagrer all prishistorikk i SQLite |
| `detect.py` | Finner feilpriser og skjult by |
| `site_builder.py` | Lager nettsiden |
| `run.py` | Kjører alt |

**Normalpris** = median av alle priser på ruten hentet de siste 30 dagene. Priser eldre enn
30 dager slettes automatisk, så databasen ikke vokser uendelig. Den blir mer
presis jo lenger systemet har kjørt – de første dagene sammenlignes datoer innenfor samme søk.

## Viktige begrensninger

- Travelpayouts-prisene er **bufret** fra ekte søk de siste dagene, ikke live. Sjekk alltid prisen før du varsler.
- Travelpayouts oppgir ikke hvor det mellomlandes. Skjult by-treff herfra merkes «Sjekk at den går via OSL».
  Fra Nord-Norge går nesten alt via Oslo, men noen ganger via Trondheim, Stockholm eller København.
- Skjult by: bare enveis, bare håndbagasje, og flyselskapene forbyr det i vilkårene sine
  (de kan i verste fall slette bonuspoeng). Hopper du over en etappe, kanselleres resten av billetten.

## Ideer videre

- Telegram-bot eller e-postvarsel når et nytt treff dukker opp
- Duffel API for live priser med eksakte mellomlandinger
- Flere avreiseflyplasser (legg dem i `ORIGINS` og `COORDS`)
