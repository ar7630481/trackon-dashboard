import base64
import datetime
import hashlib
import hmac
import html as html_module
import io
import json
import os
import re
import time
import uuid

import numpy as np
import pandas as pd
import streamlit as st

try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_OK = True
except ImportError:
    PLOTLY_OK = False


# ============================================================
# 1. COMMON HELPERS & SAFE FORMATTING
# ============================================================
def format_inr_short(amount):
    """Formats numeric INR values into executive Cr / L / K shorthand."""
    try:
        val = float(amount)
    except (TypeError, ValueError):
        return "₹0"
    if pd.isna(val) or np.isinf(val) or val == 0:
        return "₹0"
    sign = "-" if val < 0 else ""
    val = abs(val)
    if val >= 1e7:
        return f"{sign}₹{val / 1e7:.2f} Cr"
    if val >= 1e5:
        return f"{sign}₹{val / 1e5:.2f} L"
    if val >= 1e3:
        return f"{sign}₹{val / 1e3:.1f} K"
    return f"{sign}₹{val:,.0f}"


def _find_col(df, candidates):
    if df is None or df.empty:
        return None
    col_map = {str(c).replace(" ", "").replace("_", "").lower(): c for c in df.columns}
    for name in candidates:
        key = name.replace(" ", "").replace("_", "").lower()
        if key in col_map:
            return col_map[key]
    return None


def _parse_pct(val):
    if isinstance(val, (int, float)) and not pd.isna(val):
        return float(val)
    if not isinstance(val, str):
        return None
    matches = re.findall(r"(-?\d+(?:\.\d+)?)\s*%", val)
    return float(matches[-1]) if matches else None


def _parse_duration_hrs(val):
    if pd.isna(val):
        return np.nan
    s = str(val).strip()
    if not s or s in ("-", "nan", "None"):
        return np.nan
    sign = -1.0 if s.startswith("-") else 1.0
    s_clean = s.lstrip("+-")
    if ":" in s_clean:
        parts = s_clean.split(":")
        try:
            return sign * (float(parts[0]) + float(parts[1]) / 60.0)
        except ValueError:
            return np.nan
    try:
        return float(s)
    except ValueError:
        return np.nan


def _style_plotly(fig, theme, title="", height=370):
    fig.update_layout(
        title=dict(text=title, font=dict(size=15, color=theme["text"])),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=theme["text"], family="Inter, Segoe UI, sans-serif", size=12),
        height=height,
        margin=dict(t=48, b=40, l=18, r=18),
        legend=dict(orientation="h", yanchor="bottom", y=-0.28, xanchor="center", x=0.5),
        xaxis=dict(gridcolor=theme["line"], zerolinecolor=theme["line"]),
        yaxis=dict(gridcolor=theme["line"], zerolinecolor=theme["line"]),
    )
    return fig


def _render_bi_callout(title, body_html, accent_color, theme):
    st.markdown(
        f"""
        <div style="
            border-left: 4px solid {accent_color};
            background: linear-gradient(110deg, {theme['card1']}, {theme['card2']});
            border-top: 1px solid {theme['line']};
            border-right: 1px solid {theme['line']};
            border-bottom: 1px solid {theme['line']};
            border-radius: 12px;
            padding: 0.85rem 1.05rem;
            margin: 0.55rem 0 0.95rem;
        ">
            <div style="font-size:0.74rem;font-weight:800;letter-spacing:0.09em;text-transform:uppercase;color:{accent_color};">
                {html_module.escape(title)}
            </div>
            <div style="font-size:0.89rem;color:{theme['text']};margin-top:0.25rem;line-height:1.45;">
                {body_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# 2. FULL-SCREEN NEW-WINDOW RAW DATA EXPLORER (?raw_view=1)
# ============================================================
def _snapshot_dir(data_dir):
    snap_dir = os.path.join(data_dir, ".raw_snapshots")
    os.makedirs(snap_dir, exist_ok=True)
    return snap_dir


def _cleanup_old_snapshots(snap_dir, max_age_seconds=10800):
    now = time.time()
    try:
        for fname in os.listdir(snap_dir):
            fpath = os.path.join(snap_dir, fname)
            if os.path.isfile(fpath) and (now - os.path.getmtime(fpath)) > max_age_seconds:
                os.remove(fpath)
    except OSError:
        pass


def _read_signing_key(data_dir):
    key_path = os.path.join(data_dir, ".overall_issues_link_key")
    try:
        with open(key_path, "rb") as f:
            key = f.read()
        if len(key) >= 32:
            return key
    except OSError:
        pass
    key = os.urandom(32)
    try:
        with open(key_path, "wb") as f:
            f.write(key)
    except OSError:
        pass
    return key


def create_raw_view_token(data_dir, username, snap_id, ttl_seconds=7200):
    now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    payload = json.dumps(
        {"user": str(username), "snap": str(snap_id), "scope": "raw-view", "expires": now + ttl_seconds},
        separators=(",", ":"),
    ).encode("utf-8")
    encoded = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    sig = hmac.new(_read_signing_key(data_dir), encoded.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{encoded}.{sig}"


def verify_raw_view_token(data_dir, token, expected_snap_id, users_db):
    if not token or "." not in token:
        return None
    if not re.match(r"^[a-f0-9]{16}$", str(expected_snap_id or "")):
        return None
    encoded, supplied_sig = token.rsplit(".", 1)
    expected_sig = hmac.new(_read_signing_key(data_dir), encoded.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(supplied_sig, expected_sig):
        return None
    try:
        padded = encoded + ("=" * (-len(encoded) % 4))
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))
        now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        if payload.get("scope") != "raw-view":
            return None
        if payload.get("snap") != expected_snap_id:
            return None
        if int(payload.get("expires", 0)) < now:
            return None
        username = str(payload.get("user", ""))
        user_info = users_db.get(username, {})
        if not user_info or not user_info.get("active", True):
            return None
        return username
    except Exception:
        return None


def save_raw_snapshot(df, data_dir, title, subtitle="", sheet_type="generic", username="admin"):
    snap_dir = _snapshot_dir(data_dir)
    _cleanup_old_snapshots(snap_dir)

    sig_raw = f"{title}|{subtitle}|{len(df)}|{list(df.columns)}"
    cache_key = f"_snap_cache_{hashlib.md5(sig_raw.encode('utf-8')).hexdigest()[:12]}"
    existing = st.session_state.get(cache_key)
    if existing and os.path.exists(os.path.join(snap_dir, f"{existing[0]}.pkl")):
        snap_id = existing[0]
    else:
        snap_id = uuid.uuid4().hex[:16]
        df_clean = df.reset_index(drop=True).copy()
        df_clean.to_pickle(os.path.join(snap_dir, f"{snap_id}.pkl"))
        meta = {
            "title": str(title),
            "subtitle": str(subtitle),
            "sheet_type": str(sheet_type),
            "rows": int(len(df_clean)),
            "cols": int(len(df_clean.columns)),
            "created_at": (datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)).strftime(
                "%d %b %Y, %I:%M %p IST"
            ),
            "owner": str(username),
        }
        with open(os.path.join(snap_dir, f"{snap_id}.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f)
        st.session_state[cache_key] = (snap_id, time.time())

    token = create_raw_view_token(data_dir, username, snap_id)
    return snap_id, token


def render_new_window_raw_launcher(
    df,
    data_dir,
    title,
    subtitle,
    sheet_type,
    excel_writer_fn,
    style_fn,
    theme,
    key_prefix,
    file_prefix="Raw_Data",
    compact_mode=False,
):
    """
    Opens raw Excel data in a 100% Full-Screen New Window (?raw_view=1),
    keeps 1-click styled Excel download, and avoids cramped inline dumps.
    """
    if df is None or df.empty:
        st.info(f"No raw records found for {title}.")
        return

    username = st.session_state.get("username", "admin")
    snap_id, token = save_raw_snapshot(df, data_dir, title, subtitle, sheet_type, username)
    raw_url = f"?raw_view=1&snap={snap_id}&raw_auth={token}"

    st.markdown(
        f"""
        <div style="
            display:flex; flex-wrap:wrap; justify-content:space-between; align-items:center; gap:0.8rem;
            padding:0.85rem 1.05rem; margin:0.5rem 0;
            border:1px solid {theme['line']}; border-radius:14px;
            background:linear-gradient(120deg, {theme['card1']}, {theme['card2']});
        ">
            <div>
                <div style="font-size:0.71rem;font-weight:800;letter-spacing:0.1em;text-transform:uppercase;color:{theme['accent']};">
                    Full-Screen Raw Excel Explorer
                </div>
                <div style="font-size:0.98rem;font-weight:750;color:{theme['text']};margin-top:0.12rem;">
                    {html_module.escape(title)}
                    <span style="font-size:0.82rem;font-weight:500;color:{theme['muted']};margin-left:0.35rem;">
                        ({len(df):,} rows · {len(df.columns)} cols)
                    </span>
                </div>
                <div style="font-size:0.77rem;color:{theme['muted']};margin-top:0.08rem;">
                    {html_module.escape(subtitle)}
                </div>
            </div>
            <div>
                <a href="{raw_url}" target="_blank" rel="noopener noreferrer" style="
                    display:inline-flex; align-items:center; gap:0.45rem;
                    background:{theme['blue']}; color:#ffffff; text-decoration:none;
                    font-weight:700; font-size:0.86rem; padding:0.62rem 1.15rem;
                    border-radius:10px; box-shadow:0 6px 16px rgba(0,0,0,0.18);
                    white-space:nowrap;
                ">🖥️ Open Full-Screen Raw Data (New Window) ↗</a>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if compact_mode:
        return

    c_dl, c_peek = st.columns([1.25, 2.75])
    excel_buf = io.BytesIO()
    with pd.ExcelWriter(
        excel_buf, engine="xlsxwriter", engine_kwargs={"options": {"nan_inf_to_errors": True}}
    ) as writer:
        excel_writer_fn(writer, df, "Focused_Raw_Data", sheet_type=sheet_type)
    safe_fname = re.sub(r"[^A-Za-z0-9_-]+", "_", file_prefix).strip("_") or "Trackon_Raw"
    c_dl.download_button(
        "📥 Download Styled Excel (.xlsx)",
        data=excel_buf.getvalue(),
        file_name=f"{safe_fname}_{len(df)}rows.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        key=f"{key_prefix}_dl_{snap_id}",
    )
    with c_peek.expander(f"👁️ Quick Preview (Top 15 of {len(df):,} rows) — Full grid opens in New Window", expanded=False):
        st.dataframe(style_fn(df.head(15)), use_container_width=True, hide_index=True, height=290)


def render_fullscreen_raw_window(data_dir, snap_id, excel_writer_fn, style_fn, theme):
    """Dedicated 100% Full-Screen Raw Data Explorer opened via ?raw_view=1."""
    st.markdown(
        """
        <style>
            [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }
            [data-testid="stHeader"] { height: 0.35rem !important; background: transparent !important; }
            [data-testid="stMainBlockContainer"], .block-container {
                max-width: 100vw !important;
                width: 100% !important;
                padding: 0.85rem 1.4rem 1.8rem !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if not re.match(r"^[a-f0-9]{16}$", str(snap_id or "")):
        st.error("❌ Invalid snapshot reference.")
        st.stop()

    snap_dir = _snapshot_dir(data_dir)
    pkl_path = os.path.join(snap_dir, f"{snap_id}.pkl")
    meta_path = os.path.join(snap_dir, f"{snap_id}.json")

    if not os.path.exists(pkl_path):
        st.warning("⏳ Snapshot expired (auto-clears after 3 hours or cloud reboot). Go back to the main dashboard tab and click 'Open Full-Screen Raw Data' again.")
        st.stop()

    df = pd.read_pickle(pkl_path)
    meta = {}
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            meta = {}

    title = meta.get("title", "Full-Screen Raw Data Explorer")
    subtitle = meta.get("subtitle", "")
    sheet_type = meta.get("sheet_type", "generic")
    created_at = meta.get("created_at", "")

    st.markdown(
        f"""
        <div class="app-topline" style="margin-bottom:0.8rem;">
            <div>
                <div class="app-eyebrow">Trackon • Full-Screen Raw Excel Explorer</div>
                <div class="app-brandline">{html_module.escape(title)}
                    <span class="app-subline">{html_module.escape(subtitle)}</span>
                </div>
            </div>
            <div class="app-chip">Rows: {len(df):,} · Cols: {len(df.columns)} · {html_module.escape(created_at)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Excel-Style Filter Toolbar
    f1, f2, f3, f4 = st.columns([2.0, 1.3, 1.3, 1.4])
    q_search = f1.text_input("🔍 Global Search (any column):", placeholder="Search Route, Vehicle, Vendor, Invoice, Remark...", key="fs_q")

    filtered = df.copy()
    status_col = _find_col(
        filtered,
        ["Remark with 15 min waiver", "Remark", "Payment Group", "Operations Outcome", "Status", "Utilization Class", "Final_Type"],
    )
    if status_col:
        s_opts = sorted(filtered[status_col].dropna().astype(str).unique().tolist())
        sel_s = f2.multiselect(f"Filter {status_col}:", s_opts, key="fs_status")
        if sel_s:
            filtered = filtered[filtered[status_col].astype(str).isin(sel_s)]
    else:
        f2.caption("No status filter")

    entity_col = _find_col(filtered, ["VendorName", "Vendor Name", "Origin RO", "RO Name", "RO_Clean", "Route Path", "Final_Route"])
    if entity_col:
        e_opts = sorted(filtered[entity_col].dropna().astype(str).unique().tolist())
        sel_e = f3.multiselect(f"Filter {entity_col}:", e_opts, key="fs_entity")
        if sel_e:
            filtered = filtered[filtered[entity_col].astype(str).isin(sel_e)]
    else:
        f3.caption("No entity filter")

    all_cols = list(filtered.columns)
    vis_cols = f4.multiselect("Visible Columns:", all_cols, default=all_cols, key="fs_cols")
    if not vis_cols:
        vis_cols = all_cols

    if q_search.strip():
        q = q_search.strip()
        mask = filtered.astype(str).apply(lambda col: col.str.contains(q, case=False, regex=False, na=False)).any(axis=1)
        filtered = filtered[mask]

    # Live KPI Bar
    k_specs = [
        ("Filtered Rows", f"{len(filtered):,}"),
        ("Share of Total", f"{(len(filtered) / len(df) * 100) if len(df) else 0:.1f}%"),
    ]
    amt_col = _find_col(filtered, ["Amount", "Cost", "Total Trip Cost", "Balance Payable Amount"])
    if amt_col:
        amt_sum = pd.to_numeric(filtered[amt_col], errors="coerce").fillna(0).sum()
        k_specs.append((f"Total {amt_col}", format_inr_short(amt_sum)))
    wt_col = _find_col(filtered, ["Wt", "Total Carried Wt"])
    if wt_col:
        wt_sum = pd.to_numeric(filtered[wt_col], errors="coerce").fillna(0).sum()
        k_specs.append((f"Total {wt_col}", f"{wt_sum:,.1f}"))
    if status_col:
        exc_cnt = int(filtered[status_col].astype(str).str.contains("Late|Hold|Draft|Underutilized", case=False, na=False).sum())
        k_specs.append(("Exceptions / Flags", f"{exc_cnt:,}"))

    for kc, (kl, kv) in zip(st.columns(len(k_specs)), k_specs):
        kc.metric(kl, kv)

    # Export + Safe Pagination Toolbar (prevents browser freeze on 50k+ rows)
    out_df = filtered[vis_cols].copy()
    b1, b2, b3, b4 = st.columns([1.2, 0.9, 1.1, 1.3])
    xl_buf = io.BytesIO()
    with pd.ExcelWriter(
        xl_buf, engine="xlsxwriter", engine_kwargs={"options": {"nan_inf_to_errors": True}}
    ) as writer:
        excel_writer_fn(writer, out_df, "Raw_Data", sheet_type=sheet_type)
    safe_title = re.sub(r"[^A-Za-z0-9_-]+", "_", title)[:45] or "Trackon_Raw"
    b1.download_button(
        "📥 Download Filtered Excel",
        data=xl_buf.getvalue(),
        file_name=f"{safe_title}_Filtered.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        use_container_width=True,
        key="fs_dl_xlsx",
    )
    b2.download_button(
        "📄 Download CSV",
        data=out_df.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"{safe_title}_Filtered.csv",
        mime="text/csv",
        use_container_width=True,
        key="fs_dl_csv",
    )

    page_size = b3.selectbox("Rows per page:", [500, 1000, 2500, 5000, "All"], index=1, key="fs_page_size")
    total_rows = len(out_df)
    if page_size == "All" or total_rows <= int(page_size):
        page_df = out_df
        b4.caption(f"Showing all {total_rows:,} rows")
    else:
        ps = int(page_size)
        total_pages = max(1, (total_rows + ps - 1) // ps)
        page_no = b4.number_input(f"Page (1–{total_pages}):", min_value=1, max_value=total_pages, value=1, step=1, key="fs_page_no")
        start_i = (page_no - 1) * ps
        page_df = out_df.iloc[start_i : start_i + ps]

    # Render Big-Screen Full-Height Grid
    display_obj = style_fn(page_df) if page_df.size <= 35000 else page_df
    st.dataframe(display_obj, use_container_width=True, hide_index=True, height=690)

    # Built-in Quick Pivot inside Raw Window
    with st.expander("📊 Quick Pivot Slice (Group Filtered Rows by Any Column)", expanded=False):
        p1, p2 = st.columns([1, 2])
        grp_col = p1.selectbox("Group By:", vis_cols, key="fs_piv_col")
        piv = out_df.groupby(grp_col, dropna=False).size().reset_index(name="Count")
        if amt_col and amt_col in out_df.columns:
            amt_grp = (
                out_df.assign(_n=pd.to_numeric(out_df[amt_col], errors="coerce").fillna(0))
                .groupby(grp_col, dropna=False)["_n"]
                .sum()
                .reset_index(name=f"Total {amt_col}")
            )
            piv = piv.merge(amt_grp, on=grp_col, how="left")
        piv["Share %"] = (piv["Count"] / max(len(out_df), 1) * 100).round(1).astype(str) + "%"
        piv = piv.sort_values("Count", ascending=False).reset_index(drop=True)
        p2.dataframe(piv, use_container_width=True, hide_index=True, height=280)

    st.stop()


# ============================================================
# 3. POWER BI SUITE — OPERATIONS SUMMARY
# ============================================================
def render_ops_powerbi_suite(df_raw_leg, df_leg_sum, outcome_counts, theme, is_light):
    if not PLOTLY_OK or df_raw_leg is None or df_raw_leg.empty:
        return
    try:
        st.markdown("### ⚡ Power BI Operations Intelligence")
        ll = outcome_counts.get("Late Dep, Late Arr", 0)
        ol = outcome_counts.get("Ontime Dep, Late Arr", 0)
        lo = outcome_counts.get("Late Dep, Ontime Arr", 0)
        total_late_arr = ll + ol
        hub_share = (ll / total_late_arr * 100) if total_late_arr else 0.0
        transit_share = (ol / total_late_arr * 100) if total_late_arr else 0.0
        total_late_dep = ll + lo
        recovery_rate = (lo / total_late_dep * 100) if total_late_dep else 0.0

        rc1, rc2, rc3, rc4 = st.columns(4)
        rc1.metric("Hub-Driven Late Share", f"{hub_share:.1f}%", f"{ll:,} Late Dep→Arr")
        rc2.metric("Highway/Transit Late Share", f"{transit_share:.1f}%", f"{ol:,} Ontime Dep→Late Arr")
        rc3.metric("Driver Recovery Rate", f"{recovery_rate:.1f}%", f"{lo:,} Recovered on road")
        rc4.metric("Total Late Arrivals", f"{total_late_arr:,}", f"of {len(df_raw_leg):,} trips")

        if total_late_arr > 0:
            msg = (
                f"<b>Origin Hub Dispatches</b> drove <b>{hub_share:.1f}%</b> of late arrivals ({ll:,} trips), "
                f"while <b>Transit/Highway delays</b> drove <b>{transit_share:.1f}%</b> ({ol:,} trips). "
                f"Drivers recovered <b>{recovery_rate:.1f}%</b> of late departures ({lo:,} trips)."
            )
            _render_bi_callout("Root-Cause Attribution Signal", msg, "#ef4444" if hub_share >= 50 else "#f59e0b", theme)

        c1, c2 = st.columns([1.65, 1.0])
        with c1:
            date_col = _find_col(df_raw_leg, ["MCD_StartDate", "Date"])
            if date_col:
                tmp = df_raw_leg[[date_col]].copy()
                tmp["_dt"] = pd.to_datetime(tmp[date_col], dayfirst=True, errors="coerce").dt.date
                tmp["_oo"] = df_raw_leg.get("_OpsRemarkOutcome", pd.Series("", index=df_raw_leg.index)).eq("Ontime Dep, Ontime Arr").astype(int)
                tmp = tmp.dropna(subset=["_dt"])
                if not tmp.empty:
                    daily = tmp.groupby("_dt").agg(Trips=("_oo", "size"), OnTime=("_oo", "sum")).reset_index().sort_values("_dt")
                    daily["OnTime_Pct"] = (daily["OnTime"] / daily["Trips"] * 100).round(1)

                    fig_t = make_subplots(specs=[[{"secondary_y": True}]])
                    fig_t.add_trace(
                        go.Bar(x=daily["_dt"], y=daily["Trips"], name="Total Trips", marker_color=theme["blue"], opacity=0.35),
                        secondary_y=False,
                    )
                    fig_t.add_trace(
                        go.Scatter(
                            x=daily["_dt"], y=daily["OnTime_Pct"], name="On-Time E2E %",
                            mode="lines+markers+text", text=daily["OnTime_Pct"].map(lambda v: f"{v:.0f}%"),
                            textposition="top center", line=dict(color="#10b981", width=3), marker=dict(size=7),
                        ),
                        secondary_y=True,
                    )
                    fig_t.add_trace(
                        go.Scatter(
                            x=daily["_dt"], y=[85.0] * len(daily), name="85% SLA Target",
                            mode="lines", line=dict(color="#f59e0b", width=2, dash="dash"),
                        ),
                        secondary_y=True,
                    )
                    _style_plotly(fig_t, theme, "Daily Trip Volume vs On-Time E2E % Trend", height=360)
                    fig_t.update_yaxes(title_text="Trips", secondary_y=False)
                    fig_t.update_yaxes(title_text="On-Time %", range=[0, 114], secondary_y=True)
                    st.plotly_chart(fig_t, use_container_width=True, key="bi_ops_daily_trend")

        with c2:
            pie_df = pd.DataFrame([{"Outcome": k, "Trips": v} for k, v in outcome_counts.items() if v > 0])
            if not pie_df.empty:
                cmap = {
                    "Ontime Dep, Ontime Arr": "#10b981", "Ontime Dep, Late Arr": "#fb7185",
                    "Late Dep, Late Arr": "#ef4444", "Late Dep, Ontime Arr": "#a855f7",
                    "Late Dep, In-Transit": "#f59e0b", "Ontime Dep, In-Transit": "#eab308",
                    "No Departure": "#dc2626", "Missing Schedule": "#f97316",
                    "In-Transit": "#38bdf8", "Other": "#94a3b8",
                }
                fig_p = px.pie(pie_df, values="Trips", names="Outcome", hole=0.52, color="Outcome", color_discrete_map=cmap)
                fig_p.update_traces(textposition="inside", textinfo="percent")
                _style_plotly(fig_p, theme, "Exclusive Remark Outcome Split", height=360)
                st.plotly_chart(fig_p, use_container_width=True, key="bi_ops_donut")

        c3, c4 = st.columns(2)
        with c3:
            ro_col = _find_col(df_raw_leg, ["Origin RO", "RO Name"])
            if ro_col:
                rt = df_raw_leg[[ro_col]].copy()
                rt["_oo"] = df_raw_leg.get("_OpsRemarkOutcome", pd.Series("", index=df_raw_leg.index)).eq("Ontime Dep, Ontime Arr").astype(int)
                rg = rt.groupby(ro_col).agg(Trips=("_oo", "size"), OnTime=("_oo", "sum")).reset_index()
                rg = rg[rg["Trips"] > 0]
                if not rg.empty:
                    rg["OnTime_Pct"] = (rg["OnTime"] / rg["Trips"] * 100).round(1)
                    rg = rg.sort_values("OnTime_Pct", ascending=True).head(12)
                    fig_ro = px.bar(
                        rg, x="OnTime_Pct", y=ro_col, orientation="h",
                        text=rg.apply(lambda r: f"{r['OnTime_Pct']:.1f}% ({int(r['Trips'])})", axis=1),
                        color="OnTime_Pct", color_continuous_scale=[(0, "#ef4444"), (0.75, "#f59e0b"), (1, "#10b981")],
                        range_color=[0, 100],
                    )
                    fig_ro.update_traces(textposition="outside")
                    _style_plotly(fig_ro, theme, "RO Reliability Ranking (Lowest First)", height=360)
                    fig_ro.update_layout(coloraxis_showscale=False, xaxis=dict(range=[0, 118], title="On-Time E2E %"), yaxis=dict(title=""))
                    st.plotly_chart(fig_ro, use_container_width=True, key="bi_ops_ro_rank")

        with c4:
            route_col = _find_col(df_raw_leg, ["Route Path", "Route"])
            if route_col:
                rtt = df_raw_leg[[route_col]].copy()
                out_s = df_raw_leg.get("_OpsRemarkOutcome", pd.Series("", index=df_raw_leg.index))
                rtt["_late"] = out_s.isin(["Late Dep, Late Arr", "Ontime Dep, Late Arr"]).astype(int)
                rtg = rtt.groupby(route_col).agg(Trips=("_late", "size"), Late_Trips=("_late", "sum")).reset_index()
                rtg = rtg[rtg["Late_Trips"] > 0]
                if not rtg.empty:
                    rtg["Late_Pct"] = (rtg["Late_Trips"] / rtg["Trips"] * 100).round(1)
                    top_rt = rtg.nlargest(8, "Late_Trips").sort_values("Late_Trips", ascending=True)
                    fig_rt = px.bar(
                        top_rt, x="Late_Trips", y=route_col, orientation="h",
                        text=top_rt.apply(lambda r: f"{int(r['Late_Trips'])} late ({r['Late_Pct']:.0f}%)", axis=1),
                        color="Late_Pct", color_continuous_scale=[(0, "#f59e0b"), (1, "#dc2626")],
                    )
                    fig_rt.update_traces(textposition="outside")
                    _style_plotly(fig_rt, theme, "Top 8 Bottleneck Routes (by Late Volume)", height=360)
                    fig_rt.update_layout(coloraxis_showscale=False, xaxis=dict(title="Late Arrival Trips"), yaxis=dict(title=""))
                    st.plotly_chart(fig_rt, use_container_width=True, key="bi_ops_bottleneck_routes")
    except Exception as exc:
        st.caption(f"Operations BI charts skipped for current slice: {exc}")


# ============================================================
# 4. POWER BI SUITE — VENDOR PERFORMANCE
# ============================================================
def render_vendor_powerbi_suite(df_vperf_raw, df_vperf_raw_full, df_display, theme, is_light):
    if not PLOTLY_OK or df_vperf_raw is None or df_vperf_raw.empty:
        return
    try:
        st.markdown("### ⚡ Power BI Vendor Intelligence")
        status_col = _find_col(df_vperf_raw, ["Remark with 15 min waiver"])
        vendor_col = _find_col(df_vperf_raw, ["VendorName", "Vendor Name"])
        delay_col = _find_col(df_vperf_raw, ["Delay Hours"])

        if vendor_col and status_col:
            v_df = df_vperf_raw[[vendor_col, status_col]].copy()
            v_df["_ot"] = v_df[status_col].astype(str).eq("Ontime Arrival").astype(int)
            v_df["_lt"] = v_df[status_col].astype(str).eq("Late Arrival").astype(int)
            v_agg = v_df.groupby(vendor_col).agg(Trips=("_ot", "size"), OnTime=("_ot", "sum"), Late=("_lt", "sum")).reset_index()
            v_agg["OnTime_Pct"] = (v_agg["OnTime"] / v_agg["Trips"] * 100).round(1)
            v_agg["_sz"] = np.clip(v_agg["Trips"], 1, None)
            med_vol = float(v_agg["Trips"].median()) if not v_agg.empty else 10.0

            def _quad(r):
                if r["OnTime_Pct"] >= 85 and r["Trips"] >= med_vol:
                    return "⭐ Strategic Star"
                if r["OnTime_Pct"] < 85 and r["Trips"] >= med_vol:
                    return "🚨 High-Impact Risk"
                if r["OnTime_Pct"] >= 85:
                    return "🟢 Reliable Niche"
                return "⚠️ Watchlist"

            v_agg["Tier"] = v_agg.apply(_quad, axis=1)

            c1, c2 = st.columns([1.3, 1.0])
            with c1:
                fig_q = px.scatter(
                    v_agg, x="Trips", y="OnTime_Pct", size="_sz", color="Tier",
                    hover_name=vendor_col,
                    hover_data={"Trips": True, "OnTime_Pct": True, "Late": True, "_sz": False},
                    color_discrete_map={
                        "⭐ Strategic Star": "#10b981", "🚨 High-Impact Risk": "#ef4444",
                        "🟢 Reliable Niche": "#38bdf8", "⚠️ Watchlist": "#f59e0b",
                    },
                )
                fig_q.add_hline(y=85, line_dash="dash", line_color="#10b981", annotation_text="85% SLA")
                fig_q.add_vline(x=med_vol, line_dash="dot", line_color=theme["muted"], annotation_text="Median Vol")
                _style_plotly(fig_q, theme, "SLA Quadrant: Trip Volume vs On-Time Reliability", height=370)
                fig_q.update_yaxes(range=[0, 108], title="On-Time Arrival %")
                fig_q.update_xaxes(title="Total Trips")
                st.plotly_chart(fig_q, use_container_width=True, key="bi_ven_quadrant")

            with c2:
                if delay_col:
                    late_only = df_vperf_raw[df_vperf_raw[status_col].astype(str).eq("Late Arrival")]
                    if not late_only.empty:
                        hrs = late_only[delay_col].apply(_parse_duration_hrs).dropna()
                        hrs = hrs[hrs > 0.25]
                        if not hrs.empty:
                            labels = ["15–60m (Minor)", "1–3h (Moderate)", "3–6h (Severe)", ">6h (Critical)"]
                            cut_s = pd.cut(hrs, bins=[0.25, 1.0, 3.0, 6.0, 1e6], labels=labels).astype(str)
                            sev = cut_s.value_counts().reindex(labels, fill_value=0).reset_index()
                            sev.columns = ["Severity", "Trips"]
                            fig_s = px.bar(
                                sev, x="Severity", y="Trips", text="Trips", color="Severity",
                                color_discrete_sequence=["#fbbf24", "#f97316", "#ef4444", "#991b1b"],
                            )
                            fig_s.update_traces(textposition="outside")
                            _style_plotly(fig_s, theme, "Late Arrival Delay Severity", height=370)
                            fig_s.update_layout(showlegend=False, xaxis_title="", yaxis_title="Late Trips")
                            st.plotly_chart(fig_s, use_container_width=True, key="bi_ven_delay_sev")
                        else:
                            st.info("No numeric delay durations available for severity buckets.")
                    else:
                        st.success("🎉 Zero late arrivals in the current filtered view!")

        # WoW 7-Day Momentum
        date_col = _find_col(df_vperf_raw_full, ["Date"])
        if vendor_col and status_col and date_col and not df_vperf_raw_full.empty:
            wdf = df_vperf_raw_full[[vendor_col, status_col, date_col]].copy()
            wdf["_dt"] = pd.to_datetime(wdf[date_col], dayfirst=True, errors="coerce").dt.date
            wdf = wdf.dropna(subset=["_dt"])
            if not wdf.empty:
                max_d = wdf["_dt"].max()
                cur_m = (wdf["_dt"] >= max_d - datetime.timedelta(days=6)) & (wdf["_dt"] <= max_d)
                prv_m = (wdf["_dt"] >= max_d - datetime.timedelta(days=13)) & (wdf["_dt"] <= max_d - datetime.timedelta(days=7))
                wdf["_ot"] = wdf[status_col].astype(str).eq("Ontime Arrival").astype(int)
                cur_g = wdf[cur_m].groupby(vendor_col).agg(Cur_Trips=("_ot", "size"), Cur_OT=("_ot", "mean")).reset_index()
                prv_g = wdf[prv_m].groupby(vendor_col).agg(Prv_Trips=("_ot", "size"), Prv_OT=("_ot", "mean")).reset_index()
                mom = cur_g.merge(prv_g, on=vendor_col, how="inner")
                mom = mom[(mom["Cur_Trips"] >= 3) & (mom["Prv_Trips"] >= 3)]
                if not mom.empty:
                    mom["Prev %"] = (mom["Prv_OT"] * 100).round(1)
                    mom["Cur %"] = (mom["Cur_OT"] * 100).round(1)
                    mom["WoW Delta"] = (mom["Cur %"] - mom["Prev %"]).round(1)
                    m1, m2 = st.columns(2)
                    imp = mom[mom["WoW Delta"] > 0].nlargest(5, "WoW Delta")
                    dec = mom[mom["WoW Delta"] < 0].nsmallest(5, "WoW Delta")
                    with m1:
                        st.markdown("##### 🚀 Top WoW Improvers (7-Day Momentum)")
                        if not imp.empty:
                            d_i = imp[[vendor_col, "Prev %", "Cur %", "WoW Delta", "Cur_Trips"]].copy()
                            d_i["WoW Delta"] = d_i["WoW Delta"].map(lambda x: f"+{x:.1f}% ▲")
                            st.dataframe(d_i, use_container_width=True, hide_index=True)
                        else:
                            st.caption("No positive WoW movers (min 3 trips).")
                    with m2:
                        st.markdown("##### 📉 Steepest WoW SLA Drops (Immediate Call)")
                        if not dec.empty:
                            d_d = dec[[vendor_col, "Prev %", "Cur %", "WoW Delta", "Cur_Trips"]].copy()
                            d_d["WoW Delta"] = d_d["WoW Delta"].map(lambda x: f"{x:.1f}% ▼")
                            st.dataframe(d_d, use_container_width=True, hide_index=True)
                        else:
                            st.caption("No negative WoW drops (min 3 trips).")
    except Exception as exc:
        st.caption(f"Vendor BI charts skipped for current slice: {exc}")


# ============================================================
# 5. POWER BI SUITE — PAYMENT DASHBOARD (CFO CASHFLOW)
# ============================================================
def render_payment_powerbi_suite(df_pay, theme, is_light):
    if not PLOTLY_OK or df_pay is None or df_pay.empty:
        return
    try:
        st.markdown("### ⚡ Power BI Financial & Cashflow Aging Intelligence")
        amt_col = _find_col(df_pay, ["Amount", "Balance Payable Amount"])
        days_col = _find_col(df_pay, ["Days Pending"])
        bucket_col = _find_col(df_pay, ["Payment Group", "Department Bucket"])
        vendor_col = _find_col(df_pay, ["Vendor Name", "VendorName"])

        work = df_pay.copy()
        work["_amt"] = pd.to_numeric(work[amt_col], errors="coerce").fillna(0.0) if amt_col else 0.0
        work["_days"] = pd.to_numeric(work[days_col], errors="coerce").fillna(0.0) if days_col else 0.0
        pending_only = work[~work[bucket_col].astype(str).str.contains("Paid", case=False, na=False)] if bucket_col else work

        tot_amt = work["_amt"].sum()
        pen_amt = pending_only["_amt"].sum()
        crit_30 = pending_only[pending_only["_days"] > 30]
        avg_days = float(pending_only["_days"].mean()) if not pending_only.empty else 0.0

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total In-Scope Value", format_inr_short(tot_amt), f"{len(work):,} Bills")
        k2.metric("Pending Exposure (Unpaid)", format_inr_short(pen_amt), f"{len(pending_only):,} Open Bills")
        k3.metric("Critical >30 Days Stuck", format_inr_short(crit_30["_amt"].sum()), f"{len(crit_30):,} Bills", delta_color="inverse")
        k4.metric("Avg Desk Aging (Open)", f"{avg_days:.1f} Days")

        c1, c2 = st.columns(2)
        with c1:
            if bucket_col:
                bg = work.groupby(bucket_col).agg(Bills=("_amt", "size"), Value_INR=("_amt", "sum"), Avg_Days=("_days", "mean")).reset_index()
                bg = bg.sort_values("Value_INR", ascending=False)
                bg["Label"] = bg.apply(lambda r: f"{format_inr_short(r['Value_INR'])} ({int(r['Bills'])})", axis=1)
                fig_b = px.bar(
                    bg, x=bucket_col, y="Value_INR", text="Label", color="Avg_Days",
                    color_continuous_scale=[(0, "#10b981"), (0.5, "#f59e0b"), (1, "#ef4444")],
                )
                fig_b.update_traces(textposition="outside")
                _style_plotly(fig_b, theme, "₹ Exposure by Workflow Bucket (Color = Avg Days Stuck)", height=360)
                fig_b.update_layout(xaxis_title="", yaxis_title="Amount (₹)")
                st.plotly_chart(fig_b, use_container_width=True, key="bi_pay_bucket_val")

        with c2:
            if not pending_only.empty and days_col:
                labels = ["0–5d (Fresh)", "6–15d (Moderate)", "16–30d (Escalation)", ">30d (Critical)"]
                ag = pending_only.copy()
                ag["Aging_Tier"] = pd.cut(ag["_days"], bins=[-1e6, 5, 15, 30, 1e6], labels=labels).astype(str)
                ag_g = ag.groupby("Aging_Tier").agg(Bills=("_amt", "size"), Value_INR=("_amt", "sum")).reindex(labels, fill_value=0).reset_index()
                ag_g["Label"] = ag_g.apply(lambda r: f"{format_inr_short(r['Value_INR'])} ({int(r['Bills'])})", axis=1)
                fig_a = px.bar(
                    ag_g, x="Aging_Tier", y="Value_INR", text="Label", color="Aging_Tier",
                    color_discrete_sequence=["#10b981", "#fbbf24", "#f97316", "#dc2626"],
                )
                fig_a.update_traces(textposition="outside")
                _style_plotly(fig_a, theme, "Cashflow Aging Waterfall (Open Bills)", height=360)
                fig_a.update_layout(showlegend=False, xaxis_title="", yaxis_title="Pending Amount (₹)")
                st.plotly_chart(fig_a, use_container_width=True, key="bi_pay_aging")

        if vendor_col and not pending_only.empty:
            top_v = (
                pending_only.groupby(vendor_col)
                .agg(Bills=("_amt", "size"), Value_INR=("_amt", "sum"), Avg_Days=("_days", "mean"))
                .nlargest(10, "Value_INR")
                .sort_values("Value_INR", ascending=True)
                .reset_index()
            )
            if not top_v.empty and top_v["Value_INR"].sum() > 0:
                fig_tv = px.bar(
                    top_v, x="Value_INR", y=vendor_col, orientation="h",
                    text=top_v.apply(lambda r: f"{format_inr_short(r['Value_INR'])} · {int(r['Bills'])} bills", axis=1),
                    color="Avg_Days", color_continuous_scale=[(0, "#38bdf8"), (0.5, "#f59e0b"), (1, "#ef4444")],
                )
                fig_tv.update_traces(textposition="outside")
                _style_plotly(fig_tv, theme, "Top 10 Vendors by Open Payment Exposure (₹)", height=370)
                fig_tv.update_layout(xaxis_title="Pending Amount (₹)", yaxis_title="")
                st.plotly_chart(fig_tv, use_container_width=True, key="bi_pay_top_vendors")
    except Exception as exc:
        st.caption(f"Payment BI charts skipped for current slice: {exc}")


# ============================================================
# 6. POWER BI SUITE — CPK & UTILIZATION (LEAKAGE & PARETO)
# ============================================================
def render_cpk_powerbi_suite(df_master, view_type, df_updown, theme, is_light):
    if not PLOTLY_OK or df_master is None or df_master.empty:
        return
    try:
        st.markdown(f"### ⚡ Power BI Network Cost & Leakage Intelligence ({view_type})")
        w = df_master.copy()
        w["_cost"] = pd.to_numeric(w.get("Total Trip Cost", 0), errors="coerce").fillna(0.0)
        w["_wt"] = pd.to_numeric(w.get("Total Carried Wt", 0), errors="coerce").fillna(0.0)
        w["_cap"] = pd.to_numeric(w.get("Total Capacity", 0), errors="coerce").fillna(0.0)
        w["_util"] = pd.to_numeric(w.get("Overall Util %", 0), errors="coerce").fillna(0.0)
        w["_cpk"] = pd.to_numeric(w.get("Overall CPK", 0), errors="coerce").fillna(0.0)
        if w["_util"].max() > 1.5:
            w["_util"] = w["_util"] / 100.0

        w["_empty_ratio"] = np.clip(1.0 - w["_util"], 0.0, 1.0)
        w["_leakage_inr"] = w["_cost"] * w["_empty_ratio"]
        w["_sz"] = np.clip(w["_cost"], 1.0, None)

        total_spend = w["_cost"].sum()
        total_leak = w["_leakage_inr"].sum()
        below_60 = int((w["_util"] < 0.60).sum())
        high_cpk = int((w["_cpk"] > 5.0).sum())

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Network Spend", format_inr_short(total_spend))
        k2.metric("Dead-Weight Cost Leakage", format_inr_short(total_leak), f"{(total_leak / total_spend * 100) if total_spend else 0:.1f}% empty space", delta_color="inverse")
        k3.metric("Underutilized (<60%)", f"{below_60:,}", f"of {len(w):,} {view_type.lower()}s")
        k4.metric("High CPK Alerts (>₹5/kg)", f"{high_cpk:,}")

        entity_col = _find_col(w, ["Route Pair", "Route Path", "Vehicle No", "Vendor(s)", "Route"]) or w.columns[0]

        c1, c2 = st.columns(2)
        with c1:
            w["_util_pct"] = (w["_util"] * 100).round(1)
            w["_band"] = np.where(
                (w["_util_pct"] < 60) & (w["_cpk"] > 5), "🔴 Double Bleed (<60% & >₹5)",
                np.where(w["_util_pct"] < 60, "🟠 Underutilized (<60%)",
                         np.where(w["_cpk"] > 5, "🟡 High CPK (>₹5)", "🟢 Optimal Zone")),
            )
            fig_eff = px.scatter(
                w, x="_util_pct", y="_cpk", size="_sz", color="_band",
                hover_name=entity_col,
                hover_data={"_util_pct": True, "_cpk": ":.2f", "_cost": ":,.0f", "_leakage_inr": ":,.0f", "_sz": False},
                color_discrete_map={
                    "🔴 Double Bleed (<60% & >₹5)": "#dc2626", "🟠 Underutilized (<60%)": "#f97316",
                    "🟡 High CPK (>₹5)": "#eab308", "🟢 Optimal Zone": "#10b981",
                },
            )
            fig_eff.add_vline(x=60, line_dash="dash", line_color="#ef4444", annotation_text="60% Min Util")
            fig_eff.add_hline(y=5.0, line_dash="dash", line_color="#f59e0b", annotation_text="₹5 CPK Cap")
            _style_plotly(fig_eff, theme, "Efficiency Quadrant: Utilization % vs CPK", height=380)
            fig_eff.update_xaxes(title="Utilization %")
            fig_eff.update_yaxes(title="Overall CPK (₹/kg)")
            st.plotly_chart(fig_eff, use_container_width=True, key=f"bi_cpk_quad_{view_type}")

        with c2:
            pareto = w.groupby(entity_col).agg(Spend=("_cost", "sum"), Leakage=("_leakage_inr", "sum")).reset_index()
            pareto = pareto.sort_values("Spend", ascending=False).head(12)
            if not pareto.empty and total_spend > 0:
                pareto["Cum_Pct"] = (pareto["Spend"].cumsum() / total_spend * 100).round(1)
                fig_par = make_subplots(specs=[[{"secondary_y": True}]])
                fig_par.add_trace(go.Bar(x=pareto[entity_col], y=pareto["Spend"], name="Total Spend (₹)", marker_color=theme["blue"]), secondary_y=False)
                fig_par.add_trace(go.Bar(x=pareto[entity_col], y=pareto["Leakage"], name="Empty Leakage (₹)", marker_color="#ef4444", opacity=0.85), secondary_y=False)
                fig_par.add_trace(go.Scatter(x=pareto[entity_col], y=pareto["Cum_Pct"], name="Cumulative Spend %", mode="lines+markers", line=dict(color="#10b981", width=2.5)), secondary_y=True)
                _style_plotly(fig_par, theme, f"Pareto 80/20 Spend & Leakage — Top 12 {view_type}s", height=380)
                fig_par.update_layout(barmode="overlay")
                fig_par.update_yaxes(title_text="Amount (₹)", secondary_y=False)
                fig_par.update_yaxes(title_text="Cumulative %", range=[0, 108], secondary_y=True)
                st.plotly_chart(fig_par, use_container_width=True, key=f"bi_cpk_pareto_{view_type}")

        if view_type == "Route" and df_updown is not None and not df_updown.empty and "SortKey" in df_updown.columns:
            ud = df_updown.copy()
            ud["_u"] = pd.to_numeric(ud.get("Overall Util %", 0), errors="coerce").fillna(0.0)
            if ud["_u"].max() <= 1.5:
                ud["_u"] = ud["_u"] * 100.0
            ud["_c"] = pd.to_numeric(ud.get("Total Trip Cost", 0), errors="coerce").fillna(0.0)
            imb_rows = []
            for sk, grp in ud.groupby("SortKey"):
                if len(grp) >= 2:
                    gs = grp.sort_values("_u", ascending=False)
                    hi, lo = gs.iloc[0], gs.iloc[-1]
                    gap = float(hi["_u"] - lo["_u"])
                    if gap >= 20.0:
                        imb_rows.append({
                            "Route Pair": sk, "Strong Leg": hi.get("Route (UP/DOWN)", ""),
                            "Strong Util %": f"{hi['_u']:.1f}%", "Weak Backhaul Leg": lo.get("Route (UP/DOWN)", ""),
                            "Backhaul Util %": f"{lo['_u']:.1f}%", "Gap %": round(gap, 1),
                            "Backhaul Spend": format_inr_short(lo["_c"]),
                        })
            if imb_rows:
                with st.expander(f"⚖️ Backhaul Asymmetry Detector — {len(imb_rows)} Imbalanced Corridors (Gap >= 20%)", expanded=False):
                    imb_df = pd.DataFrame(imb_rows).sort_values("Gap %", ascending=False)
                    imb_df["Gap %"] = imb_df["Gap %"].map(lambda x: f"{x:.1f}%")
                    st.dataframe(imb_df, use_container_width=True, hide_index=True)
    except Exception as exc:
        st.caption(f"CPK BI charts skipped for current slice: {exc}")


# ============================================================
# 7. POWER BI SUITE — OVERALL ISSUES COMPOSITE RISK ENGINE
# ============================================================
def render_overall_risk_leaderboard(summary, theme, is_light):
    if not PLOTLY_OK or summary is None or summary.empty or "RO Name" not in summary.columns:
        return
    try:
        df_r = summary.copy()
        ops_late = (
            df_r.get("Ontime Dep, Late Arr", pd.Series("0%", index=df_r.index)).map(lambda v: _parse_pct(v) or 0.0)
            + df_r.get("Late Dep, Late Arr", pd.Series("0%", index=df_r.index)).map(lambda v: _parse_pct(v) or 0.0)
        )
        pay_fric = (
            df_r.get("Draft Bills", pd.Series("0%", index=df_r.index)).map(lambda v: _parse_pct(v) or 0.0)
            + df_r.get("Finance Hold", pd.Series("0%", index=df_r.index)).map(lambda v: _parse_pct(v) or 0.0)
            + df_r.get("Finance Pending", pd.Series("0%", index=df_r.index)).map(lambda v: _parse_pct(v) or 0.0)
        )
        under_u = df_r.get("Underutilized Routes", pd.Series("0%", index=df_r.index)).map(lambda v: _parse_pct(v) or 0.0)

        df_r["Ops Risk"] = ops_late.clip(0, 100)
        df_r["Payment Risk"] = pay_fric.clip(0, 100)
        df_r["Util Risk"] = under_u.clip(0, 100)
        df_r["Composite Risk Index"] = (0.40 * df_r["Ops Risk"] + 0.30 * df_r["Payment Risk"] + 0.30 * df_r["Util Risk"]).round(1)

        top_risk = df_r.nlargest(12, "Composite Risk Index").sort_values("Composite Risk Index", ascending=True)
        if top_risk.empty or top_risk["Composite Risk Index"].max() <= 0:
            return

        top3 = df_r.nlargest(3, "Composite Risk Index")
        esc_text = " · ".join(
            f"<b>{html_module.escape(str(r['RO Name']))}</b> ({r['Composite Risk Index']:.1f}/100)"
            for _, r in top3.iterrows()
        )
        _render_bi_callout(
            "AVP Escalation Radar — Top 3 Highest-Risk ROs (40% Ops + 30% Payment + 30% Util)",
            f"Immediate focus required on: {esc_text}",
            "#dc2626",
            theme,
        )

        fig_risk = px.bar(
            top_risk, x="Composite Risk Index", y="RO Name", orientation="h",
            text=top_risk["Composite Risk Index"].map(lambda x: f"{x:.1f}"),
            color="Composite Risk Index",
            color_continuous_scale=[(0, "#10b981"), (0.45, "#f59e0b"), (1, "#dc2626")],
            range_color=[0, 100],
            hover_data={"Ops Risk": ":.1f", "Payment Risk": ":.1f", "Util Risk": ":.1f"},
        )
        fig_risk.update_traces(textposition="outside")
        _style_plotly(fig_risk, theme, "RO Composite Risk Leaderboard (Higher = More Urgent)", height=360)
        fig_risk.update_layout(coloraxis_showscale=False, xaxis=dict(range=[0, 114], title="Composite Risk Score (0–100)"), yaxis=dict(title=""))
        st.plotly_chart(fig_risk, use_container_width=True, key="bi_overall_risk_board")
    except Exception as exc:
        st.caption(f"Risk leaderboard skipped: {exc}")
