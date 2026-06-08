# MapMyRun → Strava TCX Downloader

A Python script to bulk-download your **MapMyRun / MapMyFitness** workouts as TCX files and upload them to **Strava**.

Works on **Mac, Windows, and Linux**.

---

## ⚠️ Strava Upload Limits — Read First

| Plan | Lifetime TCX uploads | Daily upload limit | Bulk upload (web UI) |
|------|---------------------|--------------------|----------------------|
| **Free** | **15 workouts only** | 30 files/day | Up to 25 files at a time |
| **Paid (Summit)** | Unlimited | 30 files/day | Up to 25 files at a time |

> ⚠️ **Free Strava users:** After 15 TCX uploads, Strava will not accept more file uploads. You will need to log activities manually or upgrade to a paid plan.
>
> ⚠️ **All users:** Maximum **30 files per day**. If you have more, spread uploads across multiple days.

---

## How It Works

1. You export your workout history from MapMyRun as a CSV
2. The script reads the CSV, authenticates using your browser session cookies
3. Optionally filter by date range (e.g. only 2024 workouts)
4. Downloads each workout as a `.tcx` file
5. You bulk-upload the TCX files to Strava

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
python3 download_from_csv.py --csv workout.csv --cookies 'YOUR_COOKIES' --limit 15
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
3. Select up to **25 TCX files** at a time from your `tcx_downloads/` folder
4. Repeat — but remember the **30 files/day** limit
5. **Free users:** Stop after 15 uploads or upgrade to continue

### Recommended upload strategy

| Strava Plan | Strategy |
|-------------|----------|
| **Free** | Download only your 15 most recent or most important workouts using `--limit 15` |
| **Paid** | Upload 25 files at a time, max 30/day — spread across days for large archives |

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
  Free account : 15 TCX uploads lifetime (then manual entry only)
  Paid account : Unlimited uploads
  Daily limit  : 30 files per day (free and paid)
  Bulk upload  : Up to 25 files at a time via web UI

  ⚠️  You have 42 workouts — free Strava users can only
      upload 15 before hitting the limit.
  ⚠️  42 workouts will take at least 2 day(s) to upload
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
  2. Select up to 25 TCX files at a time
  3. Max 30 files per day — spread uploads across days if needed

  ⚠️  Free Strava accounts: only 15 uploads allowed lifetime.
      Upgrade to Strava Summit for unlimited TCX uploads.
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

### Some files failed
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
