# RMS Internal Audit Action Tracker

Tracks the recommendations from two internal audit reports, one tab each:
- **Regional Warehouses** (Q3, March 2026) – 23 findings · 38 actions · 36 KPIs
- **Central Warehouse** (Q4, July 2026)   – 25 findings · 45 actions · 46 KPIs

## Run locally
    python -m pip install -r requirements.txt
    python -m streamlit run app.py

## Data
Everything (findings, actions, KPI history, documents, comments, activity log) lives in ONE SQLite file,
`ia_tracker.db`, created on first run and pre-loaded from `ia_seed_data.py`.
Set `DATABASE_PATH` (e.g. a Railway volume `/data/ia_tracker.db`) so data survives redeploys.
Editing `ia_seed_data.py` later never overwrites data already in the database.

## Files
- `app.py` entry point · `ia.py` user interface · `ia_db.py` database · `ia_core.py` status/KPI maths
- `ia_export.py` Excel export · `ia_seed_data.py` data extracted from the two PDF reports

## Notes
- Owners are *proposed* from management comments (reports name units, not people) until edited.
- Initial statuses come from management comments; "Implemented – Pending Verification" = management says done, IA not yet verified.
- KPI progress = (current − baseline) ÷ (target − baseline), capped 0–100%. KPIs with no target in the report show none until set.
- Tested on Streamlit 1.66 / pandas 3.
