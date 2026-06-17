"""
app.py — MapMyFitness Exporter
Streamlit web UI: export workouts to CSV and download TCX files as a ZIP.
"""
import io
import time
import zipfile
from datetime import date, timedelta

import streamlit as st

import mmf_api
import mmf_downloader

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="MapMyFitness Exporter",
    page_icon="🏃",
    layout="centered",
)

# ── Session state defaults ────────────────────────────────────────────────────

for key, default in [("rows", []), ("csv_bytes", None), ("zip_bytes", None)]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🏃 MMF Exporter")
    st.caption("Export your MapMyFitness workouts")

    st.subheader("Authentication")
    cookie = st.text_input(
        "Browser Cookie",
        type="password",
        placeholder="Paste your MMF cookie here (masked for privacy)",
        help=(
            "Chrome: DevTools → Network → any mapmyfitness.com request "
            "→ Request Headers → cookie: — copy the entire value."
        ),
    )

    with st.expander("Advanced (API key)"):
        api_key = st.text_input(
            "MMF API Key (optional)",
            type="password",
            help="May be required when using cookie-only auth against the JSON API.",
        )

    st.subheader("Date range")
    col1, col2 = st.columns(2)
    with col1:
        from_date = st.date_input("From", value=date(date.today().year, 1, 1))
    with col2:
        to_date = st.date_input("To", value=date.today())

    dl_delay = st.slider(
        "Download delay (s)",
        min_value=0.5, max_value=3.0, value=1.0, step=0.5,
        help="Pause between TCX requests. Lower = faster but higher risk of being rate-limited.",
    )

    st.divider()

    st.markdown("**ℹ️ About This Tool**")
    st.caption(
        "👨‍💻 Open source: [github.com/mitianraushan-oss/mapmyrun-to-strava]"
        "(https://github.com/mitianraushan-oss/mapmyrun-to-strava)\n\n"
        "⚠️ Not affiliated with MapMyFitness, Under Armour, or Strava\n\n"
        "🔒 Your cookies are never stored on our servers\n\n"
        "🗑️ All session data is deleted immediately after download\n\n"
        "⏱️ Requests are rate-limited to respect MapMyFitness servers\n\n"
        "🛡️ You access only your own workout data"
    )

    st.divider()

    # ── Donate ────────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div style="
            background: linear-gradient(135deg, #FFF3CD 0%, #FFE0B2 100%);
            border: 1px solid #FFCC80;
            border-radius: 12px;
            padding: 16px;
            text-align: center;
        ">
            <a href="https://paypal.me/raushankumar2804" target="_blank"
               style="
                   display: inline-block;
                   background: linear-gradient(135deg, #FFC107 0%, #FF9800 100%);
                   color: #3E2723;
                   font-weight: 700;
                   font-size: 1rem;
                   text-decoration: none;
                   padding: 10px 20px;
                   border-radius: 8px;
                   box-shadow: 0 2px 6px rgba(0,0,0,0.15);
               ">☕ Buy me a coffee</a>
            <div style="
                margin-top: 10px;
                font-size: 0.85rem;
                color: #5D4037;
            ">If this tool saved you time, consider supporting!</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Main content ──────────────────────────────────────────────────────────────

st.title("MapMyFitness Exporter")
st.markdown(
    "Export your workouts to **CSV** and download **TCX files** ready for Strava import.\n\n"
    "Paste your browser cookie in the sidebar, pick a date range, then follow the steps below."
)

st.info(
    "🔒 **Privacy:** Your cookies are used only for this session and are never stored on our "
    "servers. They are discarded immediately after your TCX files are downloaded.",
    icon=None,
)

st.info(
    "📸 **Photos:** Workout photos from MapMyRun are not transferred. TCX format does not "
    "support photos. To migrate photos, save them from MapMyRun manually and upload to each "
    "Strava activity individually.",
    icon=None,
)

st.divider()

# ── Step 1: Export CSV ────────────────────────────────────────────────────────

st.header("Step 1 — Export Workouts to CSV")

export_disabled = not cookie.strip()
if export_disabled:
    st.info("Paste your cookie in the sidebar to get started.")

if st.button("Export Workouts", disabled=export_disabled, type="primary"):
    # Reset downstream state when re-exporting
    st.session_state.rows      = []
    st.session_state.csv_bytes = None
    st.session_state.zip_bytes = None

    with st.spinner("Authenticating with MapMyFitness…"):
        try:
            session = mmf_api.make_session(
                cookie=cookie.strip(),
                api_key=api_key.strip() or None,
            )
            user_id = mmf_api.get_user_id(session)
        except mmf_api.AuthError as e:
            st.error(f"**Authentication failed:** {e}")
            st.stop()
        except Exception as e:
            st.error(f"**Unexpected error during auth:** {e}")
            st.stop()

    started_after  = mmf_api.iso_dt(from_date.strftime("%Y-%m-%d"), end_of_day=False)
    started_before = mmf_api.iso_dt(to_date.strftime("%Y-%m-%d"),   end_of_day=True)

    progress_bar = st.progress(0.0, text="Fetching workouts…")
    status_text  = st.empty()

    def on_progress(fetched, total):
        frac = min(fetched / total, 1.0) if total > 0 else 0.0
        progress_bar.progress(frac, text=f"Fetching workout {fetched} of {total}…")

    rows = []
    try:
        for w in mmf_api.fetch_workouts(session, user_id, started_after, started_before, on_progress):
            rows.append(mmf_api.parse_workout(w))
    except mmf_api.AuthError as e:
        st.error(f"**Auth error while fetching:** {e}")
        st.stop()
    except Exception as e:
        st.error(f"**Error fetching workouts:** {e}")
        st.stop()

    progress_bar.progress(1.0, text="Done!")

    if not rows:
        status_text.warning("No workouts found in that date range.")
    else:
        st.session_state.rows      = rows
        st.session_state.csv_bytes = mmf_api.workouts_to_csv_bytes(rows)
        status_text.success(f"Found **{len(rows)} workouts**.")

if st.session_state.csv_bytes:
    st.download_button(
        label=f"⬇ Download CSV ({len(st.session_state.rows)} workouts)",
        data=st.session_state.csv_bytes,
        file_name="mmf_workouts.csv",
        mime="text/csv",
    )

st.divider()

# ── Step 2: Download TCX files ────────────────────────────────────────────────

st.header("Step 2 — Download TCX Files")

if not st.session_state.rows:
    st.info("Complete Step 1 first to enable TCX download.")
else:
    n_workouts = len(st.session_state.rows)

    # Strava limit advisory
    with st.expander("Strava upload limits — read before uploading"):
        st.markdown(
            f"- **Free account:** {mmf_downloader.STRAVA_FREE_LIMIT} TCX uploads lifetime "
            "(then manual entry only)\n"
            "- **Paid account:** Unlimited uploads\n"
            f"- **Daily limit:** {mmf_downloader.STRAVA_DAILY_LIMIT} files per day (free and paid)\n"
            "- **Bulk upload:** Up to 25 files at a time via the Strava web UI"
        )
        if n_workouts > mmf_downloader.STRAVA_FREE_LIMIT:
            st.warning(
                f"You have **{n_workouts} workouts** — free Strava users can only upload "
                f"**{mmf_downloader.STRAVA_FREE_LIMIT}** before hitting the lifetime limit."
            )
        if n_workouts > mmf_downloader.STRAVA_DAILY_LIMIT:
            days = -(-n_workouts // mmf_downloader.STRAVA_DAILY_LIMIT)
            st.warning(
                f"**{n_workouts} workouts** will take at least **{days} day(s)** to upload "
                f"(max {mmf_downloader.STRAVA_DAILY_LIMIT} per day)."
            )

    if st.button("Download TCX Files", type="primary"):
        st.session_state.zip_bytes = None

        with st.spinner("Verifying cookie for TCX download…"):
            dl_session = mmf_downloader.make_session(cookie.strip())
            if not mmf_downloader.verify_session(dl_session):
                st.error(
                    "**Cookie rejected for TCX download.** "
                    "Re-copy fresh cookies from your browser and try again."
                )
                st.stop()

        workouts = [
            {
                "workout_id": r["workout_id"],
                "date":       str(r["start_datetime"])[:10].replace("/", "-"),
                "activity":   str(r["activity_type_id"]),
            }
            for r in st.session_state.rows
        ]

        progress_bar = st.progress(0.0, text="Downloading TCX files…")
        status_text  = st.empty()
        tcx_files    = []
        ok = fail = 0
        expired = False

        for i, w in enumerate(workouts):
            status, filename, content = mmf_downloader.fetch_and_patch_tcx(dl_session, w)

            if status == "ok":
                tcx_files.append((filename, content))
                ok += 1
            elif status == "expired":
                st.error(
                    "**Session expired mid-download.** "
                    "Re-copy fresh cookies and try again — already-collected files are included in the ZIP."
                )
                expired = True
                break
            else:
                fail += 1

            pct = (i + 1) / len(workouts)
            progress_bar.progress(pct, text=f"Downloaded {ok} of {len(workouts)} | Failed: {fail}")
            time.sleep(dl_delay)

        if tcx_files:
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for fname, content in tcx_files:
                    zf.writestr(fname, content)
            buf.seek(0)
            st.session_state.zip_bytes = buf.getvalue()

        if not expired:
            progress_bar.progress(1.0, text="Done!")
            status_text.success(f"Downloaded **{ok}** TCX files. Failed: {fail}.")

    if st.session_state.zip_bytes:
        st.download_button(
            label=f"⬇ Download ZIP ({len(st.session_state.rows)} workouts)",
            data=st.session_state.zip_bytes,
            file_name="mmf_tcx_files.zip",
            mime="application/zip",
        )
