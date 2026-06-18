import pandas as pd
import os, glob

LOGS_DIR = "logs"

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

