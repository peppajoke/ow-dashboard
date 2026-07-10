# ow-dashboard

Static GitHub Pages site: Overwatch 2 hero win rate deviations by competitive map.

Live: https://peppajoke.github.io/ow-dashboard/

## Build

```
scripts/build_data.py
```

Reads:
- `~/.openclaw/workspace/data/overwatch/{dps,tank,support}.csv`
- `~/.openclaw/workspace/memory/overwatch-maps.md`

Writes `index.html` with all data embedded as JSON — no runtime API calls.

The wrapper `scripts/build-ow-dashboard.sh` (installed to `~/.openclaw/workspace/scripts/`) runs the build, commits, and pushes. It is invoked weekly (Monday 10am ET) after the OW spreadsheet sync updates the CSVs.
