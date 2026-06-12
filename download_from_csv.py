#!/usr/bin/env python3
"""
download_from_csv.py
--------------------
CLI: Read an exported workout CSV and download each workout as a TCX file.

Usage:
  python3 download_from_csv.py --csv mmf_workouts.csv --outdir tcx_downloads
  python3 download_from_csv.py --csv mmf_workouts.csv --from-date 2024-01-01 --to-date 2024-12-31

How to get your cookie string (Chrome):
  1. Go to https://www.mapmyfitness.com and log in
  2. Open DevTools → Network tab → refresh the page
  3. Click any request to mapmyfitness.com
  4. Under Request Headers, copy the entire "cookie:" value
  5. Paste into .env as: MMF_COOKIE=<value>

Strava upload limits:
  Free account : 15 TCX uploads lifetime
  Paid account : Unlimited
  Daily limit  : 30 files per day (free and paid)
"""
from dotenv import load_dotenv
load_dotenv()

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from tqdm import tqdm

import mmf_downloader


def main():
    parser = argparse.ArgumentParser(
        description="Download MapMyRun workouts as TCX files using browser cookies."
    )
    parser.add_argument("--csv",       required=True,
                        help="Path to exported CSV (mmf_workouts.csv or original MMF export)")
    parser.add_argument("--cookies",   default=os.environ.get("MMF_COOKIE"),
                        help="Cookie string (reads MMF_COOKIE from .env by default)")
    parser.add_argument("--outdir",    default="tcx_downloads",
                        help="Folder to save TCX files (created if absent)")
    parser.add_argument("--delay",     type=float, default=1.0,
                        help="Seconds between downloads (default 1.0)")
    parser.add_argument("--limit",     type=int, default=None,
                        help="Process only first N records")
    parser.add_argument("--from-date", default=None, help="Start date filter YYYY-MM-DD")
    parser.add_argument("--to-date",   default=None, help="End date filter YYYY-MM-DD")
    args = parser.parse_args()

    if not args.cookies:
        print("[ERROR] No cookie string found.")
        print("        Add MMF_COOKIE=<value> to your .env file, or pass --cookies 'string'")
        sys.exit(1)

    from_date = to_date = None
    if args.from_date:
        from_date = mmf_downloader.parse_date(args.from_date)
        if not from_date:
            print("[ERROR] Invalid --from-date format. Use YYYY-MM-DD")
            sys.exit(1)
    if args.to_date:
        to_date = mmf_downloader.parse_date(args.to_date)
        if not to_date:
            print("[ERROR] Invalid --to-date format. Use YYYY-MM-DD")
            sys.exit(1)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    session = mmf_downloader.make_session(args.cookies)

    print("[*] Verifying session cookies…")
    if not mmf_downloader.verify_session(session):
        print("[ERROR] Cookies appear expired or invalid.")
        print("        Re-copy fresh cookies from your browser and try again.")
        sys.exit(1)
    print("[OK] Session is valid.\n")

    try:
        workouts = mmf_downloader.load_workout_ids(
            args.csv, limit=args.limit, from_date=from_date, to_date=to_date
        )
    except ValueError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    print(f"[*] Found {len(workouts)} workouts to process.\n")

    # Strava limit warnings
    print("=" * 55)
    print("  STRAVA UPLOAD LIMITS — READ BEFORE UPLOADING")
    print("=" * 55)
    print(f"  Free account : {mmf_downloader.STRAVA_FREE_LIMIT} TCX uploads lifetime")
    print(f"  Paid account : Unlimited")
    print(f"  Daily limit  : {mmf_downloader.STRAVA_DAILY_LIMIT} files per day")
    print( "  Bulk upload  : Up to 25 files at a time via web UI")
    n = len(workouts)
    if n > mmf_downloader.STRAVA_FREE_LIMIT:
        print(f"\n  ⚠️  {n} workouts — free Strava users can only upload "
              f"{mmf_downloader.STRAVA_FREE_LIMIT} before hitting the limit.")
    if n > mmf_downloader.STRAVA_DAILY_LIMIT:
        days = -(-n // mmf_downloader.STRAVA_DAILY_LIMIT)
        print(f"  ⚠️  {n} workouts will take at least {days} day(s) to upload.")
    print("=" * 55 + "\n")

    print(f"[*] Downloading TCX files to '{outdir}/' …\n")

    ok = fail = skip = 0
    for w in tqdm(workouts, unit="workout", ncols=70):
        result = mmf_downloader.download_tcx(session, w, outdir)
        if result == "ok":
            ok += 1
        elif result == "skip":
            skip += 1
        elif result == "expired":
            print("\n[!] Session expired. Re-run after refreshing cookies.")
            print("    Already-downloaded files will be skipped on re-run.")
            break
        else:
            fail += 1
        time.sleep(args.delay)

    print(f"\n{'-' * 55}")
    print(f"Downloaded      : {ok}")
    print(f"Skipped (cached): {skip}")
    print(f"Failed          : {fail}")
    print(f"Files saved to  : {outdir.resolve()}")
    print(f"{'-' * 55}")

    if fail > 0:
        print("\nTip: Re-run — it will skip already-downloaded files and retry failed ones.")

    if ok + skip == len(workouts):
        print("\n✅ All workouts downloaded!")
        print("\nUpload to Strava:")
        print("  1. Go to strava.com → + → Upload Activity → Files")
        print("  2. Select up to 25 TCX files at a time")
        print(f"  3. Max {mmf_downloader.STRAVA_DAILY_LIMIT} files per day — spread uploads if needed")
        if ok + skip > mmf_downloader.STRAVA_FREE_LIMIT:
            print(f"\n  ⚠️  Free Strava: only {mmf_downloader.STRAVA_FREE_LIMIT} uploads allowed lifetime.")


if __name__ == "__main__":
    main()
