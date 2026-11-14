"""Search (and optionally download) NISAR L2 GCOV granules for the AOI."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import earthaccess

from pipeline.config import (
    AOI_BBOX,
    AOI_NAME,
    DATA_PROCESSED,
    DATA_RAW,
    DATE_AFTER,
    DATE_BEFORE,
    NISAR_SHORT_NAMES,
)


def _login(required: bool = False) -> None:
    import os

    if os.getenv("EARTHDATA_USERNAME"):
        earthaccess.login(strategy="environment")
    elif required:
        earthaccess.login()


def _window(date_iso: str, pad_days: int = 2) -> tuple[str, str]:
    day = datetime.fromisoformat(date_iso).replace(tzinfo=timezone.utc)
    start = (day - timedelta(days=pad_days)).strftime("%Y-%m-%d")
    end = (day + timedelta(days=pad_days)).strftime("%Y-%m-%d")
    return start, end


def search_gcov(date_iso: str, count: int = 12) -> list:
    start, end = _window(date_iso)
    west, south, east, north = AOI_BBOX
    hits: list = []
    for short_name in NISAR_SHORT_NAMES:
        found = earthaccess.search_data(
            short_name=short_name,
            bounding_box=(west, south, east, north),
            temporal=(start, end),
            count=count,
        )
        if found:
            hits.extend(found)
            break
    return hits


def _summarize(granule) -> dict:
    umm = granule.get("umm", {}) if isinstance(granule, dict) else getattr(granule, "umm", {})
    links = granule.data_links() if hasattr(granule, "data_links") else []
    return {
        "id": umm.get("GranuleUR") or str(granule),
        "time": (umm.get("TemporalExtent") or {}),
        "links": links,
    }


def write_catalog(before, after) -> Path:
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    catalog = {
        "aoi": AOI_NAME,
        "bbox": AOI_BBOX,
        "before_date": DATE_BEFORE,
        "after_date": DATE_AFTER,
        "product": "NISAR L2 GCOV (gamma0, analysis-ready)",
        "layer": "HHHH",
        "before": [_summarize(g) for g in before],
        "after": [_summarize(g) for g in after],
    }
    path = DATA_PROCESSED / "nisar_catalog.json"
    path.write_text(json.dumps(catalog, indent=2, default=str))
    return path


def download_h5(granules, dest: Path) -> list[Path]:
    dest.mkdir(parents=True, exist_ok=True)
    files = earthaccess.download(granules, local_path=str(dest))
    return [Path(f) for f in files]


def main(download: bool = False) -> None:
    _login(required=download)
    before = search_gcov(DATE_BEFORE)
    after = search_gcov(DATE_AFTER)
    print(f"Before {DATE_BEFORE}: {len(before)} GCOV granules")
    print(f"After  {DATE_AFTER}: {len(after)} GCOV granules")
    catalog = write_catalog(before, after)
    print(f"Catalog → {catalog}")
    if download:
        if before:
            download_h5(before[:1], DATA_RAW / "nisar" / "before")
        if after:
            download_h5(after[:1], DATA_RAW / "nisar" / "after")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true", help="Download first matching HDF5 pair")
    main(download=parser.parse_args().download)
