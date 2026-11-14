"""Search/download NASA GPM IMERG Late daily rain between the two SAR dates."""

from __future__ import annotations

import json

import earthaccess

from pipeline.config import (
    AOI_BBOX,
    DATA_PROCESSED,
    DATA_RAW,
    DATE_AFTER,
    DATE_BEFORE,
    GPM_SHORT_NAME,
    GPM_VERSION,
)


def main(download: bool = False) -> None:
    import os

    if os.getenv("EARTHDATA_USERNAME"):
        earthaccess.login(strategy="environment")
    elif download:
        earthaccess.login()
    west, south, east, north = AOI_BBOX
    results = earthaccess.search_data(
        short_name=GPM_SHORT_NAME,
        version=GPM_VERSION,
        bounding_box=(west, south, east, north),
        temporal=(DATE_BEFORE, DATE_AFTER),
        count=40,
    )
    print(f"GPM IMERG Late daily: {len(results)} granules {DATE_BEFORE} → {DATE_AFTER}")
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    catalog = {
        "short_name": GPM_SHORT_NAME,
        "version": GPM_VERSION,
        "temporal": [DATE_BEFORE, DATE_AFTER],
        "count": len(results),
        "ids": [
            (g.get("umm", {}) if isinstance(g, dict) else getattr(g, "umm", {})).get("GranuleUR")
            for g in results
        ],
    }
    (DATA_PROCESSED / "gpm_catalog.json").write_text(json.dumps(catalog, indent=2))
    if download and results:
        dest = DATA_RAW / "gpm"
        dest.mkdir(parents=True, exist_ok=True)
        earthaccess.download(results, local_path=str(dest))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true")
    main(download=parser.parse_args().download)
