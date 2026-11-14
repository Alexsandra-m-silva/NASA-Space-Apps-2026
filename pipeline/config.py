"""Climate Guardian — AOI and NASA collections.

Demo: Uruguay River flood at Uruguaiana, Rio Grande do Sul.
Same descending track, one 12-day NISAR cycle apart.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
WEB_OVERLAYS = ROOT / "web" / "overlays"

# west, south, east, north — Uruguay River at Uruguaiana
AOI_BBOX = (-57.20, -29.98, -56.72, -29.48)
AOI_NAME = "uruguaiana-uruguay-river"

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
