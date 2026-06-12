# MapMyRun → Strava TCX Downloader

Bulk-download your **MapMyRun / MapMyFitness workouts as TCX files** for a specific date range and upload them to **Strava**.

No API key or OAuth registration needed — uses your browser session cookies.

Works on **Mac, Windows, and Linux**.

---

## Option A — Web App (no Python required)

A point-and-click UI that runs in your browser.

**Live app:** [https://mapmyrun-to-strava.onrender.com](https://mapmyrun-to-strava.onrender.com)

> Free tier — spins down after 15 min of inactivity; first load may take ~30 seconds.

**Run locally:**
```bash
git clone https://github.com/mitianraushan-oss/mapmyrun-to-strava.git
cd mapmyrun-to-strava
pip3 install -r requirements.txt
streamlit run app.py
```
Then open **http://localhost:8501**, paste your cookie, pick a date range, and download.

**Self-host on Render.com (free tier):**

1. Fork this repo on GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your fork — Render auto-detects `render.yaml` and deploys

> 🔒 **Privacy:** Cookies are used only within your session and are never stored.

---

## Option B — Command-line scripts

```
Step 1 → Set up .env with your browser cookies (once)
Step 2 → Export workouts for a date range to CSV  (mmf_export_csv.py)
Step 3 → Download TCX files from that CSV          (download_from_csv.py)
Step 4 → Upload TCX files to Strava                (web UI, 15 at a time)
```

---

## ⚠️ Strava Upload Limits — Read First

| Plan | Batch size | Daily limit |
|------|-----------|-------------|
| **Free** | 15 files at a time | ~30 files/day |
| **Paid (Summit)** | 15 files at a time | ~30 files/day |

> ⚠️ After uploading ~30 files in a day, Strava shows a **"try later"** message. Wait a few hours or resume the next day.

### Recommended upload plan for large histories

| Day | Action | Total uploaded |
|-----|--------|---------------|
| Day 1 | Batch 1 (15) + Batch 2 (15) | 30 |
| Day 2 | Batch 3 (15) + Batch 4 (15) | 60 |
| Day 3 | Batch 5 (15) + Batch 6 (15) | 90 |
| Day 4 | Remaining files | ✅ Done |

---

## Requirements

- Python 3.9 or higher (tested on 3.11)
- A MapMyRun / MapMyFitness account
- A Strava account

---

## Installation

**Mac / Linux:**
```bash
git clone https://github.com/mitianraushan-oss/mapmyrun-to-strava.git
cd mapmyrun-to-strava
pip3 install requests pandas tqdm python-dotenv
```

**Windows:**
```cmd
git clone https://github.com/mitianraushan-oss/mapmyrun-to-strava.git
cd mapmyrun-to-strava
pip install requests pandas tqdm python-dotenv
```

---

## Step 1 — Set Up Authentication (one time only)

The scripts authenticate using your browser session cookies — no API key needed.

### Get your cookie string

1. Open [mapmyfitness.com](https://www.mapmyfitness.com) in Chrome and log in
2. Open DevTools:
   - **Mac:** `Cmd + Option + I`
   - **Windows / Linux:** `F12`
3. Go to the **Network** tab and refresh the page (`Cmd+R` / `F5`)
4. Click any request to `mapmyfitness.com`
5. Under **Request Headers**, find `cookie:` and **copy the entire value**

> ⚠️ The cookie string is long (several hundred characters). Copy all of it.

### Save to `.env`

Create a file named `.env` in the project folder:

```
MMF_COOKIE=paste_your_full_cookie_string_here
```

> ⚠️ Never commit `.env` to git — it's already in `.gitignore`.

Both scripts will now read cookies automatically from `.env` — no need to pass them on the command line.

---

## Step 2 — Export Workouts to CSV

Use `mmf_export_csv.py` to fetch your workout history for a date range directly from the MapMyFitness API and save it as a CSV.

```bash
python3 mmf_export_csv.py --start 2026-01-01 --end 2026-06-30
```

This creates `mmf_workouts.csv` in the current folder.

### What's in the CSV

| Column | Description |
|--------|-------------|
| `workout_id` | Unique workout ID |
| `name` | Workout name |
| `start_datetime` | Start time (ISO8601 UTC) |
| `start_locale_timezone` | Local timezone (e.g. Asia/Kolkata) |
| `activity_type_id` | Activity type (9=Walk, 16=Run, etc.) |
| `distance_km` / `distance_miles` | Distance |
| `duration_hms` | Duration (HH:MM:SS) |
| `duration_seconds` | Duration in seconds |
| `calories_kcal` | Calories burned |
| `avg_speed_kmh` / `avg_speed_mph` | Average speed |
| `avg_heart_rate` / `max_heart_rate` | Heart rate |
| `steps_total` | Step count |
| `source` | App/device used (e.g. MapMyRun iPhone) |
| `notes` | Workout notes |
| `workout_url` | Direct link to workout on mapmyrun.com |

### Options

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--start` | ✅ Yes | — | Start date `YYYY-MM-DD` (inclusive) |
| `--end` | ✅ Yes | — | End date `YYYY-MM-DD` (inclusive) |
| `--out` | No | `mmf_workouts.csv` | Output CSV filename |
| `--cookie` | No | reads `.env` | Override cookie from CLI |

### Example

```bash
# Export all of 2025
python3 mmf_export_csv.py --start 2025-01-01 --end 2025-12-31

# Export to a custom filename
python3 mmf_export_csv.py --start 2026-01-01 --end 2026-06-30 --out june_2026.csv
```

### Sample output

```
Fetching user info…
Authenticated as user_id=206395552
Date range: 2026-06-01T00:00:00Z  →  2026-06-30T23:59:59Z
  Fetched 12 / 12 workouts…
Saved 12 workouts → mmf_workouts.csv
```

---

## Step 3 — Download TCX Files

Use `download_from_csv.py` to download each workout from the CSV as a `.tcx` file.

```bash
python3 download_from_csv.py --csv mmf_workouts.csv
```

TCX files are saved to `tcx_downloads/` by default.

### Options

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--csv` | ✅ Yes | — | Path to CSV from Step 2 |
| `--outdir` | No | `tcx_downloads` | Folder to save TCX files |
| `--from-date` | No | — | Only download workouts on/after this date |
| `--to-date` | No | — | Only download workouts on/before this date |
| `--limit` | No | All | Process only first N workouts (good for testing) |
| `--delay` | No | `1.0` | Seconds between downloads (increase if rate limited) |
| `--cookies` | No | reads `.env` | Override cookie from CLI |

### Examples

```bash
# Download all workouts in the CSV
python3 download_from_csv.py --csv mmf_workouts.csv

# Filter to a specific date range within the CSV
python3 download_from_csv.py --csv mmf_workouts.csv --from-date 2026-06-01 --to-date 2026-06-15

# Test with first 5 workouts only
python3 download_from_csv.py --csv mmf_workouts.csv --limit 5

# Slower speed if getting rate limited
python3 download_from_csv.py --csv mmf_workouts.csv --delay 3
```

> ✅ **Resumable** — already-downloaded files are skipped on re-run. Safe to stop and restart anytime.

### Sample output

```
[*] Verifying session cookies ...
[OK] Session is valid.

[*] Found 12 workouts to process.

[*] Downloading TCX files to 'tcx_downloads/' ...

100%|████████████████████| 12/12 [00:48<00:00, 4.0s/workout]

-------------------------------------------------------
Downloaded      : 12
Skipped (cached): 0
Failed          : 0
Files saved to  : /Users/yourname/MapMyRunBackup/tcx_downloads
-------------------------------------------------------
✅ All workouts downloaded!
```

### Output file format

```
tcx_downloads/
├── 2026-06-06_9_8812337305.tcx
├── 2026-06-07_16_8812586926.tcx
└── 2026-06-09_9_8813875344.tcx
```

Filename format: `{date}_{activity_type_id}_{workout_id}.tcx`

---

## Step 4 — Upload to Strava

1. Log in at [strava.com](https://www.strava.com)
2. Click **+** → **Upload Activity** → **Files**
3. Select up to **15 TCX files** at a time from your `tcx_downloads/` folder
4. Wait for the batch to finish processing
5. Upload next batch — max **~30 files per day**
6. If Strava shows **"try later"** — wait a few hours or continue next day

---

## Full Example — Export and Download June 2026

```bash
# Step 1: already done — .env is set up

# Step 2: export CSV for June 2026
python3 mmf_export_csv.py --start 2026-06-01 --end 2026-06-30

# Step 3: download all as TCX
python3 download_from_csv.py --csv mmf_workouts.csv

# Step 4: upload tcx_downloads/*.tcx to Strava (15 at a time)
```

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `Session expired` or `Got HTML (login wall)` | Cookies expired — re-copy from browser and update `.env` |
| `Found 0 workouts` | Check date range in CSV or URL column mismatch |
| `python-dotenv could not parse statement` | Ignore — cookies still load correctly |
| `401 Unauthorized` | Cookie expired — refresh from browser |
| `python3 not recognized` (Windows) | Use `python` instead of `python3` |
| `pip not found` (Windows) | Use `python -m pip install ...` |
| SSL error (Mac) | Run `/Applications/Python\ 3.11/Install\ Certificates.command` |
| Strava says `"try later"` | Hit daily limit (~30 files) — wait a few hours or try next day |
| Some files failed | Re-run — script skips already-downloaded files and retries failed ones |

---

## Notes

- Cookie sessions typically last **a few hours**. For large exports (200+ workouts), you may need to refresh cookies mid-run.
- The `--delay 1.0` default adds a 1s pause between requests to avoid rate-limiting.
- Both scripts share the same `.env` file — set up once, works for both.

---

## Platform Summary

| | Mac | Windows | Linux |
|---|---|---|---|
| Python command | `python3` | `python` | `python3` |
| pip command | `pip3` | `pip` | `pip3` |
| Open DevTools | `Cmd+Option+I` | `F12` | `F12` |
| Refresh page | `Cmd+R` | `F5` | `F5` |

---

## Dependencies

```
requests
pandas
tqdm
python-dotenv
streamlit        # web app only
```

---

## License

MIT
