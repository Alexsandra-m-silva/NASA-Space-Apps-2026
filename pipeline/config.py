"""Climate Guardian — AOI and NASA collections.

Default demo: northern Pantanal (wetland + floodable plains).
L-band GCOV is the analysis-ready NISAR product for inundation.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
WEB_OVERLAYS = ROOT / "web" / "overlays"

# west, south, east, north
AOI_BBOX = (-57.9, -19.4, -56.1, -17.6)
AOI_NAME = "pantanal-norte"

# NISAR 12-day repeat. Pick two dates one cycle apart.
DATE_BEFORE = "2026-10-24"
DATE_AFTER = "2026-11-05"

# VALIDATED (from 21 Oct 2026) then PROVISIONAL fallback
NISAR_SHORT_NAMES = (
    "NISAR_L2_GCOV_V1",
    "NISAR_L2_GCOV_PROVISIONAL_V1",
)

# HH intensity (gamma0). Water = very low backscatter.
GCOV_LAYER = "HHHH"
GCOV_GROUP = "/science/LSAR/GCOV/grids/frequencyA"

# GPM IMERG Late daily — rain context between the two SAR passes
GPM_SHORT_NAME = "GPM_3IMERGDL"
GPM_VERSION = "07"

# Empirical L-band HH water threshold in dB (document as uncertainty).
WATER_DB_THRESHOLD = -18.0
