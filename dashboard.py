import pandas as pd
import json, os, glob

LOGS_DIR = "logs"
OUT      = "dashboard.html"

# ── format detection ──────────────────────────────────────────────────────────

def detect_format(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        header = f.readline()
    if "SECONDS" in header.upper() and ";" in header:
        return "long"
    if header.upper().startswith("TIME"):
        return "wide"
    return "unknown"

# ── long format (BimmerLink semicolon / long export) ─────────────────────────

LONG_PID = {
    "rpm":        ["Engine RPM", "Engine RPM x1000"],
    "speed":      ["Vehicle speed"],
    "throttle":   ["Throttle position"],
    "coolant":    ["Engine coolant temperature"],
    "maf":        ["MAF air flow rate"],
    "power":      ["Instant engine power (based on fuel consumption)"],
    "boost":      ["Calculated boost"],
    "intake_temp":["Intake air temperature"],
    "timing":     ["Timing advance"],
    "accel":      ["Vehicle acceleration"],
}

def load_long(path):
    df = pd.read_csv(path, sep=";", quotechar='"', header=0)
    df = df[["SECONDS", "PID", "VALUE"]]
    df["SECONDS"] = pd.to_numeric(df["SECONDS"], errors="coerce")
    df["VALUE"]   = pd.to_numeric(df["VALUE"],   errors="coerce")
    return df.dropna(subset=["SECONDS", "VALUE"])

def pivot_long(df):
    df = df.copy()
    df["SEC"] = df["SECONDS"].round(0).astype(int)
    p = df.pivot_table(index="SEC", columns="PID", values="VALUE", aggfunc="mean")
    return p.ffill(limit=5)

def to_clock(s):
    s = int(s)
    return f"{s // 3600 % 24:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"

def build_long(p):
    timeline = [to_clock(s) for s in p.index]
    all_data, meta = {}, {}
    for key, pids in LONG_PID.items():
        for pid in pids:
            if pid not in p.columns:
                continue
            col  = p[pid]
            vals = [round(float(v), 2) if pd.notna(v) else None for v in col]
            if key == "rpm" and pid == "Engine RPM x1000":
                vals = [round(v * 1000, 0) if v is not None else None for v in vals]
            valid = [v for v in vals if v is not None]
            if not valid:
                continue
            all_data[key] = vals
            meta[key] = {"min": round(min(valid), 2), "max": round(max(valid), 2)}
            break
    return timeline, all_data, meta

# ── wide format (BimmerLink wide / comma export) ──────────────────────────────

WIDE_PID = {
    "rpm":          ["Engine speed"],
    "speed":        ["Actual speed"],
    "throttle":     ["Throttle valve angle from potentiometer 1"],
    "boost":        ["Boost pressure"],
    "coolant":      ["Coolant temperature"],
    "maf":          ["Air mass flow"],
    "intake_temp":  ["Intake air temperature"],
    "oil_temp":     ["Oil temperature"],
    "oil_pressure": ["Oil pressure"],
    "voltage":      ["Current battery voltage"],
}

def load_wide(path):
    df = pd.read_csv(path, header=0)
    df.columns = [c.strip().strip('"') for c in df.columns]
    df["Time"] = pd.to_numeric(df["Time"], errors="coerce")
    return df.dropna(subset=["Time"])

def pivot_wide(df):
    df = df.copy()
    df["SEC"] = df["Time"].round(0).astype(int)
    num_cols = [c for c in df.select_dtypes(include="number").columns
                if c not in ("Time", "SEC")]
    p = df.groupby("SEC")[num_cols].mean()
    return p.ffill(limit=5)

def to_elapsed(s):
    s = int(s)
    return f"{s // 60}:{s % 60:02d}"

def build_wide(p):
    timeline = [to_elapsed(s) for s in p.index]
    all_data, meta = {}, {}
    for key, col_names in WIDE_PID.items():
        for col in col_names:
            if col not in p.columns:
                continue
            vals  = [round(float(v), 2) if pd.notna(v) else None for v in p[col]]
            valid = [v for v in vals if v is not None]
            if not valid:
                continue
            all_data[key] = vals
            meta[key] = {"min": round(min(valid), 2), "max": round(max(valid), 2)}
            break
    return timeline, all_data, meta

# ── load all logs ─────────────────────────────────────────────────────────────

def load_all_logs(logs_dir):
    logs = {}
    for path in sorted(glob.glob(os.path.join(logs_dir, "*.csv"))):
        name = os.path.basename(path).replace(".csv", "")
        fmt  = detect_format(path)
        print(f"  {name}  [{fmt}]")
        try:
            if fmt == "long":
                tl, ad, m = build_long(pivot_long(load_long(path)))
            elif fmt == "wide":
                tl, ad, m = build_wide(pivot_wide(load_wide(path)))
            else:
                print("    skipped (unknown format)"); continue
            logs[name] = {"timeline": tl, "all": ad, "meta": m}
            print(f"    {len(tl)} seconds, {len(ad)} metrics")
        except Exception as e:
            print(f"    error: {e}")
    return logs

# ── metrics definition ────────────────────────────────────────────────────────

METRICS = [
    ("rpm",         "Engine RPM",   "rpm", "#f97316"),
    ("speed",       "Speed",        "mph", "#38bdf8"),
    ("throttle",    "Throttle",     "%",   "#fb923c"),
    ("coolant",     "Coolant Temp", "°F",  "#f87171"),
    ("maf",         "MAF",          "g/s", "#a78bfa"),
    ("power",       "Power",        "hp",  "#4ade80"),
    ("boost",       "Boost",        "bar", "#facc15"),
    ("intake_temp", "Intake Temp",  "°F",  "#fb7185"),
    ("timing",      "Timing",       "°",   "#22d3ee"),
    ("accel",       "Accel",        "g",   "#e879f9"),
    ("oil_temp",    "Oil Temp",     "°F",  "#fbbf24"),
    ("oil_pressure","Oil Pressure", "bar", "#86efac"),
    ("voltage",     "Voltage",      "V",   "#94a3b8"),
]

# ── HTML ──────────────────────────────────────────────────────────────────────

def build_html(logs):
    first_key = next(iter(logs))
    first     = logs[first_key]
    t0        = first["timeline"][0]
    t1        = first["timeline"][-1]
    N         = len(first["timeline"]) - 1

    log_opts = "\n".join(
        f'<option value="{k}">{k}</option>' for k in logs
    )
    metric_defs_js = json.dumps([[k, l, u, c] for k, l, u, c in METRICS])

    chart_cards = "\n".join(
        f'<div class="chart-card" id="gccard-{key}">'
        f'<div class="chart-card-label">{label} <span class="chart-unit">({unit})</span></div>'
        f'<canvas id="gc-{key}"></canvas>'
        f'</div>'
        for key, label, unit, color in METRICS if key != "rpm"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BimmerLink Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ background: #0a0a0a; color: #e2e8f0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; padding: 24px; min-height: 100vh; }}
header {{ margin-bottom: 28px; }}
.header-row {{ display: flex; align-items: center; gap: 14px; margin-bottom: 18px; flex-wrap: wrap; }}
.log-label {{ font-size: .85rem; font-weight: 500; color: #475569; letter-spacing: .08em; text-transform: uppercase; white-space: nowrap; }}
.sep {{ color: #27272a; }}
.current-time {{ font-size: 1.5rem; font-weight: 700; color: #f8fafc; font-variant-numeric: tabular-nums; }}
select#log-select {{ margin-left: auto; padding: 6px 12px; border-radius: 7px; border: 1px solid #27272a; background: #111113; color: #e2e8f0; font-size: .82rem; cursor: pointer; outline: none; transition: border-color .15s; }}
select#log-select:hover, select#log-select:focus {{ border-color: #f97316; }}
.slider-row {{ display: flex; align-items: center; gap: 12px; }}
.bound-lbl {{ font-size: .7rem; color: #475569; font-variant-numeric: tabular-nums; white-space: nowrap; }}
.slider-wrap {{ position: relative; flex: 1; height: 6px; background: #1e1e23; border-radius: 3px; }}
.slider-progress {{ position: absolute; left: 0; top: 0; height: 100%; background: #f97316; border-radius: 3px; pointer-events: none; }}
#slider {{ position: absolute; width: 100%; height: 6px; appearance: none; background: transparent; outline: none; top: 0; left: 0; cursor: pointer; }}
#slider::-webkit-slider-thumb {{ appearance: none; width: 18px; height: 18px; border-radius: 50%; background: #f97316; border: 2px solid #0a0a0a; cursor: pointer; box-shadow: 0 0 0 3px #f9731630; }}
#slider::-moz-range-thumb {{ width: 18px; height: 18px; border-radius: 50%; background: #f97316; border: 2px solid #0a0a0a; cursor: pointer; }}
.controls {{ display: flex; align-items: center; gap: 10px; margin-top: 14px; }}
.btn-play {{ width: 36px; height: 36px; border-radius: 50%; border: none; cursor: pointer; background: #f97316; color: #0a0a0a; display: flex; align-items: center; justify-content: center; font-size: 1rem; flex-shrink: 0; transition: background .15s, transform .1s; }}
.btn-play:hover {{ background: #fb923c; transform: scale(1.08); }}
.speed-btns {{ display: flex; gap: 6px; }}
.btn-speed {{ padding: 5px 11px; border-radius: 6px; border: 1px solid #27272a; background: transparent; color: #64748b; font-size: .78rem; font-weight: 600; cursor: pointer; transition: background .12s, color .12s, border-color .12s; }}
.btn-speed:hover {{ background: #1e1e23; color: #94a3b8; }}
.btn-speed.active {{ background: #1e1e23; color: #f97316; border-color: #f97316; }}
@media (max-width: 700px) {{ .charts-grid {{ grid-template-columns: 1fr; }} }}
/* ── graph view ── */
.graph-rpm-wrap {{ background: #111113; border: 1px solid #1e1e23; border-radius: 14px; padding: 24px; margin-bottom: 20px; }}
.graph-rpm-label {{ font-size: 2rem; font-weight: 700; color: #f97316; margin-bottom: 14px; }}
.graph-rpm-wrap canvas {{ display: block; width: 100% !important; height: 260px !important; }}
.charts-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; }}
.chart-card {{ background: #111113; border: 1px solid #1e1e23; border-radius: 12px; padding: 20px; }}
.chart-card.no-data {{ opacity: 0.3; }}
.chart-card-label {{ font-size: .72rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: .09em; margin-bottom: 12px; }}
.chart-unit {{ color: #475569; font-weight: 400; text-transform: none; letter-spacing: 0; }}
.chart-card canvas {{ display: block; width: 100% !important; height: 150px !important; cursor: ew-resize; }}
.graph-rpm-wrap canvas {{ cursor: ew-resize; }}
@media (max-width: 700px) {{ .charts-grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>

<header>
  <div class="header-row">
    <span class="log-label">BimmerLink</span>
    <span class="sep">/</span>
    <span class="current-time" id="current-time">{t0}</span>
    <select id="log-select">{log_opts}</select>
  </div>
  <div class="slider-row">
    <span class="bound-lbl" id="lbl-start">{t0}</span>
    <div class="slider-wrap">
      <div class="slider-progress" id="slider-progress"></div>
      <input type="range" id="slider" min="0" max="{N}" value="0" step="1">
    </div>
    <span class="bound-lbl" id="lbl-end">{t1}</span>
  </div>
  <div class="controls">
    <button class="btn-play" id="btn-play">&#9654;</button>
    <div class="speed-btns">
      <button class="btn-speed" data-speed="0.5">0.5x</button>
      <button class="btn-speed active" data-speed="1">1x</button>
      <button class="btn-speed" data-speed="2">2x</button>
      <button class="btn-speed" data-speed="5">5x</button>
    </div>
  </div>
</header>

<div id="view-graph">
  <div class="graph-rpm-wrap">
    <div class="graph-rpm-label">Engine RPM</div>
    <canvas id="gc-rpm"></canvas>
  </div>
  <div class="charts-grid">{chart_cards}</div>
</div>

<script>
const LOGS        = {json.dumps(logs)};
const METRIC_DEFS = {metric_defs_js};

let TIMELINE = [], ALL = {{}}, META = {{}};

const slider   = document.getElementById("slider");
const progress = document.getElementById("slider-progress");
const timeEl   = document.getElementById("current-time");
const lblStart = document.getElementById("lbl-start");
const lblEnd   = document.getElementById("lbl-end");

function fmt(val, key) {{
  if (val === null || val === undefined) return "—";
  if (key === "rpm") return Math.round(val).toLocaleString();
  if (Math.abs(val) >= 100) return Math.round(val).toLocaleString();
  return (+val.toFixed(1)).toString();
}}

function pct(val, min, max) {{
  if (val === null || max === min) return 0;
  return Math.max(0, Math.min(100, (val - min) / (max - min) * 100));
}}

function update(i) {{
  timeEl.textContent = TIMELINE[i] || "—";
  progress.style.width = (i / Math.max(1, TIMELINE.length - 1) * 100) + "%";
  for (const [key] of METRIC_DEFS) {{
    const vEl = document.getElementById("v-" + key);
    const bEl = document.getElementById("b-" + key);
    if (!vEl) continue;
    const val = ALL[key] ? ALL[key][i] : null;
    vEl.textContent = fmt(val, key);
    if (bEl && META[key]) bEl.style.width = pct(val, META[key].min, META[key].max) + "%";
  }}
}}

function loadLog(key) {{
  stop();
  const log = LOGS[key];
  TIMELINE = log.timeline;
  ALL      = log.all;
  META     = log.meta;
  const N  = TIMELINE.length - 1;
  slider.max     = N;
  slider.value   = 0;
  graphSliderIdx = 0;
  lblStart.textContent = TIMELINE[0];
  lblEnd.textContent   = TIMELINE[N];

  for (const [key] of METRIC_DEFS) {{
    const minEl = document.getElementById("bmin-" + key);
    const maxEl = document.getElementById("bmax-" + key);
    const card  = document.getElementById("card-" + key);
    const has   = !!ALL[key];
    if (minEl) minEl.textContent = has ? fmt(META[key].min, key) : "";
    if (maxEl) maxEl.textContent = has ? fmt(META[key].max, key) : "";
    if (card)  card.classList.toggle("no-data", !has);
  }}
  const rMin = document.getElementById("bmin-rpm");
  const rMax = document.getElementById("bmax-rpm");
  if (rMin) rMin.textContent = ALL.rpm ? fmt(META.rpm.min, "rpm") : "";
  if (rMax) rMax.textContent = ALL.rpm ? fmt(META.rpm.max, "rpm") : "";

  update(0);
  requestAnimationFrame(renderCharts);
}}

document.getElementById("log-select").addEventListener("change", e => loadLog(e.target.value));
slider.addEventListener("input", () => {{
  const i = +slider.value;
  update(i);
  graphSliderIdx = i;
  for (const c of Object.values(chartInstances)) c.update("none");
}});

// ── playback ──
const btnPlay   = document.getElementById("btn-play");
const speedBtns = document.querySelectorAll(".btn-speed");
let playing = false, speed = 1, timer = null;

function interval() {{ return Math.round(1000 / speed); }}
function tick() {{
  const next = +slider.value + 1;
  if (next > +slider.max) {{ stop(); return; }}
  slider.value = next;
  graphSliderIdx = next;
  update(next);
  for (const c of Object.values(chartInstances)) c.update("none");
}}
function play() {{
  playing = true; btnPlay.innerHTML = "&#9646;&#9646;";
  if (+slider.value >= +slider.max) slider.value = 0;
  timer = setInterval(tick, interval());
}}
function stop() {{
  playing = false; btnPlay.innerHTML = "&#9654;";
  clearInterval(timer); timer = null;
}}
btnPlay.addEventListener("click", () => playing ? stop() : play());
speedBtns.forEach(btn => {{
  btn.addEventListener("click", () => {{
    speed = parseFloat(btn.dataset.speed);
    speedBtns.forEach(b => b.classList.toggle("active", b === btn));
    if (playing) {{ clearInterval(timer); timer = setInterval(tick, interval()); }}
  }});
}});

const chartInstances = {{}};
let graphSliderIdx  = 0;

loadLog("{first_key}");

// ── vertical scrub-line + value label plugin ──
Chart.register({{
  id: "scrubLine",
  afterDraw(chart) {{
    const xAxis = chart.scales.x;
    const yAxis = chart.scales.y;
    if (!xAxis || !yAxis || graphSliderIdx === null) return;
    const x = xAxis.getPixelForValue(graphSliderIdx);
    if (x < xAxis.left || x > xAxis.right) return;

    const key = chart.canvas.id.replace("gc-", "");
    const val = (ALL[key] && ALL[key][graphSliderIdx] != null)
                 ? ALL[key][graphSliderIdx] : null;

    const ctx = chart.ctx;
    ctx.save();

    // gray out future (right of line)
    ctx.fillStyle = "rgba(10, 10, 10, 0.55)";
    ctx.fillRect(x, yAxis.top, xAxis.right - x, yAxis.bottom - yAxis.top);

    // solid vertical line
    ctx.beginPath();
    ctx.moveTo(x, yAxis.top);
    ctx.lineTo(x, yAxis.bottom);
    ctx.lineWidth = 2;
    ctx.strokeStyle = "#f97316";
    ctx.stroke();

    // value badge at top of line
    if (val !== null) {{
      const text = fmt(val, key);
      ctx.font = "bold 11px -apple-system, BlinkMacSystemFont, sans-serif";
      const textW = ctx.measureText(text).width;
      const pad = 5, boxH = 18, boxW = textW + pad * 2;
      // clamp so badge stays inside chart area
      let bx = Math.max(xAxis.left, Math.min(xAxis.right - boxW, x - boxW / 2));
      const by = yAxis.top;
      ctx.fillStyle = "#f97316";
      ctx.beginPath();
      ctx.roundRect(bx, by, boxW, boxH, 3);
      ctx.fill();
      ctx.fillStyle = "#0a0a0a";
      ctx.textAlign = "left";
      ctx.textBaseline = "middle";
      ctx.fillText(text, bx + pad, by + boxH / 2);
    }}

    ctx.restore();
  }}
}});

const chartOpts = {{
  animation: false, responsive: true, maintainAspectRatio: false,
  plugins: {{ legend: {{ display: false }} }},
  elements: {{ point: {{ radius: 0 }}, line: {{ borderWidth: 1.5, tension: 0.3 }} }},
  scales: {{
    x: {{ ticks: {{ color:"#475569", font:{{size:10}}, maxTicksLimit:6, maxRotation:0 }}, grid: {{ color:"#1a1a1d" }} }},
    y: {{ grid: {{ color:"#1e1e23" }}, ticks: {{ color:"#64748b", font:{{size:11}} }} }}
  }}
}};

function seekFromChart(canvas, clientX) {{
  const chart = Chart.getChart(canvas);
  if (!chart) return;
  const xAxis = chart.scales.x;
  if (!xAxis) return;
  const rect  = canvas.getBoundingClientRect();
  const px    = clientX - rect.left;
  let idx = Math.round(xAxis.getValueForPixel(px));
  idx = Math.max(0, Math.min(TIMELINE.length - 1, idx));
  slider.value   = idx;
  graphSliderIdx = idx;
  update(idx);
  for (const c of Object.values(chartInstances)) c.update("none");
}}

function attachSeek(canvas) {{
  let down = false;
  canvas.addEventListener("mousedown",  e => {{ down = true;  seekFromChart(canvas, e.clientX); }});
  canvas.addEventListener("mousemove",  e => {{ if (down) seekFromChart(canvas, e.clientX); }});
  canvas.addEventListener("mouseup",    () => {{ down = false; }});
  canvas.addEventListener("mouseleave", () => {{ down = false; }});
  canvas.addEventListener("touchstart", e => {{ e.preventDefault(); seekFromChart(canvas, e.touches[0].clientX); }}, {{passive: false}});
  canvas.addEventListener("touchmove",  e => {{ e.preventDefault(); seekFromChart(canvas, e.touches[0].clientX); }}, {{passive: false}});
}}

function renderCharts() {{
  for (const [key,,, color] of METRIC_DEFS) {{
    const canvas = document.getElementById("gc-" + key);
    const card   = document.getElementById("gccard-" + key);
    if (!canvas) continue;
    const vals   = ALL[key] || [];
    const hasData = vals.some(v => v !== null);
    if (card) card.classList.toggle("no-data", !hasData);
    if (chartInstances[key]) {{
      chartInstances[key].data.labels          = TIMELINE;
      chartInstances[key].data.datasets[0].data = vals;
      chartInstances[key].update("none");
    }} else {{
      chartInstances[key] = new Chart(canvas, {{
        type: "line",
        options: chartOpts,
        data: {{
          labels: TIMELINE,
          datasets: [{{ data: vals, borderColor: color, backgroundColor: color + "22", fill: true }}]
        }}
      }});
      attachSeek(canvas);
    }}
  }}
}}
</script>
</body>
</html>"""

def main():
    print("Loading logs...")
    logs = load_all_logs(LOGS_DIR)
    if not logs:
        print("No logs found in logs/"); return
    with open(OUT, "w") as f:
        f.write(build_html(logs))
    print(f"Dashboard saved -> {OUT}")

if __name__ == "__main__":
    main()
