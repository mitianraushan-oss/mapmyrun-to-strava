"""
mmf_downloader.py
-----------------
Library module for downloading MapMyFitness workouts as TCX files.
No sys.exit, no print — callers handle UX.
"""
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

# ── Constants ─────────────────────────────────────────────────────────────────

TCX_URL_TEMPLATE = "https://www.mapmyfitness.com/workout/export/{workout_id}/tcx"

HEADERS_BASE = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer":         "https://www.mapmyfitness.com/",
}

# MapMyFitness activity_type_id → Strava TCX Sport tag
ACTIVITY_SPORT_MAP = {
    "9":   "Walking",
    "16":  "Running",
    "11":  "Biking",
    "12":  "Hiking",
    "14":  "Running",
    "15":  "Running",
    "17":  "Biking",
    "18":  "Walking",
    "320": "Walking",
}

STRAVA_FREE_LIMIT  = 15
STRAVA_DAILY_LIMIT = 30


# ── Session helpers ───────────────────────────────────────────────────────────

def parse_cookie_string(cookie_str):
    """Parse a raw browser cookie string into a dict."""
    cookies = {}
    for part in cookie_str.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            cookies[k.strip()] = v.strip()
    return cookies


def make_session(cookie_str):
    """Return a requests.Session loaded with browser cookies for the web endpoints."""
    session = requests.Session()
    session.headers.update(HEADERS_BASE)
    session.cookies.update(parse_cookie_string(cookie_str))
    return session


def verify_session(session):
    """Return True if the session is logged in, False if cookies are invalid/expired."""
    try:
        resp = session.get(
            "https://www.mapmyfitness.com/dashboard/",
            timeout=15,
            allow_redirects=True,
        )
        return "login" not in resp.url and "sign_in" not in resp.url
    except requests.RequestException:
        return False


# ── CSV parsing ───────────────────────────────────────────────────────────────

def parse_date(date_str):
    """Try to parse a date string in multiple formats. Returns datetime or None."""
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S+00:00",
                "%m/%d/%Y", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            clean = date_str.strip()[:19]
            return datetime.strptime(clean, fmt[:len(clean)])
        except ValueError:
            continue
    return None


def load_workout_ids(csv_path, limit=None, from_date=None, to_date=None):
    """Return list of {workout_id, date, activity} dicts from a CSV file.

    Supports mmf_workouts.csv (workout_url column) and original MMF export (Link column).
    Raises ValueError on unrecognised CSV format.
    """
    df = pd.read_csv(csv_path, on_bad_lines="skip")
    df.columns = [c.strip() for c in df.columns]

    if "workout_url" in df.columns:
        url_col, date_col, activity_col = "workout_url", "start_datetime", "activity_type_id"
    elif "Link" in df.columns:
        url_col, date_col, activity_col = "Link", "Workout Date", "Activity Type"
    else:
        raise ValueError(
            "Cannot find workout URL column. Expected 'workout_url' or 'Link'. "
            f"Found: {list(df.columns)}"
        )

    df = df[df[url_col].notna()].copy()
    df = df[df[url_col].str.contains(r"mapmyrun\.com/workout/|mapmyfitness\.com/workout/", na=False)]

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
        df = df[df[date_col].apply(in_range)].copy()

    if limit:
        df = df.head(limit)

    workouts = []
    for _, row in df.iterrows():
        link = str(row[url_col]).strip()
        m = re.search(r"/workout/(\d+)", link)
        if not m:
            continue
        raw_date = str(row.get(date_col, "unknown")).strip()[:10].replace("/", "-").replace(" ", "_")
        activity = str(row.get(activity_col, "workout")).strip().replace(" ", "_")
        workouts.append({"workout_id": m.group(1), "date": raw_date, "activity": activity})
    return workouts


# ── TCX download ──────────────────────────────────────────────────────────────

def _make_filename(workout):
    return "{}_{}_{}.tcx".format(workout["date"], workout["activity"], workout["workout_id"])


def fetch_and_patch_tcx(session, workout):
    """Download and Sport-patch a single TCX file.

    Returns (status, filename, content_str) where status is one of:
      'ok' — downloaded and patched successfully
      'fail' — network error or bad response
      'expired' — session expired / login wall
    content_str is None on failure.
    """
    wid      = workout["workout_id"]
    filename = _make_filename(workout)
    url      = TCX_URL_TEMPLATE.format(workout_id=wid)

    try:
        resp = session.get(url, timeout=30, allow_redirects=True)
    except requests.RequestException:
        return "fail", filename, None

    content = resp.text.strip()

    if resp.status_code == 200 and (
        content.startswith("<?xml") or content.startswith("<TrainingCenterDatabase")
    ):
        sport   = ACTIVITY_SPORT_MAP.get(str(workout.get("activity", "")), "Other")
        patched = re.sub(r'Sport="[^"]*"', f'Sport="{sport}"', resp.text, count=1)
        return "ok", filename, patched

    if "login" in resp.url or "sign_in" in resp.url or resp.status_code in (401, 403):
        return "expired", filename, None

    if content.startswith("<!DOCTYPE") or content.startswith("<html"):
        return "fail", filename, None

    return "fail", filename, None


def download_tcx(session, workout, outdir):
    """Write a single workout TCX to outdir (CLI use). Returns status string.

    Skips files that already exist (idempotent reruns).
    """
    filepath = outdir / _make_filename(workout)
    if filepath.exists():
        return "skip"
    status, _, content = fetch_and_patch_tcx(session, workout)
    if status == "ok":
        filepath.write_text(content, encoding="utf-8")
    return status
