# Climate Guardian — Dancing with the SARs

NASA Space Apps Challenge 2026. NISAR L-band is the core of the detection; GPM IMERG is the rainfall context.

## What is wired in

| Role | NASA product | How it enters |
| --- | --- | --- |
| Map image (today, no login) | GIBS `NISAR_L2_Geocoded_Polarimetric_Covariance` | daily GCOV mosaic, 15.6 m |
| Quantitative analysis | `NISAR_L2_GCOV_V1` (validated 6 Nov 2026) or `NISAR_L2_GCOV_PROVISIONAL_V1` | `HHHH` layer (gamma0) |
| Rain | GPM IMERG Late daily `GPM_3IMERGDL` v07 + GIBS layer `IMERG_Precipitation_Rate` | between the two SAR passes |

Calm water / flood: very low HH backscatter. Change = pixels that cross the threshold (default −18 dB) between the before/after pair, preferably on the same track and frame (12-day cycle).

## Chat about the data on screen

The avatar button opens a chat on every project page. Questions include the text and control values shown on the
current page. The browser calls the project API; the Microsoft Foundry key stays only in the server `.env`.

Set `FOUNDRY_API_KEY`, `FOUNDRY_ENDPOINT` and `FOUNDRY_MODEL` in `.env` (never in code or in the browser), then:

```bash
docker compose up --build -d     # http://localhost:8090 — click the avatar in the bottom-right corner
```

Deploy (Easypanel), the model pipeline and the Desert Sentinel agent are documented in `docs/DEPLOY_EASYPANEL.md`,
`docs/MODELO.md` and `docs/DESERT_SENTINEL.md`.

## 1. See the images now

```bash
python -m http.server 8000 --directory web
```

Open `http://localhost:8000`. The slider compares two NISAR passes over the Uruguay River at Uruguaiana (24 Oct and 5 Nov 2026, same track). Red and cyan on `web/scenes/change.png` are the calculated open-water change. Check GPM for rain.

## 2. Earthdata account (real numbers)

1. Create a login at [urs.earthdata.nasa.gov](https://urs.earthdata.nasa.gov/).
2. Copy `.env.example` to `.env` with `EARTHDATA_USERNAME` and `EARTHDATA_PASSWORD`.
3. Authorize ASF DAAC and GES DISC on the account (Applications).

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
set -a && source .env && set +a
python -m pipeline.fetch_nisar              # list the GCOV pair
python -m pipeline.fetch_gpm
python -m pipeline.fetch_nisar --download   # HDF5 (large) — 1 granule on each side
python -m pipeline.detect_change            # hectares + limitations
```

AOI and dates: `pipeline/config.py`.

## 3. Judging (Validity / Relevance)

- **Relevance:** the map and the indicators come from L-band GCOV, not from a decorative basemap.
- **Validity:** an RTC/gamma0 product built for flooding; the empirical threshold, speckle, geometry, and L-band penetration into vegetation are listed in `change_stats.json`.
