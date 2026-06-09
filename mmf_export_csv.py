#!/usr/bin/env python3
"""
mmf_export_csv.py
-----------------
Download MapMyFitness workouts for a specific date range and export to CSV.

Auth options (pick one):
  1. Cookie-based  → paste your browser session cookies (no API key needed)
  2. OAuth2 token  → use your MMF API key + access token

Usage:
  python mmf_export_csv.py \
      --start 2024-01-01 \
      --end   2024-12-31 \
      --out   workouts_2024.csv

  # With explicit auth (cookie mode is tried first automatically):
  python mmf_export_csv.py \
      --start 2024-01-01 --end 2024-12-31 \
      --cookie "your_session_cookie_string"

  # Or set env vars instead of flags:
  export MMF_API_KEY="your_api_key"
  export MMF_ACCESS_TOKEN="your_oauth2_token"
  python mmf_export_csv.py --start 2024-01-01 --end 2024-12-31
"""
from dotenv import load_dotenv
load_dotenv()   # reads .env automatically
import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone

import requests

# ── API Constants ────────────────────────────────────────────────────────────
BASE_URL   = "https://api.mapmyfitness.com"
WORKOUT_EP = "/v7.1/workout/"
USER_EP    = "/v7.1/user/self/"
PAGE_LIMIT = 20          # max the API returns per page
RATE_SLEEP = 0.25        # seconds between paginated requests (be a good citizen)

# ── CSV columns ──────────────────────────────────────────────────────────────
CSV_FIELDS = [
    "workout_id",
    "name",
    "start_datetime",
    "start_locale_timezone",
    "activity_type_id",
    "distance_km",
    "distance_miles",
    "duration_seconds",
    "duration_hms",
    "active_time_seconds",
    "calories_kcal",
    "avg_speed_kmh",
    "avg_speed_mph",
    "max_speed_kmh",
    "avg_heart_rate",
    "max_heart_rate",
    "steps_total",
    "source",
    "notes",
    "workout_url",
]

# ── Helpers ──────────────────────────────────────────────────────────────────

def seconds_to_hms(secs):
    if not secs:
        return ""
    secs = int(secs)
    h, rem = divmod(secs, 3600)
    m, s   = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def mps_to_kmh(mps):
    return round(mps * 3.6, 3) if mps else ""

def mps_to_mph(mps):
    return round(mps * 2.23694, 3) if mps else ""

def meters_to_km(m):
    return round(m / 1000, 3) if m else ""

def meters_to_miles(m):
    return round(m / 1609.344, 3) if m else ""

def joules_to_kcal(j):
    return round(j / 4184, 1) if j else ""

def build_headers(api_key=None, access_token=None, cookie=None):
    """Build request headers for either OAuth2 or cookie auth."""
    headers = {
        "Accept":       "application/json",
        "Content-Type": "application/json",
    }
    if api_key and access_token:
        headers["Api-Key"]       = api_key
        headers["Authorization"] = f"Bearer {access_token}"
    elif cookie:
        headers["Cookie"] = cookie
        # MMF still wants Api-Key even for cookie sessions when using the API
        if api_key:
            headers["Api-Key"] = api_key
    return headers

def get_user_id(session):
    """Fetch the authenticated user's numeric ID."""
    resp = session.get(BASE_URL + USER_EP)
    resp.raise_for_status()
    data = resp.json()
    user_href = data.get("_links", {}).get("self", [{}])[0].get("href", "")
    # href looks like /v7.1/user/123456789/
    user_id = user_href.rstrip("/").split("/")[-1]
    if not user_id.isdigit():
        # fallback: try 'id' directly
        user_id = str(data.get("id", ""))
    return user_id

def iso_dt(date_str, end_of_day=False):
    """Convert YYYY-MM-DD to ISO8601 UTC string for the API."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    if end_of_day:
        dt = dt.replace(hour=23, minute=59, second=59)
    dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

def fetch_workouts(session, user_id, started_after, started_before):
    """Page through /v7.1/workout/ and yield each workout dict."""
    params = {
        "user":           user_id,
        "started_after":  started_after,
        "started_before": started_before,
        "order_by":       "start_datetime",
        "limit":          PAGE_LIMIT,
        "offset":         0,
    }
    total_fetched = 0
    while True:
        resp = session.get(BASE_URL + WORKOUT_EP, params=params)
        if resp.status_code == 401:
            print("ERROR: 401 Unauthorized. Check your API key / token / cookie.")
            sys.exit(1)
        resp.raise_for_status()
        data = resp.json()

        total_count = data.get("total_count", 0)
        workouts    = data.get("_embedded", {}).get("workouts", [])

        if not workouts:
            break

        for w in workouts:
            yield w
            total_fetched += 1

        print(f"  Fetched {total_fetched} / {total_count} workouts…", end="\r")

        if total_fetched >= total_count:
            break

        params["offset"] += PAGE_LIMIT
        time.sleep(RATE_SLEEP)

    print()  # newline after the progress line

def parse_workout(w):
    """Extract a flat dict of the fields we care about."""
    agg = w.get("aggregates", {})
    links = w.get("_links", {})

    workout_id    = links.get("self", [{}])[0].get("id", "")
    activity_type = links.get("activity_type", [{}])[0].get("id", "")
    dist_m        = agg.get("distance_total")
    elapsed_s     = agg.get("elapsed_time_total")
    active_s      = agg.get("active_time_total")
    energy_j      = agg.get("metabolic_energy_total")
    avg_spd_mps   = agg.get("speed_avg")
    max_spd_mps   = agg.get("speed_max")
    hr_avg        = agg.get("heartrate_avg")
    hr_max        = agg.get("heartrate_max")
    steps         = agg.get("steps_total")

    return {
        "workout_id":           workout_id,
        "name":                 w.get("name", ""),
        "start_datetime":       w.get("start_datetime", ""),
        "start_locale_timezone": w.get("start_locale_timezone", ""),
        "activity_type_id":     activity_type,
        "distance_km":          meters_to_km(dist_m),
        "distance_miles":       meters_to_miles(dist_m),
        "duration_seconds":     int(elapsed_s) if elapsed_s else "",
        "duration_hms":         seconds_to_hms(elapsed_s),
        "active_time_seconds":  int(active_s) if active_s else "",
        "calories_kcal":        joules_to_kcal(energy_j),
        "avg_speed_kmh":        mps_to_kmh(avg_spd_mps),
        "avg_speed_mph":        mps_to_mph(avg_spd_mps),
        "max_speed_kmh":        mps_to_kmh(max_spd_mps),
        "avg_heart_rate":       int(hr_avg) if hr_avg else "",
        "max_heart_rate":       int(hr_max) if hr_max else "",
        "steps_total":          int(steps) if steps else "",
        "source":               w.get("source", ""),
        "notes":                w.get("notes", ""),
        "workout_url":          f"https://www.mapmyrun.com/workout/{workout_id}/",
    }

def write_csv(rows, out_path):
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {len(rows)} workouts → {out_path}")

# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Export MapMyFitness workouts for a date range to CSV."
    )
    parser.add_argument("--start",  required=True, help="Start date YYYY-MM-DD (inclusive)")
    parser.add_argument("--end",    required=True, help="End date YYYY-MM-DD (inclusive)")
    parser.add_argument("--out",    default="mmf_workouts.csv", help="Output CSV filename")
    parser.add_argument("--cookie", default=None,
                        help="Browser cookie string (copy from DevTools → Network → Request Headers → Cookie)")
    parser.add_argument("--api-key",      default=None, help="MMF API key (or set MMF_API_KEY env var)")
    parser.add_argument("--access-token", default=None, help="OAuth2 access token (or set MMF_ACCESS_TOKEN env var)")
    args = parser.parse_args()

    # Resolve credentials: flags > env vars
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

    headers = build_headers(api_key=api_key, access_token=access_token, cookie=cookie)
    session = requests.Session()
    session.headers.update(headers)

    print(f"Fetching user info…")
    user_id = get_user_id(session)
    print(f"Authenticated as user_id={user_id}")

    started_after  = iso_dt(args.start, end_of_day=False)
    started_before = iso_dt(args.end,   end_of_day=True)
    print(f"Date range: {started_after}  →  {started_before}")

    rows = []
    for w in fetch_workouts(session, user_id, started_after, started_before):
        rows.append(parse_workout(w))

    if not rows:
        print("No workouts found in that date range.")
        return

    write_csv(rows, args.out)


if __name__ == "__main__":
    main()
