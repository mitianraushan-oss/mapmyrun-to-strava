#!/usr/bin/env python3
"""
mmf_export_csv.py
-----------------
CLI: Download MapMyFitness workouts for a date range and export to CSV.

Usage:
  python mmf_export_csv.py --start 2024-01-01 --end 2024-12-31
  python mmf_export_csv.py --start 2024-01-01 --end 2024-12-31 --cookie "your_cookie"

Auth (pick one):
  --cookie         Browser session cookie string
  --access-token   OAuth2 access token (+ optionally --api-key)
  env vars:        MMF_COOKIE, MMF_ACCESS_TOKEN, MMF_API_KEY
"""
from dotenv import load_dotenv
load_dotenv()

import argparse
import os
import sys

import mmf_api


def main():
    parser = argparse.ArgumentParser(
        description="Export MapMyFitness workouts for a date range to CSV."
    )
    parser.add_argument("--start",        required=True, help="Start date YYYY-MM-DD (inclusive)")
    parser.add_argument("--end",          required=True, help="End date YYYY-MM-DD (inclusive)")
    parser.add_argument("--out",          default="mmf_workouts.csv", help="Output CSV filename")
    parser.add_argument("--cookie",       default=None, help="Browser cookie string")
    parser.add_argument("--api-key",      default=None, help="MMF API key (or MMF_API_KEY env var)")
    parser.add_argument("--access-token", default=None, help="OAuth2 token (or MMF_ACCESS_TOKEN env var)")
    args = parser.parse_args()

    api_key      = args.api_key      or os.environ.get("MMF_API_KEY")
    access_token = args.access_token or os.environ.get("MMF_ACCESS_TOKEN")
    cookie       = args.cookie       or os.environ.get("MMF_COOKIE")

    if not (access_token or cookie):
        print(
            "ERROR: Provide auth via one of:\n"
            "  --cookie 'your_cookie_string'\n"
            "  --access-token TOKEN  (+ optionally --api-key KEY)\n"
            "  env vars: MMF_ACCESS_TOKEN, MMF_API_KEY, or MMF_COOKIE"
        )
        sys.exit(1)

    session = mmf_api.make_session(cookie=cookie, api_key=api_key, access_token=access_token)

    print("Fetching user info…")
    try:
        user_id = mmf_api.get_user_id(session)
    except mmf_api.AuthError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    print(f"Authenticated as user_id={user_id}")

    started_after  = mmf_api.iso_dt(args.start, end_of_day=False)
    started_before = mmf_api.iso_dt(args.end,   end_of_day=True)
    print(f"Date range: {started_after}  →  {started_before}")

    def on_progress(fetched, total):
        print(f"  Fetched {fetched} / {total} workouts…", end="\r", flush=True)

    rows = []
    try:
        for w in mmf_api.fetch_workouts(session, user_id, started_after, started_before, on_progress):
            rows.append(mmf_api.parse_workout(w))
    except mmf_api.AuthError as e:
        print(f"\nERROR: {e}")
        sys.exit(1)

    print()

    if not rows:
        print("No workouts found in that date range.")
        return

    mmf_api.write_csv(rows, args.out)


if __name__ == "__main__":
    main()
