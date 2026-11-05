from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "cleaned data"
FIGURES = ROOT / "figures"

HAZE_YEARS = [2015, 2019, 2023, 2026]
REGIONS = ["north", "south", "east", "west", "central"]
WIDTH, HEIGHT = 1240, 600

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
LAND = "#f0efec"
YEAR_COLOR = {2015: "#2a78d6", 2019: "#1baf7a", 2023: "#6250d6", 2026: "#eb6834"}
EL_NINO = "#e34948"
LA_NINA = "#2a78d6"
NEUTRAL = "#c3c2b7"
BACKGROUND_LINE = "#2a78d6"
NO2_LINE = "#6250d6"
HOTSPOT = "#bf5220"
LEVEL_LABELS = ["<=15", "16-29", "30-55", "56-150", ">=151"]
LEVEL_NAMES = ["≤15 (WHO 24-h)", "16–29", "30–55", "56–150 (unhealthy)", "≥151"]
LEVEL_COLORS = ["#e99d72", "#da743f", "#bf5220", "#8c3812", "#561f0a"]

UNHEALTHY = 56
WHO_ANNUAL = 5
WHO_24H = 15
UNIT = "µg/m³"
FONT = "'Helvetica Neue', Helvetica, Arial, sans-serif"
SOURCE_PM = "Source: NEA hourly PM2.5 (data.gov.sg), national = mean of 5 regions"


def tint(hex_color, alpha):
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{g},{b},{alpha})"


def load(name, **kwargs):
    return pd.read_csv(DATA / f"{name}.csv", **kwargs)


def season_axis_date(month_day):
    return pd.to_datetime("2026-" + month_day)


def style(fig, title, subtitle, height=HEIGHT, legend=True):
    fig.update_layout(
        width=WIDTH,
        height=height,
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(family=FONT, size=17, color=INK_2),
        title=dict(
            text=f"<b>{title}</b>", subtitle=dict(text=subtitle, font=dict(size=16, color=MUTED)),
            x=0.01, xanchor="left", yref="container", y=1, yanchor="top", pad=dict(t=16),
            font=dict(size=25, color=INK),
        ),
        margin=dict(l=80, r=40, t=128, b=60),
        showlegend=legend,
        legend=dict(orientation="h", x=0, xanchor="left", y=1.02, yanchor="bottom",
                    font=dict(size=16, color=INK_2), bgcolor="rgba(0,0,0,0)",
                    itemwidth=40, tracegroupgap=24),
        hoverlabel=dict(font=dict(family=FONT, size=15), bgcolor="white", bordercolor=AXIS),
    )
    fig.update_xaxes(showgrid=False, linecolor=AXIS, ticks="outside", tickcolor=AXIS,
                     tickfont=dict(size=15, color=MUTED), title_font=dict(size=16, color=INK_2))
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor=AXIS,
                     tickfont=dict(size=15, color=MUTED), title_font=dict(size=16, color=INK_2))
    return fig


def threshold_line(fig, y, label, row=None, col=None, xref_paper=True):
    kwargs = dict(row=row, col=col) if row else {}
    fig.add_hline(y=y, line=dict(color=MUTED, width=1.2, dash="dot"),
                  annotation_text=label, annotation_position="top left", annotation_bgcolor=SURFACE,
                  annotation_font=dict(size=14, color=MUTED), **kwargs)


def longest_run_dates(flags, dates):
    best, start, run_start, length = 0, None, None, 0
    for flag, date in zip(flags, dates):
        if flag:
            run_start = date if length == 0 else run_start
            length += 1
            if length > best:
                best, start, end = length, run_start, date
        else:
            length = 0
    return best, start, end


def season_metrics():
    m = load("severity_metrics")
    return m[(m["window"] == "Jul-Oct") & (m["scope"] == "national")].set_index("year")


def make_season_overlay():
    pm = load("pm25_daily")
    m = season_metrics()
    assert m["unhealthy_days"].idxmax() == 2015 and m["longest_run_days"].idxmax() == 2026
    fig = go.Figure()
    ends = {}
    for year in HAZE_YEARS:
        d = pm[(pm["year"] == year) & pm["month_day"].between("07-01", "10-31")]
        x = season_axis_date(d["month_day"])
        fig.add_trace(go.Scatter(
            x=x, y=d["pm25_national"], name=str(year), mode="lines",
            line=dict(color=YEAR_COLOR[year], width=3.2 if year == 2026 else 1.8),
            opacity=1 if year == 2026 else 0.85,
            customdata=d["date"],
            hovertemplate=f"<b>%{{customdata}}</b><br>PM2.5 %{{y:.1f}} {UNIT}<extra>{year}</extra>",
        ))
        ends[year] = (x.iloc[-1], d["pm25_national"].iloc[-1])
    placed = []
    for year, (x_end, y_end) in sorted(ends.items(), key=lambda kv: kv[1][1]):
        y_label = max(y_end, placed[-1] + 9) if placed else y_end
        placed.append(y_label)
        fig.add_annotation(x=x_end, y=y_label, text=f"<b>{year}</b>", showarrow=False, xanchor="left",
                           xshift=6, font=dict(size=15, color=YEAR_COLOR[year]),
                           name="late" if year == 2026 else None)
    d26 = pm[(pm["year"] == 2026) & pm["month_day"].between("07-01", "10-31")]
    run, start, end = longest_run_dates(d26["is_unhealthy"], season_axis_date(d26["month_day"]))
    fig.add_vrect(x0=start - pd.Timedelta(hours=12), x1=end + pd.Timedelta(hours=12),
                  fillcolor=YEAR_COLOR[2026], opacity=0.13, line_width=0, layer="below", name="late")
    fig.add_annotation(x=start + (end - start) / 2, y=1, yref="paper", yanchor="bottom", showarrow=False,
                       text=f"<b>{run} unhealthy days in a row</b><br>{start:%d %b} to {end:%d %b} 2026",
                       font=dict(size=14, color=YEAR_COLOR[2026]), name="late")
    threshold_line(fig, UNHEALTHY, f"Unhealthy (≥{UNHEALTHY}, PSI > 100)")
    threshold_line(fig, WHO_24H, f"WHO 24-h guideline ({WHO_24H})")
    fig.update_xaxes(tickformat="%b %d", dtick="M1", range=["2026-06-29", "2026-11-06"])
    fig.update_yaxes(title_text=f"Daily PM2.5 ({UNIT})", rangemode="tozero")
    fig.update_layout(hovermode="x unified")
    title = (f"2026 had the longest unhealthy stretch ({m.loc[2026, 'longest_run_days']} days); "
             f"2015 had the most unhealthy days ({m.loc[2015, 'unhealthy_days']})")
    return style(fig, title, f"Daily mean PM2.5, 1 Jul – 31 Oct of each haze year. {SOURCE_PM}")


def make_calendar(years=HAZE_YEARS):
    pm = load("pm25_daily", parse_dates=["date"])
    level = {label: i for i, label in enumerate(LEVEL_LABELS)}
    rows = (len(years) + 1) // 2
    fig = make_subplots(rows=rows, cols=2, subplot_titles=[str(y) for y in years],
                        horizontal_spacing=0.06, vertical_spacing=0.16)
    scale = []
    for i, color in enumerate(LEVEL_COLORS):
        scale += [[i / 5, color], [(i + 1) / 5, color]]
    for k, year in enumerate(years):
        d = pm[pm["date"].between(f"{year}-07-01", f"{year}-10-31")].copy()
        d["day"] = (d["date"] - d["date"].min()).dt.days
        first_monday = d["date"].min() - pd.Timedelta(days=d["date"].min().weekday())
        d["week"] = (d["date"] - first_monday).dt.days // 7
        d["weekday"] = d["date"].dt.weekday
        z = d.pivot(index="weekday", columns="week", values="pm25_level").apply(lambda col: col.map(level))
        value = d.pivot(index="weekday", columns="week", values="pm25_national")
        when = d.pivot(index="weekday", columns="week", values="date").apply(
            lambda col: col.dt.strftime("%a %d %b %Y"))
        day = d.pivot(index="weekday", columns="week", values="day")
        row, col = k // 2 + 1, k % 2 + 1
        fig.add_trace(go.Heatmap(
            z=z.values, x=z.columns, y=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            customdata=np.dstack([when.values, value.round(1).values, day.values]),
            colorscale=scale, zmin=-0.5, zmax=4.5, xgap=2, ygap=2, showscale=(k == 0),
            colorbar=dict(
                title=dict(text=f"Daily PM2.5<br>({UNIT})", font=dict(size=14)),
                tickvals=[0, 1, 2, 3, 4], ticktext=LEVEL_NAMES, tickfont=dict(size=13),
                len=0.9, thickness=16, x=1.01, outlinewidth=0),
            hovertemplate="<b>%{customdata[0]}</b><br>PM2.5 %{customdata[1]} " + UNIT + "<extra></extra>",
        ), row=row, col=col)
        month_weeks = d.groupby(d["date"].dt.month)["week"].min()
        fig.update_xaxes(tickvals=month_weeks.values,
                         ticktext=[pd.Timestamp(2000, mth, 1).strftime("%b") for mth in month_weeks.index],
                         row=row, col=col)
        fig.update_yaxes(autorange="reversed", tickvals=["Mon", "Wed", "Fri", "Sun"], row=row, col=col)
    fig.update_xaxes(linecolor=SURFACE, ticks="")
    fig.update_yaxes(gridcolor=SURFACE, linecolor=SURFACE)
    for ann in fig.layout.annotations:
        ann.font = dict(size=18, color=INK)
        ann.x, ann.xanchor = ann.x - 0.22, "left"

    d26 = pm[pm["date"].between("2026-07-01", "2026-10-31")]
    run, start, end = longest_run_dates(d26["is_unhealthy"], d26["date"])
    title = f"2026's unhealthy days ran unbroken for {run} days ({start:%d %b} – {end:%d %b})"
    style(fig, title, "Each cell is one day (1 Jul – 31 Oct); darker = higher daily mean PM2.5", legend=False)
    fig.update_layout(margin=dict(l=60, r=150, t=110, b=40))
    return fig


def make_metrics_table():
    m = load("severity_metrics")
    m = m[m["window"] == "Jul-Oct"]
    nat = m[m["scope"] == "national"].set_index("year")
    worst = (m[m["scope"] != "national"].sort_values("unhealthy_days", ascending=False)
             .groupby("year").first())
    rows = [
        ("Peak daily PM2.5", [f"{v:.0f}" for v in nat["peak_daily"]]),
        ("Peak date", [pd.Timestamp(v).strftime("%d %b") for v in nat["peak_date"]]),
        ("Peak 1-hour PM2.5", [f"{v:.0f}" for v in nat["peak_1hr"]]),
        ("Unhealthy days (≥56)", [f"{v}" for v in nat["unhealthy_days"]]),
        ("Longest unhealthy run (days)", [f"{v}" for v in nat["longest_run_days"]]),
        ("Season mean PM2.5", [f"{v:.1f}" for v in nat["mean_pm25"]]),
        ("Worst region (unhealthy days)",
         [f"{worst.loc[y, 'scope'].title()} ({worst.loc[y, 'unhealthy_days']})" for y in nat.index]),
    ]
    header = ["Jul–Oct, national"] + [str(y) for y in nat.index]
    cells = [[r[0] for r in rows]] + [[r[1][i] for r in rows] for i in range(len(nat))]
    fill = [[SURFACE] * len(rows)] + [
        ["#fbe8de" if y == 2026 else SURFACE] * len(rows) for y in nat.index]
    fig = go.Figure(go.Table(
        columnwidth=[2.4, 1, 1, 1, 1],
        header=dict(values=[f"<b>{h}</b>" for h in header], align=["left"] + ["center"] * 4,
                    fill_color=SURFACE, line_color=AXIS, height=46,
                    font=dict(size=20, color=[INK] + [YEAR_COLOR[y] for y in nat.index])),
        cells=dict(values=cells, align=["left"] + ["center"] * 4, fill_color=fill,
                   line_color=GRID, height=52, font=dict(size=20, color=INK)),
    ))
    title = "2015 peaked highest; 2026 was second on every measure but run length"
    assert nat["peak_daily"].rank(ascending=False)[2026] == 2
    style(fig, title, f"Daily mean PM2.5 in {UNIT}; unhealthy = daily mean ≥ 56 (NEA PSI > 100)", legend=False)
    fig.update_layout(margin=dict(l=40, r=40, t=120, b=20))
    return fig


def make_region_box():
    pm = load("pm25_daily", parse_dates=["date"])
    m = load("severity_metrics")
    regional = m[(m["window"] == "Jul-Oct") & (m["year"] == 2026) & (m["scope"] != "national")]
    top = regional.sort_values("unhealthy_days", ascending=False).iloc[0]
    fig = make_subplots(rows=1, cols=4, shared_yaxes=True, horizontal_spacing=0.02,
                        subplot_titles=[str(y) for y in HAZE_YEARS])
    for k, year in enumerate(HAZE_YEARS):
        d = pm[pm["date"].between(f"{year}-07-01", f"{year}-10-31")]
        for region in REGIONS:
            fig.add_trace(go.Box(
                y=d[region], name=region.title(), marker=dict(color=YEAR_COLOR[year], size=5),
                line=dict(width=1.6), fillcolor=tint(YEAR_COLOR[year], 0.2), boxpoints="outliers",
                hovertemplate=f"{year} %{{x}}<br>%{{y:.1f}} {UNIT}<extra></extra>",
            ), row=1, col=k + 1)
        fig.add_hline(y=UNHEALTHY, line=dict(color=MUTED, width=1.2, dash="dot"), row=1, col=k + 1)
    fig.add_annotation(xref="paper", yref="y", x=1, y=UNHEALTHY, text="Unhealthy (≥56)", bgcolor=SURFACE,
                       showarrow=False, xanchor="right", yanchor="bottom", font=dict(size=14, color=MUTED))
    fig.update_yaxes(title_text=f"Daily PM2.5 ({UNIT})", col=1)
    fig.update_xaxes(tickfont=dict(size=13))
    for ann in fig.layout.annotations[:4]:
        ann.font = dict(size=18, color=INK)
    title = (f"In 2026 the {top['scope']} region suffered most: {top['unhealthy_days']} unhealthy days")
    return style(fig, title, "Distribution of daily PM2.5 by region, 1 Jul – 31 Oct", legend=False)


def make_region_bars(years=(2015, 2026)):
    m = load("severity_metrics")
    m = m[(m["window"] == "Jul-Oct") & m["year"].isin(years)]
    scopes = ["national"] + REGIONS
    fig = go.Figure()
    for year in years:
        g = m[m["year"] == year].set_index("scope").loc[scopes]
        fig.add_trace(go.Bar(
            x=[s.title() for s in scopes], y=g["unhealthy_days"], name=str(year),
            text=g["unhealthy_days"], textposition="outside", textfont=dict(size=15, color=INK_2),
            marker=dict(color=YEAR_COLOR[year], line=dict(color=SURFACE, width=2)),
            hovertemplate=f"{year} %{{x}}: %{{y}} unhealthy days<extra></extra>",
        ))
    fig.update_layout(barmode="group", bargap=0.3, bargroupgap=0.06)
    fig.update_yaxes(title_text="Unhealthy days, Jul–Oct", range=[0, 40])
    days = m.pivot(index="scope", columns="year", values="unhealthy_days")
    worst = days[2026].drop("national").idxmax()
    assert days.loc[worst, 2026] == days.loc[worst, 2015]
    title = (f"The {worst} region had as many unhealthy days in 2026 as in 2015 "
             f"({days.loc[worst, 2026]})")
    sub = "Days with daily mean PM2.5 ≥ 56 µg/m³ (PSI > 100), 1 Jul – 31 Oct. National = mean of the 5 regions"
    return style(fig, title, sub)


def make_hotspots_vs_pm25():
    d = load("drivers_daily", parse_dates=["date"])
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                        row_heights=[0.5, 0.5])
    for year in HAZE_YEARS:
        y = d[d["year"] == year]
        x = season_axis_date(y["date"].dt.strftime("%m-%d"))
        visible = year == 2026
        fig.add_trace(go.Bar(
            x=x, y=y["hotspots_total"], name=f"{year} hotspots", visible=visible,
            marker=dict(color=YEAR_COLOR[year], line=dict(width=0)),
            customdata=np.column_stack([y["date"].dt.strftime("%d %b %Y"),
                                        y["hotspots_sumatra"], y["hotspots_kalimantan"]]),
            hovertemplate="<b>%{customdata[0]}</b><br>%{y} hotspots"
                          "<br>Sumatra %{customdata[1]} · Kalimantan %{customdata[2]}<extra></extra>",
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=x, y=y["pm25_national"], name=f"{year} PM2.5", visible=visible, mode="lines",
            line=dict(color=YEAR_COLOR[year], width=2.4),
            customdata=y["date"].dt.strftime("%d %b %Y"),
            hovertemplate=f"<b>%{{customdata}}</b><br>PM2.5 %{{y:.1f}} {UNIT}<extra></extra>",
        ), row=2, col=1)
    fig.add_hline(y=UNHEALTHY, line=dict(color=MUTED, width=1.2, dash="dot"), row=2, col=1,
                  annotation_text="Unhealthy (≥56)", annotation_position="top left",
                  annotation_font=dict(size=14, color=MUTED))
    buttons = []
    for k, year in enumerate(HAZE_YEARS):
        visible = [False] * (2 * len(HAZE_YEARS))
        visible[2 * k] = visible[2 * k + 1] = True
        buttons.append(dict(label=str(year), method="update", args=[{"visible": visible}]))
    fig.update_layout(
        updatemenus=[dict(type="buttons", direction="right", buttons=buttons,
                          active=HAZE_YEARS.index(2026), x=1, xanchor="right", y=1.13, yanchor="bottom",
                          font=dict(size=15), bgcolor="white", bordercolor=AXIS, pad=dict(r=4, t=4))],
        bargap=0.15, hovermode="x unified",
    )
    fig.update_yaxes(title_text="Hotspots / day", row=1, col=1)
    fig.update_yaxes(title_text=f"PM2.5 ({UNIT})", row=2, col=1)
    fig.update_xaxes(tickformat="%b %d", dtick="M1", row=2, col=1)
    title = "Fires in Indonesia and Singapore's air, day by day"
    sub = "Top: MODIS hotspots in Sumatra + Kalimantan (confidence ≥ 30). Bottom: national daily PM2.5"
    return style(fig, title, sub, legend=False)


def correlations():
    d = load("drivers_daily")
    rows = []
    for year, g in d.groupby("year"):
        for lag, col in enumerate(["hotspots_total", "hotspots_lag1", "hotspots_lag2", "hotspots_lag3"]):
            pair = g[["pm25_national", col]].dropna()
            rows.append({"year": year, "lag": lag, "n": len(pair),
                         "rho": pair["pm25_national"].corr(pair[col], method="spearman")})
    return pd.DataFrame(rows)


def make_scatter_regression():
    d = load("drivers_daily")
    corr = correlations().query("lag == 0").set_index("year")["rho"]
    fig = make_subplots(rows=1, cols=4, shared_yaxes=True, horizontal_spacing=0.025,
                        subplot_titles=[f"{y}   ρ = {corr[y]:.2f}" for y in HAZE_YEARS])
    for k, year in enumerate(HAZE_YEARS):
        g = d[(d["year"] == year) & (d["hotspots_total"] > 0)]
        x = np.log10(g["hotspots_total"])
        slope, intercept = np.polyfit(x, g["pm25_national"], 1)
        fig.add_trace(go.Scatter(
            x=g["hotspots_total"], y=g["pm25_national"], mode="markers",
            marker=dict(color=YEAR_COLOR[year], size=8, opacity=0.75, line=dict(color=SURFACE, width=1)),
            customdata=g["date"],
            hovertemplate="<b>%{customdata}</b><br>%{x} hotspots<br>PM2.5 %{y:.1f}<extra></extra>",
        ), row=1, col=k + 1)
        xs = np.linspace(x.min(), x.max(), 50)
        fig.add_trace(go.Scatter(x=10 ** xs, y=intercept + slope * xs, mode="lines",
                                 line=dict(color=INK, width=2), hoverinfo="skip"), row=1, col=k + 1)
        fig.update_xaxes(type="log", dtick=1, title_text="Hotspots / day (log)", row=1, col=k + 1)
    fig.update_yaxes(title_text=f"Daily PM2.5 ({UNIT})", col=1)
    for ann in fig.layout.annotations[:4]:
        ann.font = dict(size=17, color=INK)
    others = corr.drop(2026)
    title = (f"More hotspots mean higher PM2.5, but the link is weakest in 2026 "
             f"(ρ = {corr[2026]:.2f} vs {others.min():.2f}–{others.max():.2f})")
    assert corr.idxmin() == 2026
    sub = "Each dot is one day, 1 Jul – 31 Oct. Line = least-squares fit on log10(hotspots). ρ = Spearman"
    return style(fig, title, sub, legend=False)


def make_lag_bars():
    c = correlations()
    fig = go.Figure()
    for year in HAZE_YEARS:
        g = c[c["year"] == year]
        fig.add_trace(go.Bar(
            x=[f"Lag {lag} day{'s' if lag != 1 else ''}" for lag in g["lag"]], y=g["rho"], name=str(year),
            marker=dict(color=YEAR_COLOR[year], line=dict(color=SURFACE, width=2)),
            customdata=g["n"],
            hovertemplate=f"{year} · %{{x}}<br>ρ = %{{y:.2f}} (n = %{{customdata}} days)<extra></extra>",
        ))
    best = c.loc[c.groupby("year")["rho"].idxmax()].set_index("year")["lag"]
    spread = c.groupby("year")["rho"].agg(lambda s: s.max() - s.min())
    fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.05)
    fig.update_yaxes(title_text="Spearman ρ (PM2.5 vs hotspots)", range=[0, 1])
    title = f"No clear lead time: correlation changes by ≤ {spread.max():.2f} across lags 0–3 days"
    sub = ("Hotspots on day t − lag vs PM2.5 on day t. Strongest lag: "
           + ", ".join(f"{y} → {best[y]}" for y in HAZE_YEARS))
    return style(fig, title, sub)


def grid_hotspots(year, cell=0.25):
    pts = load("firms_hotspots", parse_dates=["date_sgt"])
    pts = pts[pts["year"] == year].copy()
    pts["lat"] = (np.floor(pts["latitude"] / cell) + 0.5) * cell
    pts["lon"] = (np.floor(pts["longitude"] / cell) + 0.5) * cell
    return pts.groupby(["date_sgt", "lat", "lon"]).size().rename("count").reset_index()


def make_hotspot_map(year, show_date=None, controls=True, days_per_frame=1):
    grid = grid_hotspots(year)
    pm = load("pm25_daily", parse_dates=["date"])
    pm = pm[pm["date"].between(f"{year}-07-01", f"{year}-10-31")]
    days = pd.date_range(f"{year}-07-01", f"{year}-10-31")
    windows = [(d, min(d + pd.Timedelta(days=days_per_frame - 1), days[-1])) for d in days[::days_per_frame]]
    size = lambda c: 4 + 3.2 * np.sqrt(c / days_per_frame)

    def in_window(frame, w):
        return frame[frame["date_sgt" if "date_sgt" in frame else "date"].between(*w)]

    def map_trace(w):
        g = in_window(grid, w).groupby(["lat", "lon"])["count"].sum().reset_index()
        return go.Scattergeo(
            lon=g["lon"], lat=g["lat"], mode="markers",
            marker=dict(size=size(g["count"]), color=HOTSPOT, opacity=0.55, line=dict(width=0)),
            customdata=g["count"], hovertemplate="%{customdata} hotspots in this 0.25° cell<extra></extra>",
        )

    def marker_trace(w):
        p = in_window(pm, w)
        return go.Scatter(x=p["date"], y=p["pm25_national"], mode="lines+markers", hoverinfo="skip",
                          line=dict(color=YEAR_COLOR[year], width=6),
                          marker=dict(size=14 if days_per_frame == 1 else 6, color=YEAR_COLOR[year],
                                      line=dict(color=SURFACE, width=2)))

    def caption(w):
        p = in_window(pm, w)["pm25_national"]
        hotspots = int(in_window(grid, w)["count"].sum())
        if days_per_frame == 1:
            pm_text = f"{p.iloc[0]:.0f} {UNIT}" if len(p) else "n/a"
            return f"<b>{w[0]:%d %b %Y}</b>   ·   {hotspots:,} hotspots   ·   Singapore PM2.5 {pm_text}"
        return (f"<b>{w[0]:%d %b} to {w[1]:%d %b %Y}</b>   ·   {hotspots:,} hotspots   ·   "
                f"Singapore PM2.5 up to {p.max():.0f} {UNIT}")

    start = (show_date, show_date) if show_date is not None else windows[0]
    fig = make_subplots(rows=1, cols=2, column_widths=[0.62, 0.38], horizontal_spacing=0.07,
                        specs=[[{"type": "geo"}, {"type": "xy"}]])
    fig.add_trace(map_trace(start), row=1, col=1)
    fig.add_trace(go.Scattergeo(lon=[103.82], lat=[1.35], mode="markers+text", text=["Singapore"],
                                textposition="top center", textfont=dict(size=15, color=INK),
                                marker=dict(size=11, color=INK, symbol="star"), hoverinfo="skip"),
                  row=1, col=1)
    fig.add_trace(go.Scatter(x=pm["date"], y=pm["pm25_national"], mode="lines",
                             line=dict(color=YEAR_COLOR[year], width=2),
                             hovertemplate=f"%{{x|%d %b}}<br>%{{y:.1f}} {UNIT}<extra></extra>"),
                  row=1, col=2)
    fig.add_trace(marker_trace(start), row=1, col=2)
    fig.add_shape(type="line", xref="x domain", x0=0, x1=1, yref="y", y0=UNHEALTHY, y1=UNHEALTHY,
                  line=dict(color=MUTED, width=1.2, dash="dot"))
    fig.add_annotation(xref="x domain", x=0, yref="y", y=UNHEALTHY, text="Unhealthy", showarrow=False,
                       xanchor="left", yanchor="bottom", font=dict(size=13, color=MUTED))
    fig.update_geos(
        projection_type="mercator", resolution=50, lonaxis_range=[94.5, 119.5], lataxis_range=[-6.5, 6.5],
        showland=True, landcolor=LAND, showocean=True, oceancolor="#eef3f8", showlakes=False,
        showcountries=True, countrycolor=AXIS, coastlinecolor=AXIS, bgcolor=SURFACE,
    )
    fig.update_yaxes(title_text=f"Singapore PM2.5 ({UNIT})", rangemode="tozero", row=1, col=2)
    fig.update_xaxes(tickformat="%b", dtick="M1", row=1, col=2)
    fig.add_annotation(xref="paper", yref="paper", x=0, y=1.0, yanchor="bottom", showarrow=False,
                       text=caption(start), font=dict(size=17, color=INK), name="caption")

    if show_date is None:
        frames = []
        for w in windows:
            frames.append(go.Frame(
                name=f"{w[0]:%m-%d}", data=[map_trace(w), marker_trace(w)], traces=[0, 3],
                layout=dict(annotations=[a.to_plotly_json() for a in fig.layout.annotations[:-1]]
                            + [dict(fig.layout.annotations[-1].to_plotly_json(), text=caption(w))]),
            ))
        fig.frames = frames
    if show_date is None and controls:
        step_args = lambda name, dur: [[name], dict(mode="immediate", frame=dict(duration=dur, redraw=True),
                                                     transition=dict(duration=0))]
        fig.update_layout(
            updatemenus=[dict(type="buttons", direction="left", x=0, xanchor="left", y=-0.13, yanchor="top",
                              pad=dict(t=8), font=dict(size=15), bgcolor="white", bordercolor=AXIS,
                              buttons=[
                                  dict(label="▶ Play", method="animate",
                                       args=[None, dict(frame=dict(duration=140, redraw=True), fromcurrent=True,
                                                        transition=dict(duration=0))]),
                                  dict(label="❚❚ Pause", method="animate", args=step_args(None, 0)),
                              ])],
            sliders=[dict(active=0, x=0.17, len=0.83, y=-0.11, yanchor="top", pad=dict(t=6),
                          currentvalue=dict(visible=False), font=dict(size=12, color=MUTED),
                          tickcolor=AXIS, bordercolor=AXIS,
                          steps=[dict(label=f"{day:%d %b}" if day.day in (1, 15) else "", method="animate",
                                      args=step_args(f"{day:%m-%d}", 0)) for day in days])],
        )
    title = f"Hotspots spread across Sumatra and Kalimantan, Jul–Oct {year}"
    sub = ("Circle area ∝ hotspots per 0.25° cell per day" + (", averaged over each week" if days_per_frame == 7 else "")
           + " (MODIS, confidence ≥ 30, Singapore time)")
    style(fig, title, sub, legend=False)
    fig.update_layout(margin=dict(l=20, r=40, t=135, b=115 if show_date is None and controls else 40))
    return fig


def make_oni_timeline():
    c = load("climate_monthly")
    c = c[c["oni"].notna()].copy()
    c["date"] = pd.to_datetime(c["month"] + "-01")
    c["phase"] = np.select([c["oni"] >= 0.5, c["oni"] <= -0.5], ["El Niño (≥ 0.5)", "La Niña (≤ −0.5)"],
                           "Neutral")
    fig = go.Figure()
    for phase, color in [("El Niño (≥ 0.5)", EL_NINO), ("Neutral", NEUTRAL), ("La Niña (≤ −0.5)", LA_NINA)]:
        g = c[c["phase"] == phase]
        fig.add_trace(go.Bar(x=g["date"], y=g["oni"], name=phase, marker=dict(color=color, line=dict(width=0)),
                             customdata=g["oni_season"],
                             hovertemplate="%{x|%b %Y} (%{customdata})<br>ONI %{y:.1f}<extra></extra>"))
    for year in HAZE_YEARS:
        fig.add_vrect(x0=f"{year}-07-01", x1=f"{year}-10-31", fillcolor=YEAR_COLOR[year], opacity=0.18,
                      line_width=0, annotation_text=str(year), annotation_position="top left",
                      annotation_font=dict(size=14, color=YEAR_COLOR[year]))
    fig.add_hline(y=0, line=dict(color=AXIS, width=1))
    fig.update_layout(barmode="overlay", bargap=0)
    fig.update_xaxes(range=["1995-01-01", "2026-12-31"], rangeslider=dict(visible=True, thickness=0.06))
    fig.update_yaxes(title_text="Oceanic Niño Index (°C)")
    since = c[(c["date"] > "2016-06-30")]
    peak26 = c.loc[c["date"].dt.year == 2026, "oni"].max()
    assert peak26 >= since["oni"].max()
    title = f"The 2026 El Niño (ONI {peak26:.1f}) is the strongest since 2015–16"
    sub = "NOAA ONI by month (3-month centred season); shaded = haze season Jul–Oct. Drag the slider to zoom"
    return style(fig, title, sub)


def make_rain_vs_pm25():
    c = load("climate_monthly")
    c = c[c["month"] >= "2014-04"].copy()
    c["date"] = pd.to_datetime(c["month"] + "-01")
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08)
    rain = c[c["rainfall_anom_pct"].notna()]
    fig.add_trace(go.Bar(
        x=rain["date"], y=rain["rainfall_anom_pct"], name="Rainfall vs normal",
        marker=dict(color=np.where(rain["rainfall_anom_pct"] < 0, EL_NINO, LA_NINA), line=dict(width=0)),
        customdata=rain["rainfall_mm"],
        hovertemplate="%{x|%b %Y}<br>%{customdata:.0f} mm (%{y:+.0f}% vs 1991–2020)<extra></extra>",
    ), row=1, col=1)
    fig.add_trace(go.Scatter(x=c["date"], y=c["pm25_monthly"], mode="lines", line=dict(color=INK_2, width=2),
                             hovertemplate=f"%{{x|%b %Y}}<br>PM2.5 %{{y:.1f}} {UNIT}<extra></extra>"),
                  row=2, col=1)
    for year in HAZE_YEARS:
        for row in (1, 2):
            fig.add_vrect(x0=f"{year}-07-01", x1=f"{year}-10-31", fillcolor=YEAR_COLOR[year], opacity=0.15,
                          line_width=0, row=row, col=1)
        fig.add_annotation(x=f"{year}-09-01", y=1, xref="x", yref="paper", text=f"{year} haze period",
                           showarrow=False,
                           yanchor="bottom", font=dict(size=14, color=YEAR_COLOR[year]))
    fig.update_yaxes(title_text="Rainfall vs normal (%)", zeroline=True, zerolinecolor=AXIS, row=1, col=1)
    fig.update_yaxes(title_text=f"Monthly PM2.5 ({UNIT})", rangemode="tozero", row=2, col=1)
    aug = c.set_index("month").loc["2026-08", "rainfall_anom_pct"]
    title = f"Haze months are dry months: Aug 2026 rainfall was {abs(aug):.0f}% below normal"
    sub = "Top: Changi monthly rainfall vs 1991–2020 mean for that month (red = drier). Bottom: monthly mean PM2.5"
    return style(fig, title, sub, legend=False)


def make_oni_vs_p99():
    a = load("annual_summary")
    a = a[a["pm25_p99_official"].notna()]
    nino = a["elnino_months_jaso"] >= 2
    fig = go.Figure()
    for flag, name, color in [(False, "Other years", NEUTRAL), (True, "El Niño in ≥ 2 of the 4 haze months", EL_NINO)]:
        g = a[nino == flag]
        fig.add_trace(go.Scatter(
            x=g["oni_jaso_mean"], y=g["pm25_p99_official"], mode="markers+text", name=name,
            text=[str(y) if (flag or v > 50) else "" for y, v in zip(g["year"], g["pm25_p99_official"])],
            textposition="middle right", textfont=dict(size=14, color=INK_2),
            marker=dict(size=13, color=color, line=dict(color=SURFACE, width=2)),
            customdata=g["year"],
            hovertemplate="<b>%{customdata}</b><br>Jul–Oct ONI %{x:.2f}<br>99th pct %{y} " + UNIT + "<extra></extra>",
        ))
    fig.add_vline(x=0.5, line=dict(color=MUTED, width=1.2, dash="dot"), annotation_text="El Niño threshold",
                  annotation_position="top right", annotation_font=dict(size=14, color=MUTED))
    fig.update_xaxes(title_text="Mean ONI, Jul–Oct", zeroline=False)
    fig.update_yaxes(title_text=f"99th percentile of daily PM2.5 ({UNIT})", rangemode="tozero")
    r = a["oni_jaso_mean"].corr(a["pm25_p99_official"], method="spearman")
    title = f"Stronger El Niño years tend to have worse haze extremes, but the link is loose (ρ = {r:.2f})"
    sub = "Official yearly 99th percentile of 24-h PM2.5 (SingStat). 2013's haze came in June, outside this window"
    return style(fig, title, sub)


def make_enso_events():
    e = load("enso_pm25")
    e["label"] = [f"{s[:7]} → {'now' if o else x[:7]}" for s, x, o in zip(e["event_start"], e["event_end"], e["is_ongoing"])]
    fig = go.Figure(go.Scatter(
        x=e["peak_oni"], y=e["pm25_p99"], mode="markers+text", text=e["label"],
        textposition=["middle left" if v > 2.3 else "middle right" for v in e["peak_oni"]],
        textfont=dict(size=15, color=INK_2),
        marker=dict(size=[18 if o else 14 for o in e["is_ongoing"]], color=EL_NINO,
                    symbol=["circle-open" if o else "circle" for o in e["is_ongoing"]],
                    line=dict(color=EL_NINO, width=3)),
        customdata=np.column_stack([e["unhealthy_days"], e["peak_daily"]]),
        hovertemplate="Peak ONI %{x}<br>99th pct PM2.5 %{y:.0f} " + UNIT
                      + "<br>Unhealthy days %{customdata[0]}<br>Peak day %{customdata[1]:.0f}<extra></extra>",
    ))
    fig.update_xaxes(title_text="Peak ONI of the El Niño event", range=[0.6, 2.9])
    fig.update_yaxes(title_text=f"99th percentile of daily PM2.5 during event ({UNIT})", rangemode="tozero")
    title = "Only the two strongest El Niño events (2015, 2026) brought unhealthy haze"
    big = e[e["unhealthy_days"] > 0]["peak_oni"]
    assert len(big) == 2 and big.min() >= e["peak_oni"].nlargest(3).iloc[-1]
    sub = "El Niño events since 2014 (NOAA: ONI ≥ 0.5 for ≥ 5 seasons). Open circle = still running, data to 31 Oct"
    return style(fig, title, sub, legend=False)


def make_annual_trend():
    a = load("annual_summary")
    fig = go.Figure()
    off = a[a["pm25_mean_official"].notna()]
    bg = a[a["pm25_mean_background"].notna()]
    fig.add_trace(go.Scatter(x=off["year"], y=off["pm25_mean_official"], name="Annual mean (official)",
                             mode="lines+markers", line=dict(color=INK_2, width=2.2), marker=dict(size=8),
                             hovertemplate=f"%{{x}}: %{{y}} {UNIT}<extra>Annual mean</extra>"))
    partial = bg["n_days"] < 365
    fig.add_trace(go.Scatter(
        x=bg["year"], y=bg["pm25_mean_background"], name="Background (haze days removed)",
        mode="lines+markers", line=dict(color=BACKGROUND_LINE, width=2.2),
        marker=dict(size=9, symbol=np.where(partial, "circle-open", "circle"), line=dict(width=2)),
        customdata=np.column_stack([bg["haze_days_excluded"], bg["n_days"]]),
        hovertemplate="%{x}: %{y:.1f} " + UNIT + "<br>%{customdata[0]:.0f} haze days removed of "
                      "%{customdata[1]:.0f}<extra>Background</extra>"))
    fig.add_hline(y=WHO_ANNUAL, line=dict(color=MUTED, width=1.2, dash="dot"),
                  annotation_text=f"WHO annual guideline ({WHO_ANNUAL})", annotation_position="top left",
                  annotation_font=dict(size=14, color=MUTED))
    fig.update_xaxes(dtick=2, title_text="")
    fig.update_yaxes(title_text=f"PM2.5 ({UNIT})", range=[0, 26])
    full = bg[~partial]
    ratio = full["pm25_mean_background"].min() / WHO_ANNUAL
    title = f"Even without haze days, Singapore's PM2.5 stays ≥ {ratio:.1f}× the WHO guideline"
    sub = ("Haze day = daily mean ≥ 30. Background from 2014 (hourly data start); "
           "open markers = partial year (2014 from Apr, 2026 to Oct)")
    return style(fig, title, sub)


def make_background_vs_extreme():
    a = load("annual_summary")
    a = a[a["pm25_p99_official"].notna()]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=a["year"], y=a["pm25_mean_official"], name="Annual mean", mode="lines+markers",
                             line=dict(color=INK_2, width=2.2), marker=dict(size=8),
                             hovertemplate=f"%{{x}}: %{{y}} {UNIT}<extra>Annual mean</extra>"))
    fig.add_trace(go.Scatter(x=a["year"], y=a["pm25_p99_official"], name="99th percentile day",
                             mode="lines+markers", line=dict(color=EL_NINO, width=2.2), marker=dict(size=8),
                             hovertemplate=f"%{{x}}: %{{y}} {UNIT}<extra>99th percentile</extra>"))
    for _, r in a.nlargest(2, "pm25_p99_official").iterrows():
        fig.add_annotation(x=r["year"], y=r["pm25_p99_official"], text=f"{r['year']:.0f}: {r['pm25_p99_official']:.0f}",
                           showarrow=False, yshift=16, font=dict(size=15, color=INK))
    fig.update_xaxes(dtick=2)
    fig.update_yaxes(title_text=f"PM2.5 ({UNIT})", rangemode="tozero")
    title = "Everyday air changes slowly; haze shows up as spikes in the worst days"
    sub = "Official SingStat yearly statistics: annual mean vs 99th percentile of 24-h PM2.5, 2007–2025"
    return style(fig, title, sub)


def make_pollutant_index():
    a = load("annual_long")
    a = a[a["metric"] == "Annual Mean"]
    fig = go.Figure()
    change = {}
    for pollutant, color, name in [("PM2.5", INK_2, "PM2.5 (local + transboundary)"),
                                   ("NO2", NO2_LINE, "NO₂ (mostly local traffic)")]:
        g = a[a["pollutant"] == pollutant].sort_values("year")
        index = g["value"] / g["value"].iloc[0] * 100
        change[pollutant] = index.iloc[-1] - 100
        fig.add_trace(go.Scatter(x=g["year"], y=index, name=name, mode="lines+markers",
                                 line=dict(color=color, width=2.4), marker=dict(size=8),
                                 customdata=g["value"],
                                 hovertemplate="%{x}: index %{y:.0f} (%{customdata} " + UNIT + ")<extra></extra>"))
        fig.add_annotation(x=g["year"].iloc[-1], y=index.iloc[-1], text=f"<b>{change[pollutant]:+.0f}%</b>",
                           showarrow=False, xanchor="left", xshift=10, font=dict(size=16, color=color))
    fig.add_hline(y=100, line=dict(color=AXIS, width=1))
    fig.update_xaxes(dtick=2, range=[2006.5, 2026.3])
    fig.update_yaxes(title_text="Index (2007 = 100)")
    no2 = "unchanged" if abs(change["NO2"]) < 1 else f"{change['NO2']:+.0f}%"
    title = f"Since 2007 PM2.5 has fallen {abs(change['PM2.5']):.0f}%, while NO₂ is {no2}"
    sub = "Annual means indexed to 2007 (SingStat). Both measured in µg/m³; index puts them on one scale"
    return style(fig, title, sub)


FIGURES_LIST = [
    ("01_haze_season_overlay", make_season_overlay),
    ("02_calendar_heatmap", make_calendar),
    ("03_severity_table", make_metrics_table),
    ("04_region_boxplot", make_region_box),
    ("04b_region_unhealthy_days", make_region_bars),
    ("05_hotspots_vs_pm25", make_hotspots_vs_pm25),
    ("06_scatter_regression", make_scatter_regression),
    ("07_lag_correlation", make_lag_bars),
    ("08_oni_vs_p99", make_oni_vs_p99),
    ("08b_enso_events", make_enso_events),
    ("10_oni_timeline", make_oni_timeline),
    ("11_rain_vs_pm25", make_rain_vs_pm25),
    ("12_annual_trend_who", make_annual_trend),
    ("13_background_vs_extreme", make_background_vs_extreme),
    ("14_pollutant_index", make_pollutant_index),
]


def peak_hotspot_day(year):
    grid = grid_hotspots(year)
    return grid.groupby("date_sgt")["count"].sum().idxmax()


def main():
    FIGURES.mkdir(exist_ok=True)
    for name, build in FIGURES_LIST:
        build().write_image(FIGURES / f"{name}.png", scale=2)
        print(f"{name}.png")
    for year in HAZE_YEARS:
        day = peak_hotspot_day(year)
        make_hotspot_map(year, show_date=day).write_image(FIGURES / f"09_hotspot_map_{year}.png", scale=2)
        print(f"09_hotspot_map_{year}.png (peak day {day:%d %b})")


if __name__ == "__main__":
    main()
