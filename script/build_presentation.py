"""SD6105 Haze project: build the click-to-play slide deck used to record the video.

Writes presentation/haze_presentation.html: one 1280x720 slide per chart. On each slide
the first click (or Right arrow / Space) plays that chart's animation, the next click
moves on. Charts come from make_figures.py; plotly.js is embedded so it works offline.

Run from anywhere: python3 script/build_presentation.py
"""
import html
import json
from pathlib import Path

from plotly.offline import get_plotlyjs

import make_figures as mf

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "presentation" / "haze_presentation.html"

# Edit these before recording
TITLE = "When the Haze Returned"
SUBTITLE = "How bad was Singapore's 2026 haze, what drove it, and is our everyday air getting better?"
PRESENTERS = ["WANG YIJING", "WANG YIMING"]
COURSE = "SD6105 Data Visualisation · Group 47"

MITIGATION = [
    "Warn about long haze, not only high peaks. In 2026 the air stayed unhealthy for 16 days in a row.",
    "Prepare early in strong El Niño years and dry months. These are the seasons with the worst haze.",
    "Hotspots gave no clear signal one to three days ahead, so warnings also need wind and rain forecasts.",
    "Keep cleaning local air. Even without haze days, PM2.5 is more than twice the WHO guideline.",
    "Keep regional action going, such as the ASEAN Agreement on Transboundary Haze Pollution.",
]

# Each chart slide: (part, figure builder, animation steps played on the first click).
# Step ops are run by the JavaScript player below:
#   reveal  draw traces point by point     grow   raise bars from zero
#   fadein  show traces one after another  fill   fill a heatmap day by day
#   frames  play the figure's frames       late   show annotations and shapes named "late"
SLIDES = [
    (1, mf.make_season_overlay, [{"op": "reveal", "traces": [3], "ms": 6000}, {"op": "late"}]),
    (1, lambda: mf.make_calendar([2015, 2026]), [{"op": "fill", "trace": 1, "ms": 5000}]),
    (1, mf.make_region_bars, [{"op": "grow", "traces": [0], "ms": 1200}, {"op": "grow", "traces": [1], "ms": 1200}]),
    (2, lambda: mf.make_hotspot_map(2026, controls=False, days_per_frame=7), [{"op": "frames", "ms": 380}]),
    (2, mf.make_scatter_regression, [{"op": "fadein", "traces": [[0, 1], [2, 3], [4, 5], [6, 7]], "gap": 900}]),
    (2, mf.make_lag_bars, [{"op": "grow", "traces": [0, 1, 2, 3], "ms": 1500}]),
    (2, mf.make_rain_vs_pm25, [{"op": "reveal", "traces": [0, 1], "ms": 5000}]),
    (2, mf.make_enso_events, [{"op": "reveal", "traces": [0], "ms": 3000}]),
    (3, mf.make_annual_trend, [{"op": "reveal", "traces": [0], "ms": 2500}, {"op": "reveal", "traces": [1], "ms": 2500}]),
]

PARTS = {1: "Severity", 2: "Drivers", 3: "Long-term trend", 4: "Mitigation"}
PLOT_CONFIG = {"staticPlot": True, "responsive": False}


def render_title():
    names = " &nbsp;·&nbsp; ".join(html.escape(n) for n in PRESENTERS)
    return f"""<div class="text-slide">
  <div class="eyebrow">{html.escape(COURSE)}</div>
  <h1>{html.escape(TITLE)}</h1>
  <p class="lede">{html.escape(SUBTITLE)}</p>
  <p class="names">{names}</p>
</div>"""


def render_mitigation():
    items = "".join(f'<li class="step-item">{html.escape(t)}</li>' for t in MITIGATION)
    return f"""<div class="part-tag">Part 4 · {PARTS[4]}</div>
<div class="text-slide">
  <h2>What this means for Singapore</h2>
  <ol class="points">{items}</ol>
</div>"""


def render_end():
    sources = ("Data: NEA hourly PM2.5 and rainfall (data.gov.sg) · NASA FIRMS MODIS hotspots · "
               "SingStat annual air pollution · NOAA Oceanic Niño Index")
    return f"""<div class="text-slide end">
  <h1>Thank you</h1>
  <p class="lede">{html.escape(sources)}</p>
  <p class="note">Hotspots are satellite heat detections, not fire size or smoke direction.
  Correlation is not causation.</p>
</div>"""


CSS = """
:root { --surface: #fcfcfb; --plane: #1a1a19; --ink: #0b0b0b; --ink-2: #52514e; --muted: #898781;
        --accent: #eb6834; }
* { box-sizing: border-box; }
html, body { margin: 0; height: 100%; background: var(--plane);
             font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: var(--ink); }
body { display: flex; align-items: center; justify-content: center; overflow: hidden; cursor: pointer; }
#deck { position: relative; width: 1280px; height: 720px; flex: none; background: var(--surface); overflow: hidden; }
.slide { position: absolute; inset: 0; visibility: hidden; }
.slide.active { visibility: visible; }
.part-tag { position: absolute; top: 12px; right: 24px; font-size: 13px; letter-spacing: .08em;
            text-transform: uppercase; color: var(--muted); z-index: 2; }
.chart { position: absolute; left: 20px; top: 70px; width: 1240px; height: 600px; }
.text-slide { padding: 120px 120px 0; }
.eyebrow { font-size: 18px; letter-spacing: .1em; text-transform: uppercase; color: var(--accent); font-weight: 600; }
h1 { font-size: 76px; line-height: 1.05; margin: 22px 0 26px; }
h2 { font-size: 48px; margin: 0 0 30px; }
.lede { font-size: 28px; line-height: 1.35; color: var(--ink-2); max-width: 1000px; margin: 0; }
.names { font-size: 26px; margin-top: 70px; }
.points { font-size: 27px; line-height: 1.35; padding-left: 36px; margin: 0; max-width: 1040px; }
.points li { margin-bottom: 20px; opacity: 0; transition: opacity .6s; }
.points li.shown { opacity: 1; }
.end h1 { margin-top: 60px; }
.note { font-size: 20px; color: var(--muted); margin-top: 30px; }
#counter { position: fixed; right: 16px; bottom: 12px; font-size: 13px; color: #898781; }
body.clean #counter { display: none; }
"""

PLAYER_JS = """
const slides = [...document.querySelectorAll('.slide')];
const charts = {};          // slide index -> {div, fig, steps}
let current = 0, played = false, playing = false;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const copy = (o) => JSON.parse(JSON.stringify(o));
const ARRAY_KEYS = ['x', 'y', 'text', 'customdata', 'textposition', 'marker.size', 'marker.symbol', 'marker.color'];

function get(obj, key) { return key.split('.').reduce((o, k) => (o == null ? undefined : o[k]), obj); }

function slicedUpdate(trace, n) {
  const upd = {}, len = (trace.x || trace.y || []).length;
  for (const key of ARRAY_KEYS) {
    const v = get(trace, key);
    if (Array.isArray(v) && v.length === len) upd[key] = [v.slice(0, n)];
  }
  return upd;
}

async function drawPlot(entry) {
  const fig = copy(entry.fig);
  await Plotly.newPlot(entry.div, {data: fig.data, layout: fig.layout, frames: fig.frames || [],
                                  config: CONFIG});
  // Freeze every axis so traces appearing later do not rescale the chart
  const fixed = {}, full = entry.div._fullLayout;
  for (const key of Object.keys(full)) {
    if (/^[xy]axis\\d*$/.test(key) && full[key].range) {
      fixed[key + '.range'] = full[key].range.slice();
      fixed[key + '.autorange'] = false;
    }
  }
  await Plotly.relayout(entry.div, fixed);
  // Base state: what the slide shows before its first click
  for (const step of entry.steps) {
    if (step.op === 'reveal') for (const t of step.traces) await Plotly.restyle(entry.div, slicedUpdate(entry.fig.data[t], 0), [t]);
    if (step.op === 'grow') for (const t of step.traces)
      await Plotly.restyle(entry.div, {y: [entry.fig.data[t].y.map(() => 0)], text: [entry.fig.data[t].y.map(() => '')]}, [t]);
    if (step.op === 'fadein') for (const group of step.traces) await Plotly.restyle(entry.div, {visible: false}, group);
    if (step.op === 'fill') await Plotly.restyle(entry.div, {z: [entry.fig.data[step.trace].z.map((row) => row.map(() => null))]}, [step.trace]);
    if (step.op === 'late') await setLate(entry, false);
  }
}

async function setLate(entry, visible) {
  const upd = {};
  for (const kind of ['annotations', 'shapes']) {
    (entry.div.layout[kind] || []).forEach((a, i) => { if (a.name === 'late') upd[`${kind}[${i}].visible`] = visible; });
  }
  if (Object.keys(upd).length) await Plotly.relayout(entry.div, upd);
}

async function runStep(entry, step) {
  const div = entry.div, data = entry.fig.data;
  if (step.op === 'reveal') {
    const n = Math.max(...step.traces.map((t) => (data[t].x || data[t].y).length));
    const ticks = Math.min(n, 120);
    for (let k = 1; k <= ticks; k++) {
      const upto = Math.round(n * k / ticks);
      for (const t of step.traces) await Plotly.restyle(div, slicedUpdate(data[t], upto), [t]);
      await sleep(step.ms / ticks);
    }
  } else if (step.op === 'grow') {
    const ticks = 30;
    for (let k = 1; k <= ticks; k++) {
      const f = 1 - Math.pow(1 - k / ticks, 3);  // ease out
      await Plotly.restyle(div, {y: step.traces.map((t) => data[t].y.map((v) => v * f))}, step.traces);
      await sleep(step.ms / ticks);
    }
    const text = step.traces.map((t) => data[t].text);
    if (text.some(Boolean)) await Plotly.restyle(div, {text}, step.traces);
  } else if (step.op === 'fadein') {
    for (const group of step.traces) { await Plotly.restyle(div, {visible: true}, group); await sleep(step.gap); }
  } else if (step.op === 'fill') {
    const tr = data[step.trace], z = tr.z.map((row) => row.map(() => null));
    const days = Math.max(...tr.customdata.flat().map((c) => (c && c[2] != null ? c[2] : -1)));
    for (let d = 0; d <= days; d++) {
      tr.customdata.forEach((row, i) => row.forEach((c, j) => { if (c && c[2] === d) z[i][j] = tr.z[i][j]; }));
      await Plotly.restyle(div, {z: [z.map((r) => r.slice())]}, [step.trace]);
      await sleep(step.ms / (days + 1));
    }
  } else if (step.op === 'frames') {
    // Apply each frame with restyle/relayout: same result as Plotly.animate, but never stalls
    for (const frame of entry.fig.frames) {
      const upd = {};
      for (const key of ['lon', 'lat', 'x', 'y', 'customdata', 'marker.size']) {
        if (frame.data.some((d) => get(d, key) !== undefined)) upd[key] = frame.data.map((d) => get(d, key));
      }
      const layout = frame.layout && frame.layout.annotations ? {annotations: frame.layout.annotations} : {};
      await Plotly.update(div, upd, layout, frame.traces);  // one redraw per frame
      await sleep(step.ms);
    }
  } else if (step.op === 'late') {
    await setLate(entry, true);
  }
}

async function play() {
  playing = true;
  const slide = slides[current];
  if (charts[current]) for (const step of charts[current].steps) await runStep(charts[current], step);
  for (const li of slide.querySelectorAll('.step-item')) { li.classList.add('shown'); await sleep(1400); }
  playing = false; played = true;
}

async function show(i) {
  current = Math.max(0, Math.min(slides.length - 1, i));
  slides.forEach((s, k) => s.classList.toggle('active', k === current));
  slides[current].querySelectorAll('.step-item').forEach((li) => li.classList.remove('shown'));
  if (charts[current]) await drawPlot(charts[current]);
  const hasDemo = (charts[current] && charts[current].steps.length) || slides[current].querySelector('.step-item');
  played = !hasDemo;
  document.getElementById('counter').textContent = `${current + 1} / ${slides.length}  ·  H hides this`;
  history.replaceState(null, '', '#' + (current + 1));
}

function next() {
  if (playing) return;
  if (!played) play(); else show(current + 1);
}

document.addEventListener('click', next);
document.addEventListener('keydown', (e) => {
  if (['ArrowRight', 'PageDown', ' ', 'Enter'].includes(e.key)) { next(); e.preventDefault(); }
  else if (['ArrowLeft', 'PageUp'].includes(e.key)) { if (!playing) show(current - 1); e.preventDefault(); }
  else if (e.key === 'r' || e.key === 'R') { if (!playing) show(current); }
  else if (e.key === 'h' || e.key === 'H') document.body.classList.toggle('clean');
  else if (e.key === 'f' || e.key === 'F') {
    document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen();
  }
});

for (const [idx, spec] of Object.entries(CHARTS)) {
  charts[idx] = {div: document.getElementById('chart-' + idx), fig: spec.fig, steps: spec.steps};
}
show((parseInt(location.hash.slice(1)) || 1) - 1);
"""


def main():
    OUT.parent.mkdir(exist_ok=True)
    sections, chart_specs = [render_title()], {}
    for part, build, steps in SLIDES:
        idx = len(sections)
        chart_specs[idx] = {"fig": json.loads(build().to_json()), "steps": steps}
        sections.append(f'<div class="part-tag">Part {part} · {PARTS[part]}</div><div class="chart" id="chart-{idx}"></div>')
        print(f"slide {idx + 1}: Part {part} chart")
    sections += [render_mitigation(), render_end()]

    body = "\n".join(f'<section class="slide" id="s{n + 1}">{inner}</section>' for n, inner in enumerate(sections))
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(TITLE)}</title>
<style>{CSS}</style>
<script>{get_plotlyjs()}</script>
</head>
<body>
<div id="deck">
{body}
</div>
<div id="counter"></div>
<script>const CONFIG = {json.dumps(PLOT_CONFIG)};
const CHARTS = {json.dumps(chart_specs, separators=(",", ":"))};</script>
<script>{PLAYER_JS}</script>
</body>
</html>"""
    OUT.write_text(page, encoding="utf-8")
    print(f"{OUT.relative_to(ROOT)}: {len(page) / 1e6:.1f} MB, {len(sections)} slides")


if __name__ == "__main__":
    main()
