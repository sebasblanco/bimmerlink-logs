# BimmerLink Dashboard

An interactive OBD data dashboard for BMW logs exported from BimmerLink. Drop in a CSV, run one command, and get a fully scrubable session viewer with live values, playback, and full graph mode.

## Features

- **Scrub timeline** — single slider moves a vertical line across all charts simultaneously, showing the live value for each metric at that exact second
- **Playback** — play through a session at 0.5×, 1×, 2×, or 5× speed
- **Click-to-seek** — click or drag directly on any chart to jump to that timestamp
- **Multi-log support** — dropdown to switch between sessions instantly
- **Auto-detects CSV format** — handles both BimmerLink long format (semicolon) and wide format (comma-separated)
- **Future dimming** — data to the right of the scrub line is grayed out so past vs future is always clear

## Metrics

Displays any available combination of: Engine RPM, Speed, Throttle, Coolant Temp, MAF, Power, Boost, Intake Temp, Timing Advance, Acceleration, Oil Temp, Oil Pressure, Voltage.

## Usage

**1. Export a log from BimmerLink**
- Open BimmerLink → tap a session → share → Save to Files
- Save to `logs/` folder as a `.csv`

**2. Generate the dashboard**
```bash
python3 dashboard.py
```

**3. Open**
```bash
open dashboard.html
```

The dashboard embeds all logs at build time — no server needed, just open the HTML file.

## Requirements

```bash
pip install pandas
```

## Project Structure

```
bimmerlink/
├── dashboard.py     # processes logs, generates dashboard.html
├── dashboard.html   # generated output (open this)
├── logs/            # drop BimmerLink CSV exports here
└── analysis/        # notes and comparisons
```
