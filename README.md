# MapMyRun → Strava TCX Downloader

A Python script to bulk-download your **MapMyRun / MapMyFitness** workouts as TCX files and upload them to **Strava**.

Works on **Mac, Windows, and Linux**.

---

## How It Works

1. You export your workout history from MapMyRun as a CSV
2. The script reads the CSV, authenticates using your browser session cookies
3. Downloads each workout as a `.tcx` file
4. You bulk-upload the TCX files to Strava

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

The script uses your browser cookies to authenticate (same as being logged in on Chrome). You need to do this **once** before running.

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

### Mac / Linux
```bash
python3 download_from_csv.py --csv workout.csv --cookies 'PASTE_YOUR_COOKIE_STRING_HERE' --outdir tcx_downloads --limit 109 --delay 1.5
```

### Windows (Command Prompt)
```cmd
python download_from_csv.py --csv workout.csv --cookies "PASTE_YOUR_COOKIE_STRING_HERE" --outdir tcx_downloads --limit 109 --delay 1.5
```

### Windows (PowerShell)
```powershell
python download_from_csv.py --csv workout.csv --cookies "PASTE_YOUR_COOKIE_STRING_HERE" --outdir tcx_downloads --limit 109 --delay 1.5
```

> ⚠️ **Important:** Run the command on a **single line**. Do not split it across multiple lines.
>
> Note: Mac/Linux use **single quotes** `'` around the cookie string. Windows uses **double quotes** `"`.

---

## All Available Options

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--csv` | ✅ Yes | — | Path to your exported CSV file |
| `--cookies` | ✅ Yes | — | Cookie string copied from browser DevTools |
| `--outdir` | No | `tcx_downloads` | Folder where TCX files will be saved |
| `--limit` | No | All records | Process only the first N workouts |
| `--delay` | No | `1.5` | Seconds to wait between downloads (avoid rate limiting) |

---

## Examples

**Download all workouts (Mac):**
```bash
python3 download_from_csv.py --csv workout.csv --cookies 'YOUR_COOKIES' --outdir tcx_downloads
```

**Download only the first 109 workouts (Mac):**
```bash
python3 download_from_csv.py --csv workout.csv --cookies 'YOUR_COOKIES' --outdir tcx_downloads --limit 109
```

**Download all workouts (Windows):**
```cmd
python download_from_csv.py --csv workout.csv --cookies "YOUR_COOKIES" --outdir tcx_downloads
```

**Resume an interrupted download** — already downloaded files are skipped automatically, just re-run the same command.

---

## Step 4 — Upload to Strava

1. Log in at [strava.com](https://www.strava.com)
2. Click **+** → **Upload Activity** → **Files**
3. Select TCX files from your `tcx_downloads/` folder
4. Strava supports **up to 25 files at a time** in bulk upload
5. Repeat until all files are uploaded

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

[*] Found 109 workouts to process.
[*] Downloading TCX files to 'tcx_downloads/' ...

100%|████████████████████| 109/109 [02:45<00:00, workout]

--------------------------------------------------
Downloaded      : 107
Skipped (cached): 2
Failed          : 0
Files saved to  : /Users/yourname/tcx_downloads
--------------------------------------------------

All workouts downloaded!
Upload to Strava: Upload Activity -> Files -> select all TCX files
Note: Strava allows up to 25 files at a time in bulk upload.
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
Use `python` instead of `python3` — Windows uses `python` by default.

### `pip` not found on Windows
Try `pip3` or run:
```cmd
python -m pip install requests pandas tqdm
```

### Some files failed
Just re-run the same command. The script skips already-downloaded files and retries only the failed ones.

---

## Notes

- Cookie sessions typically last **a few hours**. For large exports (200+ workouts), you may need to refresh cookies mid-run.
- The `--delay 1.5` default adds a 1.5s pause between requests to avoid being rate-limited by MapMyFitness.
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
