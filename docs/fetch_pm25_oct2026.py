"""Download 2026-10 hourly PM2.5 from data.gov.sg into "raw data/", exactly as the API reports it.

The historical CSV stops at 2026-10-01 00:00. clean_data.py merges this file with it.
Run from anywhere: python3 fetch_pm25_oct2026.py
"""
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "raw data" / "Historical1hrPM2.5_2026Oct.csv"

# v2, not v1: the v1 endpoint omits the 00:00 reading of every date
API = "https://api-open.data.gov.sg/v2/real-time/api/pm25"
REGIONS = ["north", "south", "east", "west", "central"]


def get_json(url, attempts=5):
    request = urllib.request.Request(url, headers={"User-Agent": "SD6105-haze-project"})
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except OSError as error:
            if attempt == attempts:
                raise
            print(f"retry {attempt}: {error}")
            time.sleep(5 * attempt)


def fetch_date(date):
    items, token = [], None
    while True:
        query = {"date": date}
        if token:
            query["paginationToken"] = token
        data = get_json(f"{API}?{urllib.parse.urlencode(query)}")["data"]
        items += data["items"]
        token = data.get("paginationToken")
        if not token:
            return items


def main():
    rows = []
    # Readings are labelled at the end of the hour, so 10-31 ends with 11-01 00:00
    for day in pd.date_range("2026-10-01", "2026-11-01"):
        items = fetch_date(day.strftime("%Y-%m-%d"))
        rows += [
            {
                "timestamp": item["timestamp"],
                "updated_timestamp": item["updatedTimestamp"],
                **{r: item["readings"]["pm25_one_hourly"].get(r) for r in REGIONS},
            }
            for item in items
        ]
        print(day.date(), len(items))
        time.sleep(1)

    df = pd.DataFrame(rows).sort_values("timestamp")
    df = df[df["timestamp"] <= "2026-11-01T00:00:00+08:00"]
    df.to_csv(OUT, index=False)
    print(f"{OUT.name}: {len(df)} rows, {df['timestamp'].min()} to {df['timestamp'].max()}")


if __name__ == "__main__":
    main()
