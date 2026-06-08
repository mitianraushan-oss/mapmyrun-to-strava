# MapMyRun → Strava TCX Downloader

A Python script to bulk-download your **MapMyRun / MapMyFitness** workouts as TCX files and upload them to **Strava**.

Works on **Mac, Windows, and Linux**.

---

## ⚠️ Strava Upload Limits — Read First

| Plan | Upload batch size | Daily upload limit |
|------|------------------|--------------------|
| **Free** | 15 files at a time | ~30 files/day (2 batches of 15) |
| **Paid (Summit)** | 15 files at a time | ~30 files/day (2 batches of 15) |

> ⚠️ **Batch size:** You can upload **15 TCX files at a time** via the Strava web UI.
>
> ⚠️ **Daily limit:** After uploading ~30 files in a day (2 batches of 15), Strava shows a **"try later"** message. Wait a few hours or try again the next day.
>
> 📝 **Note:** The exact lifetime upload limit for free Strava accounts is not fully confirmed. Based on real usage, the practical limit appears to be **30 uploads per day**. If you hit a wall, wait and retry the next day.

### Recommended daily upload plan

| Day | Action |
|-----|--------|
| Day 1 | Upload batch 1 (15 files) → wait → Upload batch 2 (15 files) |
| Day 2 | Upload batch 3 (15 files) → wait → Upload batch 4 (15 files) |
| ... | Continue until all files uploaded |

---

## How It Works

1. You export your workout history from MapMyRun as a CSV
2. The script reads the CSV, authenticates using your browser session cookies
3. Optionally filter by date range (e.g. only 2024 workouts)
4. Downloads each workout as a `.tcx` file
5. You bulk-upload the TCX files to Strava (15 at a time, max ~30/day)

---

## Requirements

- Python 3.9 or higher (tested on Python 3.11.3)
- A MapMyRun / MapMyFitness account
- A Strava account

---

## Installation

**Mac / Linux:**
```bash
git clone https://github.com/mitianraushan-oss/mapmyrun-to-strava.git
cd mapmyrun-to-strava
pip3 install requests pandas tqdm
```

**Windows (Command Prompt or PowerShell):**
```cmd
git clone https://github.com/mitianraushan-oss/mapmyrun-to-strava.git
cd mapmyrun-to-strava
pip install requests pandas tqdm
```

---

## Step 1 — Export Your Workout History from MapMyRun

1. Log in at [mapmyfitness.com](https://www.mapmyfitness.com)
2. Go to **Settings → Privacy & Data → Export Data**
3. Request your data export — you will receive a CSV file by email
4. Save the CSV file (e.g. `workout.csv`) in the same folder as the script

---

## Step 2 — Get Your Browser Session Cookies

The script uses your browser cookies to authenticate. You need to do this **once** before running.

1. Open [mapmyfitness.com](https://www.mapmyfitness.com) in **Chrome** and log in
2. Open DevTools:
   - **Mac:** `Cmd + Option + I`
   - **Windows:** `F12`
3. Go to the **Network** tab
4. Refresh the page:
   - **Mac:** `Cmd + R`
   - **Windows:** `F5`
5. Click any request to `mapmyfitness.com` in the list
6. Scroll to **Request Headers** on the right
7. Find the `cookie:` header and **copy the entire value**

> ⚠️ The cookie string is long (several hundred characters). Copy all of it.

---

## Step 3 — Run the Script

### Basic usage

**Mac / Linux:**
```bash
python3 download_from_csv.py --csv workout.csv --cookies 'PASTE_YOUR_COOKIE_STRING_HERE' --outdir tcx_downloads
```

**Windows:**
```cmd
python download_from_csv.py --csv workout.csv --cookies "PASTE_YOUR_COOKIE_STRING_HERE" --outdir tcx_downloads
```

### Filter by date range

Download only workouts between specific dates:

**Mac / Linux:**
```bash
python3 download_from_csv.py --csv workout.csv --cookies 'YOUR_COOKIES' --from-date 2024-01-01 --to-date 2024-12-31 --outdir tcx_downloads
```

**Windows:**
```cmd
python download_from_csv.py --csv workout.csv --cookies "YOUR_COOKIES" --from-date 2024-01-01 --to-date 2024-12-31 --outdir tcx_downloads
```

You can also use only `--from-date` or only `--to-date`:
```bash
# Everything from 2023 onwards
python3 download_from_csv.py --csv workout.csv --cookies 'YOUR_COOKIES' --from-date 2023-01-01

# Everything up to end of 2022
python3 download_from_csv.py --csv workout.csv --cookies 'YOUR_COOKIES' --to-date 2022-12-31
```

### Limit to first N records

```bash
python3 download_from_csv.py --csv workout.csv --cookies 'YOUR_COOKIES' --limit 30
```

> ⚠️ **Important:** Run the command on a **single line**. Do not split it across multiple lines.

---

## All Available Options

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--csv` | ✅ Yes | — | Path to your exported CSV file |
| `--cookies` | ✅ Yes | — | Cookie string copied from browser DevTools |
| `--outdir` | No | `tcx_downloads` | Folder where TCX files will be saved |
| `--from-date` | No | — | Only download workouts on or after this date (`YYYY-MM-DD`) |
| `--to-date` | No | — | Only download workouts on or before this date (`YYYY-MM-DD`) |
| `--limit` | No | All records | Process only the first N workouts |
| `--delay` | No | `1.5` | Seconds to wait between downloads (avoid rate limiting) |

---

## Step 4 — Upload to Strava

1. Log in at [strava.com](https://www.strava.com)
2. Click **+** → **Upload Activity** → **Files**
3. Select **up to 15 TCX files** at a time from your `tcx_downloads/` folder
4. Wait for the first batch to finish processing
5. Upload the next batch of 15
6. After **30 files in a day**, Strava may show **"try later"** — wait a few hours or resume the next day

### Example: Uploading 109 files

| Day | Batches | Files uploaded |
|-----|---------|---------------|
| Day 1 | Batch 1 (15) + Batch 2 (15) | 30 |
| Day 2 | Batch 3 (15) + Batch 4 (15) | 60 |
| Day 3 | Batch 5 (15) + Batch 6 (15) | 90 |
| Day 4 | Batch 7 (15) + remaining (19) | 109 ✅ |

---

## Output

Downloaded files are saved as:
```
tcx_downloads/
├── 1-Apr-26_Run_8772460634.tcx
├── 2-Apr-26_Walk_8773012345.tcx
└── ...
```

Filename format: `{date}_{activity}_{workout_id}.tcx`

---

## Sample Run Output

```
[*] Verifying session cookies ...
[OK] Session is valid.

[*] After date filter (2024-01-01 to 2024-12-31): 42 workouts
[*] Found 42 workouts to process.

=======================================================
  STRAVA UPLOAD LIMITS — READ BEFORE UPLOADING
=======================================================
  Batch size   : 15 files at a time
  Daily limit  : ~30 files/day (2 batches of 15)
  After 30/day : Strava says "try later" — wait a few hours or next day
=======================================================

[*] Downloading TCX files to 'tcx_downloads/' ...

100%|████████████████████| 42/42 [01:10<00:00, workout]

-------------------------------------------------------
Downloaded      : 42
Skipped (cached): 0
Failed          : 0
Files saved to  : /Users/yourname/tcx_downloads
-------------------------------------------------------

All workouts downloaded!

Upload to Strava:
  1. Go to strava.com -> + -> Upload Activity -> Files
  2. Select up to 15 TCX files at a time
  3. After ~30 files/day Strava may say "try later"
  4. Wait a few hours or continue next day
```

---

## Troubleshooting

### `error: unrecognized arguments`
Run the entire command on **one line** — do not use line breaks.

### `Session expired` or `Got HTML (login wall)`
Your cookies have expired. Go back to Chrome, refresh mapmyfitness.com, re-copy the `cookie:` header from DevTools, and re-run. Already downloaded files will be skipped.

### SSL errors on Mac
```bash
/Applications/Python\ 3.11/Install\ Certificates.command
```

### `python3` not recognized on Windows
Use `python` instead of `python3`.

### `pip` not found on Windows
```cmd
python -m pip install requests pandas tqdm
```

### Date filter not working
Make sure to use `YYYY-MM-DD` format, e.g. `--from-date 2024-01-01`.

### Strava says "try later"
You have hit the daily upload limit (~30 files). Wait a few hours or try again the next day.

### Some files failed to download
Just re-run the same command. The script skips already-downloaded files and retries only the failed ones.

---

## Notes

- Cookie sessions typically last **a few hours**. For large exports (200+ workouts), you may need to refresh cookies mid-run.
- The `--delay 1.5` default adds a 1.5s pause between requests to avoid rate-limiting by MapMyFitness.
- The script is fully **resumable** — safe to stop and restart at any time.

---

## Platform Summary

| | Mac | Windows | Linux |
|---|---|---|---|
| Python command | `python3` | `python` | `python3` |
| pip command | `pip3` | `pip` | `pip3` |
| Cookie quotes | Single `'` | Double `"` | Single `'` |
| Open DevTools | `Cmd+Option+I` | `F12` | `F12` |
| Refresh page | `Cmd+R` | `F5` | `F5` |

---

## Dependencies

```
requests
pandas
tqdm
```

---

## License

MIT
