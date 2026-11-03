"""SD6105 Haze project: clean raw data into the chart-ready CSVs in "cleaned data/".

Run from anywhere: python3 clean_data.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw data"
FIRMS = RAW / "NASA FRIMS"
OUT = ROOT / "cleaned data"

REGIONS = ["north", "south", "east", "west", "central"]
HAZE_YEARS = [2015, 2019, 2023, 2026]

UNHEALTHY_MIN = 56  # daily PM2.5, corresponds to NEA PSI > 100
HAZE_DAY_MIN = 30  # daily PM2.5
LEVEL_BINS = [-np.inf, 15, 29, 55, 150, np.inf]
LEVEL_LABELS = ["<=15", "16-29", "30-55", "56-150", ">=151"]

FIRMS_2026_PARTS = ["2026-part1.csv", "2026-part2.csv", "2026Oct30.csv", "2026Oct31.csv"]
MIN_CONFIDENCE = 30
LON_RANGE = (95, 119)
LAT_RANGE = (-6, 6)
SUMATRA_MAX_LON = 108.7  # open sea between Belitung and western Kalimantan

RAIN_BASELINE = ("1991-01", "2020-12")


def round_half_up(values):
    # Daily means are judged as whole numbers, the way NEA bands are stated
    return np.floor(values + 0.5)


def write(df, name, expected_rows):
    assert len(df) == expected_rows, f"{name}: {len(df)} rows, expected {expected_rows}"
    df.to_csv(OUT / f"{name}.csv", index=False)
    print(f"{name}.csv: {len(df):,} rows")


# ---------- Dataset 1: Historical 1-hr PM2.5 ----------

def load_pm25_hourly():
    df = pd.read_csv(RAW / "Historical1hrPM2.5.csv")
    labels = pd.to_datetime(df["1hr_pm25"], format="%d/%m/%Y %H:%M", errors="coerce")

    # Rows are in unbroken hourly order, so row position recovers the 4 bad labels
    df["time"] = pd.date_range("2014-04-01 01:00", periods=len(df), freq="h")
    assert (labels != df["time"]).sum() == 4

    # October comes from the API (fetch_pm25_oct2026.py). Same hour labels as the
    # historical file, which is kept for the one hour they share (10-01 00:00)
    october = pd.read_csv(RAW / "Historical1hrPM2.5_2026Oct.csv")
    october["time"] = pd.to_datetime(october["timestamp"]).dt.tz_localize(None)
    october = october[october["time"] > df["time"].max()]
    df = pd.concat([df, october], ignore_index=True)
    assert (df["time"].diff().dropna() == pd.Timedelta(hours=1)).all()

    df[REGIONS] = df[REGIONS].apply(pd.to_numeric)
    assert df[REGIONS].notna().all().all()
    assert df[REGIONS].stack().between(1, 500).all()

    # Labels mark the end of the hour: 00:00 belongs to the previous day
    df["date"] = (df["time"] - pd.Timedelta(hours=1)).dt.normalize()
    df["national"] = df[REGIONS].mean(axis=1)
    return df[["date"] + REGIONS + ["national"]]


def build_pm25_daily(hourly):
    daily = hourly.groupby("date").agg(
        **{r: (r, "mean") for r in REGIONS},
        pm25_national=("national", "mean"),
        pm25_1hr_max=("national", "max"),
        n_hours=("national", "count"),
    ).reset_index()
    # Only the last day can be incomplete (the API download stopped partway through it)
    assert (daily["n_hours"].iloc[:-1] == 24).all()
    daily = daily[daily["n_hours"] == 24].copy()

    whole = round_half_up(daily["pm25_national"])
    daily["year"] = daily["date"].dt.year
    daily["month_day"] = daily["date"].dt.strftime("%m-%d")
    daily["pm25_level"] = pd.cut(whole, LEVEL_BINS, labels=LEVEL_LABELS).astype(str)
    daily["is_unhealthy"] = whole >= UNHEALTHY_MIN
    daily["is_haze_day"] = whole >= HAZE_DAY_MIN
    return daily[["date", "year", "month_day"] + REGIONS + [
        "pm25_national", "pm25_1hr_max", "pm25_level", "is_unhealthy", "is_haze_day"]]


def longest_run(flags):
    groups = (flags != flags.shift()).cumsum()
    return int(flags.groupby(groups).sum().max())


def build_severity_metrics(hourly, daily):
    rows = []
    for year in HAZE_YEARS:
        for window, end in (("Jul-Oct", "10-31"), ("Jul-Sep", "09-30")):
            days = daily[daily["date"].between(f"{year}-07-01", f"{year}-{end}")]
            hours = hourly[hourly["date"].isin(days["date"])]
            for scope, col in [("national", "pm25_national")] + [(r, r) for r in REGIONS]:
                hourly_col = "national" if scope == "national" else scope
                unhealthy = round_half_up(days[col]) >= UNHEALTHY_MIN
                rows.append({
                    "year": year,
                    "scope": scope,
                    "window": window,
                    "peak_daily": days[col].max(),
                    "peak_date": days.loc[days[col].idxmax(), "date"].date(),
                    "peak_1hr": hours[hourly_col].max(),
                    "unhealthy_days": int(unhealthy.sum()),
                    "longest_run_days": longest_run(unhealthy),
                    "mean_pm25": days[col].mean(),
                    "n_days": len(days),
                })
    return pd.DataFrame(rows)


# ---------- Dataset 2: NASA FIRMS hotspots ----------

def merge_firms_2026():
    # 2026 was downloaded in pieces; rebuild 2026.csv from all of them on every run
    parts = [pd.read_csv(FIRMS / name, dtype=str) for name in FIRMS_2026_PARTS]
    merged = pd.concat(parts, ignore_index=True)[list(parts[0].columns)]
    merged = merged.drop_duplicates(["latitude", "longitude", "acq_date", "acq_time", "satellite"])
    merged.sort_values(["acq_date", "acq_time"], kind="stable").to_csv(FIRMS / "2026.csv", index=False)


def build_firms_hotspots():
    merge_firms_2026()
    df = pd.concat(
        [pd.read_csv(FIRMS / f"{year}.csv", dtype={"acq_time": str}) for year in HAZE_YEARS],
        ignore_index=True,
    )
    df = df[
        df["longitude"].between(*LON_RANGE)
        & df["latitude"].between(*LAT_RANGE)
        & (df["confidence"] >= MIN_CONFIDENCE)
    ].copy()

    # acq_time is UTC; PM2.5 days are Singapore time (UTC+8)
    utc = pd.to_datetime(df["acq_date"] + df["acq_time"].str.zfill(4), format="%Y-%m-%d%H%M")
    df["date_sgt"] = (utc + pd.Timedelta(hours=8)).dt.normalize()
    df = df[df["date_sgt"].dt.month <= 10]  # drop Oct 31 UTC evening spilling into Nov 1

    df["year"] = df["date_sgt"].dt.year
    df["region"] = np.where(df["longitude"] < SUMATRA_MAX_LON, "sumatra", "kalimantan")
    return df[["date_sgt", "year", "latitude", "longitude", "region",
               "confidence", "frp", "daynight", "satellite"]].sort_values(
        "date_sgt", kind="stable").reset_index(drop=True)


def build_hotspots_daily(points):
    counts = points.groupby(["date_sgt", "region"]).size().unstack(fill_value=0)
    frp = points.groupby("date_sgt")["frp"].sum()

    # A day with no hotspots is a true 0
    days = pd.DatetimeIndex(np.concatenate([
        pd.date_range(f"{year}-07-01", f"{year}-10-31").values for year in HAZE_YEARS
    ]))
    daily = pd.DataFrame({
        "date": days,
        "year": days.year,
        "hotspots_sumatra": counts["sumatra"].reindex(days, fill_value=0).values,
        "hotspots_kalimantan": counts["kalimantan"].reindex(days, fill_value=0).values,
        "frp_sum": frp.reindex(days, fill_value=0).values,
    })
    daily["hotspots_total"] = daily["hotspots_sumatra"] + daily["hotspots_kalimantan"]
    return daily[["date", "year", "hotspots_total", "hotspots_sumatra",
                  "hotspots_kalimantan", "frp_sum"]]


def build_drivers_daily(hotspots, pm25):
    df = hotspots.drop(columns="frp_sum").copy()
    # Shift inside each year so a lag never reaches across to another haze season
    for lag in (1, 2, 3):
        df[f"hotspots_lag{lag}"] = df.groupby("year")["hotspots_total"].shift(lag)
    df = df.merge(pm25[["date", "pm25_national"]], on="date", how="inner")
    return df[["date", "year", "hotspots_total", "hotspots_sumatra", "hotspots_kalimantan",
               "pm25_national", "hotspots_lag1", "hotspots_lag2", "hotspots_lag3"]]


# ---------- Datasets 4 + 5: rainfall and ONI ----------

def load_oni():
    oni = pd.read_csv(RAW / "NOAA ONI" / "oni_long.csv")
    oni["month"] = oni["date"].str[:7]
    return oni.rename(columns={"season": "oni_season"})[["month", "Year", "oni", "oni_season"]]


def load_events():
    events = pd.read_csv(RAW / "NOAA ONI" / "elnino_events.csv", parse_dates=["start", "end"])
    events["start_month"] = events["start"].dt.strftime("%Y-%m")
    events["end_month"] = events["end"].dt.strftime("%Y-%m")
    return events


def in_event(months, events):
    flags = pd.Series(False, index=months.index)
    for event in events.itertuples():
        flags |= months.between(event.start_month, event.end_month)
    return flags


def build_climate_monthly(pm25, oni, events):
    rain = pd.read_csv(RAW / "RainfallMonthlyTotal.csv").rename(
        columns={"total_rainfall": "rainfall_mm"})
    baseline = rain[rain["month"].between(*RAIN_BASELINE)]
    normal = baseline.groupby(baseline["month"].str[5:])["rainfall_mm"].mean()
    usual = rain["month"].str[5:].map(normal)
    rain["rainfall_anom_pct"] = (rain["rainfall_mm"] - usual) / usual * 100

    monthly = pm25.groupby(pm25["date"].dt.strftime("%Y-%m"))["pm25_national"].mean()
    monthly = monthly.rename_axis("month").rename("pm25_monthly").reset_index()

    # Outer join keeps months that have PM2.5 but no rainfall yet (2026-10)
    df = rain.merge(monthly, on="month", how="outer").sort_values("month")
    df = df.merge(oni[["month", "oni", "oni_season"]], on="month", how="left")
    # No ONI yet means "unknown", not "not El Nino"
    df["is_elnino"] = in_event(df["month"], events).astype("boolean").mask(df["oni"].isna())
    return df[["month", "rainfall_mm", "rainfall_anom_pct", "oni", "oni_season",
               "is_elnino", "pm25_monthly"]]


def build_enso_pm25(pm25, oni, events):
    last_oni = pd.Timestamp(oni["month"].max() + "-01")
    first_pm25, last_pm25 = pm25["date"].min(), pm25["date"].max()
    rows = []
    for event in events[events["end"] >= first_pm25].itertuples():
        # An event still running when ONI stops is extended to the last PM2.5 day
        is_ongoing = event.end == last_oni
        end = last_pm25 if is_ongoing else event.end + pd.offsets.MonthEnd(0)
        days = pm25[pm25["date"].between(event.start, end)]
        rows.append({
            "event_start": event.start.date(),
            "event_end": event.end.date(),
            "n_seasons": event.n_seasons,
            "peak_oni": event.peak_oni,
            "is_ongoing": is_ongoing,
            "pm25_mean": days["pm25_national"].mean(),
            "pm25_p99": days["pm25_national"].quantile(0.99),
            "peak_daily": days["pm25_national"].max(),
            "unhealthy_days": int(days["is_unhealthy"].sum()),
        })
    return pd.DataFrame(rows)


# ---------- Dataset 3: Air Pollution Levels, Annual ----------

POLLUTANTS = {
    "Sulphur Dioxide": ("SO2", "ug/m3"),
    "Nitrogen Dioxide": ("NO2", "ug/m3"),
    "Particulate Matter (PM10)": ("PM10", "ug/m3"),
    "Particulate Matter (PM2.5)": ("PM2.5", "ug/m3"),
    "Carbon Monoxide": ("CO", "mg/m3"),
    "Ozone": ("O3", "ug/m3"),
}


def build_annual_long():
    wide = pd.read_csv(RAW / "AirPollutionLevelsAnnual.csv")
    df = wide.melt(id_vars="DataSeries", var_name="year", value_name="value")
    parts = df["DataSeries"].str.extract(r"^(.+) \((.+?)\)$")
    df["pollutant"] = parts[0].map(lambda name: POLLUTANTS[name][0])
    df["unit"] = parts[0].map(lambda name: POLLUTANTS[name][1])
    df["metric"] = parts[1]
    df["year"] = df["year"].astype(int)
    return df[["year", "pollutant", "metric", "value", "unit"]].sort_values(
        ["pollutant", "metric", "year"]).reset_index(drop=True)


def build_annual_summary(annual_long, pm25, oni, events):
    pm = annual_long[annual_long["pollutant"] == "PM2.5"]
    official = pm.pivot(index="year", columns="metric", values="value")
    df = pd.DataFrame({"year": range(2007, 2027)}).set_index("year")
    df["pm25_mean_official"] = official["Annual Mean"]
    df["pm25_p99_official"] = official["99th Percentile 24-Hour Mean"]

    # From 2014 only: daily data begins 2014-04 and 2026 stops at 10-31 (see n_days)
    by_year = pm25.groupby("year")
    df["pm25_mean_all"] = by_year["pm25_national"].mean()
    df["pm25_mean_background"] = pm25[~pm25["is_haze_day"]].groupby("year")["pm25_national"].mean()
    df["haze_days_excluded"] = by_year["is_haze_day"].sum().astype("Int64")
    df["n_days"] = by_year.size().astype("Int64")

    # Jul-Oct is the haze season; 2026 ONI covers only Jul and Aug so far
    season = oni[oni["month"].str[5:].isin(["07", "08", "09", "10"])].copy()
    season["in_event"] = in_event(season["month"], events)
    df["oni_jaso_mean"] = season.groupby("Year")["oni"].mean()
    df["elnino_months_jaso"] = season.groupby("Year")["in_event"].sum()
    return df.reset_index()


def main():
    OUT.mkdir(exist_ok=True)

    hourly = load_pm25_hourly()
    pm25 = build_pm25_daily(hourly)
    points = build_firms_hotspots()
    hotspots = build_hotspots_daily(points)
    oni, events = load_oni(), load_events()
    annual_long = build_annual_long()

    write(pm25.round(2), "pm25_daily", 4597)
    write(build_severity_metrics(hourly, pm25).round(2), "severity_metrics", 48)
    write(points.astype({"year": int}), "firms_hotspots", 289666)
    write(hotspots.round(1), "hotspots_daily", 492)
    write(build_drivers_daily(hotspots, pm25).round(2), "drivers_daily", 492)
    write(build_climate_monthly(pm25, oni, events).round(2), "climate_monthly", 538)
    write(build_enso_pm25(pm25, oni, events).round(2), "enso_pm25", 5)
    write(build_annual_summary(annual_long, pm25, oni, events).round(2), "annual_summary", 20)
    write(annual_long, "annual_long", 190)


if __name__ == "__main__":
    main()
