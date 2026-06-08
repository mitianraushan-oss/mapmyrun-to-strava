# -*- coding: utf-8 -*-
"""
MapMyRun / MapMyFitness -> TCX Downloader (Cookie-based Auth)
=============================================================
Reads your exported workout CSV and downloads each workout as a TCX
file using your browser session cookies (no OAuth needed).

Usage:
    python3 download_from_csv.py \
        --csv  workout.csv \
        --cookies "COOKIE_STRING_FROM_BROWSER" \
        --outdir tcx_downloads

    # With date range filter:
    python3 download_from_csv.py \
        --csv workout.csv \
        --cookies "COOKIE_STRING" \
        --from-date 2024-01-01 \
        --to-date 2024-12-31 \
        --outdir tcx_downloads

How to get your cookie string (Chrome on Mac/Windows):
    1. Go to https://www.mapmyfitness.com and log in
    2. Open DevTools -> Cmd+Option+I (Mac) or F12 (Windows)
    3. Go to Network tab
    4. Refresh the page
    5. Click any request to mapmyfitness.com
    6. Under Request Headers, find "cookie:" and copy the entire value
    7. Paste it as the --cookies argument (wrap in single quotes on Mac, double quotes on Windows)

Strava Upload Limits:
    - Free account : 15 TCX uploads total (after that, manual entry only)
    - Paid account : Unlimited uploads
    - Daily limit  : 30 files per day (free and paid)
    - Bulk upload  : Up to 25 files at a time via the web UI

Requirements:
    pip install requests pandas tqdm
"""

import argparse
import sys
import time
import re
import pandas as pd
import requests
from datetime import datetime
from pathlib import Path
from tqdm import tqdm

# -- Constants ----------------------------------------------------------------

TCX_URL_TEMPLATE = (
    "https://www.mapmyfitness.com"
    "/workout/export/{workout_id}/tcx"
)

HEADERS_BASE = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.mapmyfitness.com/",
}

STRAVA_FREE_LIMIT  = 15   # max TCX uploads for free Strava accounts
STRAVA_DAILY_LIMIT = 30   # max uploads per day (free and paid)


# -- Cookie helpers -----------------------------------------------------------

def parse_cookie_string(cookie_str):
    """Parse a raw browser cookie string into a dict."""
    cookies = {}
    for part in cookie_str.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            cookies[k.strip()] = v.strip()
    return cookies


def verify_session(session):
    """Quick check that the session is actually logged in."""
    print("[*] Verifying session cookies ...")
    resp = session.get(
        "https://www.mapmyfitness.com/dashboard/",
        timeout=15,
        allow_redirects=True,
    )
    if "login" in resp.url or "sign_in" in resp.url:
        print("[ERROR] Cookies appear to be expired or invalid.")
        print("        Please re-copy fresh cookies from your browser and try again.")
        sys.exit(1)
    print("[OK] Session is valid.\n")


# -- CSV parsing --------------------------------------------------------------

def parse_date(date_str):
    """Try to parse a date string in multiple formats."""
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None


def load_workout_ids(csv_path, limit=None, from_date=None, to_date=None):
    """Return list of {workout_id, date, activity} from the CSV.

    Args:
        csv_path  : path to the exported CSV file
        limit     : optional max number of workouts to process
        from_date : optional start date filter (datetime object)
        to_date   : optional end date filter (datetime object)
    """
    df = pd.read_csv(csv_path, on_bad_lines="skip")
    df.columns = [c.strip() for c in df.columns]

    df = df[df["Link"].notna()].copy()
    df = df[df["Link"].str.contains("mapmyfitness.com/workout/", na=False)]

    # -- Date range filter ----------------------------------------------------
    if from_date or to_date:
        def in_range(date_val):
            dt = parse_date(str(date_val))
            if dt is None:
                return False
            if from_date and dt < from_date:
                return False
            if to_date and dt > to_date:
                return False
            return True

        df = df[df["Workout Date"].apply(in_range)].copy()
        print("[*] After date filter ({} to {}): {} workouts".format(
            from_date.strftime("%Y-%m-%d") if from_date else "beginning",
            to_date.strftime("%Y-%m-%d") if to_date else "today",
            len(df),
        ))

    # -- Row limit ------------------------------------------------------------
    if limit:
        df = df.head(limit)

    workouts = []
    for _, row in df.iterrows():
        link = str(row["Link"]).strip()
        m = re.search(r"/workout/(\d+)", link)
        if not m:
            continue
        workouts.append({
            "workout_id": m.group(1),
            "date":       str(row.get("Workout Date", "unknown")).strip().replace("/", "-").replace(" ", "_"),
            "activity":   str(row.get("Activity Type", "workout")).strip().replace(" ", "_"),
        })
    return workouts


# -- Download -----------------------------------------------------------------

def download_tcx(session, workout, outdir):
    """Download a single workout as TCX. Returns status string."""
    wid      = workout["workout_id"]
    filename = outdir / "{}_{} {}.tcx".format(
        workout["date"], workout["activity"], wid
    )

    if filename.exists():
        return "skip"

    url = TCX_URL_TEMPLATE.format(workout_id=wid)
    try:
        resp = session.get(url, timeout=30, allow_redirects=True)
    except requests.RequestException as e:
        print("\n[WARN] Network error for {}: {}".format(wid, e))
        return "fail"

    content = resp.text.strip()

    # Valid TCX starts with XML declaration or <TrainingCenterDatabase
    if resp.status_code == 200 and (
        content.startswith("<?xml") or content.startswith("<TrainingCenterDatabase")
    ):
        filename.write_text(resp.text, encoding="utf-8")
        return "ok"

    # Detect session expiry
    if "login" in resp.url or "sign_in" in resp.url or resp.status_code in (401, 403):
        print("\n[ERROR] Session expired at workout {}.".format(wid))
        print("        Re-copy fresh cookies from browser and re-run.")
        return "expired"

    # HTML response = login wall
    if content.startswith("<!DOCTYPE") or content.startswith("<html"):
        print("\n[WARN] Got HTML (login wall) for workout {}. Session may be expiring.".format(wid))
        return "fail"

    print("\n[WARN] Unexpected response for {}: HTTP {}".format(wid, resp.status_code))
    return "fail"


# -- Strava limit warnings ----------------------------------------------------

def print_strava_warnings(total_workouts):
    """Warn user about Strava upload limits before starting."""
    print("=" * 55)
    print("  STRAVA UPLOAD LIMITS — READ BEFORE UPLOADING")
    print("=" * 55)
    print("  Free account : {} TCX uploads lifetime (then manual entry only)".format(STRAVA_FREE_LIMIT))
    print("  Paid account : Unlimited uploads")
    print("  Daily limit  : {} files per day (free and paid)".format(STRAVA_DAILY_LIMIT))
    print("  Bulk upload  : Up to 25 files at a time via web UI")
    print()
    if total_workouts > STRAVA_FREE_LIMIT:
        print("  ⚠️  You have {} workouts — free Strava users can only".format(total_workouts))
        print("      upload {} before hitting the limit.".format(STRAVA_FREE_LIMIT))
        print("      Consider upgrading to Strava Summit for unlimited uploads.")
    if total_workouts > STRAVA_DAILY_LIMIT:
        days_needed = -(-total_workouts // STRAVA_DAILY_LIMIT)  # ceiling division
        print("  ⚠️  {} workouts will take at least {} day(s) to upload".format(
            total_workouts, days_needed))
        print("      (max {} files per day on Strava).".format(STRAVA_DAILY_LIMIT))
    print("=" * 55)
    print()


# -- Main ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Download MapMyRun workouts as TCX files using browser cookies."
    )
    parser.add_argument("--csv",       required=True,
                        help="Path to your exported CSV (e.g. workout.csv)")
    parser.add_argument("--cookies",   required=True,
                        help="Raw cookie string copied from browser DevTools")
    parser.add_argument("--outdir",    default="tcx_downloads",
                        help="Folder to save TCX files (created if absent)")
    parser.add_argument("--delay",     type=float, default=1.5,
                        help="Seconds to wait between downloads (default 1.5)")
    parser.add_argument("--limit",     type=int, default=None,
                        help="Process only first N records (e.g. --limit 109)")
    parser.add_argument("--from-date", default=None,
                        help="Start date filter YYYY-MM-DD (e.g. --from-date 2024-01-01)")
    parser.add_argument("--to-date",   default=None,
                        help="End date filter YYYY-MM-DD (e.g. --to-date 2024-12-31)")
    args = parser.parse_args()

    # Parse date filters
    from_date = None
    to_date   = None
    if args.from_date:
        from_date = parse_date(args.from_date)
        if not from_date:
            print("[ERROR] Invalid --from-date format. Use YYYY-MM-DD (e.g. 2024-01-01)")
            sys.exit(1)
    if args.to_date:
        to_date = parse_date(args.to_date)
        if not to_date:
            print("[ERROR] Invalid --to-date format. Use YYYY-MM-DD (e.g. 2024-12-31)")
            sys.exit(1)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # Build session with browser cookies
    session = requests.Session()
    session.headers.update(HEADERS_BASE)
    session.cookies.update(parse_cookie_string(args.cookies))

    # Verify session is valid before starting
    verify_session(session)

    workouts = load_workout_ids(
        args.csv,
        limit=args.limit,
        from_date=from_date,
        to_date=to_date,
    )
    print("[*] Found {} workouts to process.\n".format(len(workouts)))

    # Show Strava limits warning
    print_strava_warnings(len(workouts))

    print("[*] Downloading TCX files to '{}/' ...\n".format(outdir))

    ok = fail = skip = 0

    for w in tqdm(workouts, unit="workout", ncols=70):
        result = download_tcx(session, w, outdir)
        if result == "ok":
            ok += 1
        elif result == "skip":
            skip += 1
        elif result == "expired":
            print("\n[!] Stopping. Re-run after refreshing cookies.")
            print("    Already downloaded files are safe — script will skip them on re-run.")
            break
        else:
            fail += 1
        time.sleep(args.delay)

    print("\n" + "-" * 55)
    print("Downloaded      : {}".format(ok))
    print("Skipped (cached): {}".format(skip))
    print("Failed          : {}".format(fail))
    print("Files saved to  : {}".format(outdir.resolve()))
    print("-" * 55)

    if fail > 0:
        print("\nTip: Re-run the script -- it will skip already-downloaded files")
        print("     and retry only the failed ones.")

    if ok + skip == len(workouts):
        print("\nAll workouts downloaded!")
        print("\nUpload to Strava:")
        print("  1. Go to strava.com -> + -> Upload Activity -> Files")
        print("  2. Select up to 25 TCX files at a time")
        print("  3. Max 30 files per day — spread uploads across days if needed")
        if ok + skip > STRAVA_FREE_LIMIT:
            print("\n  ⚠️  Free Strava accounts: only {} uploads allowed lifetime.".format(STRAVA_FREE_LIMIT))
            print("      Upgrade to Strava Summit for unlimited TCX uploads.")


if __name__ == "__main__":
    main()
