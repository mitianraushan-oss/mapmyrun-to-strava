# MapMyRun → Strava TCX Downloader

A Python script to bulk-download your **MapMyRun / MapMyFitness** workouts as TCX files and upload them to **Strava**.

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

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO

# Install dependencies
pip3 install requests pandas tqdm
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
2. Press `Cmd + Option + I` (Mac) or `F12` (Windows) to open **DevTools**
3. Go to the **Network** tab
4. Refresh the page (`Cmd + R`)
5. Click any request to `mapmyfitness.com` in the list
6. Scroll to **Request Headers** on the right
7. Find the `cookie:` header and **copy the entire value**

> ⚠️ The cookie string is long (several hundred characters). Copy all of it.

---

## Step 3 — Run the Script

```bash
python3 download_from_csv.py --csv workout.csv --cookies 'PASTE_YOUR_COOKIE_STRING_HERE' --outdir tcx_downloads --limit 109 --delay 1.5
```

> ⚠️ **Important:** Run the command on a **single line**. Do not split it across multiple lines.

### All Available Options

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--csv` | ✅ Yes | — | Path to your exported CSV file |
| `--cookies` | ✅ Yes | — | Cookie string copied from browser DevTools |
| `--outdir` | No | `tcx_downloads` | Folder where TCX files will be saved |
| `--limit` | No | All records | Process only the first N workouts |
| `--delay` | No | `1.5` | Seconds to wait between downloads (avoid rate limiting) |

### Examples

**Download all workouts:**
```bash
python3 download_from_csv.py --csv workout.csv --cookies 'YOUR_COOKIES' --outdir tcx_downloads
```

**Download only the first 109 workouts:**
```bash
python3 download_from_csv.py --csv workout.csv --cookies 'YOUR_COOKIES' --outdir tcx_downloads --limit 109
```

**Resume an interrupted download (already downloaded files are skipped automatically):**
```bash
python3 download_from_csv.py --csv workout.csv --cookies 'YOUR_COOKIES' --outdir tcx_downloads --limit 109
```

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
Run the entire command on **one line** — do not use line breaks or `\` continuations.

### `Session expired` or `Got HTML (login wall)`
Your cookies have expired. Go back to Chrome, refresh mapmyfitness.com, and re-copy the `cookie:` header from DevTools. Then re-run — the script will skip already-downloaded files.

### SSL errors on Mac
```bash
/Applications/Python\ 3.11/Install\ Certificates.command
```

### Some files failed
Just re-run the same command. The script skips already-downloaded files and retries only the failed ones.

---

## Notes

- Cookie sessions typically last **a few hours**. For large exports (200+ workouts), you may need to refresh cookies mid-run.
- The `--delay 1.5` default adds a 1.5s pause between requests to avoid being rate-limited by MapMyFitness.
- The script is fully **resumable** — safe to stop and restart at any time.

---

## Dependencies

```
requests
pandas
tqdm
```

Install with:
```bash
pip3 install requests pandas tqdm
```

---

## License

MIT
