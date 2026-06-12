"""
mmf_api.py
----------
Library module for MapMyFitness JSON API access.
No sys.exit, no print — raises exceptions so callers (CLI or Streamlit) handle UX.
"""
import csv
import io
import time
from datetime import datetime, timezone

import requests

# ── Constants ─────────────────────────────────────────────────────────────────
BASE_URL   = "https://api.mapmyfitness.com"
WORKOUT_EP = "/v7.1/workout/"
USER_EP    = "/v7.1/user/self/"
PAGE_LIMIT = 20
RATE_SLEEP = 0.25

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


class AuthError(Exception):
    """Raised when the API rejects credentials (401/403)."""


# ── Unit helpers ──────────────────────────────────────────────────────────────

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


# ── Auth / session ────────────────────────────────────────────────────────────

def build_headers(api_key=None, access_token=None, cookie=None):
    headers = {
        "Accept":       "application/json",
        "Content-Type": "application/json",
    }
    if api_key and access_token:
        headers["Api-Key"]       = api_key
        headers["Authorization"] = f"Bearer {access_token}"
    elif cookie:
        headers["Cookie"] = cookie
        if api_key:
            headers["Api-Key"] = api_key
    return headers


def make_session(cookie=None, api_key=None, access_token=None):
    """Return a requests.Session wired up for the MMF JSON API."""
    session = requests.Session()
    session.headers.update(build_headers(api_key=api_key, access_token=access_token, cookie=cookie))
    return session


# ── API calls ─────────────────────────────────────────────────────────────────

def get_user_id(session):
    """Return the authenticated user's numeric ID. Raises AuthError on 401/403."""
    resp = session.get(BASE_URL + USER_EP)
    if resp.status_code in (401, 403):
        raise AuthError(
            "API rejected your credentials (HTTP {}).\n"
            "• Cookie-only mode: MMF may require an Api-Key header — try adding your API key.\n"
            "• Token mode: check that your access token has not expired.".format(resp.status_code)
        )
    resp.raise_for_status()
    data = resp.json()
    user_href = data.get("_links", {}).get("self", [{}])[0].get("href", "")
    user_id = user_href.rstrip("/").split("/")[-1]
    if not user_id.isdigit():
        user_id = str(data.get("id", ""))
    return user_id


def iso_dt(date_str, end_of_day=False):
    """Convert YYYY-MM-DD to ISO8601 UTC string for the API."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    if end_of_day:
        dt = dt.replace(hour=23, minute=59, second=59)
    dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_workouts(session, user_id, started_after, started_before, progress_callback=None):
    """Page through /v7.1/workout/ and yield each workout dict.

    progress_callback(fetched: int, total: int) is called after each workout.
    Raises AuthError on 401.
    """
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
            raise AuthError("401 Unauthorized while fetching workouts — cookie may have expired.")
        resp.raise_for_status()
        data = resp.json()

        total_count = data.get("total_count", 0)
        workouts    = data.get("_embedded", {}).get("workouts", [])

        if not workouts:
            break

        for w in workouts:
            yield w
            total_fetched += 1
            if progress_callback:
                progress_callback(total_fetched, total_count)

        if total_fetched >= total_count:
            break

        params["offset"] += PAGE_LIMIT
        time.sleep(RATE_SLEEP)


def parse_workout(w):
    """Extract a flat dict of the fields we care about."""
    agg   = w.get("aggregates", {})
    links = w.get("_links", {})

    workout_id    = links.get("self",          [{}])[0].get("id", "")
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
        "workout_id":            workout_id,
        "name":                  w.get("name", ""),
        "start_datetime":        w.get("start_datetime", ""),
        "start_locale_timezone": w.get("start_locale_timezone", ""),
        "activity_type_id":      activity_type,
        "distance_km":           meters_to_km(dist_m),
        "distance_miles":        meters_to_miles(dist_m),
        "duration_seconds":      int(elapsed_s) if elapsed_s else "",
        "duration_hms":          seconds_to_hms(elapsed_s),
        "active_time_seconds":   int(active_s) if active_s else "",
        "calories_kcal":         joules_to_kcal(energy_j),
        "avg_speed_kmh":         mps_to_kmh(avg_spd_mps),
        "avg_speed_mph":         mps_to_mph(avg_spd_mps),
        "max_speed_kmh":         mps_to_kmh(max_spd_mps),
        "avg_heart_rate":        int(hr_avg) if hr_avg else "",
        "max_heart_rate":        int(hr_max) if hr_max else "",
        "steps_total":           int(steps) if steps else "",
        "source":                w.get("source", ""),
        "notes":                 w.get("notes", ""),
        "workout_url":           f"https://www.mapmyrun.com/workout/{workout_id}/",
    }


# ── Output helpers ────────────────────────────────────────────────────────────

def workouts_to_csv_bytes(rows):
    """Serialise workout rows to UTF-8 CSV bytes (for in-memory / download use)."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


def write_csv(rows, out_path):
    """Write workout rows to a CSV file on disk (CLI use)."""
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {len(rows)} workouts → {out_path}")
