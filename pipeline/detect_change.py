"""Flood change from a NISAR GCOV HH pair.

Calm open water has very low L-band HH gamma0. New inundation is pixels
that cross below WATER_DB_THRESHOLD between the before and after scenes.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rioxarray  # noqa: F401 — registers .rio
import xarray as xr

from pipeline.config import (
    DATA_PROCESSED,
    DATA_RAW,
    GCOV_GROUP,
    GCOV_LAYER,
    WATER_DB_THRESHOLD,
    WEB_OVERLAYS,
)


def _open_hhhh(path: Path) -> xr.DataArray:
    ds = xr.open_dataset(
        path,
        engine="h5netcdf",
        group=GCOV_GROUP,
        phony_dims="sort",
        drop_variables=["listOfCovarianceTerms", "listOfPolarizations"],
    )
    if GCOV_LAYER not in ds:
        raise KeyError(f"{path.name} has no {GCOV_LAYER}. Keys: {list(ds.data_vars)}")
    da = ds[GCOV_LAYER]
    da.rio.set_spatial_dims(x_dim="xCoordinates", y_dim="yCoordinates", inplace=True)
    if "spatial_ref" not in ds and "projection" in ds:
        epsg = int(ds["projection"].attrs.get("epsg_code", 0) or 0)
        if epsg:
            da.rio.write_crs(f"EPSG:{epsg}", inplace=True)
    return da


def _to_db(power: np.ndarray) -> np.ndarray:
    return 10.0 * np.log10(np.clip(power, 1e-8, None))


def _find_h5(folder: Path) -> Path | None:
    if not folder.exists():
        return None
    files = sorted(folder.glob("*.h5"))
    return files[0] if files else None


def main() -> None:
    before_path = _find_h5(DATA_RAW / "nisar" / "before")
    after_path = _find_h5(DATA_RAW / "nisar" / "after")
    if not before_path or not after_path:
        raise SystemExit(
            "Missing GCOV HDF5 pair. Run: python -m pipeline.fetch_nisar --download"
        )

    before = _open_hhhh(before_path)
    after = _open_hhhh(after_path).rio.reproject_match(before)

    before_db = _to_db(before.values)
    after_db = _to_db(after.values)
    water_before = before_db < WATER_DB_THRESHOLD
    water_after = after_db < WATER_DB_THRESHOLD
    new_water = water_after & ~water_before
    receded = water_before & ~water_after

    pixel_m = float(abs(before["xCoordinates"].diff("xCoordinates").median()))
    pixel_ha = (pixel_m * pixel_m) / 10_000.0
    stats = {
        "product": "NISAR_L2_GCOV HHHH gamma0",
        "threshold_db": WATER_DB_THRESHOLD,
        "pixel_m": pixel_m,
        "new_inundation_ha": float(new_water.sum() * pixel_ha),
        "receded_ha": float(receded.sum() * pixel_ha),
        "water_before_ha": float(water_before.sum() * pixel_ha),
        "water_after_ha": float(water_after.sum() * pixel_ha),
        "limitations": [
            "Threshold is empirical; incidence angle and soil moisture shift it.",
            "L-band penetrates vegetation: inundated wetlands ≠ open-water C-band maps.",
            "Speckle and layover remain after RTC; treat edges as uncertain.",
            "Pair must share orbit/geometry (same track/frame) for a fair change map.",
        ],
    }
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    WEB_OVERLAYS.mkdir(parents=True, exist_ok=True)
    (DATA_PROCESSED / "change_stats.json").write_text(json.dumps(stats, indent=2))
    (WEB_OVERLAYS / "change_stats.json").write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
