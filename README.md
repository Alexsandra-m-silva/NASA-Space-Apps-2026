# Climate Sentinel

NASA Space Apps Challenge 2026. Surface change in Brazil's semi-arid, read from satellite series and shown as risk, impact, the cost of waiting, and regeneration.

The public site is the Next.js app in `platform/`. The API serves precomputed results. Nothing is calculated in the browser, and opening the site does not need an Earthdata login.

## What is on the site

| Route | What it is |
| --- | --- |
| `/` and `/about` | Project story: from a radar signal to the cost of inaction and regeneration |
| `/explore` | Territories, trend, risk, impact, and the cost of waiting |
| `/comparar/` | Pick a municipality, draw a box: NDVI with rainfall removed, NISAR, rain, and temperature |
| `/newsletter` | Email when the chosen territory changes |
| `/docs` | Interactive API docs |

## Data behind the numbers

| Role | Source | What we use it for |
| --- | --- | --- |
| Vegetation trend | MODIS MOD13Q1, 2001–2024 | NDVI with rainfall removed (RESTREND) and a Mann-Kendall test |
| Rain | CHIRPS | The rainfall term in RESTREND, and the climate series |
| Temperature | ERA5-Land | Climate context for the same municipalities |
| Land cover | MapBiomas Collection 10 | Class and cover context. A class change is not, by itself, desertification |
| Radar check | NISAR L2 GCOV | Dry-season 2026 passes only. It checks the regional signal; it is not a multi-year trend |

Degradation of vegetation is not the same as proven desertification. NISAR has no years before 2026 over this area. Two dates are not a trend.

## Run it

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up --build -d
```

Open `http://localhost:8090`. Deploy steps are in `docs/DEPLOY_EASYPANEL.md`.

The on-page chat calls the API. The key stays in `.env`, never in the browser:

```
FOUNDRY_API_KEY=
FOUNDRY_ENDPOINT=
FOUNDRY_MODEL=
```

Optional, and not required to open the site: `GEMINI_API_KEY` for the recommendation agent (`docs/DESERT_SENTINEL.md`), and Earthdata plus a Google Earth Engine project to rerun the pipeline (`docs/MODELO.md`).

## Repo map

| Path | Contents |
| --- | --- |
| `platform/` | Climate Sentinel interface |
| `app/` | Read-only API, database publish step, recommendation agent |
| `pipeline/` | MODIS, NISAR, climate, MapBiomas, and the susceptibility model |
| `web/` | Earlier static pages (compare, municipalities, NISAR scenes) |
| `docs/` | Deploy, model, datasets, and limits |
