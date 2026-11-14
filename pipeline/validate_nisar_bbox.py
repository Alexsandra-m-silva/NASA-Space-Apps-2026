"""List NISAR products over one small box, and download them when asked.

The box is about 11 km on a side near Petrolina, on descending track 168.
Search uses the public CMR catalog. Download needs an Earthdata login
(EARTHDATA_USERNAME and EARTHDATA_PASSWORD, or a ~/.netrc entry).

Validated collections are tried first, then provisional, then beta.
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "nisar-validate"

# west, south, east, north
BBOX = (-40.55, -9.48, -40.45, -9.40)
DAY = "2026-09-05"

# One family, in the order we prefer.
FAMILIES = {
    "RSLC": (
        "NISAR_L1_RSLC_V1",
        "NISAR_L1_RSLC_PROVISIONAL_V1",
        "NISAR_L1_RSLC_BETA_V1",
    ),
    "GSLC": (
        "NISAR_L2_GSLC_V1",
        "NISAR_L2_GSLC_PROVISIONAL_V1",
        "NISAR_L2_GSLC_BETA_V1",
    ),
    "GCOV": (
        "NISAR_L2_GCOV_V1",
        "NISAR_L2_GCOV_PROVISIONAL_V1",
        "NISAR_L2_GCOV_BETA_V1",
    ),
    "GUNW": (
        "NISAR_L2_GUNW_V1",
        "NISAR_L2_GUNW_PROVISIONAL_V1",
        "NISAR_L2_GUNW_BETA_V1",
    ),
    "SME2": (
        "NISAR_L3_SME2_V1",
        "NISAR_L3_SME2_PROVISIONAL_V1",
        "NISAR_L3_SME2_BETA_V1",
    ),
}


def search(short_name: str) -> list[dict]:
    west, south, east, north = BBOX
    query = urlencode(
        {
            "short_name": short_name,
            "bounding_box": f"{west},{south},{east},{north}",
            "temporal": f"{DAY}T00:00:00Z,{DAY}T23:59:59Z",
            "page_size": 5,
        }
    )
    url = "https://cmr.earthdata.nasa.gov/search/granules.json?" + query
    with urlopen(url, timeout=60) as response:
        feed = json.load(response)["feed"]["entry"]
    return feed


def data_link(entry: dict) -> str:
    for link in entry.get("links", []):
        href = link.get("href", "")
        if href.endswith((".h5", ".nc")) and "s3credentials" not in href:
            return href
    for link in entry.get("links", []):
        rel = (link.get("rel") or "").lower()
        if "data" in rel and link.get("href"):
            return link["href"]
    return ""


def catalog() -> dict:
    found = {}
    for family, names in FAMILIES.items():
        for short_name in names:
            hits = search(short_name)
            if not hits:
                continue
            found[family] = {
                "short_name": short_name,
                "granules": [
                    {"id": hit.get("title"), "link": data_link(hit)} for hit in hits
                ],
            }
            break
        else:
            found[family] = {"short_name": None, "granules": []}
    return found


def download(found: dict) -> None:
    import earthaccess

    earthaccess.login(strategy="environment")
    for family, info in found.items():
        granules = info["granules"]
        if not granules:
            print(f"{family}: nothing to download")
            continue
        dest = OUT / family
        dest.mkdir(parents=True, exist_ok=True)
        granule_id = granules[0]["id"]
        print(f"{family}: downloading {granule_id}")
        results = earthaccess.search_data(granule_name=granule_id, count=1)
        if not results:
            print(f"{family}: catalog id not opened by earthaccess")
            continue
        saved = earthaccess.download(results, str(dest))
        print(f"{family}: {saved}")


def main(do_download: bool = False) -> None:
    west, south, east, north = BBOX
    print(f"bbox {west}, {south}, {east}, {north}")
    print(f"day  {DAY}")
    found = catalog()
    for family, info in found.items():
        granules = info["granules"]
        if not granules:
            print(f"{family:5}  no granule")
            continue
        first = granules[0]
        print(f"{family:5}  {info['short_name']}")
        print(f"       {first['id']}")
        print(f"       {first['link']}")
    OUT.mkdir(parents=True, exist_ok=True)
    report = OUT / "catalog.json"
    report.write_text(json.dumps({"bbox": BBOX, "day": DAY, "products": found}, indent=2))
    print(f"catalog {report}")
    if do_download:
        download(found)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Validate NISAR products on a small box")
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download the first granule of each product (needs Earthdata login)",
    )
    main(do_download=parser.parse_args().download)
