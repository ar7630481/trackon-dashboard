import streamlit as st
import pandas as pd
import numpy as np
import datetime
import urllib.parse
import os
import warnings
import json
import gc
import hashlib
import hmac
import base64
import tempfile
import logging
import io
import re
import html as html_module
import textwrap
import inspect
import zipfile
import pickle
import xml.etree.ElementTree as ET

# Disable SettingWithCopyWarning for Pandas
warnings.filterwarnings('ignore')
pd.options.mode.chained_assignment = None

# ==========================================
# 1. PAGE SETUP (Trackon Executive Dashboard)
# ==========================================
st.set_page_config(
    page_title="Trackon Command Center",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Global Center + Middle Alignment for all Streamlit DataFrames & Data Editors
_COL_CFG_HAS_ALIGNMENT = False
try:
    _COL_CFG_HAS_ALIGNMENT = "alignment" in inspect.signature(st.column_config.Column).parameters
except Exception:
    _COL_CFG_HAS_ALIGNMENT = False

def _apply_center_col_config(data_obj, existing_cfg=None):
    if not _COL_CFG_HAS_ALIGNMENT:
        return existing_cfg
    cols = []
    try:
        if hasattr(data_obj, "data") and hasattr(data_obj.data, "columns"):
            cols = list(data_obj.data.columns)
        elif hasattr(data_obj, "columns"):
            cols = list(data_obj.columns)
    except Exception:
        return existing_cfg
    cfg = dict(existing_cfg) if isinstance(existing_cfg, dict) else {}
    for c in cols:
        c_str = str(c)
        if c_str == "Select 👁️":
            continue
        if c in cfg and isinstance(cfg[c], dict):
            item = dict(cfg[c])
            item.setdefault("alignment", "center")
            cfg[c] = item
        elif c not in cfg:
            cfg[c] = st.column_config.Column(alignment="center")
    return cfg

if not getattr(st, "_trackon_center_wrapped", False):
    _orig_st_dataframe = st.dataframe
    _orig_st_data_editor = st.data_editor

    def _centered_st_dataframe(data=None, *args, **kwargs):
        if _COL_CFG_HAS_ALIGNMENT and data is not None:
            orig_cc = kwargs.get("column_config")
            try:
                kwargs["column_config"] = _apply_center_col_config(data, orig_cc)
                return _orig_st_dataframe(data, *args, **kwargs)
            except TypeError:
                if orig_cc is None:
                    kwargs.pop("column_config", None)
                else:
                    kwargs["column_config"] = orig_cc
        return _orig_st_dataframe(data, *args, **kwargs)

    def _centered_st_data_editor(data, *args, **kwargs):
        if _COL_CFG_HAS_ALIGNMENT and data is not None:
            orig_cc = kwargs.get("column_config")
            try:
                kwargs["column_config"] = _apply_center_col_config(data, orig_cc)
                return _orig_st_data_editor(data, *args, **kwargs)
            except TypeError:
                if orig_cc is None:
                    kwargs.pop("column_config", None)
                else:
                    kwargs["column_config"] = orig_cc
        return _orig_st_data_editor(data, *args, **kwargs)

    st.dataframe = _centered_st_dataframe
    st.data_editor = _centered_st_data_editor
    st._trackon_center_wrapped = True


THEME_OPTIONS = {
    "🌌 Aurora Night": {
        "navy950": "#07111f", "navy900": "#0b1728", "navy800": "#10233a",
        "glow1": "rgba(37, 99, 235, .18)", "glow2": "rgba(20, 184, 166, .13)",
        "accent": "#55d6d2", "blue": "#60a5fa", "card1": "#182d46", "card2": "#0c1c2f",
        "sidebar1": "#0c1a2c", "sidebar2": "#081321", "line": "rgba(148, 163, 184, .20)",
        "text": "#e8f0fb", "muted": "#9fb1c8", "button1": "#1e4069", "button2": "#123348"
    },
    "🌊 Ocean Glass": {
        "navy950": "#061521", "navy900": "#082333", "navy800": "#0c3444",
        "glow1": "rgba(14, 165, 233, .20)", "glow2": "rgba(45, 212, 191, .14)",
        "accent": "#67e8f9", "blue": "#38bdf8", "card1": "#12384a", "card2": "#0b2536",
        "sidebar1": "#0a2635", "sidebar2": "#061923", "line": "rgba(103, 232, 249, .20)",
        "text": "#e8fbff", "muted": "#a4c9d5", "button1": "#155e75", "button2": "#164e63"
    },
    "🌿 Emerald Executive": {
        "navy950": "#081711", "navy900": "#0d2118", "navy800": "#143226",
        "glow1": "rgba(34, 197, 94, .16)", "glow2": "rgba(20, 184, 166, .12)",
        "accent": "#86efac", "blue": "#6ee7b7", "card1": "#1a3a2a", "card2": "#10271d",
        "sidebar1": "#10261a", "sidebar2": "#09170f", "line": "rgba(134, 239, 172, .19)",
        "text": "#effcf3", "muted": "#b1cdb9", "button1": "#166534", "button2": "#14532d"
    },
    "🤍 Bright Executive": {
        "navy950": "#f4f7fb", "navy900": "#ffffff", "navy800": "#eaf1f8",
        "glow1": "rgba(59, 130, 246, .10)", "glow2": "rgba(20, 184, 166, .08)",
        "accent": "#087e8b", "blue": "#2563eb", "card1": "#ffffff", "card2": "#f1f6fc",
        "sidebar1": "#edf4fb", "sidebar2": "#e5eef8", "line": "rgba(51, 65, 85, .18)",
        "text": "#172033", "muted": "#526176", "button1": "#dceafe", "button2": "#d8f3ee"
    },
    "📊 Power BI Pro": {
        "navy950": "#f3f6fb", "navy900": "#ffffff", "navy800": "#edf2f8",
        "glow1": "rgba(17, 141, 255, .11)", "glow2": "rgba(242, 200, 17, .12)",
        "accent": "#8a6d00", "blue": "#0f6cbd", "card1": "#ffffff", "card2": "#edf2f8",
        "sidebar1": "#ffffff", "sidebar2": "#f6f8fc", "line": "rgba(23, 43, 77, .14)",
        "text": "#172b4d", "muted": "#5f6f86", "button1": "#e8f0fb", "button2": "#dce9f8"
    },
    "🧊 Arctic Blue": {
        "navy950": "#eef6fb", "navy900": "#ffffff", "navy800": "#e4f0f7",
        "glow1": "rgba(14, 165, 233, .12)", "glow2": "rgba(6, 182, 212, .08)",
        "accent": "#0e7490", "blue": "#0369a1", "card1": "#ffffff", "card2": "#e4f0f7",
        "sidebar1": "#f9fcff", "sidebar2": "#edf5fa", "line": "rgba(18, 48, 71, .15)",
        "text": "#123047", "muted": "#536d80", "button1": "#dceef8", "button2": "#d8eafa"
    },
    "🌅 Sandstone Luxe": {
        "navy950": "#f7f3ed", "navy900": "#fffdf9", "navy800": "#f1e9dd",
        "glow1": "rgba(217, 119, 6, .10)", "glow2": "rgba(180, 83, 9, .07)",
        "accent": "#9a5b13", "blue": "#8b4513", "card1": "#fffdf9", "card2": "#f1e9dd",
        "sidebar1": "#fffdf9", "sidebar2": "#f7f1e8", "line": "rgba(48, 40, 31, .15)",
        "text": "#30281f", "muted": "#6e6255", "button1": "#f3e7d5", "button2": "#eee0cb"
    },
    "🌑 Midnight Graphite": {
        "navy950": "#101319", "navy900": "#191e27", "navy800": "#222a35",
        "glow1": "rgba(59, 130, 246, .14)", "glow2": "rgba(251, 191, 36, .09)",
        "accent": "#fbbf24", "blue": "#60a5fa", "card1": "#191e27", "card2": "#222a35",
        "sidebar1": "#171b22", "sidebar2": "#101319", "line": "rgba(203, 213, 225, .17)",
        "text": "#f4f6fa", "muted": "#a7b0bf", "button1": "#303a49", "button2": "#263342"
    },
    "🟣 Amethyst Studio": {
        "navy950": "#120f1d", "navy900": "#1b1730", "navy800": "#28213e",
        "glow1": "rgba(139, 92, 246, .18)", "glow2": "rgba(217, 70, 239, .10)",
        "accent": "#c4b5fd", "blue": "#a78bfa", "card1": "#1b1730", "card2": "#28213e",
        "sidebar1": "#191429", "sidebar2": "#100d19", "line": "rgba(196, 181, 253, .19)",
        "text": "#f5f1ff", "muted": "#b8aecf", "button1": "#47336f", "button2": "#342650"
    },
    "🍷 Burgundy Executive": {
        "navy950": "#1a0f16", "navy900": "#26151f", "navy800": "#36202d",
        "glow1": "rgba(244, 63, 94, .15)", "glow2": "rgba(192, 38, 101, .10)",
        "accent": "#fda4af", "blue": "#fb7185", "card1": "#26151f", "card2": "#36202d",
        "sidebar1": "#21111b", "sidebar2": "#160b12", "line": "rgba(253, 164, 175, .19)",
        "text": "#fff1f3", "muted": "#d3adb8", "button1": "#623143", "button2": "#472332"
    }
}
_theme_names = list(THEME_OPTIONS)
_default_theme = _theme_names.index("📊 Power BI Pro")
selected_theme_name = st.sidebar.selectbox(
    "🎨 Dashboard theme", _theme_names, index=_default_theme, key="app_visual_theme"
)
selected_theme = THEME_OPTIONS[selected_theme_name]
THEME_LIGHT_NAMES = {"🤍 Bright Executive", "📊 Power BI Pro", "🧊 Arctic Blue", "🌅 Sandstone Luxe"}
THEME_IS_LIGHT = selected_theme_name in THEME_LIGHT_NAMES
theme_primary_text = "#ffffff" if THEME_IS_LIGHT else selected_theme["navy950"]
if THEME_IS_LIGHT:
    THEME_STATUS_PALETTE = {
        'green': ('#dcfce7', '#166534'), 'red': ('#fee2e2', '#991b1b'),
        'soft_red': ('#fff1f2', '#9f1239'), 'yellow': ('#fef3c7', '#92400e'),
        'purple': ('#f3e8ff', '#6b21a8'), 'muted': ('#f1f5f9', selected_theme['muted'])
    }
else:
    THEME_STATUS_PALETTE = {
        'green': ('rgba(34,197,94,.16)', '#86efac'), 'red': ('rgba(248,113,113,.20)', '#fecaca'),
        'soft_red': ('rgba(244,63,94,.16)', '#fda4af'), 'yellow': ('rgba(234,179,8,.17)', '#fde68a'),
        'purple': ('rgba(168,85,247,.18)', '#e9d5ff'), 'muted': ('rgba(148,163,184,.10)', selected_theme['muted'])
    }

# Custom CSS adapts to the selected theme.
theme_css = """
    <style>
    :root {
        --navy-950: __NAVY950__;
        --navy-900: __NAVY900__;
        --navy-800: __NAVY800__;
        --line: __LINE__;
        --cyan: __ACCENT__;
        --blue: __BLUE__;
        --text: __TEXT__;
        --muted: __MUTED__;
        --card-1: __CARD1__;
        --card-2: __CARD2__;
        --sidebar-1: __SIDEBAR1__;
        --sidebar-2: __SIDEBAR2__;
        --button-1: __BUTTON1__;
        --button-2: __BUTTON2__;
    }
    .stApp {
        background:
            radial-gradient(ellipse at 8% 0%, __GLOW1__, transparent 34%),
            radial-gradient(ellipse at 92% 8%, __GLOW2__, transparent 30%),
            linear-gradient(145deg, var(--navy-950) 0%, var(--navy-900) 52%, var(--navy-800) 100%);
        color: var(--text);
    }
    [data-testid="stHeader"] { background: rgba(7, 17, 31, .78); }
    [data-testid="stAppViewContainer"] { background: transparent; }
    [data-testid="stMainBlockContainer"], .block-container {
        padding-top: 2.1rem;
        padding-bottom: 3rem;
        max-width: 1600px;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--sidebar-1) 0%, var(--sidebar-2) 100%);
        border-right: 1px solid var(--line);
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #c1d0e2; }
    h1, h2, h3, h4 {
        color: #f5f9ff !important;
        letter-spacing: -.025em;
        font-weight: 740 !important;
    }
    h1 { font-size: clamp(2rem, 3vw, 2.8rem) !important; }
    h2 { margin-top: .4rem !important; }
    p, label, [data-testid="stCaptionContainer"] { color: #c2d1e3; }
    [data-testid="metric-container"] {
        background: linear-gradient(145deg, color-mix(in srgb, var(--card-1) 92%, transparent), color-mix(in srgb, var(--card-2) 94%, transparent));
        border: 1px solid color-mix(in srgb, var(--blue) 28%, transparent);
        border-radius: 16px;
        padding: 1.1rem 1.2rem;
        box-shadow: 0 14px 36px rgba(0, 0, 0, .20);
        transition: transform .18s ease, border-color .18s ease;
    }
    [data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        border-color: color-mix(in srgb, var(--cyan) 56%, transparent);
    }
    [data-testid="stMetricLabel"] { color: #aabbd0 !important; }
    [data-testid="stMetricValue"] { color: #f4f8ff !important; }
    [data-testid="stDataFrame"], [data-testid="stDataEditor"] {
        border: 1px solid var(--line);
        border-radius: 14px;
        overflow: hidden;
        background: rgba(12, 26, 43, .72);
    }
    th { background-color: #153657 !important; color: #f7fbff !important; font-weight: 650 !important; }
    .stButton > button, .stDownloadButton > button {
        border: 1px solid color-mix(in srgb, var(--blue) 44%, transparent);
        border-radius: 10px;
        font-weight: 650;
        color: #edf6ff;
        background: linear-gradient(120deg, var(--button-1), var(--button-2));
        transition: transform .16s ease, box-shadow .16s ease, border-color .16s ease;
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        transform: translateY(-1px);
        border-color: color-mix(in srgb, var(--cyan) 78%, transparent);
        box-shadow: 0 8px 22px rgba(0, 0, 0, .22);
        color: white;
    }
    [data-baseweb="tab"] { color: #aebfd2; }
    [aria-selected="true"][data-baseweb="tab"] { color: #78e0da !important; }
    [data-testid="stAlert"] { border-radius: 12px; }
    [data-baseweb="select"] > div, [data-baseweb="input"] > div, [data-baseweb="textarea"] > div {
        background: color-mix(in srgb, var(--navy-800) 84%, transparent);
        border-color: var(--line);
        border-radius: 10px;
    }
    [data-testid="stRadio"] label, [data-testid="stSegmentedControl"] button { border-radius: 9px; }
    [data-testid="stRadio"] label:hover, [data-testid="stSegmentedControl"] button:hover { color: var(--cyan); }
    [data-testid="stSidebar"] [data-testid="stSelectbox"] label { color: var(--cyan) !important; font-weight: 700; }
    hr { border-color: rgba(148, 163, 184, .16); }
    .app-topline {
        display: flex; justify-content: space-between; align-items: center; gap: 1rem;
        margin: .25rem 0 1.2rem; padding: .95rem 1.15rem;
        border: 1px solid var(--line); border-radius: 16px;
        background: linear-gradient(110deg, var(--card-1), var(--card-2));
        box-shadow: 0 8px 24px rgba(15, 23, 42, .045);
    }
    .app-eyebrow, .section-kicker { color: var(--cyan); font-size: .72rem; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }
    .app-brandline { color: var(--text); font-size: 1.05rem; font-weight: 750; margin-top: .12rem; }
    .app-subline { color: var(--muted); font-size: .82rem; font-weight: 500; margin-left: .45rem; }
    .app-chip { border: 1px solid var(--line); border-radius: 999px; padding: .42rem .72rem; color: var(--muted); font-size: .76rem; font-weight: 650; white-space: nowrap; }
    .ops-overview-line { display:flex; justify-content:space-between; align-items:end; gap:1rem; margin:.15rem 0 .7rem; }
    .ops-overview-line h3 { margin:.2rem 0 0 !important; }
    .ops-data-chip { border:1px solid var(--line); border-radius:999px; padding:.45rem .8rem; color:var(--muted); font-size:.82rem; font-weight:650; white-space:nowrap; }
    .gauge-grid { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:12px; margin:.6rem 0 1.1rem; }
    .gauge-card { min-width:0; text-align:center; background:linear-gradient(145deg,var(--card-1),var(--card-2)); border:1px solid var(--line); border-radius:15px; padding:1rem .55rem .8rem; box-shadow:0 8px 22px rgba(15,23,42,.05); }
    .gauge-label { min-height:2.35rem; color:var(--text); font-size:.82rem; font-weight:700; display:flex; justify-content:center; align-items:center; }
    .gauge-card svg { display:block; width:min(100%,170px); height:auto; margin:.2rem auto -.15rem; overflow:visible; }
    .gauge-caption { color:var(--muted); font-size:.72rem; font-weight:550; }
    .outcome-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(185px,1fr)); gap:10px; margin:.5rem 0 1rem; }
    .outcome-card { border:1px solid #e2e8f0; border-radius:13px; padding:.72rem .85rem; background:#fff; box-shadow:0 5px 16px rgba(15,23,42,.045); }
    .outcome-label { font-size:.76rem; font-weight:700; line-height:1.25; min-height:2.1em; }
    .outcome-value { font-size:1.25rem; font-weight:800; margin:.25rem 0 .1rem; }
    .outcome-share { font-size:.72rem; opacity:.82; }
    .outcome-green { background:#f0fdf4; border-color:#bbf7d0; color:#166534; }
    .outcome-soft-red { background:#fff1f2; border-color:#fecdd3; color:#9f1239; }
    .outcome-red { background:#fef2f2; border-color:#fecaca; color:#991b1b; }
    .outcome-yellow { background:#fffbeb; border-color:#fde68a; color:#92400e; }
    .outcome-purple { background:#faf5ff; border-color:#e9d5ff; color:#6b21a8; }
    .outcome-muted { background:#f8fafc; border-color:#e2e8f0; color:#475569; }
    [data-testid="stDataEditor"], [data-testid="stDataFrame"] {
        --gdg-bg-cell: #ffffff;
        --gdg-bg-cell-medium: #f8fafc;
        --gdg-bg-cell-medium-hover: #f1f5f9;
        --gdg-bg-cell-light: #ffffff;
        --gdg-bg-header: #eef3f9;
        --gdg-bg-header-hovered: #e4edf8;
        --gdg-bg-header-has-focus: #dbeafe;
        --gdg-bg-header-has-focus-hovered: #dbeafe;
        --gdg-text-dark: #1e293b;
        --gdg-text-medium: #334155;
        --gdg-text-light: #64748b;
        --gdg-text-header: #172033;
        --gdg-text-group-header: #334155;
        --gdg-border-color: #e2e8f0;
        --gdg-horizontal-border-color: #e2e8f0;
        --gdg-accent-color: #2563eb;
        --gdg-link-color: #0f766e;
        --gdg-font-family: Inter, ui-sans-serif, system-ui, sans-serif;
    }
    @media (max-width: 1100px) { .gauge-grid { grid-template-columns:repeat(3,minmax(0,1fr)); } }
    @media (max-width: 700px) {
        .gauge-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
        .app-topline, .ops-overview-line { align-items:flex-start; flex-direction:column; }
    }
    @media (max-width: 420px) { .gauge-grid { grid-template-columns:1fr; } }
    </style>
"""
for theme_key, theme_value in selected_theme.items():
    theme_css = theme_css.replace(f"__{theme_key.upper()}__", theme_value)
st.markdown(theme_css, unsafe_allow_html=True)
if selected_theme_name == "🤍 Bright Executive":
    st.markdown("""
    <style>
    html, body, [class*="css"] { font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    :root { color-scheme:light; --primary-color:#2563eb !important; --background-color:#f4f7fb !important; --secondary-background-color:#ffffff !important; --text-color:#172033 !important; }
    .stApp {
        background:
          radial-gradient(ellipse at 7% 0%, rgba(59,130,246,.08), transparent 34%),
          radial-gradient(ellipse at 94% 8%, rgba(20,184,166,.06), transparent 31%),
          linear-gradient(145deg, #f4f7fb 0%, #ffffff 56%, #edf3f9 100%);
        color: #172033;
    }
    [data-testid="stHeader"] { background: transparent !important; }
    [data-testid="stMainBlockContainer"], .block-container { max-width:1560px; padding-top:1.15rem; padding-bottom:3rem; }
    [data-testid="stSidebar"] { background:linear-gradient(180deg,#fff 0%,#f5f8fc 100%); border-right:1px solid rgba(51,65,85,.14); }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] h4 { font-size:1rem !important; letter-spacing:-.01em; }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"], [data-testid="stSidebar"] p, [data-testid="stSidebar"] label,
    p, label, [data-testid="stCaptionContainer"], [data-testid="stMarkdownContainer"] { color:#334155; }
    [data-testid="stCaptionContainer"] { color:#64748b !important; }
    h1, h2, h3, h4 { color:#172033 !important; letter-spacing:-.03em; font-weight:720 !important; }
    h1 { font-size:clamp(2rem,3vw,2.65rem) !important; }
    h2 { font-size:clamp(1.4rem,2vw,1.85rem) !important; }
    [data-testid="metric-container"] {
        background:linear-gradient(145deg,#fff,#f7faff); border:1px solid rgba(51,65,85,.13);
        border-radius:16px; padding:1rem 1.15rem; box-shadow:0 8px 24px rgba(15,23,42,.055);
        transition:transform .18s ease, box-shadow .18s ease, border-color .18s ease;
    }
    [data-testid="metric-container"]:hover { transform:translateY(-2px); border-color:rgba(37,99,235,.35); box-shadow:0 12px 28px rgba(15,23,42,.09); }
    [data-testid="stMetricLabel"] { color:#64748b !important; font-weight:600; }
    [data-testid="stMetricValue"] { color:#172033 !important; font-weight:750; }
    [data-testid="stDataFrame"], [data-testid="stDataEditor"], [data-testid="stTable"] {
        background:#fff !important; border:1px solid rgba(51,65,85,.14); border-radius:14px; overflow:hidden;
    }
    th { background-color:#edf3f9 !important; color:#172033 !important; font-weight:650 !important; }
    .stButton > button, .stDownloadButton > button {
        border:1px solid rgba(37,99,235,.22); border-radius:10px; min-height:2.55rem; font-weight:650;
        color:#17314f !important; background:linear-gradient(120deg,#e3edfb,#e0f3f0);
        transition:transform .16s ease, box-shadow .16s ease, border-color .16s ease;
    }
    .stApp button[data-testid="stBaseButton-secondary"], .stApp button[data-testid="stBaseButton-secondary"]:hover {
        background:linear-gradient(120deg,#e8f0fd,#e5f5f1) !important; color:#17314f !important;
        border:1px solid rgba(37,99,235,.22) !important; box-shadow:none;
    }
    .stApp button[data-testid="stBaseButton-secondary"]:disabled {
        background:#f1f5f9 !important; color:#64748b !important; border:1px solid #dce4ed !important; opacity:1 !important;
    }
    .stButton > button:hover, .stDownloadButton > button:hover { transform:translateY(-1px); border-color:#087e8b; box-shadow:0 8px 20px rgba(15,23,42,.1); color:#0f253e !important; }
    button[data-testid="stBaseButton-primary"] { color:#fff !important; background:linear-gradient(120deg,#2563eb,#087e8b) !important; border:0 !important; }
    [role="tablist"] { gap:.35rem; border-bottom:1px solid rgba(51,65,85,.14); }
    [data-baseweb="tab"] { color:#64748b; font-weight:600; }
    [aria-selected="true"][data-baseweb="tab"] { color:#2563eb !important; }
    [data-testid="stAlert"] { border-radius:12px; }
    [data-baseweb="select"] > div, [data-baseweb="input"] > div, [data-baseweb="textarea"] > div {
        background:#fff !important; color:#172033 !important; border-color:rgba(51,65,85,.18); border-radius:10px;
    }
    [data-baseweb="select"] > div > div, [data-baseweb="select"] [role="combobox"],
    [data-baseweb="input"] input, [data-baseweb="textarea"] textarea,
    input, textarea { background:#fff !important; color:#172033 !important; }
    [data-testid="stDateInput"] [data-baseweb="input"],
    [data-testid="stDateInput"] [data-baseweb="input"] *,
    [data-testid="stDateInput"] input, [data-testid="stDateInput"] button,
    [data-testid="stDateInput"] [role="button"] {
        background-color:#fff !important; color:#172033 !important; border-color:#cbd5e1 !important;
    }
    [data-testid="stDateInput"] svg { fill:#64748b !important; color:#64748b !important; }
    [data-baseweb="select"] svg { fill:#64748b !important; }
    .stApp [data-baseweb="select"] > div, .stApp [data-baseweb="select"] > div > div,
    .stApp [data-baseweb="select"] [role="combobox"] { background-color:#fff !important; color:#172033 !important; }
    .stApp [data-baseweb="select"], .stApp [data-baseweb="select"] * { background-color:#fff !important; color:#172033 !important; }
    .stApp [data-baseweb="select"] [data-testid="stMarkdownContainer"], .stApp [data-baseweb="select"] span { color:#172033 !important; }
    .stApp [data-testid*="DateInput"] [data-baseweb="input"],
    .stApp [data-testid*="DateInput"] [data-baseweb="input"] *,
    .stApp [data-testid*="DateInput"] input, .stApp [data-testid*="DateInput"] button {
        background:#fff !important; color:#172033 !important; border-color:#cbd5e1 !important;
    }
    .stApp [data-testid^="stBaseButton-"] { font-weight:650 !important; border-radius:10px !important; }
    .stApp button[data-testid="stBaseButton-secondary"] { background:#e8f0fd !important; color:#17314f !important; border:1px solid #cbdcf2 !important; }
    .stApp button[data-testid="stBaseButton-secondary"]:disabled { background:#f1f5f9 !important; color:#64748b !important; }
    [data-baseweb="popover"] [role="listbox"] { background:#fff; color:#172033; }
    [data-testid="stRadio"] label, [data-testid="stSegmentedControl"] button { border-radius:9px; }
    [data-testid="stSidebar"] [data-testid="stRadio"] label { padding:.48rem .6rem; margin:.08rem 0; font-size:.88rem; border-radius:9px; }
    [data-testid="stSidebar"] [data-testid="stRadio"] [data-baseweb="radio"] { display:none !important; }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked),
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has([aria-checked="true"]) { background:#eaf2ff; color:#1d4ed8 !important; font-weight:700; }
    [data-testid="stSidebar"] [data-testid="stSelectbox"] label { color:#087e8b !important; font-weight:700; }
    hr { border-color:rgba(51,65,85,.14); }
    .app-topline {
        display:flex; justify-content:space-between; align-items:center; gap:1rem; margin:.25rem 0 1.2rem;
        padding:.95rem 1.15rem; border:1px solid rgba(51,65,85,.13); border-radius:16px;
        background:linear-gradient(110deg,#fff,#f5f8fc); box-shadow:0 8px 24px rgba(15,23,42,.045);
    }
    .app-eyebrow { color:#087e8b; font-size:.68rem; font-weight:800; letter-spacing:.13em; text-transform:uppercase; }
    .app-brandline { color:#172033; font-size:1.05rem; font-weight:750; letter-spacing:-.02em; margin-top:.12rem; }
    .app-subline { color:#64748b; font-size:.82rem; font-weight:500; margin-left:.45rem; }
    .app-chip { border:1px solid rgba(51,65,85,.14); border-radius:999px; padding:.42rem .72rem; color:#526176; font-size:.76rem; font-weight:650; white-space:nowrap; }
    .section-kicker { color:#087e8b; font-size:.72rem; font-weight:800; letter-spacing:.11em; text-transform:uppercase; margin:.2rem 0 -.35rem; }
    .gauge-card { background:linear-gradient(145deg,#fff,#f7faff); border-color:rgba(51,65,85,.13); box-shadow:0 8px 24px rgba(15,23,42,.055); }
    .gauge-label { color:#172033; }
    .gauge-caption, .ops-data-chip { color:#64748b; }
    @media (max-width:700px) { .block-container { padding:.75rem .8rem 2rem; } .app-topline { align-items:flex-start; flex-direction:column; } }
    </style>
    """, unsafe_allow_html=True)


theme_mode = "light" if THEME_IS_LIGHT else "dark"
theme_control_bg = "#ffffff" if THEME_IS_LIGHT else selected_theme["navy900"]
theme_nav_active_text = selected_theme["blue"] if THEME_IS_LIGHT else selected_theme["accent"]
theme_override_css = f"""
<style>
:root {{
    color-scheme:{theme_mode};
    --theme-bg:{selected_theme['navy950']}; --theme-surface:{selected_theme['navy900']};
    --theme-surface-alt:{selected_theme['navy800']}; --theme-text:{selected_theme['text']};
    --theme-muted:{selected_theme['muted']}; --theme-accent:{selected_theme['accent']};
    --theme-blue:{selected_theme['blue']}; --theme-line:{selected_theme['line']};
    --theme-sidebar:{selected_theme['sidebar1']}; --theme-sidebar-alt:{selected_theme['sidebar2']};
    --theme-control-bg:{theme_control_bg}; --theme-control-text:{selected_theme['text']};
    --theme-nav-active-text:{theme_nav_active_text};
    --gdg-bg-cell:{selected_theme['card1']}; --gdg-bg-cell-medium:{selected_theme['card2']};
    --gdg-bg-cell-medium-hover:{selected_theme['card2']}; --gdg-bg-cell-light:{selected_theme['card1']};
    --gdg-bg-header:{selected_theme['card2']}; --gdg-bg-header-hovered:{selected_theme['card2']};
    --gdg-bg-header-has-focus:{selected_theme['card2']}; --gdg-bg-header-has-focus-hovered:{selected_theme['card2']};
    --gdg-text-dark:{selected_theme['text']}; --gdg-text-medium:{selected_theme['text']};
    --gdg-text-light:{selected_theme['muted']}; --gdg-text-header:{selected_theme['text']};
    --gdg-text-group-header:{selected_theme['text']}; --gdg-border-color:{selected_theme['line']};
    --gdg-horizontal-border-color:{selected_theme['line']}; --gdg-accent-color:{selected_theme['blue']};
    --gdg-link-color:{selected_theme['accent']};
}}
.stApp {{ color:var(--theme-text) !important; background:linear-gradient(145deg,var(--theme-bg),var(--theme-surface),var(--theme-surface-alt)) !important; }}
[data-testid="stHeader"] {{ background:transparent !important; }}
.stApp h1,.stApp h2,.stApp h3,.stApp h4 {{ color:var(--theme-text) !important; }}
.stApp p,.stApp label,.stApp [data-testid="stCaptionContainer"],.stApp [data-testid="stMarkdownContainer"] {{ color:var(--theme-text) !important; }}
.stApp [data-testid="stCaptionContainer"] {{ color:var(--theme-muted) !important; }}
[data-testid="stSidebar"] {{ background:linear-gradient(180deg,var(--theme-sidebar),var(--theme-sidebar-alt)) !important; }}
[data-testid="stSidebar"] p,[data-testid="stSidebar"] label,[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {{ color:var(--theme-text) !important; }}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{ color:var(--theme-muted) !important; }}
[data-testid="stMetricLabel"] {{ color:var(--theme-muted) !important; }}
[data-testid="stMetricValue"] {{ color:var(--theme-text) !important; }}
[data-testid="stTable"] {{ background:{selected_theme['card1']} !important; color:{selected_theme['text']} !important; }}
[data-testid="stTable"] th {{ background:{selected_theme['card2']} !important; color:{selected_theme['text']} !important; border-color:var(--theme-line) !important; text-align:center !important; vertical-align:middle !important; }}
[data-testid="stTable"] td {{ background:{selected_theme['card1']} !important; color:{selected_theme['text']} !important; border-color:var(--theme-line) !important; text-align:center !important; vertical-align:middle !important; }}
[data-testid="stDataFrame"],[data-testid="stDataEditor"] {{
    --gdg-bg-cell:{selected_theme['card1']} !important; --gdg-bg-cell-medium:{selected_theme['card2']} !important;
    --gdg-bg-cell-medium-hover:{selected_theme['card2']} !important; --gdg-bg-cell-light:{selected_theme['card1']} !important;
    --gdg-bg-header:{selected_theme['card2']} !important; --gdg-bg-header-hovered:{selected_theme['card2']} !important;
    --gdg-bg-header-has-focus:{selected_theme['card2']} !important; --gdg-bg-header-has-focus-hovered:{selected_theme['card2']} !important;
    --gdg-text-dark:{selected_theme['text']} !important; --gdg-text-medium:{selected_theme['text']} !important;
    --gdg-text-light:{selected_theme['muted']} !important; --gdg-text-header:{selected_theme['text']} !important;
    --gdg-text-group-header:{selected_theme['text']} !important; --gdg-border-color:{selected_theme['line']} !important;
    --gdg-horizontal-border-color:{selected_theme['line']} !important; --gdg-accent-color:{selected_theme['blue']} !important;
}}
[data-baseweb="select"] > div,[data-baseweb="input"] > div,[data-baseweb="textarea"] > div,
[data-testid="stDateInput"] input,[data-testid="stDateInput"] button {{
    background:var(--theme-control-bg) !important; color:var(--theme-control-text) !important; border-color:var(--theme-line) !important;
}}
.stApp [data-baseweb="select"] *,[data-baseweb="popover"],[data-baseweb="popover"] [role="listbox"],
[data-baseweb="popover"] [role="option"] {{ background-color:var(--theme-control-bg) !important; color:var(--theme-control-text) !important; }}
.stApp input,.stApp textarea {{ background:var(--theme-control-bg) !important; color:var(--theme-control-text) !important; }}
[data-testid="stSidebar"] [data-testid="stRadio"] label {{ color:var(--theme-text) !important; }}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked),
[data-testid="stSidebar"] [data-testid="stRadio"] label:has([aria-checked="true"]) {{
    background:color-mix(in srgb,var(--theme-accent) 16%,var(--theme-sidebar)) !important;
    color:var(--theme-nav-active-text) !important; border:1px solid var(--theme-line); font-weight:750;
}}
[data-testid="stSidebar"] [data-testid="stSelectbox"] label {{ color:var(--theme-accent) !important; }}
.stApp button[data-testid="stBaseButton-secondary"],.stApp button[data-testid="stBaseButton-secondary"]:hover {{
    background:linear-gradient(120deg,{selected_theme['button1']},{selected_theme['button2']}) !important;
    color:var(--theme-text) !important; border-color:var(--theme-line) !important;
}}
.stApp button[data-testid="stBaseButton-primary"] {{ background:var(--theme-blue) !important; color:{theme_primary_text} !important; border-color:var(--theme-blue) !important; }}
[data-baseweb="tab"] {{ color:var(--theme-muted) !important; }}
[data-baseweb="tab"][aria-selected="true"] {{ color:var(--theme-blue) !important; }}
hr {{ border-color:var(--theme-line) !important; }}
.app-topline {{ background:linear-gradient(110deg,{selected_theme['card1']},{selected_theme['card2']}) !important; border-color:var(--theme-line) !important; }}
.app-brandline,.app-chip {{ color:var(--theme-text) !important; }}
.app-subline,.gauge-caption,.ops-data-chip {{ color:var(--theme-muted) !important; }}
.app-eyebrow,.section-kicker {{ color:var(--theme-accent) !important; }}
.theme-preview {{ display:flex; align-items:center; gap:.38rem; margin:-.15rem 0 .7rem; color:var(--theme-muted); font-size:.73rem; font-weight:650; }}
.theme-swatch {{ width:.68rem; height:.68rem; border-radius:50%; border:1px solid var(--theme-line); }}
/* Power BI Sticky Unified Filter Strip & Active Filter Chips */
[data-testid="stVerticalBlock"]:has(> .element-container .pbi-sticky-anchor) {{
    position: sticky;
    top: 3.2rem;
    z-index: 95;
    background: color-mix(in srgb, var(--theme-surface) 94%, transparent);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border: 1px solid var(--theme-line);
    border-radius: 14px;
    padding: .75rem .9rem .55rem;
    margin: 0 0 1rem;
    box-shadow: 0 10px 26px rgba(15, 23, 42, .12);
}}
.pbi-chip-bar {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: .4rem;
    margin: .35rem 0 .15rem;
}}
.pbi-chip-title {{
    color: var(--theme-muted);
    font-size: .72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .06em;
    margin-right: .2rem;
}}
.pbi-chip {{
    display: inline-flex;
    align-items: center;
    gap: .3rem;
    padding: .22rem .62rem;
    border-radius: 999px;
    font-size: .74rem;
    font-weight: 650;
    border: 1px solid color-mix(in srgb, var(--theme-blue) 40%, var(--theme-line));
    background: color-mix(in srgb, var(--theme-blue) 14%, var(--theme-surface));
    color: var(--theme-text);
}}
.pbi-chip-muted {{
    opacity: .8;
    border-color: var(--theme-line);
    background: var(--theme-surface-alt);
    color: var(--theme-muted);
}}
</style>
"""
st.markdown(theme_override_css, unsafe_allow_html=True)
st.sidebar.markdown(
    f"<div class='theme-preview'><span class='theme-swatch' style='background:{selected_theme['navy950']}'></span>"
    f"<span class='theme-swatch' style='background:{selected_theme['card1']}'></span>"
    f"<span class='theme-swatch' style='background:{selected_theme['blue']}'></span>"
    f"<span class='theme-swatch' style='background:{selected_theme['accent']}'></span>"
    f"<span>{html_module.escape(selected_theme_name)}</span></div>",
    unsafe_allow_html=True
)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploaded_raw_data")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

FILE_MAP = {
    "PAYMENT": os.path.join(DATA_DIR, "payment_data.xlsx"),
    "LEGWISE": os.path.join(DATA_DIR, "legwise_data.xlsx"),
    "ROUTE_MASTER": os.path.join(DATA_DIR, "route_master.xlsx"),
    "BRANCH_MASTER": os.path.join(DATA_DIR, "branch_master.xlsx"),
    "MCD_VENDOR": os.path.join(DATA_DIR, "mcd_vendor.xlsx"),
    "CPK_UTIL": os.path.join(DATA_DIR, "cpk_util.xlsx"),
    "ROUTE_LOOKUP": os.path.join(DATA_DIR, "route_lookup.xlsx"),
    "FINAL_OUTPUT": os.path.join(DATA_DIR, "Auto_Generated_Monitoring_Data.xlsx"),
    "EXECUTIVE_REPORT": os.path.join(DATA_DIR, "Trackon_VIP_Executive_Report.xlsx"),
    "RATE_CORRECTIONS": os.path.join(DATA_DIR, "rate_corrections.json"),
    "VENDOR_MASTER": os.path.join(DATA_DIR, "vendor_master.json"),
    "ACTION_PLANS": os.path.join(DATA_DIR, "action_plans.json"),
    "USERS_DB": os.path.join(DATA_DIR, "users_master.json"),
    "VENDOR_CATEGORY_MAP": os.path.join(DATA_DIR, "vendor_category_mapping.json"),
    "USER_VENDOR_CATEGORY_MAP": os.path.join(DATA_DIR, "user_vendor_category_mappings.json"),
    "USER_TRACKED_VENDORS": os.path.join(DATA_DIR, "user_tracked_vendors.json")
}

DEFAULT_VENDOR_CATEGORY_MAP = {
    "Vehicle Vendors bill": [
        "Contract - Feeder Connection vehicle charges",
        "Contract Network Vehicle Hired - Regional",
        "Contract Network Vehicle Hired - Zonal",
        "Contract Network Vehicle Hired - National"
    ]
}

def load_vendor_category_mapping():
    path = FILE_MAP["VENDOR_CATEGORY_MAP"]
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                return loaded
        except Exception:
            pass
    save_vendor_category_mapping(DEFAULT_VENDOR_CATEGORY_MAP)
    return {k: list(v) for k, v in DEFAULT_VENDOR_CATEGORY_MAP.items()}

def save_vendor_category_mapping(mapping_dict):
    with open(FILE_MAP["VENDOR_CATEGORY_MAP"], 'w', encoding='utf-8') as f:
        json.dump(mapping_dict, f, indent=4)

def load_all_user_vendor_category_mappings():
    path = FILE_MAP["USER_VENDOR_CATEGORY_MAP"]
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {}

def load_user_vendor_category_mapping(username):
    if not username:
        return {}
    return dict(load_all_user_vendor_category_mappings().get(str(username), {}))

def save_user_vendor_category_mapping(username, mapping_dict):
    if not username:
        return
    all_maps = load_all_user_vendor_category_mappings()
    all_maps[str(username)] = mapping_dict
    with open(FILE_MAP["USER_VENDOR_CATEGORY_MAP"], 'w', encoding='utf-8') as f:
        json.dump(all_maps, f, indent=4)

def load_all_user_tracked_vendors():
    path = FILE_MAP["USER_TRACKED_VENDORS"]
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {}

def load_user_tracked_vendors(username):
    if not username:
        return {}
    return dict(load_all_user_tracked_vendors().get(str(username), {}))

def save_user_tracked_vendors(username, tracker_dict):
    if not username:
        return
    all_t = load_all_user_tracked_vendors()
    all_t[str(username)] = tracker_dict
    with open(FILE_MAP["USER_TRACKED_VENDORS"], 'w', encoding='utf-8') as f:
        json.dump(all_t, f, indent=4)

SCHEDULED_ROUTE_MASTER_TSV = r"""Route Path	Legwise	Legs	Scheduled Departure Time	Scheduled Arrival Time	Given Driving Hours	Scheduled Halting	Scheduled TAT Till Destination
BKLH-JPRBPH-DELAP	Leg1	BKLH to JPRBPH	01-09-2026 01:00	01-09-2026 16:00	15:00	Origin	23:01
BKLH-JPRBPH-DELAP	Leg2	JPRBPH to DELAP	01-09-2026 17:00	02-09-2026 00:01	7:01	1:00 at JPRBPH	23:01
BKLH-JPRH-DELAP	Leg1	BKLH to JPRH	12-09-2026 01:00	12-09-2026 16:00	15:00	Origin	23:01
BKLH-JPRH-DELAP	Leg2	JPRH to DELAP	12-09-2026 17:00	13-09-2026 00:01	7:01	1:00 at JPRH	23:01
DELAP-BKLH	Leg1	DELAP to BKLH	03-09-2026 15:00	04-09-2026 16:00	25:00	Origin	25:00
DELAP-JPRBPH-BKLH	Leg1	DELAP to JPRBPH	01-09-2026 15:00	01-09-2026 23:30	8:30	Origin	39:30
DELAP-JPRBPH-BKLH	Leg2	JPRBPH to BKLH	01-09-2026 01:30	02-09-2026 17:00	39:30	-22:00 at JPRBPH	39:30
DELAP-JPRH-BKLH	Leg1	DELAP to JPRH	10-09-2026 15:00	10-09-2026 23:30	8:30	Origin	39:30
DELAP-JPRH-BKLH	Leg2	JPRH to BKLH	10-09-2026 01:30	11-09-2026 17:00	39:30	-22:00 at JPRH	39:30
BLRSH-HYDH-NGPLAVA-DELAP	Leg1	BLRSH to HYDH	02-09-2026 08:00	02-09-2026 23:00	15:00	Origin	54:30
BLRSH-HYDH-NGPLAVA-DELAP	Leg2	HYDH to NGPLAVA	02-09-2026 23:59	03-09-2026 12:30	12:31	0:59 at HYDH	54:30
BLRSH-HYDH-NGPLAVA-DELAP	Leg3	NGPLAVA to DELAP	03-09-2026 13:30	04-09-2026 14:30	25:00	1:00 at NGPLAVA	54:30
DELAP-BLRSH	Leg1	DELAP to BLRSH	03-09-2026 05:00	05-09-2026 13:00	56:00	Origin	56:00
DELAP-NGPLAVA-HYDH-BLRSH	Leg1	DELAP to NGPLAVA	01-09-2026 05:00	02-09-2026 06:00	25:00	Origin	56:00
DELAP-NGPLAVA-HYDH-BLRSH	Leg2	NGPLAVA to HYDH	02-09-2026 07:30	02-09-2026 23:30	16:00	1:30 at NGPLAVA	56:00
DELAP-NGPLAVA-HYDH-BLRSH	Leg3	HYDH to BLRSH	02-09-2026 23:59	03-09-2026 13:00	13:01	0:29 at HYDH	56:00
BWNDLH-PNQHWH-BLRSH-HOSURH-CHIH	Leg1	BWNDLH to PNQHWH	01-09-2026 08:00	01-09-2026 13:00	5:00	Origin	46:00
BWNDLH-PNQHWH-BLRSH-HOSURH-CHIH	Leg2	PNQHWH to BLRSH	01-09-2026 14:30	02-09-2026 11:00	20:30	1:30 at PNQHWH	46:00
BWNDLH-PNQHWH-BLRSH-HOSURH-CHIH	Leg3	BLRSH to HOSURH	02-09-2026 20:30	02-09-2026 22:00	1:30	9:30 at BLRSH	46:00
BWNDLH-PNQHWH-BLRSH-HOSURH-CHIH	Leg4	HOSURH to CHIH	03-09-2026 22:30	04-09-2026 06:00	7:30	0:30 at HOSURH	46:00
CHIH-HOSURH-BLRSH-PNQHWH-BWNDLH	Leg1	CHIH to HOSURH	01-09-2026 04:30	01-09-2026 11:00	6:30	Origin	40:00
CHIH-HOSURH-BLRSH-PNQHWH-BWNDLH	Leg2	HOSURH to BLRSH	01-09-2026 11:30	01-09-2026 13:30	2:00	0:30 at HOSURH	40:00
CHIH-HOSURH-BLRSH-PNQHWH-BWNDLH	Leg3	BLRSH to PNQHWH	01-09-2026 15:30	02-09-2026 12:30	21:00	2:00 at BLRSH	40:00
CHIH-HOSURH-BLRSH-PNQHWH-BWNDLH	Leg4	PNQHWH to BWNDLH	12-09-2026 15:00	12-09-2026 20:30	5:30	2:30 at PNQHWH	40:00
BWNDLH-DELAP	Leg1	BWNDLH to DELAP	01-09-2026 10:30	03-09-2026 01:00	38:30	Origin	38:30
DELAP-BKLH-BWNDLH	Leg1	DELAP to BKLH	01-09-2026 05:00	02-09-2026 03:00	22:00	Origin	39:00
DELAP-BKLH-BWNDLH	Leg2	BKLH to BWNDLH	02-09-2026 05:00	02-09-2026 20:00	15:00	2:00 at BKLH	39:00
DELAP-BWNDLH	Leg1	DELAP to BWNDLH	02-09-2026 05:00	03-09-2026 20:00	39:00	Origin	39:00
BWNDLH-NGPLAVA-RAIH-HOWDG	Leg1	BWNDLH to NGPLAVA	01-09-2026 12:00	02-09-2026 04:00	16:00	Origin	50:00
BWNDLH-NGPLAVA-RAIH-HOWDG	Leg2	NGPLAVA to RAIH	02-09-2026 05:00	02-09-2026 17:00	12:00	1:00 at NGPLAVA	50:00
BWNDLH-NGPLAVA-RAIH-HOWDG	Leg3	RAIH to HOWDG	02-09-2026 18:00	03-09-2026 14:00	20:00	1:00 at RAIH	50:00
HOWDG-RAIH-NGPLAVA-BWNDLH	Leg1	HOWDG to RAIH	01-09-2026 13:00	02-09-2026 09:00	20:00	Origin	50:00
HOWDG-RAIH-NGPLAVA-BWNDLH	Leg2	RAIH to NGPLAVA	02-09-2026 10:00	02-09-2026 22:00	12:00	1:00 at RAIH	50:00
HOWDG-RAIH-NGPLAVA-BWNDLH	Leg3	NGPLAVA to BWNDLH	02-09-2026 23:00	03-09-2026 15:00	16:00	1:00 at NGPLAVA	50:00
BWNDLH-PNQHWH-HYDH	Leg1	BWNDLH to PNQHWH	01-09-2026 07:00	01-09-2026 13:00	6:00	Origin	19:00
BWNDLH-PNQHWH-HYDH	Leg2	PNQHWH to HYDH	01-09-2026 14:00	02-09-2026 02:00	12:00	1:00 at PNQHWH	19:00
HYDH-PNQHWH-BWNDLH	Leg1	HYDH to PNQHWH	01-09-2026 02:00	01-09-2026 15:00	13:00	Origin	25:00
HYDH-PNQHWH-BWNDLH	Leg2	PNQHWH to BWNDLH	01-09-2026 22:30	02-09-2026 03:00	4:30	7:30 at PNQHWH	25:00
CCUH-HOWDG-PATH-DELAP	Leg1	CCUH to HOWDG	01-09-2026 01:00	01-09-2026 02:00	1:00	Origin	46:30
CCUH-HOWDG-PATH-DELAP	Leg2	HOWDG to PATH	01-09-2026 03:00	01-09-2026 18:00	15:00	1:00 at HOWDG	46:30
CCUH-HOWDG-PATH-DELAP	Leg3	PATH to DELAP	02-09-2026 19:00	03-09-2026 23:30	28:30	1:00 at PATH	46:30
DELAP-PATH-CCUH	Leg1	DELAP to PATH	01-09-2026 03:00	02-09-2026 05:00	26:00	Origin	43:00
DELAP-PATH-CCUH	Leg2	PATH to CCUH	02-09-2026 06:00	02-09-2026 22:00	16:00	1:00 at PATH	43:00
DELAP-BHOH-INDH	Leg1	DELAP to BHOH	01-09-2026 04:30	02-09-2026 01:00	20:30	Origin	28:30
DELAP-BHOH-INDH	Leg2	BHOH to INDH	02-09-2026 04:00	02-09-2026 09:00	5:00	3:00 at BHOH	28:30
INDH-BHOH-GWLH-DELAP	Leg1	INDH to BHOH	01-09-2026 23:30	02-09-2026 04:30	5:00	Origin	27:30
INDH-BHOH-GWLH-DELAP	Leg2	BHOH to GWLH	02-09-2026 05:30	02-09-2026 16:30	11:00	1:00 at BHOH	27:30
INDH-BHOH-GWLH-DELAP	Leg3	GWLH to DELAP	02-09-2026 17:00	03-09-2026 03:00	10:00	0:30 at GWLH	27:30
PATH-VNS1	Leg1	PATH to VNS1	01-09-2026 23:30	02-09-2026 08:30	9:00	Origin	9:00
VNS1-PATH	Leg1	VNS1 to PATH	01-09-2026 23:30	02-09-2026 08:30	9:00	Origin	9:00
AGR1-MTHB-DELAP	Leg1	AGR1 to MTHB	01-09-2026 23:00	02-09-2026 01:00	2:00	Origin	6:00
AGR1-MTHB-DELAP	Leg2	MTHB to DELAP	02-09-2026 01:30	02-09-2026 05:00	3:30	0:30 at MTHB	6:00
DELAP-MTHB-AGR1	Leg1	DELAP to MTHB	01-09-2026 03:30	01-09-2026 07:00	3:30	Origin	9:00
DELAP-MTHB-AGR1	Leg2	MTHB to AGR1	01-09-2026 07:30	01-09-2026 09:00	1:30	0:30 at MTHB	9:00
ALGH-GZBH-DELAP	Leg1	ALGH to GZBH	01-09-2026 23:30	02-09-2026 02:00	2:30	Origin	4:30
ALGH-GZBH-DELAP	Leg2	GZBH to DELAP	02-09-2026 02:30	02-09-2026 04:00	1:30	0:30 at GZBH	4:30
DELAP-ALGH	Leg1	DELAP to ALGH	01-09-2026 04:30	01-09-2026 07:30	3:00	Origin	7:30
DELAP-GZBH-ALGH	Leg1	DELAP to GZBH	02-09-2026 05:00	02-09-2026 07:00	2:00	Origin	9:00
DELAP-GZBH-ALGH	Leg2	GZBH to ALGH	02-09-2026 07:30	02-09-2026 09:00	1:30	0:30 at GZBH	9:00
AMBH-DELAP	Leg1	AMBH to DELAP	01-09-2026 02:15	01-09-2026 06:45	4:30	Origin	6:45
DELAP-AMBH	Leg1	DELAP to AMBH	02-09-2026 00:00	02-09-2026 05:00	5:00	Origin	5:00
AMBH-PKLH-IXCH	Leg1	AMBH to PKLH	01-09-2026 07:30	01-09-2026 08:30	1:00	Origin	9:30
AMBH-PKLH-IXCH	Leg2	PKLH to IXCH	01-09-2026 09:00	01-09-2026 09:30	0:30	0:30 at PKLH	9:30
IXCH-AMBH	Leg1	IXCH to AMBH	01-09-2026 01:30	01-09-2026 02:30	1:00	Origin	2:30
AMBH-RJPH-LDHH-JLRH	Leg1	AMBH to RJPH	01-09-2026 06:30	01-09-2026 07:30	1:00	Origin	12:00
AMBH-RJPH-LDHH-JLRH	Leg2	RJPH to LDHH	01-09-2026 08:00	01-09-2026 10:00	2:00	0:30 at RJPH	12:00
AMBH-RJPH-LDHH-JLRH	Leg3	LDHH to JLRH	06-09-2026 10:30	06-09-2026 12:00	1:30	0:30 at LDHH	12:00
JLRH-LDHH-AMBH	Leg1	JLRH to LDHH	01-09-2026 22:30	02-09-2026 00:01	1:31	Origin	4:30
JLRH-LDHH-AMBH	Leg2	LDHH to AMBH	02-09-2026 01:00	02-09-2026 03:00	2:00	0:59 at LDHH	4:30
AMBH-KLKH	Leg1	AMBH to KLKH	01-09-2026 07:00	01-09-2026 08:30	1:30	Origin	8:30
KLKH-AMBH	Leg1	KLKH to AMBH	02-09-2026 01:00	02-09-2026 03:00	2:00	Origin	3:00
AMDH-AMDKKH-MUMH	Leg1	AMDH to AMDKKH	01-09-2026 22:00	01-09-2026 22:30	0:30	Origin	10:00
AMDH-AMDKKH-MUMH	Leg2	AMDKKH to MUMH	01-09-2026 23:00	02-09-2026 08:00	9:00	0:30 at AMDKKH	10:00
MUMH-VASAOH-AMDH	Leg1	MUMH to VASAOH	01-09-2026 23:00	02-09-2026 00:30	1:30	Origin	10:30
MUMH-VASAOH-AMDH	Leg2	VASAOH to AMDH	02-09-2026 00:40	02-09-2026 09:30	8:50	0:10 at VASAOH	10:30
ASRH-JLRH-DELAP	Leg1	ASRH to JLRH	01-09-2026 20:00	01-09-2026 22:00	2:00	Origin	11:00
ASRH-JLRH-DELAP	Leg2	JLRH to DELAP	01-09-2026 22:30	02-09-2026 07:00	8:30	0:30 at JLRH	11:00
DELAP-JLRH-ASRH	Leg1	DELAP to JLRH	02-09-2026 00:01	02-09-2026 08:30	8:29	Origin	11:00
DELAP-JLRH-ASRH	Leg2	JLRH to ASRH	02-09-2026 09:00	02-09-2026 11:00	2:00	0:30 at JLRH	11:00
BBSH-CTKH-JJPRH-BLSRB-HOWDG-CCUH	Leg1	BBSH to CTKH	01-09-2026 21:00	01-09-2026 22:30	1:30	Origin	16:00
BBSH-CTKH-JJPRH-BLSRB-HOWDG-CCUH	Leg2	CTKH to JJPRH	01-09-2026 23:00	02-09-2026 01:15	2:15	0:30 at CTKH	16:00
BBSH-CTKH-JJPRH-BLSRB-HOWDG-CCUH	Leg3	JJPRH to BLSRB	02-09-2026 01:45	02-09-2026 06:00	4:15	0:30 at JJPRH	16:00
BBSH-CTKH-JJPRH-BLSRB-HOWDG-CCUH	Leg4	BLSRB to HOWDG	02-09-2026 06:30	02-09-2026 11:30	5:00	0:30 at BLSRB	16:00
CCUH-HOWDG-BLSRB-JJPRH-CTKH-BBSH	Leg1	CCUH to HOWDG	01-09-2026 22:30	01-09-2026 23:30	1:00	Origin	14:00
CCUH-HOWDG-BLSRB-JJPRH-CTKH-BBSH	Leg2	HOWDG to BLSRB	01-09-2026 23:59	02-09-2026 05:30	5:31	0:29 at HOWDG	14:00
CCUH-HOWDG-BLSRB-JJPRH-CTKH-BBSH	Leg3	BLSRB to JJPRH	02-09-2026 06:00	02-09-2026 08:30	2:30	0:30 at BLSRB	14:00
CCUH-HOWDG-BLSRB-JJPRH-CTKH-BBSH	Leg4	JJPRH to CTKH	07-09-2026 09:00	07-09-2026 11:00	2:00	0:30 at JJPRH	14:00
CCUH-HOWDG-BLSRB-JJPRH-CTKH-BBSH	Leg5	CTKH to BBSH	15-09-2026 11:30	15-09-2026 12:30	1:00	0:30 at CTKH	14:00
BDQH-ANKH-SRTKDH-MUMH	Leg1	BDQH to ANKH	01-09-2026 22:00	01-09-2026 23:30	1:30	Origin	10:00
BDQH-ANKH-SRTKDH-MUMH	Leg2	ANKH to SRTKDH	01-09-2026 23:45	02-09-2026 02:00	2:15	0:15 at ANKH	10:00
BDQH-ANKH-SRTKDH-MUMH	Leg3	SRTKDH to MUMH	02-09-2026 02:30	02-09-2026 08:00	5:30	0:30 at SRTKDH	10:00
MUMH-VASAOH-SRTKDH-ANKH-BDQH	Leg1	MUMH to VASAOH	01-09-2026 23:30	02-09-2026 01:00	1:30	Origin	10:30
MUMH-VASAOH-SRTKDH-ANKH-BDQH	Leg2	VASAOH to SRTKDH	02-09-2026 01:10	02-09-2026 06:00	4:50	0:10 at VASAOH	10:30
BGHB-DELAP	Leg1	BGHB to DELAP	01-09-2026 23:00	02-09-2026 03:00	4:00	Origin	4:00
DELAP-BGHB	Leg1	DELAP to BGHB	01-09-2026 06:00	01-09-2026 07:30	1:30	Origin	7:30
BKLH-BDQH-ANKH-SRTKDH-MUMH	Leg1	BKLH to BDQH	01-09-2026 01:00	01-09-2026 03:00	2:00	Origin	14:00
BKLH-BDQH-ANKH-SRTKDH-MUMH	Leg2	BDQH to ANKH	01-09-2026 03:45	01-09-2026 05:30	1:45	0:45 at BDQH	14:00
BKLH-BDQH-ANKH-SRTKDH-MUMH	Leg3	ANKH to SRTKDH	01-09-2026 06:00	01-09-2026 08:30	2:30	0:30 at ANKH	14:00
BKLH-BDQH-ANKH-SRTKDH-MUMH	Leg4	SRTKDH to MUMH	15-09-2026 09:00	15-09-2026 14:00	5:00	0:30 at SRTKDH	14:00
MUMH-SRTKDH-BDQH-BKLH	Leg1	MUMH to SRTKDH	01-09-2026 04:00	01-09-2026 11:00	7:00	Origin	17:00
MUMH-SRTKDH-BDQH-BKLH	Leg2	SRTKDH to BDQH	01-09-2026 11:15	01-09-2026 14:15	3:00	0:15 at SRTKDH	17:00
BLRSH-HOSURH-SLMH-CJBH-COKAP	Leg1	BLRSH to HOSURH	01-09-2026 23:00	02-09-2026 00:30	1:30	Origin	14:00
BLRSH-HOSURH-SLMH-CJBH-COKAP	Leg2	HOSURH to SLMH	02-09-2026 01:00	02-09-2026 05:00	4:00	0:30 at HOSURH	14:00
BLRSH-HOSURH-SLMH-CJBH-COKAP	Leg3	SLMH to CJBH	02-09-2026 05:30	02-09-2026 09:00	3:30	0:30 at SLMH	14:00
BLRSH-HOSURH-SLMH-CJBH-COKAP	Leg4	CJBH to COKAP	16-09-2026 09:30	16-09-2026 13:00	3:30	0:30 at CJBH	14:00
COKAP-CJBH-SLMH-HOSURH-BLRSH	Leg1	COKAP to CJBH	01-09-2026 19:00	01-09-2026 23:00	4:00	Origin	15:30
COKAP-CJBH-SLMH-HOSURH-BLRSH	Leg2	CJBH to SLMH	01-09-2026 23:59	02-09-2026 03:30	3:31	0:59 at CJBH	15:30
COKAP-CJBH-SLMH-HOSURH-BLRSH	Leg3	SLMH to HOSURH	02-09-2026 04:00	02-09-2026 08:00	4:00	0:30 at SLMH	15:30
BLYH-DELAP	Leg1	BLYH to DELAP	09-09-2026 21:00	10-09-2026 06:30	9:30	Origin	9:30
BLYH-MBDH-DELAP	Leg1	BLYH to MBDH	01-09-2026 21:00	02-09-2026 00:30	3:30	Origin	9:30
BLYH-MBDH-DELAP	Leg2	MBDH to DELAP	02-09-2026 01:00	02-09-2026 06:30	5:30	0:30 at MBDH	9:30
DELAP-GZBH-MBDH-BLYH	Leg1	DELAP to GZBH	01-09-2026 02:00	01-09-2026 03:30	1:30	Origin	10:00
DELAP-GZBH-MBDH-BLYH	Leg2	GZBH to MBDH	01-09-2026 04:00	01-09-2026 07:00	3:00	0:30 at GZBH	10:00
DELAP-MBDH-BLYH	Leg1	DELAP to MBDH	03-09-2026 02:00	03-09-2026 08:00	6:00	Origin	11:45
DELAP-MBDH-BLYH	Leg2	MBDH to BLYH	03-09-2026 08:30	03-09-2026 11:45	3:15	0:30 at MBDH	11:45
BWNDH-BWNDLH-PNQHWH-PNQH	Leg1	BWNDH to BWNDLH	01-09-2026 22:30	01-09-2026 23:00	0:30	Origin	7:00
BWNDH-BWNDLH-PNQHWH-PNQH	Leg2	BWNDLH to PNQHWH	01-09-2026 23:15	02-09-2026 03:15	4:00	0:15 at BWNDLH	7:00
BWNDH-BWNDLH-PNQHWH-PNQH	Leg3	PNQHWH to PNQH	02-09-2026 04:15	02-09-2026 05:30	1:15	1:00 at PNQHWH	7:00
PNQH-PNQHWH-BWNDLH	Leg1	PNQH to PNQHWH	02-09-2026 00:01	02-09-2026 01:00	0:59	Origin	6:30
PNQH-PNQHWH-BWNDLH	Leg2	PNQHWH to BWNDLH	02-09-2026 03:30	02-09-2026 06:30	3:00	2:30 at PNQHWH	6:30
BWNDLH-PNQHWH	Leg1	BWNDLH to PNQHWH	15-09-2026 05:00	15-09-2026 10:00	5:00	Origin	10:00
CCUH-HOWDG-KGPRH-JSRH-RNC1	Leg1	CCUH to HOWDG	01-09-2026 23:00	02-09-2026 00:00	1:00	Origin	13:00
CCUH-HOWDG-KGPRH-JSRH-RNC1	Leg2	HOWDG to KGPRH	02-09-2026 00:30	02-09-2026 03:30	3:00	0:30 at HOWDG	13:00
CCUH-HOWDG-KGPRH-JSRH-RNC1	Leg3	KGPRH to JSRH	03-09-2026 04:00	03-09-2026 08:00	4:00	0:30 at KGPRH	13:00
CCUH-HOWDG-KGPRH-JSRH-RNC1	Leg4	JSRH to RNC1	05-09-2026 08:30	05-09-2026 12:00	3:30	0:30 at JSRH	13:00
RNC1-JSRH-KGPRH-HOWDG-CCUH	Leg1	RNC1 to JSRH	01-09-2026 22:00	02-09-2026 01:30	3:30	Origin	12:00
RNC1-JSRH-KGPRH-HOWDG-CCUH	Leg2	JSRH to KGPRH	02-09-2026 02:00	02-09-2026 05:30	3:30	0:30 at JSRH	12:00
RNC1-JSRH-KGPRH-HOWDG-CCUH	Leg3	KGPRH to HOWDG	02-09-2026 06:00	02-09-2026 08:00	2:00	0:30 at KGPRH	12:00
RNC1-JSRH-KGPRH-HOWDG-CCUH	Leg4	HOWDG to CCUH	05-09-2026 08:30	05-09-2026 10:00	1:30	0:30 at HOWDG	12:00
CHIH-SLMH-COKAP	Leg1	CHIH to SLMH	12-09-2026 23:30	13-09-2026 05:30	6:00	Origin	13:30
CHIH-SLMH-COKAP	Leg2	SLMH to COKAP	13-09-2026 06:30	13-09-2026 13:00	6:30	1:00 at SLMH	13:30
CHIH-VPMH-SLMH-PKDH-COKAP	Leg1	CHIH to VPMH	01-09-2026 23:30	02-09-2026 05:30	6:00	Origin	15:30
CHIH-VPMH-SLMH-PKDH-COKAP	Leg2	VPMH to SLMH	02-09-2026 06:30	02-09-2026 10:00	3:30	1:00 at VPMH	15:30
CHIH-VPMH-SLMH-PKDH-COKAP	Leg3	SLMH to PKDH	06-09-2026 10:30	06-09-2026 11:30	1:00	0:30 at SLMH	15:30
COKAP-SLMH-CHIH	Leg1	COKAP to SLMH	01-09-2026 19:00	02-09-2026 01:00	6:00	Origin	12:30
COKAP-SLMH-CHIH	Leg2	SLMH to CHIH	02-09-2026 01:30	02-09-2026 07:30	6:00	0:30 at SLMH	12:30
COKH-THRH-CJBH-TRPH1-ERDH	Leg1	COKH to THRH	01-09-2026 04:15	01-09-2026 05:15	1:00	Origin	11:00
COKH-THRH-CJBH-TRPH1-ERDH	Leg2	THRH to CJBH	01-09-2026 06:15	01-09-2026 08:45	2:30	1:00 at THRH	11:00
COKH-THRH-CJBH-TRPH1-ERDH	Leg3	CJBH to TRPH1	01-09-2026 09:00	01-09-2026 09:45	0:45	0:15 at CJBH	11:00
ERDH-TRPH1-CJBH-COKAP-COKH	Leg1	ERDH to TRPH1	01-09-2026 21:00	01-09-2026 22:00	1:00	Origin	6:45
ERDH-TRPH1-CJBH-COKAP-COKH	Leg2	TRPH1 to CJBH	01-09-2026 22:30	01-09-2026 23:15	0:45	0:30 at TRPH1	6:45
ERDH-TRPH1-CJBH-COKAP-COKH	Leg3	CJBH to COKAP	01-09-2026 23:45	02-09-2026 03:00	3:15	0:30 at CJBH	6:45
ERDH-TRPH1-CJBH-COKAP-COKH	Leg4	COKAP to COKH	02-09-2026 03:15	02-09-2026 03:45	0:30	0:15 at COKAP	6:45
DDNS-RRKH-GZBH-DELAP	Leg1	DDNS to RRKH	01-09-2026 23:00	02-09-2026 00:30	1:30	Origin	7:00
DDNS-RRKH-GZBH-DELAP	Leg2	RRKH to GZBH	02-09-2026 01:00	02-09-2026 04:00	3:00	0:30 at RRKH	7:00
DDNS-RRKH-GZBH-DELAP	Leg3	GZBH to DELAP	04-09-2026 04:15	04-09-2026 06:00	1:45	0:15 at GZBH	7:00
DELAP-GZBH-RRKH-DDNS	Leg1	DELAP to GZBH	01-09-2026 02:00	01-09-2026 03:30	1:30	Origin	10:00
DELAP-GZBH-RRKH-DDNS	Leg2	GZBH to RRKH	01-09-2026 04:00	01-09-2026 07:30	3:30	0:30 at GZBH	10:00
DELAP-GZBH-RRKH-DDNS	Leg3	RRKH to DDNS	01-09-2026 08:00	01-09-2026 10:00	2:00	0:30 at RRKH	10:00
DELAP-GZBH	Leg1	DELAP to GZBH	01-09-2026 05:00	01-09-2026 08:00	3:00	Origin	8:00
DELAP-SBDH-GZBH	Leg1	DELAP to SBDH	N/A	N/A		Origin	
DELAP-SBDH-GZBH	Leg2	SBDH to GZBH	N/A	N/A		0:00 at SBDH	
GZBH-DELAP	Leg1	GZBH to DELAP	01-09-2026 23:30	02-09-2026 01:00	1:30	Origin	1:30
GZBH-SBDH-DELAP	Leg1	GZBH to SBDH	01-09-2026 21:32	01-09-2026 22:15	0:43	Origin	23:45
GZBH-SBDH-DELAP	Leg2	SBDH to DELAP	01-09-2026 22:30	01-09-2026 23:45	1:15	0:15 at SBDH	23:45
DELAP-GZBH-MBDH-RUDH-HALDH	Leg1	DELAP to GZBH	01-09-2026 02:00	01-09-2026 03:30	1:30	Origin	11:00
DELAP-GZBH-MBDH-RUDH-HALDH	Leg2	GZBH to MBDH	01-09-2026 04:00	01-09-2026 07:00	3:00	0:30 at GZBH	11:00
DELAP-GZBH-MBDH-RUDH-HALDH	Leg3	MBDH to RUDH	16-09-2026 07:30	16-09-2026 09:30	2:00	0:30 at MBDH	11:00
DELAP-MBDH-RUDH-HALDH	Leg1	DELAP to MBDH	03-09-2026 01:30	03-09-2026 05:30	4:00	Origin	12:00
DELAP-MBDH-RUDH-HALDH	Leg2	MBDH to RUDH	03-09-2026 06:00	03-09-2026 08:30	2:30	0:30 at MBDH	12:00
DELAP-MBDH-RUDH-HALDH	Leg3	RUDH to HALDH	03-09-2026 09:00	03-09-2026 12:00	3:00	0:30 at RUDH	12:00
HALDH-RUDH-MBDH-GZBH-DELAP	Leg1	HALDH to RUDH	01-09-2026 20:30	01-09-2026 22:00	1:30	Origin	9:45
HALDH-RUDH-MBDH-GZBH-DELAP	Leg2	RUDH to MBDH	01-09-2026 23:00	02-09-2026 01:00	2:00	1:00 at RUDH	9:45
HALDH-RUDH-MBDH-GZBH-DELAP	Leg3	MBDH to GZBH	03-09-2026 01:30	03-09-2026 04:15	2:45	0:30 at MBDH	9:45
DELAP-RRKH-HRDH	Leg1	DELAP to RRKH	08-09-2026 02:00	08-09-2026 07:00	5:00	Origin	8:59
HRDH-RRKH-DELAP	Leg1	HRDH to RRKH	01-09-2026 23:00	02-09-2026 00:00	1:00	Origin	6:30
HRDH-RRKH-DELAP	Leg2	RRKH to DELAP	02-09-2026 00:30	02-09-2026 05:30	5:00	0:30 at RRKH	6:30
DELAP-RTQH-HSRH	Leg1	DELAP to RTQH	01-09-2026 04:30	01-09-2026 06:30	2:00	Origin	9:00
DELAP-RTQH-HSRH	Leg2	RTQH to HSRH	01-09-2026 07:00	01-09-2026 09:00	2:00	0:30 at RTQH	9:00
HSRH-RTQH-DELAP	Leg1	HSRH to RTQH	01-09-2026 21:00	02-09-2026 22:00	25:00	Origin	26:30
HSRH-RTQH-DELAP	Leg2	RTQH to DELAP	02-09-2026 22:30	02-09-2026 23:30	1:00	0:30 at RTQH	26:30
DELAP-AMBH-IXCH	Leg1	DELAP to AMBH	01-09-2026 03:30	01-09-2026 08:30	5:00	Origin	9:30
DELAP-AMBH-IXCH	Leg2	AMBH to IXCH	01-09-2026 09:00	01-09-2026 09:30	0:30	0:30 at AMBH	9:30
DELAP-IXCH	Leg1	DELAP to IXCH	01-09-2026 03:00	01-09-2026 08:30	5:30	Origin	8:30
IXCH-DELAP	Leg1	IXCH to DELAP	01-09-2026 00:30	01-09-2026 06:30	6:00	Origin	6:30
IXCH-PKLH-DELAP	Leg1	IXCH to PKLH	01-09-2026 20:30	01-09-2026 21:00	0:30	Origin	9:00
IXCH-PKLH-DELAP	Leg2	PKLH to DELAP	01-09-2026 23:30	02-09-2026 05:30	6:00	2:30 at PKLH	9:00
DELAP-LDHH-JLRH	Leg1	DELAP to LDHH	06-09-2026 00:30	06-09-2026 08:30	8:00	Origin	11:00
DELAP-LDHH-JLRH	Leg2	LDHH to JLRH	06-09-2026 09:30	06-09-2026 11:00	1:30	1:00 at LDHH	11:00
JPRBPH-JPRH-BEHH-DELAP	Leg1	JPRBPH to JPRH	03-09-2026 22:00	03-09-2026 22:30	0:30	Origin	7:30
JPRBPH-JPRH-BEHH-DELAP	Leg2	JPRH to BEHH	03-09-2026 23:00	04-09-2026 02:00	3:00	0:30 at JPRH	7:30
JPRBPH-JPRH-BEHH-DELAP	Leg3	BEHH to DELAP	04-09-2026 02:30	04-09-2026 05:30	3:00	0:30 at BEHH	7:30
DELAP-BEHH-JPRH	Leg1	DELAP to BEHH	01-09-2026 03:00	01-09-2026 06:30	3:30	Origin	9:00
DELAP-BEHH-JPRH	Leg2	BEHH to JPRH	01-09-2026 07:00	01-09-2026 09:00	2:00	0:30 at BEHH	9:00
DELAP-JPRH	Leg1	DELAP to JPRH	02-09-2026 00:00	02-09-2026 06:00	6:00	Origin	6:00
JPRH-BEHH-DELAP	Leg1	JPRH to BEHH	01-09-2026 22:00	02-09-2026 00:30	2:30	Origin	5:30
JPRH-BEHH-DELAP	Leg2	BEHH to DELAP	02-09-2026 00:45	02-09-2026 03:30	2:45	0:15 at BEHH	5:30
JPRH-DELAP	Leg1	JPRH to DELAP	01-09-2026 00:00	02-09-2026 06:00	30:00	Origin	30:00
JPRH-JPRBPH-DELAP	Leg1	JPRH to JPRBPH	04-09-2026 23:30	05-09-2026 00:01	0:31	Origin	7:00
JPRH-JPRBPH-DELAP	Leg2	JPRBPH to DELAP	05-09-2026 00:30	05-09-2026 06:30	6:00	0:29 at JPRBPH	7:00
DELAP-PKLH-KLKH	Leg1	DELAP to PKLH	01-09-2026 01:00	01-09-2026 07:00	6:00	Origin	9:30
DELAP-PKLH-KLKH	Leg2	PKLH to KLKH	01-09-2026 08:15	01-09-2026 09:30	1:15	1:15 at PKLH	9:30
KLKH-PKLH-DELAP	Leg1	KLKH to PKLH	01-09-2026 00:30	02-09-2026 01:30	25:00	Origin	30:00
KLKH-PKLH-DELAP	Leg2	PKLH to DELAP	04-09-2026 02:00	04-09-2026 06:30	4:30	0:30 at PKLH	30:00
DELAP-PNPH-KNLH	Leg1	DELAP to PNPH	01-09-2026 04:30	01-09-2026 07:00	2:30	Origin	9:00
DELAP-PNPH-KNLH	Leg2	PNPH to KNLH	01-09-2026 08:00	01-09-2026 09:00	1:00	1:00 at PNPH	9:00
KNLH-PNPH-DELAP	Leg1	KNLH to PNPH	01-09-2026 21:30	01-09-2026 23:30	2:00	Origin	5:30
KNLH-PNPH-DELAP	Leg2	PNPH to DELAP	01-09-2026 23:59	02-09-2026 03:00	3:01	0:29 at PNPH	5:30
DELAP-LDHH	Leg1	DELAP to LDHH	01-09-2026 00:30	01-09-2026 08:30	8:00	Origin	8:30
LDHH-DELAP	Leg1	LDHH to DELAP	01-09-2026 23:30	02-09-2026 07:00	7:30	Origin	7:30
DELAP-LKOH	Leg1	DELAP to LKOH	01-09-2026 23:59	02-09-2026 09:30	9:31	Origin	9:31
LKOH-DELAP	Leg1	LKOH to DELAP	01-09-2026 01:00	02-09-2026 12:00	35:00	Origin	35:00
DELAP-KNPKNB-LKOTP1	Leg1	DELAP to KNPKNB	01-09-2026 05:00	01-09-2026 16:00	11:00	Origin	19:00
DELAP-KNPKNB-LKOTP1	Leg2	KNPKNB to LKOTP1	01-09-2026 17:00	01-09-2026 19:00	2:00	1:00 at KNPKNB	19:00
DELAP-LKOTP1	Leg1	DELAP to LKOTP1	02-09-2026 03:00	03-09-2026 12:00	33:00	Origin	33:00
LKOTP1-DELAP	Leg1	LKOTP1 to DELAP	03-09-2026 16:00	04-09-2026 03:00	11:00	Origin	11:00
LKOTP1-KNPKNB-DELAP	Leg1	LKOTP1 to KNPKNB	01-09-2026 02:00	01-09-2026 04:30	2:30	Origin	16:00
LKOTP1-KNPKNB-DELAP	Leg2	KNPKNB to DELAP	01-09-2026 05:30	01-09-2026 16:00	10:30	1:00 at KNPKNB	16:00
DELAP-GZBH-MRTH	Leg1	DELAP to GZBH	01-09-2026 05:00	01-09-2026 06:30	1:30	Origin	8:30
DELAP-GZBH-MRTH	Leg2	GZBH to MRTH	01-09-2026 07:00	01-09-2026 08:30	1:30	0:30 at GZBH	8:30
MRTH-GZBH-DELAP	Leg1	MRTH to GZBH	01-09-2026 23:55	02-09-2026 01:00	1:05	Origin	3:35
MRTH-GZBH-DELAP	Leg2	GZBH to DELAP	02-09-2026 01:30	02-09-2026 03:30	2:00	0:30 at GZBH	3:35
DELAP-RRKH-HRDH-RKSH	Leg1	DELAP to RRKH	01-09-2026 03:00	02-09-2026 06:00	27:00	Origin	30:00
DELAP-RRKH-HRDH-RKSH	Leg2	RRKH to HRDH	06-09-2026 06:30	05-09-2026 08:30	-22:00	0:30 at RRKH	30:00
DELAP-SBDH	Leg1	DELAP to SBDH	N/A	N/A		Origin	
SBDH-DELAP	Leg1	SBDH to DELAP	N/A	N/A		Origin	
DELAP-SNP2-SNPH	Leg1	DELAP to SNP2	01-09-2026 05:00	01-09-2026 06:30	1:30	Origin	8:00
DELAP-SNP2-SNPH	Leg2	SNP2 to SNPH	01-09-2026 07:30	01-09-2026 08:00	0:30	1:00 at SNP2	8:00
SNPH-SNP2-DELAP	Leg1	SNPH to SNP2	01-09-2026 22:00	01-09-2026 23:00	1:00	Origin	3:30
SNPH-SNP2-DELAP	Leg2	SNP2 to DELAP	01-09-2026 23:30	02-09-2026 01:30	2:00	0:30 at SNP2	3:30
DELAP-MZNH-SREH	Leg1	DELAP to MZNH	01-09-2026 04:30	01-09-2026 08:30	4:00	Origin	10:00
DELAP-MZNH-SREH	Leg2	MZNH to SREH	01-09-2026 09:00	01-09-2026 10:00	1:00	0:30 at MZNH	10:00
SREH-MZNH-DELAP	Leg1	SREH to MZNH	01-09-2026 22:30	01-09-2026 23:55	1:25	Origin	27:20
SREH-MZNH-DELAP	Leg2	MZNH to DELAP	01-09-2026 00:10	02-09-2026 03:30	27:20	-23:45 at MZNH	27:20
DELAP-KNPKNB-IXD1-VNSTPT-VNS1	Leg1	DELAP to KNPKNB	04-09-2026 03:00	05-09-2026 14:00	35:00	Origin	45:20
DELAP-KNPKNB-IXD1-VNSTPT-VNS1	Leg2	KNPKNB to IXD1	05-09-2026 15:00	05-09-2026 20:00	5:00	1:00 at KNPKNB	45:20
DELAP-KNPKNB-IXD1-VNSTPT-VNS1	Leg3	IXD1 to VNSTPT	05-09-2026 21:00	06-09-2026 00:00	3:00	1:00 at IXD1	45:20
DELAP-KNPKNB-IXD1-VNSTPT-VNS1	Leg4	VNSTPT to VNS1	06-09-2026 00:15	06-09-2026 00:20	0:05	0:15 at VNSTPT	45:20
VNS1-VNSTPT-IXD1-KNPKNB-DELAP	Leg1	VNS1 to VNSTPT	01-09-2026 23:00	01-09-2026 23:30	0:30	Origin	47:59
VNS1-VNSTPT-IXD1-KNPKNB-DELAP	Leg2	VNSTPT to IXD1	01-09-2026 00:00	02-09-2026 02:30	26:30	-23:30 at VNSTPT	47:59
VNS1-VNSTPT-IXD1-KNPKNB-DELAP	Leg3	IXD1 to KNPKNB	04-09-2026 03:00	04-09-2026 07:00	4:00	0:30 at IXD1	47:59
DELAP-IXD1-VNSTPT	Leg1	DELAP to IXD1	04-09-2026 11:00	05-09-2026 23:00	36:00	Origin	36:00
DELAP-IXD1-VNSTPT	Leg2	IXD1 to VNSTPT	05-09-2026 01:00	05-09-2026 07:00	6:00	-22:00 at IXD1	36:00
DELAP-KNPKNB-IXD1-VNSTPT	Leg1	DELAP to KNPKNB	02-09-2026 11:00	03-09-2026 22:00	35:00	Origin	35:00
DELAP-KNPKNB-IXD1-VNSTPT	Leg2	KNPKNB to IXD1	03-09-2026 22:30	03-09-2026 03:00	-19:30	0:30 at KNPKNB	35:00
DELAP-KNPKNB-IXD1-VNSTPT	Leg3	IXD1 to VNSTPT	07-09-2026 03:30	07-09-2026 07:00	3:30	0:30 at IXD1	35:00
GZBH-MBDH-BLYH-LKOTP1	Leg1	GZBH to MBDH	02-09-2026 23:00	03-09-2026 02:30	3:30	Origin	13:30
GZBH-MBDH-BLYH-LKOTP1	Leg2	MBDH to BLYH	03-09-2026 03:00	03-09-2026 05:00	2:00	0:30 at MBDH	13:30
GZBH-MBDH-BLYH-LKOTP1	Leg3	BLYH to LKOTP1	03-09-2026 05:30	03-09-2026 12:30	7:00	0:30 at BLYH	13:30
LKOTP1-BLYH-MBDH-GZBH	Leg1	LKOTP1 to BLYH	01-09-2026 00:30	02-09-2026 06:30	30:00	Origin	37:30
LKOTP1-BLYH-MBDH-GZBH	Leg2	BLYH to MBDH	11-09-2026 07:00	11-09-2026 10:00	3:00	0:30 at BLYH	37:30
GZBH-NDAH-NDAPH2	Leg1	GZBH to NDAH	N/A	N/A		Origin	
GZBH-NDAH-NDAPH2	Leg2	NDAH to NDAPH2	N/A	N/A		0:00 at NDAH	
NDAPH2-NDAH-GZBH	Leg1	NDAPH2 to NDAH	N/A	N/A		Origin	
NDAPH2-NDAH-GZBH	Leg2	NDAH to GZBH	N/A	N/A		0:00 at NDAH	
MUMDAH-MUMTCS-MUMGTK-MUMSPD-PNQHWH	Leg1	MUMDAH to MUMTCS	01-09-2026 21:00	01-09-2026 22:15	1:15	Origin	6:30
MUMDAH-MUMTCS-MUMGTK-MUMSPD-PNQHWH	Leg2	MUMTCS to MUMGTK	01-09-2026 22:30	01-09-2026 23:00	0:30	0:15 at MUMTCS	6:30
MUMDAH-MUMTCS-MUMGTK-MUMSPD-PNQHWH	Leg3	MUMGTK to MUMSPD	01-09-2026 23:15	02-09-2026 00:01	0:46	0:15 at MUMGTK	6:30
MUMDAH-MUMTCS-MUMGTK-MUMSPD-PNQHWH	Leg4	MUMSPD to PNQHWH	02-09-2026 00:30	02-09-2026 03:30	3:00	0:29 at MUMSPD	6:30
MUMFORT -MUMLWP-MUMH-PNQHWH	Leg1	MUMFORT  to MUMLWP	01-09-2026 21:15	01-09-2026 21:50	0:35	Origin	5:15
MUMFORT -MUMLWP-MUMH-PNQHWH	Leg2	MUMLWP to MUMH	01-09-2026 22:00	01-09-2026 22:45	0:45	0:10 at MUMLWP	5:15
MUMFORT -MUMLWP-MUMH-PNQHWH	Leg3	MUMH to PNQHWH	02-09-2026 23:15	03-09-2026 02:30	3:15	0:30 at MUMH	5:15
MUMH-NSKH	Leg1	MUMH to NSKH	01-09-2026 05:00	01-09-2026 09:00	4:00	Origin	9:00
NSKH-MUMH	Leg1	NSKH to MUMH	01-09-2026 22:30	02-09-2026 03:00	4:30	Origin	4:30
MUMH-KHPH-PNQLH-PNQHWH-PNQH	Leg1	MUMH to KHPH	01-09-2026 02:30	01-09-2026 03:45	1:15	Origin	9:00
MUMH-KHPH-PNQLH-PNQHWH-PNQH	Leg2	KHPH to PNQLH	01-09-2026 04:00	01-09-2026 04:15	0:15	0:15 at KHPH	9:00
MUMH-KHPH-PNQLH-PNQHWH-PNQH	Leg3	PNQLH to PNQHWH	01-09-2026 04:45	01-09-2026 05:45	1:00	0:30 at PNQLH	9:00
PNQH-PNQBH-PNQPB-PNQLH-KHPH-MUMH	Leg1	PNQH to PNQBH	01-09-2026 22:30	01-09-2026 23:00	0:30	Origin	5:30
PNQH-PNQBH-PNQPB-PNQLH-KHPH-MUMH	Leg2	PNQBH to PNQPB	08-09-2026 23:10	08-09-2026 23:25	0:15	0:10 at PNQBH	5:30
PNQHWH-MUMH	Leg1	PNQHWH to MUMH	01-09-2026 03:00	01-09-2026 06:15	3:15	Origin	6:15
MUMH-VPIH	Leg1	MUMH to VPIH	01-09-2026 05:30	02-09-2026 09:00	27:30	Origin	27:30
VPIH-MUMH	Leg1	VPIH to MUMH	01-09-2026 23:00	02-09-2026 03:30	4:30	Origin	4:30
PNQHWH-MUMSPD	Leg1	PNQHWH to MUMSPD	01-09-2026 05:00	01-09-2026 09:00	4:00	Origin	9:00"""

ALL_PORTAL_MODULES = [
    "📊 Operations Summary",
    "🚚 Vendor Performance",
    "💳 Payment Dashboard",
    "📱 Communication Hub",
    "💰 Network Utilization",
    "📝 Today's Call Action Plan",
    "🧭 Scheduled Route Master",
    "⚠️ Overall Issues",
    "🔐 User & Access Control"
]

STANDARD_MODULES = [m for m in ALL_PORTAL_MODULES if m != "🔐 User & Access Control"]

# Pre-defined National Route Pairs for Communication Hub
NATIONAL_ROUTE_PAIRS = {
    "HYDH-PNQHWH-BWNDLH": ["HYDH-PNQHWH-BWNDLH", "BWNDLH-PNQHWH-HYDH"],
    "PATH-VNS1": ["PATH-VNS1", "VNS1-PATH"],
    "BLRSH-HYDH-NGPLAVA-DELAP": ["BLRSH-HYDH-NGPLAVA-DELAP", "DELAP-NGPLAVA-HYDH-BLRSH"],
    "BWNDLH-PNQHWH-BLRSH-HOSURH-CHIH": ["BWNDLH-PNQHWH-BLRSH-HOSURH-CHIH", "CHIH-HOSURH-BLRSH-PNQHWH-BWNDLH"],
    "BWNDLH-NGPLAVA-RAIH-HOWDG": ["BWNDLH-NGPLAVA-RAIH-HOWDG", "HOWDG-RAIH-NGPLAVA-BWNDLH"],
    "DELAP-PATH-CCUH": ["DELAP-PATH-CCUH", "CCUH-HOWDG-PATH-DELAP"],
    "DELAP-BKLH-BWNDLH": ["DELAP-BKLH-BWNDLH", "BWNDLH-DELAP", "BWNDLH-BKLH-DELAP"],
    "DELAP-JPRH-BKLH": ["DELAP-JPRH-BKLH", "BKLH-JPRH-DELAP"],
    "DELAP-BHOH-INDH": ["DELAP-BHOH-INDH", "INDH-BHOH-GWLH-DELAP"]
}

# Undesirable / Backend columns to strip from final downloaded Excel reports
JUNK_EXCEL_COLS = [
    'Zone', 'VehicleType', 'ReplaceVehicleNo', 'ContractTypeDesc', 'Loaded_wt',
    'MCD_StartYear', 'MCD_StartWeek', 'unloadwt', 'CD_FromBranch_Clean',
    'RPTBranchcode_Clean', 'Route Code_x', 'Route Branch Code_x', 'Dep_Route_Day',
    'Sch_Dep_Time_Raw', 'Route Code', 'Route Branch Code_y', 'Arr_Route_Day',
    'Sch_Arr_Time_Raw', 'Dep_Status', 'Arr_Status', 'Given_Secs', 'Actual_Secs',
    'Given Driving Hours_Raw', 'Actual Driving Hours_Raw', 'Delay Hours_Raw',
    'MCD_StartDate_DT', 'Date_DT', 'Leg_Num', 'E2E_Pair', 'OO_Cnt', 'LO_Cnt',
    'OL_Cnt', 'LL_Cnt', 'Ontime_Dep_IT_Cnt', 'Late_Dep_IT_Cnt', 'Ontime_Cnt',
    'Late_Cnt', 'Transit_Cnt', 'Sort_Pct', 'MergeKey', 'LKP_ROUTE', 'LKP_TYPE',
    'LKP_FROM', 'LKP_TO', 'Final_From', 'Final_To', 'Total_Cap_Raw',
    'Trip_Rate_Str', 'RO Name Clean', 'Late Dep', 'Late Arr', 'Missing',
    'Scheduled TAT Till Destination', 'Actual TAT Till Destination',
    'Overall Remark', 'MCD_EndDate', 'Origin', 'Destination', 'Region',
    'MCD_Created_By', 'RowKey', 'SortKey_Temp', 'Is_Single_Trip'
]

def get_ist_now():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)

# ==========================================
# 2. DYNAMIC USER & ACCESS MANAGEMENT DB
# ==========================================
DEFAULT_USERS_SEED = {
    "admin": {
        "pass": "9211213",
        "role": "Admin",
        "label": "Master Admin",
        "active": True,
        "all_vendors": True,
        "vendors": [],
        "modules": ALL_PORTAL_MODULES
    },
    "admin2": {
        "pass": "1234",
        "role": "Admin",
        "label": "Operations Admin",
        "active": True,
        "all_vendors": True,
        "vendors": [],
        "modules": STANDARD_MODULES
    },
    "user": {
        "pass": "5272",
        "role": "User",
        "label": "Standard User",
        "active": True,
        "all_vendors": True,
        "vendors": [],
        "modules": STANDARD_MODULES
    },
    "EWL": {
        "pass": "1234",
        "role": "Vendor",
        "label": "E Wheels & Logistics",
        "active": True,
        "all_vendors": False,
        "vendors": ["E WHEELS AND LOGISTICS", "AAGFE8904K-E WHEELS AND LOGISTICS"],
        "modules": ["🚚 Vendor Performance"]
    },
    "MRT": {
        "pass": "1234",
        "role": "Vendor",
        "label": "Mehtaroad India Transport",
        "active": True,
        "all_vendors": False,
        "vendors": ["MEHTAROAD INDIA TRANSPORT PRIVATE LIMITED", "MEHTAROAD"],
        "modules": ["🚚 Vendor Performance"]
    },
    "vandna": {
        "pass": "1234",
        "role": "Vendor",
        "label": "Vandna Motors",
        "active": True,
        "all_vendors": False,
        "vendors": ["VANDNA MOTORS", "AAOFV8863G-VANDNA MOTORS"],
        "modules": ["🚚 Vendor Performance"]
    },
    "TEJAS": {
        "pass": "1234",
        "role": "Vendor",
        "label": "Tejas Cargo India Pvt Ltd",
        "active": True,
        "all_vendors": False,
        "vendors": ["TEJAS CARGO INDIA PVT LTD", "TEJAS"],
        "modules": ["🚚 Vendor Performance"]
    }
}

def load_users_db():
    path = FILE_MAP["USERS_DB"]
    db = {}
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                db = json.load(f)
        except Exception:
            db = {}
    
    changed = False
    for u_k, u_v in DEFAULT_USERS_SEED.items():
        if u_k not in db:
            db[u_k] = u_v.copy()
            changed = True
        else:
            # Ensure all required keys exist
            for field_k, field_v in u_v.items():
                if field_k not in db[u_k]:
                    db[u_k][field_k] = field_v
                    changed = True

    # Give the seeded standard accounts access to the newly added default modules
    # when they still have the original standard-module set. Custom permissions stay intact.
    legacy_standard_modules = [
        "📊 Operations Summary", "🚚 Vendor Performance", "💳 Payment Dashboard",
        "📱 Communication Hub", "💰 Network Utilization", "📝 Today's Call Action Plan"
    ]
    for seeded_id in ("admin2", "user"):
        if seeded_id in db and set(db[seeded_id].get("modules", [])) == set(legacy_standard_modules):
            db[seeded_id]["modules"] = STANDARD_MODULES
            changed = True

    # Always guarantee master 'admin' has full access
    db["admin"]["role"] = "Admin"
    db["admin"]["active"] = True
    db["admin"]["all_vendors"] = True
    db["admin"]["modules"] = ALL_PORTAL_MODULES

    if changed or not os.path.exists(path):
        save_users_db(db)
    return db

def save_users_db(db_dict):
    with open(FILE_MAP["USERS_DB"], 'w') as f:
        json.dump(db_dict, f, indent=4)

USERS_DB = load_users_db()

ISSUE_LINK_KEY_PATH = os.path.join(DATA_DIR, ".overall_issues_link_key")

@st.cache_resource(show_spinner=False)
def _get_issue_link_key():
    """Return a private signing key used only for short-lived issue-detail links."""
    try:
        with open(ISSUE_LINK_KEY_PATH, 'rb') as key_file:
            key = key_file.read()
        if len(key) >= 32:
            return key
    except OSError:
        pass
    key = os.urandom(32)
    try:
        with open(ISSUE_LINK_KEY_PATH, 'xb') as key_file:
            key_file.write(key)
        return key
    except FileExistsError:
        with open(ISSUE_LINK_KEY_PATH, 'rb') as key_file:
            return key_file.read()

def create_overall_issue_access_token(username):
    """Create a 15-minute token scoped to the Overall Issues drill-down only."""
    user = USERS_DB.get(username, {})
    if not user or not user.get('active', True):
        return ''
    if username != 'admin' and '⚠️ Overall Issues' not in user.get('modules', []):
        return ''
    now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    cached = st.session_state.get('_overall_issue_link_token')
    if cached and cached[0] == username and cached[1] > now + 60:
        return cached[2]
    payload = json.dumps({
        'user': username,
        'scope': 'overall-issues',
        'expires': now + 900
    }, separators=(',', ':')).encode('utf-8')
    encoded = base64.urlsafe_b64encode(payload).decode('ascii').rstrip('=')
    signature = hmac.new(_get_issue_link_key(), encoded.encode('ascii'), hashlib.sha256).hexdigest()
    token = f'{encoded}.{signature}'
    st.session_state['_overall_issue_link_token'] = (username, now + 900, token)
    return token

def verify_overall_issue_access_token(token):
    if not token or '.' not in token:
        return None
    encoded, supplied_signature = token.rsplit('.', 1)
    expected_signature = hmac.new(_get_issue_link_key(), encoded.encode('ascii'), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(supplied_signature, expected_signature):
        return None
    try:
        padded = encoded + ('=' * (-len(encoded) % 4))
        payload = json.loads(base64.urlsafe_b64decode(padded.encode('ascii')).decode('utf-8'))
        username = str(payload.get('user', ''))
        user = USERS_DB.get(username, {})
        now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        if payload.get('scope') != 'overall-issues' or int(payload.get('expires', 0)) < now:
            return None
        if not user or not user.get('active', True):
            return None
        if username != 'admin' and '⚠️ Overall Issues' not in user.get('modules', []):
            return None
        return username
    except Exception:
        return None

def create_ops_remark_access_token(username):
    """Create a 15-minute signed token scoped to Operations Summary Remark raw drill-down."""
    user = USERS_DB.get(username, {})
    if not user or not user.get('active', True):
        return ''
    if username != 'admin' and '📊 Operations Summary' not in user.get('modules', []):
        return ''
    now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    cached = st.session_state.get('_ops_remark_link_token')
    if cached and cached[0] == username and cached[1] > now + 60:
        return cached[2]
    payload = json.dumps({
        'user': username,
        'scope': 'ops-remark-raw',
        'expires': now + 900
    }, separators=(',', ':')).encode('utf-8')
    encoded = base64.urlsafe_b64encode(payload).decode('ascii').rstrip('=')
    signature = hmac.new(_get_issue_link_key(), encoded.encode('ascii'), hashlib.sha256).hexdigest()
    token = f'{encoded}.{signature}'
    st.session_state['_ops_remark_link_token'] = (username, now + 900, token)
    return token

def verify_ops_remark_access_token(token):
    if not token or '.' not in token:
        return None
    encoded, supplied_signature = token.rsplit('.', 1)
    expected_signature = hmac.new(_get_issue_link_key(), encoded.encode('ascii'), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(supplied_signature, expected_signature):
        return None
    try:
        padded = encoded + ('=' * (-len(encoded) % 4))
        payload = json.loads(base64.urlsafe_b64decode(padded.encode('ascii')).decode('utf-8'))
        username = str(payload.get('user', ''))
        user = USERS_DB.get(username, {})
        now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        if payload.get('scope') != 'ops-remark-raw' or int(payload.get('expires', 0)) < now:
            return None
        if not user or not user.get('active', True):
            return None
        if username != 'admin' and '📊 Operations Summary' not in user.get('modules', []):
            return None
        return username
    except Exception:
        return None

def create_vendor_perf_access_token(username):
    """Create a 15-minute signed token scoped to Vendor Performance raw drill-down."""
    user = USERS_DB.get(username, {})
    if not user or not user.get('active', True):
        return ''
    if username != 'admin' and '🚚 Vendor Performance' not in user.get('modules', []):
        return ''
    now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    cached = st.session_state.get('_ven_perf_link_token')
    if cached and cached[0] == username and cached[1] > now + 60:
        return cached[2]
    payload = json.dumps({
        'user': username,
        'scope': 'ven-perf-raw',
        'expires': now + 900
    }, separators=(',', ':')).encode('utf-8')
    encoded = base64.urlsafe_b64encode(payload).decode('ascii').rstrip('=')
    signature = hmac.new(_get_issue_link_key(), encoded.encode('ascii'), hashlib.sha256).hexdigest()
    token = f'{encoded}.{signature}'
    st.session_state['_ven_perf_link_token'] = (username, now + 900, token)
    return token

def verify_vendor_perf_access_token(token):
    if not token or '.' not in token:
        return None
    encoded, supplied_signature = token.rsplit('.', 1)
    expected_signature = hmac.new(_get_issue_link_key(), encoded.encode('ascii'), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(supplied_signature, expected_signature):
        return None
    try:
        padded = encoded + ('=' * (-len(encoded) % 4))
        payload = json.loads(base64.urlsafe_b64decode(padded.encode('ascii')).decode('utf-8'))
        username = str(payload.get('user', ''))
        user = USERS_DB.get(username, {})
        now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        if payload.get('scope') != 'ven-perf-raw' or int(payload.get('expires', 0)) < now:
            return None
        if not user or not user.get('active', True):
            return None
        if username != 'admin' and '🚚 Vendor Performance' not in user.get('modules', []):
            return None
        return username
    except Exception:
        return None

def rotate_overall_issue_link_key():
    """Revoke already-issued drill-down links when the user logs out."""
    try:
        with open(ISSUE_LINK_KEY_PATH, 'wb') as key_file:
            key_file.write(os.urandom(32))
        _get_issue_link_key.clear()
        st.session_state.pop('_overall_issue_link_token', None)
        st.session_state.pop('_ops_remark_link_token', None)
        st.session_state.pop('_ven_perf_link_token', None)
    except OSError:
        logging.warning('Could not rotate Overall Issues link key during logout.')

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'role' not in st.session_state:
    st.session_state['role'] = None
if 'username' not in st.session_state:
    st.session_state['username'] = None
if 'allowed_vendors' not in st.session_state:
    st.session_state['allowed_vendors'] = []
if 'all_vendors' not in st.session_state:
    st.session_state['all_vendors'] = True
if 'allowed_modules' not in st.session_state:
    st.session_state['allowed_modules'] = []

# A signed, expiring link lets a logged-in user open Overall Issues details in a
# new tab without sharing their password or disabling the portal's login check.
try:
    early_params = st.query_params
    incoming_raw_flag = str(early_params.get('issues_raw', ''))
    incoming_issue_token = str(early_params.get('issues_auth', ''))
    incoming_ops_raw_flag = str(early_params.get('ops_raw', ''))
    incoming_ops_token = str(early_params.get('ops_auth', ''))
    incoming_ven_raw_flag = str(early_params.get('ven_raw', ''))
    incoming_ven_token = str(early_params.get('ven_auth', ''))
except Exception:
    try:
        early_params = st.experimental_get_query_params()
        incoming_raw_flag = str((early_params.get('issues_raw') or [''])[0])
        incoming_issue_token = str((early_params.get('issues_auth') or [''])[0])
        incoming_ops_raw_flag = str((early_params.get('ops_raw') or [''])[0])
        incoming_ops_token = str((early_params.get('ops_auth') or [''])[0])
        incoming_ven_raw_flag = str((early_params.get('ven_raw') or [''])[0])
        incoming_ven_token = str((early_params.get('ven_auth') or [''])[0])
    except Exception:
        incoming_raw_flag, incoming_issue_token = '', ''
        incoming_ops_raw_flag, incoming_ops_token = '', ''
        incoming_ven_raw_flag, incoming_ven_token = '', ''
if not st.session_state['logged_in']:
    token_user = None
    if incoming_raw_flag == '1':
        token_user = verify_overall_issue_access_token(incoming_issue_token)
    elif incoming_ops_raw_flag == '1':
        token_user = verify_ops_remark_access_token(incoming_ops_token)
    elif incoming_ven_raw_flag == '1':
        token_user = verify_vendor_perf_access_token(incoming_ven_token)
    if token_user:
        token_user_data = USERS_DB[token_user]
        st.session_state['logged_in'] = True
        st.session_state['username'] = token_user
        st.session_state['role'] = token_user_data.get('role', 'User')
        st.session_state['all_vendors'] = token_user_data.get('all_vendors', True)
        st.session_state['allowed_vendors'] = token_user_data.get('vendors', [])
        st.session_state['allowed_modules'] = token_user_data.get('modules', STANDARD_MODULES)
        st.session_state['user_label'] = token_user_data.get('label', token_user)

if not st.session_state['logged_in']:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: #60A5FA; font-size: 3rem;'>🚀 Trackon Command Center</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #94A3B8; font-weight: 400;'>Enterprise Logistics & Fleet Operations Portal</h3>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        with st.form("login_form"):
            st.markdown("#### 🔒 Secure Access")
            username_in = st.text_input("Username").strip()
            password_in = st.text_input("Password", type="password").strip()
            submit = st.form_submit_button("Authenticate", use_container_width=True)
            
            if submit:
                USERS_DB = load_users_db()
                matched_user = None
                for u_key, u_info in USERS_DB.items():
                    if u_key.lower() == username_in.lower() and str(u_info.get("pass", "")) == password_in:
                        matched_user = (u_key, u_info)
                        break
                
                if matched_user:
                    u_id, u_data = matched_user
                    if not u_data.get("active", True):
                        st.error("🚫 Your account has been disabled by the Administrator.")
                    else:
                        st.session_state['logged_in'] = True
                        st.session_state['username'] = u_id
                        st.session_state['role'] = u_data.get('role', 'User')
                        st.session_state['all_vendors'] = u_data.get('all_vendors', True)
                        st.session_state['allowed_vendors'] = u_data.get('vendors', [])
                        st.session_state['allowed_modules'] = u_data.get('modules', STANDARD_MODULES)
                        st.session_state['user_label'] = u_data.get('label', u_id)
                        st.rerun()
                else:
                    st.error("❌ Invalid Credentials. Access Denied.")
    st.stop()

# Refresh live session permissions from DB on each run so Admin edits apply immediately
curr_u = st.session_state.get('username')
if curr_u and curr_u in USERS_DB:
    if not USERS_DB[curr_u].get('active', True) and curr_u != 'admin':
        st.session_state['logged_in'] = False
        st.rerun()
    st.session_state['role'] = USERS_DB[curr_u].get('role', 'User')
    st.session_state['all_vendors'] = USERS_DB[curr_u].get('all_vendors', True)
    st.session_state['allowed_vendors'] = USERS_DB[curr_u].get('vendors', [])
    st.session_state['allowed_modules'] = USERS_DB[curr_u].get('modules', STANDARD_MODULES)
    st.session_state['user_label'] = USERS_DB[curr_u].get('label', curr_u)

# ==========================================
# 3. HELPER FUNCTIONS & VENDOR NORMALIZATION
# ==========================================
def normalize_vendor_name(val):
    """
    Combines duplicate vendor names with PAN prefixes (like AAGFE8904K-E WHEELS AND LOGISTICS
    and E WHEELS AND LOGISTICS) into a single clean canonical vendor name.
    """
    if pd.isna(val):
        return ""
    s = str(val).strip().upper()
    if s in ["", "NAN", "NONE"]:
        return ""
    s = re.sub(r'^[A-Z]{5}[0-9]{4}[A-Z]\s*-\s*', '', s).strip()
    if "E WHEELS" in s:
        return "E WHEELS AND LOGISTICS"
    if "VANDNA MOTORS" in s:
        return "VANDNA MOTORS"
    if "MEHTAROAD" in s:
        return "MEHTAROAD INDIA TRANSPORT PRIVATE LIMITED"
    if "TEJAS CARGO" in s:
        return "TEJAS CARGO INDIA PVT LTD"
    return s

@st.cache_data(show_spinner=False, max_entries=8)
def normalize_vendor_column_cached(frame, column):
    """Normalize repeated vendor labels once per workbook version/frame."""
    result = frame.copy()
    if column in result.columns and not result.empty:
        source = result[column].fillna('').astype(str)
        mapping = {value: normalize_vendor_name(value) for value in source.unique()}
        result[column] = source.map(mapping)
    return result

def filter_df_by_user_vendors(df, vendor_col):
    """Filters any DataFrame by the logged-in user's allowed vendors if restricted."""
    if df is None or df.empty or vendor_col not in df.columns:
        return df
    if st.session_state.get('all_vendors', True):
        return df
    allowed_raw = st.session_state.get('allowed_vendors', [])
    if not allowed_raw:
        return df.iloc[0:0].copy()
    allowed_norm = [normalize_vendor_name(v) for v in allowed_raw if v]
    allowed_norm = list(dict.fromkeys([v for v in allowed_norm if v]))
    vendor_text = df[vendor_col].fillna('').astype(str)
    vendor_map = {value: normalize_vendor_name(value) for value in vendor_text.unique()}
    normalized_vendors = vendor_text.map(vendor_map)
    match_map = {
        vendor_name: any(allowed in vendor_name or vendor_name in allowed for allowed in allowed_norm if vendor_name)
        for vendor_name in normalized_vendors.unique()
    }
    mask = normalized_vendors.map(match_map)
    return df[mask].copy()

def save_file(uploaded_file, key):
    if uploaded_file is None:
        return False
    buffer = uploaded_file.getbuffer()
    digest = hashlib.sha256(buffer).hexdigest()
    state_key = f"saved_upload_{key}"
    path = FILE_MAP[key]
    if st.session_state.get(state_key) == digest and os.path.exists(path):
        return False
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(dir=DATA_DIR, suffix='.xlsx', delete=False) as f:
            temp_path = f.name
            f.write(buffer)
        os.replace(temp_path, path)
        st.session_state[state_key] = digest
        return True
    except Exception as exc:
        st.error(f"Could not save {key}: {exc}")
        return False
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

def get_file_time(key):
    path = FILE_MAP[key]
    if os.path.exists(path):
        ts = os.path.getmtime(path)
        return datetime.datetime.fromtimestamp(ts).strftime('%d %b %Y, %I:%M %p')
    return "Not Uploaded Yet ❌"

def _fast_excel_engine():
    try:
        import python_calamine  # noqa: F401
        return 'calamine'
    except Exception:
        return 'openpyxl'

def _read_excel_fast(path, sheet_name=0):
    eng = _fast_excel_engine()
    try:
        return pd.read_excel(path, sheet_name=sheet_name, engine=eng)
    except Exception:
        return pd.read_excel(path, sheet_name=sheet_name, engine='openpyxl')

def file_version(path):
    stat = os.stat(path)
    return (stat.st_mtime_ns, stat.st_size)

NEEDED_PAYMENT_COLS_LOWER = {
    'invoice id', 'invoiceid', 'invoice id no', 'invoice no',
    'invoice date', 'invoicedate',
    'submitted at', 'submittedat',
    'ro name', 'ro_selection', 'roselection', 'ro',
    'vendor name', 'vendorname',
    'category', 'bill category',
    'amount', 'net payable', 'net_payable',
    'status', 'invoice status',
    'pending with', 'pendingwith',
    'name', 'bill uploader', 'uploader name', 'uploadername',
    'finance name', 'financename',
    'last approved at', 'lastapprovedat',
    'finance revert remarks 1', 'financerevertremarks1',
    'approver revert remarks', 'approverrevertremarks',
    'hold.name', 'hold name', 'holdname',
    'hold-key', 'hold key', 'holdkey',
    'hold.time', 'hold time', 'holdtime',
    'approver_1_reverted_action', 'approver_2_reverted_action',
    'approver_3_reverted_action', 'approver_4_reverted_action',
    'approver_5_reverted_action',
    'partial payment', 'partialpayment',
    'balance payable amount', 'balancepayableamount',
    'branch_name', 'branch name', 'branch',
    'state_name', 'state name', 'state'
}

def _fast_read_xlsx_sheet_xml(path, preferred_sheet=None, needed_cols_lower=None):
    """Streaming stdlib XML XLSX reader: 2.5x faster & 5x less RAM than openpyxl on large files."""
    with zipfile.ZipFile(path, 'r') as zf:
        names = set(zf.namelist())
        shared_strings = []
        if 'xl/sharedStrings.xml' in names:
            with zf.open('xl/sharedStrings.xml') as ss_f:
                for _, elem in ET.iterparse(ss_f, events=('end',)):
                    if elem.tag.endswith('}si') or elem.tag == 'si':
                        shared_strings.append(''.join(t.text or '' for t in elem.iter() if t.tag.endswith('}t') or t.tag == 't'))
                        elem.clear()

        wb_xml = ET.fromstring(zf.read('xl/workbook.xml'))
        rels_xml = ET.fromstring(zf.read('xl/_rels/workbook.xml.rels'))
        rel_map = {}
        for rel in rels_xml:
            rid = rel.attrib.get('Id')
            target = rel.attrib.get('Target', '')
            if rid and target:
                rel_map[rid] = target.lstrip('/') if target.startswith('/') else ('xl/' + target if not target.startswith('xl/') else target)

        sheets_list = []
        for sh in wb_xml.iter():
            if sh.tag.endswith('}sheet') or sh.tag == 'sheet':
                s_name = sh.attrib.get('name', '')
                rid = next((v for k, v in sh.attrib.items() if k.endswith('}id') or k == 'r:id'), None)
                if rid in rel_map:
                    sheets_list.append((s_name, rel_map[rid]))

        target_path = None
        if preferred_sheet:
            for s_name, s_path in sheets_list:
                if s_name.lower() == preferred_sheet.lower():
                    target_path = s_path
                    break
        if not target_path and sheets_list:
            target_path = sheets_list[0][1]
        if not target_path or target_path not in names:
            return pd.DataFrame()

        def col_idx(ref):
            idx = 0
            for ch in ref:
                if 'A' <= ch <= 'Z':
                    idx = idx * 26 + (ord(ch) - 64)
                else:
                    break
            return idx - 1

        header = None
        keep_idx_set = None
        keep_idx_order = None
        keep_names = None
        rows_out = []

        with zf.open(target_path) as sh_f:
            for _, elem in ET.iterparse(sh_f, events=('end',)):
                if elem.tag.endswith('}row') or elem.tag == 'row':
                    row_dict = {}
                    for c in elem:
                        r_attr = c.attrib.get('r', '')
                        ci = col_idx(r_attr) if r_attr else len(row_dict)
                        if keep_idx_set is not None and ci not in keep_idx_set:
                            continue
                        t_attr = c.attrib.get('t', '')
                        val = None
                        if t_attr == 's':
                            for child in c:
                                if child.tag.endswith('}v') or child.tag == 'v':
                                    if child.text is not None:
                                        s_i = int(child.text)
                                        if 0 <= s_i < len(shared_strings):
                                            val = shared_strings[s_i]
                                    break
                        elif t_attr == 'inlineStr':
                            val = ''.join(t.text or '' for t in c.iter() if t.tag.endswith('}t') or t.tag == 't')
                        else:
                            for child in c:
                                if child.tag.endswith('}v') or child.tag == 'v':
                                    val = child.text
                                    break
                        row_dict[ci] = val
                    elem.clear()
                    if header is None:
                        max_c = max(row_dict.keys()) + 1 if row_dict else 0
                        header = [str(row_dict.get(i, '') or '').strip() for i in range(max_c)]
                        if needed_cols_lower is not None:
                            keep_idx_order = [i for i, h in enumerate(header) if h.lower() in needed_cols_lower]
                            keep_idx_set = set(keep_idx_order)
                            keep_names = [header[i] for i in keep_idx_order]
                        else:
                            keep_idx_order = list(range(len(header)))
                            keep_idx_set = set(keep_idx_order)
                            keep_names = header
                    else:
                        rows_out.append([row_dict.get(i) for i in keep_idx_order])

        return pd.DataFrame(rows_out, columns=keep_names)

def _load_disk_pkl_cache(cache_path, expected_sig):
    try:
        if os.path.exists(cache_path):
            with open(cache_path, 'rb') as f:
                payload = pickle.load(f)
            if isinstance(payload, tuple) and len(payload) == 2 and payload[0] == expected_sig:
                return payload[1]
    except Exception:
        pass
    return None

def _save_disk_pkl_cache(cache_path, sig, obj):
    tmp_p = None
    try:
        with tempfile.NamedTemporaryFile(dir=os.path.dirname(cache_path), suffix='.pkl', delete=False) as tf:
            tmp_p = tf.name
            pickle.dump((sig, obj), tf, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(tmp_p, cache_path)
    except Exception:
        if tmp_p and os.path.exists(tmp_p):
            try:
                os.remove(tmp_p)
            except Exception:
                pass


def read_payment_sheet_cached(path, signature, sheet_name):
    try:
        import python_calamine  # noqa: F401
        with pd.ExcelFile(path, engine='calamine') as workbook:
            selected_sheet = sheet_name if sheet_name in workbook.sheet_names else workbook.sheet_names[0]
            return workbook.parse(selected_sheet)
    except Exception:
        pass
    try:
        df_xml = _fast_read_xlsx_sheet_xml(path, preferred_sheet=sheet_name, needed_cols_lower=NEEDED_PAYMENT_COLS_LOWER)
        if not df_xml.empty:
            return df_xml
    except Exception as exc:
        logging.warning(f"Fast XML payment read fallback to openpyxl: {exc}")
    with pd.ExcelFile(path, engine='openpyxl') as workbook:
        selected_sheet = sheet_name if sheet_name in workbook.sheet_names else workbook.sheet_names[0]
        return workbook.parse(selected_sheet)


def get_col(df, possible_names):
    col_map = {str(c).replace(' ', '').replace('_', '').lower(): c for c in df.columns}
    for n in possible_names:
        clean_n = n.replace(' ', '').replace('_', '').lower()
        if clean_n in col_map:
            return col_map[clean_n]
    return None

def format_hrs_safe(hrs):
    if pd.isna(hrs):
        return ""
    sign = "-" if hrs < 0 else ""
    hrs = abs(hrs)
    h = int(hrs)
    m = int(round((hrs - h) * 60))
    if m == 60:
        h += 1
        m = 0
    return f"{sign}{h}:{m:02d}"

def extract_orig_dest(route_str):
    s = str(route_str).upper()
    parts = s.replace(' TO ', '-').split('-')
    if len(parts) >= 2:
        return parts[0].strip(), parts[-1].strip()
    return s.strip(), s.strip()

def get_route_pair(route_str):
    o, d = extract_orig_dest(route_str)
    return f"{min(o, d)}-{max(o, d)}"

def extract_leg_num_val(series):
    return series.astype(str).str.extract(r'(\d+)')[0].astype(float).fillna(999)

def sort_by_route_and_leg(df):
    if df is None or df.empty:
        return df
    df_out = df.copy()
    sort_cols = []
    if 'Route Path' in df_out.columns:
        sort_cols.append('Route Path')
    elif 'Route' in df_out.columns:
        sort_cols.append('Route')
    elif 'Route (UP/DOWN)' in df_out.columns:
        sort_cols.append('Route (UP/DOWN)')
        
    if 'Legwise' in df_out.columns:
        df_out['_leg_sort_num_'] = extract_leg_num_val(df_out['Legwise'])
        sort_cols.append('_leg_sort_num_')
        sort_cols.append('Legwise')
        
    if 'VendorName' in df_out.columns:
        sort_cols.append('VendorName')
        
    if 'Date' in df_out.columns:
        sort_cols.append('Date')
    elif 'MCD_StartDate' in df_out.columns:
        sort_cols.append('MCD_StartDate')
        
    if sort_cols:
        df_out = df_out.sort_values(by=sort_cols, ascending=True)
    if '_leg_sort_num_' in df_out.columns:
        df_out.drop(columns=['_leg_sort_num_'], inplace=True, errors='ignore')
    return df_out

def time_to_hrs(t):
    if pd.isna(t):
        return np.nan
    t_str = str(t).strip()
    if t_str.lower() in ['', 'nan', 'nat']:
        return np.nan
    if hasattr(t, 'hour'):
        return t.hour + t.minute / 60.0
    if ':' in t_str:
        parts = t_str.split(':')
        if len(parts) >= 2:
            try:
                return float(parts[0]) + float(parts[1]) / 60.0
            except:
                return np.nan
    try:
        return float(t_str)
    except:
        return np.nan

def get_day_offset(day_val):
    try:
        if pd.isna(day_val):
            return np.nan
        return float(day_val) * 24
    except:
        return np.nan

def format_pct_cnt(count, total):
    if total == 0 or pd.isna(total):
        return "0.0% (0)"
    pct = (count / total) * 100
    return f"{pct:.1f}% ({int(count)})"

def format_ops_badge(x):
    if isinstance(x, str) and '%' in x and '(' in x:
        try:
            pct = x.split('%')[0].strip() + '%'
            count = x.split('(')[1].replace(')', '').strip()
            if count == '0':
                return "0%"
            return f"{pct} | 🚚 {count}"
        except:
            return x
    return x

def parse_pct_from_str(val):
    if isinstance(val, (int, float)) and not pd.isna(val):
        return float(val)
    if not isinstance(val, str) or '%' not in val:
        return None
    try:
        matches = re.findall(r'(-?\d+(?:\.\d+)?)\s*%', val)
        return float(matches[-1]) if matches else None
    except:
        return None

def load_action_plans():
    path = FILE_MAP["ACTION_PLANS"]
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_action_plans(data):
    with open(FILE_MAP["ACTION_PLANS"], 'w') as f:
        json.dump(data, f)

def _lookup_key(value):
    if pd.isna(value):
        return ''
    return re.sub(r'[^A-Z0-9]+', '', str(value).replace('\u00a0', ' ').strip().upper())

def get_route_excel_sources():
    """Return uploaded Excel workbooks in lookup-first order, including extra uploaded files."""
    sources = []
    seen_paths = set()
    preferred_keys = ['BRANCH_MASTER', 'LEGWISE', 'MCD_VENDOR', 'ROUTE_MASTER', 'PAYMENT', 'CPK_UTIL', 'ROUTE_LOOKUP']
    for key in preferred_keys:
        path = FILE_MAP.get(key)
        if path and os.path.exists(path) and path.lower().endswith(('.xlsx', '.xlsm', '.xls')):
            normalized_path = os.path.normcase(os.path.abspath(path))
            if normalized_path not in seen_paths:
                sources.append((key, path))
                seen_paths.add(normalized_path)
    try:
        for filename in sorted(os.listdir(DATA_DIR)):
            path = os.path.join(DATA_DIR, filename)
            if not os.path.isfile(path) or not path.lower().endswith(('.xlsx', '.xlsm', '.xls')):
                continue
            normalized_path = os.path.normcase(os.path.abspath(path))
            if normalized_path not in seen_paths:
                sources.append((os.path.splitext(filename)[0], path))
                seen_paths.add(normalized_path)
    except Exception as exc:
        logging.warning(f"Uploaded workbook discovery warning: {exc}")
    return sources

def get_route_lookup_signature():
    signature = []
    for key, path in get_route_excel_sources():
        if os.path.exists(path):
            stat = os.stat(path)
            signature.append((key, stat.st_mtime_ns, stat.st_size))
    return tuple(signature)

@st.cache_data(show_spinner=False)
def get_route_branch_lookup_data(file_signature):
    """Read branch-to-RO labels and discover OnDemand Origin/Destination mappings."""
    branch_by_code = {}
    branch_by_name = {}
    ondemand_by_route = {}
    ondemand_by_pair = {}
    branch_source = ''
    ondemand_source = ''

    def find_column(frame, candidates):
        normalized = {_lookup_key(col): col for col in frame.columns}
        for candidate in candidates:
            match = normalized.get(_lookup_key(candidate))
            if match is not None:
                return match
        return None

    for source_key, branch_path in get_route_excel_sources():
        try:
            workbook = pd.ExcelFile(branch_path)
            for sheet_name in workbook.sheet_names:
                branches = workbook.parse(sheet_name)
                branches.columns = branches.columns.astype(str).str.strip()
                code_col = find_column(branches, ['RPTBranchcode', 'BranchCode', 'Branch Code', 'Route Branch Code'])
                ro_col = find_column(branches, ['RPTRO', 'RPTROCode', 'RO Name', 'RO Code', 'RO', 'Regional Office', 'Regional Office Name', 'RO Description'])
                if not code_col or not ro_col:
                    continue
                name_col = find_column(branches, [
                    'RPTBranchName', 'RPTBranchDescription', 'RPTBranchDesc',
                    'BranchName', 'Branch Name', 'Branch Description', 'Branch Desc', 'Branch Long Name', 'Branch Short Name'
                ])
                for _, row in branches.iterrows():
                    code = _lookup_key(row.get(code_col, ''))
                    if not code:
                        continue
                    branch_name = str(row.get(name_col, '')).strip() if name_col else ''
                    ro_name = str(row.get(ro_col, '')).strip() if ro_col else ''
                    if branch_name.lower() in ('nan', 'none'):
                        branch_name = ''
                    if ro_name.lower() in ('nan', 'none'):
                        ro_name = ''
                    record = {'code': str(row.get(code_col, '')).strip(), 'name': branch_name, 'ro': ro_name}
                    branch_by_code[code] = record
                    if branch_name:
                        branch_by_name[_lookup_key(branch_name)] = record
                source_label = 'RO & Branch List' if source_key == 'BRANCH_MASTER' else source_key
                branch_source = f"{source_label} · {sheet_name}"
                break
            if branch_source:
                break
        except Exception as exc:
            logging.warning(f"Branch-list lookup warning: {exc}")

    for key, path in get_route_excel_sources():
        try:
            workbook = pd.ExcelFile(path)
            ondemand_sheets = [
                name for name in workbook.sheet_names
                if 'ONDEMAND' in _lookup_key(name)
            ]
            for sheet_name in ondemand_sheets:
                frame = workbook.parse(sheet_name)
                frame.columns = frame.columns.astype(str).str.strip()
                origin_col = find_column(frame, [
                    'Origin', 'Origin Branch', 'Origin Branch Code', 'OriginBranchCode',
                    'From Branch', 'From Branch Code', 'FromBranch'
                ])
                destination_col = find_column(frame, [
                    'Destination', 'Destination Branch', 'Destination Branch Code', 'DestinationBranchCode',
                    'Dest', 'Dest Branch', 'Dest Branch Code', 'To Branch', 'To Branch Code', 'ToBranch'
                ])
                route_col = find_column(frame, ['Route Path', 'RoutePath', 'Route', 'Route Name'])
                leg_col = find_column(frame, ['Legwise', 'Leg', 'Leg No', 'Leg Number', 'Leg Name'])
                leg_path_col = find_column(frame, ['Legs', 'Leg Path', 'Leg Route', 'Leg Description'])
                if not origin_col or not destination_col:
                    continue
                for _, row in frame.iterrows():
                    origin = str(row.get(origin_col, '')).strip()
                    destination = str(row.get(destination_col, '')).strip()
                    origin_key, destination_key = _lookup_key(origin), _lookup_key(destination)
                    if not origin_key or not destination_key or origin_key in ('NAN', 'NONE') or destination_key in ('NAN', 'NONE'):
                        continue
                    ondemand_by_pair.setdefault((origin_key, destination_key), (origin, destination))
                    if route_col:
                        route_key = _lookup_key(row.get(route_col, ''))
                        if route_key:
                            ondemand_by_route.setdefault(route_key, (origin, destination))
                            for leg_identifier_col in [leg_col, leg_path_col]:
                                if leg_identifier_col:
                                    leg_identifier = _lookup_key(row.get(leg_identifier_col, ''))
                                    if leg_identifier:
                                        ondemand_by_route.setdefault(route_key + leg_identifier, (origin, destination))
                ondemand_source = f"{key} · {sheet_name}"
                break
            if ondemand_source:
                break
        except Exception as exc:
            logging.warning(f"OnDemand lookup warning in {key}: {exc}")

    return branch_by_code, branch_by_name, ondemand_by_route, ondemand_by_pair, branch_source, ondemand_source

@st.cache_data(show_spinner=False)
def get_scheduled_route_master(file_signature=()):
    """Build the route-leg view from the same RoutePathReportModel used by processing."""
    output_cols = [
        'Route Code', 'RO', 'Origin', 'Origin Branch', 'Destination',
        'Destination Branch', 'Destination RO', 'Route Path', 'Legwise', 'Legs',
        'From Branch', 'To Branch', 'Departure Route Day', 'Scheduled Departure Time',
        'Arrival Route Day', 'Scheduled Arrival Time', 'Scheduled Driving Hours',
        'Scheduled Halting', 'Scheduled TAT Till Destination'
    ]
    try:
        schedule_path = FILE_MAP.get('ROUTE_MASTER', '')
        if not schedule_path or not os.path.exists(schedule_path):
            df = pd.read_csv(io.StringIO(SCHEDULED_ROUTE_MASTER_TSV), sep='\t', dtype=str, keep_default_na=False)
            df.columns = df.columns.astype(str).str.strip()
            df['Route Code'] = ''
            df['Departure Route Day'] = ''
            df['Arrival Route Day'] = ''
            endpoints = df['Legs'].astype(str).str.split(r'\s+to\s+', n=1, expand=True)
            df['From Branch'] = endpoints[0].fillna('').str.strip()
            df['To Branch'] = endpoints[1].fillna('').str.strip() if 1 in endpoints.columns else ''
            df['Scheduled Driving Hours'] = df.get('Given Driving Hours', pd.Series('', index=df.index)).replace('', '-')
            schedule_source = 'Bundled fallback schedule (upload the current National and Zonal workbook)'
        else:
            with pd.ExcelFile(schedule_path, engine='openpyxl') as workbook:
                sheet_name = next(
                    (name for name in workbook.sheet_names if _lookup_key(name) == 'ROUTEPATHREPORTMODEL'),
                    workbook.sheet_names[0]
                )
                source = workbook.parse(sheet_name, dtype=str)
            source.columns = source.columns.astype(str).str.replace('\u00a0', ' ', regex=False).str.strip()

            column_map = {
                'Route Code': get_col(source, ['Route Code']),
                'Route Path': get_col(source, ['Route Path']),
                'Route No': get_col(source, ['Route No', 'Route Number']),
                'Route Branch Code': get_col(source, ['Route Branch Code', 'Branch Code']),
                'Route Day': get_col(source, ['Route Day']),
                'Schedule Departure Time': get_col(source, ['Schedule Departure Time', 'Scheduled Departure Time']),
                'Schedule Arrival Time': get_col(source, ['Schedule Arrival Time', 'Scheduled Arrival Time'])
            }
            missing_columns = [name for name, col in column_map.items() if col is None]
            if missing_columns:
                raise ValueError(f"RoutePathReportModel is missing required columns: {', '.join(missing_columns)}")

            route_rows = pd.DataFrame({
                name: source[col].fillna('').astype(str).str.replace('\u00a0', ' ', regex=False).str.strip()
                for name, col in column_map.items()
            })
            route_rows['_row_order'] = np.arange(len(route_rows))
            route_rows['_route_no_num'] = pd.to_numeric(route_rows['Route No'], errors='coerce')
            route_rows['_route_day_num'] = pd.to_numeric(route_rows['Route Day'], errors='coerce')
            route_rows['_dep_hours'] = route_rows['Schedule Departure Time'].map(time_to_hrs)
            route_rows['_arr_hours'] = route_rows['Schedule Arrival Time'].map(time_to_hrs)
            route_rows['_dep_abs'] = route_rows['_route_day_num'].map(get_day_offset) + route_rows['_dep_hours']
            route_rows['_arr_abs'] = route_rows['_route_day_num'].map(get_day_offset) + route_rows['_arr_hours']

            # Match the existing Vendor Performance TAT calculation exactly:
            # max scheduled arrival minus min scheduled departure per Route Code.
            route_tat = route_rows.groupby('Route Code').agg(
                _min_dep=('_dep_abs', 'min'), _max_arr=('_arr_abs', 'max')
            )
            route_tat['_tat'] = route_tat['_max_arr'] - route_tat['_min_dep']
            tat_by_route = route_tat['_tat'].map(format_hrs_safe).to_dict()

            def clock_label(value):
                text = str(value).strip()
                if not text or text.lower() in ('nan', 'nat', 'none'):
                    return '-'
                match = re.match(r'^(-?\d+):(\d{1,2})', text)
                if match:
                    return f"{int(match.group(1)):02d}:{int(match.group(2)):02d}"
                hours = time_to_hrs(value)
                return format_hrs_safe(hours) if not pd.isna(hours) else text

            def route_day_label(value):
                day = pd.to_numeric(value, errors='coerce')
                return f"Day {int(day)}" if not pd.isna(day) else '-'

            schedule_rows = []
            route_groups = route_rows[route_rows['Route Code'].ne('')].groupby('Route Code', sort=False)
            for route_code, group in route_groups:
                group = group.sort_values(['_route_no_num', '_row_order'], kind='mergesort', na_position='last').reset_index(drop=True)
                if len(group) < 2:
                    continue
                for leg_index in range(len(group) - 1):
                    origin_row = group.iloc[leg_index]
                    destination_row = group.iloc[leg_index + 1]
                    origin_code = origin_row['Route Branch Code']
                    destination_code = destination_row['Route Branch Code']
                    if not origin_code or not destination_code:
                        continue
                    driving_hours = destination_row['_arr_abs'] - origin_row['_dep_abs']
                    if leg_index == 0:
                        halting = 'Origin'
                    else:
                        halt_hours = origin_row['_dep_hours'] - origin_row['_arr_hours']
                        halting = f"{format_hrs_safe(halt_hours)} at {origin_code}" if not pd.isna(halt_hours) else '-'
                    schedule_rows.append({
                        'Route Code': route_code,
                        'Route Path': origin_row['Route Path'],
                        'Legwise': f"Leg{leg_index + 1}",
                        'Legs': f"{origin_code} to {destination_code}",
                        'From Branch': origin_code,
                        'To Branch': destination_code,
                        'Departure Route Day': route_day_label(origin_row['_route_day_num']),
                        'Scheduled Departure Time': clock_label(origin_row['Schedule Departure Time']),
                        'Arrival Route Day': route_day_label(destination_row['_route_day_num']),
                        'Scheduled Arrival Time': clock_label(destination_row['Schedule Arrival Time']),
                        'Scheduled Driving Hours': format_hrs_safe(driving_hours),
                        'Scheduled Halting': halting,
                        'Scheduled TAT Till Destination': tat_by_route.get(route_code, '-') or '-'
                    })
            df = pd.DataFrame(schedule_rows)
            schedule_source = f"{os.path.basename(schedule_path)} · {sheet_name} · {len(df):,} derived route legs"

        for col in output_cols:
            if col not in df.columns:
                df[col] = ''
        df['Origin'] = df['From Branch'].fillna('').astype(str).str.strip()
        df['Destination'] = df['To Branch'].fillna('').astype(str).str.strip()

        file_signature = file_signature or get_route_lookup_signature()
        branch_by_code, branch_by_name, _, _, branch_source, _ = get_route_branch_lookup_data(file_signature)

        def branch_record(value):
            key = _lookup_key(value)
            return branch_by_code.get(key) or branch_by_name.get(key) or {}

        origin_records = [branch_record(value) for value in df['Origin']]
        destination_records = [branch_record(value) for value in df['Destination']]
        df['RO'] = [record.get('ro', '') or 'RO NOT MAPPED' for record in origin_records]
        df['Destination RO'] = [record.get('ro', '') or 'RO NOT MAPPED' for record in destination_records]
        df['Origin Branch'] = [record.get('name', '') or record.get('code', '') or str(value) for record, value in zip(origin_records, df['Origin'])]
        df['Destination Branch'] = [record.get('name', '') or record.get('code', '') or str(value) for record, value in zip(destination_records, df['Destination'])]
        result = df.reindex(columns=output_cols).fillna('')
        result.attrs['branch_source'] = branch_source
        result.attrs['ondemand_source'] = ''
        result.attrs['schedule_source'] = schedule_source
        return result
    except Exception as exc:
        logging.exception("Could not load scheduled route master from the shared route workbook")
        st.warning(f"Could not read the uploaded Scheduled Route Master workbook: {exc}")
        return pd.DataFrame(columns=output_cols)

def build_print_ready_schedule_html(df, branch_label):
    """Build a self-contained A3 landscape sheet that can be printed or saved as PDF."""
    title = f"National & Zonal Scheduled Route Master — {branch_label}"
    table_html = df.to_html(index=False, escape=True, border=0, classes='schedule-table')
    safe_title = html_module.escape(title)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{safe_title}</title>
<style>
@page {{ size: A3 landscape; margin: 9mm; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; padding: 20px; color: {selected_theme["text"]}; background: {selected_theme["navy950"]}; font: 12px/1.35 Arial, sans-serif; }}
.toolbar {{ display: flex; justify-content: space-between; align-items: center; gap: 16px; margin: 0 0 16px; }}
.toolbar button {{ border: 0; border-radius: 7px; background: {selected_theme["blue"]}; color: {theme_primary_text}; padding: 10px 16px; font-size: 13px; font-weight: 700; cursor: pointer; }}
h1 {{ margin: 0 0 4px; font-size: 22px; }}
.subtitle {{ margin: 0; color: {selected_theme["muted"]}; }}
.schedule-table {{ width: 100%; border-collapse: collapse; font-size: 8px; }}
.schedule-table th {{ background: {selected_theme["navy800"]}; color: {selected_theme["text"]}; text-align: left; padding: 7px 6px; }}
.schedule-table td {{ border-bottom: 1px solid {selected_theme["line"]}; padding: 6px; vertical-align: top; }}
.schedule-table tr:nth-child(even) td {{ background: {selected_theme["card2"]}; }}
thead {{ display: table-header-group; }}
tr {{ break-inside: avoid; page-break-inside: avoid; }}
@media print {{ body {{ padding: 0; }} .toolbar button {{ display: none; }} }}
</style></head><body>
<div class="toolbar"><div><h1>{safe_title}</h1><p class="subtitle">Leg order follows Route No. Route TAT uses the same calculation as Vendor Performance; halt is scheduled departure minus arrival at the branch.</p></div>
<button onclick="window.print()">Print / Save as PDF</button></div>
{table_html}
</body></html>'''

def build_formatted_excel_bytes(df, sheet_name, report_title, percent_columns=None, width_overrides=None, paper_size=8, landscape=True):
    """Write a compact, styled Excel table with filters, frozen headers, and print setup."""
    buffer = io.BytesIO()
    df_out = df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame()
    percent_columns = set(percent_columns or [])
    width_overrides = width_overrides or {}
    if df_out.empty:
        if len(df_out.columns) == 0:
            df_out = pd.DataFrame(columns=['Status'])
        placeholder = {col: '' for col in df_out.columns}
        placeholder[df_out.columns[0]] = 'No records for the selected filters.'
        df_out = pd.DataFrame([placeholder])
    safe_sheet = str(sheet_name)[:31] or 'Report'
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet(safe_sheet)
        writer.sheets[safe_sheet] = worksheet
        ncols = max(len(df_out.columns), 1)
        title_fmt = workbook.add_format({'bold': True, 'font_size': 16, 'font_color': '#FFFFFF', 'bg_color': '#102B46', 'valign': 'vcenter'})
        subtitle_fmt = workbook.add_format({'font_color': '#42566B', 'italic': True, 'bg_color': '#EAF2F8', 'valign': 'vcenter'})
        header_fmt = workbook.add_format({'bold': True, 'font_color': '#FFFFFF', 'bg_color': '#155E75', 'border': 1, 'border_color': '#0E7490', 'align': 'center', 'valign': 'vcenter', 'text_wrap': True})
        base_even_fmt = workbook.add_format({'bg_color': '#F2F7FB', 'font_color': '#14283B', 'bottom': 1, 'bottom_color': '#D9E3EC', 'align': 'center', 'valign': 'vcenter', 'text_wrap': True})
        base_odd_fmt = workbook.add_format({'bg_color': '#FFFFFF', 'font_color': '#14283B', 'bottom': 1, 'bottom_color': '#D9E3EC', 'align': 'center', 'valign': 'vcenter', 'text_wrap': True})
        low_even_fmt = workbook.add_format({'bg_color': '#DDF3E8', 'font_color': '#14532D', 'bold': True, 'bottom': 1, 'bottom_color': '#B8DDC8', 'align': 'center', 'valign': 'vcenter'})
        low_odd_fmt = workbook.add_format({'bg_color': '#EAF8F0', 'font_color': '#14532D', 'bold': True, 'bottom': 1, 'bottom_color': '#B8DDC8', 'align': 'center', 'valign': 'vcenter'})
        high_even_fmt = workbook.add_format({'bg_color': '#FCE1E1', 'font_color': '#8A1C1C', 'bold': True, 'bottom': 1, 'bottom_color': '#E9BABA', 'align': 'center', 'valign': 'vcenter'})
        high_odd_fmt = workbook.add_format({'bg_color': '#FFF0E0', 'font_color': '#8A3B0A', 'bold': True, 'bottom': 1, 'bottom_color': '#E9CBAA', 'align': 'center', 'valign': 'vcenter'})
        numeric_even_fmt = workbook.add_format({'bg_color': '#F2F7FB', 'font_color': '#14283B', 'bottom': 1, 'bottom_color': '#D9E3EC', 'num_format': '#,##0.00'})
        numeric_odd_fmt = workbook.add_format({'bg_color': '#FFFFFF', 'font_color': '#14283B', 'bottom': 1, 'bottom_color': '#D9E3EC', 'num_format': '#,##0.00'})
        worksheet.merge_range(0, 0, 0, ncols - 1, report_title, title_fmt)
        worksheet.merge_range(1, 0, 1, ncols - 1, f"Generated {get_ist_now():%d %b %Y, %I:%M %p} IST · Trackon Command Center", subtitle_fmt)
        worksheet.set_row(0, 30)
        worksheet.set_row(1, 21)
        for col_idx, col_name in enumerate(df_out.columns):
            worksheet.write(2, col_idx, str(col_name), header_fmt)
        worksheet.set_row(2, 34)
        for row_idx, (_, row) in enumerate(df_out.iterrows(), start=3):
            is_even = (row_idx - 3) % 2 == 0
            for col_idx, col_name in enumerate(df_out.columns):
                value = row[col_name]
                if isinstance(value, np.generic):
                    value = value.item()
                if value is None or (not isinstance(value, (list, dict)) and pd.isna(value)):
                    value = ''
                fmt = base_even_fmt if is_even else base_odd_fmt
                if col_name in percent_columns:
                    pct = parse_pct_from_str(value)
                    if pct is not None:
                        fmt = (high_even_fmt if is_even else high_odd_fmt) if pct >= 50 else (low_even_fmt if is_even else low_odd_fmt)
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    fmt = numeric_even_fmt if is_even else numeric_odd_fmt
                    worksheet.write_number(row_idx, col_idx, value, fmt)
                else:
                    worksheet.write(row_idx, col_idx, str(value), fmt)
            worksheet.set_row(row_idx, 24)
        for col_idx, col_name in enumerate(df_out.columns):
            values = df_out[col_name].fillna('').astype(str).tolist()
            measured = max([len(str(col_name))] + [min(len(value), 60) for value in values]) + 2
            worksheet.set_column(col_idx, col_idx, width_overrides.get(col_name, min(max(measured, 12), 38)))
        last_data_row = len(df_out) + 2
        worksheet.autofilter(2, 0, last_data_row, len(df_out.columns) - 1)
        worksheet.freeze_panes(3, 0)
        worksheet.set_landscape() if landscape else worksheet.set_portrait()
        worksheet.set_paper(paper_size)
        worksheet.fit_to_pages(1, 0)
        worksheet.repeat_rows(2)
        worksheet.set_margins(0.25, 0.25, 0.4, 0.4)
        worksheet.set_header('&LTrackon Command Center&R&P')
        worksheet.set_footer('&LConfidential meeting report&RPage &P of &N')
    return buffer.getvalue()

def _clean_ro_series(series):
    return series.fillna('RO NOT MAPPED').astype(str).str.strip().str.upper().replace({'': 'RO NOT MAPPED', 'NAN': 'RO NOT MAPPED', 'NONE': 'RO NOT MAPPED'})

def build_overall_issues_summary(ops_raw, pay_raw, cpk_raw=None):
    """Create RO/zone issue and utilization rates in percentage-and-count form."""
    ops = ops_raw.copy() if isinstance(ops_raw, pd.DataFrame) else pd.DataFrame()
    pay = pay_raw.copy() if isinstance(pay_raw, pd.DataFrame) else pd.DataFrame()
    cpk = cpk_raw.copy() if isinstance(cpk_raw, pd.DataFrame) else pd.DataFrame()
    ops_ro_col = get_col(ops, ['Origin RO', 'RO Name', 'RO'])
    pay_ro_col = get_col(pay, ['RO Name', 'Origin RO', 'RO'])
    ops_zone_col = get_col(ops, ['Zone'])
    pay_zone_col = get_col(pay, ['Zone'])
    ops_rows = {}
    pay_rows = {}

    if ops_ro_col:
        remark_col = get_col(ops, ['Remark'])
        dep_col = get_col(ops, ['Dep_Status'])
        arr_col = get_col(ops, ['Arr_Status'])
        remark = ops[remark_col].fillna('').astype(str) if remark_col else pd.Series('', index=ops.index)
        dep_status = ops[dep_col].fillna('').astype(str) if dep_col else remark
        arr_status = ops[arr_col].fillna('').astype(str) if arr_col else remark
        outcome_source = remark.where(remark.str.strip().ne(''), dep_status + ', ' + arr_status)
        ops_ro = _clean_ro_series(ops[ops_ro_col])
        ops_zone = ops[ops_zone_col].fillna('UNKNOWN ZONE').astype(str).str.strip().str.upper() if ops_zone_col else pd.Series('UNKNOWN ZONE', index=ops.index)
        ops_zone = ops_zone.replace({'': 'UNKNOWN ZONE', 'NAN': 'UNKNOWN ZONE', 'NONE': 'UNKNOWN ZONE'})
        outcome_patterns = {
            '_OO': 'Ontime Dep, Ontime Arr',
            '_OL': 'Ontime Dep, Late Arr',
            '_LL': 'Late Dep, Late Arr',
            '_LO': 'Late Dep, Ontime Arr'
        }
        grouped = pd.DataFrame({
            '_RO': ops_ro, '_ZONE': ops_zone,
            **{key: outcome_source.str.contains(pattern, case=False, na=False).astype(int)
               for key, pattern in outcome_patterns.items()}
        }).groupby(['_RO', '_ZONE'], dropna=False).agg(
            Total_Trips=('_RO', 'size'), OO_Cnt=('_OO', 'sum'), OL_Cnt=('_OL', 'sum'),
            LL_Cnt=('_LL', 'sum'), LO_Cnt=('_LO', 'sum')
        )
        for (ro, zone), row in grouped.iterrows():
            ops_rows[(ro, zone)] = row.to_dict()

    if pay_ro_col:
        payment_masks = get_overall_payment_status_masks(pay)
        draft_mask = payment_masks['Draft bills'].astype(int)
        pending_mask = payment_masks['Pending bills'].astype(int)
        payment_pending_mask = payment_masks['Payment pending / paid'].astype(int)
        finance_pending_mask = payment_masks['Finance pending'].astype(int)
        finance_hold_mask = payment_masks['Finance hold'].astype(int)
        other_mask = payment_masks['Other bills'].astype(int)
        pay_ro = _clean_ro_series(pay[pay_ro_col])
        pay_zone = pay[pay_zone_col].fillna('UNKNOWN ZONE').astype(str).str.strip().str.upper() if pay_zone_col else pd.Series('UNKNOWN ZONE', index=pay.index)
        pay_zone = pay_zone.replace({'': 'UNKNOWN ZONE', 'NAN': 'UNKNOWN ZONE', 'NONE': 'UNKNOWN ZONE'})
        grouped = pd.DataFrame({
            '_RO': pay_ro, '_ZONE': pay_zone, '_DRAFT': draft_mask,
            '_PENDING': pending_mask, '_PAYMENT_PENDING_PAID': payment_pending_mask,
            '_FINANCE_PENDING': finance_pending_mask, '_FINANCE_HOLD': finance_hold_mask, '_OTHER': other_mask
        }).groupby(['_RO', '_ZONE'], dropna=False).agg(
            Total_Bills=('_RO', 'size'), Draft_Cnt=('_DRAFT', 'sum'), Pending_Cnt=('_PENDING', 'sum'),
            Payment_Pending_Paid_Cnt=('_PAYMENT_PENDING_PAID', 'sum'),
            Finance_Pending_Cnt=('_FINANCE_PENDING', 'sum'), Finance_Hold_Cnt=('_FINANCE_HOLD', 'sum'),
            Other_Cnt=('_OTHER', 'sum')
        )
        for (ro, zone), row in grouped.iterrows():
            pay_rows[(ro, zone)] = row.to_dict()

    utilization_rows = {}
    if not cpk.empty:
        try:
            route_master = build_cpk_tables_from_raw(cpk).get('CPK_National_Zonal_UpDown', pd.DataFrame())
            if not route_master.empty:
                route_ro = get_col(route_master, ['VendorRO', 'RO_Clean', 'RO'])
                route_zone = get_col(route_master, ['Zone'])
                route_type = get_col(route_master, ['Type', 'Final_Type'])
                util_col = get_col(route_master, ['Overall Util %', 'Utilization'])
                route_name = get_col(route_master, ['Route (UP/DOWN)', 'Final_Route', 'Route'])
                if route_ro and route_type and util_col:
                    route_data = pd.DataFrame({
                        '_RO': _clean_ro_series(route_master[route_ro]),
                        '_ZONE': route_master[route_zone].fillna('UNKNOWN ZONE').astype(str).str.strip().str.upper() if route_zone else 'UNKNOWN ZONE',
                        '_TYPE': route_master[route_type].fillna('').astype(str).str.strip().str.upper(),
                        '_UTIL': pd.to_numeric(route_master[util_col], errors='coerce')
                    })
                    if route_name:
                        route_data['_ROUTE'] = route_master[route_name].fillna('').astype(str).str.strip().str.upper()
                        route_data = route_data.drop_duplicates(['_RO', '_ZONE', '_TYPE', '_ROUTE'])
                    route_data['_ZONE'] = route_data['_ZONE'].replace({'': 'UNKNOWN ZONE', 'NAN': 'UNKNOWN ZONE', 'NONE': 'UNKNOWN ZONE'})
                    route_data = route_data[route_data['_TYPE'].isin(['NATIONAL LH', 'ZONAL LH']) & route_data['_UTIL'].notna()]
                    for (ro, zone), group in route_data.groupby(['_RO', '_ZONE'], dropna=False):
                        # The summary combines national and zonal route counts; detailed
                        # records still keep their route type for the drill-down tabs.
                        total_routes = len(group)
                        under_count = int(group['_UTIL'].lt(0.60).sum())
                        efficient_count = int(group['_UTIL'].ge(0.60).sum())
                        utilization_rows[(ro, zone)] = {
                            'Underutilized Routes': format_pct_cnt(under_count, total_routes),
                            'Efficiently Utilized Routes': format_pct_cnt(efficient_count, total_routes)
                        }
        except Exception as exc:
            logging.warning(f"Overall Issues utilization summary warning: {exc}")

    rows = []
    for ro, zone in sorted(set(ops_rows) | set(pay_rows) | set(utilization_rows)):
        ops_stats = ops_rows.get((ro, zone), {})
        pay_stats = pay_rows.get((ro, zone), {})
        trips = int(ops_stats.get('Total_Trips', 0))
        bills = int(pay_stats.get('Total_Bills', 0))
        oo = int(ops_stats.get('OO_Cnt', 0))
        ol = int(ops_stats.get('OL_Cnt', 0))
        ll = int(ops_stats.get('LL_Cnt', 0))
        lo = int(ops_stats.get('LO_Cnt', 0))
        draft = int(pay_stats.get('Draft_Cnt', 0))
        pending = int(pay_stats.get('Pending_Cnt', 0))
        payment_pending_paid = int(pay_stats.get('Payment_Pending_Paid_Cnt', 0))
        finance_pending = int(pay_stats.get('Finance_Pending_Cnt', 0))
        finance_hold = int(pay_stats.get('Finance_Hold_Cnt', 0))
        other = int(pay_stats.get('Other_Cnt', 0))
        utilization = utilization_rows.get((ro, zone), {})
        rows.append({
            'RO Name': ro, 'Zone': zone, 'Total Trips': trips,
            'Ontime Dep, Ontime Arr': format_pct_cnt(oo, trips),
            'Ontime Dep, Late Arr': format_pct_cnt(ol, trips),
            'Late Dep, Late Arr': format_pct_cnt(ll, trips),
            'Late Dep, Ontime Arr': format_pct_cnt(lo, trips), 'Total Bills': bills,
            'Draft Bills': format_pct_cnt(draft, bills),
            'Pending': format_pct_cnt(pending, bills),
            'Payment Pending / Paid': format_pct_cnt(payment_pending_paid, bills),
            'Finance Pending': format_pct_cnt(finance_pending, bills),
            'Finance Hold': format_pct_cnt(finance_hold, bills),
            'Other': format_pct_cnt(other, bills),
            'Underutilized Routes': utilization.get('Underutilized Routes', '0.0% (0)'),
            'Efficiently Utilized Routes': utilization.get('Efficiently Utilized Routes', '0.0% (0)')
        })
    return pd.DataFrame(rows, columns=[
        'RO Name', 'Zone', 'Total Trips', 'Ontime Dep, Ontime Arr',
        'Ontime Dep, Late Arr', 'Late Dep, Late Arr', 'Late Dep, Ontime Arr',
        'Total Bills', 'Draft Bills', 'Pending', 'Payment Pending / Paid',
        'Finance Pending', 'Finance Hold', 'Other', 'Underutilized Routes',
        'Efficiently Utilized Routes'
    ])

# ==========================================
# 3B. DYNAMIC SUMMARY CALCULATORS (With Vendor Grouping)
# ==========================================
@st.cache_data(show_spinner=False, max_entries=12)
def build_ops_summary_from_raw(df_group):
    if df_group is None or df_group.empty:
        return pd.DataFrame()
    df_valid = df_group.copy()
    if 'E2E_Pair' not in df_valid.columns and 'Route Path' in df_valid.columns:
        df_valid['E2E_Pair'] = df_valid['Route Path'].apply(get_route_pair)
    if 'Origin' not in df_valid.columns and 'Route Path' in df_valid.columns:
        df_valid[['Origin', 'Destination']] = df_valid['Route Path'].apply(lambda x: pd.Series(extract_orig_dest(x)))
    if 'Leg_Num' not in df_valid.columns and 'Legwise' in df_valid.columns:
        df_valid['Leg_Num'] = extract_leg_num_val(df_valid['Legwise'])
    if 'Zone' not in df_valid.columns:
        df_valid['Zone'] = 'UNKNOWN ZONE'
    if 'LH Type' not in df_valid.columns:
        df_valid['LH Type'] = 'National LH'

    trip_col = 'Total_Trips'
    remark_text = df_valid.get('Remark', pd.Series('', index=df_valid.index)).fillna('').astype(str)
    df_valid['OO_Cnt'] = remark_text.str.contains('Ontime Dep, Ontime Arr', case=False, regex=False).astype('int8')
    df_valid['LL_Cnt'] = remark_text.str.contains('Late Dep, Late Arr', case=False, regex=False).astype('int8')
    df_valid['LO_Cnt'] = remark_text.str.contains('Late Dep, Ontime Arr', case=False, regex=False).astype('int8')
    df_valid['OL_Cnt'] = remark_text.str.contains('Ontime Dep, Late Arr', case=False, regex=False).astype('int8')
    
    group_cols = ['Zone', 'LH Type', 'E2E_Pair', 'Origin RO', 'Route Path', 'Origin', 'Destination', 'Leg_Num', 'Legwise', 'Legs']
    existing_gcols = [c for c in group_cols if c in df_valid.columns]
    
    agg_dict = {
        'MasterCDNo': 'count',
        'OO_Cnt': 'sum',
        'LO_Cnt': 'sum',
        'OL_Cnt': 'sum',
        'LL_Cnt': 'sum',
    }
    summary = df_valid.groupby(existing_gcols).agg(agg_dict).reset_index()
    summary.rename(columns={'MasterCDNo': trip_col}, inplace=True)
    
    summary['Ontime Dep, Ontime Arr %'] = summary.apply(lambda r: format_pct_cnt(r['OO_Cnt'], r[trip_col]), axis=1)
    summary['Late Dep, Late Arr %'] = summary.apply(lambda r: format_pct_cnt(r['LL_Cnt'], r[trip_col]), axis=1)
    summary['Late Dep, Ontime Arr %'] = summary.apply(lambda r: format_pct_cnt(r['LO_Cnt'], r[trip_col]), axis=1)
    summary['Ontime Dep, Late Arr %'] = summary.apply(lambda r: format_pct_cnt(r['OL_Cnt'], r[trip_col]), axis=1)
    return sort_by_route_and_leg(summary)

OPS_REMARK_OUTCOME_LABELS = [
    ('Ontime Dep, Ontime Arr', 'green', '🟢'),
    ('Ontime Dep, Late Arr', 'soft_red', '🌸'),
    ('Late Dep, Late Arr', 'red', '🔴'),
    ('Late Dep, Ontime Arr', 'purple', '🟣'),
    ('Late Dep, In-Transit', 'yellow', '🟡'),
    ('Ontime Dep, In-Transit', 'yellow', '🟡'),
    ('Missing Schedule', 'yellow', '🟡'),
    ('No Departure', 'red', '🔴'),
    ('In-Transit', 'yellow', '🟡'),
    ('Other', 'muted', '⚪')
]

def ops_remark_outcome_series(df_raw):
    """Return one exclusive outcome per trip, based on Remark first."""
    if not isinstance(df_raw, pd.DataFrame) or df_raw.empty:
        return pd.Series(dtype=object)
    remark_col = get_col(df_raw, ['Remark'])
    dep_col = get_col(df_raw, ['Dep_Status'])
    arr_col = get_col(df_raw, ['Arr_Status'])
    remark = df_raw[remark_col].fillna('').astype(str) if remark_col else pd.Series('', index=df_raw.index)
    dep = df_raw[dep_col].fillna('').astype(str) if dep_col else pd.Series('', index=df_raw.index)
    arr = df_raw[arr_col].fillna('').astype(str) if arr_col else pd.Series('', index=df_raw.index)
    outcome = remark.where(remark.str.strip().ne(''), dep + ', ' + arr)
    outcome = outcome.str.casefold().str.replace(r'\s+', ' ', regex=True).str.strip()
    patterns = [
        ('Missing Schedule', r'missing\s+(?:sch|schedule)'),
        ('No Departure', r'no\s+dep(?:arture)?'),
        ('Late Dep, Late Arr', r'late\s+(?:dep|departure)\s*,\s*late\s+(?:arr|arrival)'),
        ('Ontime Dep, Late Arr', r'ontime\s+(?:dep|departure)\s*,\s*late\s+(?:arr|arrival)'),
        ('Late Dep, In-Transit', r'late\s+(?:dep|departure)\s*,\s*in-transit'),
        ('Ontime Dep, Ontime Arr', r'ontime\s+(?:dep|departure)\s*,\s*ontime\s+(?:arr|arrival)'),
        ('Late Dep, Ontime Arr', r'late\s+(?:dep|departure)\s*,\s*ontime\s+(?:arr|arrival)'),
        ('Ontime Dep, In-Transit', r'ontime\s+(?:dep|departure)\s*,\s*in-transit'),
        ('In-Transit', r'in-transit')
    ]
    buckets = pd.Series('Other', index=df_raw.index, dtype=object)
    unassigned = pd.Series(True, index=df_raw.index)
    for label, pattern in patterns:
        matched = unassigned & outcome.str.contains(pattern, regex=True, na=False)
        buckets.loc[matched] = label
        unassigned.loc[matched] = False
    return buckets

def summarize_ops_remark_outcomes(df_raw):
    """Count selected rows using their cached exclusive Remark outcome."""
    labels = OPS_REMARK_OUTCOME_LABELS
    if not isinstance(df_raw, pd.DataFrame) or df_raw.empty:
        return {label: 0 for label, _, _ in labels}, 0, labels
    outcomes = (
        df_raw['_OpsRemarkOutcome']
        if '_OpsRemarkOutcome' in df_raw.columns
        else ops_remark_outcome_series(df_raw)
    )
    counts = outcomes.value_counts().to_dict()
    return {label: int(counts.get(label, 0)) for label, _, _ in labels}, len(df_raw), labels

@st.cache_data(show_spinner=False, max_entries=8)
def build_vendor_summary_from_raw(df_vperf_raw):
    if df_vperf_raw is None or df_vperf_raw.empty:
        return pd.DataFrame()
    df_in = df_vperf_raw.copy()
    if 'VendorName' in df_in.columns:
        df_in['VendorName'] = df_in['VendorName'].apply(normalize_vendor_name)
    if 'Zone' not in df_in.columns:
        df_in['Zone'] = 'UNKNOWN ZONE'
    sum_cols = ['Zone', 'Origin RO', 'Route Path', 'Legwise', 'Legs', 'VendorName']
    existing_scols = [c for c in sum_cols if c in df_in.columns]
    
    perf_sum = df_in.groupby(existing_scols).agg(
        Total_Trips=('MasterCDNo', 'count'),
        Ontime_Cnt=('Remark with 15 min waiver', lambda x: (x == 'Ontime Arrival').sum()),
        Late_Cnt=('Remark with 15 min waiver', lambda x: (x == 'Late Arrival').sum()),
        Transit_Cnt=('Remark with 15 min waiver', lambda x: (x == 'In-Transit').sum()),
        Missing_Cnt=('Remark with 15 min waiver', lambda x: (x == 'Missing Schedule').sum())
    ).reset_index()
    
    perf_sum['Ontime Arrival'] = perf_sum.apply(lambda r: format_pct_cnt(r['Ontime_Cnt'], r['Total_Trips']), axis=1)
    perf_sum['Late Arrival'] = perf_sum.apply(lambda r: format_pct_cnt(r['Late_Cnt'], r['Total_Trips']), axis=1)
    perf_sum['In-Transit'] = perf_sum.apply(lambda r: format_pct_cnt(r['Transit_Cnt'], r['Total_Trips']), axis=1)
    perf_sum['Missing Schedule'] = perf_sum.apply(lambda r: format_pct_cnt(r['Missing_Cnt'], r['Total_Trips']), axis=1)
    
    perf_sum = perf_sum.drop(columns=['Ontime_Cnt', 'Late_Cnt', 'Transit_Cnt', 'Missing_Cnt'], errors='ignore')
    return sort_by_route_and_leg(perf_sum)

@st.cache_data(show_spinner=False, max_entries=8)
def build_cpk_tables_from_raw(df_updn_in):
    out = {
        'CPK_National_Zonal_UpDown': pd.DataFrame(),
        'CPK_National_Zonal_Master': pd.DataFrame(),
        'CPK_Feeder_Regional': pd.DataFrame(),
        'CPK_Coloader': pd.DataFrame()
    }
    if df_updn_in is None or df_updn_in.empty:
        return out
    df_updn = df_updn_in.copy()
    if 'VendorName' in df_updn.columns:
        df_updn['VendorName'] = df_updn['VendorName'].apply(normalize_vendor_name)
    df_updn['Trip_Rate'] = np.where(df_updn['Trips'] > 0, df_updn['Cost'] / df_updn['Trips'], 0).round(2)
    df_updn['Trip_Rate_Str'] = "₹" + df_updn['Trip_Rate'].astype(str)
    df_updn['Total_Cap_Raw'] = df_updn['Cap'] * df_updn['Trips']
    
    # 1. National & Zonal
    nz_mask = df_updn['Final_Type'].isin(['National LH', 'Zonal LH'])
    if nz_mask.any():
        agg_nz_updown = df_updn[nz_mask].groupby(['RO_Clean', 'Zone', 'Final_Route', 'Final_Type', 'Cap', 'SortKey', 'Trip_Rate']).agg(
            Total_Trips=('Trips', 'sum'),
            Total_Carried_Wt=('Wt', 'sum'),
            Total_Trip_Cost=('Cost', 'sum'),
            VendorName=('VendorName', lambda x: ', '.join(sorted(set(x.dropna().astype(str))))),
            Per_Trip_Cost=('Trip_Rate_Str', lambda x: ', '.join(sorted(set(x.dropna().astype(str)))))
        ).reset_index()
        agg_nz_updown['Total Capacity'] = agg_nz_updown['Cap'] * agg_nz_updown['Total_Trips']
        agg_nz_updown['Overall CPK'] = np.where(agg_nz_updown['Total_Carried_Wt'] > 0, agg_nz_updown['Total_Trip_Cost'] / agg_nz_updown['Total_Carried_Wt'], 0)
        agg_nz_updown['Overall Util %'] = np.where(agg_nz_updown['Total Capacity'] > 0, agg_nz_updown['Total_Carried_Wt'] / agg_nz_updown['Total Capacity'], 0)
        nz_updown_final = agg_nz_updown[['Zone', 'RO_Clean', 'Final_Route', 'Final_Type', 'Overall CPK', 'Overall Util %', 'Cap', 'Total Capacity', 'Total_Carried_Wt', 'Per_Trip_Cost', 'Total_Trip_Cost', 'Total_Trips', 'VendorName', 'SortKey']]
        nz_updown_final.columns = ["Zone", "VendorRO", "Route (UP/DOWN)", "Type", "Overall CPK", "Overall Util %", "VehCap (Base)", "Total Capacity", "Total Carried Wt", "Per Trip Cost", "Total Trip Cost", "Total Trips", "Vendor(s)", "SortKey"]
        out['CPK_National_Zonal_UpDown'] = nz_updown_final.sort_values(by=['Type', 'SortKey', 'Route (UP/DOWN)'])
        
        agg_nz_master = df_updn[nz_mask].groupby(['RO_Clean', 'Zone', 'SortKey', 'Final_Type']).agg(
            Total_Trips=('Trips', 'sum'),
            Total_Carried_Wt=('Wt', 'sum'),
            Total_Trip_Cost=('Cost', 'sum'),
            Total_Capacity=('Total_Cap_Raw', 'sum'),
            Unique_Vendors=('VendorName', lambda x: x.nunique()),
            VendorName=('VendorName', lambda x: ', '.join(sorted(set(x.dropna().astype(str))))),
            Route_Path=('Final_Route', lambda x: ', '.join(sorted(set(x.dropna().astype(str))))),
            Per_Trip_Cost=('Trip_Rate_Str', lambda x: ', '.join(sorted(set(x.dropna().astype(str)))))
        ).reset_index()
        agg_nz_master['Overall CPK'] = np.where(agg_nz_master['Total_Carried_Wt'] > 0, agg_nz_master['Total_Trip_Cost'] / agg_nz_master['Total_Carried_Wt'], 0)
        agg_nz_master['Overall Util %'] = np.where(agg_nz_master['Total_Capacity'] > 0, agg_nz_master['Total_Carried_Wt'] / agg_nz_master['Total_Capacity'], 0)
        nz_master_final = agg_nz_master[['Zone', 'RO_Clean', 'Route_Path', 'Final_Type', 'Overall CPK', 'Overall Util %', 'Total_Capacity', 'Total_Carried_Wt', 'Per_Trip_Cost', 'Total_Trip_Cost', 'Total_Trips', 'Unique_Vendors', 'VendorName', 'SortKey']]
        nz_master_final.columns = ["Zone", "VendorRO", "Route Path", "Type", "Overall CPK", "Overall Util %", "Total Capacity", "Total Carried Wt", "Per Trip Cost", "Total Trip Cost", "Total Trips", "Unique Vendors", "Vendor(s)", "Route Pair"]
        out['CPK_National_Zonal_Master'] = nz_master_final.sort_values(by=['Type', 'Overall Util %'])

    # 2. Feeder & Regional
    fr_mask = df_updn['Final_Type'].isin(['Regional LH', 'Feeder'])
    if fr_mask.any():
        agg_fr = df_updn[fr_mask].groupby(['RO_Clean', 'Zone', 'Vehicle No', 'Final_Type', 'Cap', 'Trip_Rate']).agg(
            Total_Trips=('Trips', 'sum'),
            Total_Carried_Wt=('Wt', 'sum'),
            Total_Trip_Cost=('Cost', 'sum'),
            VendorName=('VendorName', lambda x: ', '.join(sorted(set(x.dropna().astype(str))))),
            Per_Trip_Cost=('Trip_Rate_Str', lambda x: ', '.join(sorted(set(x.dropna().astype(str))))),
            Routes_Covered=('Final_Route', lambda x: ', '.join(sorted(set(x.dropna().astype(str)))))
        ).reset_index()
        agg_fr['Total Capacity'] = agg_fr['Cap'] * agg_fr['Total_Trips']
        agg_fr['Overall CPK'] = np.where(agg_fr['Total_Carried_Wt'] > 0, agg_fr['Total_Trip_Cost'] / agg_fr['Total_Carried_Wt'], 0)
        agg_fr['Overall Util %'] = np.where(agg_fr['Total Capacity'] > 0, agg_fr['Total_Carried_Wt'] / agg_fr['Total Capacity'], 0)
        fr_final = agg_fr[['Zone', 'RO_Clean', 'Vehicle No', 'Final_Type', 'Overall CPK', 'Overall Util %', 'Cap', 'Total Capacity', 'Total_Carried_Wt', 'Per_Trip_Cost', 'Total_Trip_Cost', 'Total_Trips', 'VendorName', 'Routes_Covered']]
        fr_final.columns = ["Zone", "VendorRO", "Vehicle No", "Type", "Overall CPK", "Overall Util %", "VehCap (Base)", "Total Capacity", "Total Carried Wt", "Per Trip Cost", "Total Trip Cost", "Total Trips", "Vendor(s)", "Routes Covered"]
        out['CPK_Feeder_Regional'] = fr_final.sort_values(by=['Type', 'VendorRO', 'Overall Util %'])
        
    # 3. Co-loader
    col_mask = df_updn['Final_Type'] == 'CO-LOADER'
    if col_mask.any():
        agg_col = df_updn[col_mask].groupby(['RO_Clean', 'Zone', 'VendorName', 'Final_Route', 'Vehicle No', 'Trip_Rate']).agg(
            Total_Trips=('Trips', 'sum'),
            Total_Carried_Wt=('Wt', 'sum'),
            Total_Trip_Cost=('Cost', 'sum'),
            Per_Trip_Cost=('Trip_Rate_Str', lambda x: ', '.join(sorted(set(x.dropna().astype(str)))))
        ).reset_index()
        agg_col['Cap'] = df_updn[col_mask].groupby(['RO_Clean', 'Zone', 'VendorName', 'Final_Route', 'Vehicle No', 'Trip_Rate'])['Cap'].max().values
        agg_col['Total Capacity'] = agg_col['Cap'] * agg_col['Total_Trips']
        agg_col['Overall CPK'] = np.where(agg_col['Total_Carried_Wt'] > 0, agg_col['Total_Trip_Cost'] / agg_col['Total_Carried_Wt'], 0)
        agg_col['Overall Util %'] = np.where(agg_col['Total Capacity'] > 0, agg_col['Total_Carried_Wt'] / agg_col['Total Capacity'], 0)
        col_final = agg_col[['Zone', 'RO_Clean', 'VendorName', 'Final_Route', 'Vehicle No', 'Overall CPK', 'Overall Util %', 'Cap', 'Total Capacity', 'Total_Carried_Wt', 'Per_Trip_Cost', 'Total_Trip_Cost', 'Total_Trips']]
        col_final.columns = ["Zone", "VendorRO", "Vendor(s)", "Route", "Vehicle No", "Overall CPK", "Overall Util %", "VehCap (Base)", "Total Capacity", "Total Carried Wt", "Per Trip Cost", "Total Trip Cost", "Total Trips"]
        out['CPK_Coloader'] = col_final.sort_values(by=['VendorRO', 'Overall Util %'])
        
    return out

# ==========================================
# 3C. EMAIL TEXT SUMMARY FORMATTER (Clean, Grouped & Aligned)
# ==========================================
def build_clean_email_message(recipient_title, duration_label, ops_sum_df=None, ven_sum_df=None, pay_df=None, cpk_df=None):
    clean_dur = str(duration_label).replace("((", "(").replace("))", ")")
    
    lines = []
    lines.append(f"Dear {recipient_title},")
    lines.append("")
    lines.append(f"Please find the performance summary for {clean_dur}:")
    lines.append("")

    # 1. VENDOR PERFORMANCE BLOCK (Grouped by Route & Vendor)
    if ven_sum_df is not None and not ven_sum_df.empty:
        df_v = sort_by_route_and_leg(ven_sum_df)
        tot_t = int(df_v['Total_Trips'].sum()) if 'Total_Trips' in df_v.columns else len(df_v)
        lines.append(f"📌 VENDOR PERFORMANCE SUMMARY (Total Leg Trips: {tot_t})")
        lines.append("==========================================================")
        
        for route_name, grp in df_v.groupby('Route Path', sort=False):
            lines.append(f"🚛 Route: {route_name}")
            for _, r in grp.iterrows():
                lg = str(r.get('Legwise', '')).strip()
                leg_nodes = str(r.get('Legs', '')).strip()
                v_name = str(r.get('VendorName', '')).strip()
                tr = int(r.get('Total_Trips', 0))
                ot = str(r.get('Ontime Arrival', '0%')).strip()
                lt = str(r.get('Late Arrival', '0%')).strip()
                it = str(r.get('In-Transit', '0%')).strip()
                
                it_str = f" | 🟡 In-Transit: {it}" if not it.startswith("0.0%") and not it.startswith("0%") else ""
                lines.append(f"   • {lg} ({leg_nodes}) [{v_name}] | Trips: {tr}  ➔  🟢 Ontime: {ot}  |  🔴 Late: {lt}{it_str}")
            lines.append("")

    # 2. OPERATIONS PERFORMANCE BLOCK
    if ops_sum_df is not None and not ops_sum_df.empty:
        df_o = sort_by_route_and_leg(ops_sum_df)
        tot_o = int(df_o['Total_Trips'].sum()) if 'Total_Trips' in df_o.columns else len(df_o)
        lines.append(f"📌 OPERATIONS PERFORMANCE SUMMARY (Total Leg Trips: {tot_o})")
        lines.append("==========================================================")
        
        for route_name, grp in df_o.groupby('Route Path', sort=False):
            lines.append(f"🛣️ Route: {route_name}")
            for _, r in grp.iterrows():
                lg = str(r.get('Legwise', '')).strip()
                leg_nodes = str(r.get('Legs', '')).strip()
                tr = int(r.get('Total_Trips', 0))
                oo = str(r.get('Ontime Dep, Ontime Arr %', '0%')).strip()
                ll = str(r.get('Late Dep, Late Arr %', '0%')).strip()
                ol = str(r.get('Ontime Dep, Late Arr %', '0%')).strip()
                lo = str(r.get('Late Dep, Ontime Arr %', '0%')).strip()
                
                lines.append(
                    f"   • {lg} ({leg_nodes}) | Trips: {tr}  ➔  "
                    f"🟢 Ontime Dep-Arr: {oo} | 🔴 Late Dep-Arr: {ll} | 🟡 OntimeDep-LateArr: {ol} | 🟣 LateDep-OntimeArr: {lo}"
                )
            lines.append("")

    # 3. CPK & UTILIZATION BLOCK
    if cpk_df is not None and not cpk_df.empty and 'Total Trips' in cpk_df.columns:
        tot_cpk_trips = int(cpk_df['Total Trips'].sum())
        tot_wt = cpk_df['Total Carried Wt'].sum() if 'Total Carried Wt' in cpk_df.columns else 0
        tot_cap = cpk_df['Total Capacity'].sum() if 'Total Capacity' in cpk_df.columns else 0
        tot_cost = cpk_df['Total Trip Cost'].sum() if 'Total Trip Cost' in cpk_df.columns else 0
        util_p = (tot_wt / tot_cap * 100) if tot_cap > 0 else 0
        cpk_v = (tot_cost / tot_wt) if tot_wt > 0 else 0
        lines.append("📌 NETWORK UTILIZATION & CPK SUMMARY")
        lines.append("==========================================================")
        lines.append(f"   • Total Trips: {tot_cpk_trips}  |  Overall Utilization: {util_p:.1f}%  |  Overall CPK: Rs.{cpk_v:.2f}")
        lines.append("")

    # 4. PAYMENT PENDING BLOCK
    if pay_df is not None and not pay_df.empty:
        lines.append(f"📌 PAYMENT RECORDS SUMMARY (Total Bills: {len(pay_df)})")
        lines.append("==========================================================")
        if 'Department Bucket' in pay_df.columns:
            b_counts = pay_df['Department Bucket'].value_counts()
            for b_name, b_cnt in b_counts.items():
                lines.append(f"   • {b_name}: {b_cnt} Bills")
        lines.append("")

    lines.append("Detailed Excel data is attached with this mail. Please check and take required action.")
    lines.append("")
    lines.append("Thanks,")
    lines.append("Ajay Singh Rawat")
    lines.append("Fleet Operation Executive")
    return "\n".join(lines)

# ==========================================
# 4. UI & EXCEL HIGHLIGHTING ENGINE
# ==========================================
def clean_dataframe_for_excel(df_in, sheet_type="generic", preserve_order=False):
    if df_in is None or df_in.empty:
        return pd.DataFrame()
    df = df_in.copy()
    
    if 'VendorName' in df.columns:
        df['VendorName'] = df['VendorName'].apply(normalize_vendor_name)
        
    if not preserve_order:
        df = sort_by_route_and_leg(df)
    
    cols_to_remove = [c for c in JUNK_EXCEL_COLS if c in df.columns]
    df.drop(columns=cols_to_remove, inplace=True, errors='ignore')
    
    if sheet_type == "ops_sum":
        preferred = [
            'Origin RO', 'Route Path', 'Legwise', 'Legs', 'Total_Trips',
            'Ontime Dep, Ontime Arr %', 'Late Dep, Late Arr %',
            'Ontime Dep, Late Arr %', 'Late Dep, Ontime Arr %'
        ]
        df.drop(columns=['Ontime Dep, In-Transit', 'Late Dep, In-Transit'], errors='ignore', inplace=True)
        pct_cols = [c for c in df.columns if '%' in c]
        for c in pct_cols:
            df[c] = df[c].apply(format_ops_badge)
    elif sheet_type == "ops_raw":
        preferred = [
            'MCD_StartDate', 'Remark', 'Origin RO', 'Route Path', 'Legwise', 'Legs',
            'Scheduled Departure Time', 'Actual Departure Time',
            'Scheduled Arrival Time', 'Actual Arrival Time',
            'Scheduled Halting', 'Actual Halting', 'VendorName',
            'VehicleNo', 'MasterCDNo', 'RouteCode'
        ]
    elif sheet_type == "ven_sum":
        preferred = [
            'Origin RO', 'Route Path', 'Legwise', 'Legs', 'VendorName',
            'Total_Trips', 'Ontime Arrival', 'Late Arrival', 'In-Transit', 'Missing Schedule'
        ]
    elif sheet_type == "ven_raw":
        preferred = [
            'Date', 'Remark with 15 min waiver', 'Origin RO', 'Route Path', 'Legwise', 'Legs',
            'VendorName', 'VehicleNo', 'Actual Departure Time',
            'Actual Arrival Time', 'Given Driving Hours',
            'Actual Driving Hours', 'Delay Hours',
            'MasterCDNo', 'RouteCode'
        ]
    elif sheet_type == "cpk_raw":
        preferred = [
            'RO_Clean', 'Final_Route', 'Final_Type', 'VendorName',
            'Vehicle No', 'Date', 'Cap', 'Wt', 'Trips', 'Cost'
        ]
    else:
        preferred = [
            'Origin RO', 'VendorRO', 'RO Name', 'Route Path', 'Route',
            'Legwise', 'Legs', 'VendorName', 'Vendor(s)', 'VehicleNo',
            'Vehicle No', 'Total_Trips', 'Total Trips'
        ]
        
    front_cols = [c for c in preferred if c in df.columns]
    remaining_cols = [c for c in df.columns if c not in front_cols]
    df = df[front_cols + remaining_cols]
    return df

def style_ui_dataframe(df_in):
    """Applies Green (Achievement), Red (Failure), Yellow (Warning), Purple highlights to Streamlit UI tables."""
    if df_in is None or df_in.empty:
        return df_in

    def tone_css(tone):
        bg, fg = THEME_STATUS_PALETTE.get(tone, THEME_STATUS_PALETTE['muted'])
        return f'background-color: {bg}; color: {fg}; font-weight: bold;'

    def ui_cell_color(val, col_name):
        if pd.isna(val):
            return ''
        s_val = str(val).strip()
        s_lower = s_val.lower()
        c_lower = str(col_name).lower()
        pct = parse_pct_from_str(s_val)
        if 'util' in c_lower and pct is not None and pct <= 1:
            pct *= 100
        if not s_lower or s_lower in ('-', 'nan', 'none'):
            return ''

        if c_lower == 'payment pending / paid' or s_lower == 'payment pending / paid':
            return tone_css('green')
        if c_lower == 'finance hold' or s_lower == 'finance hold':
            return tone_css('red')
        if c_lower == 'finance pending' or s_lower == 'finance pending':
            return tone_css('yellow')
        if c_lower == 'other' or s_lower == 'other':
            return tone_css('yellow')
        if c_lower in ['draft', 'draft bills'] or s_lower == 'draft':
            return tone_css('red')
        if c_lower == 'underutilized routes':
            return tone_css('red')
        if c_lower == 'efficiently utilized routes':
            return tone_css('green')

        # Schedule outcomes follow the Remark pair first, before generic arrival/departure rules.
        if 'late dep, in-transit' in c_lower:
            return tone_css('yellow' if pct is None or pct > 0 else 'muted')
        if 'ontime dep, late arr' in c_lower:
            return tone_css('soft_red' if pct is None or pct > 0 else 'muted')
        if 'late dep, ontime arr' in c_lower:
            return tone_css('purple' if pct is None or pct > 0 else 'muted')
        if 'late dep, late arr' in c_lower:
            return tone_css('red' if pct is None or pct > 0 else 'muted')
        if 'ontime dep, ontime arr' in c_lower:
            return tone_css('green' if pct is None or pct > 0 else 'muted')
        if 'in-transit' in c_lower:
            return tone_css('yellow' if pct is None or pct > 0 else 'muted')
        if 'missing schedule' in c_lower:
            return tone_css('yellow' if pct is None or pct > 0 else 'muted')
        if 'no departure' in c_lower:
            return tone_css('red' if pct is None or pct > 0 else 'muted')
        if 'late arrival' in c_lower or 'late departure' in c_lower or 'late dep' in c_lower or 'late arr' in c_lower:
            return tone_css('red' if pct is None or pct > 0 else 'muted')
        if 'ontime arrival' in c_lower:
            return tone_css('green' if pct is None or pct > 0 else 'muted')
        if 'on-time' in c_lower and 'departure' not in c_lower and any(period in c_lower for period in ['previous 7 days', 'current 7 days', 'all available']):
            return tone_css('green' if pct is not None and pct > 0 else 'muted')
        if 'ontime departure' in c_lower or ('on-time' in c_lower and 'departure' in c_lower):
            if pct is not None:
                return tone_css('green' if pct >= 95 else ('yellow' if pct >= 80 else 'red'))

        # Status text rules also cover raw-trip and payment tables.
        if 'late dep, late arr' in s_lower:
            return tone_css('red')
        if 'ontime dep, late arr' in s_lower:
            return tone_css('soft_red')
        if 'late dep, in-transit' in s_lower:
            return tone_css('yellow')
        if 'ontime dep, ontime arr' in s_lower:
            return tone_css('green')
        if 'late dep, ontime arr' in s_lower:
            return tone_css('yellow')
        if 'missing sch' in s_lower or 'missing schedule' in s_lower:
            return tone_css('yellow')
        if 'ontime dep, in-transit' in s_lower or 'in-transit' in s_lower or 'finance pending' in s_lower or 'finance hold' in s_lower or 'cost control pending' in s_lower or 'pending' in s_lower:
            return tone_css('yellow')
        if any(k in s_lower for k in ['late arrival', 'late departure', 'no dep', 'no arrival', 'other', 'draft', 'disabled', 'underutilized']):
            return tone_css('red')
        if 'ontime arrival' in s_lower or 'ontime departure' in s_lower or s_lower == 'paid' or 'paid achievement' in s_lower or 'active' in s_lower or 'efficiently utilized' in s_lower:
            return tone_css('green')
        if 'payment pending / paid' in s_lower:
            return tone_css('green')

        if 'util' in c_lower and pct is not None:
            return tone_css('red') if pct < 60 else (tone_css('yellow') if pct < 80 else tone_css('green'))

        if any(word in c_lower for word in ['payment pending / paid', 'payment pending']):
            return tone_css('yellow') if pct is None or pct > 0 else tone_css('muted')
        if any(word in c_lower for word in ['other', 'draft']):
            return tone_css('red') if pct is None or pct > 0 else tone_css('green')
        if any(word in c_lower for word in ['finance pending', 'finance hold', 'cost control pending']):
            return tone_css('yellow') if pct is None or pct > 0 else tone_css('green')
        if 'underutilized' in c_lower:
            return tone_css('red') if pct is None or pct > 0 else tone_css('green')
        if 'efficiently utilized' in c_lower:
            return tone_css('green') if pct is None or pct > 0 else tone_css('muted')

        if c_lower == 'delay hours' and s_val not in ['', '-', '0:00']:
            if not s_val.startswith('-'):
                try:
                    parts = s_val.split(':')
                    if (int(parts[0]) + int(parts[1]) / 60.0) > 0.25:
                        return tone_css('red')
                except:
                    pass
            return tone_css('green')

        if pct is not None and 'late' in c_lower:
            return tone_css('red' if pct > 0 else 'muted')
        if pct is not None and ('previous 7 days' in c_lower or 'current 7 days' in c_lower or 'all available' in c_lower) and 'on-time' in c_lower:
            return tone_css('green' if pct > 0 else 'muted')

        if '%' in c_lower and pct is not None:
            if pct == 0:
                return tone_css('muted')
            if any(k in c_lower for k in ['achievement', 'ontime', 'on-time']):
                return tone_css('green' if pct >= 95 else ('yellow' if pct >= 80 else 'red'))
            return tone_css('muted')

        return ''

    styled = df_in.style.set_properties(**{
        'background-color': selected_theme['card1'],
        'color': selected_theme['text'],
        'border-color': selected_theme['line'],
        'font-size': '12px',
        'padding': '7px 9px',
        'text-align': 'center',
        'vertical-align': 'middle'
    }).set_table_styles([
        {'selector': 'th', 'props': [
            ('background-color', selected_theme['card2']), ('color', selected_theme['text']),
            ('font-weight', '700'), ('border-color', selected_theme['line']),
            ('padding', '8px 9px'), ('text-align', 'center')
        ]},
        {'selector': 'td', 'props': [('border-color', selected_theme['line']), ('text-align', 'center'), ('vertical-align', 'middle')]},
    ], overwrite=False)
    for col in df_in.columns:
        if hasattr(styled, 'map'):
            styled = styled.map(lambda x, c=col: ui_cell_color(x, c), subset=[col])
        else:
            styled = styled.applymap(lambda x, c=col: ui_cell_color(x, c), subset=[col])
    status_cols = [col for col in ['Payment Group', 'Operations Outcome', 'Remark with 15 min waiver', 'Remark', 'Dep_Status', 'Arr_Status'] if col in df_in.columns]
    status_text = df_in[status_cols].fillna('').astype(str).apply(lambda col: col.str.lower()) if status_cols else pd.DataFrame(index=df_in.index)
    def contains_status(pattern):
        if status_text.empty:
            return pd.Series(False, index=df_in.index)
        return status_text.apply(lambda col: col.str.contains(pattern, regex=True, na=False)).any(axis=1)
    row_tones = pd.Series('', index=df_in.index, dtype=object)
    payment_good = contains_status(r'^paid$|paid achievement|payment completed')
    row_tones.loc[payment_good] = 'green'
    row_tones.loc[contains_status(r'payment pending|finance pending|finance hold|cost control pending|in-transit')] = 'yellow'
    row_tones.loc[contains_status(r'late dep, ontime arr')] = 'yellow'
    row_tones.loc[contains_status(r'ontime dep, ontime arr|ontime arrival')] = 'green'
    row_tones.loc[contains_status(r'ontime dep, late arr')] = 'soft_red'
    # Apply exact paired Remark outcomes last, so a mixed row follows its actual trip result.
    row_tones.loc[contains_status(r'late dep, in-transit')] = 'yellow'
    row_tones.loc[contains_status(r'late dep, late arr|^draft$|late arrival|late departure|no dep|no arrival')] = 'red'
    row_tones.loc[contains_status(r'missing sch|missing schedule')] = 'yellow'
    row_tones.loc[contains_status(r'payment pending / paid')] = 'green'
    row_tones.loc[contains_status(r'finance hold')] = 'red'
    row_tones.loc[contains_status(r'^other$')] = 'yellow'
    if 'Utilization Class' in df_in.columns:
        util_class = df_in['Utilization Class'].fillna('').astype(str).str.lower()
        row_tones.loc[util_class.str.contains('efficiently', na=False)] = 'green'
        row_tones.loc[util_class.str.contains('underutilized', na=False)] = 'red'
    row_style = pd.DataFrame('', index=df_in.index, columns=df_in.columns)
    for tone in ['green', 'soft_red', 'red', 'yellow', 'purple', 'muted']:
        row_style.loc[row_tones.eq(tone), :] = tone_css(tone)
    styled = styled.apply(lambda col: row_style[col.name], axis=0)
    return styled

def write_styled_sheet_to_excel(writer, df_in, sheet_name, sheet_type="generic", preserve_order=False):
    df = clean_dataframe_for_excel(df_in, sheet_type=sheet_type, preserve_order=preserve_order)
    if not df.empty and df.columns.duplicated().any():
        df = df.loc[:, ~df.columns.duplicated()].copy()
    workbook = writer.book
    worksheet = workbook.add_worksheet(sheet_name)
    writer.sheets[sheet_name] = worksheet
    
    header_fmt = workbook.add_format({
        'bold': True, 'bg_color': '#1E3A8A', 'font_color': 'white',
        'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True
    })
    cell_fmt = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter'})
    center_fmt = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter'})
    muted_fmt = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_color': '#9CA3AF'})
    
    green_fmt = workbook.add_format({
        'border': 1, 'bg_color': '#D4EDDA', 'font_color': '#155724',
        'bold': True, 'align': 'center', 'valign': 'vcenter'
    })
    red_fmt = workbook.add_format({
        'border': 1, 'bg_color': '#F8D7DA', 'font_color': '#721C24',
        'bold': True, 'align': 'center', 'valign': 'vcenter'
    })
    soft_red_fmt = workbook.add_format({
        'border': 1, 'bg_color': '#FFF1F2', 'font_color': '#9F1239',
        'bold': True, 'align': 'center', 'valign': 'vcenter'
    })
    yellow_fmt = workbook.add_format({
        'border': 1, 'bg_color': '#FFF3CD', 'font_color': '#856404',
        'bold': True, 'align': 'center', 'valign': 'vcenter'
    })
    purple_fmt = workbook.add_format({
        'border': 1, 'bg_color': '#E2D9F3', 'font_color': '#4A148C',
        'bold': True, 'align': 'center', 'valign': 'vcenter'
    })
    blue_bold_fmt = workbook.add_format({
        'border': 1, 'bg_color': '#DBEAFE', 'font_color': '#1E3A8A',
        'bold': True, 'align': 'center', 'valign': 'vcenter'
    })
    total_row_fmt = workbook.add_format({
        'bold': True, 'bg_color': '#E2E8F0', 'font_color': '#0F172A',
        'border': 1, 'align': 'center', 'valign': 'vcenter'
    })
    row_green_fmt = workbook.add_format({'border': 1, 'bg_color': '#E2F0D9', 'font_color': '#1F4E2B', 'align': 'center', 'valign': 'vcenter'})
    row_red_fmt = workbook.add_format({'border': 1, 'bg_color': '#FCE4D6', 'font_color': '#7F1D1D', 'align': 'center', 'valign': 'vcenter'})
    row_soft_red_fmt = workbook.add_format({'border': 1, 'bg_color': '#FFF1F2', 'font_color': '#9F1239', 'align': 'center', 'valign': 'vcenter'})
    row_yellow_fmt = workbook.add_format({'border': 1, 'bg_color': '#FFF2CC', 'font_color': '#7F6000', 'align': 'center', 'valign': 'vcenter'})
    row_purple_fmt = workbook.add_format({'border': 1, 'bg_color': '#E4DFEC', 'font_color': '#4C2A69', 'align': 'center', 'valign': 'vcenter'})

    if df.empty:
        worksheet.write(0, 0, "No Data Available", header_fmt)
        return

    worksheet.set_row(0, 26)
    for col_idx, col_name in enumerate(df.columns):
        worksheet.write(0, col_idx, str(col_name), header_fmt)

    for row_idx, (_, row) in enumerate(df.iterrows(), start=1):
        is_total_row = any(str(row.get(k, '')).upper() in ['TOTAL', 'GRAND TOTAL'] for k in ['VendorRO', 'RO Name', 'Route Path', 'Origin RO'])
        row_labels = ' '.join(str(row.get(col, '')).strip().lower() for col in ['Payment Group', 'Operations Outcome', 'Remark with 15 min waiver', 'Remark', 'Status'] if col in row.index)
        if 'late dep, late arr' in row_labels or 'late arrival' in row_labels or 'no dep' in row_labels:
            row_status_fmt = row_red_fmt
        elif 'ontime dep, late arr' in row_labels:
            row_status_fmt = row_soft_red_fmt
        elif 'late dep, in-transit' in row_labels or 'ontime dep, in-transit' in row_labels or 'missing sch' in row_labels or 'missing schedule' in row_labels:
            row_status_fmt = row_yellow_fmt
        elif 'ontime dep, ontime arr' in row_labels or 'ontime arrival' in row_labels or 'payment pending / paid' in row_labels or 'paid' in row_labels:
            row_status_fmt = row_green_fmt
        elif 'other' in row_labels or 'draft' in row_labels or 'late departure' in row_labels or 'missing' in row_labels:
            row_status_fmt = row_red_fmt
        elif 'finance pending' in row_labels or 'finance hold' in row_labels or 'cost control pending' in row_labels or 'in-transit' in row_labels:
            row_status_fmt = row_yellow_fmt
        elif 'late dep, ontime arr' in row_labels:
            row_status_fmt = row_purple_fmt
        else:
            row_status_fmt = None
        for col_idx, col_name in enumerate(df.columns):
            val = row[col_name]
            if pd.isna(val):
                val_str = ""
            elif isinstance(val, float) and val.is_integer():
                val_str = int(val)
            else:
                val_str = val
                
            s_val = str(val_str).strip()
            s_lower = s_val.lower()
            c_lower = str(col_name).lower()
            
            chosen_fmt = total_row_fmt if is_total_row else (row_status_fmt or cell_fmt)
            
            if not is_total_row:
                if any(k in c_lower for k in ['payment pending / paid', 'payment pending', 'paid achievement']):
                    chosen_fmt = green_fmt if (parse_pct_from_str(s_val) or 0) > 0 or (s_val.isdigit() and int(s_val) > 0) else muted_fmt
                elif 'other' in c_lower or 'draft' in c_lower:
                    chosen_fmt = red_fmt if (parse_pct_from_str(s_val) or 0) > 0 or (s_val.isdigit() and int(s_val) > 0) else muted_fmt
                elif 'cost control pending' in c_lower or 'finance pending' in c_lower or 'finance hold' in c_lower:
                    chosen_fmt = yellow_fmt if (parse_pct_from_str(s_val) or 0) > 0 or (s_val.isdigit() and int(s_val) > 0) else muted_fmt
                elif 'late dep, in-transit' in c_lower:
                    pct = parse_pct_from_str(s_val)
                    if pct is not None:
                        chosen_fmt = yellow_fmt if pct > 0 else muted_fmt
                elif 'ontime dep, late arr' in c_lower:
                    pct = parse_pct_from_str(s_val)
                    if pct is not None:
                        chosen_fmt = soft_red_fmt if pct > 0 else muted_fmt
                elif 'late dep, ontime arr' in c_lower:
                    pct = parse_pct_from_str(s_val)
                    if pct is not None:
                        chosen_fmt = purple_fmt if pct > 0 else muted_fmt
                elif 'late dep, late arr' in c_lower or 'late arrival' in c_lower or 'late departure' in c_lower:
                    pct = parse_pct_from_str(s_val)
                    if pct is not None:
                        chosen_fmt = red_fmt if pct > 0 else muted_fmt
                elif 'ontime dep, ontime arr' in c_lower or 'ontime arrival' in c_lower:
                    pct = parse_pct_from_str(s_val)
                    if pct is not None:
                        chosen_fmt = green_fmt if pct > 0 else muted_fmt
                elif 'missing schedule' in c_lower:
                    pct = parse_pct_from_str(s_val)
                    if pct is not None:
                        chosen_fmt = yellow_fmt if pct > 0 else muted_fmt
                elif 'no departure' in c_lower:
                    pct = parse_pct_from_str(s_val)
                    if pct is not None:
                        chosen_fmt = red_fmt if pct > 0 else muted_fmt
                elif 'on-time' in c_lower and 'departure' not in c_lower and any(period in c_lower for period in ['previous 7 days', 'current 7 days', 'all available']):
                    pct = parse_pct_from_str(s_val)
                    if pct is not None:
                        chosen_fmt = green_fmt if pct > 0 else muted_fmt
                elif 'ontime departure' in c_lower or ('on-time' in c_lower and 'departure' in c_lower):
                    pct = parse_pct_from_str(s_val)
                    if pct is not None:
                        chosen_fmt = green_fmt if pct >= 95 else (yellow_fmt if pct >= 80 else red_fmt)
                elif 'late' in c_lower:
                    pct = parse_pct_from_str(s_val)
                    if pct is not None:
                        chosen_fmt = red_fmt if pct > 0 else muted_fmt
                elif 'in-transit' in c_lower:
                    pct = parse_pct_from_str(s_val)
                    if pct is not None:
                        chosen_fmt = yellow_fmt if pct > 0 else muted_fmt
                elif 'remark' in c_lower:
                    if 'late dep, late arr' in s_lower or 'late arrival' in s_lower or 'no dep' in s_lower:
                        chosen_fmt = red_fmt
                    elif 'ontime dep, late arr' in s_lower:
                        chosen_fmt = soft_red_fmt
                    elif 'late dep, in-transit' in s_lower or 'ontime dep, in-transit' in s_lower or 'in-transit' in s_lower or 'missing sch' in s_lower:
                        chosen_fmt = yellow_fmt
                    elif 'ontime dep, ontime arr' in s_lower or 'ontime arrival' in s_lower:
                        chosen_fmt = green_fmt
                    elif 'late dep, ontime arr' in s_lower:
                        chosen_fmt = purple_fmt
                elif c_lower == 'delay hours' and s_val not in ['', '-', '0:00']:
                    if not s_val.startswith('-'):
                        try:
                            parts = s_val.split(':')
                            hrs_delay = int(parts[0]) + int(parts[1]) / 60.0
                            chosen_fmt = red_fmt if hrs_delay > 0.25 else green_fmt
                        except:
                            pass
                    else:
                        chosen_fmt = green_fmt
                elif 'overall util %' in c_lower:
                    pct = parse_pct_from_str(s_val)
                    if pct is not None and isinstance(val_str, (int, float)) and pct <= 1:
                        pct *= 100
                    if pct is not None:
                        chosen_fmt = red_fmt if pct < 60 else (yellow_fmt if pct < 80 else green_fmt)
                elif 'overall cpk' in c_lower:
                    chosen_fmt = blue_bold_fmt
                elif '1. user / draft pending' in c_lower:
                    try:
                        if float(val_str) > 0: chosen_fmt = red_fmt
                    except: pass
                elif '2. cost control pending' in c_lower or '3. finance pending' in c_lower:
                    try:
                        if float(val_str) > 0: chosen_fmt = yellow_fmt
                    except: pass
                elif c_lower in ['total_trips', 'total trips', 'legwise', 'date', 'mcd_startdate']:
                    chosen_fmt = center_fmt

            worksheet.write(row_idx, col_idx, val_str, chosen_fmt)

    for i, col in enumerate(df.columns):
        if not df.empty:
            _s_len = df.iloc[:, i].fillna('').astype(str).str.len().max()
            max_val_len = int(_s_len) if pd.notna(_s_len) else 10
        else:
            max_val_len = 10
        col_len = max(max_val_len, len(str(col))) + 3
        worksheet.set_column(i, i, min(col_len, 42))
    worksheet.autofilter(0, 0, len(df), max(len(df.columns) - 1, 0))
    worksheet.freeze_panes(1, 0)
    worksheet.set_landscape()
    worksheet.fit_to_pages(1, 0)
    worksheet.repeat_rows(0)
    worksheet.set_margins(0.25, 0.25, 0.4, 0.4)

def get_selected_cell_from_event(event, displayed_df):
    """Return (row index, column name) from a Streamlit dataframe selection event."""
    try:
        selection = getattr(event, 'selection', {})
        if not isinstance(selection, dict):
            selection = {name: getattr(selection, name, None) for name in ['rows', 'columns', 'cells']}
        cells = selection.get('cells') or []
        if cells:
            cell = cells[-1]
            if isinstance(cell, (tuple, list)) and len(cell) >= 2:
                row_idx, col_ref = cell[0], cell[1]
            else:
                row_text, col_text = str(cell).replace(':', ',').split(',', 1)
                row_idx, col_ref = int(row_text), col_text
            col_name = col_ref if isinstance(col_ref, str) and col_ref in displayed_df.columns else displayed_df.columns[int(col_ref)]
            return int(row_idx), col_name
        rows = selection.get('rows') or []
        if rows:
            cols = selection.get('columns') or []
            col_name = cols[-1] if cols and cols[-1] in displayed_df.columns else None
            return int(rows[-1]), col_name
    except Exception:
        pass
    return None, None


def compact_detail_frame(frame, kind):
    if frame is None or frame.empty:
        return pd.DataFrame()
    preferred_by_kind = {
        'ven_raw': ['Date', 'Remark with 15 min waiver', 'Origin RO', 'Route Path', 'Legwise', 'VendorName', 'Actual Arrival Time', 'Delay Hours', 'MasterCDNo'],
        'ops_raw': ['MCD_StartDate', 'Remark', 'Operations Outcome', 'Zone', 'Origin RO', 'Route Path', 'Legwise', 'Legs', 'CD_FromBranch', 'CD_ToBranch', 'MasterCDNo'],
        'pay_raw': ['Invoice Id', 'Invoice Date', 'RO Name', 'Zone', 'Vendor Name', 'Vendor Mapping Category', 'Category', 'Amount', 'Status', 'Payment Group', 'Pending With', 'Pending Since', 'Days Pending', 'Hold Key'],
        'cpk_raw': ['Date', 'RO_Clean', 'Final_Route', 'Final_Type', 'VendorName', 'Vehicle No', 'Cap', 'Wt', 'Trips', 'Cost']
    }
    cols = [col for col in preferred_by_kind.get(kind, list(frame.columns)) if col in frame.columns]
    out = frame.loc[:, cols].copy() if cols else frame.copy()
    for col in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[col]) or col in ['Date', 'Invoice Date', 'Base Date', 'Last Approved At', 'MCD_StartDate']:
            parsed = pd.to_datetime(out[col], dayfirst=True, errors='coerce')
            if pd.api.types.is_datetime64_any_dtype(out[col]) or parsed.notna().sum() >= max(1, int(out[col].notna().sum() * 0.7)):
                out[col] = parsed.dt.strftime('%d-%b-%Y').fillna('')
    return out.reset_index(drop=True)


def render_summary_with_raw_drilldown(summary, raw, title, raw_kind, key, match_columns=None):
    """A compact, selectable summary that opens only the clicked row's raw records below."""
    if summary is None or summary.empty:
        st.info(f'No {title.lower()} summary is available for this selection.')
        return
    display = summary.reset_index(drop=True).copy()
    try:
        event = st.dataframe(
            style_ui_dataframe(display), use_container_width=True, hide_index=True,
            on_select='rerun', selection_mode='single-cell', key=key
        )
    except TypeError:
        st.dataframe(style_ui_dataframe(display), use_container_width=True, hide_index=True)
        st.caption('Select a summary cell to open its focused raw records.')
        return
    row_idx, selected_col = get_selected_cell_from_event(event, display)
    if row_idx is None or not (0 <= row_idx < len(display)):
        st.caption('Click a count or percentage above to open the matching raw records.')
        return
    selected = display.iloc[row_idx]
    detail = raw.copy() if isinstance(raw, pd.DataFrame) else pd.DataFrame()
    match_pairs = match_columns or [
        ('Origin RO', 'Origin RO'), ('RO Name', 'RO Name'), ('VendorRO', 'RO_Clean'),
        ('Route Path', 'Route Path'), ('Route (UP/DOWN)', 'Final_Route'), ('Final_Route', 'Final_Route'),
        ('Route Pair', 'Final_Route'), ('Type', 'Final_Type'), ('Legwise', 'Legwise'),
        ('VendorName', 'VendorName'), ('Vendor(s)', 'VendorName'), ('Vendor Name', 'Vendor Name')
    ]
    for summary_col, raw_col in match_pairs:
        if summary_col in selected.index and raw_col in detail.columns:
            target = str(selected[summary_col]).strip()
            if target and target.casefold() not in ('nan', 'none', 'all', 'total', 'grand total'):
                detail = detail[detail[raw_col].fillna('').astype(str).str.strip().eq(target)].copy()
    clicked_metric = str(selected_col or '').strip().lower()
    if raw_kind == 'ven_raw':
        target_status = None
        if 'ontime arrival' in clicked_metric or 'on-time' in clicked_metric:
            target_status = 'Ontime Arrival'
        elif 'late arrival' in clicked_metric or clicked_metric.endswith(' late'):
            target_status = 'Late Arrival'
        elif 'in-transit' in clicked_metric:
            target_status = 'In-Transit'
        status_col = get_col(detail, ['Remark with 15 min waiver'])
        if target_status and status_col:
            detail = detail[detail[status_col].fillna('').astype(str).str.strip().str.casefold().eq(target_status.casefold())].copy()
    elif raw_kind == 'ops_raw':
        outcome_map = {
            'ontime dep, ontime arr': 'Ontime Dep, Ontime Arr',
            'ontime dep, late arr': 'Ontime Dep, Late Arr',
            'late dep, late arr': 'Late Dep, Late Arr',
            'late dep, ontime arr': 'Late Dep, Ontime Arr'
        }
        clicked_outcome = next((outcome for token, outcome in outcome_map.items() if token in clicked_metric), None)
        remark_col = get_col(detail, ['Remark'])
        if clicked_outcome and remark_col:
            detail = detail[detail[remark_col].fillna('').astype(str).str.contains(re.escape(clicked_outcome), case=False, na=False)].copy()
        elif clicked_outcome:
            dep_col, arr_col = get_col(detail, ['Dep_Status']), get_col(detail, ['Arr_Status'])
            if dep_col and arr_col:
                dep_wanted, arr_wanted = clicked_outcome.split(', ')
                detail = detail[
                    detail[dep_col].fillna('').astype(str).str.contains(dep_wanted.replace(' Dep', ''), case=False, na=False) &
                    detail[arr_col].fillna('').astype(str).str.contains(arr_wanted.replace(' Arr', ''), case=False, na=False)
                ].copy()
    st.markdown(f'#### {title} · {selected_col or "selected row"} detail · {len(detail):,} records')
    compact = compact_detail_frame(detail, raw_kind)
    if compact.empty:
        st.info('No matching raw rows were found for the selected summary line.')
        return
    render_centered_html_table(compact, height=380)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        write_styled_sheet_to_excel(writer, compact, 'Focused_Raw_Data', sheet_type=raw_kind)
    st.download_button(
        f'📥 Download {title} detail (formatted Excel)', data=buffer.getvalue(),
        file_name=f'{re.sub(r"[^A-Za-z0-9_-]+", "_", title)}_Detail.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        key=f'{key}_download'
    )


def add_total_row_cpk_df(df):
    if df is None or df.empty:
        return pd.DataFrame()
    df_c = df.copy()
    tot_trips = df_c['Total Trips'].sum() if 'Total Trips' in df_c.columns else 0
    tot_cap = df_c['Total Capacity'].sum() if 'Total Capacity' in df_c.columns else 0
    tot_wt = df_c['Total Carried Wt'].sum() if 'Total Carried Wt' in df_c.columns else 0
    tot_cost = df_c['Total Trip Cost'].sum() if 'Total Trip Cost' in df_c.columns else 0
    
    tot_cpk = tot_cost / tot_wt if tot_wt > 0 else 0
    tot_util = tot_wt / tot_cap if tot_cap > 0 else 0
    
    tot_dict = {c: '-' for c in df_c.columns}
    if 'VendorRO' in df_c.columns: tot_dict['VendorRO'] = 'TOTAL'
    if 'Route Path' in df_c.columns: tot_dict['Route Path'] = 'TOTAL'
    if 'Unique Vendors' in df_c.columns: tot_dict['Unique Vendors'] = df_c['Unique Vendors'].sum()
    if 'Total Trips' in df_c.columns: tot_dict['Total Trips'] = tot_trips
    if 'Total Capacity' in df_c.columns: tot_dict['Total Capacity'] = tot_cap
    if 'Total Carried Wt' in df_c.columns: tot_dict['Total Carried Wt'] = tot_wt
    if 'Total Trip Cost' in df_c.columns: tot_dict['Total Trip Cost'] = tot_cost
    if 'Overall CPK' in df_c.columns: tot_dict['Overall CPK'] = tot_cpk
    if 'Overall Util %' in df_c.columns: tot_dict['Overall Util %'] = tot_util
    if 'Route Pair' in df_c.columns: tot_dict['Route Pair'] = 'TOTAL'
    
    df_out = pd.concat([df_c, pd.DataFrame([tot_dict])], ignore_index=True)
    for col in ['Overall CPK', 'Total Trip Cost']:
        if col in df_out.columns:
            df_out[col] = df_out[col].apply(lambda x: f"₹{x:.2f}" if isinstance(x, (int, float)) else x)
    if 'Overall Util %' in df_out.columns:
        df_out['Overall Util %'] = df_out['Overall Util %'].apply(lambda x: f"{x * 100:.2f}%" if isinstance(x, (int, float)) else x)
    return df_out

def generate_vip_executive_report_to_disk(data_dict, output_path=None):
    with pd.ExcelWriter(output_path or FILE_MAP["EXECUTIVE_REPORT"], engine='xlsxwriter') as writer:
        if 'Legwise_Route_Summary' in data_dict:
            write_styled_sheet_to_excel(writer, data_dict['Legwise_Route_Summary'], 'Operations_Summary', sheet_type="ops_sum")
        if 'Legwise_Processed_Data' in data_dict:
            write_styled_sheet_to_excel(writer, data_dict['Legwise_Processed_Data'], 'Operations_Raw', sheet_type="ops_raw")
        if 'Vendor_Perf_Summary' in data_dict:
            write_styled_sheet_to_excel(writer, data_dict['Vendor_Perf_Summary'], 'Vendor_Perf_Summary', sheet_type="ven_sum")
        if 'Vendor_Perf_Raw' in data_dict:
            write_styled_sheet_to_excel(writer, data_dict['Vendor_Perf_Raw'], 'Vendor_Perf_Raw', sheet_type="ven_raw")
            
        if 'Master_Database' in data_dict and not data_dict['Master_Database'].empty:
            df_pay = data_dict['Master_Database'].copy()
            pvt = pd.pivot_table(df_pay, values='Invoice Id', index='RO Name', columns='Department Bucket', aggfunc='count', fill_value=0, margins=True, margins_name='Grand Total')
            cols_order = ["1. USER / DRAFT PENDING", "2. COST CONTROL PENDING", "3. FINANCE PENDING", "4. PAYMENT PENDING", "5. OTHER PENDING", "Grand Total"]
            existing_cols = [c for c in cols_order if c in pvt.columns]
            pvt = pvt.reindex(columns=existing_cols).reset_index()
            write_styled_sheet_to_excel(writer, pvt, 'Payment_Summary', sheet_type="pay_sum")
            write_styled_sheet_to_excel(writer, df_pay, 'Payment_Raw', sheet_type="pay_raw")

        if 'CPK_National_Zonal_Master' in data_dict and not data_dict['CPK_National_Zonal_Master'].empty:
            df_cpk1 = add_total_row_cpk_df(data_dict['CPK_National_Zonal_Master'].sort_values(by='Overall Util %', ascending=True))
            write_styled_sheet_to_excel(writer, df_cpk1, 'CPK_Nat_Zon', sheet_type="cpk")
        if 'CPK_Feeder_Regional' in data_dict and not data_dict['CPK_Feeder_Regional'].empty:
            df_cpk2 = add_total_row_cpk_df(data_dict['CPK_Feeder_Regional'].sort_values(by='Overall Util %', ascending=True))
            write_styled_sheet_to_excel(writer, df_cpk2, 'CPK_Feed_Reg', sheet_type="cpk")
        if 'CPK_Coloader' in data_dict and not data_dict['CPK_Coloader'].empty:
            df_cpk3 = add_total_row_cpk_df(data_dict['CPK_Coloader'].sort_values(by='Overall Util %', ascending=True))
            write_styled_sheet_to_excel(writer, df_cpk3, 'CPK_Coloader', sheet_type="cpk")
        if 'CPK_Raw_Data' in data_dict and not data_dict['CPK_Raw_Data'].empty:
            write_styled_sheet_to_excel(writer, data_dict['CPK_Raw_Data'], 'Network_Raw', sheet_type="cpk_raw")

# ==========================================
# 5. MAIN DATA PROCESSING (With Caching, Missing RO Fix & Vendor Grouping)
# ==========================================
# Removed ttl=3600 so data never disappears automatically while browser is open
def get_processed_data_cached(file_timestamps):
    data_for_export = {}
    
    ro_zone_map = {}
    branch_to_ro_map = {}
    branch_to_zone_map = {}
    
    if os.path.exists(FILE_MAP["BRANCH_MASTER"]):
        try:
            xl_brn = pd.ExcelFile(FILE_MAP["BRANCH_MASTER"], engine=_fast_excel_engine())
            sheet_to_read = "Sheet1" if "Sheet1" in xl_brn.sheet_names else xl_brn.sheet_names[0]
            df_brn_master = xl_brn.parse(sheet_to_read)
            df_brn_master.columns = df_brn_master.columns.astype(str).str.strip()
            
            brn_col_m = next((c for c in df_brn_master.columns if 'branchcode' in c.lower().replace(' ', '')), 'RPTBranchcode')
            ro_col_m = next((c for c in df_brn_master.columns if 'rptro' in c.lower().replace(' ', '')), 'RPTRO')
            zone_col_m = next((c for c in df_brn_master.columns if 'zone' in c.lower().replace(' ', '')), 'Zone')
            
            df_brn_master['BRN_CLEAN'] = df_brn_master[brn_col_m].astype(str).str.strip().str.upper()
            df_brn_master['RO_CLEAN'] = df_brn_master[ro_col_m].astype(str).str.strip().str.upper()
            df_brn_master['ZONE_CLEAN'] = df_brn_master[zone_col_m].astype(str).str.strip().str.upper()
            
            valid_brn = df_brn_master[
                (~df_brn_master['RO_CLEAN'].isin(['', 'NAN', 'NONE']))
                & (~df_brn_master['BRN_CLEAN'].isin(['', 'NAN', 'NONE']))
            ]
            ro_zone_map = valid_brn.drop_duplicates(subset=['RO_CLEAN']).set_index('RO_CLEAN')['ZONE_CLEAN'].to_dict()
            
            unique_branches = valid_brn.drop_duplicates(subset=['BRN_CLEAN'])
            branch_to_ro_map = unique_branches.set_index('BRN_CLEAN')['RO_CLEAN'].to_dict()
            branch_to_zone_map = unique_branches.set_index('BRN_CLEAN')['ZONE_CLEAN'].to_dict()
        except Exception as e:
            logging.warning(f"Branch master read warning: {e}")

    # --- MODULE 0: PAYMENT DATA ---
    if os.path.exists(FILE_MAP["PAYMENT"]):
        df_pay = read_payment_sheet_cached(FILE_MAP["PAYMENT"], file_version(FILE_MAP["PAYMENT"]), "Report")
        df_pay.columns = df_pay.columns.astype(str).str.strip().str.upper().str.replace(" ", "").str.replace("_", "")
        
        rename_dict = {}
        for col in df_pay.columns:
            if 'ROSELECTION' in col: rename_dict[col] = 'RO Name'
            elif 'CATEGORY' in col: rename_dict[col] = 'Category'
            elif 'VENDORNAME' in col: rename_dict[col] = 'Vendor Name'
            elif 'INVOICEID' in col: rename_dict[col] = 'Invoice Id'
            elif 'INVOICEDATE' in col: rename_dict[col] = 'Invoice Date'
            elif 'AMOUNT' == col: rename_dict[col] = 'Amount'
            elif 'STATUS' == col: rename_dict[col] = 'Status'
            elif 'PENDINGWITH' in col: rename_dict[col] = 'Pending With'
            elif 'LASTAPPROVEDAT' in col: rename_dict[col] = 'Last Approved At'
            elif 'FINANCEREVERTREMARKS1' in col: rename_dict[col] = 'Finance Revert Remarks 1'
            elif 'APPROVERREVERTREMARKS' in col: rename_dict[col] = 'Approver Revert Remarks'
            elif 'HOLD.KEY' in col or 'HOLDKEY' in col: rename_dict[col] = 'Hold Key'
            elif 'NAME' == col or 'UPLOADERNAME' in col or 'BILLUPLOADER' in col: rename_dict[col] = 'Bill Uploader'

        df_pay.rename(columns=rename_dict, inplace=True)
        
        required_cols = ['RO Name', 'Category', 'Vendor Name', 'Invoice Id', 'Invoice Date', 'Amount', 'Status', 'Pending With', 'Last Approved At', 'Finance Revert Remarks 1', 'Approver Revert Remarks', 'Hold Key', 'Bill Uploader']
        for req in required_cols:
            if req not in df_pay.columns:
                df_pay[req] = ""
                
        df_pay['Vendor Name'] = df_pay['Vendor Name'].fillna('').apply(normalize_vendor_name)
        df_pay['Category'] = df_pay['Category'].fillna('').astype(str).str.strip()
        df_pay['Status'] = df_pay['Status'].fillna('').astype(str).str.upper()
        df_pay['Pending With'] = df_pay['Pending With'].fillna('').astype(str).str.upper()
        
        df_pay['RO Name Clean'] = df_pay['RO Name'].astype(str).str.strip().str.upper()
        df_pay['Zone'] = df_pay['RO Name Clean'].map(ro_zone_map).fillna('UNKNOWN ZONE')
        
        valid_cats = [
            "Contract - Feeder Connection vehicle charges",
            "Market - Feeder Connection vehicle charges", 
            "Market Vehicle Hired -Linehaul",
            "Contract Network Vehicle Hired - Regional", 
            "Contract Network Vehicle Hired - Zonal",
            "Contract Network Vehicle Hired - National"
        ]
        df_pay = df_pay[df_pay['Category'].isin(valid_cats)]
        
        vip_vends = [
            "SHRI GANPATI", "MOHD ASLAM", "MEHTAROAD", "E WHEELS", "TEJAS", "T T TRANSPORT", 
            "APL EXPRESS", "GOTRUCKS", "RADHA RANI", "FASTLANE", "MMM LOGISTICS", "ATA ROADWAYS", "ZAST", "FLEETX"
        ]
        df_pay = df_pay[~df_pay['Vendor Name'].str.contains('|'.join(vip_vends), na=False, regex=True)].copy()
        df_pay = df_pay[~df_pay['Status'].str.contains('PAID|PROCESSED|CANCELLED|DECLINED', na=False)]
        
        df_pay['Finance Revert Remarks 1'] = df_pay.get('Finance Revert Remarks 1', pd.Series(['']*len(df_pay))).fillna('')
        df_pay['Approver Revert Remarks'] = df_pay.get('Approver Revert Remarks', pd.Series(['']*len(df_pay))).fillna('')
        df_pay['Revert Remarks'] = np.where(df_pay['Finance Revert Remarks 1'] != '', df_pay['Finance Revert Remarks 1'], df_pay['Approver Revert Remarks'])
        
        conds = [
            (df_pay['Status'].str.contains('PAYMENT') | df_pay['Pending With'].str.contains('PAYMENT')),
            (df_pay['Status'].str.contains('FINANCE') | df_pay['Pending With'].str.contains('FINANCE|LEVEL 3') | df_pay['Status'].str.contains('HOLD')),
            (df_pay['Revert Remarks'] != '') | (df_pay['Status'].str.contains('DRAFT')) | (df_pay['Pending With'].str.contains('AJAY')),
            (df_pay['Status'].str.contains('PENDING') | df_pay['Pending With'].str.contains('COST CONTROL|OPSACCTS|ACC'))
        ]
        df_pay['Department Bucket'] = np.select(
            conds,
            ["4. PAYMENT PENDING", "3. FINANCE PENDING", "1. USER / DRAFT PENDING", "2. COST CONTROL PENDING"],
            "5. OTHER PENDING"
        )
        
        today = pd.to_datetime('today').normalize()
        df_pay['Last Approved At'] = pd.to_datetime(df_pay['Last Approved At'], dayfirst=True, errors='coerce').dt.normalize()
        df_pay['Invoice Date'] = pd.to_datetime(df_pay['Invoice Date'], dayfirst=True, errors='coerce').dt.normalize()
        df_pay['Base Date'] = df_pay['Last Approved At'].combine_first(df_pay['Invoice Date']).fillna(today)
        df_pay['Days Pending'] = (today - df_pay['Base Date']).dt.days
        df_pay['Aging Bucket'] = np.where(df_pay['Days Pending'] <= 5, "1. 0-5 Days", "2. >5 Days")
        df_pay['Base Date'] = df_pay['Base Date'].dt.strftime('%d-%b-%Y').fillna("")
        df_pay['Invoice Month'] = df_pay['Invoice Date'].dt.strftime('%b-%Y').fillna("UNKNOWN")
        
        df_master = df_pay[["Zone", "RO Name", "Category", "Vendor Name", "Bill Uploader", "Invoice Id", "Hold Key", "Aging Bucket", "Invoice Month", "Days Pending", "Status", "Pending With", "Revert Remarks", "Department Bucket", "Amount", "Base Date"]]
        data_for_export['Master_Database'] = df_master
        del df_pay
        gc.collect()

    # --- MODULE 1: LEGWISE OPERATIONS & VENDOR PERFORMANCE ---
    if os.path.exists(FILE_MAP["LEGWISE"]) and os.path.exists(FILE_MAP["ROUTE_MASTER"]) and os.path.exists(FILE_MAP["BRANCH_MASTER"]):
        df_leg_all = _read_excel_fast(FILE_MAP["LEGWISE"], sheet_name="Sheet1")
        df_rte = _read_excel_fast(FILE_MAP["ROUTE_MASTER"], sheet_name="RoutePathReportModel")
        
        df_rte_tat = df_rte.copy()
        df_rte_tat['Dep_Hrs'] = df_rte_tat['Schedule Departure Time'].apply(time_to_hrs)
        df_rte_tat['Arr_Hrs'] = df_rte_tat['Schedule Arrival Time'].apply(time_to_hrs)
        df_rte_tat['Day_Offset'] = df_rte_tat['Route Day'].apply(get_day_offset)
        df_rte_tat['Abs_Dep'] = df_rte_tat['Day_Offset'] + df_rte_tat['Dep_Hrs']
        df_rte_tat['Abs_Arr'] = df_rte_tat['Day_Offset'] + df_rte_tat['Arr_Hrs']
        
        route_tat_master = df_rte_tat.groupby('Route Code').agg(Min_Dep=('Abs_Dep', 'min'), Max_Arr=('Abs_Arr', 'max')).reset_index()
        route_tat_master['Master_Sch_E2E_Hrs'] = route_tat_master['Max_Arr'] - route_tat_master['Min_Dep']
        route_tat_master['Scheduled TAT Till Destination'] = route_tat_master['Master_Sch_E2E_Hrs'].apply(format_hrs_safe)

        df_leg_all.columns = df_leg_all.columns.str.strip()
        if 'VendorName' in df_leg_all.columns:
            df_leg_all['VendorName'] = df_leg_all['VendorName'].apply(normalize_vendor_name)
        df_leg_all['MCD_StartDate_DT'] = pd.to_datetime(df_leg_all['MCD_StartDate'], dayfirst=True, errors='coerce')
        df_leg_all['Leg_Num'] = df_leg_all['Legwise'].astype(str).str.extract(r'(\d+)')[0].astype(float).fillna(1)
        
        df_leg_all = df_leg_all.sort_values(by=['RouteCode', 'MCD_StartDate_DT', 'Min_CD_StartDatetime'])
        dedup = df_leg_all.groupby(['RouteCode', 'MCD_StartDate_DT'])['MasterCDNo'].first().reset_index()
        df_leg_all = df_leg_all.merge(dedup, on=['RouteCode', 'MCD_StartDate_DT', 'MasterCDNo'])
        df_leg_all['Legs'] = df_leg_all['CD_FromBranch'].astype(str).str.strip() + " to " + df_leg_all['CD_ToBranch'].astype(str).str.strip()
        df_leg_all.rename(columns={'Min_CD_StartDatetime': 'Actual Departure Time', 'Max_CD_EndDatetime': 'Actual Arrival Time', 'Route': 'Route Path'}, inplace=True)
        
        df_leg_all[['Origin', 'Destination']] = df_leg_all['Route Path'].apply(lambda x: pd.Series(extract_orig_dest(x)))
        df_leg_all['CD_FromBranch_Clean'] = df_leg_all['CD_FromBranch'].astype(str).str.strip().str.upper()
        df_leg_all['CD_ToBranch_Clean'] = df_leg_all['CD_ToBranch'].astype(str).str.strip().str.upper()
        df_leg_all['Origin_Clean'] = df_leg_all['Origin'].astype(str).str.strip().str.upper()

        # Each leg belongs to the RO mapped to that row's origin branch.
        df_leg_all['Origin RO'] = (
            df_leg_all['CD_FromBranch_Clean'].map(branch_to_ro_map).fillna('UNMAPPED')
        )

        def resolve_zone(row):
            ro_val = row['Origin RO']
            if ro_val in ro_zone_map and ro_zone_map[ro_val]:
                return ro_zone_map[ro_val]
            for code in [row['Origin_Clean'], row['CD_FromBranch_Clean'], row['CD_ToBranch_Clean']]:
                if code in branch_to_zone_map and branch_to_zone_map[code]:
                    return branch_to_zone_map[code]
            return "NORTH"

        df_leg_all['Zone'] = df_leg_all.apply(resolve_zone, axis=1)
        df_leg_all.drop(columns=['CD_ToBranch_Clean', 'Origin_Clean'], inplace=True, errors='ignore')
        
        df_leg_all['E2E_Pair'] = df_leg_all['Route Path'].apply(get_route_pair)
        df_leg_all.rename(columns={'LH_Type': 'LH Type'}, inplace=True)
        df_leg_all = df_leg_all.merge(route_tat_master[['Route Code', 'Scheduled TAT Till Destination']], left_on='RouteCode', right_on='Route Code', how='left')
        
        def get_sch_time(r, day_c, time_c):
            try:
                if pd.isna(r['MCD_StartDate_DT']) or pd.isna(r[day_c]):
                    return pd.NaT
                day_offset = float(r[day_c])
                d = r['MCD_StartDate_DT'] + pd.to_timedelta(day_offset, unit='D')
                t_str = str(r[time_c]).strip()
                if t_str == 'nan' or not t_str:
                    return pd.NaT
                return pd.to_datetime(d.strftime('%Y-%m-%d') + ' ' + str(pd.to_datetime(t_str).time()))
            except:
                return pd.NaT

        df_rte['Route Branch Code'] = df_rte['Route Branch Code'].astype(str).str.strip()
        df_rte = df_rte[['Route Code', 'Route Branch Code', 'Route Day', 'Schedule Departure Time', 'Schedule Arrival Time']]
        df_leg_all = df_leg_all.merge(df_rte, left_on=['RouteCode', 'CD_FromBranch'], right_on=['Route Code', 'Route Branch Code'], how='left')
        df_leg_all.rename(columns={'Route Day': 'Dep_Route_Day', 'Schedule Departure Time': 'Sch_Dep_Time_Raw'}, inplace=True)
        df_leg_all.drop(columns=['Schedule Arrival Time'], inplace=True, errors='ignore')
        
        df_leg_all = df_leg_all.merge(df_rte[['Route Code', 'Route Branch Code', 'Route Day', 'Schedule Arrival Time']], left_on=['RouteCode', 'CD_ToBranch'], right_on=['Route Code', 'Route Branch Code'], how='left')
        df_leg_all.rename(columns={'Route Day': 'Arr_Route_Day', 'Schedule Arrival Time': 'Sch_Arr_Time_Raw'}, inplace=True)

        df_leg_all['Scheduled Departure Time'] = df_leg_all.apply(lambda r: get_sch_time(r, 'Dep_Route_Day', 'Sch_Dep_Time_Raw'), axis=1)
        df_leg_all['Scheduled Arrival Time'] = df_leg_all.apply(lambda r: get_sch_time(r, 'Arr_Route_Day', 'Sch_Arr_Time_Raw'), axis=1)
        df_leg_all['Actual Departure Time'] = pd.to_datetime(df_leg_all['Actual Departure Time'], dayfirst=True, errors='coerce')
        df_leg_all['Actual Arrival Time'] = pd.to_datetime(df_leg_all['Actual Arrival Time'], dayfirst=True, errors='coerce')
        
        # VENDOR PERFORMANCE
        df_vperf = df_leg_all.copy()
        df_vperf['Given_Secs'] = (df_vperf['Scheduled Arrival Time'] - df_vperf['Scheduled Departure Time']).dt.total_seconds()
        df_vperf['Actual_Secs'] = (df_vperf['Actual Arrival Time'] - df_vperf['Actual Departure Time']).dt.total_seconds()
        
        df_vperf['Given Driving Hours_Raw'] = df_vperf['Given_Secs'] / 3600.0
        df_vperf['Actual Driving Hours_Raw'] = df_vperf['Actual_Secs'] / 3600.0
        df_vperf['Delay Hours_Raw'] = df_vperf['Actual Driving Hours_Raw'] - df_vperf['Given Driving Hours_Raw']
        
        vendor_arrival_missing = df_vperf['Actual Arrival Time'].isna()
        vendor_schedule_missing = df_vperf['Delay Hours_Raw'].isna()
        vendor_within_waiver = df_vperf['Delay Hours_Raw'].le(0.25)
        df_vperf['Remark with 15 min waiver'] = np.select(
            [vendor_arrival_missing, vendor_schedule_missing, vendor_within_waiver],
            ['In-Transit', 'Missing Schedule', 'Ontime Arrival'],
            default='Late Arrival'
        )
        df_vperf['Given Driving Hours'] = df_vperf['Given Driving Hours_Raw'].apply(format_hrs_safe)
        df_vperf['Actual Driving Hours'] = df_vperf['Actual Driving Hours_Raw'].apply(format_hrs_safe)
        df_vperf['Delay Hours'] = df_vperf['Delay Hours_Raw'].apply(format_hrs_safe)
        
        df_vperf['Actual Departure Time'] = df_vperf['Actual Departure Time'].dt.strftime('%d-%m-%Y %H:%M').fillna('-')
        df_vperf['Actual Arrival Time'] = df_vperf['Actual Arrival Time'].dt.strftime('%d-%m-%Y %H:%M').fillna('-')
        
        perf_cols = [
            'Route Path', 'Legwise', 'Legs', 'Actual Departure Time', 'Actual Arrival Time',
            'Given Driving Hours', 'Actual Driving Hours', 'Delay Hours',
            'Remark with 15 min waiver', 'VendorName', 'VehicleNo', 'MasterCDNo',
            'RouteCode', 'Zone', 'Origin RO'
        ]
        df_vperf_raw = df_vperf[perf_cols + ['MCD_StartDate_DT']].copy()
        df_vperf_raw['Date'] = df_vperf_raw['MCD_StartDate_DT'].dt.strftime('%d-%m-%Y')
        df_vperf_raw = df_vperf_raw.drop(columns=['MCD_StartDate_DT'])
        df_vperf_raw = sort_by_route_and_leg(df_vperf_raw)
        
        perf_sum = build_vendor_summary_from_raw(df_vperf_raw)
        
        data_for_export['Vendor_Perf_Summary'] = perf_sum
        data_for_export['Vendor_Perf_Raw'] = df_vperf_raw
        del df_vperf, df_vperf_raw, perf_sum
        
        # OPERATIONS EXCEPTION
        df_leg = df_leg_all[(df_leg_all['MCD_Created_By'] == 'SCHEDULED') & (df_leg_all['LH Type'].isin(['National LH', 'Zonal LH']))].copy()
        
        def calc_status_series(actual, scheduled, mode):
            delay_minutes = (actual - scheduled).dt.total_seconds() / 60
            missing_actual_status = f"No {mode}" if mode == 'Dep' else "In-Transit"
            return pd.Series(np.select(
                [actual.isna(), scheduled.isna(), delay_minutes.le(15)],
                [missing_actual_status, 'Missing Sch', f"Ontime {mode}"],
                default=f"Late {mode}"
            ), index=actual.index)

        df_leg['Dep_Status'] = calc_status_series(
            df_leg['Actual Departure Time'], df_leg['Scheduled Departure Time'], 'Dep'
        )
        df_leg['Arr_Status'] = calc_status_series(
            df_leg['Actual Arrival Time'], df_leg['Scheduled Arrival Time'], 'Arr'
        )
        df_leg['Remark'] = df_leg['Dep_Status'] + ", " + df_leg['Arr_Status']

        df_leg['Late Dep'] = df_leg['Remark'].str.contains('Late Dep', case=False, na=False).astype(int)
        df_leg['Late Arr'] = df_leg['Remark'].str.contains('Late Arr', case=False, na=False).astype(int)
        df_leg['Missing'] = df_leg['Remark'].str.contains('No Dep|Missing', case=False, na=False, regex=True).astype(int)

        leg_sum = build_ops_summary_from_raw(df_leg)
        data_for_export['Legwise_Route_Summary'] = leg_sum
        
        dt_cols = ['Scheduled Departure Time', 'Actual Departure Time', 'Scheduled Arrival Time', 'Actual Arrival Time']
        for c in dt_cols:
            df_leg[c] = df_leg[c].dt.strftime('%d-%m-%Y %H:%M').fillna('')
        df_leg['MCD_StartDate'] = pd.to_datetime(df_leg['MCD_StartDate_DT']).dt.strftime('%d-%m-%Y')
        df_leg_final = df_leg.drop(columns=['MCD_StartDate_DT'], errors='ignore')
        df_leg_final = sort_by_route_and_leg(df_leg_final)
        data_for_export['Legwise_Processed_Data'] = df_leg_final
        
        del df_leg, df_leg_all, df_rte, route_tat_master
        gc.collect()

    # --- MODULE 2: CPK AND UTILIZATION ---
    if os.path.exists(FILE_MAP["CPK_UTIL"]) and os.path.exists(FILE_MAP["ROUTE_LOOKUP"]):
        try:
            df_raw = _read_excel_fast(FILE_MAP["CPK_UTIL"], sheet_name='ContractVehicle_DetailReport')
        except:
            df_raw = _read_excel_fast(FILE_MAP["CPK_UTIL"])
            
        df_lookup = _read_excel_fast(FILE_MAP["ROUTE_LOOKUP"])
        df_raw.columns = df_raw.columns.astype(str).str.strip()
        df_lookup.columns = df_lookup.columns.astype(str).str.strip()
        if 'VehicleUsageType' in df_raw.columns:
            df_raw = df_raw[df_raw['VehicleUsageType'] != 'VehicleUsageType']
        if 'VendorName' in df_raw.columns:
            df_raw['VendorName'] = df_raw['VendorName'].apply(normalize_vendor_name)

        vno_col = get_col(df_raw, ['vehicleno', 'vehicle']) or 'VehicleNo'
        df_raw['Vehicle No'] = df_raw.get(vno_col, pd.Series(['Unlisted']*len(df_raw))).fillna('Unlisted')
        date_col = get_col(df_raw, ['date', 'mcd_startdate']) or 'Date'
        df_raw['Date'] = df_raw.get(date_col, pd.Series(['']*len(df_raw))).fillna('')
        
        raw_key_col = get_col(df_raw, ['refnumber', 'mastercdno', 'mcdno']) or 'RefNumber'
        lkp_key_col = get_col(df_lookup, ['mastercdno', 'mcdno']) or 'MasterCDNo'
        
        if raw_key_col in df_raw.columns and lkp_key_col in df_lookup.columns:
            df_raw['MergeKey'] = df_raw[raw_key_col].astype(str).str.strip().str.upper()
            df_lookup['MergeKey'] = df_lookup[lkp_key_col].astype(str).str.strip().str.upper()
            
            lkp_route_col = get_col(df_lookup, ['route', 'routepath', 'routes'])
            lkp_type_col = get_col(df_lookup, ['lh_type', 'lhtype', 'type'])
            lkp_from_col = get_col(df_lookup, ['mcd_frombranch', 'frombranch'])
            lkp_to_col = get_col(df_lookup, ['mcd_tobranch', 'tobranch'])
            
            cols_to_bring = ['MergeKey']
            if lkp_route_col: cols_to_bring.append(lkp_route_col)
            if lkp_type_col: cols_to_bring.append(lkp_type_col)
            if lkp_from_col: cols_to_bring.append(lkp_from_col)
            if lkp_to_col: cols_to_bring.append(lkp_to_col)
                
            lkp_sub = df_lookup[cols_to_bring].drop_duplicates(subset=['MergeKey'])
            
            rename_dict = {}
            if lkp_route_col: rename_dict[lkp_route_col] = 'LKP_ROUTE'
            if lkp_type_col: rename_dict[lkp_type_col] = 'LKP_TYPE'
            if lkp_from_col: rename_dict[lkp_from_col] = 'LKP_FROM'
            if lkp_to_col: rename_dict[lkp_to_col] = 'LKP_TO'
            lkp_sub.rename(columns=rename_dict, inplace=True)
            
            df_raw = df_raw.merge(lkp_sub, on='MergeKey', how='left')
            
            df_raw['Final_Route'] = df_raw.get('LKP_ROUTE', pd.Series([np.nan]*len(df_raw)))
            raw_route_col = get_col(df_raw, ['route', 'routepath', 'route(up/down)'])
            if raw_route_col:
                df_raw['Final_Route'] = df_raw['Final_Route'].combine_first(df_raw[raw_route_col])
                
            df_raw['Final_Type'] = df_raw.get('LKP_TYPE', pd.Series([np.nan]*len(df_raw)))
            raw_type_col = get_col(df_raw, ['type', 'vehicletype', 'category'])
            if raw_type_col:
                df_raw['Final_Type'] = df_raw['Final_Type'].combine_first(df_raw[raw_type_col])
                
            df_raw['Final_From'] = df_raw.get('LKP_FROM', pd.Series([np.nan]*len(df_raw)))
            df_raw['Final_To'] = df_raw.get('LKP_TO', pd.Series([np.nan]*len(df_raw)))
        else:
            df_raw['Final_Route'] = df_raw.get('Route', df_raw.get('Route Path', ''))
            df_raw['Final_Type'] = df_raw.get('Type', df_raw.get('VehicleType', 'Unlisted Type'))
            df_raw['Final_From'] = ''
            df_raw['Final_To'] = ''

        trips_col = get_col(df_raw, ['nooftrips', 'trips', 'noofdays'])
        cost_col = get_col(df_raw, ['totalcost', 'contractcost', 'amount'])
        wt_col = get_col(df_raw, ['totalwt', 'weight', 'mcdwt'])
        cap_col = get_col(df_raw, ['vehiclecapacity', 'capacity', 'vehcap'])

        df_raw['Trips'] = pd.to_numeric(df_raw[trips_col], errors='coerce').fillna(1) if trips_col else 1
        df_raw['Cost'] = pd.to_numeric(df_raw[cost_col], errors='coerce').fillna(0) if cost_col else 0
        df_raw['Wt'] = pd.to_numeric(df_raw[wt_col], errors='coerce').fillna(0) if wt_col else 0
        df_raw['Cap'] = pd.to_numeric(df_raw[cap_col], errors='coerce').fillna(0) if cap_col else 0

        df_raw['Final_Type'] = df_raw['Final_Type'].apply(lambda x: f"MCD-{x}" if isinstance(x, str) and "LH" in x.upper() and "MCD" not in x.upper() else x)
        df_raw['Final_Type'] = df_raw['Final_Type'].fillna('Unlisted Type')

        def fix_route(row):
            r = str(row.get('Final_Route', '')).strip()
            if pd.isna(r) or r.lower() in ['nan', 'na', '', 'manual']:
                b = str(row.get('VendorBranch', '')).strip()
                return b + " (Local)" if b and b.lower() not in ['nan', 'na', ''] else "Local Operations"
            return r
        df_raw['Final_Route'] = df_raw.apply(fix_route, axis=1)

        def create_sort_key(row):
            fb = str(row.get('Final_From', '')).strip().upper()
            tb = str(row.get('Final_To', '')).strip().upper()
            if fb and tb and fb != 'NAN' and tb != 'NAN':
                return f"{min(fb, tb)}-{max(fb, tb)}"
            r = str(row.get('Final_Route', '')).strip().upper()
            pts = r.replace(' TO ', '-').split('-')
            if len(pts) >= 2:
                return f"{min(pts[0].strip(), pts[-1].strip())}-{max(pts[0].strip(), pts[-1].strip())}"
            return r
            
        df_raw['SortKey'] = df_raw.apply(create_sort_key, axis=1)

        ro_col = get_col(df_raw, ['vendorro', 'ro']) or 'VendorRO'
        df_raw['RO_Clean'] = df_raw.get(ro_col, pd.Series(['UNKNOWN']*len(df_raw))).astype(str).str.upper().str.strip()
        df_raw['Zone'] = df_raw['RO_Clean'].map(ro_zone_map).fillna('UNKNOWN ZONE')
        
        target_ros = ['PATRO', 'CCURO', 'BBSRO', 'GAURO', 'MUMRO', 'DELRO', 'LKORO']
        
        df_raw['Date_DT'] = pd.to_datetime(df_raw['Date'], errors='coerce', dayfirst=True)
        if os.path.exists(FILE_MAP["RATE_CORRECTIONS"]):
            try:
                with open(FILE_MAP["RATE_CORRECTIONS"], 'r') as f:
                    corrections = json.load(f)
                for corr in corrections:
                    route_str = str(corr['route']).strip().upper()
                    cap_val = float(corr['capacity'])
                    new_cost = float(corr['new_cost'])
                    eff_date = pd.to_datetime(corr['eff_date'])
                    
                    route_mask = df_raw['Final_Route'].astype(str).str.upper() == route_str
                    cap_mask = pd.to_numeric(df_raw['Cap'], errors='coerce') == cap_val
                    date_mask = df_raw['Date_DT'] >= eff_date
                    
                    mask = route_mask & cap_mask & date_mask
                    df_raw.loc[mask, 'Cost'] = new_cost * df_raw.loc[mask, 'Trips']
            except Exception:
                pass 
        
        df_updn = df_raw[~df_raw['Final_Type'].str.upper().str.contains('OFD|PICKUP', na=False)].copy()
        target_keys = df_updn[df_updn['RO_Clean'].isin(target_ros)]['SortKey'].unique()
        df_updn = df_updn[df_updn['SortKey'].isin(target_keys)]
        
        df_updn['Final_Type'] = df_updn['Final_Type'].replace({
            'MCD-National LH': 'National LH',
            'MCD-Zonal LH': 'Zonal LH',
            'MCD-Regional LH': 'Regional LH',
            'MCD-Feeder': 'Feeder'
        })
        
        df_updn_save = df_updn.drop(columns=['Date_DT'], errors='ignore')
        data_for_export['CPK_Raw_Data'] = df_updn_save

        cpk_tables = build_cpk_tables_from_raw(df_updn_save)
        for k_cpk, v_cpk in cpk_tables.items():
            if not v_cpk.empty:
                data_for_export[k_cpk] = v_cpk

        del df_raw, df_lookup
        gc.collect()

    return data_for_export

def process_all_data():
    progress = st.progress(0)
    status_text = st.empty()
    temp_output = None
    data_for_export = None
    try:
        status_text.text("⚙️ Aggregating & Processing all files (Fast Low-RAM Engine)...")
        progress.progress(15)
        file_timestamps = {}
        for k, v in FILE_MAP.items():
            if os.path.exists(v):
                file_timestamps[k] = os.path.getmtime(v)

        data_for_export = get_processed_data_cached(file_timestamps)
        progress.progress(70)

        if not data_for_export:
            status_text.warning("No datasets were processed. Check the uploaded files.")
            return False

        # Pre-compute _OpsRemarkOutcome once so dashboard loads instantly
        if 'Legwise_Processed_Data' in data_for_export and not data_for_export['Legwise_Processed_Data'].empty:
            if '_OpsRemarkOutcome' not in data_for_export['Legwise_Processed_Data'].columns:
                data_for_export['Legwise_Processed_Data']['_OpsRemarkOutcome'] = ops_remark_outcome_series(
                    data_for_export['Legwise_Processed_Data']
                )

        status_text.text("⚙️ Saving Master Database (Streaming Low-RAM Mode)...")
        with tempfile.NamedTemporaryFile(dir=DATA_DIR, suffix='.xlsx', delete=False) as tmp:
            temp_output = tmp.name
        try:
            with pd.ExcelWriter(temp_output, engine='xlsxwriter', engine_kwargs={'options': {'constant_memory': True}}) as writer:
                for k, v in data_for_export.items():
                    v.to_excel(writer, sheet_name=k, index=False)
        except TypeError:
            with pd.ExcelWriter(temp_output, engine='xlsxwriter') as writer:
                for k, v in data_for_export.items():
                    v.to_excel(writer, sheet_name=k, index=False)
        os.replace(temp_output, FILE_MAP["FINAL_OUTPUT"])
        progress.progress(90)

        # Save instant binary pickle cache so switching modules is <0.1s with zero Excel re-read!
        status_text.text("⚙️ Saving Instant Fast-Cache...")
        mon_sig = ("mon_sheets_v2", file_version(FILE_MAP["FINAL_OUTPUT"]))
        _save_disk_pkl_cache(os.path.join(DATA_DIR, ".monitoring_sheets_fast_cache.pkl"), mon_sig, data_for_export)

        # Clear stale caches
        st.session_state.pop('_dashboard_cache', None)
        st.session_state.pop('_dashboard_page_cache', None)
        st.session_state.pop('_pay_prepared_frame_cache', None)
        st.session_state.pop('_download_version', None)
        st.session_state.pop('_vip_exec_report_ready', None)
        try:
            st.cache_data.clear()
        except Exception:
            pass

        del data_for_export
        data_for_export = None
        gc.collect()

        progress.progress(100)
        status_text.success("✅ All Data Processed Successfully! Loading Dashboard...")
        return True
    except Exception as e:
        logging.exception("Dashboard processing failed")
        status_text.error(f"Error during processing: {e}")
        st.exception(e)
        return False
    finally:
        if data_for_export is not None:
            del data_for_export
        if temp_output and os.path.exists(temp_output):
            try:
                os.remove(temp_output)
            except Exception:
                pass
        gc.collect()

# ==========================================
# 6. SIDEBAR: ADMIN PANEL & RATE CORRECTIONS
# ==========================================
st.sidebar.markdown(f"### Welcome, **{st.session_state.get('user_label', st.session_state['role'])}**")
st.sidebar.caption(f"ID: `{st.session_state.get('username')}` | Role: `{st.session_state.get('role')}`")
if st.sidebar.button("Logout", key="logout_btn", use_container_width=True):
    rotate_overall_issue_link_key()
    st.session_state['logged_in'] = False
    st.session_state['role'] = None
    st.session_state['username'] = None
    st.session_state['allowed_vendors'] = []
    st.session_state['allowed_modules'] = []
    st.rerun()

st.sidebar.markdown("---")

if st.session_state['role'] == 'Admin':
    st.sidebar.header("🛠 Data Management")
    
    # -------------------------------------------------------------
    # BRAND NEW ADMIN BUTTON TO REMOVE ALL EXCEL FILES
    # -------------------------------------------------------------
    if st.sidebar.button("🗑️ Remove Data", use_container_width=True):
        # Delete only uploaded/generated Excel files, preserve json configurations
        preserve_keys = ["USERS_DB", "ACTION_PLANS", "VENDOR_MASTER", "RATE_CORRECTIONS"]
        for k, v in FILE_MAP.items():
            if k not in preserve_keys:
                if os.path.exists(v):
                    try:
                        os.remove(v)
                    except:
                        pass
        
        # Clear specific uploader session states to show them empty again
        for key in list(st.session_state.keys()):
            if key.startswith("saved_upload_"):
                del st.session_state[key]
                
        for _cp in (".monitoring_sheets_fast_cache.pkl", ".payment_norm_fast_cache.pkl"):
            _fp = os.path.join(DATA_DIR, _cp)
            if os.path.exists(_fp):
                try: os.remove(_fp)
                except Exception: pass
        st.session_state.pop('_pay_prepared_frame_cache', None)
        st.session_state.pop('_dashboard_cache', None)
        st.session_state.pop('_dashboard_page_cache', None)
        try:
            st.cache_data.clear()
        except Exception:
            pass
        st.sidebar.success("Old Data Removed! You can paste new data now.")
        st.rerun()
        
    with st.sidebar.expander("📂 Upload Raw Files", expanded=False):
        f1 = st.file_uploader("1. Payment Data", type=['xlsx'])
        if save_file(f1, "PAYMENT"): st.success("Saved!")
        st.caption(f"Last updated: {get_file_time('PAYMENT')}")
        
        f2 = st.file_uploader("2. Legwise Report", type=['xlsx'])
        if save_file(f2, "LEGWISE"): st.success("Saved!")
        st.caption(f"Last updated: {get_file_time('LEGWISE')}")
        
        f3 = st.file_uploader("3. Scheduled Route Master — National and Zonal (single workbook)", type=['xlsx'])
        if save_file(f3, "ROUTE_MASTER"): st.success("Saved!")
        st.caption(f"Last updated: {get_file_time('ROUTE_MASTER')}")
        st.caption("This one workbook feeds Scheduled Route Master, scheduled departure/arrival, TAT, halting, and Vendor Performance. After replacing it, press PROCESS & REFRESH DATA to recalculate the other modules.")
        
        f4 = st.file_uploader("4. RO & Branch List", type=['xlsx'])
        if save_file(f4, "BRANCH_MASTER"): st.success("Saved!")
        st.caption(f"Last updated: {get_file_time('BRANCH_MASTER')}")
        
        f5 = st.file_uploader("5. MCD Vendor Monitoring", type=['xlsx'])
        if save_file(f5, "MCD_VENDOR"): st.success("Saved!")
        st.caption(f"Last updated: {get_file_time('MCD_VENDOR')}")
        
        f6 = st.file_uploader("6. CPK & Util Raw File", type=['xlsx'])
        if save_file(f6, "CPK_UTIL"): st.success("Saved!")
        st.caption(f"Last updated: {get_file_time('CPK_UTIL')}")
        
        f7 = st.file_uploader("7. Route Lookup File", type=['xlsx'])
        if save_file(f7, "ROUTE_LOOKUP"): st.success("Saved!")
        st.caption(f"Last updated: {get_file_time('ROUTE_LOOKUP')}")

    with st.sidebar.expander("💸 Rate Correction Master"):
        st.caption("Fix raw Vendor Rates dynamically before dashboard processes data.")
        with st.form("rate_form"):
            rc_route = st.text_input("Route (e.g. DELAP-PKLH-KLKH)")
            rc_cap = st.number_input("Vehicle Capacity", min_value=0)
            rc_cost = st.number_input("Corrected Trip Cost (₹)", min_value=0.0)
            rc_date = st.date_input("Effective From Date")
            submitted = st.form_submit_button("Save Rate Correction")
            
            if submitted:
                rate_file = FILE_MAP["RATE_CORRECTIONS"]
                rates = []
                if os.path.exists(rate_file):
                    try:
                        with open(rate_file, 'r') as f:
                            rates = json.load(f)
                    except:
                        pass
                rates.append({
                    "route": rc_route.strip(),
                    "capacity": rc_cap,
                    "new_cost": rc_cost,
                    "eff_date": rc_date.strftime('%Y-%m-%d')
                })
                with open(rate_file, 'w') as f:
                    json.dump(rates, f)
                st.success("✅ Correction Saved! Press Process & Refresh below.")

    st.sidebar.markdown("---")
    if st.sidebar.button("🚀 PROCESS & REFRESH DATA", use_container_width=True, type="primary"):
        st.session_state.pop('_dashboard_cache', None)
        st.session_state.pop('_dashboard_page_cache', None)
        try:
            st.cache_data.clear()
        except Exception:
            pass
        for _cp in (".monitoring_sheets_fast_cache.pkl", ".payment_norm_fast_cache.pkl"):
            _fp = os.path.join(DATA_DIR, _cp)
            if os.path.exists(_fp):
                try: os.remove(_fp)
                except Exception: pass
        st.session_state.pop('_pay_prepared_frame_cache', None)
        gc.collect()
        if process_all_data():
            try:
                st.query_params.clear()
            except Exception:
                pass
            st.session_state["ops_win_hide_sidebar"] = False
            st.session_state["ven_win_hide_sidebar"] = False
            st.session_state['_processing_success'] = True
            st.rerun()
        st.stop()

# ==========================================
# 7. DASHBOARD NAVIGATION & DATA LOADER
# ==========================================
def read_overall_issue_query_params():
    try:
        params = st.query_params
        def read_value(key):
            value = params.get(key, '')
            return str(value[0] if isinstance(value, (list, tuple)) and value else value or '')
    except Exception:
        try:
            params = st.experimental_get_query_params()
            def read_value(key):
                value = params.get(key, [''])
                return str(value[0] if isinstance(value, (list, tuple)) and value else value or '')
        except Exception:
            return {}
    return {key: read_value(key) for key in [
        'issues_raw', 'issues_auth', 'issues_ro', 'issues_route', 'issues_zone',
        'issues_type', 'issues_start', 'issues_end'
    ]}

MENU_SHEETS = {
    "📊 Operations Summary": ('Legwise_Route_Summary', 'Legwise_Processed_Data'),
    "🚚 Vendor Performance": ('Vendor_Perf_Summary', 'Vendor_Perf_Raw'),
    "💳 Payment Dashboard": ('Master_Database',),
    "📱 Communication Hub": (
        'Legwise_Route_Summary', 'Legwise_Processed_Data',
        'Vendor_Perf_Summary', 'Vendor_Perf_Raw',
        'Master_Database',
        'CPK_National_Zonal_Master', 'CPK_National_Zonal_UpDown',
        'CPK_Feeder_Regional', 'CPK_Coloader', 'CPK_Raw_Data'
    ),
    "💰 Network Utilization": (
        'CPK_National_Zonal_Master', 'CPK_National_Zonal_UpDown',
        'CPK_Feeder_Regional', 'CPK_Coloader', 'CPK_Raw_Data'
    ),
    "🧭 Scheduled Route Master": (),
    "⚠️ Overall Issues": ('Legwise_Processed_Data', 'Master_Database', 'CPK_Raw_Data'),
    "📝 Today's Call Action Plan": (
        'Legwise_Route_Summary', 'Vendor_Perf_Summary',
        'CPK_National_Zonal_Master', 'CPK_Feeder_Regional', 'CPK_Coloader'
    ),
    # Access control only needs distinct vendor names. Read those columns below
    # instead of loading both full raw sheets on every rerun.
    "🔐 User & Access Control": ()
}

# Dynamically filter Navigation menu based on user's allowed_modules
user_allowed_mods = st.session_state.get('allowed_modules', [])
menu = [m for m in MENU_SHEETS.keys() if m in user_allowed_mods]

# LOCK "User & Access Control" explicitly to 'admin' username only
if st.session_state.get('username') == 'admin' and "🔐 User & Access Control" not in menu:
    menu.append("🔐 User & Access Control")
if not menu:
    menu = ["🚚 Vendor Performance"]

def read_ops_remark_query_params():
    try:
        params = st.query_params
        def read_value(key):
            value = params.get(key, '')
            return str(value[0] if isinstance(value, (list, tuple)) and value else value or '')
    except Exception:
        try:
            params = st.experimental_get_query_params()
            def read_value(key):
                value = params.get(key, [''])
                return str(value[0] if isinstance(value, (list, tuple)) and value else value or '')
        except Exception:
            return {}
    return {key: read_value(key) for key in [
        'ops_raw', 'ops_auth', 'ops_outcome', 'ops_start', 'ops_end',
        'ops_zone', 'ops_ro', 'ops_vendor', 'ops_route', 'ops_leg', 'ops_search'
    ]}

def read_vendor_perf_query_params():
    try:
        params = st.query_params
        def read_value(key):
            value = params.get(key, '')
            return str(value[0] if isinstance(value, (list, tuple)) and value else value or '')
    except Exception:
        try:
            params = st.experimental_get_query_params()
            def read_value(key):
                value = params.get(key, [''])
                return str(value[0] if isinstance(value, (list, tuple)) and value else value or '')
        except Exception:
            return {}
    return {key: read_value(key) for key in [
        'ven_raw', 'ven_auth', 'ven_status', 'ven_start', 'ven_end',
        'ven_zone', 'ven_ro', 'ven_vendor', 'ven_route', 'ven_leg', 'ven_search'
    ]}

issue_query = read_overall_issue_query_params()
overall_issue_raw_view = issue_query.get('issues_raw') == '1'
ops_remark_query = read_ops_remark_query_params()
ops_remark_raw_view = ops_remark_query.get('ops_raw') == '1'
ven_perf_query = read_vendor_perf_query_params()
ven_perf_raw_view = ven_perf_query.get('ven_raw') == '1'

if ops_remark_raw_view and "_ops_win_nav_init" not in st.session_state:
    st.session_state["_ops_win_nav_init"] = True
    if "📊 Operations Summary" in menu:
        st.session_state["main_nav_radio"] = "📊 Operations Summary"
elif ven_perf_raw_view and "_ven_win_nav_init" not in st.session_state:
    st.session_state["_ven_win_nav_init"] = True
    if "🚚 Vendor Performance" in menu:
        st.session_state["main_nav_radio"] = "🚚 Vendor Performance"

choice = st.sidebar.radio("Navigation:", menu, key="main_nav_radio")

if ops_remark_raw_view and choice != "📊 Operations Summary":
    try:
        st.query_params.clear()
    except Exception:
        pass
    st.session_state.pop("_ops_win_nav_init", None)
    st.session_state["ops_win_hide_sidebar"] = False
    ops_remark_raw_view = False
    st.rerun()

if ven_perf_raw_view and choice != "🚚 Vendor Performance":
    try:
        st.query_params.clear()
    except Exception:
        pass
    st.session_state.pop("_ven_win_nav_init", None)
    st.session_state["ven_win_hide_sidebar"] = False
    ven_perf_raw_view = False
    st.rerun()

if overall_issue_raw_view:
    if st.session_state.get('role') != 'Admin' and "⚠️ Overall Issues" not in st.session_state.get('allowed_modules', []):
        st.error('Your account does not have access to Overall Issues details.')
        st.stop()
    choice = "⚠️ Overall Issues"
elif ops_remark_raw_view:
    if st.session_state.get('role') != 'Admin' and "📊 Operations Summary" not in st.session_state.get('allowed_modules', []):
        st.error('Your account does not have access to Operations Summary details.')
        st.stop()
    choice = "📊 Operations Summary"
elif ven_perf_raw_view:
    if st.session_state.get('role') != 'Admin' and "🚚 Vendor Performance" not in st.session_state.get('allowed_modules', []):
        st.error('Your account does not have access to Vendor Performance details.')
        st.stop()
    choice = "🚚 Vendor Performance"

def get_overall_issue_ro_zone_lookup(data=None):
    """Build RO-to-zone labels from the uploaded branch master and processed data."""
    lookup = {}
    for key in ['Master_Database', 'Legwise_Processed_Data', 'CPK_Raw_Data']:
        frame = (data or {}).get(key, pd.DataFrame())
        ro_col = get_col(frame, ['RO Name', 'Origin RO', 'VendorRO', 'RO_Clean', 'RO'])
        zone_col = get_col(frame, ['Zone'])
        if ro_col and zone_col:
            pairs = zip(_clean_ro_series(frame[ro_col]), frame[zone_col].fillna('').astype(str).str.strip().str.upper())
            for ro, zone in pairs:
                if ro and zone and zone not in ('NAN', 'NONE', 'UNKNOWN ZONE'):
                    lookup.setdefault(ro, zone)

    branch_path = FILE_MAP.get('BRANCH_MASTER')
    if branch_path and os.path.exists(branch_path):
        try:
            with pd.ExcelFile(branch_path, engine='openpyxl') as workbook:
                for sheet in workbook.sheet_names:
                    frame = workbook.parse(sheet)
                    ro_col = get_col(frame, ['RPTRO', 'RPTROCode', 'RO Name', 'RO Code', 'RO', 'Regional Office'])
                    zone_col = get_col(frame, ['Zone', 'Zone Name', 'Region'])
                    if not ro_col or not zone_col:
                        continue
                    for ro_value, zone_value in zip(frame[ro_col], frame[zone_col]):
                        ro = _clean_ro_series(pd.Series([ro_value])).iloc[0]
                        zone = str(zone_value).strip().upper() if pd.notna(zone_value) else ''
                        if ro and zone and zone not in ('NAN', 'NONE', 'UNKNOWN ZONE'):
                            lookup[ro] = zone
                    break
        except Exception as exc:
            logging.warning(f"Overall Issues branch-zone lookup warning: {exc}")
    return lookup

def normalize_overall_payment_raw(raw, data=None):
    """Keep all payment source fields needed for accurate buckets, Pending With, and Days Pending."""
    if raw is None or raw.empty:
        return pd.DataFrame(columns=[
            'Invoice Id', 'Invoice Date', 'Base Date', 'RO Name', 'Zone', 'Vendor Name',
            'Category', 'Amount', 'Status', 'Pending With', 'Bill Uploader', 'Hold Name', 'Hold Time'
        ])
    source = raw.copy()
    source.columns = source.columns.astype(str).str.strip()
    aliases = {
        'Invoice Id': ['Invoice Id', 'InvoiceID', 'Invoice Id No', 'Invoice No'],
        'Invoice Date': ['Invoice Date', 'InvoiceDate'],
        'Submitted At': ['Submitted At', 'SubmittedAt'],
        'RO Name': ['RO Name', 'ro_selection', 'ROSelection', 'RO'],
        'Vendor Name': ['Vendor Name', 'VendorName'],
        'Category': ['Category', 'Bill Category'],
        'Amount': ['Amount', 'Net Payable', 'net_payable'],
        'Status': ['Status', 'Invoice Status'],
        'Pending With': ['Pending With', 'PendingWith'],
        'Bill Uploader': ['Name', 'Bill Uploader', 'Uploader Name', 'UploaderName'],
        'Finance Name': ['Finance Name', 'FinanceName'],
        'Last Approved At': ['Last Approved At', 'LastApprovedAt'],
        'Finance Revert Remarks 1': ['Finance Revert Remarks 1', 'FinanceRevertRemarks1'],
        'Approver Revert Remarks': ['Approver Revert Remarks', 'ApproverRevertRemarks'],
        'Hold Name': ['hold.name', 'Hold Name', 'HoldName'],
        'Hold Key': ['hold-key', 'Hold Key', 'HoldKey'],
        'Hold Time': ['hold.time', 'Hold Time', 'HoldTime'],
        'Rev Action 1': ['approver_1_reverted_action'],
        'Rev Action 2': ['approver_2_reverted_action'],
        'Rev Action 3': ['approver_3_reverted_action'],
        'Rev Action 4': ['approver_4_reverted_action'],
        'Rev Action 5': ['approver_5_reverted_action'],
        'Partial Payment': ['Partial Payment', 'PartialPayment'],
        'Balance Payable Amount': ['Balance Payable Amount', 'BalancePayableAmount'],
        'Branch': ['branch_name', 'Branch Name', 'Branch'],
        'State': ['state_name', 'State Name', 'State']
    }
    normalized = pd.DataFrame(index=source.index)
    for target, candidates in aliases.items():
        col = get_col(source, candidates)
        if col:
            normalized[target] = source[col]
    for col in ['Invoice Date', 'Submitted At', 'Last Approved At', 'Hold Time',
                'Rev Action 1', 'Rev Action 2', 'Rev Action 3', 'Rev Action 4', 'Rev Action 5']:
        if col in normalized.columns:
            normalized[col] = pd.to_datetime(normalized[col], dayfirst=True, errors='coerce')
    invoice_date = normalized.get('Invoice Date', pd.Series(pd.NaT, index=normalized.index))
    submitted_date = normalized.get('Submitted At', pd.Series(pd.NaT, index=normalized.index))
    approved_date = normalized.get('Last Approved At', pd.Series(pd.NaT, index=normalized.index))
    normalized['Base Date'] = approved_date.combine_first(submitted_date).combine_first(invoice_date).fillna(pd.Timestamp(get_ist_now().date()))
    for col in ['RO Name', 'Vendor Name', 'Category', 'Status', 'Pending With', 'Bill Uploader', 'Hold Name', 'Finance Name']:
        if col not in normalized.columns:
            normalized[col] = ''
    normalized['RO Name'] = _clean_ro_series(normalized['RO Name'])
    normalized['Status'] = normalized['Status'].fillna('').astype(str).str.strip().str.upper().str.replace(' ', '_', regex=False)
    _v_src = normalized['Vendor Name'].fillna('').astype(str)
    _v_map = {v: normalize_vendor_name(v) for v in _v_src.unique()}
    normalized['Vendor Name'] = _v_src.map(_v_map)
    if 'Amount' in normalized.columns:
        normalized['Amount'] = pd.to_numeric(normalized['Amount'], errors='coerce').fillna(0.0)
    normalized['Category'] = normalized['Category'].fillna('').astype(str).str.strip()
    ro_zone = get_overall_issue_ro_zone_lookup(data)
    normalized['Zone'] = normalized['RO Name'].map(ro_zone).fillna('UNKNOWN ZONE')
    return normalized.reset_index(drop=True)


def prepare_payment_dashboard_frame(raw_frame):
    """Keep all categories, exclude CANCELLED/DECLINED/FAILED, and compute exact buckets, Pending With, and Days Pending."""
    if not isinstance(raw_frame, pd.DataFrame) or raw_frame.empty:
        return pd.DataFrame()
    frame = raw_frame.copy()

    status = frame.get('Status', pd.Series('', index=frame.index)).fillna('').astype(str).str.strip().str.upper().str.replace(' ', '_', regex=False)

    # Exclude CANCELLED, DECLINED, FAILED completely from all calculations
    drop_mask = status.str.contains(r'CANCEL|DECLIN|FAIL', regex=True, na=False)
    frame = frame[~drop_mask].copy()
    if frame.empty:
        return frame

    status = frame.get('Status', pd.Series('', index=frame.index)).fillna('').astype(str).str.strip().str.upper().str.replace(' ', '_', regex=False)
    pending_with_raw = frame.get('Pending With', pd.Series('', index=frame.index)).fillna('').astype(str).str.strip()
    pending_with_up = pending_with_raw.str.upper()
    hold_name = frame.get('Hold Name', pd.Series('', index=frame.index)).fillna('').astype(str).str.strip()
    uploader = frame.get('Bill Uploader', pd.Series('', index=frame.index)).fillna('').astype(str).str.strip()
    fin_name = frame.get('Finance Name', pd.Series('', index=frame.index)).fillna('').astype(str).str.strip()

    is_paid = status.isin(['PAID', 'PROCESSED'])
    is_payment_pending = status.str.contains('PAYMENT', na=False) | pending_with_up.str.contains('PAYMENT', na=False)
    is_finance_hold = status.str.contains('HOLD', na=False) | (hold_name.ne('') & ~is_paid & ~is_payment_pending)
    is_finance_pending = (status.str.contains('FINANCE', na=False) | pending_with_up.str.contains(r'FINANCE|LEVEL\s*3', regex=True, na=False)) & ~is_finance_hold & ~is_paid & ~is_payment_pending
    is_draft = status.str.contains('DRAFT', na=False) & ~is_finance_hold & ~is_finance_pending & ~is_paid & ~is_payment_pending
    is_cost_control = (status.str.contains('PENDING', na=False) | pending_with_up.str.contains(r'COST\s*CONTROL|OPSACCTS|ACC', regex=True, na=False)) & ~is_finance_hold & ~is_finance_pending & ~is_paid & ~is_payment_pending & ~is_draft

    frame['Payment Group'] = np.select(
        [is_paid | is_payment_pending, is_draft, is_cost_control, is_finance_pending, is_finance_hold],
        ['Payment Pending / Paid', 'Draft', 'Cost Control Pending', 'Finance Pending', 'Finance Hold'],
        default='Cost Control Pending'
    )
    frame['Department Bucket'] = frame['Payment Group'].map({
        'Payment Pending / Paid': '1. PAYMENT PENDING / PAID',
        'Draft': '2. DRAFT',
        'Cost Control Pending': '3. COST CONTROL PENDING',
        'Finance Pending': '4. FINANCE PENDING',
        'Finance Hold': '5. FINANCE HOLD'
    })

    # Exact Pending With logic:
    # 1. Draft -> Uploader (Name)
    # 2. Finance Hold -> hold.name (fallback Pending With / Finance Name)
    # 3. Paid -> Paid
    # 4. Others -> Pending With (fallback Finance Name / Uploader)
    fallback_pw = pending_with_raw.where(pending_with_raw.ne(''), fin_name.where(fin_name.ne(''), uploader))
    hold_pw = hold_name.where(hold_name.ne(''), fallback_pw)
    draft_pw = uploader.where(uploader.ne(''), fallback_pw)
    frame['Pending With'] = np.select(
        [is_paid, frame['Payment Group'].eq('Finance Hold'), frame['Payment Group'].eq('Draft')],
        ['Paid', hold_pw, draft_pw],
        default=fallback_pw
    )

    # Exact Days Pending calculation:
    # - Finance Hold: Today - hold.time
    # - Draft: Today - latest approver_*_reverted_action
    # - Paid: 0
    # - Others: Today - Last Approved At (fallback Submitted At -> Invoice Date)
    today_ts = pd.Timestamp(get_ist_now().date())
    inv_dt = pd.to_datetime(frame.get('Invoice Date', pd.Series(pd.NaT, index=frame.index)), dayfirst=True, errors='coerce')
    sub_dt = pd.to_datetime(frame.get('Submitted At', pd.Series(pd.NaT, index=frame.index)), dayfirst=True, errors='coerce')
    app_dt = pd.to_datetime(frame.get('Last Approved At', pd.Series(pd.NaT, index=frame.index)), dayfirst=True, errors='coerce')
    hold_dt = pd.to_datetime(frame.get('Hold Time', pd.Series(pd.NaT, index=frame.index)), dayfirst=True, errors='coerce')

    rev_cols = [c for c in ['Rev Action 1', 'Rev Action 2', 'Rev Action 3', 'Rev Action 4', 'Rev Action 5'] if c in frame.columns]
    if rev_cols:
        rev_df = pd.DataFrame({c: pd.to_datetime(frame[c], dayfirst=True, errors='coerce') for c in rev_cols}, index=frame.index)
        latest_rev_dt = rev_df.max(axis=1)
    else:
        latest_rev_dt = pd.Series(pd.NaT, index=frame.index)

    general_dt = app_dt.combine_first(sub_dt).combine_first(inv_dt)
    eff_pending_dt = general_dt.copy()
    hold_mask = frame['Payment Group'].eq('Finance Hold')
    draft_mask = frame['Payment Group'].eq('Draft')
    eff_pending_dt.loc[hold_mask] = hold_dt.loc[hold_mask].combine_first(general_dt.loc[hold_mask])
    eff_pending_dt.loc[draft_mask] = latest_rev_dt.loc[draft_mask].combine_first(general_dt.loc[draft_mask])

    days_series = (today_ts - eff_pending_dt.dt.normalize()).dt.days
    days_series = days_series.where(~is_paid, 0).fillna(0).clip(lower=0).astype(int)
    frame['Days Pending'] = days_series
    frame['Pending Since'] = eff_pending_dt.dt.strftime('%d-%b-%Y').fillna('')
    frame.loc[is_paid, 'Pending Since'] = 'Paid'

    # Apply Vendor Category Mapping (Admin Permanent + Logged-in User Personal)
    admin_cat_map = load_vendor_category_mapping()
    curr_user_id = st.session_state.get('username', '')
    user_cat_map = load_user_vendor_category_mapping(curr_user_id) if curr_user_id else {}
    cat_to_group = {}
    for grp_name, cat_list in user_cat_map.items():
        for c_item in (cat_list or []):
            cat_to_group[str(c_item).strip().lower()] = f"{grp_name} (My Mapping)"
    for grp_name, cat_list in admin_cat_map.items():
        for c_item in (cat_list or []):
            cat_to_group[str(c_item).strip().lower()] = grp_name
    frame['Vendor Mapping Category'] = (
        frame.get('Category', pd.Series('', index=frame.index))
        .fillna('').astype(str).str.strip().str.lower()
        .map(cat_to_group).fillna('Unmapped')
    )
    return frame.reset_index(drop=True)

@st.cache_data(show_spinner=False, max_entries=1)
def _get_normalized_payment_cached(path, payment_signature, branch_signature, processed_signature):
    """Ultra-fast payment loader: disk pickle -> streaming XML -> openpyxl fallback."""
    pkl_path = os.path.join(DATA_DIR, ".payment_norm_fast_cache.pkl")
    sig = ("pay_norm_v2", payment_signature, branch_signature, processed_signature)
    hit = _load_disk_pkl_cache(pkl_path, sig)
    if isinstance(hit, pd.DataFrame) and not hit.empty:
        return hit
    payment_raw = read_payment_sheet_cached(path, payment_signature, 'Report')
    normalized = normalize_overall_payment_raw(payment_raw, None)
    _save_disk_pkl_cache(pkl_path, sig, normalized)
    return normalized

def get_normalized_overall_payment(path, data=None, processed_signature=None):
    if not path or not os.path.exists(path):
        return pd.DataFrame()
    payment_signature = file_version(path)
    branch_path = FILE_MAP.get('BRANCH_MASTER', '')
    branch_signature = file_version(branch_path) if branch_path and os.path.exists(branch_path) else None
    return _get_normalized_payment_cached(path, payment_signature, branch_signature, processed_signature)

@st.cache_data(show_spinner=False, max_entries=1)
def _read_all_dashboard_sheets_once(path, signature):
    """Read and pre-normalize the master workbook ONCE with disk pickle cache so every switch is <0.1s."""
    pkl_path = os.path.join(DATA_DIR, ".monitoring_sheets_fast_cache.pkl")
    sig = ("mon_sheets_v2", signature)
    hit = _load_disk_pkl_cache(pkl_path, sig)
    if isinstance(hit, dict) and hit:
        return hit
    engine = 'openpyxl'
    try:
        import python_calamine  # noqa: F401
        engine = 'calamine'
    except Exception:
        engine = 'openpyxl'
    with pd.ExcelFile(path, engine=engine) as workbook:
        sheets = {name: workbook.parse(name) for name in workbook.sheet_names}
    if 'Vendor_Perf_Raw' in sheets and not sheets['Vendor_Perf_Raw'].empty:
        if 'VendorName' in sheets['Vendor_Perf_Raw'].columns:
            sheets['Vendor_Perf_Raw'] = normalize_vendor_column_cached(sheets['Vendor_Perf_Raw'], 'VendorName')
        sheets['Vendor_Perf_Summary'] = build_vendor_summary_from_raw(sheets['Vendor_Perf_Raw'])
    elif 'Vendor_Perf_Summary' in sheets and not sheets['Vendor_Perf_Summary'].empty:
        if 'VendorName' in sheets['Vendor_Perf_Summary'].columns:
            sheets['Vendor_Perf_Summary'] = normalize_vendor_column_cached(sheets['Vendor_Perf_Summary'], 'VendorName')
    if 'Legwise_Processed_Data' in sheets and not sheets['Legwise_Processed_Data'].empty:
        if 'VendorName' in sheets['Legwise_Processed_Data'].columns:
            sheets['Legwise_Processed_Data'] = normalize_vendor_column_cached(sheets['Legwise_Processed_Data'], 'VendorName')
        if '_OpsRemarkOutcome' not in sheets['Legwise_Processed_Data'].columns:
            sheets['Legwise_Processed_Data']['_OpsRemarkOutcome'] = ops_remark_outcome_series(sheets['Legwise_Processed_Data'])
    _save_disk_pkl_cache(pkl_path, sig, sheets)
    return sheets

def read_dashboard_sheets_cached(path, signature, sheet_names):
    """Serve requested module sheets instantaneously from the single cached workbook."""
    all_sheets = _read_all_dashboard_sheets_once(path, signature)
    return {name: all_sheets[name] for name in sheet_names if name in all_sheets}

@st.cache_data(show_spinner=False, max_entries=2)
def read_binary_asset_cached(path, signature):
    """Reuse report bytes across Streamlit reruns until the report file changes."""
    with open(path, 'rb') as source_file:
        return source_file.read()

@st.cache_data(show_spinner=False, max_entries=8)
def read_access_vendor_options_cached(path, signature):
    """Read only vendor-name columns for the access editor, not both full raw sheets."""
    vendor_names = set()
    try:
        with pd.ExcelFile(path, engine='openpyxl') as workbook:
            for sheet_name in ('Vendor_Perf_Raw', 'CPK_Raw_Data'):
                if sheet_name not in workbook.sheet_names:
                    continue
                header = workbook.parse(sheet_name, nrows=0)
                if 'VendorName' not in header.columns:
                    continue
                values = workbook.parse(sheet_name, usecols=['VendorName'])['VendorName'].dropna().unique()
                vendor_names.update(
                    clean_name for clean_name in (normalize_vendor_name(value) for value in values)
                    if clean_name
                )
    except Exception as exc:
        logging.warning(f"Could not load access-control vendor options: {exc}")
    return sorted(vendor_names)

def load_dashboard_data(page):
    if page == "🧭 Scheduled Route Master":
        return {'Scheduled_Route_Master': get_scheduled_route_master(get_route_lookup_signature())}
    path = FILE_MAP["FINAL_OUTPUT"]
    if not os.path.exists(path):
        if page in ["📝 Today's Call Action Plan", "🔐 User & Access Control", "⚠️ Overall Issues", "💳 Payment Dashboard", "📱 Communication Hub"]:
            data = {"dummy": pd.DataFrame()}
            if page in ["⚠️ Overall Issues", "💳 Payment Dashboard", "📱 Communication Hub"] and os.path.exists(FILE_MAP.get('PAYMENT', '')):
                try:
                    data['Payment_Raw'] = get_normalized_overall_payment(FILE_MAP['PAYMENT'], data)
                except Exception as exc:
                    logging.warning(f"Could not load raw payment data for Overall Issues: {exc}")
            return data
        return {}
    try:
        processed_signature = file_version(path)
        payment_path = FILE_MAP.get('PAYMENT', '')
        payment_signature = file_version(payment_path) if payment_path and os.path.exists(payment_path) else None
        branch_path = FILE_MAP.get('BRANCH_MASTER', '')
        branch_signature = file_version(branch_path) if branch_path and os.path.exists(branch_path) else None
        page_cache_key = (page, processed_signature, payment_signature, branch_signature)
        page_cache = st.session_state.setdefault('_dashboard_page_cache', {})
        if page_cache_key in page_cache:
            # Page frames are kept for this session, so module navigation avoids another
            # workbook deserialize and normalization pass. Renderers work on local copies.
            return dict(page_cache[page_cache_key])
        if page == "🔐 User & Access Control":
            return {'Vendor_Options': read_access_vendor_options_cached(path, processed_signature)}
        data = read_dashboard_sheets_cached(path, processed_signature, MENU_SHEETS[page])
        if page in ["⚠️ Overall Issues", "💳 Payment Dashboard", "📱 Communication Hub"] and os.path.exists(FILE_MAP.get('PAYMENT', '')):
            try:
                data['Payment_Raw'] = get_normalized_overall_payment(FILE_MAP['PAYMENT'], data, processed_signature)
            except Exception as exc:
                logging.warning(f"Could not load raw payment data for Overall Issues: {exc}")
        if page in ["📝 Today's Call Action Plan", "🔐 User & Access Control", "⚠️ Overall Issues"] and not data:
            data = {"dummy": pd.DataFrame()}
        page_cache[page_cache_key] = data
        while len(page_cache) > 3:
            page_cache.pop(next(iter(page_cache)))
        return data
    except Exception as exc:
        logging.exception("Cannot read dashboard workbook")
        st.error(f"Cannot read the processed Excel file: {exc}")
        if st.session_state['role'] == 'Admin':
            st.exception(exc)
        st.stop()

if st.session_state.pop('_processing_success', False):
    st.success("Data refreshed successfully. Your Executive Report is ready to download!")

# 📥 EXPORT REPORT - ON-DEMAND GENERATION (Zero RAM overhead during processing!)
if st.session_state.get('all_vendors', True) and os.path.exists(FILE_MAP["FINAL_OUTPUT"]):
    st.sidebar.markdown("---")
    st.sidebar.header("📥 Export Reports")
    if st.sidebar.button("⚙️ Prepare VIP Executive Report", key="prep_vip_exec_btn", use_container_width=True):
        with st.spinner("Generating VIP Executive Report..."):
            try:
                all_s = _read_all_dashboard_sheets_once(FILE_MAP["FINAL_OUTPUT"], file_version(FILE_MAP["FINAL_OUTPUT"]))
                generate_vip_executive_report_to_disk(all_s)
                st.session_state['_vip_exec_report_ready'] = True
                gc.collect()
            except Exception as exc:
                st.sidebar.error(f"Could not generate report: {exc}")
    if os.path.exists(FILE_MAP["EXECUTIVE_REPORT"]):
        try:
            report_path = FILE_MAP["EXECUTIVE_REPORT"]
            report_bytes = read_binary_asset_cached(report_path, file_version(report_path))
            st.sidebar.download_button(
                "📄 Download VIP Executive Report",
                data=report_bytes,
                file_name=f"Trackon_Executive_Master_Report_{get_ist_now():%d_%b_%Y}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary"
            )
        except Exception as exc:
            st.sidebar.error(f"Could not load download: {exc}")

    ts = os.path.getmtime(FILE_MAP["FINAL_OUTPUT"])
    ist = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    dt = datetime.datetime.fromtimestamp(ts, tz=ist).strftime('%d %b %Y, %I:%M %p')
    st.sidebar.caption(f"📊 Dashboard Refreshed: {dt} (IST)")

data = load_dashboard_data(choice)
if not data and choice not in ["🔐 User & Access Control", "🧭 Scheduled Route Master", "⚠️ Overall Issues"]:
    if ops_remark_raw_view or ven_perf_raw_view or overall_issue_raw_view:
        try:
            st.query_params.clear()
        except Exception:
            pass
        st.session_state["ops_win_hide_sidebar"] = False
        st.session_state["ven_win_hide_sidebar"] = False
        st.rerun()
    st.warning("No processed data for this page. Admin must upload the relevant files and process data.")
    st.stop()

st.markdown(f"""
<div class="app-topline">
  <div>
    <div class="app-eyebrow">Trackon • Fleet Operations</div>
    <div class="app-brandline">Command Center <span class="app-subline">Network performance at a glance</span></div>
  </div>
  <div class="app-chip">{html_module.escape(selected_theme_name)} &nbsp;·&nbsp; {html_module.escape(choice)}</div>
</div>
""", unsafe_allow_html=True)

try:
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# ==========================================
# 7B. UNIFIED FILTER BAR, DATE PRESETS & CROSS-FILTER ENGINE
# ==========================================
def _clamp_date(val, min_d, max_d):
    if val is None or val < min_d:
        return min_d
    if val > max_d:
        return max_d
    return val

def _set_date_preset(key_prefix, start_val, end_val):
    st.session_state[f"{key_prefix}_sd"] = start_val
    st.session_state[f"{key_prefix}_ed"] = end_val

def _reset_unified_filters(key_prefix, min_d=None, max_d=None):
    if min_d is not None and max_d is not None:
        st.session_state[f"{key_prefix}_sd"] = min_d
        st.session_state[f"{key_prefix}_ed"] = max_d
    for suffix in ("zone", "ro", "vendor", "route", "leg"):
        st.session_state[f"{key_prefix}_{suffix}"] = "ALL"
    st.session_state[f"{key_prefix}_search"] = ""

def render_duration_selector(df_raw, date_col_name, key_prefix):
    """Upgraded date selector with Power BI presets (Last 7D, Last 14D, MTD, All)."""
    if df_raw is None or df_raw.empty or date_col_name not in df_raw.columns:
        return df_raw, False, "All Available Days"

    parsed_dates = pd.to_datetime(df_raw[date_col_name], dayfirst=True, errors='coerce')
    valid_dates = parsed_dates.dropna()
    if valid_dates.empty:
        return df_raw, False, "All Available Days"

    min_d = valid_dates.min().date()
    max_d = valid_dates.max().date()

    sd_key, ed_key = f"{key_prefix}_sd", f"{key_prefix}_ed"
    st.session_state[sd_key] = _clamp_date(st.session_state.get(sd_key, min_d), min_d, max_d)
    st.session_state[ed_key] = _clamp_date(st.session_state.get(ed_key, max_d), min_d, max_d)

    last_7_start = max(min_d, max_d - datetime.timedelta(days=6))
    last_14_start = max(min_d, max_d - datetime.timedelta(days=13))
    mtd_start = max(min_d, max_d.replace(day=1))

    p1, p2, p3, p4, dc1, dc2 = st.columns([0.75, 0.8, 0.7, 0.7, 1.25, 1.25])
    p1.button("Last 7D", key=f"{key_prefix}_p7", use_container_width=True,
              on_click=_set_date_preset, args=(key_prefix, last_7_start, max_d))
    p2.button("Last 14D", key=f"{key_prefix}_p14", use_container_width=True,
              on_click=_set_date_preset, args=(key_prefix, last_14_start, max_d))
    p3.button("MTD", key=f"{key_prefix}_pmtd", use_container_width=True,
              on_click=_set_date_preset, args=(key_prefix, mtd_start, max_d))
    p4.button("All", key=f"{key_prefix}_pall", use_container_width=True,
              on_click=_set_date_preset, args=(key_prefix, min_d, max_d))

    start_d = dc1.date_input("Start Date", min_value=min_d, max_value=max_d, key=sd_key, label_visibility="collapsed")
    end_d = dc2.date_input("End Date", min_value=min_d, max_value=max_d, key=ed_key, label_visibility="collapsed")
    if start_d > end_d:
        start_d, end_d = end_d, start_d

    days_cnt = (end_d - start_d).days + 1
    is_custom = (start_d != min_d) or (end_d != max_d)
    mask = (parsed_dates.dt.date >= start_d) & (parsed_dates.dt.date <= end_d)
    filtered_df = df_raw[mask].copy()
    dur_label = f"{start_d.strftime('%d %b %Y')} to {end_d.strftime('%d %b %Y')} ({days_cnt} Days)"
    return filtered_df, is_custom, dur_label

def render_unified_filter_bar(
    df_raw,
    key_prefix,
    date_col=None,
    zone_col=None,
    ro_col=None,
    vendor_col=None,
    route_col=None,
    leg_col=None,
    search_placeholder="Search Route, Vendor, Invoice..."
):
    """Sticky Power BI-style filter strip with Date Presets, cascading dropdowns & Active Filter Chips."""
    state = {
        "is_date_filtered": False,
        "dur_label": "All Available Days",
        "zone": "ALL",
        "ro": "ALL",
        "vendor": "ALL",
        "route": "ALL",
        "leg": "ALL",
        "search": ""
    }
    if df_raw is None or df_raw.empty:
        return df_raw, state

    for suffix in ("zone", "ro", "vendor", "route", "leg"):
        pending_key = f"_pending_{key_prefix}_{suffix}"
        if pending_key in st.session_state:
            st.session_state[f"{key_prefix}_{suffix}"] = st.session_state.pop(pending_key)

    df_work = df_raw.copy()
    min_d = max_d = None

    with st.container():
        st.markdown('<div class="pbi-sticky-anchor"></div>', unsafe_allow_html=True)

        if date_col and date_col in df_work.columns:
            if pd.api.types.is_datetime64_any_dtype(df_work[date_col]):
                parsed_dates = df_work[date_col]
            else:
                parsed_dates = pd.to_datetime(df_work[date_col], dayfirst=True, errors='coerce')
            valid_dates = parsed_dates.dropna()
            if not valid_dates.empty:
                min_d = valid_dates.min().date()
                max_d = valid_dates.max().date()
                sd_key, ed_key = f"{key_prefix}_sd", f"{key_prefix}_ed"
                st.session_state[sd_key] = _clamp_date(st.session_state.get(sd_key, min_d), min_d, max_d)
                st.session_state[ed_key] = _clamp_date(st.session_state.get(ed_key, max_d), min_d, max_d)

                last_7_start = max(min_d, max_d - datetime.timedelta(days=6))
                last_14_start = max(min_d, max_d - datetime.timedelta(days=13))
                mtd_start = max(min_d, max_d.replace(day=1))

                r1c1, r1c2, r1c3, r1c4, r1c5, r1c6, r1c7 = st.columns([0.65, 0.7, 0.6, 0.6, 1.1, 1.1, 0.85])
                r1c1.button("Last 7D", key=f"{key_prefix}_u7", use_container_width=True,
                            on_click=_set_date_preset, args=(key_prefix, last_7_start, max_d))
                r1c2.button("Last 14D", key=f"{key_prefix}_u14", use_container_width=True,
                            on_click=_set_date_preset, args=(key_prefix, last_14_start, max_d))
                r1c3.button("MTD", key=f"{key_prefix}_umtd", use_container_width=True,
                            on_click=_set_date_preset, args=(key_prefix, mtd_start, max_d))
                r1c4.button("All", key=f"{key_prefix}_uall", use_container_width=True,
                            on_click=_set_date_preset, args=(key_prefix, min_d, max_d))

                start_d = r1c5.date_input("Start Date", min_value=min_d, max_value=max_d, key=sd_key, label_visibility="collapsed")
                end_d = r1c6.date_input("End Date", min_value=min_d, max_value=max_d, key=ed_key, label_visibility="collapsed")
                r1c7.button("↺ Reset", key=f"{key_prefix}_reset", use_container_width=True,
                            on_click=_reset_unified_filters, args=(key_prefix, min_d, max_d))

                if start_d > end_d:
                    start_d, end_d = end_d, start_d
                days_cnt = (end_d - start_d).days + 1
                state["is_date_filtered"] = (start_d != min_d) or (end_d != max_d)
                state["dur_label"] = f"{start_d.strftime('%d %b %Y')} to {end_d.strftime('%d %b %Y')} ({days_cnt} Days)"
                df_work = df_work[(parsed_dates.dt.date >= start_d) & (parsed_dates.dt.date <= end_d)].copy()
        else:
            _, reset_col = st.columns([5.2, 0.8])
            reset_col.button("↺ Reset", key=f"{key_prefix}_reset_nodate", use_container_width=True,
                             on_click=_reset_unified_filters, args=(key_prefix, None, None))

        active_controls = []
        if zone_col and zone_col in df_work.columns:
            active_controls.append(("zone", "Zone", zone_col))
        if ro_col and ro_col in df_work.columns:
            active_controls.append(("ro", "RO", ro_col))
        if vendor_col and vendor_col in df_work.columns:
            active_controls.append(("vendor", "Vendor", vendor_col))
        if route_col and route_col in df_work.columns:
            active_controls.append(("route", "Route", route_col))
        if leg_col and leg_col in df_work.columns:
            active_controls.append(("leg", "Legwise", leg_col))

        col_weights = [1.0] * len(active_controls) + [1.35]
        row2_cols = st.columns(col_weights)

        for idx, (suffix, label, col_name) in enumerate(active_controls):
            raw_vals = [
                v for v in df_work[col_name].dropna().astype(str).str.strip().unique().tolist()
                if v and v.upper() not in ("NAN", "NONE")
            ]
            if suffix == "leg":
                raw_vals = sorted(raw_vals, key=lambda x: (int(re.search(r'(\d+)', x).group(1)) if re.search(r'(\d+)', x) else 999, x))
            else:
                raw_vals = sorted(raw_vals)
            opts = ["ALL"] + raw_vals
            w_key = f"{key_prefix}_{suffix}"
            if st.session_state.get(w_key) not in opts:
                st.session_state[w_key] = "ALL"
            chosen = row2_cols[idx].selectbox(label, opts, key=w_key)
            state[suffix] = chosen
            if chosen != "ALL":
                df_work = df_work[df_work[col_name].fillna('').astype(str).str.strip().eq(chosen)].copy()

        search_key = f"{key_prefix}_search"
        search_val = row2_cols[-1].text_input("🔍 Quick Search", placeholder=search_placeholder, key=search_key)
        state["search"] = search_val.strip()
        if state["search"]:
            q = state["search"]
            mask = df_work.astype(str).apply(lambda c: c.str.contains(q, case=False, regex=False, na=False)).any(axis=1)
            df_work = df_work[mask].copy()

        chips = [f'<span class="pbi-chip">📅 {html_module.escape(state["dur_label"])}</span>']
        for label_name, key_name in [("Zone", "zone"), ("RO", "ro"), ("Vendor", "vendor"), ("Route", "route"), ("Legwise", "leg")]:
            if state[key_name] != "ALL":
                chips.append(f'<span class="pbi-chip">{label_name}: {html_module.escape(str(state[key_name]))}</span>')
        if state["search"]:
            chips.append(f'<span class="pbi-chip">🔍 “{html_module.escape(state["search"])}”</span>')
        if len(chips) == 1 and not state["is_date_filtered"]:
            chips.append('<span class="pbi-chip pbi-chip-muted">All records active · Click any chart bar/point to cross-filter</span>')

        st.markdown(
            f'<div class="pbi-chip-bar"><span class="pbi-chip-title">Active Filters</span>{"".join(chips)}</div>',
            unsafe_allow_html=True
        )

    return df_work, state

def render_crossfilter_plotly(container, fig, key, target_state_key, point_field="x"):
    """Render a Plotly chart; clicking a bar/point updates the unified filter bar on rerun."""
    try:
        event = container.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points", key=key)
        sel = getattr(event, "selection", None)
        points = sel.get("points", []) if isinstance(sel, dict) else (getattr(sel, "points", []) or [])
        if points:
            pt = points[0]
            clicked = pt.get(point_field) or pt.get("hovertext") or pt.get("x") or pt.get("label")
            if clicked is not None:
                clicked_str = str(clicked).strip()
                if clicked_str and st.session_state.get(target_state_key) != clicked_str:
                    st.session_state[f"_pending_{target_state_key}"] = clicked_str
                    st.rerun()
    except TypeError:
        container.plotly_chart(fig, use_container_width=True)

def render_powerbi_insights(title, metrics, insights, period_note=None):
    """Render a consistent, filter-aware insight strip for each dashboard module."""
    st.markdown(f"#### ✨ {title}")
    if period_note:
        st.caption(period_note)
    metric_list = list(metrics or [])
    for metric_start in range(0, len(metric_list), 4):
        metric_specs = metric_list[metric_start:metric_start + 4]
        metric_columns = st.columns(len(metric_specs))
        for metric_column, metric_spec in zip(metric_columns, metric_specs):
            label, value = metric_spec[:2]
            delta = metric_spec[2] if len(metric_spec) > 2 else None
            metric_column.metric(label, value, delta=delta)
    insight_list = [str(item).strip() for item in (insights or []) if str(item).strip()]
    if insight_list:
        st.caption("Key signals")
        for insight in insight_list:
            st.markdown(f"- {insight}")

def render_scheduled_route_master(data):
    st.markdown("## 🧭 Scheduled Route Master")
    st.caption("Each row is mapped to its own leg origin, destination, branch names, and ROs · Download a print-ready Excel poster")
    df_master = data.get('Scheduled_Route_Master', pd.DataFrame()).copy()
    if df_master.empty:
        st.warning("The supplied scheduled route table could not be loaded.")
        return

    lookup_info = df_master.attrs
    st.caption(f"Route legs, departure/arrival times, TAT, and halting are derived from the uploaded RoutePathReportModel. Branch and RO labels: {lookup_info.get('branch_source') or 'branch list not available'}.")
    schedule_source = lookup_info.get('schedule_source', '')
    if schedule_source:
        if 'Bundled fallback schedule' in schedule_source:
            st.warning(f"Schedule source: {schedule_source}. Upload the latest National/Zonal Scheduled Route Master workbook in Data Management to refresh these rows.")
        else:
            st.caption(f"Schedule source: {schedule_source}")
    unmapped_count = int(df_master.get('RO', pd.Series(dtype=str)).astype(str).str.upper().eq('RO NOT MAPPED').sum())
    unmapped_count += int(df_master.get('Destination RO', pd.Series(dtype=str)).astype(str).str.upper().eq('RO NOT MAPPED').sum())
    if unmapped_count:
        st.warning(f"{unmapped_count} leg endpoints have no matching RO in the uploaded branch list. Check the branch codes or the RO & Branch List workbook.")

    branch_columns = ['From Branch', 'To Branch', 'Origin', 'Origin Branch', 'Destination', 'Destination Branch']
    branch_values = sorted({
        str(value).strip() for col in branch_columns if col in df_master.columns
        for value in df_master[col].dropna().tolist() if str(value).strip() and str(value).strip() not in ('-', 'nan', 'None')
    })
    filter_col, search_col = st.columns([1, 2])
    selected_branch = filter_col.selectbox("Branch", ["ALL BRANCHES"] + branch_values, key="schedule_branch_filter")
    search_route = search_col.text_input("Find a route", placeholder="Type a route path or branch code", key="schedule_route_search")

    visible = df_master.copy()
    if selected_branch != "ALL BRANCHES":
        branch_mask = pd.Series(False, index=visible.index)
        for col in branch_columns:
            if col in visible.columns:
                branch_mask |= visible[col].astype(str).str.casefold().eq(selected_branch.casefold())
        visible = visible[branch_mask].copy()
    if search_route.strip():
        q = search_route.strip()
        visible = visible[visible.astype(str).apply(
            lambda col: col.str.contains(q, case=False, regex=False, na=False)
        ).any(axis=1)].copy()

    route_path_col = get_col(visible, ['Route Path', 'Route'])
    origin_branch_col = get_col(visible, ['Origin Branch', 'From Branch', 'Origin'])
    origin_ro_col = get_col(visible, ['RO', 'Origin RO'])
    destination_ro_col = get_col(visible, ['Destination RO'])
    route_count = int(visible[route_path_col].nunique()) if route_path_col else 0
    branch_count = int(visible[origin_branch_col].nunique()) if origin_branch_col else 0
    unmapped_endpoints = 0
    for ro_col in [origin_ro_col, destination_ro_col]:
        if ro_col:
            unmapped_endpoints += int(
                visible[ro_col].fillna('').astype(str).str.strip().str.upper().isin(['RO NOT MAPPED', 'UNMAPPED']).sum()
            )
    schedule_fields = [col for col in ['Scheduled Departure Time', 'Scheduled Arrival Time'] if col in visible.columns]
    complete_schedule_rows = 0
    if schedule_fields:
        schedule_present = pd.DataFrame({
            col: visible[col].fillna('').astype(str).str.strip().str.upper().ne('')
            & ~visible[col].fillna('').astype(str).str.strip().str.upper().isin(['-', 'NAN', 'NONE'])
            for col in schedule_fields
        }, index=visible.index)
        complete_schedule_rows = int(schedule_present.all(axis=1).sum())
    schedule_insights = []
    if route_path_col and not visible.empty:
        route_counts = visible[route_path_col].dropna().astype(str).value_counts()
        if not route_counts.empty:
            top_route = route_counts.index[0].replace('`', '')
            schedule_insights.append(f"Highest leg volume: `{top_route}` has {int(route_counts.iloc[0]):,} visible legs.")
    if unmapped_endpoints:
        schedule_insights.append(f"{unmapped_endpoints:,} visible endpoints have no RO mapping and need a branch-list review.")
    elif not visible.empty:
        schedule_insights.append("All visible route endpoints have an RO mapping.")
    if schedule_fields:
        schedule_insights.append(
            f"{complete_schedule_rows:,} of {len(visible):,} visible legs have all available scheduled time fields filled."
        )
    render_powerbi_insights(
        'Scheduled Network Snapshot',
        [('Visible route legs', f'{len(visible):,}'), ('Route paths', f'{route_count:,}'),
         ('Origin branches', f'{branch_count:,}'), ('Unmapped endpoints', f'{unmapped_endpoints:,}')],
        schedule_insights,
        period_note='Signals follow the selected branch and route search.'
    )

    branch_label = selected_branch if selected_branch != "ALL BRANCHES" else "All Branches"
    safe_branch = re.sub(r'[^A-Za-z0-9_-]+', '_', branch_label).strip('_') or 'all_branches'

    poster_specs = [
        {
            'key': 'departure', 'tab': '🚚 Departure Poster', 'label': 'Scheduled Departure Poster',
            'columns': ['Route Code', 'Route Path', 'Legwise', 'Legs', 'RO', 'Origin Branch', 'Departure Route Day', 'Scheduled Departure Time'],
            'scope_columns': ['Origin', 'Origin Branch', 'From Branch'],
            'caption': 'Departure schedule from each route branch. Route Day is the same offset used by Vendor Performance.',
            'widths': {'Route Code': 12, 'Route Path': 28, 'Legwise': 11, 'Legs': 24, 'Origin RO': 16, 'Origin Branch': 28, 'Departure Route Day': 18, 'Scheduled Departure Time': 24},
            'paper_size': 8, 'landscape': True
        },
        {
            'key': 'arrival', 'tab': '🏁 Arrival Poster', 'label': 'Scheduled Arrival Poster',
            'columns': ['Route Code', 'Route Path', 'Legwise', 'Legs', 'Origin Branch', 'RO', 'Destination Branch', 'Destination RO', 'Arrival Route Day', 'Scheduled Arrival Time', 'Scheduled Driving Hours'],
            'scope_columns': ['Destination', 'Destination Branch', 'To Branch'],
            'caption': 'Arrival schedule at each destination branch, with route day and scheduled leg hours.',
            'widths': {'Route Code': 12, 'Route Path': 26, 'Legwise': 10, 'Legs': 21, 'Origin Branch': 22, 'Origin RO': 15, 'Destination Branch': 25, 'Destination RO': 18, 'Arrival Route Day': 18, 'Scheduled Arrival Time': 22, 'Scheduled Leg Hours': 20},
            'paper_size': 8, 'landscape': True
        },
        {
            'key': 'halting', 'tab': '⏱️ Halting Poster', 'label': 'Scheduled Halting Poster',
            'columns': ['Route Code', 'Route Path', 'Legwise', 'Legs', 'Origin Branch', 'RO', 'Departure Route Day', 'Scheduled Departure Time', 'Arrival Route Day', 'Scheduled Arrival Time', 'Scheduled Halting', 'Scheduled TAT Till Destination'],
            'scope_columns': ['Origin', 'Origin Branch', 'From Branch', 'Scheduled Halting'],
            'caption': 'Halting is the scheduled departure minus scheduled arrival at the origin branch; route TAT follows the existing processing calculation.',
            'widths': {'Route Code': 12, 'Route Path': 25, 'Legwise': 10, 'Legs': 20, 'Origin Branch': 21, 'Origin RO': 15, 'Departure Route Day': 18, 'Scheduled Departure Time': 22, 'Arrival Route Day': 18, 'Scheduled Arrival Time': 22, 'Scheduled Halting': 20, 'Scheduled TAT Till Destination': 24},
            'paper_size': 8, 'landscape': True
        }
    ]
    poster_tabs = st.tabs([spec['tab'] for spec in poster_specs])
    selected_key = _lookup_key(selected_branch)
    for poster_tab, spec in zip(poster_tabs, poster_specs):
        with poster_tab:
            poster_source = visible.copy()
            if selected_branch != 'ALL BRANCHES':
                branch_mask = pd.Series(False, index=poster_source.index)
                for col in spec['scope_columns']:
                    if col in poster_source.columns:
                        branch_mask |= poster_source[col].fillna('').astype(str).apply(_lookup_key).eq(selected_key)
                poster_source = poster_source[branch_mask].copy()

            poster = poster_source.reindex(columns=spec['columns']).fillna('')
            poster = poster.rename(columns={'RO': 'Origin RO', 'Scheduled Driving Hours': 'Scheduled Leg Hours'})
            st.caption(spec['caption'])
            if poster.empty:
                st.info(f"No {spec['label'].lower()} rows for {branch_label} with these filters.")
                continue
            render_centered_html_table(poster, height=400)
            poster_bytes = build_formatted_excel_bytes(
                poster, spec['label'], f"{spec['label']} · {branch_label}",
                width_overrides=spec['widths'], paper_size=spec['paper_size'], landscape=spec['landscape']
            )
            file_stem = f"Scheduled_{spec['key'].title()}_Poster_{safe_branch}"
            st.download_button(
                f"📥 Download {spec['label']} (Excel)",
                data=poster_bytes,
                file_name=f"{file_stem}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary",
                key=f"schedule_poster_{spec['key']}_{safe_branch}"
            )

    master_columns = [
        'Route Code', 'RO', 'Origin', 'Origin Branch', 'Destination', 'Destination Branch', 'Destination RO',
        'Route Path', 'Legwise', 'Legs', 'Departure Route Day', 'Scheduled Departure Time',
        'Arrival Route Day', 'Scheduled Arrival Time',
        'Scheduled Driving Hours', 'Scheduled Halting', 'Scheduled TAT Till Destination'
    ]
    with st.expander("Full leg-wise route master preview", expanded=False):
        render_centered_html_table(visible.reindex(columns=master_columns).fillna(''), height=460)

def get_overall_issue_frames(data):
    ops_raw = data.get('Legwise_Processed_Data', pd.DataFrame())
    pay_raw = data.get('Payment_Raw', data.get('Master_Database', pd.DataFrame()))
    if not st.session_state.get('all_vendors', True):
        ops_vendor_col = get_col(ops_raw, ['VendorName', 'Vendor Name'])
        pay_vendor_col = get_col(pay_raw, ['Vendor Name', 'VendorName'])
        ops_raw = filter_df_by_user_vendors(ops_raw, ops_vendor_col) if ops_vendor_col else ops_raw.iloc[0:0].copy()
        pay_raw = filter_df_by_user_vendors(pay_raw, pay_vendor_col) if pay_vendor_col else pay_raw.iloc[0:0].copy()
    return ops_raw, pay_raw

def get_overall_cpk_frame(data):
    cpk_raw = data.get('CPK_Raw_Data', pd.DataFrame())
    if not st.session_state.get('all_vendors', True):
        vendor_col = get_col(cpk_raw, ['VendorName', 'Vendor Name'])
        cpk_raw = filter_df_by_user_vendors(cpk_raw, vendor_col) if vendor_col else cpk_raw.iloc[0:0].copy()
    return cpk_raw

def get_overall_issue_date_bounds(ops_raw, pay_raw, cpk_raw=None):
    available = []
    frames = [(ops_raw, ['MCD_StartDate', 'Date']), (pay_raw, ['Base Date', 'Invoice Date'])]
    if isinstance(cpk_raw, pd.DataFrame):
        frames.append((cpk_raw, ['Date']))
    for frame, candidates in frames:
        date_col = get_col(frame, candidates)
        if date_col and not frame.empty:
            parsed = pd.to_datetime(frame[date_col], dayfirst=True, errors='coerce').dropna()
            if not parsed.empty:
                available.extend([parsed.min().date(), parsed.max().date()])
    if available:
        return min(available), max(available)
    today = get_ist_now().date()
    return today - datetime.timedelta(days=13), today

def filter_overall_issue_frames(ops_raw, pay_raw, start_date, end_date, selected_zone='ALL ZONES'):
    def apply_filters(frame, date_candidates):
        result = frame.copy()
        if result.empty:
            return result
        date_col = get_col(result, date_candidates)
        if date_col:
            parsed = pd.to_datetime(result[date_col], dayfirst=True, errors='coerce')
            mask = parsed.dt.date.between(start_date, end_date)
            result = result[mask].copy()
        if selected_zone != 'ALL ZONES':
            zone_col = get_col(result, ['Zone'])
            if zone_col:
                result = result[result[zone_col].fillna('UNKNOWN ZONE').astype(str).str.strip().str.upper().eq(selected_zone.upper())].copy()
            else:
                result = result.iloc[0:0].copy()
        return result
    return apply_filters(ops_raw, ['MCD_StartDate', 'Date']), apply_filters(pay_raw, ['Base Date', 'Invoice Date'])

def filter_overall_utilization_frame(cpk_raw, start_date, end_date, selected_zone='ALL ZONES'):
    result = cpk_raw.copy() if isinstance(cpk_raw, pd.DataFrame) else pd.DataFrame()
    if result.empty:
        return result
    date_col = get_col(result, ['Date'])
    if date_col:
        parsed = pd.to_datetime(result[date_col], dayfirst=True, errors='coerce')
        result = result[parsed.dt.date.between(start_date, end_date)].copy()
    if selected_zone != 'ALL ZONES':
        zone_col = get_col(result, ['Zone'])
        result = result[result[zone_col].fillna('UNKNOWN ZONE').astype(str).str.strip().str.upper().eq(selected_zone.upper())].copy() if zone_col else result.iloc[0:0].copy()
    return result

def get_overall_issue_query_url():
    try:
        return str(st.context.url)
    except Exception:
        return ''

def get_overall_payment_status_masks(frame):
    status_col = get_col(frame, ['Status', 'Invoice Status'])
    status = (frame[status_col].fillna('').astype(str).str.strip().str.upper()
              .str.replace(r'[\s/-]+', '_', regex=True).str.strip('_')) if status_col else pd.Series('', index=frame.index)
    pending_with_col = get_col(frame, ['Pending With', 'PendingWith'])
    pending_with = frame[pending_with_col].fillna('').astype(str).str.strip().str.upper() if pending_with_col else pd.Series('', index=frame.index)

    def has_value(column_names):
        column = get_col(frame, column_names)
        if not column:
            return pd.Series(False, index=frame.index)
        value = frame[column].fillna('').astype(str).str.strip().str.upper()
        return value.ne('') & ~value.isin(['NAN', 'NONE', 'NULL', '0'])

    finance_hold = (
        status.str.contains(r'(?:^|_)HOLD(?:$|_)', regex=True, na=False)
        | has_value(['Hold Name', 'HoldName'])
        | has_value(['Hold Key', 'HoldKey'])
    )
    finance_pending = (
        status.str.contains(r'(?:^|_)FINANCE(?:$|_)', regex=True, na=False)
        | pending_with.str.contains(r'FINANCE|LEVEL\s*3', regex=True, na=False)
    ) & ~finance_hold
    payment_pending_paid = (
        status.str.contains(r'(?:^|_)(?:PAID|PROCESSED|PAYMENT)(?:_|$)', regex=True, na=False)
        | pending_with.str.contains('PAYMENT', regex=False, na=False)
    ) & ~finance_hold & ~finance_pending
    draft = status.str.contains(r'(?:^|_)DRAFT(?:$|_)', regex=True, na=False) & ~finance_hold & ~finance_pending & ~payment_pending_paid
    pending = status.str.contains(r'(?:^|_)PENDING(?:$|_)', regex=True, na=False) & ~finance_hold & ~finance_pending & ~payment_pending_paid & ~draft
    other = status.ne('') & ~(draft | pending | payment_pending_paid | finance_pending | finance_hold)
    return {
        'Draft bills': draft,
        'Pending bills': pending,
        'Payment pending / paid': payment_pending_paid,
        'Finance pending': finance_pending,
        'Finance hold': finance_hold,
        'Other bills': other
    }

# --------------------- Overall Issues: in-session drill-down and export ---------------------
def _overall_count_from_cell(value):
    if isinstance(value, str):
        match = re.search(r'\(([-\d,]+)\)', value)
        if match:
            try:
                return int(match.group(1).replace(',', ''))
            except ValueError:
                pass
    return int(value) if isinstance(value, (int, np.integer)) else 0

def build_overall_issue_export_frames(ops_raw, pay_raw, cpk_raw, ro='ALL ROS'):
    """Return focused, purpose-built detail tables for the issue workbook."""
    operations = ops_raw.copy() if isinstance(ops_raw, pd.DataFrame) else pd.DataFrame()
    payments = pay_raw.copy() if isinstance(pay_raw, pd.DataFrame) else pd.DataFrame()
    cpk = cpk_raw.copy() if isinstance(cpk_raw, pd.DataFrame) else pd.DataFrame()

    ops_ro_col = get_col(operations, ['Origin RO', 'RO Name', 'RO'])
    if ro != 'ALL ROS' and ops_ro_col:
        operations = operations[_clean_ro_series(operations[ops_ro_col]).eq(ro)].copy()
    remark_col = get_col(operations, ['Remark'])
    dep_col, arr_col = get_col(operations, ['Dep_Status']), get_col(operations, ['Arr_Status'])
    remark = operations[remark_col].fillna('').astype(str) if remark_col else pd.Series('', index=operations.index)
    dep = operations[dep_col].fillna('').astype(str) if dep_col else remark
    arr = operations[arr_col].fillna('').astype(str) if arr_col else remark
    source = remark.where(remark.str.strip().ne(''), dep + ', ' + arr)
    outcomes = ['Ontime Dep, Ontime Arr', 'Ontime Dep, Late Arr', 'Late Dep, Late Arr', 'Late Dep, Ontime Arr']
    operations['Operations Outcome'] = ''
    for outcome in outcomes:
        mask = source.str.contains(outcome, case=False, na=False)
        operations.loc[mask, 'Operations Outcome'] = outcome
    operations = operations[operations['Operations Outcome'].ne('')].copy()
    operations_columns = [
        'MCD_StartDate', 'Remark', 'Operations Outcome', 'Zone', 'Origin RO', 'Route Path', 'Legwise', 'Legs',
        'CD_FromBranch', 'CD_ToBranch', 'MasterCDNo',
        'Scheduled Departure Time', 'Actual Departure Time',
        'Scheduled Arrival Time', 'Actual Arrival Time'
    ]
    operations = operations.reindex(columns=[c for c in operations_columns if c in operations.columns]).fillna('')

    pay_ro_col = get_col(payments, ['RO Name', 'Origin RO', 'RO'])
    if ro != 'ALL ROS' and pay_ro_col:
        payments = payments[_clean_ro_series(payments[pay_ro_col]).eq(ro)].copy()
    status_masks = get_overall_payment_status_masks(payments)
    payments['Payment Group'] = ''
    for label, mask_name in [
        ('Draft', 'Draft bills'), ('Pending', 'Pending bills'),
        ('Payment Pending / Paid', 'Payment pending / paid'),
        ('Finance Pending', 'Finance pending'), ('Finance Hold', 'Finance hold')
    ]:
        payments.loc[status_masks[mask_name], 'Payment Group'] = label
    payments.loc[status_masks['Other bills'], 'Payment Group'] = 'Other'
    payment_columns = [
        'Base Date', 'Invoice Id', 'Invoice Date', 'RO Name', 'Zone', 'Vendor Name',
        'Category', 'Amount', 'Status', 'Payment Group', 'Pending With', 'Last Approved At',
        'Partial Payment', 'Balance Payable Amount', 'Hold Name', 'Hold Key', 'Finance Revert Remarks 1',
        'Approver Revert Remarks'
    ]
    payments = payments.reindex(columns=[c for c in payment_columns if c in payments.columns]).fillna('')

    utilization = pd.DataFrame()
    if not cpk.empty:
        try:
            route_master = build_cpk_tables_from_raw(cpk).get('CPK_National_Zonal_UpDown', pd.DataFrame()).copy()
            route_ro_col = get_col(route_master, ['VendorRO', 'RO_Clean', 'RO'])
            if route_ro_col and ro != 'ALL ROS':
                route_master = route_master[_clean_ro_series(route_master[route_ro_col]).eq(ro)].copy()
            route_type_col = get_col(route_master, ['Type', 'Final_Type'])
            util_col = get_col(route_master, ['Overall Util %', 'Utilization'])
            if route_type_col and util_col:
                route_master = route_master[route_master[route_type_col].astype(str).str.upper().isin(['NATIONAL LH', 'ZONAL LH'])].copy()
                route_name_col = get_col(route_master, ['Route (UP/DOWN)', 'Final_Route', 'Route'])
                route_zone_col = get_col(route_master, ['Zone'])
                route_keys = [c for c in [route_ro_col, route_zone_col, route_type_col, route_name_col] if c]
                if route_keys:
                    route_master = route_master.drop_duplicates(route_keys)
                rates = pd.to_numeric(route_master[util_col], errors='coerce')
                if rates.dropna().gt(1).any():
                    rates = rates / 100
                route_master['Utilization Class'] = np.where(rates < 0.60, 'Underutilized (<60%)', 'Efficiently utilized (60%+)')
                route_master['Route Utilization'] = (rates * 100).round(1).astype('string') + '%'
            utilization_columns = [
                'Zone', route_ro_col, 'Route (UP/DOWN)', route_type_col,
                'Vehicle Count', 'Total Trips', 'Overall Util %', 'Route Utilization', 'Utilization Class'
            ]
            utilization = route_master.reindex(columns=[c for c in utilization_columns if c and c in route_master.columns]).fillna('')
            utilization = utilization.rename(columns={route_ro_col: 'RO', route_type_col: 'Route Type'})
        except Exception as exc:
            logging.warning(f"Overall Issues utilization detail warning: {exc}")

    return payments, operations, utilization

def build_overall_issues_excel_bytes(summary, payment, operations, utilization, report_title):
    """Build one polished workbook with summary and three focused data sheets."""
    buffer = io.BytesIO()
    sheets = [
        ('Summary', summary, {c: 0.50 for c in summary.columns if c not in ['RO Name', 'Zone', 'Total Trips', 'Total Bills']}),
        ('Payment', payment, {}),
        ('Operations Performance', operations, {}),
        ('Utilization', utilization, {'Route Utilization': 0.60, 'Overall Util %': 0.60})
    ]
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        workbook = writer.book
        title_fmt = workbook.add_format({'bold': True, 'font_size': 16, 'font_color': '#FFFFFF', 'bg_color': '#102B46', 'valign': 'vcenter'})
        sub_fmt = workbook.add_format({'font_color': '#42566B', 'italic': True, 'bg_color': '#EAF2F8', 'valign': 'vcenter'})
        head_fmt = workbook.add_format({'bold': True, 'font_color': '#FFFFFF', 'bg_color': '#155E75', 'border': 1, 'border_color': '#0E7490', 'align': 'center', 'valign': 'vcenter', 'text_wrap': True})
        base_even = workbook.add_format({'bg_color': '#F2F7FB', 'font_color': '#14283B', 'bottom': 1, 'bottom_color': '#D9E3EC', 'valign': 'vcenter', 'text_wrap': True})
        base_odd = workbook.add_format({'bg_color': '#FFFFFF', 'font_color': '#14283B', 'bottom': 1, 'bottom_color': '#D9E3EC', 'valign': 'vcenter', 'text_wrap': True})
        low_even = workbook.add_format({'bg_color': '#DDF3E8', 'font_color': '#14532D', 'bold': True, 'bottom': 1, 'bottom_color': '#B8DDC8', 'align': 'center'})
        low_odd = workbook.add_format({'bg_color': '#EAF8F0', 'font_color': '#14532D', 'bold': True, 'bottom': 1, 'bottom_color': '#B8DDC8', 'align': 'center'})
        high_even = workbook.add_format({'bg_color': '#FCE1E1', 'font_color': '#8A1C1C', 'bold': True, 'bottom': 1, 'bottom_color': '#E9BABA', 'align': 'center'})
        high_odd = workbook.add_format({'bg_color': '#FFF0E0', 'font_color': '#8A3B0A', 'bold': True, 'bottom': 1, 'bottom_color': '#E9CBAA', 'align': 'center'})
        row_green_fmt = workbook.add_format({'bg_color': '#E2F0D9', 'font_color': '#1F4E2B', 'bottom': 1, 'bottom_color': '#B8DDC8', 'valign': 'vcenter', 'text_wrap': True})
        row_red_fmt = workbook.add_format({'bg_color': '#FCE4D6', 'font_color': '#7F1D1D', 'bottom': 1, 'bottom_color': '#E9BABA', 'valign': 'vcenter', 'text_wrap': True})
        row_soft_red_fmt = workbook.add_format({'bg_color': '#FFF1F2', 'font_color': '#9F1239', 'bottom': 1, 'bottom_color': '#FECDD3', 'valign': 'vcenter', 'text_wrap': True})
        row_yellow_fmt = workbook.add_format({'bg_color': '#FFF2CC', 'font_color': '#7F6000', 'bottom': 1, 'bottom_color': '#E9CBAA', 'valign': 'vcenter', 'text_wrap': True})
        row_purple_fmt = workbook.add_format({'bg_color': '#E4DFEC', 'font_color': '#4C2A69', 'bottom': 1, 'bottom_color': '#D5C8E5', 'valign': 'vcenter', 'text_wrap': True})
        for sheet_name, source_df, thresholds in sheets:
            frame = source_df.copy() if isinstance(source_df, pd.DataFrame) else pd.DataFrame()
            if frame.empty:
                frame = pd.DataFrame({'Status': ['No records for the selected RO, zone, and duration.']})
            frame = frame.reset_index(drop=True)
            ncols = max(len(frame.columns), 1)
            frame.to_excel(writer, sheet_name=sheet_name, startrow=2, index=False)
            ws = writer.sheets[sheet_name]
            ws.merge_range(0, 0, 0, ncols - 1, report_title, title_fmt)
            ws.merge_range(1, 0, 1, ncols - 1, f"{sheet_name} · Generated {get_ist_now():%d %b %Y, %I:%M %p} IST", sub_fmt)
            ws.set_row(0, 30); ws.set_row(1, 21); ws.set_row(2, 34)
            for ci, col in enumerate(frame.columns):
                ws.write(2, ci, str(col), head_fmt)
                vals = frame[col].fillna('').astype(str).tolist()
                width = min(max(max([len(str(col))] + [min(len(v), 55) for v in vals]) + 2, 12), 38)
                ws.set_column(ci, ci, width)
            for ri, (_, row) in enumerate(frame.iterrows(), start=3):
                even = (ri - 3) % 2 == 0
                row_label_text = ' '.join(str(row.get(col, '')).strip().lower() for col in ['Payment Group', 'Operations Outcome', 'Utilization Class'] if col in row.index)
                if 'payment pending / paid' in row_label_text or 'efficiently' in row_label_text or 'ontime dep, ontime arr' in row_label_text:
                    row_fmt = row_green_fmt
                elif 'finance hold' in row_label_text or 'draft' in row_label_text or 'underutilized' in row_label_text or 'late dep, late arr' in row_label_text:
                    row_fmt = row_red_fmt
                elif 'ontime dep, late arr' in row_label_text:
                    row_fmt = row_soft_red_fmt
                elif 'finance pending' in row_label_text or 'other' in row_label_text or 'pending' in row_label_text or 'late dep, ontime arr' in row_label_text:
                    row_fmt = row_yellow_fmt
                else:
                    row_fmt = base_even if even else base_odd
                for ci, col in enumerate(frame.columns):
                    value = row[col]
                    if isinstance(value, np.generic):
                        value = value.item()
                    if value is None or (not isinstance(value, (list, dict)) and pd.isna(value)):
                        value = ''
                    fmt = row_fmt
                    col_lower = str(col).strip().lower()
                    if col_lower == 'payment pending / paid':
                        fmt = row_green_fmt
                    elif col_lower in ['other', 'other bills']:
                        fmt = row_yellow_fmt
                    elif col_lower in ['draft', 'draft bills', 'finance hold', 'underutilized routes']:
                        fmt = row_red_fmt
                    elif col_lower in ['finance pending', 'pending']:
                        fmt = row_yellow_fmt
                    elif col_lower == 'ontime dep, ontime arr':
                        fmt = row_green_fmt
                    elif col_lower == 'ontime dep, late arr':
                        fmt = row_soft_red_fmt
                    elif col_lower == 'late dep, late arr':
                        fmt = row_red_fmt
                    elif col_lower == 'late dep, ontime arr':
                        fmt = row_yellow_fmt
                    elif col_lower == 'efficiently utilized routes':
                        fmt = row_green_fmt
                    threshold = thresholds.get(col)
                    if threshold is not None:
                        pct = None if col == 'Overall Util %' and isinstance(value, (int, float)) else parse_pct_from_str(value)
                        if pct is None and isinstance(value, (int, float)):
                            pct = float(value) * 100 if float(value) <= 1 else float(value)
                        if pct is not None:
                            is_low = pct < threshold * 100
                            if col in ('Route Utilization', 'Overall Util %'):
                                is_low = not is_low
                            fmt = (low_even if even else low_odd) if is_low else (high_even if even else high_odd)
                    if col_lower == 'payment pending / paid':
                        fmt = row_green_fmt
                    elif col_lower in ['draft', 'draft bills', 'finance hold', 'underutilized routes']:
                        fmt = row_red_fmt
                    elif col_lower in ['finance pending', 'pending', 'other', 'other bills']:
                        fmt = row_yellow_fmt
                    elif col_lower in ['ontime dep, ontime arr', 'efficiently utilized routes']:
                        fmt = row_green_fmt
                    elif col_lower == 'ontime dep, late arr':
                        fmt = row_soft_red_fmt
                    elif col_lower == 'late dep, late arr':
                        fmt = row_red_fmt
                    elif col_lower == 'late dep, ontime arr':
                        fmt = row_yellow_fmt
                    ws.write(ri, ci, value, fmt)
                ws.set_row(ri, 23)
            ws.autofilter(2, 0, len(frame) + 2, max(len(frame.columns) - 1, 0))
            ws.freeze_panes(3, 0)
            ws.set_landscape(); ws.fit_to_pages(1, 0); ws.repeat_rows(2)
            ws.set_margins(0.25, 0.25, 0.4, 0.4)
            ws.set_header('&LTrackon Command Center&R&P')
            ws.set_footer('&LConfidential report&RPage &P of &N')
    return buffer.getvalue()

def _overall_issue_pivot_selection(frame, group_columns, count_label, key, default_frame=None):
    """Show a compact pivot; selecting a row narrows the raw records below it."""
    if frame.empty or not all(column in frame.columns for column in group_columns):
        st.info('No records for this section in the selected window.')
        return default_frame.copy() if isinstance(default_frame, pd.DataFrame) else frame
    pivot = frame.groupby(group_columns, dropna=False).size().reset_index(name=count_label)
    pivot = pivot.sort_values(count_label, ascending=False).reset_index(drop=True)
    try:
        event = st.dataframe(
            style_ui_dataframe(pivot), use_container_width=True, hide_index=True, height=210,
            on_select='rerun', selection_mode='single-row', key=key
        )
        selection = getattr(event, 'selection', {})
        rows = getattr(selection, 'rows', None) if not isinstance(selection, dict) else selection.get('rows')
        if rows:
            selected_index = rows[-1]
            if isinstance(selected_index, int) and 0 <= selected_index < len(pivot):
                selected = pivot.iloc[selected_index]
                narrowed = frame
                for column in group_columns:
                    value = selected[column]
                    narrowed = narrowed[narrowed[column].fillna('').astype(str).eq(str(value))]
                st.caption(f"Pivot selection: {int(selected[count_label]):,} matching records")
                return narrowed.copy()
    except TypeError:
        st.dataframe(style_ui_dataframe(pivot), use_container_width=True, hide_index=True, height=210)
    return default_frame.copy() if isinstance(default_frame, pd.DataFrame) else frame

def render_overall_issue_raw_page(data, query):
    """Show focused issue details with summaries, filters and one formatted workbook."""
    st.markdown('## Issue detail records')
    st.caption('Only the selected issue category is shown. Select a summary row to narrow its records, or download the selected issue.')
    ops_all, pay_all = get_overall_issue_frames(data)
    cpk_all = get_overall_cpk_frame(data)
    default_start, default_end = get_overall_issue_date_bounds(ops_all, pay_all, cpk_all)
    try:
        start_date = datetime.date.fromisoformat(query.get('issues_start', ''))
        end_date = datetime.date.fromisoformat(query.get('issues_end', ''))
    except Exception:
        start_date, end_date = default_start, default_end
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    zone = query.get('issues_zone', 'ALL ZONES') or 'ALL ZONES'
    issue_type = query.get('issues_type', 'Ontime Dep, Ontime Arr') or 'Ontime Dep, Ontime Arr'
    valid_types = [
        'Ontime Dep, Ontime Arr', 'Ontime Dep, Late Arr', 'Late Dep, Late Arr', 'Late Dep, Ontime Arr',
        'Draft bills', 'Pending bills', 'Payment pending / paid', 'Finance pending', 'Finance hold', 'Other bills',
        'Underutilized routes', 'Efficiently utilized routes'
    ]
    if issue_type not in valid_types:
        issue_type = 'Ontime Dep, Ontime Arr'
    ops_base, pay_base = filter_overall_issue_frames(ops_all, pay_all, start_date, end_date, zone)
    cpk_base = filter_overall_utilization_frame(cpk_all, start_date, end_date, zone)
    all_ro = {'ALL ROS'}
    for frame, candidates in [
        (ops_base, ['Origin RO', 'RO Name', 'RO']),
        (pay_base, ['RO Name', 'Origin RO', 'RO']),
        (cpk_base, ['RO_Clean', 'VendorRO', 'RO'])
    ]:
        col = get_col(frame, candidates)
        if col:
            all_ro.update(_clean_ro_series(frame[col]).tolist())
    ro_options = ['ALL ROS'] + sorted(x for x in all_ro if x != 'ALL ROS')
    requested_ro = query.get('issues_ro', 'ALL ROS') or 'ALL ROS'
    if requested_ro not in ro_options:
        requested_ro = 'ALL ROS'
    route_options = {'ALL ROUTES'}
    for frame, candidates in [
        (ops_base, ['Route Path', 'Route']),
        (cpk_base, ['Final_Route', 'Route (UP/DOWN)', 'Route'])
    ]:
        col = get_col(frame, candidates)
        if col:
            route_options.update(frame[col].dropna().astype(str).str.strip().tolist())
    route_options = ['ALL ROUTES'] + sorted(x for x in route_options if x and x != 'ALL ROUTES')
    requested_route = query.get('issues_route', 'ALL ROUTES') or 'ALL ROUTES'
    if requested_route not in route_options:
        requested_route = 'ALL ROUTES'
    filter_ro_col, filter_route_col = st.columns(2)
    selected_ro = filter_ro_col.selectbox('Filter by RO', ro_options, index=ro_options.index(requested_ro), key='overall_issues_raw_ro')
    selected_route = filter_route_col.selectbox('Filter by route', route_options, index=route_options.index(requested_route), key='overall_issues_raw_route')

    def ro_filter(frame, candidates):
        col = get_col(frame, candidates)
        if selected_ro == 'ALL ROS':
            return frame.copy()
        return frame[_clean_ro_series(frame[col]).eq(selected_ro)].copy() if col else frame.iloc[0:0].copy()

    operations, payments, cpk = (
        ro_filter(ops_base, ['Origin RO', 'RO Name', 'RO']),
        ro_filter(pay_base, ['RO Name', 'Origin RO', 'RO']),
        ro_filter(cpk_base, ['RO_Clean', 'VendorRO', 'RO'])
    )
    route_applies_to_payment = issue_type.lower() in [
        'draft bills', 'pending bills', 'payment pending / paid', 'finance pending', 'finance hold', 'other bills'
    ]
    if selected_route != 'ALL ROUTES':
        ops_route_col = get_col(operations, ['Route Path', 'Route'])
        cpk_route_col = get_col(cpk, ['Final_Route', 'Route (UP/DOWN)', 'Route'])
        if ops_route_col:
            operations = operations[operations[ops_route_col].fillna('').astype(str).str.strip().eq(selected_route)].copy()
        if cpk_route_col:
            cpk = cpk[cpk[cpk_route_col].fillna('').astype(str).str.strip().eq(selected_route)].copy()
    if route_applies_to_payment and selected_route != 'ALL ROUTES':
        st.info('Payment records do not contain a route field, so the route filter is ignored for this payment issue.')

    summary = build_overall_issues_summary(operations, payments, cpk)
    payments, operations, utilization = build_overall_issue_export_frames(operations, payments, cpk, 'ALL ROS')
    operations_issues = [
        'Ontime Dep, Ontime Arr', 'Ontime Dep, Late Arr', 'Late Dep, Late Arr', 'Late Dep, Ontime Arr'
    ]
    payment_groups = {
        'Draft bills': 'Draft', 'Pending bills': 'Pending',
        'Payment pending / paid': 'Payment Pending / Paid',
        'Finance pending': 'Finance Pending', 'Finance hold': 'Finance Hold', 'Other bills': 'Other'
    }
    if issue_type in operations_issues:
        focused = operations[operations.get('Operations Outcome', pd.Series('', index=operations.index)).eq(issue_type)].copy()
        denominator = len(operations)
    elif issue_type in payment_groups:
        focused = payments[payments.get('Payment Group', pd.Series('', index=payments.index)).eq(payment_groups[issue_type])].copy()
        denominator = len(payments)
    else:
        class_col = get_col(utilization, ['Utilization Class'])
        is_under = issue_type == 'Underutilized routes'
        wanted = 'Underutilized' if is_under else 'Efficiently'
        focused = utilization[utilization[class_col].astype(str).str.contains(wanted, case=False, na=False)].copy() if class_col else utilization.iloc[0:0].copy()
        denominator = len(utilization)
    issue_count = len(focused)
    issue_pct = issue_count / denominator * 100 if denominator else 0
    safe_issue_key = re.sub(r'[^A-Za-z0-9]+', '_', issue_type).strip('_')
    pivot_suffix = f"_{safe_issue_key}_{start_date:%Y%m%d}_{end_date:%Y%m%d}_{selected_ro}_{selected_route}"
    st.caption(f"{issue_type} · {selected_ro} · {zone} · {start_date:%d %b %Y} to {end_date:%d %b %Y} · {selected_route}")
    m1, m2, m3 = st.columns(3)
    m1.metric('Selected issue rate', f'{issue_pct:.1f}%')
    m2.metric('Matching records', f'{issue_count:,}')
    m3.metric('Selected denominator', f'{denominator:,}')

    if issue_type in operations_issues:
        st.markdown('### Operations Performance')
        view = _overall_issue_pivot_selection(
            focused, ['Origin RO', 'Route Path', 'Operations Outcome'], 'Trips',
            f'overall_issues_ops_pivot{pivot_suffix}', focused
        )
        compact_view = compact_detail_frame(view, 'ops_raw')
        if compact_view.empty:
            st.info('No matching operations records for this issue.')
        else:
            render_centered_html_table(compact_view, height=420)
    elif issue_type in payment_groups:
        st.markdown('### Payment')
        view = _overall_issue_pivot_selection(
            focused, ['RO Name', 'Payment Group'], 'Bills',
            f'overall_issues_payment_pivot{pivot_suffix}', focused
        )
        compact_view = compact_detail_frame(view, 'pay_raw')
        if compact_view.empty:
            st.info('No matching payment records for this issue.')
        else:
            render_centered_html_table(compact_view, height=420)
    else:
        st.markdown('### Utilization')
        util_ro_col = get_col(focused, ['RO'])
        util_route_col = get_col(focused, ['Route'])
        util_type_col = get_col(focused, ['Route Type'])
        util_class_col = get_col(focused, ['Utilization Class'])
        util_group_cols = [c for c in [util_ro_col, util_route_col, util_type_col, util_class_col] if c]
        view = _overall_issue_pivot_selection(
            focused, util_group_cols, 'Routes', f'overall_issues_util_pivot{pivot_suffix}', focused
        ) if util_group_cols else focused
        compact_view = compact_detail_frame(view, 'cpk_raw')
        if compact_view.empty:
            st.info('No matching utilization records for this issue.')
        else:
            render_centered_html_table(compact_view, height=420)

    focused_kind = 'ops_raw' if issue_type in operations_issues else ('pay_raw' if issue_type in payment_groups else 'cpk_raw')
    focused_compact = compact_detail_frame(focused, focused_kind)
    if not focused_compact.empty:
        focused_excel = io.BytesIO()
        with pd.ExcelWriter(focused_excel, engine='xlsxwriter') as writer:
            write_styled_sheet_to_excel(writer, focused_compact, 'Selected_Issue_Raw', sheet_type=focused_kind)
        st.download_button(
            f'📥 Download only {issue_type} raw records (formatted Excel)',
            data=focused_excel.getvalue(),
            file_name=f"Overall_Issue_{safe_issue_key}_{selected_ro}_{start_date:%Y%m%d}_{end_date:%Y%m%d}.xlsx",
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            key='overall_issues_focused_download'
        )

    title = f"Overall Issues · {selected_ro} · {zone} · {start_date:%d %b %Y} to {end_date:%d %b %Y}"
    excel_bytes = build_overall_issues_excel_bytes(summary, payments, operations, utilization, title)
    safe_ro = re.sub(r'[^A-Za-z0-9_-]+', '_', selected_ro).strip('_') or 'ALL_ROS'
    st.download_button(
        '📥 Download Summary + Payment + Operations + Utilization (formatted Excel)',
        data=excel_bytes,
        file_name=f"Overall_Issues_{safe_ro}_{start_date:%Y%m%d}_{end_date:%Y%m%d}.xlsx",
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        type='primary', key='overall_issues_raw_excel'
    )

def _overall_issue_link_markup(issue_type, ro, zone, start_date, end_date, route='ALL ROUTES'):
    params = {
        'issues_raw': '1',
        'issues_auth': create_overall_issue_access_token(st.session_state.get('username', '')),
        'issues_ro': str(ro), 'issues_route': str(route), 'issues_zone': str(zone),
        'issues_type': str(issue_type), 'issues_start': start_date.isoformat(),
        'issues_end': end_date.isoformat()
    }
    params_json = json.dumps(params, ensure_ascii=True).replace('</', '<\\/')
    base_url_json = json.dumps(get_overall_issue_query_url(), ensure_ascii=True).replace('</', '<\\/')
    return params_json, base_url_json

def render_overall_issues_metric_cards(metric_specs, zone=None, start_date=None, end_date=None,
                                       ro='ALL ROS', route='ALL ROUTES'):
    issue_lookup = {
        'Ontime Dep, Ontime Arr': 'Ontime Dep, Ontime Arr',
        'Ontime Dep, Late Arr': 'Ontime Dep, Late Arr',
        'Late Dep, Late Arr': 'Late Dep, Late Arr',
        'Late Dep, Ontime Arr': 'Late Dep, Ontime Arr',
        'Draft Bills': 'Draft bills', 'Pending': 'Pending bills',
        'Payment Pending / Paid': 'Payment pending / paid',
        'Finance Pending': 'Finance pending', 'Finance Hold': 'Finance hold', 'Other': 'Other bills',
        'Underutilized Routes': 'Underutilized routes',
        'Efficiently Utilized Routes': 'Efficiently utilized routes'
    }
    gauge_colors = {
        'Ontime Dep, Ontime Arr': ('#16a34a', '#f0fdf4', '#bbf7d0', '🟢'),
        'Ontime Dep, Late Arr': ('#f87171', '#fff1f2', '#fecdd3', '🌸'),
        'Late Dep, Late Arr': ('#dc2626', '#fef2f2', '#fecaca', '🔴'),
        'Late Dep, Ontime Arr': ('#f59e0b', '#fffbeb', '#fde68a', '🟡'),
        'Draft Bills': ('#dc2626', '#fef2f2', '#fecaca', '🔴'),
        'Pending': ('#f59e0b', '#fffbeb', '#fde68a', '🟡'),
        'Payment Pending / Paid': ('#16a34a', '#f0fdf4', '#bbf7d0', '🟢'),
        'Finance Pending': ('#f59e0b', '#fffbeb', '#fde68a', '🟡'),
        'Finance Hold': ('#dc2626', '#fef2f2', '#fecaca', '🔴'),
        'Other': ('#f59e0b', '#fffbeb', '#fde68a', '🟡'),
        'Underutilized Routes': ('#dc2626', '#fef2f2', '#fecaca', '🔴'),
        'Efficiently Utilized Routes': ('#16a34a', '#f0fdf4', '#bbf7d0', '🟢')
    }
    gauges = []
    for label, count, total, unit in metric_specs:
        issue = issue_lookup.get(label)
        if not issue:
            continue
        pct = min(100, max(0, count / total * 100)) if total else 0
        color, surface, border, icon = gauge_colors[label]
        if not THEME_IS_LIGHT:
            if label in {'Ontime Dep, Ontime Arr', 'Payment Pending / Paid', 'Efficiently Utilized Routes'}:
                tone_key = 'green'
            elif label in {'Ontime Dep, Late Arr'}:
                tone_key = 'soft_red'
            elif label in {'Late Dep, Ontime Arr', 'Draft Bills', 'Finance Hold', 'Underutilized Routes'}:
                tone_key = 'red'
            elif label == 'Late Dep, Late Arr':
                tone_key = 'red'
            else:
                tone_key = 'yellow'
            surface = THEME_STATUS_PALETTE[tone_key][0]
            border = selected_theme['line']
        params_json, base_url_json = _overall_issue_link_markup(issue, ro, zone or 'ALL ZONES', start_date, end_date, route)
        gauge_dash = 201.06 * pct / 100
        gauges.append(f'''<a class="gauge-link" href="#" data-params="{html_module.escape(params_json, quote=True)}" data-base="{html_module.escape(base_url_json, quote=True)}">
          <div class="gauge-card" style="background:{surface};border-color:{border}">
            <div class="gauge-label">{icon} {html_module.escape(label)}</div>
            <svg viewBox="0 0 160 108" role="img" aria-label="{pct:.1f} percent">
              <path d="M 16 88 A 64 64 0 0 1 144 88" fill="none" stroke="{html_module.escape(selected_theme['line'])}" stroke-width="11" stroke-linecap="round" pathLength="201.06"/>
              <path d="M 16 88 A 64 64 0 0 1 144 88" fill="none" stroke="{color}" stroke-width="11" stroke-linecap="round" stroke-dasharray="{gauge_dash:.2f} 201.06" pathLength="201.06"/>
              <text x="80" y="83" text-anchor="middle" font-size="22" font-weight="750" fill="{html_module.escape(selected_theme['text'])}">{pct:.1f}%</text>
              <text x="16" y="104" text-anchor="middle" font-size="9" fill="{html_module.escape(selected_theme['muted'])}">0%</text>
              <text x="144" y="104" text-anchor="middle" font-size="9" fill="{html_module.escape(selected_theme['muted'])}">100%</text>
            </svg>
            <div class="gauge-caption">{count:,} of {total:,} {html_module.escape(unit)}</div>
          </div>
        </a>''')
    markup = '''<!doctype html><html><head><meta charset="utf-8"><style>
    * { box-sizing:border-box; } body { margin:0; font:12px/1.35 Arial,sans-serif; background:#f4f7fb; color:#172033; }
    .grid { display:grid; grid-template-columns:repeat(4,minmax(150px,1fr)); gap:10px; }
    .gauge-link { color:inherit; text-decoration:none; min-width:0; }
    .gauge-link:hover .gauge-card { transform:translateY(-2px); box-shadow:0 10px 24px rgba(15,23,42,.11); }
    .gauge-card { min-width:0; min-height:148px; text-align:center; border:1px solid #dbe4ee; border-radius:15px; padding:.65rem .45rem .55rem; box-shadow:0 6px 18px rgba(15,23,42,.055); transition:transform .14s ease,box-shadow .14s ease; }
    .gauge-label { min-height:2.25rem; color:#172033; font-size:.78rem; font-weight:700; display:flex; justify-content:center; align-items:center; }
    svg { display:block; width:min(100%,160px); height:auto; margin:.05rem auto -.15rem; overflow:visible; }
    .gauge-caption { color:#64748b; font-size:.7rem; font-weight:600; }
    @media(max-width:900px) { .grid { grid-template-columns:repeat(2,minmax(140px,1fr)); } }
    @media(max-width:520px) { .grid { grid-template-columns:1fr; } }
    </style></head><body><div class="grid">CARD_HTML</div><script>
    let lastGaugeOpenAt = 0;
    document.querySelectorAll('.gauge-link').forEach((link) => link.addEventListener('click', (event) => {
      event.preventDefault();
      const now = Date.now();
      if (now - lastGaugeOpenAt < 650) return;
      lastGaugeOpenAt = now;
      try { const base = JSON.parse(link.dataset.base) || document.referrer; const target = new URL(base);
        Object.entries(JSON.parse(link.dataset.params)).forEach(([key,value]) => target.searchParams.set(key,value));
        window.open(target.toString(), '_blank', 'noopener,noreferrer');
      } catch (error) { window.alert('Could not open issue details. Please open the dashboard in a browser tab and try again.'); }
    }));
    </script></body></html>'''.replace('CARD_HTML', ''.join(gauges))
    markup = (markup.replace('background:#f4f7fb; color:#172033;',
                             f"background:{selected_theme['navy950']}; color:{selected_theme['text']};")
              .replace('border:1px solid #dbe4ee;', f"border:1px solid {selected_theme['line']};")
              .replace('color:#172033;', f"color:{selected_theme['text']};")
              .replace('color:#64748b;', f"color:{selected_theme['muted']};"))
    st.components.v1.html(markup, height=560, scrolling=False)

def render_overall_issues_clickable_table(summary, start_date=None, end_date=None,
                                           zone='ALL ZONES', route='ALL ROUTES'):
    """Render rate/count cells as focused, signed new-tab drill-down links."""
    issue_lookup = {
        'Ontime Dep, Ontime Arr': 'Ontime Dep, Ontime Arr',
        'Ontime Dep, Late Arr': 'Ontime Dep, Late Arr',
        'Late Dep, Late Arr': 'Late Dep, Late Arr',
        'Late Dep, Ontime Arr': 'Late Dep, Ontime Arr',
        'Draft Bills': 'Draft bills', 'Pending': 'Pending bills',
        'Payment Pending / Paid': 'Payment pending / paid',
        'Finance Pending': 'Finance pending', 'Finance Hold': 'Finance hold', 'Other': 'Other bills',
        'Underutilized Routes': 'Underutilized routes',
        'Efficiently Utilized Routes': 'Efficiently utilized routes'
    }
    all_columns = [
        'RO Name', 'Zone', 'Total Trips',
        'Ontime Dep, Ontime Arr', 'Ontime Dep, Late Arr', 'Late Dep, Late Arr', 'Late Dep, Ontime Arr',
        'Total Bills', 'Draft Bills', 'Pending', 'Payment Pending / Paid', 'Finance Pending', 'Finance Hold', 'Other',
        'Underutilized Routes', 'Efficiently Utilized Routes'
    ]
    columns = [c for c in all_columns if c in summary.columns]
    header_html = ''.join(f'<th title="{html_module.escape(str(col), quote=True)}">{html_module.escape(str(col))}</th>' for col in columns)
    rows_html = []
    for _, row in summary.iterrows():
        cells = []
        for col in columns:
            value = html_module.escape(str(row.get(col, '')))
            if col in issue_lookup:
                pct = parse_pct_from_str(str(row.get(col, '')))
                if col == 'Ontime Dep, Ontime Arr':
                    tone = 'good'
                elif col == 'Ontime Dep, Late Arr':
                    tone = 'soft-red' if pct is not None and pct > 0 else 'good'
                elif col == 'Late Dep, Late Arr':
                    tone = 'bad' if pct is not None and pct > 0 else 'good'
                elif col == 'Late Dep, Ontime Arr':
                    tone = 'warn' if pct is not None and pct > 0 else 'good'
                elif col in ['Pending', 'Finance Pending', 'Other']:
                    tone = 'warn' if pct is not None and pct > 0 else 'good'
                elif col in ['Finance Hold', 'Draft Bills', 'Underutilized Routes']:
                    tone = 'bad' if pct is not None and pct > 0 else 'good'
                elif col in ['Payment Pending / Paid', 'Efficiently Utilized Routes']:
                    tone = 'good'
                else:
                    tone = 'good'
                params_json, base_url_json = _overall_issue_link_markup(
                    issue_lookup[col], row.get('RO Name', 'ALL ROS'), zone, start_date, end_date, route
                )
                cells.append(f'<td><a class="issue-cell {tone}" href="#" data-params="{html_module.escape(params_json, quote=True)}" '
                             f'data-base="{html_module.escape(base_url_json, quote=True)}">{value}</a></td>')
            else:
                cells.append(f'<td>{value}</td>')
        rows_html.append('<tr>' + ''.join(cells) + '</tr>')
    markup = '''<!doctype html><html><head><meta charset="utf-8"><style>
    * { box-sizing:border-box; } body { margin:0; font:12px/1.35 Arial,sans-serif; color:#e5eef9; background:#091521; }
    .wrap { width:100%; height:560px; overflow:auto; border:1px solid #33475b; border-radius:12px; scrollbar-gutter:stable; scrollbar-color:#64748b #e2e8f0; scrollbar-width:auto; }
    .wrap::-webkit-scrollbar { width:12px; height:12px; }
    .wrap::-webkit-scrollbar-track { background:#e2e8f0; border-radius:8px; }
    .wrap::-webkit-scrollbar-thumb { background:#64748b; border:2px solid #e2e8f0; border-radius:8px; }
    table { border-collapse:separate; border-spacing:0; width:max-content; min-width:100%; }
    th { position:sticky; top:0; z-index:2; background:#182b40; color:#bdd1e5; text-align:center; vertical-align:middle; white-space:nowrap; padding:10px 11px; border-bottom:1px solid #3b4c60; }
    td { white-space:nowrap; text-align:center; vertical-align:middle; padding:8px 11px; border-bottom:1px solid rgba(148,163,184,.13); }
    tr:nth-child(even) td { background:rgba(30,49,69,.44); }
    th:nth-child(1), td:nth-child(1) { position:sticky; left:0; min-width:132px; z-index:3; }
    th:nth-child(2), td:nth-child(2) { position:sticky; left:132px; min-width:105px; z-index:3; }
    th:nth-child(3), td:nth-child(3) { position:sticky; left:237px; min-width:84px; z-index:3; }
    th:nth-child(-n+3) { background:#182b40; z-index:4; }
    tr:nth-child(odd) td:nth-child(-n+3) { background:#091521; }
    tr:nth-child(even) td:nth-child(-n+3) { background:#122b40; }
    .issue-cell { display:block; margin:-8px -11px; padding:8px 11px; color:inherit; text-decoration:none; font-weight:700; }
    .issue-cell.good { background:rgba(52,211,153,.15); color:#a7f3d0; }
    .issue-cell.soft-red { background:rgba(244,63,94,.18); color:#fda4af; }
    .issue-cell.warn { background:rgba(250,204,21,.16); color:#fde68a; }
    .issue-cell.bad { background:rgba(248,113,113,.22); color:#fecaca; }
    .issue-cell.recover { background:rgba(192,132,252,.18); color:#e9d5ff; }
    .status-cell { font-weight:700; }
    .status-cell.good { background:rgba(52,211,153,.15); color:#a7f3d0; }
    .status-cell.warn { background:rgba(250,204,21,.16); color:#fde68a; }
    .status-cell.bad { background:rgba(248,113,113,.22); color:#fecaca; }
    .issue-cell:hover { outline:2px solid #67e8f9; outline-offset:-2px; filter:brightness(1.18); }
    </style></head><body><div class="wrap"><table><thead><tr>HEADER_HTML</tr></thead><tbody>ROWS_HTML</tbody></table></div><script>
    let lastIssueOpenAt = 0;
    document.querySelectorAll('.issue-cell').forEach((link) => link.addEventListener('click', (event) => {
      event.preventDefault();
      const now = Date.now();
      if (now - lastIssueOpenAt < 650) return;
      lastIssueOpenAt = now;
      try { const base = JSON.parse(link.dataset.base) || document.referrer; const target = new URL(base);
        Object.entries(JSON.parse(link.dataset.params)).forEach(([key,value]) => target.searchParams.set(key,value));
        window.open(target.toString(), '_blank', 'noopener,noreferrer');
      } catch (error) { window.alert('Could not open issue details. Please open the dashboard in a browser tab and try again.'); }
    }));
    </script></body></html>'''.replace('HEADER_HTML', header_html).replace('ROWS_HTML', ''.join(rows_html))
    issue_status_styles = {
        'good': THEME_STATUS_PALETTE['green'],
        'soft-red': THEME_STATUS_PALETTE['soft_red'],
        'warn': THEME_STATUS_PALETTE['yellow'],
        'bad': THEME_STATUS_PALETTE['red'],
        'recover': THEME_STATUS_PALETTE['purple']
    }
    issue_theme_colors = {
        'color:#e5eef9; background:#091521;': f"color:{selected_theme['text']}; background:{selected_theme['navy950']};",
        'border:1px solid #33475b;': f"border:1px solid {selected_theme['line']};",
        'background:#182b40; color:#bdd1e5;': f"background:{selected_theme['navy800']}; color:{selected_theme['text']};",
        'th:nth-child(-n+3) { background:#182b40; z-index:4; }': f"th:nth-child(-n+3) {{ background:{selected_theme['navy800']}; z-index:4; }}",
        'border-bottom:1px solid #3b4c60;': f"border-bottom:1px solid {selected_theme['line']};",
        'rgba(30,49,69,.44)': f"color-mix(in srgb,{selected_theme['navy800']} 70%,transparent)",
        'rgba(148,163,184,.13)': f"color-mix(in srgb,{selected_theme['line']} 65%,transparent)",
        'background:#091521;': f"background:{selected_theme['navy950']};",
        'background:#122b40;': f"background:{selected_theme['navy800']};",
        '#e2e8f0': selected_theme['navy800'],
        '#64748b': selected_theme['muted'],
        '#67e8f9': selected_theme['accent']
    }
    base_issue_status_styles = {
        'good': 'rgba(52,211,153,.15); color:#a7f3d0;',
        'soft-red': 'rgba(244,63,94,.18); color:#fda4af;',
        'warn': 'rgba(250,204,21,.16); color:#fde68a;',
        'bad': 'rgba(248,113,113,.22); color:#fecaca;',
        'recover': 'rgba(192,132,252,.18); color:#e9d5ff;'
    }
    for issue_tone, (issue_bg, issue_text) in issue_status_styles.items():
        issue_theme_colors[base_issue_status_styles[issue_tone]] = f"{issue_bg}; color:{issue_text};"
    for old_color, new_color in issue_theme_colors.items():
        markup = markup.replace(old_color, new_color)
    st.components.v1.html(markup, height=580, scrolling=False)

def render_overall_issues(data):
    st.markdown('## ⚠️ Overall Issues')
    if overall_issue_raw_view:
        render_overall_issue_raw_page(data, issue_query)
        return
    st.caption('Combined operations outcomes, payment exceptions, and route utilization · click a rate/count cell to inspect focused records.')
    ops_all, pay_all = get_overall_issue_frames(data)
    cpk_all = get_overall_cpk_frame(data)
    if ops_all.empty and pay_all.empty and cpk_all.empty:
        st.info('No operations, payment, or utilization records are available yet. Upload the relevant files and process the data first.')
        return
    try:
        source_signature = file_version(FILE_MAP['FINAL_OUTPUT']) if os.path.exists(FILE_MAP['FINAL_OUTPUT']) else None
        payment_signature = file_version(FILE_MAP['PAYMENT']) if os.path.exists(FILE_MAP.get('PAYMENT', '')) else None
        branch_signature = file_version(FILE_MAP['BRANCH_MASTER']) if os.path.exists(FILE_MAP.get('BRANCH_MASTER', '')) else None
    except Exception:
        source_signature, payment_signature, branch_signature = None, None, None
    source_key = (source_signature, payment_signature, branch_signature,
                  st.session_state.get('username'), st.session_state.get('all_vendors', True))
    filter_options_cache = st.session_state.get('_overall_issues_filter_options_cache')
    if filter_options_cache and filter_options_cache[0] == source_key:
        all_start, all_end = filter_options_cache[1], filter_options_cache[2]
        zones = list(filter_options_cache[3])
    else:
        all_start, all_end = get_overall_issue_date_bounds(ops_all, pay_all, cpk_all)
        zones = set()
        for frame in [ops_all, pay_all, cpk_all]:
            zone_name_col = get_col(frame, ['Zone'])
            if zone_name_col:
                zones.update(frame[zone_name_col].dropna().astype(str).str.strip().str.upper().tolist())
        zones = sorted(z for z in zones if z and z not in ('NAN', 'NONE'))
        st.session_state['_overall_issues_filter_options_cache'] = (source_key, all_start, all_end, tuple(zones))
    date_key = 'overall_issues_date_range'
    if date_key not in st.session_state:
        st.session_state[date_key] = (all_start, all_end)
    all_col = st.columns([1, 3])[0]
    if all_col.button('All Available Days', use_container_width=True):
        st.session_state[date_key] = (all_start, all_end)
        st.rerun()
    zone_options = ['ALL ZONES'] + zones
    zone_col, date_col = st.columns([1, 2])
    selected_zone = zone_col.selectbox('Zone', zone_options, key='overall_issues_zone')
    selected_dates = date_col.date_input('Duration', key=date_key,
        help='Operations use MCD start date, payments use Base Date, utilization uses trip date.')
    if isinstance(selected_dates, (list, tuple)) and len(selected_dates) == 2:
        start_date, end_date = selected_dates
    else:
        start_date = end_date = selected_dates
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    st.caption(f"Showing {start_date:%d %b %Y} to {end_date:%d %b %Y}. Operations use MCD start date; payments use Base Date; utilization uses trip date.")
    filtered_key = (source_key, selected_zone, start_date, end_date)
    filtered_cache = st.session_state.get('_overall_issues_filtered_cache')
    if filtered_cache and filtered_cache[0] == filtered_key:
        ops_base, pay_base, cpk_base = filtered_cache[1:]
    else:
        ops_base, pay_base = filter_overall_issue_frames(ops_all, pay_all, start_date, end_date, selected_zone)
        cpk_base = filter_overall_utilization_frame(cpk_all, start_date, end_date, selected_zone)
        st.session_state['_overall_issues_filtered_cache'] = (filtered_key, ops_base, pay_base, cpk_base)

    ro_options = {'ALL ROS'}
    for frame, candidates in [
        (ops_base, ['Origin RO', 'RO Name', 'RO']),
        (pay_base, ['RO Name', 'Origin RO', 'RO']),
        (cpk_base, ['RO_Clean', 'VendorRO', 'RO'])
    ]:
        ro_col = get_col(frame, candidates)
        if ro_col:
            ro_options.update(_clean_ro_series(frame[ro_col]).tolist())
    ro_options = ['ALL ROS'] + sorted(x for x in ro_options if x != 'ALL ROS')
    ro_filter_col, route_filter_col = st.columns(2)
    selected_ro = ro_filter_col.selectbox('RO', ro_options, key='overall_issues_main_ro')

    def filter_frame_ro(frame, candidates):
        result = frame
        col = get_col(result, candidates)
        if selected_ro != 'ALL ROS':
            result = result[_clean_ro_series(result[col]).eq(selected_ro)].copy() if col else result.iloc[0:0].copy()
        return result

    ops_ro_view = filter_frame_ro(ops_base, ['Origin RO', 'RO Name', 'RO'])
    pay_view = filter_frame_ro(pay_base, ['RO Name', 'Origin RO', 'RO'])
    cpk_ro_view = filter_frame_ro(cpk_base, ['RO_Clean', 'VendorRO', 'RO'])
    route_options = {'ALL ROUTES'}
    ops_route_col = get_col(ops_ro_view, ['Route Path', 'Route'])
    if ops_route_col:
        route_options.update(ops_ro_view[ops_route_col].dropna().astype(str).str.strip().tolist())
    cpk_route_col = get_col(cpk_ro_view, ['Final_Route', 'Route (UP/DOWN)', 'Route'])
    if cpk_route_col:
        route_options.update(cpk_ro_view[cpk_route_col].dropna().astype(str).str.strip().tolist())
    route_options = ['ALL ROUTES'] + sorted(x for x in route_options if x and x != 'ALL ROUTES')
    selected_route = route_filter_col.selectbox('Route', route_options, key='overall_issues_main_route')
    ops_view = ops_ro_view
    cpk_view = cpk_ro_view
    if selected_route != 'ALL ROUTES':
        if ops_route_col:
            ops_view = ops_view[ops_view[ops_route_col].fillna('').astype(str).str.strip().eq(selected_route)].copy()
        if cpk_route_col:
            cpk_view = cpk_view[cpk_view[cpk_route_col].fillna('').astype(str).str.strip().eq(selected_route)].copy()

    summary_key = ('remark-gauges-finance-split-v3', source_key, selected_zone, start_date, end_date, selected_ro, selected_route)
    summary_cache = st.session_state.get('_overall_issues_summary_cache')
    if summary_cache and summary_cache[0] == summary_key:
        summary = summary_cache[1].copy()
    else:
        summary = build_overall_issues_summary(ops_view, pay_view, cpk_view)
        st.session_state['_overall_issues_summary_cache'] = (summary_key, summary.copy())
    if summary.empty:
        st.info('No records match this zone and duration.')
        return
    trips = int(summary['Total Trips'].sum()) if 'Total Trips' in summary else len(ops_view)
    bills = int(summary['Total Bills'].sum()) if 'Total Bills' in summary else len(pay_view)
    outcome_labels = ['Ontime Dep, Ontime Arr', 'Ontime Dep, Late Arr', 'Late Dep, Late Arr', 'Late Dep, Ontime Arr']
    metric_specs = [
        (label, sum(_overall_count_from_cell(v) for v in summary.get(label, pd.Series(dtype=object))), trips, 'trips')
        for label in outcome_labels
    ]
    metric_specs += [
        (label, sum(_overall_count_from_cell(v) for v in summary.get(label, pd.Series(dtype=object))), bills, 'bills')
        for label in ['Draft Bills', 'Pending', 'Payment Pending / Paid', 'Finance Pending', 'Finance Hold', 'Other']
    ]
    utilization_count = sum(_overall_count_from_cell(v) for v in summary.get('Underutilized Routes', pd.Series(dtype=object)))
    efficient_count = sum(_overall_count_from_cell(v) for v in summary.get('Efficiently Utilized Routes', pd.Series(dtype=object)))
    utilization_total = utilization_count + efficient_count
    metric_specs += [
        ('Underutilized Routes', utilization_count, utilization_total, 'routes'),
        ('Efficiently Utilized Routes', efficient_count, utilization_total, 'routes')
    ]
    ops_on_time = metric_specs[0][1] if metric_specs else 0
    ops_late_arrivals = sum(
        _overall_count_from_cell(v)
        for label in ['Ontime Dep, Late Arr', 'Late Dep, Late Arr']
        for v in summary.get(label, pd.Series(dtype=object))
    )
    draft_bills = next((count for label, count, _, _ in metric_specs if label == 'Draft Bills'), 0)
    finance_followup = sum(count for label, count, _, _ in metric_specs if label in ['Finance Pending', 'Finance Hold'])
    overall_on_time_pct = ops_on_time / trips * 100 if trips else 0
    overall_issue_insights = []
    if trips:
        overall_issue_insights.append(
            f"{overall_on_time_pct:.1f}% of scoped trips were on time for both departure and arrival."
        )
        overall_issue_insights.append(f"{ops_late_arrivals:,} scoped trips arrived late.")
    if bills:
        overall_issue_insights.append(
            f"Finance follow-up covers {finance_followup:,} bills; {draft_bills:,} bills are in the draft bucket."
        )
    if utilization_total:
        overall_issue_insights.append(
            f"{utilization_count:,} of {utilization_total:,} scoped routes are underutilized."
        )
    render_powerbi_insights(
        'Cross-Module Executive Brief',
        [('Operations trips', f'{trips:,}'), ('On-time end-to-end', f'{overall_on_time_pct:.1f}%'),
         ('Late arrivals', f'{ops_late_arrivals:,}'), ('Bills in scope', f'{bills:,}'),
         ('Finance follow-up', f'{finance_followup:,}'), ('Underutilized routes', f'{utilization_count:,}')],
        overall_issue_insights,
        period_note='Signals follow the selected duration, zone, RO, and route. Use the date range for period selection.'
    )
    render_overall_issues_metric_cards(
        metric_specs, selected_zone, start_date, end_date, selected_ro, selected_route
    )
    st.markdown('### RO-wise issue summary')
    st.caption('Click a gauge or a rate/count cell to open only that issue type. Operations, payment, and utilization outcomes use the same colors in the summary below.')
    render_overall_issues_clickable_table(summary, start_date, end_date, selected_zone, selected_route)
    excel_cache = st.session_state.get('_overall_issues_excel_cache')
    if excel_cache and excel_cache[0] == summary_key:
        excel_bytes = excel_cache[1]
    else:
        pct_cols = [c for c in summary.columns if c not in ['RO Name', 'Zone', 'Total Trips', 'Total Bills']]
        excel_bytes = build_formatted_excel_bytes(
            summary, 'Summary', f"Overall Issues · {selected_zone} · {start_date:%d %b %Y} to {end_date:%d %b %Y}",
            percent_columns=pct_cols,
            width_overrides={'RO Name': 17, 'Zone': 16, 'Total Trips': 14, 'Total Bills': 14}
        )
        st.session_state['_overall_issues_excel_cache'] = (summary_key, excel_bytes)
    st.download_button(
        '📊 Download Formatted RO Summary (Excel)', data=excel_bytes,
        file_name=f"Overall_Issues_Summary_{start_date:%Y%m%d}_{end_date:%Y%m%d}.xlsx",
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', key='overall_issues_summary_excel'
    )

def render_ops_remark_gauges(ops_outcome_counts, ops_total_trips, ops_outcome_labels, gauge_context):
    """Render interactive Remark-wise gauges; double-clicking any gauge opens its full raw data in a new window."""
    if THEME_IS_LIGHT:
        gauge_tones = {
            'green': ('#16a34a', '#f0fdf4', '#bbf7d0'),
            'soft_red': ('#f472b6', '#fff1f2', '#fecdd3'),
            'red': ('#dc2626', '#fef2f2', '#fecaca'),
            'yellow': ('#f59e0b', '#fffbeb', '#fde68a'),
            'purple': ('#8b5cf6', '#f5f3ff', '#ddd6fe'),
            'muted': (selected_theme['muted'], selected_theme['card2'], selected_theme['line'])
        }
    else:
        gauge_tones = {
            'green': ('#34d399', 'rgba(34,197,94,.16)', 'rgba(52,211,153,.34)'),
            'soft_red': ('#fb7185', 'rgba(244,63,94,.16)', 'rgba(251,113,133,.34)'),
            'red': ('#f87171', 'rgba(248,113,113,.20)', 'rgba(248,113,113,.36)'),
            'yellow': ('#facc15', 'rgba(234,179,8,.17)', 'rgba(250,204,21,.36)'),
            'purple': ('#c084fc', 'rgba(168,85,247,.18)', 'rgba(192,132,252,.36)'),
            'muted': (selected_theme['muted'], selected_theme['card2'], selected_theme['line'])
        }

    base_url_json = json.dumps(get_overall_issue_query_url(), ensure_ascii=True).replace('</', '<\\/')
    token = create_ops_remark_access_token(st.session_state.get('username', ''))
    cards = []

    for outcome_label, outcome_tone, outcome_icon in ops_outcome_labels:
        outcome_count = ops_outcome_counts[outcome_label]
        primary_outcome = outcome_label in {
            'Ontime Dep, Ontime Arr', 'Ontime Dep, Late Arr',
            'Late Dep, Late Arr', 'Late Dep, Ontime Arr'
        }
        if not (primary_outcome or outcome_count > 0):
            continue
        gauge_pct = min(100, max(0, outcome_count / ops_total_trips * 100)) if ops_total_trips else 0
        gauge_color, gauge_surface, gauge_border = gauge_tones.get(outcome_tone, gauge_tones['muted'])
        gauge_dash = 201.06 * gauge_pct / 100
        params = {
            'ops_raw': '1',
            'ops_auth': token,
            'ops_outcome': outcome_label,
            'ops_start': gauge_context.get('start', ''),
            'ops_end': gauge_context.get('end', ''),
            'ops_zone': gauge_context.get('zone', 'ALL'),
            'ops_ro': gauge_context.get('ro', 'ALL'),
            'ops_vendor': gauge_context.get('vendor', 'ALL'),
            'ops_route': gauge_context.get('route', 'ALL'),
            'ops_leg': gauge_context.get('leg', 'ALL'),
            'ops_search': gauge_context.get('search', '')
        }
        params_json = json.dumps(params, ensure_ascii=True).replace('</', '<\\/')
        cards.append(f'''<div class="ops-gauge-card" role="button" tabindex="0" title="Double-click to open raw trip data in a new window"
          data-params="{html_module.escape(params_json, quote=True)}" data-base="{html_module.escape(base_url_json, quote=True)}"
          style="background:{gauge_surface};border-color:{gauge_border}">
          <div class="gauge-label">{outcome_icon} {html_module.escape(outcome_label)}</div>
          <svg viewBox="0 0 180 108" role="img" aria-label="{gauge_pct:.1f} percent">
            <path d="M 18 90 A 72 72 0 0 1 162 90" fill="none" stroke="{html_module.escape(selected_theme['line'])}" stroke-width="13" stroke-linecap="round" pathLength="201.06"/>
            <path d="M 18 90 A 72 72 0 0 1 162 90" fill="none" stroke="{gauge_color}" stroke-width="13" stroke-linecap="round" stroke-dasharray="{gauge_dash:.2f} 201.06" pathLength="201.06"/>
            <text x="90" y="75" text-anchor="middle" font-size="27" font-weight="850" fill="{html_module.escape(selected_theme['text'])}">{gauge_pct:.1f}%</text>
            <text x="90" y="99" text-anchor="middle" font-size="14" font-weight="800" fill="{gauge_color}">{outcome_count:,} trips</text>
          </svg>
          <div class="gauge-caption">out of <strong>{ops_total_trips:,}</strong> trips</div>
          <div class="gauge-hint">Double-click for raw data ↗</div>
        </div>''')

    if not cards:
        return

    row_count = (len(cards) + 3) // 4
    frame_height = row_count * 176 + 18
    markup = f'''<!doctype html><html><head><meta charset="utf-8"><style>
    * {{ box-sizing:border-box; }}
    body {{ margin:0; padding:4px 2px; font:12px/1.35 Inter,Arial,sans-serif; background:transparent; color:{selected_theme['text']}; user-select:none; }}
    .grid {{ display:grid; grid-template-columns:repeat(4,minmax(160px,1fr)); gap:12px; }}
    .ops-gauge-card {{
        min-width:0; min-height:162px; text-align:center; border:1px solid {selected_theme['line']};
        border-radius:15px; padding:.72rem .55rem .6rem; cursor:pointer;
        box-shadow:0 6px 18px rgba(15,23,42,.06);
        transition:transform .15s ease, box-shadow .15s ease, border-color .15s ease;
    }}
    .ops-gauge-card:hover {{
        transform:translateY(-3px);
        box-shadow:0 12px 26px rgba(15,23,42,.14);
        border-color:{selected_theme['blue']} !important;
    }}
    .ops-gauge-card:active {{ transform:translateY(-1px) scale(.99); }}
    .gauge-label {{ min-height:2.25rem; color:{selected_theme['text']}; font-size:.82rem; font-weight:700; display:flex; justify-content:center; align-items:center; }}
    svg {{ display:block; width:min(100%,164px); height:auto; margin:.05rem auto -.12rem; overflow:visible; }}
    .gauge-caption {{ color:{selected_theme['muted']}; font-size:.73rem; font-weight:600; }}
    .gauge-hint {{ color:{selected_theme['blue']}; font-size:.66rem; font-weight:650; margin-top:.22rem; opacity:.82; }}
    .ops-gauge-card:hover .gauge-hint {{ opacity:1; text-decoration:underline; }}
    @media(max-width:960px) {{ .grid {{ grid-template-columns:repeat(2,minmax(150px,1fr)); }} }}
    @media(max-width:520px) {{ .grid {{ grid-template-columns:1fr; }} }}
    </style></head><body><div class="grid">{''.join(cards)}</div><script>
    let lastOpsOpenAt = 0;
    function openOpsRawWindow(card) {{
      const now = Date.now();
      if (now - lastOpsOpenAt < 500) return;
      lastOpsOpenAt = now;
      try {{
        const base = JSON.parse(card.dataset.base) || document.referrer || window.location.href;
        const target = new URL(base);
        ['issues_raw','issues_auth','issues_ro','issues_route','issues_zone','issues_type','issues_start','issues_end'].forEach((k) => target.searchParams.delete(k));
        Object.entries(JSON.parse(card.dataset.params)).forEach(([key, value]) => {{
          if (value !== '' && value !== null && value !== undefined) target.searchParams.set(key, value);
          else target.searchParams.delete(key);
        }});
        window.open(target.toString(), '_blank', 'noopener,noreferrer');
      }} catch (error) {{
        window.alert('Could not open raw data window. Please allow pop-ups for this dashboard and try again.');
      }}
    }}
    document.querySelectorAll('.ops-gauge-card').forEach((card) => {{
      card.addEventListener('dblclick', (event) => {{
        event.preventDefault();
        openOpsRawWindow(card);
      }});
      card.addEventListener('keydown', (event) => {{
        if (event.key === 'Enter') {{
          event.preventDefault();
          openOpsRawWindow(card);
        }}
      }});
    }});
    </script></body></html>'''
    st.components.v1.html(markup, height=frame_height, scrolling=False)

def render_centered_html_table(
    df_in,
    height=500,
    num_cols=None,
    bold_cols=None,
    pill_cols=None,
    max_rows=500
):
    """Render a crisp Excel-style table with guaranteed 100% Center + Middle alignment on every cell & header."""
    if df_in is None or df_in.empty:
        st.info("No records match the selected filters.")
        return

    df_view = df_in.head(max_rows).reset_index(drop=True)
    num_set = set(num_cols or []) | {
        'Total Trips', 'Total_Trips', 'Trips', 'Count', 'Total Bills', 'Days Pending',
        'Prev 7D Trips', 'Curr 7D Trips', 'Overall Trips', 'ROs', 'Routes', 'Vendors',
        'Overall CPK', 'Total Capacity', 'Total Carried Wt', 'Total Trip Cost', 'Unique Vendors'
    }
    bold_set = set(bold_cols or []) | {
        'Origin RO', 'RO', 'RO Name', 'VendorRO', 'RO_Clean', 'Legwise', 'Zone',
        'Vendor', 'VendorName', 'Vendor Name', 'User ID', 'Route Code', 'Module Name'
    }
    pill_set = set(pill_cols or []) | {
        'Remark', 'Remark % (Count)', 'Ontime Dep, Ontime Arr', 'Ontime Dep, Late Arr',
        'Late Dep, Late Arr', 'Late Dep, Ontime Arr', 'Late Dep, In-Transit',
        'Ontime Dep, In-Transit', 'Missing Schedule', 'No Departure',
        'Ontime Arrival', 'Late Arrival', 'In-Transit',
        'Remark with 15 min waiver', 'Status', 'Status % (Count)', 'Delay Hours',
        '7D Trend', 'Prev 7D On-Time', 'Curr 7D On-Time', 'Curr 7D Late',
        'Overall On-Time', 'Overall Late', 'Overall Util %', 'Route Utilization', 'Utilization Class',
        'Payment Group', 'Payment Pending / Paid', 'Finance Pending / Hold', 'Finance Pending',
        'Finance Hold', 'Draft', 'Draft Bills', 'Cost Control Pending', 'Other', 'Operations Outcome'
    }

    pal = _ops_window_semantic_palette()

    def _pill_tone(col_name, val_str, row_dict):
        c = str(col_name).lower()
        s = str(val_str).strip().lower()
        if not s or s in ('-', '—', 'nan', 'none'):
            return None
        if 'trend' in c:
            if '▲' in val_str or s.startswith('+'):
                return 'good'
            if '▼' in val_str or s.startswith('-'):
                return 'bad'
            return 'neutral'
        if col_name in ('Remark', 'Remark with 15 min waiver', 'Status'):
            if 'ontime dep, ontime arr' in s or 'ontime arrival' in s or 'strong' in s:
                return 'good'
            if 'late dep, late arr' in s or 'late arrival' in s or 'no dep' in s or 'action needed' in s:
                return 'bad'
            if 'ontime dep, late arr' in s:
                return 'soft_bad'
            if 'late dep, ontime arr' in s:
                return 'recover'
            if 'in-transit' in s or 'missing' in s or 'watch' in s:
                return 'warn'
            return 'neutral'
        if 'remark %' in c or 'status %' in c:
            ref_txt = str(row_dict.get('Remark', row_dict.get('Status', ''))).lower()
            if 'ontime dep, ontime arr' in ref_txt or 'ontime arrival' in ref_txt:
                return 'good'
            if 'late dep, late arr' in ref_txt or 'late arrival' in ref_txt or 'no dep' in ref_txt:
                return 'bad'
            if 'ontime dep, late arr' in ref_txt:
                return 'soft_bad'
            if 'late dep, ontime arr' in ref_txt:
                return 'recover'
            if 'in-transit' in ref_txt or 'missing' in ref_txt:
                return 'warn'
            return 'neutral'
        pct = parse_pct_from_str(val_str)
        if 'ontime' in c or 'on-time' in c:
            if pct is None:
                return 'neutral'
            if pct >= 80:
                return 'good'
            if pct >= 55:
                return 'warn'
            return 'bad'
        if 'late' in c:
            if pct is None or pct == 0:
                return 'neutral'
            return 'bad'
        if 'in-transit' in c or 'missing' in c:
            if pct is None or pct == 0:
                return 'neutral'
            return 'warn'
        if 'util' in c:
            if 'efficient' in s:
                return 'good'
            if 'underutilized' in s:
                return 'bad'
            if pct is not None:
                return 'bad' if pct < 60 else ('warn' if pct < 80 else 'good')
        if 'payment pending / paid' in c or 'payment pending / paid' in s or s == 'paid':
            return 'good'
        if 'finance hold' in c or 'finance hold' in s or 'draft' in c or s == 'draft' or 'disabled' in s:
            return 'bad'
        if 'finance pending' in c or 'finance pending' in s or 'cost control' in c or 'cost control' in s or c == 'other' or s == 'other':
            return 'warn'
        if 'active' in s:
            return 'good'
        if c == 'delay hours' and s not in ('', '-', '0:00'):
            if s.startswith('-'):
                return 'good'
            try:
                pts = s.split(':')
                if (int(pts[0]) + int(pts[1]) / 60.0) > 0.25:
                    return 'bad'
            except Exception:
                pass
            return 'good'
        if 'ontime dep, late arr' in c:
            return 'soft_bad' if (pct is not None and pct > 0) else 'neutral'
        if 'late dep, ontime arr' in c:
            return 'recover' if (pct is not None and pct > 0) else 'neutral'
        if 'late dep, late arr' in c or 'no departure' in c:
            return 'bad' if (pct is not None and pct > 0) else 'neutral'
        return None

    headers = ''.join(f'<th>{html_module.escape(str(c))}</th>' for c in df_view.columns)
    rows_html = []
    cols_list = list(df_view.columns)

    for row_dict in df_view.to_dict(orient='records'):
        tds = []
        for col in cols_list:
            raw_v = row_dict.get(col, '')
            if raw_v is None or (not isinstance(raw_v, (list, dict)) and pd.isna(raw_v)):
                txt = ''
            elif isinstance(raw_v, (int, np.integer)):
                txt = f"{int(raw_v):,}"
            elif isinstance(raw_v, (float, np.floating)) and float(raw_v).is_integer():
                txt = f"{int(raw_v):,}"
            else:
                txt = str(raw_v).strip()

            safe_txt = html_module.escape(txt)
            cls = ''
            style = ''
            if col in num_set:
                style = f'background:{pal["num_bg"]};color:{pal["num_fg"]};font-weight:850;'
            elif col in pill_set:
                tone = _pill_tone(col, txt, row_dict)
                if tone and tone in pal:
                    bg, fg, acc = pal[tone]
                    style = f'background:{bg};color:{fg};font-weight:800;box-shadow:inset 3px 0 0 {acc};'
            elif col in bold_set:
                cls = ' class="c-bold"'
            tds.append(f'<td{cls} style="{style}">{safe_txt}</td>' if style else f'<td{cls}>{safe_txt}</td>')
        rows_html.append('<tr>' + ''.join(tds) + '</tr>')

    scroll_thumb = '#94a3b8' if THEME_IS_LIGHT else '#475569'
    scroll_track = '#f1f5f9' if THEME_IS_LIGHT else selected_theme['navy900']
    actual_h = min(int(height), max(130, len(df_view) * 38 + 52))

    doc = (
        f'<!doctype html><html><head><meta charset="utf-8"><style>'
        f'* {{ box-sizing:border-box; }}'
        f'html, body {{ margin:0; padding:0; background:transparent; font-family:Inter,system-ui,-apple-system,Segoe UI,Arial,sans-serif; }}'
        f'.tbl-wrap {{ width:100%; height:{actual_h}px; overflow:auto; border:1px solid {pal["border"]}; border-radius:12px; background:{pal["row_even"]}; scrollbar-color:{scroll_thumb} {scroll_track}; scrollbar-width:thin; }}'
        f'.tbl-wrap::-webkit-scrollbar {{ width:10px; height:10px; }}'
        f'.tbl-wrap::-webkit-scrollbar-track {{ background:{scroll_track}; border-radius:8px; }}'
        f'.tbl-wrap::-webkit-scrollbar-thumb {{ background:{scroll_thumb}; border-radius:8px; border:2px solid {scroll_track}; }}'
        f'table {{ width:100%; min-width:max-content; border-collapse:separate; border-spacing:0; font-size:12.8px; color:{pal["text"]}; }}'
        f'thead th {{ position:sticky; top:0; z-index:4; background:{pal["header_bg"]}; color:{pal["header_text"]}; font-weight:800; text-align:center !important; vertical-align:middle !important; padding:10px 12px; border-bottom:2px solid {pal["border"]}; border-right:1px solid {pal["border"]}; white-space:nowrap; }}'
        f'tbody td {{ text-align:center !important; vertical-align:middle !important; padding:8px 12px; border-bottom:1px solid {pal["border"]}; border-right:1px solid {pal["border"]}; white-space:nowrap; }}'
        f'thead th:last-child, tbody td:last-child {{ border-right:none; }}'
        f'tbody tr:nth-child(odd) {{ background:{pal["row_even"]}; }}'
        f'tbody tr:nth-child(even) {{ background:{pal["row_odd"]}; }}'
        f'tbody tr:hover td {{ filter:brightness(0.97); }}'
        f'td.c-bold {{ font-weight:750; }}'
        f'</style></head><body>'
        f'<div class="tbl-wrap"><table><thead><tr>{headers}</tr></thead><tbody>{"".join(rows_html)}</tbody></table></div>'
        f'</body></html>'
    )
    st.components.v1.html(doc, height=actual_h + 6, scrolling=False)
    if len(df_in) > max_rows:
        st.caption(f"Showing first {max_rows:,} of {len(df_in):,} rows for smooth performance. Download Excel for all rows.")

def _sort_ops_window_df(df):
    """Sort strictly by Origin RO (A->Z), Route Path (A->Z), Legwise (A->Z), and Remark (Z->A)."""
    if df is None or df.empty:
        return df
    out = df.copy()
    sort_cols = []
    ascending_flags = []

    if 'Origin RO' in out.columns:
        out['_s_ro'] = out['Origin RO'].fillna('').astype(str).str.strip().str.upper()
        sort_cols.append('_s_ro')
        ascending_flags.append(True)

    if 'Route Path' in out.columns:
        out['_s_route'] = out['Route Path'].fillna('').astype(str).str.strip().str.upper()
        sort_cols.append('_s_route')
        ascending_flags.append(True)

    if 'Legwise' in out.columns:
        out['_s_leg_num'] = extract_leg_num_val(out['Legwise'])
        out['_s_leg_txt'] = out['Legwise'].fillna('').astype(str).str.strip().str.upper()
        sort_cols.extend(['_s_leg_num', '_s_leg_txt'])
        ascending_flags.extend([True, True])

    remark_sort_col = 'Remark' if 'Remark' in out.columns else ('_OpsRemarkOutcome' if '_OpsRemarkOutcome' in out.columns else None)
    if remark_sort_col:
        out['_s_remark'] = out[remark_sort_col].fillna('').astype(str).str.strip().str.upper()
        sort_cols.append('_s_remark')
        ascending_flags.append(False)  # Z to A

    if sort_cols:
        out = out.sort_values(by=sort_cols, ascending=ascending_flags, kind='mergesort')

    drop_helpers = [c for c in ['_s_ro', '_s_route', '_s_leg_num', '_s_leg_txt', '_s_remark'] if c in out.columns]
    if drop_helpers:
        out = out.drop(columns=drop_helpers)
    return out.reset_index(drop=True)

def _ops_window_semantic_palette():
    """Clean semantic palette: crisp accents on status & count cells, neutral data rows."""
    if THEME_IS_LIGHT:
        return {
            'row_even': '#ffffff', 'row_odd': '#f8fafc', 'text': '#1e293b', 'border': '#e2e8f0',
            'header_bg': '#eef2f7', 'header_text': '#0f172a',
            'num_bg': '#eff6ff', 'num_fg': '#1e3a8a',
            'good': ('#ecfdf5', '#065f46', '#10b981'),
            'soft_bad': ('#fff1f2', '#9f1239', '#fb7185'),
            'bad': ('#fef2f2', '#991b1b', '#ef4444'),
            'warn': ('#fffbeb', '#92400e', '#f59e0b'),
            'recover': ('#f5f3ff', '#5b21b6', '#8b5cf6'),
            'neutral': ('#f1f5f9', '#475569', '#94a3b8')
        }
    return {
        'row_even': selected_theme['card1'], 'row_odd': selected_theme['card2'],
        'text': selected_theme['text'], 'border': selected_theme['line'],
        'header_bg': selected_theme['navy800'], 'header_text': selected_theme['text'],
        'num_bg': 'rgba(59,130,246,.16)', 'num_fg': '#93c5fd',
        'good': ('rgba(16,185,129,.16)', '#6ee7b7', '#10b981'),
        'soft_bad': ('rgba(244,63,94,.16)', '#fda4af', '#f43f5e'),
        'bad': ('rgba(239,68,68,.18)', '#fca5a5', '#ef4444'),
        'warn': ('rgba(245,158,11,.16)', '#fde68a', '#f59e0b'),
        'recover': ('rgba(139,92,246,.18)', '#ddd6fe', '#8b5cf6'),
        'neutral': ('rgba(148,163,184,.12)', selected_theme['muted'], '#64748b')
    }

def style_ops_window_dataframe(df_in):
    """Clean table styling: neutral zebra rows, bold highlighted counts, and soft status pills."""
    if df_in is None or df_in.empty:
        return df_in
    pal = _ops_window_semantic_palette()

    def pill_css(tone_key):
        bg, fg, accent = pal[tone_key]
        return f'background-color: {bg}; color: {fg}; font-weight: 800; border-left: 3px solid {accent}; text-align: center;'

    def classify_text(val_str):
        s = val_str.lower()
        if 'ontime dep, ontime arr' in s:
            return 'good'
        if 'late dep, late arr' in s or 'no dep' in s:
            return 'bad'
        if 'ontime dep, late arr' in s:
            return 'soft_bad'
        if 'late dep, ontime arr' in s:
            return 'recover'
        if 'in-transit' in s or 'missing' in s:
            return 'warn'
        return 'neutral'

    def style_frame(frame):
        styles = pd.DataFrame('', index=frame.index, columns=frame.columns)
        for i, idx in enumerate(frame.index):
            base_bg = pal['row_even'] if i % 2 == 0 else pal['row_odd']
            styles.loc[idx, :] = f'background-color: {base_bg}; color: {pal["text"]}; text-align: center;'

        for col in frame.columns:
            c_low = str(col).lower()
            if col == 'Remark':
                for idx, val in frame[col].items():
                    styles.loc[idx, col] = pill_css(classify_text(str(val)))
            elif col == 'Ontime Dep, Ontime Arr':
                for idx, val in frame[col].items():
                    pct = parse_pct_from_str(str(val))
                    if pct is None or pct == 0:
                        styles.loc[idx, col] = pill_css('bad' if pct == 0 else 'neutral')
                    elif pct >= 70:
                        styles.loc[idx, col] = pill_css('good')
                    elif pct >= 40:
                        styles.loc[idx, col] = pill_css('warn')
                    else:
                        styles.loc[idx, col] = pill_css('bad')
            elif 'remark %' in c_low:
                remark_series = frame['Remark'] if 'Remark' in frame.columns else pd.Series('', index=frame.index)
                for idx, val in frame[col].items():
                    styles.loc[idx, col] = pill_css(classify_text(str(remark_series.loc[idx])))
            elif col in ('Total Trips', 'Trips', 'Count'):
                for idx in frame.index:
                    styles.loc[idx, col] = f'background-color: {pal["num_bg"]}; color: {pal["num_fg"]}; font-weight: 850; text-align: center;'
            elif col in ('Origin RO', 'Legwise'):
                for idx in frame.index:
                    styles.loc[idx, col] += ' font-weight: 700;'
        return styles

    return (
        df_in.style
        .apply(style_frame, axis=None)
        .set_properties(**{'border-color': pal['border'], 'font-size': '13px', 'padding': '8px 10px', 'text-align': 'center', 'vertical-align': 'middle'})
        .set_table_styles([
            {'selector': 'th', 'props': [
                ('background-color', pal['header_bg']), ('color', pal['header_text']),
                ('font-weight', '800'), ('border-color', pal['border']), ('padding', '9px 10px'),
                ('text-align', 'center')
            ]},
            {'selector': 'td', 'props': [('text-align', 'center'), ('vertical-align', 'middle')]}
        ], overwrite=False)
    )

def build_ops_window_excel_bytes(breakdown_df, raw_df, report_title):
    """Build a clean 2-sheet Excel workbook (Route_Leg_Breakdown + Detailed_Raw_Trips)."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        wb = writer.book
        title_fmt = wb.add_format({'bold': True, 'font_size': 15, 'font_color': '#FFFFFF', 'bg_color': '#0F2942', 'valign': 'vcenter'})
        sub_fmt = wb.add_format({'font_color': '#475569', 'italic': True, 'bg_color': '#EDF2F7', 'valign': 'vcenter', 'font_size': 10})
        head_fmt = wb.add_format({'bold': True, 'font_color': '#FFFFFF', 'bg_color': '#1B365D', 'border': 1, 'border_color': '#CBD5E1', 'align': 'center', 'valign': 'vcenter', 'text_wrap': True})
        even_fmt = wb.add_format({'bg_color': '#FFFFFF', 'font_color': '#1E293B', 'border': 1, 'border_color': '#E2E8F0', 'align': 'center', 'valign': 'vcenter'})
        odd_fmt = wb.add_format({'bg_color': '#F8FAFC', 'font_color': '#1E293B', 'border': 1, 'border_color': '#E2E8F0', 'align': 'center', 'valign': 'vcenter'})
        num_fmt = wb.add_format({'bg_color': '#EFF6FF', 'font_color': '#1E3A8A', 'bold': True, 'border': 1, 'border_color': '#BFDBFE', 'align': 'center', 'valign': 'vcenter', 'num_format': '#,##0'})

        pill_fmts = {
            'good': wb.add_format({'bg_color': '#ECFDF5', 'font_color': '#065F46', 'bold': True, 'border': 1, 'border_color': '#A7F3D0', 'align': 'center', 'valign': 'vcenter'}),
            'bad': wb.add_format({'bg_color': '#FEF2F2', 'font_color': '#991B1B', 'bold': True, 'border': 1, 'border_color': '#FECACA', 'align': 'center', 'valign': 'vcenter'}),
            'soft_bad': wb.add_format({'bg_color': '#FFF1F2', 'font_color': '#9F1239', 'bold': True, 'border': 1, 'border_color': '#FECDD3', 'align': 'center', 'valign': 'vcenter'}),
            'warn': wb.add_format({'bg_color': '#FFFBEB', 'font_color': '#92400E', 'bold': True, 'border': 1, 'border_color': '#FDE68A', 'align': 'center', 'valign': 'vcenter'}),
            'recover': wb.add_format({'bg_color': '#F5F3FF', 'font_color': '#5B21B6', 'bold': True, 'border': 1, 'border_color': '#DDD6FE', 'align': 'center', 'valign': 'vcenter'}),
            'neutral': wb.add_format({'bg_color': '#F1F5F9', 'font_color': '#475569', 'bold': True, 'border': 1, 'border_color': '#CBD5E1', 'align': 'center', 'valign': 'vcenter'})
        }

        def tone_for(text):
            s = str(text).lower()
            if 'ontime dep, ontime arr' in s:
                return 'good'
            if 'late dep, late arr' in s or 'no dep' in s:
                return 'bad'
            if 'ontime dep, late arr' in s:
                return 'soft_bad'
            if 'late dep, ontime arr' in s:
                return 'recover'
            if 'in-transit' in s or 'missing' in s:
                return 'warn'
            return 'neutral'

        for s_name, df_src in [('Route_Leg_Breakdown', breakdown_df), ('Detailed_Raw_Trips', raw_df)]:
            frame = df_src.copy() if isinstance(df_src, pd.DataFrame) and not df_src.empty else pd.DataFrame({'Status': ['No matching records.']})
            frame = frame.reset_index(drop=True)
            ws = wb.add_worksheet(s_name)
            writer.sheets[s_name] = ws
            ncols = max(len(frame.columns), 1)
            ws.merge_range(0, 0, 0, ncols - 1, report_title, title_fmt)
            ws.merge_range(1, 0, 1, ncols - 1, f"{s_name.replace('_', ' ')} · Origin RO (A→Z), Route Path (A→Z), Legwise (A→Z), Remark (Z→A) · {get_ist_now():%d %b %Y, %I:%M %p} IST", sub_fmt)
            ws.set_row(0, 28)
            ws.set_row(1, 20)
            ws.set_row(2, 28)

            for ci, col in enumerate(frame.columns):
                ws.write(2, ci, str(col), head_fmt)

            for ri, (_, row) in enumerate(frame.iterrows(), start=3):
                is_even = (ri - 3) % 2 == 0
                base_fmt = even_fmt if is_even else odd_fmt
                row_remark = str(row.get('Remark', ''))
                for ci, col in enumerate(frame.columns):
                    val = row[col]
                    if isinstance(val, np.generic):
                        val = val.item()
                    if val is None or (not isinstance(val, (list, dict)) and pd.isna(val)):
                        val = ''
                    c_low = str(col).lower()
                    fmt = base_fmt
                    if col == 'Remark':
                        fmt = pill_fmts[tone_for(val)]
                    elif col == 'Ontime Dep, Ontime Arr':
                        pct = parse_pct_from_str(str(val))
                        fmt = pill_fmts['good'] if (pct is not None and pct >= 70) else (pill_fmts['warn'] if (pct is not None and pct >= 40) else pill_fmts['bad'])
                    elif 'remark %' in c_low:
                        fmt = pill_fmts[tone_for(row_remark)]
                    elif isinstance(val, (int, float)) and not isinstance(val, bool):
                        fmt = num_fmt

                    if isinstance(val, (int, float)) and not isinstance(val, bool):
                        ws.write_number(ri, ci, val, fmt)
                    else:
                        ws.write(ri, ci, str(val), fmt)
                ws.set_row(ri, 22)

            for ci, col in enumerate(frame.columns):
                vals = frame[col].fillna('').astype(str).tolist()
                max_len = max([len(str(col))] + [min(len(v), 52) for v in vals]) + 3
                ws.set_column(ci, ci, min(max(max_len, 12), 40))
            ws.autofilter(2, 0, len(frame) + 2, ncols - 1)
            ws.freeze_panes(3, 0)
            ws.set_landscape()
            ws.fit_to_pages(1, 0)
            ws.repeat_rows(2)
            ws.set_margins(0.25, 0.25, 0.35, 0.35)
    return buffer.getvalue()

def render_ops_window_remark_gauges(base_scope_df, active_remarks, gauge_context, remark_state_key, available_remarks):
    """Render Remark-wise gauges in exact sequence; double-clicking any gauge filters the tables below in-place."""
    scope_total = len(base_scope_df)
    counts = base_scope_df['_OpsRemarkOutcome'].value_counts().to_dict() if not base_scope_df.empty else {}

    primary_sequence = [
        ('Ontime Dep, Ontime Arr', '#16a34a', '#f0fdf4', '#bbf7d0', '🟢'),
        ('Ontime Dep, Late Arr', '#f43f5e', '#fff1f2', '#fecdd3', '🌸'),
        ('Late Dep, Late Arr', '#dc2626', '#fef2f2', '#fecaca', '🔴'),
        ('Late Dep, Ontime Arr', '#8b5cf6', '#f5f3ff', '#ddd6fe', '🟣'),
    ]
    extra_sequence = [
        ('Late Dep, In-Transit', '#f59e0b', '#fffbeb', '#fde68a', '🟡'),
        ('Ontime Dep, In-Transit', '#f59e0b', '#fffbeb', '#fde68a', '🟡'),
        ('Missing Schedule', '#f59e0b', '#fffbeb', '#fde68a', '🟡'),
        ('No Departure', '#dc2626', '#fef2f2', '#fecaca', '🔴'),
        ('In-Transit', '#f59e0b', '#fffbeb', '#fde68a', '🟡'),
        ('Other', '#64748b', '#f8fafc', '#e2e8f0', '⚪'),
    ]

    items = list(primary_sequence)
    for item in extra_sequence:
        if int(counts.get(item[0], 0)) > 0:
            items.append(item)

    if THEME_IS_LIGHT:
        track_c, text_c, muted_c = '#e2e8f0', '#0f172a', '#475569'
    else:
        track_c, text_c, muted_c = 'rgba(148,163,184,.22)', selected_theme['text'], selected_theme['muted']

    # Hidden Streamlit trigger buttons so double-clicking any gauge updates the tables below in-place
    def _pick_remark_from_gauge(chosen_label):
        if chosen_label in available_remarks:
            st.session_state[remark_state_key] = [chosen_label]

    st.markdown("""
    <style>
    .st-key-ops_gauge_triggers_box {
        position: fixed !important; left: -9999px !important; top: -9999px !important;
        width: 0px !important; height: 0px !important; max-height: 0px !important;
        overflow: hidden !important; opacity: 0 !important; margin: 0 !important; padding: 0 !important;
        pointer-events: none !important;
    }
    </style>
    """, unsafe_allow_html=True)
    try:
        _ops_t_box = st.container(key="ops_gauge_triggers_box")
    except TypeError:
        _ops_t_box = st.container()
    with _ops_t_box:
        for idx, (label, _, _, _, _) in enumerate(items):
            st.button(
                f"__OPS_GPICK__{label}",
                key=f"ops_win_gpick_{idx}_{re.sub(r'[^A-Za-z0-9]+', '_', label)}",
                on_click=_pick_remark_from_gauge,
                args=(label,)
            )

    base_url_json = json.dumps(get_overall_issue_query_url(), ensure_ascii=True).replace('</', '<\\/')
    token = create_ops_remark_access_token(st.session_state.get('username', ''))

    cards = []
    for label, color, light_bg, light_border, icon in items:
        cnt = int(counts.get(label, 0))
        pct = (cnt / scope_total * 100.0) if scope_total else 0.0
        dash = 201.06 * min(100.0, max(0.0, pct)) / 100.0
        bg = light_bg if THEME_IS_LIGHT else selected_theme['card1']
        border = light_border if THEME_IS_LIGHT else selected_theme['line']
        is_active = label in active_remarks
        ring_css = f'box-shadow: 0 0 0 2.5px {color}, 0 8px 20px rgba(15,23,42,.10);' if is_active else 'box-shadow: 0 4px 14px rgba(15,23,42,.05);'

        params = {
            'ops_raw': '1',
            'ops_auth': token,
            'ops_outcome': label,
            'ops_start': gauge_context.get('start', ''),
            'ops_end': gauge_context.get('end', ''),
            'ops_zone': gauge_context.get('zone', 'ALL'),
            'ops_ro': gauge_context.get('ro', 'ALL'),
            'ops_route': gauge_context.get('route', 'ALL'),
            'ops_vendor': gauge_context.get('vendor', 'ALL'),
            'ops_search': gauge_context.get('search', '')
        }
        params_json = json.dumps(params, ensure_ascii=True).replace('</', '<\\/')

        cards.append(
            f'<div class="rm-card" role="button" tabindex="0" title="Double-click to filter {html_module.escape(label)} below" '
            f'data-label="{html_module.escape(label, quote=True)}" '
            f'data-params="{html_module.escape(params_json, quote=True)}" data-base="{html_module.escape(base_url_json, quote=True)}" '
            f'style="background:{bg};border-color:{border};{ring_css}">'
            f'<div class="rm-label">{icon} {html_module.escape(label)}</div>'
            f'<svg viewBox="0 0 180 108" role="img" aria-label="{pct:.1f} percent">'
            f'<path d="M 18 90 A 72 72 0 0 1 162 90" fill="none" stroke="{track_c}" stroke-width="13" stroke-linecap="round" pathLength="201.06"/>'
            f'<path d="M 18 90 A 72 72 0 0 1 162 90" fill="none" stroke="{color}" stroke-width="13" stroke-linecap="round" stroke-dasharray="{dash:.2f} 201.06" pathLength="201.06"/>'
            f'<text x="90" y="75" text-anchor="middle" font-size="27" font-weight="850" fill="{text_c}">{pct:.1f}%</text>'
            f'<text x="90" y="99" text-anchor="middle" font-size="14" font-weight="800" fill="{color}">{cnt:,} trips</text>'
            f'</svg>'
            f'<div class="rm-sub">out of <strong>{scope_total:,}</strong> trips</div>'
            f'<div class="rm-hint">Double-click to filter below</div>'
            f'</div>'
        )

    rows = (len(cards) + 3) // 4
    height_px = rows * 198 + 16
    html_doc = (
        f'<!doctype html><html><head><meta charset="utf-8"><style>'
        f'* {{ box-sizing:border-box; }}'
        f'body {{ margin:0; padding:3px 2px; font-family:Inter,system-ui,-apple-system,Arial,sans-serif; background:transparent; color:{text_c}; user-select:none; }}'
        f'.grid {{ display:grid; grid-template-columns:repeat(4,minmax(170px,1fr)); gap:12px; }}'
        f'.rm-card {{ border:1px solid; border-radius:15px; padding:10px 10px 8px; text-align:center; cursor:pointer; transition:transform .14s ease, box-shadow .14s ease; }}'
        f'.rm-card:hover {{ transform:translateY(-2px); box-shadow:0 10px 22px rgba(15,23,42,.12) !important; }}'
        f'.rm-card:active {{ transform:translateY(0) scale(.99); }}'
        f'.rm-label {{ font-size:12.5px; font-weight:800; color:{text_c}; min-height:22px; display:flex; align-items:center; justify-content:center; }}'
        f'svg {{ display:block; width:min(100%,180px); height:auto; margin:0 auto; overflow:visible; }}'
        f'.rm-sub {{ font-size:11.5px; font-weight:600; color:{muted_c}; margin-top:2px; }}'
        f'.rm-sub strong {{ color:{text_c}; font-weight:800; }}'
        f'.rm-hint {{ font-size:10.5px; font-weight:650; color:{selected_theme["blue"]}; margin-top:3px; opacity:.82; }}'
        f'.rm-card:hover .rm-hint {{ opacity:1; text-decoration:underline; }}'
        f'@media(max-width:960px) {{ .grid {{ grid-template-columns:repeat(2,minmax(150px,1fr)); }} }}'
        f'@media(max-width:520px) {{ .grid {{ grid-template-columns:1fr; }} }}'
        f'</style></head><body><div class="grid">{"".join(cards)}</div><script>'
        f'function filterGaugeBelow(card) {{'
        f'  const targetLabel = "__OPS_GPICK__" + card.dataset.label;'
        f'  try {{'
        f'    const btns = window.parent.document.querySelectorAll("button");'
        f'    for (const b of btns) {{'
        f'      if ((b.innerText || b.textContent || "").trim() === targetLabel) {{'
        f'        b.click();'
        f'        return;'
        f'      }}'
        f'    }}'
        f'  }} catch (e) {{}}'
        f'  try {{'
        f'    const base = JSON.parse(card.dataset.base) || document.referrer || window.location.href;'
        f'    const target = new URL(base);'
        f'    Object.entries(JSON.parse(card.dataset.params)).forEach(([k, v]) => {{'
        f'      if (v !== "" && v !== null && v !== undefined) target.searchParams.set(k, v);'
        f'      else target.searchParams.delete(k);'
        f'    }});'
        f'    window.top.location.href = target.toString();'
        f'  }} catch (err) {{'
        f'    const base = JSON.parse(card.dataset.base) || document.referrer || window.location.href;'
        f'    const target = new URL(base);'
        f'    Object.entries(JSON.parse(card.dataset.params)).forEach(([k, v]) => {{'
        f'      if (v !== "" && v !== null && v !== undefined) target.searchParams.set(k, v);'
        f'      else target.searchParams.delete(k);'
        f'    }});'
        f'    window.open(target.toString(), "_blank", "noopener,noreferrer");'
        f'  }}'
        f'}}'
        f'document.querySelectorAll(".rm-card").forEach((card) => {{'
        f'  card.addEventListener("dblclick", (e) => {{ e.preventDefault(); filterGaugeBelow(card); }});'
        f'  card.addEventListener("keydown", (e) => {{ if (e.key === "Enter") {{ e.preventDefault(); filterGaugeBelow(card); }} }});'
        f'}});'
        f'</script></body></html>'
    )
    st.components.v1.html(html_doc, height=height_px, scrolling=False)

def render_ops_remark_raw_window(data, query):
    """Full-width new-window view for Operations Remark-wise raw trips."""
    outcome_label = query.get('ops_outcome', 'Ontime Dep, Ontime Arr') or 'Ontime Dep, Ontime Arr'
    icon_lookup = {label: icon for label, _, icon in OPS_REMARK_OUTCOME_LABELS}

    # Hide left sidebar by default for full-width tables, with 1-click button to show & switch modules
    if "ops_win_hide_sidebar" not in st.session_state:
        st.session_state["ops_win_hide_sidebar"] = True

    def _toggle_ops_win_sidebar():
        st.session_state["ops_win_hide_sidebar"] = not st.session_state.get("ops_win_hide_sidebar", True)

    if st.session_state.get("ops_win_hide_sidebar", True):
        st.markdown("""
        <style>
        [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] { display: none !important; }
        [data-testid="stMainBlockContainer"], .block-container {
            max-width: 99% !important;
            padding-left: 1.4rem !important;
            padding-right: 1.4rem !important;
            padding-top: 1.1rem !important;
        }
        </style>
        """, unsafe_allow_html=True)

    df_source = data.get('Legwise_Processed_Data', pd.DataFrame()).copy()
    if df_source.empty:
        st.warning("No processed Operations data available.")
        return

    if not st.session_state.get('all_vendors', True):
        df_source = filter_df_by_user_vendors(df_source, 'VendorName')

    if '_OpsRemarkOutcome' not in df_source.columns:
        df_source['_OpsRemarkOutcome'] = ops_remark_outcome_series(df_source)

    # Apply Date from parent window; Zone, RO, Route, Vendor, Search stay switchable below!
    scoped = df_source.copy()
    start_str = query.get('ops_start', '').strip()
    end_str = query.get('ops_end', '').strip()
    if start_str and end_str and 'MCD_StartDate' in scoped.columns:
        try:
            sd = datetime.date.fromisoformat(start_str)
            ed = datetime.date.fromisoformat(end_str)
            if sd > ed:
                sd, ed = ed, sd
            parsed_d = pd.to_datetime(scoped['MCD_StartDate'], dayfirst=True, errors='coerce')
            scoped = scoped[(parsed_d.dt.date >= sd) & (parsed_d.dt.date <= ed)].copy()
        except Exception:
            pass

    # Seed initial Zone / RO / Route / Vendor / Search from parent query params (user can freely change them!)
    init_sig = (
        outcome_label, start_str, end_str,
        query.get('ops_zone', 'ALL'), query.get('ops_ro', 'ALL'),
        query.get('ops_route', 'ALL'), query.get('ops_leg', 'ALL'), query.get('ops_vendor', 'ALL')
    )
    if st.session_state.get("_ops_win_seed_sig") != init_sig:
        st.session_state["_ops_win_seed_sig"] = init_sig
        st.session_state["ops_win_zone"] = query.get('ops_zone', 'ALL').strip() or "ALL"
        st.session_state["ops_win_ro"] = query.get('ops_ro', 'ALL').strip() or "ALL"
        st.session_state["ops_win_route"] = query.get('ops_route', 'ALL').strip() or "ALL"
        st.session_state["ops_win_leg"] = query.get('ops_leg', 'ALL').strip() or "ALL"
        st.session_state["ops_win_vendor"] = query.get('ops_vendor', 'ALL').strip() or "ALL"
        st.session_state["ops_win_search"] = query.get('ops_search', '').strip()

    available_remarks = sorted(
        set(scoped['_OpsRemarkOutcome'].dropna().astype(str).unique().tolist())
        | {'Ontime Dep, Ontime Arr', 'Ontime Dep, Late Arr', 'Late Dep, Late Arr', 'Late Dep, Ontime Arr'},
        reverse=True
    )
    default_remarks = [outcome_label] if outcome_label in available_remarks else available_remarks
    remark_state_key = f"ops_win_remark_{re.sub(r'[^A-Za-z0-9]+', '_', outcome_label)}"
    if remark_state_key not in st.session_state:
        st.session_state[remark_state_key] = default_remarks

    def _reset_ops_win_filters():
        st.session_state[remark_state_key] = default_remarks
        st.session_state["ops_win_zone"] = "ALL"
        st.session_state["ops_win_ro"] = "ALL"
        st.session_state["ops_win_route"] = "ALL"
        st.session_state["ops_win_leg"] = "ALL"
        st.session_state["ops_win_vendor"] = "ALL"
        st.session_state["ops_win_search"] = ""

    # Top Header Row with Sidebar Show/Hide Toggle Button
    hdr_l, hdr_r = st.columns([5.2, 1.1])
    with hdr_r:
        toggle_lbl = "☰ Show Left Panel" if st.session_state.get("ops_win_hide_sidebar", True) else "✕ Hide Left Panel"
        st.button(toggle_lbl, key="ops_win_sidebar_toggle", use_container_width=True, on_click=_toggle_ops_win_sidebar)

    # Sticky Dynamic Filter Strip (Remark + Switchable Zone + RO + Route + Vendor + Search)
    with st.container():
        st.markdown('<div class="pbi-sticky-anchor"></div>', unsafe_allow_html=True)
        r1_rem, r1_btn = st.columns([5.3, 0.7])
        selected_remarks = r1_rem.multiselect(
            "Filter Remark (Z → A):",
            options=available_remarks,
            key=remark_state_key,
            placeholder="All Remarks (select one or more)..."
        )
        r1_btn.markdown("<div style='height:1.72rem'></div>", unsafe_allow_html=True)
        r1_btn.button("↺ Reset", key="ops_win_reset_btn", use_container_width=True, on_click=_reset_ops_win_filters)

        # Base scope BEFORE Remark filter (Zone & RO are fully switchable across all records in date range)
        base_scope_df = scoped.copy()
        fc_z, fc1, fc2, fc_l, fc3, fc4 = st.columns([0.85, 0.9, 1.3, 0.85, 1.1, 1.3])

        zone_opts = ["ALL"] + sorted(
            z for z in base_scope_df['Zone'].dropna().astype(str).str.strip().unique().tolist()
            if z and z.upper() not in ("NAN", "NONE")
        ) if 'Zone' in base_scope_df.columns else ["ALL"]
        if st.session_state.get("ops_win_zone") not in zone_opts:
            st.session_state["ops_win_zone"] = "ALL"
        sel_zone_local = fc_z.selectbox("Zone:", zone_opts, key="ops_win_zone")
        if sel_zone_local != "ALL" and 'Zone' in base_scope_df.columns:
            base_scope_df = base_scope_df[base_scope_df['Zone'].fillna('').astype(str).str.strip().eq(sel_zone_local)].copy()

        ro_opts = ["ALL"] + sorted(base_scope_df['Origin RO'].dropna().astype(str).unique().tolist()) if 'Origin RO' in base_scope_df.columns else ["ALL"]
        if st.session_state.get("ops_win_ro") not in ro_opts:
            st.session_state["ops_win_ro"] = "ALL"
        sel_ro_local = fc1.selectbox("RO:", ro_opts, key="ops_win_ro")
        if sel_ro_local != "ALL" and 'Origin RO' in base_scope_df.columns:
            base_scope_df = base_scope_df[base_scope_df['Origin RO'].astype(str).eq(sel_ro_local)].copy()

        rt_opts = ["ALL"] + sorted(base_scope_df['Route Path'].dropna().astype(str).unique().tolist()) if 'Route Path' in base_scope_df.columns else ["ALL"]
        if st.session_state.get("ops_win_route") not in rt_opts:
            st.session_state["ops_win_route"] = "ALL"
        sel_rt_local = fc2.selectbox("Route:", rt_opts, key="ops_win_route")
        if sel_rt_local != "ALL" and 'Route Path' in base_scope_df.columns:
            base_scope_df = base_scope_df[base_scope_df['Route Path'].astype(str).eq(sel_rt_local)].copy()

        leg_raw_vals = [v for v in base_scope_df['Legwise'].dropna().astype(str).str.strip().unique().tolist() if v] if 'Legwise' in base_scope_df.columns else []
        leg_opts = ["ALL"] + sorted(leg_raw_vals, key=lambda x: (int(re.search(r'(\d+)', x).group(1)) if re.search(r'(\d+)', x) else 999, x))
        if st.session_state.get("ops_win_leg") not in leg_opts:
            st.session_state["ops_win_leg"] = "ALL"
        sel_leg_local = fc_l.selectbox("Legwise:", leg_opts, key="ops_win_leg")
        if sel_leg_local != "ALL" and 'Legwise' in base_scope_df.columns:
            base_scope_df = base_scope_df[base_scope_df['Legwise'].astype(str).str.strip().eq(sel_leg_local)].copy()

        ven_opts = ["ALL"] + sorted(base_scope_df['VendorName'].dropna().astype(str).unique().tolist()) if 'VendorName' in base_scope_df.columns else ["ALL"]
        if st.session_state.get("ops_win_vendor") not in ven_opts:
            st.session_state["ops_win_vendor"] = "ALL"
        sel_ven_local = fc3.selectbox("Vendor:", ven_opts, key="ops_win_vendor")
        if sel_ven_local != "ALL" and 'VendorName' in base_scope_df.columns:
            base_scope_df = base_scope_df[base_scope_df['VendorName'].astype(str).eq(sel_ven_local)].copy()

        local_search = fc4.text_input("Search Vehicle, CD No, Branch:", key="ops_win_search").strip()
        if local_search:
            l_mask = base_scope_df.astype(str).apply(lambda c: c.str.contains(local_search, case=False, regex=False, na=False)).any(axis=1)
            base_scope_df = base_scope_df[l_mask].copy()

        active_remarks = selected_remarks if selected_remarks else available_remarks
        view_df = base_scope_df[base_scope_df['_OpsRemarkOutcome'].isin(active_remarks)].copy()

        # Active Filter Chips
        chips = []
        if start_str and end_str:
            chips.append(f'<span class="pbi-chip">📅 {html_module.escape(start_str)} to {html_module.escape(end_str)}</span>')
        if selected_remarks:
            rem_chip = ', '.join(selected_remarks[:2]) + (f' +{len(selected_remarks) - 2} more' if len(selected_remarks) > 2 else '')
            chips.append(f'<span class="pbi-chip">Remark: {html_module.escape(rem_chip)}</span>')
        else:
            chips.append('<span class="pbi-chip">Remark: ALL</span>')
        for lbl, val in [('Zone', sel_zone_local), ('RO', sel_ro_local), ('Route', sel_rt_local), ('Legwise', sel_leg_local), ('Vendor', sel_ven_local)]:
            if val != 'ALL':
                chips.append(f'<span class="pbi-chip">{lbl}: {html_module.escape(val)}</span>')
        if local_search:
            chips.append(f'<span class="pbi-chip">🔍 “{html_module.escape(local_search)}”</span>')
        st.markdown(
            f'<div class="pbi-chip-bar"><span class="pbi-chip-title">Filters</span>{"".join(chips)}</div>',
            unsafe_allow_html=True
        )

    # Clean Direct Page Title (No fancy words)
    if len(active_remarks) == 1:
        title_label = active_remarks[0]
        title_icon = icon_lookup.get(title_label, '📄')
    elif len(active_remarks) == len(available_remarks):
        title_label = "All Remarks"
        title_icon = "📊"
    else:
        title_label = f"{len(active_remarks)} Remarks"
        title_icon = "🎯"
    with hdr_l:
        st.markdown(f"<h2 style='margin:0'>{title_icon} {html_module.escape(title_label)}</h2>", unsafe_allow_html=True)

    # Remark-wise Gauges in exact sequence; double-click any gauge to update tables below
    win_gauge_context = {
        'start': start_str,
        'end': end_str,
        'zone': sel_zone_local,
        'ro': sel_ro_local,
        'route': sel_rt_local,
        'vendor': sel_ven_local,
        'search': local_search
    }
    render_ops_window_remark_gauges(base_scope_df, active_remarks, win_gauge_context, remark_state_key, available_remarks)

    if view_df.empty:
        st.info("No raw trips match the selected filters.")
        return

    match_cnt = len(view_df)

    # =========================================================
    # 1. ROUTE & LEG BREAKDOWN (Total Trips + Ontime Dep, Ontime Arr + Remark + Remark % (Count))
    # Sorted: Origin RO (A->Z), Route Path (A->Z), Legwise (A->Z), Remark (Z->A)
    # =========================================================
    leg_keys = [c for c in ['Origin RO', 'Route Path', 'Legwise', 'Legs'] if c in view_df.columns]
    pivot_cols = leg_keys + (['Remark'] if 'Remark' in view_df.columns else [])
    narrowed_df = view_df.copy()

    if leg_keys and not view_df.empty:
        st.markdown("### 📊 Route & Leg Breakdown")

        leg_totals = base_scope_df.groupby(leg_keys, dropna=False).agg(
            Total_Trips=('_OpsRemarkOutcome', 'size'),
            OO_Trips=('_OpsRemarkOutcome', lambda s: int((s == 'Ontime Dep, Ontime Arr').sum()))
        ).reset_index()

        pivot_df = view_df.groupby(pivot_cols, dropna=False).size().reset_index(name='_Match_Cnt')
        pivot_df = pivot_df.merge(leg_totals, on=leg_keys, how='left')
        pivot_df['Total_Trips'] = pivot_df['Total_Trips'].fillna(pivot_df['_Match_Cnt']).astype(int)
        pivot_df['OO_Trips'] = pivot_df['OO_Trips'].fillna(0).astype(int)

        pivot_df['Ontime Dep, Ontime Arr'] = [
            format_pct_cnt(oo, tot) for oo, tot in zip(pivot_df['OO_Trips'], pivot_df['Total_Trips'])
        ]
        pivot_df['Remark % (Count)'] = [
            format_pct_cnt(mc, tot) for mc, tot in zip(pivot_df['_Match_Cnt'], pivot_df['Total_Trips'])
        ]
        pivot_df = pivot_df.rename(columns={'Total_Trips': 'Total Trips'})
        final_piv_cols = leg_keys + ['Total Trips', 'Ontime Dep, Ontime Arr'] + (['Remark'] if 'Remark' in pivot_df.columns else []) + ['Remark % (Count)']
        pivot_df = _sort_ops_window_df(pivot_df[final_piv_cols])

        render_centered_html_table(pivot_df, height=480)

        drill_labels = ["Show All Matching Trips"] + [
            f"{r.get('Origin RO', '')} | {r.get('Route Path', '')} | {r.get('Legwise', '')} | {r.get('Remark', '')} ({r.get('Remark % (Count)', '')})"
            for _, r in pivot_df.iterrows()
        ]
        chosen_drill = st.selectbox("🎯 Narrow Raw Trips by Route & Leg:", drill_labels, key="ops_win_drill_select")
        if chosen_drill != "Show All Matching Trips":
            p_idx = drill_labels.index(chosen_drill) - 1
            if 0 <= p_idx < len(pivot_df):
                chosen_p = pivot_df.iloc[p_idx]
                for pc in pivot_cols:
                    narrowed_df = narrowed_df[narrowed_df[pc].fillna('').astype(str).eq(str(chosen_p[pc]))].copy()
    else:
        pivot_df = pd.DataFrame()

    # =========================================================
    # 2. DETAILED RAW TRIP RECORDS
    # Sorted: Origin RO (A->Z), Route Path (A->Z), Legwise (A->Z), Remark (Z->A)
    # =========================================================
    raw_clean = clean_dataframe_for_excel(
        narrowed_df.drop(columns=['_OpsRemarkOutcome'], errors='ignore'),
        sheet_type="ops_raw",
        preserve_order=True
    )
    excel_lead_cols = [
        'Origin RO', 'Route Path', 'Legwise', 'Legs', 'Remark',
        'MCD_StartDate', 'Scheduled Departure Time', 'Actual Departure Time',
        'Scheduled Arrival Time', 'Actual Arrival Time',
        'Scheduled Halting', 'Actual Halting',
        'VendorName', 'VehicleNo', 'MasterCDNo', 'RouteCode'
    ]
    ordered_raw_cols = [c for c in excel_lead_cols if c in raw_clean.columns] + [c for c in raw_clean.columns if c not in excel_lead_cols]
    raw_clean = raw_clean[ordered_raw_cols]
    raw_clean = _sort_ops_window_df(raw_clean)

    st.markdown(f"### 📄 Detailed Raw Trip Records ({len(raw_clean):,} rows)")
    if raw_clean.empty:
        st.info("No records match the selected filters.")
        return

    render_centered_html_table(raw_clean, height=580)

    # 2-Sheet Formatted Excel Export (Route_Leg_Breakdown + Detailed_Raw_Trips)
    excel_title = f"Operations Report · {title_label}"
    excel_bytes = build_ops_window_excel_bytes(pivot_df, raw_clean, excel_title)

    safe_name = re.sub(r'[^A-Za-z0-9_-]+', '_', title_label).strip('_') or 'Remark_Raw'
    st.download_button(
        f"📥 Download {title_label} Report (Excel)",
        data=excel_bytes,
        file_name=f"Ops_{safe_name}_Report_{get_ist_now():%d_%b_%Y}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        use_container_width=True,
        key="ops_win_download_btn"
    )

def render_vendor_perf_gauges_open_window(ven_counts, ven_total, gauge_context):
    """Render Vendor Arrival Performance gauges on main page; double-clicking opens full-width ven_raw=1 window."""
    items = [
        ('Ontime Arrival', int(ven_counts.get('Ontime Arrival', 0)), '#16a34a', '#f0fdf4', '#bbf7d0', '🟢'),
        ('Late Arrival', int(ven_counts.get('Late Arrival', 0)), '#dc2626', '#fef2f2', '#fecaca', '🔴'),
        ('In-Transit', int(ven_counts.get('In-Transit', 0)), '#f59e0b', '#fffbeb', '#fde68a', '🟡'),
    ]
    if int(ven_counts.get('Missing Schedule', 0)) > 0:
        items.append(('Missing Schedule', int(ven_counts.get('Missing Schedule', 0)), '#8b5cf6', '#f5f3ff', '#ddd6fe', '🟣'))

    track_c = '#e2e8f0' if THEME_IS_LIGHT else 'rgba(148,163,184,.22)'
    text_c = '#0f172a' if THEME_IS_LIGHT else selected_theme['text']
    muted_c = '#475569' if THEME_IS_LIGHT else selected_theme['muted']

    base_url_json = json.dumps(get_overall_issue_query_url(), ensure_ascii=True).replace('</', '<\\/')
    token = create_vendor_perf_access_token(st.session_state.get('username', ''))

    cards = []
    for label, cnt, color, light_bg, light_border, icon in items:
        pct = (cnt / ven_total * 100.0) if ven_total else 0.0
        dash = 201.06 * min(100.0, max(0.0, pct)) / 100.0
        bg = light_bg if THEME_IS_LIGHT else selected_theme['card1']
        border = light_border if THEME_IS_LIGHT else selected_theme['line']
        params = {
            'ven_raw': '1',
            'ven_auth': token,
            'ven_status': label,
            'ven_start': gauge_context.get('start', ''),
            'ven_end': gauge_context.get('end', ''),
            'ven_zone': gauge_context.get('zone', 'ALL'),
            'ven_ro': gauge_context.get('ro', 'ALL'),
            'ven_vendor': gauge_context.get('vendor', 'ALL'),
            'ven_route': gauge_context.get('route', 'ALL'),
            'ven_leg': gauge_context.get('leg', 'ALL'),
            'ven_search': gauge_context.get('search', '')
        }
        params_json = json.dumps(params, ensure_ascii=True).replace('</', '<\\/')
        cards.append(
            f'<div class="vg-card" role="button" tabindex="0" title="Double-click to open full Vendor Performance window" '
            f'data-params="{html_module.escape(params_json, quote=True)}" data-base="{html_module.escape(base_url_json, quote=True)}" '
            f'style="background:{bg};border-color:{border}">'
            f'<div class="vg-label">{icon} {html_module.escape(label)}</div>'
            f'<svg viewBox="0 0 180 108" role="img" aria-label="{pct:.1f} percent">'
            f'<path d="M 18 90 A 72 72 0 0 1 162 90" fill="none" stroke="{track_c}" stroke-width="13" stroke-linecap="round" pathLength="201.06"/>'
            f'<path d="M 18 90 A 72 72 0 0 1 162 90" fill="none" stroke="{color}" stroke-width="13" stroke-linecap="round" stroke-dasharray="{dash:.2f} 201.06" pathLength="201.06"/>'
            f'<text x="90" y="75" text-anchor="middle" font-size="27" font-weight="850" fill="{text_c}">{pct:.1f}%</text>'
            f'<text x="90" y="99" text-anchor="middle" font-size="14" font-weight="800" fill="{color}">{cnt:,} trips</text>'
            f'</svg>'
            f'<div class="vg-sub">out of <strong>{ven_total:,}</strong> trips</div>'
            f'<div class="vg-hint">Double-click for raw data ↗</div>'
            f'</div>'
        )

    cols_cnt = min(len(cards), 4)
    html_doc = (
        f'<!doctype html><html><head><meta charset="utf-8"><style>'
        f'* {{ box-sizing:border-box; }}'
        f'body {{ margin:0; padding:4px 2px; font-family:Inter,system-ui,-apple-system,Arial,sans-serif; background:transparent; color:{text_c}; user-select:none; }}'
        f'.grid {{ display:grid; grid-template-columns:repeat({cols_cnt},minmax(170px,1fr)); gap:12px; }}'
        f'.vg-card {{ border:1px solid; border-radius:15px; padding:11px 10px 9px; text-align:center; cursor:pointer; box-shadow:0 6px 18px rgba(15,23,42,.06); transition:transform .14s ease, box-shadow .14s ease, border-color .14s ease; }}'
        f'.vg-card:hover {{ transform:translateY(-3px); box-shadow:0 12px 26px rgba(15,23,42,.14); border-color:{selected_theme["blue"]} !important; }}'
        f'.vg-label {{ font-size:12.5px; font-weight:800; color:{text_c}; min-height:22px; display:flex; align-items:center; justify-content:center; }}'
        f'svg {{ display:block; width:min(100%,180px); height:auto; margin:0 auto; overflow:visible; }}'
        f'.vg-sub {{ font-size:11.5px; font-weight:600; color:{muted_c}; margin-top:2px; }}'
        f'.vg-sub strong {{ color:{text_c}; font-weight:800; }}'
        f'.vg-hint {{ font-size:10.5px; font-weight:650; color:{selected_theme["blue"]}; margin-top:3px; opacity:.82; }}'
        f'.vg-card:hover .vg-hint {{ opacity:1; text-decoration:underline; }}'
        f'@media(max-width:860px) {{ .grid {{ grid-template-columns:repeat(2,minmax(150px,1fr)); }} }}'
        f'@media(max-width:500px) {{ .grid {{ grid-template-columns:1fr; }} }}'
        f'</style></head><body><div class="grid">{"".join(cards)}</div><script>'
        f'let lastVenOpenAt = 0;'
        f'function openVenRawWindow(card) {{'
        f'  const now = Date.now();'
        f'  if (now - lastVenOpenAt < 500) return;'
        f'  lastVenOpenAt = now;'
        f'  try {{'
        f'    const base = JSON.parse(card.dataset.base) || document.referrer || window.location.href;'
        f'    const target = new URL(base);'
        f'    ["issues_raw","issues_auth","issues_ro","issues_route","issues_zone","issues_type","issues_start","issues_end","ops_raw","ops_auth","ops_outcome","ops_start","ops_end","ops_zone","ops_ro","ops_vendor","ops_route","ops_search"].forEach((k) => target.searchParams.delete(k));'
        f'    Object.entries(JSON.parse(card.dataset.params)).forEach(([key, value]) => {{'
        f'      if (value !== "" && value !== null && value !== undefined) target.searchParams.set(key, value);'
        f'      else target.searchParams.delete(key);'
        f'    }});'
        f'    window.open(target.toString(), "_blank", "noopener,noreferrer");'
        f'  }} catch (err) {{ window.alert("Could not open Vendor Performance window. Please allow pop-ups and try again."); }}'
        f'}}'
        f'document.querySelectorAll(".vg-card").forEach((card) => {{'
        f'  card.addEventListener("dblclick", (e) => {{ e.preventDefault(); openVenRawWindow(card); }});'
        f'  card.addEventListener("keydown", (e) => {{ if (e.key === "Enter") {{ e.preventDefault(); openVenRawWindow(card); }} }});'
        f'}});'
        f'</script></body></html>'
    )
    st.components.v1.html(html_doc, height=205, scrolling=False)


def render_vendor_window_gauges(base_scope_df, active_statuses, status_state_key, available_statuses):
    """Render interactive Vendor Arrival gauges inside ven_raw=1 window; double-click filters below in-place."""
    scope_total = len(base_scope_df)
    st_series = base_scope_df.get('Remark with 15 min waiver', pd.Series('', index=base_scope_df.index)).fillna('').astype(str).str.strip()
    counts = st_series.value_counts().to_dict() if not base_scope_df.empty else {}

    items = [
        ('Ontime Arrival', int(counts.get('Ontime Arrival', 0)), '#16a34a', '#f0fdf4', '#bbf7d0', '🟢'),
        ('Late Arrival', int(counts.get('Late Arrival', 0)), '#dc2626', '#fef2f2', '#fecaca', '🔴'),
        ('In-Transit', int(counts.get('In-Transit', 0)), '#f59e0b', '#fffbeb', '#fde68a', '🟡'),
    ]
    if int(counts.get('Missing Schedule', 0)) > 0:
        items.append(('Missing Schedule', int(counts.get('Missing Schedule', 0)), '#8b5cf6', '#f5f3ff', '#ddd6fe', '🟣'))

    def _pick_ven_win_gauge(chosen_lbl):
        if chosen_lbl in available_statuses:
            st.session_state[status_state_key] = [chosen_lbl]

    st.markdown("""
    <style>
    .st-key-ven_win_triggers_box {
        position: fixed !important; left: -9999px !important; top: -9999px !important;
        width: 0px !important; height: 0px !important; max-height: 0px !important;
        overflow: hidden !important; opacity: 0 !important; margin: 0 !important; padding: 0 !important;
        pointer-events: none !important;
    }
    </style>
    """, unsafe_allow_html=True)
    try:
        _ven_t_box = st.container(key="ven_win_triggers_box")
    except TypeError:
        _ven_t_box = st.container()
    with _ven_t_box:
        for idx, (lbl, _, _, _, _, _) in enumerate(items):
            st.button(
                f"__VENWIN_GPICK__{lbl}",
                key=f"ven_win_gpick_{idx}_{re.sub(r'[^A-Za-z0-9]+', '_', lbl)}",
                on_click=_pick_ven_win_gauge,
                args=(lbl,)
            )

    track_c = '#e2e8f0' if THEME_IS_LIGHT else 'rgba(148,163,184,.22)'
    text_c = '#0f172a' if THEME_IS_LIGHT else selected_theme['text']
    muted_c = '#475569' if THEME_IS_LIGHT else selected_theme['muted']

    cards = []
    for label, cnt, color, light_bg, light_border, icon in items:
        pct = (cnt / scope_total * 100.0) if scope_total else 0.0
        dash = 201.06 * min(100.0, max(0.0, pct)) / 100.0
        bg = light_bg if THEME_IS_LIGHT else selected_theme['card1']
        border = light_border if THEME_IS_LIGHT else selected_theme['line']
        is_active = label in active_statuses
        ring_css = f'box-shadow: 0 0 0 2.5px {color}, 0 8px 20px rgba(15,23,42,.10);' if is_active else 'box-shadow: 0 4px 14px rgba(15,23,42,.05);'
        cards.append(
            f'<div class="vg-card" role="button" tabindex="0" data-label="{html_module.escape(label, quote=True)}" '
            f'title="Double-click to filter {html_module.escape(label)} below" '
            f'style="background:{bg};border-color:{border};{ring_css}">'
            f'<div class="vg-label">{icon} {html_module.escape(label)}</div>'
            f'<svg viewBox="0 0 180 108" role="img" aria-label="{pct:.1f} percent">'
            f'<path d="M 18 90 A 72 72 0 0 1 162 90" fill="none" stroke="{track_c}" stroke-width="13" stroke-linecap="round" pathLength="201.06"/>'
            f'<path d="M 18 90 A 72 72 0 0 1 162 90" fill="none" stroke="{color}" stroke-width="13" stroke-linecap="round" stroke-dasharray="{dash:.2f} 201.06" pathLength="201.06"/>'
            f'<text x="90" y="75" text-anchor="middle" font-size="27" font-weight="850" fill="{text_c}">{pct:.1f}%</text>'
            f'<text x="90" y="99" text-anchor="middle" font-size="14" font-weight="800" fill="{color}">{cnt:,} trips</text>'
            f'</svg>'
            f'<div class="vg-sub">out of <strong>{scope_total:,}</strong> trips</div>'
            f'<div class="vg-hint">Double-click to filter below</div>'
            f'</div>'
        )

    cols_cnt = min(len(cards), 4)
    html_doc = (
        f'<!doctype html><html><head><meta charset="utf-8"><style>'
        f'* {{ box-sizing:border-box; }}'
        f'body {{ margin:0; padding:3px 2px; font-family:Inter,system-ui,-apple-system,Arial,sans-serif; background:transparent; color:{text_c}; user-select:none; }}'
        f'.grid {{ display:grid; grid-template-columns:repeat({cols_cnt},minmax(170px,1fr)); gap:12px; }}'
        f'.vg-card {{ border:1px solid; border-radius:15px; padding:10px 10px 8px; text-align:center; cursor:pointer; transition:transform .14s ease, box-shadow .14s ease; }}'
        f'.vg-card:hover {{ transform:translateY(-2px); box-shadow:0 10px 22px rgba(15,23,42,.12) !important; }}'
        f'.vg-label {{ font-size:12.5px; font-weight:800; color:{text_c}; min-height:22px; display:flex; align-items:center; justify-content:center; }}'
        f'svg {{ display:block; width:min(100%,180px); height:auto; margin:0 auto; overflow:visible; }}'
        f'.vg-sub {{ font-size:11.5px; font-weight:600; color:{muted_c}; margin-top:2px; }}'
        f'.vg-sub strong {{ color:{text_c}; font-weight:800; }}'
        f'.vg-hint {{ font-size:10.5px; font-weight:650; color:{selected_theme["blue"]}; margin-top:3px; opacity:.82; }}'
        f'.vg-card:hover .vg-hint {{ opacity:1; text-decoration:underline; }}'
        f'@media(max-width:860px) {{ .grid {{ grid-template-columns:repeat(2,minmax(150px,1fr)); }} }}'
        f'@media(max-width:500px) {{ .grid {{ grid-template-columns:1fr; }} }}'
        f'</style></head><body><div class="grid">{"".join(cards)}</div><script>'
        f'function filterVenBelow(card) {{'
        f'  const targetLabel = "__VENWIN_GPICK__" + card.dataset.label;'
        f'  try {{'
        f'    const btns = window.parent.document.querySelectorAll("button");'
        f'    for (const b of btns) {{'
        f'      if ((b.innerText || b.textContent || "").trim() === targetLabel) {{ b.click(); return; }}'
        f'    }}'
        f'  }} catch (e) {{}}'
        f'}}'
        f'document.querySelectorAll(".vg-card").forEach((card) => {{'
        f'  card.addEventListener("dblclick", (e) => {{ e.preventDefault(); filterVenBelow(card); }});'
        f'  card.addEventListener("keydown", (e) => {{ if (e.key === "Enter") {{ e.preventDefault(); filterVenBelow(card); }} }});'
        f'}});'
        f'</script></body></html>'
    )
    st.components.v1.html(html_doc, height=205, scrolling=False)


def render_vendor_perf_raw_window(data, query):
    """Full-width new-window view for Vendor Performance (RO-wise / Zone-wise / Vendor-wise / Route & Leg-wise)."""
    status_label = query.get('ven_status', 'Ontime Arrival') or 'Ontime Arrival'
    icon_map = {
        'Ontime Arrival': '🟢', 'Late Arrival': '🔴',
        'In-Transit': '🟡', 'Missing Schedule': '🟣'
    }

    if "ven_win_hide_sidebar" not in st.session_state:
        st.session_state["ven_win_hide_sidebar"] = True

    def _toggle_ven_win_sidebar():
        st.session_state["ven_win_hide_sidebar"] = not st.session_state.get("ven_win_hide_sidebar", True)

    if st.session_state.get("ven_win_hide_sidebar", True):
        st.markdown("""
        <style>
        [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] { display: none !important; }
        [data-testid="stMainBlockContainer"], .block-container {
            max-width: 99% !important;
            padding-left: 1.4rem !important;
            padding-right: 1.4rem !important;
            padding-top: 1.1rem !important;
        }
        </style>
        """, unsafe_allow_html=True)

    df_source = data.get('Vendor_Perf_Raw', pd.DataFrame()).copy()
    if df_source.empty:
        st.warning("No processed Vendor Performance data available.")
        return

    if not st.session_state.get('all_vendors', True):
        df_source = filter_df_by_user_vendors(df_source, 'VendorName')

    scoped = df_source.copy()
    start_str = query.get('ven_start', '').strip()
    end_str = query.get('ven_end', '').strip()
    if start_str and end_str and 'Date' in scoped.columns:
        try:
            sd = datetime.date.fromisoformat(start_str)
            ed = datetime.date.fromisoformat(end_str)
            if sd > ed:
                sd, ed = ed, sd
            parsed_d = pd.to_datetime(scoped['Date'], dayfirst=True, errors='coerce')
            scoped = scoped[(parsed_d.dt.date >= sd) & (parsed_d.dt.date <= ed)].copy()
        except Exception:
            pass

    init_sig = (
        status_label, start_str, end_str,
        query.get('ven_zone', 'ALL'), query.get('ven_ro', 'ALL'),
        query.get('ven_vendor', 'ALL'), query.get('ven_route', 'ALL'), query.get('ven_leg', 'ALL')
    )
    if st.session_state.get("_ven_win_seed_sig") != init_sig:
        st.session_state["_ven_win_seed_sig"] = init_sig
        st.session_state["ven_win_zone"] = query.get('ven_zone', 'ALL').strip() or "ALL"
        st.session_state["ven_win_ro"] = query.get('ven_ro', 'ALL').strip() or "ALL"
        st.session_state["ven_win_vendor"] = query.get('ven_vendor', 'ALL').strip() or "ALL"
        st.session_state["ven_win_route"] = query.get('ven_route', 'ALL').strip() or "ALL"
        st.session_state["ven_win_leg"] = query.get('ven_leg', 'ALL').strip() or "ALL"
        st.session_state["ven_win_search"] = query.get('ven_search', '').strip()

    available_statuses = ['Ontime Arrival', 'Late Arrival', 'In-Transit', 'Missing Schedule']
    default_statuses = [status_label] if status_label in available_statuses else available_statuses
    status_state_key = f"ven_win_status_{re.sub(r'[^A-Za-z0-9]+', '_', status_label)}"
    if status_state_key not in st.session_state:
        st.session_state[status_state_key] = default_statuses

    def _reset_ven_win_filters():
        st.session_state[status_state_key] = default_statuses
        st.session_state["ven_win_zone"] = "ALL"
        st.session_state["ven_win_ro"] = "ALL"
        st.session_state["ven_win_vendor"] = "ALL"
        st.session_state["ven_win_route"] = "ALL"
        st.session_state["ven_win_leg"] = "ALL"
        st.session_state["ven_win_search"] = ""

    hdr_l, hdr_r = st.columns([5.2, 1.1])
    with hdr_r:
        toggle_lbl = "☰ Show Left Panel" if st.session_state.get("ven_win_hide_sidebar", True) else "✕ Hide Left Panel"
        st.button(toggle_lbl, key="ven_win_sidebar_toggle", use_container_width=True, on_click=_toggle_ven_win_sidebar)

    with st.container():
        st.markdown('<div class="pbi-sticky-anchor"></div>', unsafe_allow_html=True)
        r1_st, r1_btn = st.columns([5.3, 0.7])
        selected_statuses = r1_st.multiselect(
            "Filter Arrival Status:",
            options=available_statuses,
            key=status_state_key,
            placeholder="All Statuses (select one or more)..."
        )
        r1_btn.markdown("<div style='height:1.72rem'></div>", unsafe_allow_html=True)
        r1_btn.button("↺ Reset", key="ven_win_reset_btn", use_container_width=True, on_click=_reset_ven_win_filters)

        base_scope_df = scoped.copy()
        fc_z, fc1, fc2, fc3, fc_l, fc4 = st.columns([0.85, 0.9, 1.2, 1.25, 0.85, 1.25])

        zone_opts = ["ALL"] + sorted(
            z for z in base_scope_df['Zone'].dropna().astype(str).str.strip().unique().tolist()
            if z and z.upper() not in ("NAN", "NONE")
        ) if 'Zone' in base_scope_df.columns else ["ALL"]
        if st.session_state.get("ven_win_zone") not in zone_opts:
            st.session_state["ven_win_zone"] = "ALL"
        sel_zone_local = fc_z.selectbox("Zone:", zone_opts, key="ven_win_zone")
        if sel_zone_local != "ALL" and 'Zone' in base_scope_df.columns:
            base_scope_df = base_scope_df[base_scope_df['Zone'].fillna('').astype(str).str.strip().eq(sel_zone_local)].copy()

        ro_opts = ["ALL"] + sorted(base_scope_df['Origin RO'].dropna().astype(str).unique().tolist()) if 'Origin RO' in base_scope_df.columns else ["ALL"]
        if st.session_state.get("ven_win_ro") not in ro_opts:
            st.session_state["ven_win_ro"] = "ALL"
        sel_ro_local = fc1.selectbox("RO:", ro_opts, key="ven_win_ro")
        if sel_ro_local != "ALL" and 'Origin RO' in base_scope_df.columns:
            base_scope_df = base_scope_df[base_scope_df['Origin RO'].astype(str).eq(sel_ro_local)].copy()

        ven_opts = ["ALL"] + sorted(base_scope_df['VendorName'].dropna().astype(str).unique().tolist()) if 'VendorName' in base_scope_df.columns else ["ALL"]
        if st.session_state.get("ven_win_vendor") not in ven_opts:
            st.session_state["ven_win_vendor"] = "ALL"
        sel_ven_local = fc2.selectbox("Vendor:", ven_opts, key="ven_win_vendor")
        if sel_ven_local != "ALL" and 'VendorName' in base_scope_df.columns:
            base_scope_df = base_scope_df[base_scope_df['VendorName'].astype(str).eq(sel_ven_local)].copy()

        rt_opts = ["ALL"] + sorted(base_scope_df['Route Path'].dropna().astype(str).unique().tolist()) if 'Route Path' in base_scope_df.columns else ["ALL"]
        if st.session_state.get("ven_win_route") not in rt_opts:
            st.session_state["ven_win_route"] = "ALL"
        sel_rt_local = fc3.selectbox("Route:", rt_opts, key="ven_win_route")
        if sel_rt_local != "ALL" and 'Route Path' in base_scope_df.columns:
            base_scope_df = base_scope_df[base_scope_df['Route Path'].astype(str).eq(sel_rt_local)].copy()

        v_leg_vals = [v for v in base_scope_df['Legwise'].dropna().astype(str).str.strip().unique().tolist() if v] if 'Legwise' in base_scope_df.columns else []
        v_leg_opts = ["ALL"] + sorted(v_leg_vals, key=lambda x: (int(re.search(r'(\d+)', x).group(1)) if re.search(r'(\d+)', x) else 999, x))
        if st.session_state.get("ven_win_leg") not in v_leg_opts:
            st.session_state["ven_win_leg"] = "ALL"
        sel_leg_local = fc_l.selectbox("Legwise:", v_leg_opts, key="ven_win_leg")
        if sel_leg_local != "ALL" and 'Legwise' in base_scope_df.columns:
            base_scope_df = base_scope_df[base_scope_df['Legwise'].astype(str).str.strip().eq(sel_leg_local)].copy()

        local_search = fc4.text_input("Search Vehicle, CD No, Branch:", key="ven_win_search").strip()
        if local_search:
            l_mask = base_scope_df.astype(str).apply(lambda c: c.str.contains(local_search, case=False, regex=False, na=False)).any(axis=1)
            base_scope_df = base_scope_df[l_mask].copy()

        active_statuses = selected_statuses if selected_statuses else available_statuses
        st_col = 'Remark with 15 min waiver'
        view_df = base_scope_df[base_scope_df[st_col].fillna('').astype(str).str.strip().isin(active_statuses)].copy() if st_col in base_scope_df.columns else base_scope_df.copy()

        chips = []
        if start_str and end_str:
            chips.append(f'<span class="pbi-chip">📅 {html_module.escape(start_str)} to {html_module.escape(end_str)}</span>')
        if selected_statuses:
            chips.append(f'<span class="pbi-chip">Status: {html_module.escape(", ".join(selected_statuses))}</span>')
        else:
            chips.append('<span class="pbi-chip">Status: ALL</span>')
        for lbl, val in [('Zone', sel_zone_local), ('RO', sel_ro_local), ('Vendor', sel_ven_local), ('Route', sel_rt_local), ('Legwise', sel_leg_local)]:
            if val != 'ALL':
                chips.append(f'<span class="pbi-chip">{lbl}: {html_module.escape(val)}</span>')
        if local_search:
            chips.append(f'<span class="pbi-chip">🔍 “{html_module.escape(local_search)}”</span>')
        st.markdown(
            f'<div class="pbi-chip-bar"><span class="pbi-chip-title">Filters</span>{"".join(chips)}</div>',
            unsafe_allow_html=True
        )

    if len(active_statuses) == 1:
        title_label = active_statuses[0]
        title_icon = icon_map.get(title_label, '🚚')
    else:
        title_label = "Vendor Performance Breakdown"
        title_icon = "🚚"
    with hdr_l:
        st.markdown(f"<h2 style='margin:0'>{title_icon} {html_module.escape(title_label)}</h2>", unsafe_allow_html=True)

    render_vendor_window_gauges(base_scope_df, active_statuses, status_state_key, available_statuses)

    if view_df.empty:
        st.info("No vendor trips match the selected filters.")
        return

    st.markdown("### 📊 Performance Breakdown")
    view_mode = st.radio(
        "Group By:",
        ["Vendor-wise", "RO-wise", "Zone-wise", "Route & Leg-wise"],
        horizontal=True,
        key="ven_win_group_mode"
    )

    def _agg_vendor_group(df_g, grp_cols, extra_aggs=None):
        g_cols = [c for c in grp_cols if c in df_g.columns]
        if not g_cols:
            return pd.DataFrame()
        tmp = df_g.copy()
        s_txt = tmp[st_col].fillna('').astype(str).str.strip()
        tmp['_ot'] = (s_txt == 'Ontime Arrival').astype(int)
        tmp['_lt'] = (s_txt == 'Late Arrival').astype(int)
        tmp['_it'] = (s_txt == 'In-Transit').astype(int)
        tmp['_ms'] = (s_txt == 'Missing Schedule').astype(int)
        agg_spec = {
            'Total Trips': (st_col, 'size'),
            '_ot': ('_ot', 'sum'),
            '_lt': ('_lt', 'sum'),
            '_it': ('_it', 'sum'),
            '_ms': ('_ms', 'sum'),
        }
        if extra_aggs:
            agg_spec.update(extra_aggs)
        res = tmp.groupby(g_cols, dropna=False).agg(**agg_spec).reset_index()
        res['Ontime Arrival'] = [format_pct_cnt(o, t) for o, t in zip(res['_ot'], res['Total Trips'])]
        res['Late Arrival'] = [format_pct_cnt(l, t) for l, t in zip(res['_lt'], res['Total Trips'])]
        res['In-Transit'] = [format_pct_cnt(i, t) for i, t in zip(res['_it'], res['Total Trips'])]
        if res['_ms'].sum() > 0:
            res['Missing Schedule'] = [format_pct_cnt(m, t) for m, t in zip(res['_ms'], res['Total Trips'])]
        res['_ot_pct'] = np.where(res['Total Trips'] > 0, res['_ot'] / res['Total Trips'] * 100.0, 0.0)
        res['Status'] = np.where(res['_ot_pct'] >= 85, '🟢 Strong', np.where(res['_ot_pct'] >= 70, '🟡 Watch', '🔴 Action Needed'))
        res = res.sort_values(by=['Total Trips', '_ot_pct'], ascending=[False, True])
        drop_c = ['_ot', '_lt', '_it', '_ms', '_ot_pct']
        return res.drop(columns=drop_c, errors='ignore').reset_index(drop=True)

    if view_mode == "Vendor-wise":
        breakdown_df = _agg_vendor_group(
            base_scope_df, ['VendorName'],
            {'ROs': ('Origin RO', 'nunique'), 'Routes': ('Route Path', 'nunique')}
        ).rename(columns={'VendorName': 'Vendor'})
        lead = ['Vendor', 'ROs', 'Routes', 'Total Trips', 'Ontime Arrival', 'Late Arrival', 'In-Transit', 'Missing Schedule', 'Status']
        breakdown_df = breakdown_df[[c for c in lead if c in breakdown_df.columns]]
    elif view_mode == "RO-wise":
        breakdown_df = _agg_vendor_group(
            base_scope_df, ['Zone', 'Origin RO'],
            {'Vendors': ('VendorName', 'nunique'), 'Routes': ('Route Path', 'nunique')}
        )
        lead = ['Zone', 'Origin RO', 'Vendors', 'Routes', 'Total Trips', 'Ontime Arrival', 'Late Arrival', 'In-Transit', 'Missing Schedule', 'Status']
        breakdown_df = breakdown_df[[c for c in lead if c in breakdown_df.columns]]
    elif view_mode == "Zone-wise":
        breakdown_df = _agg_vendor_group(
            base_scope_df, ['Zone'],
            {'ROs': ('Origin RO', 'nunique'), 'Vendors': ('VendorName', 'nunique')}
        )
        lead = ['Zone', 'ROs', 'Vendors', 'Total Trips', 'Ontime Arrival', 'Late Arrival', 'In-Transit', 'Missing Schedule', 'Status']
        breakdown_df = breakdown_df[[c for c in lead if c in breakdown_df.columns]]
    else:
        breakdown_df = _agg_vendor_group(
            base_scope_df, ['Origin RO', 'Route Path', 'Legwise', 'Legs', 'VendorName']
        ).rename(columns={'VendorName': 'Vendor'})
        lead = ['Origin RO', 'Route Path', 'Legwise', 'Legs', 'Vendor', 'Total Trips', 'Ontime Arrival', 'Late Arrival', 'In-Transit', 'Missing Schedule', 'Status']
        breakdown_df = breakdown_df[[c for c in lead if c in breakdown_df.columns]]

    render_centered_html_table(breakdown_df, height=500)

    # 7-Day & Overall Vendor Comparison (Inside Double-Click Window)
    st.markdown("---")
    st.markdown("### 📅 7-Day & Overall Vendor Comparison")
    comp_base_df = df_source.copy()
    if sel_zone_local != "ALL" and 'Zone' in comp_base_df.columns:
        comp_base_df = comp_base_df[comp_base_df['Zone'].fillna('').astype(str).str.strip().eq(sel_zone_local)]
    if sel_ro_local != "ALL" and 'Origin RO' in comp_base_df.columns:
        comp_base_df = comp_base_df[comp_base_df['Origin RO'].astype(str).eq(sel_ro_local)]
    if sel_ven_local != "ALL" and 'VendorName' in comp_base_df.columns:
        comp_base_df = comp_base_df[comp_base_df['VendorName'].astype(str).eq(sel_ven_local)]
    if sel_rt_local != "ALL" and 'Route Path' in comp_base_df.columns:
        comp_base_df = comp_base_df[comp_base_df['Route Path'].astype(str).eq(sel_rt_local)]
    if sel_leg_local != "ALL" and 'Legwise' in comp_base_df.columns:
        comp_base_df = comp_base_df[comp_base_df['Legwise'].astype(str).str.strip().eq(sel_leg_local)]

    c_date_col = get_col(comp_base_df, ['Date'])
    c_dates = pd.to_datetime(comp_base_df[c_date_col], dayfirst=True, errors='coerce').dt.date if c_date_col else pd.Series([None] * len(comp_base_df), index=comp_base_df.index)
    valid_c_dates = c_dates.dropna()
    today_c = valid_c_dates.max() if not valid_c_dates.empty else get_ist_now().date()
    curr_7_s = today_c - datetime.timedelta(days=6)
    prev_7_s = today_c - datetime.timedelta(days=13)
    prev_7_e = today_c - datetime.timedelta(days=7)

    st.caption(
        f"**Previous 7 Days:** {prev_7_s:%d %b %Y} – {prev_7_e:%d %b %Y}  ·  "
        f"**Current 7 Days:** {curr_7_s:%d %b %Y} – {today_c:%d %b %Y}  ·  "
        f"**Overall:** All available dates"
    )

    comp_vendors_w = sorted(comp_base_df.get('VendorName', pd.Series(dtype=str)).dropna().astype(str).unique().tolist())
    wc1, wc2 = st.columns([2.2, 1.4])
    comp_scope_w = wc1.selectbox(
        "Comparison Scope (All Vendors or Individual Vendor Route/Leg Breakdown):",
        ["ALL VENDORS (Summary)"] + comp_vendors_w,
        key="ven_win_comp_scope"
    )
    comp_sort_w = wc2.selectbox(
        "Sort By:",
        ["Worst Curr 7D On-Time First", "Highest Curr 7D Trips", "Biggest Drop First", "Best Improvement First"],
        key="ven_win_comp_sort"
    )

    if st_col in comp_base_df.columns and not comp_base_df.empty:
        cw = comp_base_df.copy()
        cw['_dt'] = c_dates
        cw['_is_prev'] = (cw['_dt'] >= prev_7_s) & (cw['_dt'] <= prev_7_e)
        cw['_is_curr'] = (cw['_dt'] >= curr_7_s) & (cw['_dt'] <= today_c)
        c_st = cw[st_col].fillna('').astype(str).str.strip()
        cw['_ot'] = (c_st == 'Ontime Arrival').astype(int)
        cw['_lt'] = (c_st == 'Late Arrival').astype(int)

        if comp_scope_w == "ALL VENDORS (Summary)":
            c_grp_cols = ['VendorName']
        else:
            cw = cw[cw['VendorName'].astype(str).eq(comp_scope_w)].copy()
            c_grp_cols = [c for c in ['Origin RO', 'Route Path', 'Legwise', 'Legs'] if c in cw.columns]

        c_rows = []
        for keys, grp in cw.groupby(c_grp_cols, dropna=False):
            if not isinstance(keys, tuple):
                keys = (keys,)
            rd = dict(zip(c_grp_cols, keys))
            if 'VendorName' in rd:
                rd['Vendor'] = rd.pop('VendorName')
            pg, cg = grp[grp['_is_prev']], grp[grp['_is_curr']]
            pt, po = len(pg), int(pg['_ot'].sum())
            ct, co, cl = len(cg), int(cg['_ot'].sum()), int(cg['_lt'].sum())
            at, ao, al = len(grp), int(grp['_ot'].sum()), int(grp['_lt'].sum())
            pp = (po / pt * 100.0) if pt else None
            cp = (co / ct * 100.0) if ct else None
            ap = (ao / at * 100.0) if at else 0.0
            if pp is not None and cp is not None:
                diff = cp - pp
                tr_s = f"▲ +{diff:.1f}%" if diff > 0.05 else (f"▼ {diff:.1f}%" if diff < -0.05 else "━ 0.0%")
            elif cp is not None and pp is None:
                diff, tr_s = 0.0, "New"
            else:
                diff, tr_s = 0.0, "—"
            ref_p = cp if cp is not None else ap
            st_tag = "🟢 Strong" if ref_p >= 85 else ("🟡 Watch" if ref_p >= 70 else "🔴 Action Needed")
            rd.update({
                'Prev 7D Trips': pt,
                'Prev 7D On-Time': format_pct_cnt(po, pt) if pt else "—",
                'Curr 7D Trips': ct,
                'Curr 7D On-Time': format_pct_cnt(co, ct) if ct else "—",
                'Curr 7D Late': format_pct_cnt(cl, ct) if ct else "—",
                '7D Trend': tr_s,
                'Overall Trips': at,
                'Overall On-Time': format_pct_cnt(ao, at),
                'Overall Late': format_pct_cnt(al, at),
                'Status': st_tag,
                '_sc': cp if cp is not None else 999.0,
                '_sd': diff
            })
            c_rows.append(rd)
        comp_df_w = pd.DataFrame(c_rows)
        if not comp_df_w.empty:
            if comp_sort_w == "Worst Curr 7D On-Time First":
                comp_df_w = comp_df_w.sort_values(by=['_sc', 'Curr 7D Trips'], ascending=[True, False])
            elif comp_sort_w == "Highest Curr 7D Trips":
                comp_df_w = comp_df_w.sort_values(by=['Curr 7D Trips', 'Overall Trips'], ascending=[False, False])
            elif comp_sort_w == "Biggest Drop First":
                comp_df_w = comp_df_w.sort_values(by=['_sd', 'Curr 7D Trips'], ascending=[True, False])
            else:
                comp_df_w = comp_df_w.sort_values(by=['_sd', 'Curr 7D Trips'], ascending=[False, False])
            comp_disp_w = comp_df_w.drop(columns=['_sc', '_sd'], errors='ignore').reset_index(drop=True)
            render_centered_html_table(comp_disp_w, height=480)

    raw_clean = clean_dataframe_for_excel(view_df, sheet_type="ven_raw", preserve_order=False)
    st.markdown(f"### 📄 Detailed Raw Trip Records ({len(raw_clean):,} rows)")
    render_centered_html_table(raw_clean, height=580)

    ven_win_buf = io.BytesIO()
    with pd.ExcelWriter(ven_win_buf, engine='xlsxwriter') as writer:
        write_styled_sheet_to_excel(writer, breakdown_df, f'{view_mode[:20]}_Summary', sheet_type='generic', preserve_order=True)
        write_styled_sheet_to_excel(writer, raw_clean, 'Detailed_Raw_Trips', sheet_type='ven_raw')
    safe_v_title = re.sub(r'[^A-Za-z0-9_-]+', '_', title_label).strip('_') or 'Vendor_Perf'
    st.download_button(
        f"📥 Download {title_label} ({view_mode}) Report (Excel)",
        data=ven_win_buf.getvalue(),
        file_name=f"Vendor_{safe_v_title}_{get_ist_now():%d_%b_%Y}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        use_container_width=True,
        key="ven_win_download_btn"
    )

# -------------------------------------------------------------
# A. DAILY STANDUP (Operations Summary)
# -------------------------------------------------------------
if choice == "🧭 Scheduled Route Master":
    render_scheduled_route_master(data)
elif choice == "⚠️ Overall Issues":
    render_overall_issues(data)
elif choice == "📊 Operations Summary":
    if ops_remark_raw_view:
        render_ops_remark_raw_window(data, ops_remark_query)
        st.stop()
    st.markdown("<h2>Operations Exception Summary</h2>", unsafe_allow_html=True)
    
    if 'Legwise_Route_Summary' in data and 'Legwise_Processed_Data' in data:
        df_raw_leg_source = data['Legwise_Processed_Data']
        if '_OpsRemarkOutcome' not in df_raw_leg_source.columns:
            # This frame is held in the page cache, so the buckets survive RO selector reruns.
            df_raw_leg_source['_OpsRemarkOutcome'] = ops_remark_outcome_series(df_raw_leg_source)
        df_raw_leg_full = df_raw_leg_source.copy()
        if not st.session_state.get('all_vendors', True):
            df_raw_leg_full = filter_df_by_user_vendors(df_raw_leg_full, 'VendorName')
            
        df_raw_leg, ops_filters = render_unified_filter_bar(
            df_raw_leg_full,
            key_prefix="ops_main",
            date_col="MCD_StartDate",
            zone_col="Zone" if "Zone" in df_raw_leg_full.columns else None,
            ro_col="Origin RO" if "Origin RO" in df_raw_leg_full.columns else None,
            vendor_col="VendorName" if "VendorName" in df_raw_leg_full.columns else None,
            route_col="Route Path" if "Route Path" in df_raw_leg_full.columns else None,
            leg_col="Legwise" if "Legwise" in df_raw_leg_full.columns else None,
            search_placeholder="Search Route, Leg, Vehicle..."
        )
        is_date_filtered = ops_filters["is_date_filtered"]
        dur_str_ops = ops_filters["dur_label"]
        selected_zone = ops_filters["zone"]
        selected_ro = ops_filters["ro"]
        search_q = ops_filters["search"]

        any_ops_filter = (
            is_date_filtered
            or not st.session_state.get('all_vendors', True)
            or any(ops_filters[k] != "ALL" for k in ("zone", "ro", "vendor", "route", "leg"))
            or bool(search_q)
        )
        df_leg_sum = build_ops_summary_from_raw(df_raw_leg) if any_ops_filter else data['Legwise_Route_Summary'].copy()

        if df_leg_sum.empty or df_raw_leg.empty:
            st.info("No operation trips match the selected filters.")
            st.stop()

        # Classify every filtered trip into one mutually exclusive Remark outcome.
        raw_status = df_raw_leg.copy()
        if 'E2E_Pair' not in raw_status.columns and 'Route Path' in raw_status.columns:
            raw_status['E2E_Pair'] = raw_status['Route Path'].apply(get_route_pair)
        if 'Origin' not in raw_status.columns and 'Route Path' in raw_status.columns:
            raw_status[['Origin', 'Destination']] = raw_status['Route Path'].apply(lambda route: pd.Series(extract_orig_dest(route)))
        if 'Leg_Num' not in raw_status.columns and 'Legwise' in raw_status.columns:
            raw_status['Leg_Num'] = extract_leg_num_val(raw_status['Legwise'])
        if 'Zone' not in raw_status.columns:
            raw_status['Zone'] = 'UNKNOWN ZONE'
        if 'LH Type' not in raw_status.columns:
            raw_status['LH Type'] = 'National LH'
        status_group_keys = [
            key for key in ['Zone', 'LH Type', 'E2E_Pair', 'Origin RO', 'Route Path', 'Origin', 'Destination', 'Leg_Num', 'Legwise', 'Legs']
            if key in raw_status.columns and key in df_leg_sum.columns
        ]
        if status_group_keys:
            if '_OpsRemarkOutcome' in raw_status.columns:
                raw_status['_RemarkOutcome'] = raw_status['_OpsRemarkOutcome']
            else:
                raw_status['_RemarkOutcome'] = ops_remark_outcome_series(raw_status)
            status_counts = raw_status.groupby(
                status_group_keys + ['_RemarkOutcome'], dropna=False, sort=False
            ).size().unstack('_RemarkOutcome', fill_value=0)
            status_counts = status_counts.reindex(
                columns=[label for label, _, _ in OPS_REMARK_OUTCOME_LABELS], fill_value=0
            )
            status_counts.columns = [f'{label} Trips' for label in status_counts.columns]
            status_counts = status_counts.reset_index()
            df_leg_sum = df_leg_sum.merge(status_counts, on=status_group_keys, how='left')
            for status_name, _, _ in OPS_REMARK_OUTCOME_LABELS:
                count_col = f'{status_name} Trips'
                if count_col not in df_leg_sum.columns:
                    df_leg_sum[count_col] = 0
                df_leg_sum[count_col] = pd.to_numeric(df_leg_sum[count_col], errors='coerce').fillna(0).astype(int)
                df_leg_sum[f'{status_name} %'] = [
                    format_pct_cnt(count, total)
                    for count, total in zip(df_leg_sum[count_col], pd.to_numeric(df_leg_sum['Total_Trips'], errors='coerce').fillna(0))
                ]

        # Remark-wise gauges and route rates follow the current filter scope.
        ops_outcome_counts, ops_total_trips, ops_outcome_labels = summarize_ops_remark_outcomes(raw_status)

        st.markdown("### Remark-wise Trip Outcome")
        st.caption("🟢 Ontime Dep, Ontime Arr · 🌸 Ontime Dep, Late Arr · 🔴 Late Dep, Late Arr · 🟣 Late Dep, Ontime Arr · 🟡 Late Dep, In-Transit · 🟡 Ontime Dep, In-Transit · 🟡 Missing Schedule · 🔴 No Departure · 🟡 In-Transit · ⚪ Other. Each trip is counted once from its Remark; double-click any gauge to open its raw trip data in a new window.")
        st.caption(f"{ops_total_trips:,} trips · {len(df_leg_sum):,} route legs")

        _ops_sd_val = st.session_state.get("ops_main_sd")
        _ops_ed_val = st.session_state.get("ops_main_ed")
        ops_gauge_context = {
            "start": _ops_sd_val.isoformat() if hasattr(_ops_sd_val, "isoformat") else "",
            "end": _ops_ed_val.isoformat() if hasattr(_ops_ed_val, "isoformat") else "",
            "zone": ops_filters.get("zone", "ALL"),
            "ro": ops_filters.get("ro", "ALL"),
            "vendor": ops_filters.get("vendor", "ALL"),
            "route": ops_filters.get("route", "ALL"),
            "leg": ops_filters.get("leg", "ALL"),
            "search": ops_filters.get("search", "")
        }
        render_ops_remark_gauges(ops_outcome_counts, ops_total_trips, ops_outcome_labels, ops_gauge_context)

        # Clean, Logical Operations Route & Leg Summary Table (Matching Vendor Performance Style)
        st.markdown("---")
        st.markdown("### 📋 Route & Leg Operations Summary")

        ops_leg_keys = [c for c in ['Origin RO', 'Route Path', 'Legwise', 'Legs'] if c in raw_status.columns]
        if ops_leg_keys:
            ops_tbl = raw_status.copy()
            ops_out_s = ops_tbl['_OpsRemarkOutcome'].fillna('Other').astype(str)
            primary_outcomes = [
                'Ontime Dep, Ontime Arr',
                'Ontime Dep, Late Arr',
                'Late Dep, Late Arr',
                'Late Dep, Ontime Arr'
            ]
            extra_outcomes = [
                lbl for lbl, _, _ in OPS_REMARK_OUTCOME_LABELS
                if lbl not in primary_outcomes and int(ops_outcome_counts.get(lbl, 0)) > 0
            ]
            shown_outcomes = primary_outcomes + extra_outcomes

            ops_piv = ops_tbl.groupby(ops_leg_keys + ['_OpsRemarkOutcome'], dropna=False).size().unstack('_OpsRemarkOutcome', fill_value=0)
            ops_piv = ops_piv.reindex(columns=shown_outcomes, fill_value=0)
            ops_tot = ops_tbl.groupby(ops_leg_keys, dropna=False).size().rename('Total Trips')
            ops_summary_df = ops_tot.to_frame().join(ops_piv).reset_index()

            oo_cnts = ops_summary_df['Ontime Dep, Ontime Arr'].astype(int) if 'Ontime Dep, Ontime Arr' in ops_summary_df.columns else pd.Series(0, index=ops_summary_df.index)
            tot_cnts = ops_summary_df['Total Trips'].astype(int)
            oo_pct_num = np.where(tot_cnts > 0, oo_cnts / tot_cnts * 100.0, 0.0)

            for lbl in shown_outcomes:
                ops_summary_df[lbl] = [format_pct_cnt(c, t) for c, t in zip(ops_summary_df[lbl], tot_cnts)]

            ops_summary_df['Status'] = np.where(oo_pct_num >= 85, '🟢 Strong', np.where(oo_pct_num >= 70, '🟡 Watch', '🔴 Action Needed'))
            ops_summary_df['_leg_n'] = extract_leg_num_val(ops_summary_df['Legwise']) if 'Legwise' in ops_summary_df.columns else 999
            ops_summary_df = ops_summary_df.sort_values(
                by=[c for c in ['Origin RO', 'Route Path', '_leg_n'] if c in ops_summary_df.columns],
                ascending=True
            ).drop(columns=['_leg_n'], errors='ignore').reset_index(drop=True)

            render_centered_html_table(ops_summary_df, height=520)

            # Clean 1-line Raw Trip Inspector
            ops_drill_opts = ["Select a Route & Leg to inspect raw trips..."] + [
                f"{r.get('Origin RO', '')} | {r.get('Route Path', '')} | {r.get('Legwise', '')} ({r.get('Total Trips', 0)} trips)"
                for _, r in ops_summary_df.iterrows()
            ]
            chosen_ops_drill = st.selectbox("🔎 Inspect Raw Trips:", ops_drill_opts, key="ops_main_raw_inspector")
            if chosen_ops_drill != ops_drill_opts[0]:
                o_idx = ops_drill_opts.index(chosen_ops_drill) - 1
                if 0 <= o_idx < len(ops_summary_df):
                    sel_or = ops_summary_df.iloc[o_idx]
                    o_raw = raw_status[
                        raw_status['Origin RO'].astype(str).eq(str(sel_or['Origin RO']))
                        & raw_status['Route Path'].astype(str).eq(str(sel_or['Route Path']))
                        & raw_status['Legwise'].astype(str).eq(str(sel_or['Legwise']))
                    ].drop(columns=['_OpsRemarkOutcome', '_RemarkOutcome'], errors='ignore').copy()
                    o_raw_clean = clean_dataframe_for_excel(o_raw, sheet_type="ops_raw")
                    st.markdown(f"#### 📄 `{sel_or['Origin RO']}` · `{sel_or['Route Path']}` · `{sel_or['Legwise']}` (**{len(o_raw_clean):,} trips**)")
                    render_centered_html_table(o_raw_clean, height=400)

            # On-demand Styled Excel Export
            ops_dl1, ops_dl2 = st.columns([1.6, 3.4])
            if ops_dl1.button("📥 Prepare Styled Excel Report", key="ops_prepare_excel_btn", type="primary", use_container_width=True):
                with st.spinner("Generating styled Operations Excel..."):
                    dl_buf_o = io.BytesIO()
                    with pd.ExcelWriter(dl_buf_o, engine='xlsxwriter') as writer:
                        write_styled_sheet_to_excel(writer, ops_summary_df, 'Operations_Summary', sheet_type="generic", preserve_order=True)
                        write_styled_sheet_to_excel(writer, raw_status.drop(columns=['_OpsRemarkOutcome', '_RemarkOutcome'], errors='ignore'), 'Operations_Raw', sheet_type="ops_raw")
                    st.session_state["_ops_excel_ready_bytes"] = dl_buf_o.getvalue()
            if st.session_state.get("_ops_excel_ready_bytes"):
                ops_dl2.download_button(
                    "⬇️ Download Operations Summary Report (Excel)",
                    data=st.session_state["_ops_excel_ready_bytes"],
                    file_name=f"Operations_Summary_Report_{get_ist_now():%d_%b_%Y}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="ops_ready_download_btn"
                )


# -------------------------------------------------------------
# B. VENDOR PERFORMANCE (With Dynamic User/Vendor Restriction)
# -------------------------------------------------------------
elif choice == "🚚 Vendor Performance":
    if ven_perf_raw_view:
        render_vendor_perf_raw_window(data, ven_perf_query)
        st.stop()

    st.markdown("<h2>Vendor Performance (Routewise/Legwise)</h2>", unsafe_allow_html=True)

    if 'Vendor_Perf_Summary' in data and 'Vendor_Perf_Raw' in data:
        df_vperf_raw_full = data['Vendor_Perf_Raw'].copy()

        if not st.session_state.get('all_vendors', True):
            allowed_v = [normalize_vendor_name(v) for v in st.session_state.get('allowed_vendors', []) if v]
            allowed_v = list(dict.fromkeys([v for v in allowed_v if v]))
            st.info(f"🔒 **Restricted Vendor View:** Showing exclusive performance records for **{', '.join(allowed_v) if allowed_v else 'No Assigned Vendors'}**")
            df_vperf_raw_full = filter_df_by_user_vendors(df_vperf_raw_full, 'VendorName')

        df_vperf_raw, ven_filters = render_unified_filter_bar(
            df_vperf_raw_full,
            key_prefix="ven_main",
            date_col="Date",
            zone_col="Zone" if "Zone" in df_vperf_raw_full.columns else None,
            ro_col="Origin RO" if "Origin RO" in df_vperf_raw_full.columns else None,
            vendor_col="VendorName" if "VendorName" in df_vperf_raw_full.columns else None,
            route_col="Route Path" if "Route Path" in df_vperf_raw_full.columns else None,
            leg_col="Legwise" if "Legwise" in df_vperf_raw_full.columns else None,
            search_placeholder="Search Route, Leg, Vehicle..."
        )
        selected_zone = ven_filters["zone"]
        selected_ro = ven_filters["ro"]
        selected_vendor_b = ven_filters["vendor"]
        search_q = ven_filters["search"]

        df_vperf_sum = build_vendor_summary_from_raw(df_vperf_raw)
        if df_vperf_sum.empty:
            st.warning("No Vendor trips found for the selected criteria/duration.")
            st.stop()

        display_cols = ['Origin RO', 'Route Path', 'Legwise', 'Legs', 'VendorName', 'Total_Trips', 'Ontime Arrival', 'Late Arrival', 'In-Transit']
        df_display = df_vperf_sum[[c for c in display_cols if c in df_vperf_sum.columns]].copy()
        df_display = sort_by_route_and_leg(df_display)
        df_display['RowKey'] = df_display['Origin RO'].astype(str) + " || " + df_display['VendorName'].astype(str) + " | " + df_display['Route Path'].astype(str) + " | " + df_display['Legwise'].astype(str)

        if search_q:
            mask = df_display.astype(str).apply(lambda x: x.str.contains(search_q, case=False, regex=False, na=False)).any(axis=1)
            df_display = df_display[mask]

        # 1. VENDOR ARRIVAL PERFORMANCE GAUGES (Double-click opens ven_raw=1 full window)
        st.markdown("### Vendor Arrival Performance")
        st.caption("🟢 Ontime Arrival · 🔴 Late Arrival · 🟡 In-Transit · 🟣 Missing Schedule. Double-click any gauge to open full RO/Zone/Vendor breakdown in a new window.")

        st_col = 'Remark with 15 min waiver'
        ven_status_series = df_vperf_raw.get(st_col, pd.Series('', index=df_vperf_raw.index)).fillna('').astype(str).str.strip()
        ven_counts = ven_status_series.value_counts().to_dict()
        ven_total = len(df_vperf_raw)
        st.caption(f"**{ven_total:,}** trips · **{len(df_display):,}** vendor route legs")

        _ven_sd_val = st.session_state.get("ven_main_sd")
        _ven_ed_val = st.session_state.get("ven_main_ed")
        ven_gauge_context = {
            "start": _ven_sd_val.isoformat() if hasattr(_ven_sd_val, "isoformat") else "",
            "end": _ven_ed_val.isoformat() if hasattr(_ven_ed_val, "isoformat") else "",
            "zone": ven_filters.get("zone", "ALL"),
            "ro": ven_filters.get("ro", "ALL"),
            "vendor": ven_filters.get("vendor", "ALL"),
            "route": ven_filters.get("route", "ALL"),
            "leg": ven_filters.get("leg", "ALL"),
            "search": ven_filters.get("search", "")
        }
        render_vendor_perf_gauges_open_window(ven_counts, ven_total, ven_gauge_context)

        # On-demand Styled Excel Export
        ven_dl_col1, ven_dl_col2 = st.columns([1.6, 3.4])
        if ven_dl_col1.button("📥 Prepare Styled Excel Report", key="ven_prepare_excel_btn", type="primary", use_container_width=True):
            with st.spinner("Generating styled Vendor Performance Excel..."):
                dl_buf_v = io.BytesIO()
                with pd.ExcelWriter(dl_buf_v, engine='xlsxwriter') as writer:
                    write_styled_sheet_to_excel(writer, df_vperf_sum, 'Vendor_Performance', sheet_type="ven_sum")
                    write_styled_sheet_to_excel(writer, df_vperf_raw, 'Vendor_Raw_Data', sheet_type="ven_raw")
                st.session_state["_ven_excel_ready_bytes"] = dl_buf_v.getvalue()
        if st.session_state.get("_ven_excel_ready_bytes"):
            ven_dl_col2.download_button(
                "⬇️ Download Vendor Performance Report (Excel)",
                data=st.session_state["_ven_excel_ready_bytes"],
                file_name=f"Vendor_Performance_Report_{get_ist_now():%d_%b_%Y}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="ven_ready_download_btn"
            )


# -------------------------------------------------------------
# C. VENDOR PAYMENT DASHBOARD 
# -------------------------------------------------------------
elif choice == "💳 Payment Dashboard":
    st.markdown("<h2>Pending Payments Tracker</h2>", unsafe_allow_html=True)

    if 'Master_Database' in data or 'Payment_Raw' in data:
        curr_u_id = st.session_state.get('username', 'user')
        _pay_p = FILE_MAP.get('PAYMENT', '')
        _vcm_p = FILE_MAP.get('VENDOR_CATEGORY_MAP', '')
        _uvcm_p = FILE_MAP.get('USER_VENDOR_CATEGORY_MAP', '')
        _pay_prep_sig = (
            file_version(_pay_p) if _pay_p and os.path.exists(_pay_p) else None,
            file_version(_vcm_p) if _vcm_p and os.path.exists(_vcm_p) else None,
            file_version(_uvcm_p) if _uvcm_p and os.path.exists(_uvcm_p) else None,
            curr_u_id,
            bool(st.session_state.get('all_vendors', True)),
            tuple(st.session_state.get('allowed_vendors', []))
        )
        _pay_prep_cache = st.session_state.get('_pay_prepared_frame_cache')
        if _pay_prep_cache and _pay_prep_cache[0] == _pay_prep_sig:
            df_pay = _pay_prep_cache[1]
        else:
            payment_source = data.get('Payment_Raw', data.get('Master_Database', pd.DataFrame()))
            df_pay = prepare_payment_dashboard_frame(payment_source)
            if df_pay.empty and 'Master_Database' in data:
                df_pay = prepare_payment_dashboard_frame(data['Master_Database'])
            if not st.session_state.get('all_vendors', True):
                df_pay = filter_df_by_user_vendors(df_pay, 'Vendor Name')
            st.session_state['_pay_prepared_frame_cache'] = (_pay_prep_sig, df_pay)

        if df_pay.empty:
            st.warning("No active payment records found for your assigned vendor access.")
            st.stop()
        is_admin_user = st.session_state.get('role') == 'Admin'
        all_raw_cats = sorted(
            c for c in df_pay.get('Category', pd.Series(dtype=str)).dropna().astype(str).str.strip().unique().tolist()
            if c and c.upper() not in ('NAN', 'NONE')
        )
        all_pay_vendors = sorted(
            v for v in df_pay.get('Vendor Name', pd.Series(dtype=str)).dropna().astype(str).str.strip().unique().tolist()
            if v and v.upper() not in ('NAN', 'NONE')
        )
        all_pay_uploaders = sorted(
            u for u in df_pay.get('Bill Uploader', pd.Series(dtype=str)).dropna().astype(str).str.strip().unique().tolist()
            if u and u.upper() not in ('NAN', 'NONE')
        )

        # ---------------------------------------------------------
        # A. VENDOR MAPPING CATEGORY & UPLOADER/VENDOR TRACKER
        #    (Single clean expander with tabs — NO nested st.columns!)
        # ---------------------------------------------------------
        with st.expander("🗂️ Vendor Mapping Category & Uploader Tracker", expanded=False):
            admin_cat_map = load_vendor_category_mapping()
            user_cat_map = load_user_vendor_category_mapping(curr_u_id)

            if is_admin_user:
                tab_vcm_admin, tab_vcm_user, tab_utv = st.tabs([
                    "🔒 Vendor Mapping (Admin Global)",
                    "👤 My Personal Category Mapping",
                    "🎯 My Tracked Vendors / Uploader Tracker"
                ])
            else:
                tab_vcm_user, tab_utv, tab_vcm_admin = st.tabs([
                    "👤 My Personal Category Mapping",
                    "🎯 My Tracked Vendors / Uploader Tracker",
                    "🔒 Admin Global Mapping (View Only)"
                ])

            with tab_vcm_admin:
                if is_admin_user:
                    st.caption("Permanent mappings visible to all users. Only Admin can edit or delete these.")
                    ex_a_grps = list(admin_cat_map.keys())
                    sel_a_grp = st.selectbox("Select Global Group or Create New:", ["+ Create New Group"] + ex_a_grps, key="vcm_admin_sel_grp")
                    if sel_a_grp == "+ Create New Group":
                        a_grp_name = st.text_input("New Global Mapping Name:", placeholder="e.g. Vehicle Vendors bill", key="vcm_admin_new_name").strip()
                        a_def_cats = []
                    else:
                        a_grp_name = sel_a_grp
                        a_def_cats = [c for c in admin_cat_map.get(sel_a_grp, []) if c in all_raw_cats]
                    a_chosen = st.multiselect(
                        "Assign Raw Categories:",
                        options=sorted(set(all_raw_cats) | set(a_def_cats)),
                        default=a_def_cats,
                        key=f"vcm_admin_cats_{re.sub(r'[^A-Za-z0-9]+', '_', sel_a_grp)}"
                    )
                    ab1, ab2 = st.columns(2)
                    if ab1.button("💾 Save Global Mapping", key="vcm_admin_save", type="primary", use_container_width=True):
                        if not a_grp_name:
                            st.error("Enter a group name.")
                        else:
                            admin_cat_map[a_grp_name] = a_chosen
                            save_vendor_category_mapping(admin_cat_map)
                            st.session_state.pop('_pay_prepared_frame_cache', None)
                            st.success(f"Saved permanent mapping **{a_grp_name}**.")
                            st.rerun()
                    if sel_a_grp != "+ Create New Group":
                        if ab2.button("🗑️ Delete Global Mapping", key="vcm_admin_del", use_container_width=True):
                            admin_cat_map.pop(sel_a_grp, None)
                            save_vendor_category_mapping(admin_cat_map)
                            st.session_state.pop('_pay_prepared_frame_cache', None)
                            st.success(f"Deleted **{sel_a_grp}**.")
                            st.rerun()
                else:
                    st.caption("Permanent mappings set by Admin (read-only for users).")
                if admin_cat_map:
                    render_centered_html_table(pd.DataFrame([
                        {"Global Mapping": g, "Count": len(cs), "Categories": ", ".join(cs)}
                        for g, cs in admin_cat_map.items()
                    ]), height=200)

            with tab_vcm_user:
                st.caption(f"Personal category mappings for **`{curr_u_id}`** (only visible to your account; Admin permanent mappings stay intact).")
                ex_u_grps = list(user_cat_map.keys())
                sel_u_grp = st.selectbox("Select Personal Group or Create New:", ["+ Create New Group"] + ex_u_grps, key="vcm_user_sel_grp")
                if sel_u_grp == "+ Create New Group":
                    u_grp_name = st.text_input("New Personal Mapping Name:", placeholder="e.g. My Feeder Bills", key="vcm_user_new_name").strip()
                    u_def_cats = []
                else:
                    u_grp_name = sel_u_grp
                    u_def_cats = [c for c in user_cat_map.get(sel_u_grp, []) if c in all_raw_cats]
                u_chosen = st.multiselect(
                    "Assign Raw Categories:",
                    options=sorted(set(all_raw_cats) | set(u_def_cats)),
                    default=u_def_cats,
                    key=f"vcm_user_cats_{re.sub(r'[^A-Za-z0-9]+', '_', sel_u_grp)}"
                )
                ub1, ub2 = st.columns(2)
                if ub1.button("💾 Save Personal Mapping", key="vcm_user_save", type="primary", use_container_width=True):
                    if not u_grp_name:
                        st.error("Enter a group name.")
                    else:
                        user_cat_map[u_grp_name] = u_chosen
                        save_user_vendor_category_mapping(curr_u_id, user_cat_map)
                        st.session_state.pop('_pay_prepared_frame_cache', None)
                        st.success(f"Saved personal mapping **{u_grp_name}**.")
                        st.rerun()
                if sel_u_grp != "+ Create New Group":
                    if ub2.button("🗑️ Delete Personal Mapping", key="vcm_user_del", use_container_width=True):
                        user_cat_map.pop(sel_u_grp, None)
                        save_user_vendor_category_mapping(curr_u_id, user_cat_map)
                        st.session_state.pop('_pay_prepared_frame_cache', None)
                        st.success(f"Deleted **{sel_u_grp}**.")
                        st.rerun()
                if user_cat_map:
                    render_centered_html_table(pd.DataFrame([
                        {"My Mapping": g, "Count": len(cs), "Categories": ", ".join(cs)}
                        for g, cs in user_cat_map.items()
                    ]), height=200)

            with tab_utv:
                st.caption(f"Saved separately for **`{curr_u_id}`**. Pick the Vendors and/or Bill Uploader names you want to track payment performance for.")
                my_trackers = load_user_tracked_vendors(curr_u_id)
                ex_t_grps = list(my_trackers.keys())
                sel_t_grp = st.selectbox("Select Tracker Group or Create New:", ["+ Create New Tracker"] + ex_t_grps, key="utv_sel_grp")
                if sel_t_grp == "+ Create New Tracker":
                    t_name_in = st.text_input("Tracker Name:", placeholder="e.g. My Uploaded Vendors", key="utv_new_name").strip()
                    t_def_vends = []
                    t_def_upls = []
                else:
                    t_name_in = sel_t_grp
                    t_info = my_trackers.get(sel_t_grp, {})
                    t_def_vends = [v for v in t_info.get("vendors", []) if v in all_pay_vendors]
                    t_def_upls = [u for u in t_info.get("uploaders", []) if u in all_pay_uploaders]

                t_vends_in = st.multiselect(
                    "Select Vendors to Track:",
                    options=sorted(set(all_pay_vendors) | set(t_def_vends)),
                    default=t_def_vends,
                    key=f"utv_vends_{re.sub(r'[^A-Za-z0-9]+', '_', sel_t_grp)}"
                )
                t_upls_in = st.multiselect(
                    "Select Bill Uploader Name(s) (optional):",
                    options=sorted(set(all_pay_uploaders) | set(t_def_upls)),
                    default=t_def_upls,
                    key=f"utv_upls_{re.sub(r'[^A-Za-z0-9]+', '_', sel_t_grp)}"
                )
                tb1, tb2 = st.columns(2)
                if tb1.button("💾 Save Tracker", key="utv_save_btn", type="primary", use_container_width=True):
                    if not t_name_in:
                        st.error("Please enter a tracker name.")
                    elif not t_vends_in and not t_upls_in:
                        st.error("Select at least one Vendor or Bill Uploader.")
                    else:
                        my_trackers[t_name_in] = {"vendors": t_vends_in, "uploaders": t_upls_in}
                        save_user_tracked_vendors(curr_u_id, my_trackers)
                        st.success(f"Saved tracker **{t_name_in}** ({len(t_vends_in)} vendors, {len(t_upls_in)} uploaders).")
                        st.rerun()
                if sel_t_grp != "+ Create New Tracker":
                    if tb2.button("🗑️ Delete Tracker", key="utv_del_btn", use_container_width=True):
                        my_trackers.pop(sel_t_grp, None)
                        save_user_tracked_vendors(curr_u_id, my_trackers)
                        st.success(f"Deleted tracker **{sel_t_grp}**.")
                        st.rerun()

                if my_trackers:
                    render_centered_html_table(pd.DataFrame([
                        {
                            "Tracker Name": tn,
                            "Vendors": len(ti.get("vendors", [])),
                            "Uploaders": ", ".join(ti.get("uploaders", [])) or "—"
                        }
                        for tn, ti in my_trackers.items()
                    ]), height=200)

        # Top Unified Filter Bar
        pay_date_col = "Base Date" if "Base Date" in df_pay.columns else ("Invoice Date" if "Invoice Date" in df_pay.columns else None)
        df_pay, pay_filters = render_unified_filter_bar(
            df_pay,
            key_prefix="pay_main",
            date_col=pay_date_col,
            zone_col="Zone" if "Zone" in df_pay.columns else None,
            ro_col="RO Name" if "RO Name" in df_pay.columns else None,
            vendor_col="Vendor Name" if "Vendor Name" in df_pay.columns else None,
            route_col=None,
            search_placeholder="Search Invoice, Vendor, RO, Pending With..."
        )

        # Vendor Mapping Category + Invoice Category + My Tracked Vendors/Uploaders Filter Row
        pf1, pf2, pf3 = st.columns([1.2, 1.3, 1.3])

        # Build Vendor Mapping Category filter options (Admin Global + User Personal)
        admin_cat_map_f = load_vendor_category_mapping()
        user_cat_map_f = load_user_vendor_category_mapping(curr_u_id)
        vmc_filter_map = {}
        for g_n, c_l in admin_cat_map_f.items():
            vmc_filter_map[g_n] = {str(x).strip().lower() for x in (c_l or [])}
        for g_n, c_l in user_cat_map_f.items():
            vmc_filter_map[f"{g_n} (My Mapping)"] = {str(x).strip().lower() for x in (c_l or [])}
        vmc_opts = ["ALL"] + list(vmc_filter_map.keys()) + ["Unmapped"]
        sel_vmc = pf1.selectbox("Vendor Mapping Category:", vmc_opts, key="pay_vmc_filter")
        if sel_vmc != "ALL":
            if sel_vmc == "Unmapped":
                df_pay = df_pay[df_pay['Vendor Mapping Category'].astype(str).eq("Unmapped")].copy()
            else:
                target_cat_set = vmc_filter_map.get(sel_vmc, set())
                df_pay = df_pay[df_pay['Category'].fillna('').astype(str).str.strip().str.lower().isin(target_cat_set)].copy()

        cat_opts = ["ALL"] + sorted(
            v for v in df_pay['Category'].dropna().astype(str).unique().tolist() if v
        ) if 'Category' in df_pay.columns else ["ALL"]
        sel_cat = pf2.selectbox("Invoice Category:", cat_opts, key="pay_cat_filter")
        if sel_cat != "ALL":
            df_pay = df_pay[df_pay['Category'].astype(str).eq(sel_cat)].copy()

        # Build My Tracked Vendors / Uploader Tracker filter options
        tracker_choices = {}
        my_t_dict = load_user_tracked_vendors(curr_u_id)
        for t_n, t_info in my_t_dict.items():
            tracker_choices[f"⭐ {t_n}"] = t_info
        if is_admin_user:
            all_t_db = load_all_user_tracked_vendors()
            for u_other, u_t_dict in all_t_db.items():
                if u_other == curr_u_id:
                    continue
                for t_n, t_info in (u_t_dict or {}).items():
                    tracker_choices[f"👤 {u_other} · {t_n}"] = t_info

        tracker_opts = ["ALL"] + list(tracker_choices.keys())
        sel_tracker = pf3.selectbox("👤 Vendor / Uploader Tracker:", tracker_opts, key="pay_tracker_filter")
        if sel_tracker != "ALL" and sel_tracker in tracker_choices:
            t_sel_info = tracker_choices[sel_tracker]
            t_v_set = {str(x).strip().upper() for x in t_sel_info.get("vendors", [])}
            t_u_set = {str(x).strip().upper() for x in t_sel_info.get("uploaders", [])}
            t_mask = pd.Series(False, index=df_pay.index)
            if t_v_set and 'Vendor Name' in df_pay.columns:
                t_mask |= df_pay['Vendor Name'].fillna('').astype(str).str.strip().str.upper().isin(t_v_set)
            if t_u_set and 'Bill Uploader' in df_pay.columns:
                t_mask |= df_pay['Bill Uploader'].fillna('').astype(str).str.strip().str.upper().isin(t_u_set)
            df_pay = df_pay[t_mask].copy()

        if df_pay.empty:
            st.info("No payment records match the selected filters.")
            st.stop()

        # Exact 5-bucket sequence: Payment Pending / Paid -> Draft -> Cost Control Pending -> Finance Pending -> Finance Hold
        bucket_labels = [
            'Payment Pending / Paid',
            'Draft',
            'Cost Control Pending',
            'Finance Pending',
            'Finance Hold'
        ]
        pay_total_bills = len(df_pay)
        payment_counts = df_pay['Payment Group'].value_counts().to_dict()

        if "pay_gauge_bucket_filter" not in st.session_state:
            st.session_state["pay_gauge_bucket_filter"] = "ALL"

        def _pick_pay_gauge(chosen_b):
            if st.session_state.get("pay_gauge_bucket_filter") == chosen_b:
                st.session_state["pay_gauge_bucket_filter"] = "ALL"
            else:
                st.session_state["pay_gauge_bucket_filter"] = chosen_b

        st.markdown("### Payment Status Overview")
        st.caption(f"🟢 Payment Pending / Paid · 🔴 Draft · 🟡 Cost Control Pending · 🟡 Finance Pending · 🔴 Finance Hold · **{pay_total_bills:,}** active bills (double-click any gauge to filter below)")

        pay_gauge_specs = [
            ('Payment Pending / Paid', int(payment_counts.get('Payment Pending / Paid', 0)), '#16a34a', '#f0fdf4', '#bbf7d0', '🟢'),
            ('Draft', int(payment_counts.get('Draft', 0)), '#dc2626', '#fef2f2', '#fecaca', '🔴'),
            ('Cost Control Pending', int(payment_counts.get('Cost Control Pending', 0)), '#f59e0b', '#fffbeb', '#fde68a', '🟡'),
            ('Finance Pending', int(payment_counts.get('Finance Pending', 0)), '#f59e0b', '#fffbeb', '#fde68a', '🟡'),
            ('Finance Hold', int(payment_counts.get('Finance Hold', 0)), '#dc2626', '#fef2f2', '#fecaca', '🔴'),
        ]

        p_track_c = '#e2e8f0' if THEME_IS_LIGHT else 'rgba(148,163,184,.22)'
        p_text_c = '#0f172a' if THEME_IS_LIGHT else selected_theme['text']
        p_muted_c = '#475569' if THEME_IS_LIGHT else selected_theme['muted']
        active_pay_bkt = st.session_state.get("pay_gauge_bucket_filter", "ALL")

        p_cards = []
        for p_lbl, p_cnt, p_col, p_lbg, p_lbd, p_ico in pay_gauge_specs:
            p_pct = (p_cnt / pay_total_bills * 100.0) if pay_total_bills else 0.0
            p_dash = 201.06 * min(100.0, max(0.0, p_pct)) / 100.0
            p_bg = p_lbg if THEME_IS_LIGHT else selected_theme['card1']
            p_bd = p_lbd if THEME_IS_LIGHT else selected_theme['line']
            p_ring = f'box-shadow: 0 0 0 2.5px {p_col}, 0 8px 20px rgba(15,23,42,.10);' if active_pay_bkt == p_lbl else 'box-shadow: 0 4px 14px rgba(15,23,42,.05);'
            p_cards.append(
                f'<div class="pg-card" role="button" tabindex="0" data-label="{html_module.escape(p_lbl, quote=True)}" '
                f'title="Double-click to filter {html_module.escape(p_lbl)} below" '
                f'style="background:{p_bg};border-color:{p_bd};{p_ring}">'
                f'<div class="pg-label">{p_ico} {html_module.escape(p_lbl)}</div>'
                f'<svg viewBox="0 0 180 108" role="img" aria-label="{p_pct:.1f} percent">'
                f'<path d="M 18 90 A 72 72 0 0 1 162 90" fill="none" stroke="{p_track_c}" stroke-width="13" stroke-linecap="round" pathLength="201.06"/>'
                f'<path d="M 18 90 A 72 72 0 0 1 162 90" fill="none" stroke="{p_col}" stroke-width="13" stroke-linecap="round" stroke-dasharray="{p_dash:.2f} 201.06" pathLength="201.06"/>'
                f'<text x="90" y="75" text-anchor="middle" font-size="27" font-weight="850" fill="{p_text_c}">{p_pct:.1f}%</text>'
                f'<text x="90" y="99" text-anchor="middle" font-size="14" font-weight="800" fill="{p_col}">{p_cnt:,} bills</text>'
                f'</svg>'
                f'<div class="pg-sub">out of <strong>{pay_total_bills:,}</strong> bills</div>'
                f'<div class="pg-hint">Double-click to filter below</div>'
                f'</div>'
            )

        p_html = (
            f'<!doctype html><html><head><meta charset="utf-8"><style>'
            f'* {{ box-sizing:border-box; }}'
            f'body {{ margin:0; padding:2px; font-family:Inter,system-ui,-apple-system,Arial,sans-serif; background:transparent; color:{p_text_c}; user-select:none; }}'
            f'.grid {{ display:grid; grid-template-columns:repeat(5,minmax(145px,1fr)); gap:10px; }}'
            f'.pg-card {{ border:1px solid; border-radius:15px; padding:10px 8px 8px; text-align:center; cursor:pointer; transition:transform .14s ease, box-shadow .14s ease; }}'
            f'.pg-card:hover {{ transform:translateY(-2px); box-shadow:0 10px 22px rgba(15,23,42,.12) !important; }}'
            f'.pg-label {{ font-size:12px; font-weight:800; color:{p_text_c}; min-height:22px; display:flex; align-items:center; justify-content:center; }}'
            f'svg {{ display:block; width:min(100%,168px); height:auto; margin:0 auto; overflow:visible; }}'
            f'.pg-sub {{ font-size:11px; font-weight:600; color:{p_muted_c}; margin-top:2px; }}'
            f'.pg-sub strong {{ color:{p_text_c}; font-weight:800; }}'
            f'.pg-hint {{ font-size:10px; font-weight:650; color:{selected_theme["blue"]}; margin-top:3px; opacity:.82; }}'
            f'.pg-card:hover .pg-hint {{ opacity:1; text-decoration:underline; }}'
            f'@media(max-width:1050px) {{ .grid {{ grid-template-columns:repeat(3,minmax(145px,1fr)); }} }}'
            f'@media(max-width:650px) {{ .grid {{ grid-template-columns:repeat(2,minmax(140px,1fr)); }} }}'
            f'</style></head><body><div class="grid">{"".join(p_cards)}</div><script>'
            f'function pickPayGauge(card) {{'
            f'  const targetLabel = "__PAY_GPICK__" + card.dataset.label;'
            f'  try {{'
            f'    const btns = window.parent.document.querySelectorAll("button");'
            f'    for (const b of btns) {{'
            f'      if ((b.innerText || b.textContent || "").trim() === targetLabel) {{ b.click(); return; }}'
            f'    }}'
            f'  }} catch (e) {{}}'
            f'}}'
            f'document.querySelectorAll(".pg-card").forEach((card) => {{'
            f'  card.addEventListener("dblclick", (e) => {{ e.preventDefault(); pickPayGauge(card); }});'
            f'  card.addEventListener("keydown", (e) => {{ if (e.key === "Enter") {{ e.preventDefault(); pickPayGauge(card); }} }});'
            f'}});'
            f'</script></body></html>'
        )
        st.components.v1.html(p_html, height=202, scrolling=False)

        # Safe keyed offscreen trigger container (NEVER affects outer page block!)
        st.markdown("""
        <style>
        .st-key-pay_gauge_triggers_box {
            position: fixed !important; left: -9999px !important; top: -9999px !important;
            width: 0px !important; height: 0px !important; max-height: 0px !important;
            overflow: hidden !important; opacity: 0 !important; margin: 0 !important; padding: 0 !important;
            pointer-events: none !important;
        }
        </style>
        """, unsafe_allow_html=True)
        try:
            _pay_t_box = st.container(key="pay_gauge_triggers_box")
        except TypeError:
            _pay_t_box = st.container()
        with _pay_t_box:
            for p_idx, (p_lbl, _, _, _, _, _) in enumerate(pay_gauge_specs):
                st.button(
                    f"__PAY_GPICK__{p_lbl}",
                    key=f"pay_gpick_{p_idx}_{re.sub(r'[^A-Za-z0-9]+', '_', p_lbl)}",
                    on_click=_pick_pay_gauge,
                    args=(p_lbl,)
                )

        if active_pay_bkt != "ALL":
            pb1, pb2 = st.columns([4.5, 1.2])
            pb1.info(f"Gauge filter active: **{active_pay_bkt}** (double-click same gauge or click Show All)")
            if pb2.button("↺ Show All", key="pay_gauge_reset_btn", use_container_width=True):
                st.session_state["pay_gauge_bucket_filter"] = "ALL"
                st.rerun()

        # Summary Table with Group-By Switcher: RO-wise / Vendor-wise / Uploader-wise
        st.markdown('### 📋 Payment Performance Summary')
        pay_grp_mode = st.radio(
            "Group Summary By:",
            ["RO-wise", "Vendor-wise", "Uploader-wise"],
            horizontal=True,
            key="pay_summary_group_mode"
        )

        if pay_grp_mode == "RO-wise":
            grp_col_name, grp_disp_label = get_col(df_pay, ['RO Name']), 'RO'
        elif pay_grp_mode == "Vendor-wise":
            grp_col_name, grp_disp_label = get_col(df_pay, ['Vendor Name']), 'Vendor'
        else:
            grp_col_name, grp_disp_label = get_col(df_pay, ['Bill Uploader']), 'Bill Uploader'

        summary_rows = []
        if grp_col_name:
            for g_val, g_rows in df_pay.groupby(grp_col_name, dropna=False):
                g_str = str(g_val).strip() or 'Unassigned'
                total_bills = len(g_rows)
                row = {grp_disp_label: g_str, 'Total Bills': total_bills}
                for bucket in bucket_labels:
                    cnt = int(g_rows['Payment Group'].eq(bucket).sum())
                    row[bucket] = format_pct_cnt(cnt, total_bills)
                summary_rows.append(row)
        payment_summary = pd.DataFrame(summary_rows, columns=[grp_disp_label, 'Total Bills'] + bucket_labels)
        if not payment_summary.empty:
            payment_summary = payment_summary.sort_values(by='Total Bills', ascending=False).reset_index(drop=True)

        if payment_summary.empty:
            st.info('No payment rows match the selected filters.')
        else:
            render_centered_html_table(payment_summary, height=460)

            # Focused Invoice Drill-Down (auto-filters if a gauge is active!)
            st.markdown('### 📄 Detailed Invoice Records')
            pc1, pc2 = st.columns([1.4, 1.4])
            pay_ro_pick = pc1.selectbox(f'Filter Invoices by {grp_disp_label}:', [f'ALL {grp_disp_label.upper()}S'] + payment_summary[grp_disp_label].astype(str).tolist(), key='pay_ro_inspector')
            default_bkt_idx = (bucket_labels.index(active_pay_bkt) + 1) if active_pay_bkt in bucket_labels else 0
            pay_bkt_pick = pc2.selectbox('Filter by Payment Bucket:', ['ALL BUCKETS'] + bucket_labels, index=default_bkt_idx, key='pay_bkt_inspector')

            detail = df_pay.copy()
            if pay_ro_pick != f'ALL {grp_disp_label.upper()}S' and grp_col_name:
                detail = detail[detail[grp_col_name].fillna('').astype(str).str.strip().eq(pay_ro_pick)].copy()
            if pay_bkt_pick != 'ALL BUCKETS':
                detail = detail[detail['Payment Group'].eq(pay_bkt_pick)].copy()
            elif active_pay_bkt != 'ALL':
                detail = detail[detail['Payment Group'].eq(active_pay_bkt)].copy()

            if 'Amount' in detail.columns:
                detail['Amount'] = pd.to_numeric(detail['Amount'], errors='coerce').fillna(0.0)
            if 'Days Pending' in detail.columns and 'Amount' in detail.columns:
                detail = detail.sort_values(by=['Days Pending', 'Amount'], ascending=[False, False])
            total_detail_cnt = len(detail)
            compact_display = compact_detail_frame(detail.head(400), 'pay_raw')
            st.caption(f"Showing top **{len(compact_display):,}** of **{total_detail_cnt:,}** matching invoices (sorted by highest Days Pending). Download Excel for all {total_detail_cnt:,} rows.")
            render_centered_html_table(compact_display, height=520, max_rows=400)

            pay_dl1, pay_dl2 = st.columns([1.6, 3.4])
            if pay_dl1.button('📥 Prepare Payment Report (Excel)', key='pay_prep_excel_btn', type='primary', use_container_width=True):
                with st.spinner('Generating formatted Payment Excel...'):
                    compact_full = compact_detail_frame(detail, 'pay_raw')
                    pay_bytes = io.BytesIO()
                    with pd.ExcelWriter(pay_bytes, engine='xlsxwriter') as writer:
                        write_styled_sheet_to_excel(writer, payment_summary, f'{pay_grp_mode}_Summary', sheet_type='generic', preserve_order=True)
                        write_styled_sheet_to_excel(writer, compact_full, 'Detailed_Invoices', sheet_type='pay_raw', preserve_order=True)
                    st.session_state['_pay_excel_ready_bytes'] = pay_bytes.getvalue()
            if st.session_state.get('_pay_excel_ready_bytes'):
                pay_dl2.download_button(
                    '⬇️ Download Payment Report (Excel)',
                    data=st.session_state['_pay_excel_ready_bytes'],
                    file_name=f"Payment_Dashboard_{get_ist_now():%d_%b_%Y}.xlsx",
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    key='payment_detail_download'
                )

# -------------------------------------------------------------
# D. COMMUNICATION HUB (3 Full Sub-Modules: National, Vendor, RO)
# -------------------------------------------------------------
elif choice == "📱 Communication Hub":
    st.markdown("<h2>📱 Communication Hub (National Routes, Vendors & Regional Offices)</h2>", unsafe_allow_html=True)
    
    df_ops_raw_base = data.get('Legwise_Processed_Data', pd.DataFrame()).copy()
    df_ven_raw_base = data.get('Vendor_Perf_Raw', pd.DataFrame()).copy()
    if not df_ven_raw_base.empty and 'VendorName' in df_ven_raw_base.columns:
        df_ven_raw_base['VendorName'] = df_ven_raw_base['VendorName'].apply(normalize_vendor_name)
    if not st.session_state.get('all_vendors', True):
        df_ven_raw_base = filter_df_by_user_vendors(df_ven_raw_base, 'VendorName')
        
    df_pay_base = prepare_payment_dashboard_frame(data.get('Payment_Raw', data.get('Master_Database', pd.DataFrame())))
    if not st.session_state.get('all_vendors', True):
        df_pay_base = filter_df_by_user_vendors(df_pay_base, 'Vendor Name')
    df_cpk_raw_base = data.get('CPK_Raw_Data', pd.DataFrame()).copy()
    
    df_ven_raw_hub, is_hub_filtered, hub_dur_str = render_duration_selector(df_ven_raw_base, 'Date', 'comm_hub')
    if is_hub_filtered and not df_ops_raw_base.empty:
        sd_hub = st.session_state.get('comm_hub_sd')
        ed_hub = st.session_state.get('comm_hub_ed')
        ops_dt = pd.to_datetime(df_ops_raw_base['MCD_StartDate'], dayfirst=True, errors='coerce')
        df_ops_raw_hub = df_ops_raw_base[(ops_dt.dt.date >= sd_hub) & (ops_dt.dt.date <= ed_hub)].copy()
        df_ops_sum_hub = build_ops_summary_from_raw(df_ops_raw_hub)
        df_ven_sum_hub = build_vendor_summary_from_raw(df_ven_raw_hub)
        if not df_cpk_raw_base.empty and 'Date' in df_cpk_raw_base.columns:
            cpk_dt = pd.to_datetime(df_cpk_raw_base['Date'], dayfirst=True, errors='coerce')
            df_cpk_raw_hub = df_cpk_raw_base[(cpk_dt.dt.date >= sd_hub) & (cpk_dt.dt.date <= ed_hub)].copy()
        else:
            df_cpk_raw_hub = df_cpk_raw_base
    else:
        df_ops_raw_hub = df_ops_raw_base
        df_ops_sum_hub = data.get('Legwise_Route_Summary', pd.DataFrame()).copy()
        df_ven_sum_hub = build_vendor_summary_from_raw(df_ven_raw_hub)
        df_cpk_raw_hub = df_cpk_raw_base

    hub_ops_outcomes = ops_remark_outcome_series(df_ops_raw_hub)
    hub_ops_total = len(df_ops_raw_hub)
    hub_ops_ontime = int(hub_ops_outcomes.eq('Ontime Dep, Ontime Arr').sum()) if hub_ops_total else 0
    hub_ops_ontime_pct = hub_ops_ontime / hub_ops_total * 100 if hub_ops_total else 0
    hub_vendor_status_col = get_col(df_ven_raw_hub, ['Remark with 15 min waiver'])
    hub_vendor_status = (
        df_ven_raw_hub[hub_vendor_status_col].fillna('').astype(str)
        if hub_vendor_status_col else pd.Series('', index=df_ven_raw_hub.index)
    )
    hub_vendor_late = int(hub_vendor_status.str.contains('Late Arrival', case=False, na=False).sum())
    hub_vendor_total = len(df_ven_raw_hub)
    hub_vendor_late_pct = hub_vendor_late / hub_vendor_total * 100 if hub_vendor_total else 0
    hub_payment_counts = df_pay_base.get('Payment Group', pd.Series('', index=df_pay_base.index)).value_counts()
    hub_payment_followup = sum(
        int(hub_payment_counts.get(bucket, 0))
        for bucket in ['Finance Pending / Hold', 'Draft', 'Cost Control Pending']
    )
    hub_util_trips = (
        int(pd.to_numeric(df_cpk_raw_hub['Trips'], errors='coerce').fillna(0).sum())
        if 'Trips' in df_cpk_raw_hub.columns else len(df_cpk_raw_hub)
    )
    hub_util_label = 'Utilization trips' if 'Trips' in df_cpk_raw_hub.columns else 'Utilization rows'
    hub_insights = []
    if hub_ops_total:
        hub_insights.append(f"Operations end-to-end on-time rate is {hub_ops_ontime_pct:.1f}% for the selected window.")
    if hub_vendor_total:
        hub_insights.append(f"Vendor late-arrival rate is {hub_vendor_late_pct:.1f}% for the selected window.")
    if hub_payment_followup:
        hub_insights.append(f"{hub_payment_followup:,} available payment records are in finance, draft, or cost-control follow-up buckets.")
    render_powerbi_insights(
        'Communication Hub Network Pulse',
        [('Operations trips', f'{hub_ops_total:,}'), ('Ops on-time end-to-end', f'{hub_ops_ontime_pct:.1f}%'),
         ('Vendor late arrivals', f'{hub_vendor_late:,}'), ('Payment follow-up records', f'{hub_payment_followup:,}'),
         (hub_util_label, f'{hub_util_trips:,}')],
        hub_insights,
        period_note=f"Operational, vendor, and utilization signals use {hub_dur_str}; payment records show the available invoice set."
    )

    hub_tab1, hub_tab2, hub_tab3 = st.tabs([
        "🛣️ 1. National Route Ops & Vendor Summary",
        "🚚 2. Individual & Bulk Vendor Hub",
        "🏢 3. Regionwise (RO) All-Module Summary"
    ])

    # =========================================================
    # HUB TAB 1: NATIONAL ROUTE OPS & VENDOR PERFORMANCE (ROUND TRIP)
    # =========================================================
    with hub_tab1:
        st.markdown("### 🛣️ National Route Round-Trip Ops & Vendor Summary")
        st.caption("Select any National Round-Trip pair below. Duplicate PAN vendor names (like E WHEELS) are automatically combined into 1 row. If a route has 2 different vendors, you can either send combined or select an individual vendor!")
        
        col_nr1, col_nr2, col_nr3 = st.columns([1.2, 1.1, 1.3])
        pair_keys = list(NATIONAL_ROUTE_PAIRS.keys())
        selected_pair_key = col_nr1.selectbox(
            "1. Select National Round-Trip Route Pair:",
            pair_keys,
            format_func=lambda k: f"{k}  🔄  ({' / '.join(NATIONAL_ROUTE_PAIRS[k])})"
        )
        
        active_routes = NATIONAL_ROUTE_PAIRS[selected_pair_key]
        
        nat_ops_sum = sort_by_route_and_leg(df_ops_sum_hub[df_ops_sum_hub['Route Path'].isin(active_routes)].copy()) if not df_ops_sum_hub.empty else pd.DataFrame()
        nat_ops_raw = sort_by_route_and_leg(df_ops_raw_hub[df_ops_raw_hub['Route Path'].isin(active_routes)].copy()) if not df_ops_raw_hub.empty else pd.DataFrame()
        
        nat_ven_raw_all = sort_by_route_and_leg(df_ven_raw_hub[df_ven_raw_hub['Route Path'].isin(active_routes)].copy()) if not df_ven_raw_hub.empty else pd.DataFrame()
        
        route_vendors = sorted(nat_ven_raw_all['VendorName'].dropna().unique().tolist()) if not nat_ven_raw_all.empty else []
        
        selected_nat_vendor = col_nr2.selectbox(
            "2. Select Vendor (For Vendor Perf & Mail):",
            ["ALL VENDORS (Combined)"] + route_vendors,
            key="nat_ven_sel"
        )
        
        v_master_nat = {}
        if os.path.exists(FILE_MAP.get("VENDOR_MASTER")):
            try:
                with open(FILE_MAP.get("VENDOR_MASTER"), 'r') as f:
                    v_master_nat = json.load(f)
            except:
                pass
        default_nat_mail = v_master_nat.get(selected_nat_vendor, {}).get("email", "") if selected_nat_vendor != "ALL VENDORS (Combined)" else ""
        
        nat_emails = col_nr3.text_input(
            "3. Recipient Email IDs (comma separated):",
            value=default_nat_mail,
            placeholder="e.g. anurag@trackon.in, vendor@gmail.com",
            key="nat_mail_input"
        )
        
        st.markdown(f"**Included UP/DOWN Routes:** `{'` , `'.join(active_routes)}` | **Active Vendors on Route:** `{', '.join(route_vendors) if route_vendors else 'None'}`")
        
        if selected_nat_vendor != "ALL VENDORS (Combined)":
            nat_ven_raw = nat_ven_raw_all[nat_ven_raw_all['VendorName'] == selected_nat_vendor].copy()
            nat_ven_sum = build_vendor_summary_from_raw(nat_ven_raw)
            mail_recipient_title = selected_nat_vendor
            vendor_tag_file = f"_{selected_nat_vendor.replace(' ', '_')}"
        else:
            nat_ven_raw = nat_ven_raw_all
            nat_ven_sum = build_vendor_summary_from_raw(nat_ven_raw)
            mail_recipient_title = "Team / Vendor Partner" if len(route_vendors) != 1 else route_vendors[0]
            vendor_tag_file = ""

        nat_excel_buf = io.BytesIO()
        with pd.ExcelWriter(nat_excel_buf, engine='xlsxwriter') as writer:
            write_styled_sheet_to_excel(writer, nat_ven_sum, 'Current_Vendor_Performance', sheet_type="ven_sum")
            write_styled_sheet_to_excel(writer, nat_ven_raw, 'Vendor_Performance_Raw_Data', sheet_type="ven_raw")
            write_styled_sheet_to_excel(writer, nat_ops_sum, 'Current_Ops_Performance', sheet_type="ops_sum")
            write_styled_sheet_to_excel(writer, nat_ops_raw, 'Ops_Performance_Raw_Data', sheet_type="ops_raw")
            
        v_subj_tag = f" [{selected_nat_vendor}]" if selected_nat_vendor != "ALL VENDORS (Combined)" else ""
        nat_subject = f"{selected_pair_key} round trip ops and Vendor performance{v_subj_tag} - {hub_dur_str}"
        nat_body = build_clean_email_message(
            recipient_title=mail_recipient_title,
            duration_label=f"{selected_pair_key} Round Trip ({hub_dur_str})",
            ops_sum_df=nat_ops_sum,
            ven_sum_df=nat_ven_sum
        )
        
        nat_gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&to={urllib.parse.quote(nat_emails.strip())}&su={urllib.parse.quote(nat_subject)}&body={urllib.parse.quote(nat_body)}&authuser=lh.fleetops@trackon.in"
        
        btn_c1, btn_c2 = st.columns(2)
        btn_c1.download_button(
            f"1️⃣ Download {selected_pair_key} Round-Trip Excel (4 Sheets) 📊",
            data=nat_excel_buf.getvalue(),
            file_name=f"{selected_pair_key}{vendor_tag_file}_RoundTrip_Ops_Vendor_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary"
        )
        btn_c2.markdown(
            f'<a href="{nat_gmail_url}" target="_blank"><button style="background-color: #EF4444; color: white; padding: 10px; border: none; border-radius: 8px; width: 100%; cursor: pointer; font-weight: 600;">2️⃣ Send Mail in 1-Click (Gmail) ✉️</button></a>',
            unsafe_allow_html=True
        )
        
        st.markdown("#### Preview: Current Vendor Performance")
        ven_prev_df = clean_dataframe_for_excel(nat_ven_sum, sheet_type="ven_sum")
        render_summary_with_raw_drilldown(
            ven_prev_df, nat_ven_raw, 'National route vendor performance', 'ven_raw', 'comm_national_vendor_drilldown'
        )
        
        st.markdown("#### Preview: Current Ops Performance (Full Route)")
        ops_prev_df = clean_dataframe_for_excel(nat_ops_sum, sheet_type="ops_sum")
        render_summary_with_raw_drilldown(
            ops_prev_df, nat_ops_raw, 'National route operations performance', 'ops_raw', 'comm_national_ops_drilldown'
        )

    # =========================================================
    # HUB TAB 2: INDIVIDUAL VENDOR & BULK MESSAGING HUB
    # =========================================================
    with hub_tab2:
        if not df_ven_sum_hub.empty and not df_ven_raw_hub.empty:
            df_vperf_sum = df_ven_sum_hub.copy()
            df_vperf_raw = df_ven_raw_hub.copy()
            
            if st.session_state.get('role') == 'Admin':
                with st.expander("🛠 Manage Vendor Master Contacts", expanded=False):
                    st.caption("Save Vendor WhatsApp and Email IDs for quick communication.")
                    vendor_master_file = FILE_MAP.get("VENDOR_MASTER")
                    v_master_data = {}
                    if os.path.exists(vendor_master_file):
                        try:
                            with open(vendor_master_file, 'r') as f:
                                v_master_data = json.load(f)
                        except:
                            pass
                    
                    with st.form("vendor_master_form"):
                        col_m1, col_m2, col_m3 = st.columns(3)
                        all_vendors_list = sorted(df_vperf_sum['VendorName'].dropna().unique().tolist())
                        vm_name = col_m1.selectbox("Select Vendor Name", all_vendors_list)
                        pre_wp = v_master_data.get(vm_name, {}).get("whatsapp", "")
                        pre_em = v_master_data.get(vm_name, {}).get("email", "")
                        vm_wp = col_m2.text_input("WhatsApp No (with country code e.g. 9198...)", value=pre_wp)
                        vm_email = col_m3.text_input("Email ID (comma separated allowed)", value=pre_em)
                        
                        if st.form_submit_button("💾 Save to Master"):
                            v_master_data[vm_name] = {"whatsapp": vm_wp.strip(), "email": vm_email.strip()}
                            with open(vendor_master_file, 'w') as f:
                                json.dump(v_master_data, f)
                            st.success(f"Contact details for {vm_name} saved successfully!")
                st.markdown("---")
            
            st.markdown("### 🔍 Individual Vendor Messaging & Report")
            col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
            
            all_zones = sorted(df_vperf_sum['Zone'].dropna().unique().tolist()) if 'Zone' in df_vperf_sum.columns else []
            selected_zone = col1.selectbox("Filter Zone:", ["ALL"] + all_zones, key="vh_z")
            if selected_zone != "ALL":
                df_vperf_sum = df_vperf_sum[df_vperf_sum['Zone'] == selected_zone]
                df_vperf_raw = df_vperf_raw[df_vperf_raw['Zone'] == selected_zone]
                
            all_ros = sorted(df_vperf_sum['Origin RO'].dropna().unique().tolist())
            selected_ro = col2.selectbox("Filter RO:", ["ALL"] + all_ros, key="vh_r")
            if selected_ro != "ALL":
                df_vperf_sum = df_vperf_sum[df_vperf_sum['Origin RO'] == selected_ro]
                df_vperf_raw = df_vperf_raw[df_vperf_raw['Origin RO'] == selected_ro]

            all_routes = sorted(df_vperf_sum['Route Path'].dropna().unique().tolist())
            selected_route = col3.selectbox("Filter Route:", ["ALL"] + all_routes, key="vh_rt")
            if selected_route != "ALL":
                df_vperf_sum = df_vperf_sum[df_vperf_sum['Route Path'] == selected_route]
                df_vperf_raw = df_vperf_raw[df_vperf_raw['Route Path'] == selected_route]
                
            all_vendors_filtered = sorted(df_vperf_sum['VendorName'].dropna().unique().tolist())
            selected_vendor = col4.selectbox("Select Vendor for Detailed View:", ["ALL"] + all_vendors_filtered, key="vh_v")
            
            if selected_vendor != "ALL":
                target_vendor = selected_vendor
                ven_sum = sort_by_route_and_leg(df_vperf_sum[df_vperf_sum['VendorName'] == target_vendor].copy())
                ven_raw = sort_by_route_and_leg(df_vperf_raw[df_vperf_raw['VendorName'] == target_vendor].copy())
                
                st.markdown(f"#### Performance View: `{target_vendor}`")
                ind_ven_prev = clean_dataframe_for_excel(ven_sum, sheet_type="ven_sum")
                render_summary_with_raw_drilldown(
                    ind_ven_prev, ven_raw, f'{target_vendor} performance', 'ven_raw', 'comm_vendor_detail_drilldown'
                )

                v_master_data_live = {}
                if os.path.exists(FILE_MAP.get("VENDOR_MASTER")):
                    try:
                        with open(FILE_MAP.get("VENDOR_MASTER"), 'r') as f:
                            v_master_data_live = json.load(f)
                    except:
                        pass
                ven_contact = v_master_data_live.get(target_vendor, {})
                wp_num = ven_contact.get("whatsapp", "")
                saved_email = ven_contact.get("email", "")
                
                custom_ven_email = st.text_input("Recipient Email ID(s) (optional):", value=saved_email, placeholder="Enter email or leave blank to type in Gmail", key="ind_ven_email")
                
                msg = build_clean_email_message(
                    recipient_title=target_vendor,
                    duration_label=hub_dur_str,
                    ven_sum_df=ven_sum
                )
                
                output_ven = io.BytesIO()
                with pd.ExcelWriter(output_ven, engine='xlsxwriter') as writer:
                    write_styled_sheet_to_excel(writer, ven_sum, 'Performance_Summary', sheet_type="ven_sum")
                    write_styled_sheet_to_excel(writer, ven_raw, 'Raw_Trip_Details', sheet_type="ven_raw")

                ven_file_name = f"{target_vendor}_Performance_Report.xlsx"
                
                c1, c2, c3 = st.columns(3)
                c1.download_button(
                    "1️⃣ Download Styled Excel 📊",
                    data=output_ven.getvalue(),
                    file_name=ven_file_name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    type="primary"
                )
                
                encoded_msg = urllib.parse.quote(msg)
                wp_url = f"https://api.whatsapp.com/send?phone={wp_num}&text={encoded_msg}"
                c2.markdown(f'<a href="{wp_url}" target="_blank"><button style="background-color: #25D366; color: white; padding: 10px; border: none; border-radius: 8px; width: 100%; cursor: pointer; font-weight: 600;">2️⃣ Open WhatsApp 💬</button></a>', unsafe_allow_html=True)
                
                subject = urllib.parse.quote(f"Trackon Performance Report: {target_vendor} - {hub_dur_str}")
                gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&to={urllib.parse.quote(custom_ven_email.strip())}&su={subject}&body={encoded_msg}&authuser=lh.fleetops@trackon.in"
                c3.markdown(f'<a href="{gmail_url}" target="_blank"><button style="background-color: #EF4444; color: white; padding: 10px; border: none; border-radius: 8px; width: 100%; cursor: pointer; font-weight: 600;">3️⃣ Open in Gmail 🌐</button></a>', unsafe_allow_html=True)

            st.markdown("---")
            if st.session_state.get('role') == 'Admin':
                st.markdown("### 🚀 Bulk Messaging Hub (All Saved Vendors)")
                v_master_data_live = {}
                if os.path.exists(FILE_MAP.get("VENDOR_MASTER")):
                    try:
                        with open(FILE_MAP.get("VENDOR_MASTER"), 'r') as f:
                            v_master_data_live = json.load(f)
                    except:
                        pass
                saved_vendors_in_data = [v for v in v_master_data_live.keys() if v in all_vendors_filtered]
                if not saved_vendors_in_data:
                    st.info("No saved vendors found in current filtered data. Save them in Vendor Master first.")
                else:
                    for v_name in saved_vendors_in_data:
                        v_email = v_master_data_live[v_name].get("email", "")
                        v_sum = sort_by_route_and_leg(df_vperf_sum[df_vperf_sum['VendorName'] == v_name].copy())
                        if v_sum.empty:
                            continue
                        v_total_trips = int(v_sum['Total_Trips'].sum())
                        v_msg = build_clean_email_message(recipient_title=v_name, duration_label=hub_dur_str, ven_sum_df=v_sum)
                        v_subject = urllib.parse.quote(f"Trackon Performance Report: {v_name} - {hub_dur_str}")
                        v_gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&to={urllib.parse.quote(v_email)}&su={v_subject}&body={urllib.parse.quote(v_msg)}&authuser=lh.fleetops@trackon.in"
                        
                        b1, b2 = st.columns([3, 1])
                        b1.markdown(f"**{v_name}** (Trips: {v_total_trips} | Email: `{v_email or 'Not Set'}`)")
                        b2.markdown(f'<a href="{v_gmail_url}" target="_blank"><button style="background-color: #EF4444; color: white; padding: 5px 15px; border: none; border-radius: 6px; width: 100%; cursor: pointer; font-size: 14px; font-weight: 600;">✉️ Compose</button></a>', unsafe_allow_html=True)
                        st.divider()

    # =========================================================
    # HUB TAB 3: REGIONWISE (RO) ALL-MODULE MASTER SUMMARY & FAILURES
    # =========================================================
    with hub_tab3:
        st.markdown("### 🏢 Regionwise (RO) Complete Report & Failures Generator")
        st.caption("Select any RO (e.g. DELRO, AMDRO, HPJRO, MUMRO) to generate its complete multi-module Excel workbook (Ops, Vendor, CPK/Util, Payments) and send email in 1 click.")
        
        ro_set = {"DELRO", "AMDRO", "HPJRO", "MUMRO", "BLRRO", "HYDRO", "CCURO", "PATRO", "LKORO", "JPRRO", "INDRO", "MAHRO", "BBSRO", "GAURO", "CHIRO"}
        if not df_ops_sum_hub.empty and 'Origin RO' in df_ops_sum_hub.columns:
            ro_set.update(df_ops_sum_hub['Origin RO'].dropna().unique().tolist())
        if not df_ven_sum_hub.empty and 'Origin RO' in df_ven_sum_hub.columns:
            ro_set.update(df_ven_sum_hub['Origin RO'].dropna().unique().tolist())
        if not df_pay_base.empty and 'RO Name' in df_pay_base.columns:
            ro_set.update(df_pay_base['RO Name'].dropna().astype(str).str.upper().unique().tolist())
        if not df_cpk_raw_hub.empty and 'RO_Clean' in df_cpk_raw_hub.columns:
            ro_set.update(df_cpk_raw_hub['RO_Clean'].dropna().astype(str).str.upper().unique().tolist())
            
        ro_list_sorted = sorted([r for r in ro_set if r and r not in ['NAN', 'MISSING RO', 'UNKNOWN']])
        
        rc1, rc2, rc3 = st.columns([1, 1, 1.5])
        sel_ro_hub = rc1.selectbox("Select Regional Office (RO):", ro_list_sorted, index=ro_list_sorted.index("DELRO") if "DELRO" in ro_list_sorted else 0)
        ro_mode = rc2.selectbox("Report Mode:", ["All Modules (Full Master + Failures)", "Only Failures / Exceptions"])
        ro_emails_in = rc3.text_input("RO Recipient Email IDs (optional):", placeholder="e.g. rm.delro@trackon.in (or leave blank)", key="ro_mail_in")
        
        ro_ops_sum = sort_by_route_and_leg(df_ops_sum_hub[df_ops_sum_hub['Origin RO'].astype(str).str.upper() == sel_ro_hub].copy()) if not df_ops_sum_hub.empty else pd.DataFrame()
        ro_ops_raw = sort_by_route_and_leg(df_ops_raw_hub[df_ops_raw_hub['Origin RO'].astype(str).str.upper() == sel_ro_hub].copy()) if not df_ops_raw_hub.empty else pd.DataFrame()
        ro_ops_fail_raw = ro_ops_raw[ro_ops_raw['Remark'].astype(str).str.contains('Late|No Dep|Missing', case=False, na=False)].copy() if not ro_ops_raw.empty else pd.DataFrame()
        
        ro_ven_sum = sort_by_route_and_leg(df_ven_sum_hub[df_ven_sum_hub['Origin RO'].astype(str).str.upper() == sel_ro_hub].copy()) if not df_ven_sum_hub.empty else pd.DataFrame()
        ro_ven_raw = sort_by_route_and_leg(df_ven_raw_hub[df_ven_raw_hub['Origin RO'].astype(str).str.upper() == sel_ro_hub].copy()) if not df_ven_raw_hub.empty else pd.DataFrame()
        ro_ven_fail_raw = ro_ven_raw[ro_ven_raw['Remark with 15 min waiver'].astype(str).str.contains('Late|Missing', case=False, na=False)].copy() if not ro_ven_raw.empty else pd.DataFrame()
        
        ro_pay_raw = df_pay_base[df_pay_base['RO Name'].astype(str).str.strip().str.upper() == sel_ro_hub].copy() if not df_pay_base.empty else pd.DataFrame()
        ro_cpk_raw = df_cpk_raw_hub[df_cpk_raw_hub['RO_Clean'].astype(str).str.strip().str.upper() == sel_ro_hub].copy() if not df_cpk_raw_hub.empty else pd.DataFrame()
        ro_cpk_tables = build_cpk_tables_from_raw(ro_cpk_raw)
        
        k1, k2, k3, k4 = st.columns(4)
        k1.metric(f"{sel_ro_hub} Ops Trips", int(ro_ops_sum['Total_Trips'].sum()) if not ro_ops_sum.empty else 0)
        k2.metric(f"{sel_ro_hub} Ops Failures", len(ro_ops_fail_raw))
        k3.metric(f"{sel_ro_hub} Vendor Late Trips", len(ro_ven_fail_raw))
        k4.metric(f"{sel_ro_hub} Payment Records", len(ro_pay_raw))

        st.markdown(f'#### `{sel_ro_hub}` payment buckets · count and percentage')
        comm_payment_buckets = ['Payment Pending / Paid', 'Finance Pending / Hold', 'Draft', 'Cost Control Pending', 'Other']
        comm_payment_total = len(ro_pay_raw)
        comm_payment_row = {'RO': sel_ro_hub, 'Total Bills': comm_payment_total}
        for bucket in comm_payment_buckets:
            bucket_count = int(ro_pay_raw.get('Payment Group', pd.Series('', index=ro_pay_raw.index)).eq(bucket).sum())
            bucket_pct = bucket_count / comm_payment_total * 100 if comm_payment_total else 0
            comm_payment_row[bucket] = f'{bucket_count:,} · {bucket_pct:.1f}%'
        comm_payment_summary = pd.DataFrame([comm_payment_row])
        if not ro_pay_raw.empty:
            payment_event = st.dataframe(
                style_ui_dataframe(comm_payment_summary), use_container_width=True, hide_index=True,
                on_select='rerun', selection_mode='single-cell', key='comm_ro_payment_bucket_click'
            )
            payment_row_idx, payment_col = get_selected_cell_from_event(payment_event, comm_payment_summary)
            if payment_row_idx is not None:
                payment_detail = ro_pay_raw.copy()
                if payment_col in comm_payment_buckets:
                    payment_detail = payment_detail[payment_detail['Payment Group'].eq(payment_col)].copy()
                payment_compact = compact_detail_frame(payment_detail, 'pay_raw')
                st.markdown(f'Focused payment records · {payment_col if payment_col in comm_payment_buckets else "all buckets"} · {len(payment_compact):,}')
                render_centered_html_table(payment_compact, height=360)
                payment_excel = io.BytesIO()
                with pd.ExcelWriter(payment_excel, engine='xlsxwriter') as writer:
                    write_styled_sheet_to_excel(writer, comm_payment_summary, 'Payment_Summary', sheet_type='payment_summary')
                    write_styled_sheet_to_excel(writer, payment_compact, 'Focused_Payments', sheet_type='pay_raw')
                st.download_button(
                    '📥 Download focused payment records (formatted Excel)', data=payment_excel.getvalue(),
                    file_name=f'{sel_ro_hub}_Focused_Payment_Records.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    key='comm_ro_payment_download'
                )
            else:
                st.caption('Click a payment count or percentage to show matching invoices.')
        else:
            st.info(f'No payment records available for {sel_ro_hub}.')

        ro_excel_buf = io.BytesIO()
        with pd.ExcelWriter(ro_excel_buf, engine='xlsxwriter') as writer:
            write_styled_sheet_to_excel(writer, ro_ops_sum, 'Ops_Summary', sheet_type="ops_sum")
            write_styled_sheet_to_excel(writer, ro_ops_fail_raw, 'Ops_Failures_Raw', sheet_type="ops_raw")
            if "All Modules" in ro_mode:
                write_styled_sheet_to_excel(writer, ro_ops_raw, 'Ops_All_Raw', sheet_type="ops_raw")
            write_styled_sheet_to_excel(writer, ro_ven_sum, 'Vendor_Summary', sheet_type="ven_sum")
            write_styled_sheet_to_excel(writer, ro_ven_fail_raw, 'Vendor_Failures_Raw', sheet_type="ven_raw")
            if "All Modules" in ro_mode:
                write_styled_sheet_to_excel(writer, ro_ven_raw, 'Vendor_All_Raw', sheet_type="ven_raw")
                if not ro_cpk_tables['CPK_National_Zonal_Master'].empty:
                    write_styled_sheet_to_excel(writer, add_total_row_cpk_df(ro_cpk_tables['CPK_National_Zonal_Master']), 'CPK_Nat_Zonal', sheet_type="cpk")
                if not ro_cpk_tables['CPK_Feeder_Regional'].empty:
                    write_styled_sheet_to_excel(writer, add_total_row_cpk_df(ro_cpk_tables['CPK_Feeder_Regional']), 'CPK_Feeder_Reg', sheet_type="cpk")
                if not ro_cpk_tables['CPK_Coloader'].empty:
                    write_styled_sheet_to_excel(writer, add_total_row_cpk_df(ro_cpk_tables['CPK_Coloader']), 'CPK_Coloader', sheet_type="cpk")
                if not ro_cpk_raw.empty:
                    write_styled_sheet_to_excel(writer, ro_cpk_raw, 'CPK_Raw', sheet_type="cpk_raw")
                if not ro_pay_raw.empty:
                    write_styled_sheet_to_excel(writer, ro_pay_raw, 'Payment_Records', sheet_type="pay_raw")

        ro_subject = f"Trackon {sel_ro_hub} Regional Performance & Exception Report - {hub_dur_str}"
        ro_body = build_clean_email_message(
            recipient_title=f"{sel_ro_hub} Regional Team",
            duration_label=f"{sel_ro_hub} ({hub_dur_str})",
            ops_sum_df=ro_ops_sum,
            ven_sum_df=ro_ven_sum,
            pay_df=ro_pay_raw,
            cpk_df=ro_cpk_tables['CPK_National_Zonal_Master']
        )
        ro_gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&to={urllib.parse.quote(ro_emails_in.strip())}&su={urllib.parse.quote(ro_subject)}&body={urllib.parse.quote(ro_body)}&authuser=lh.fleetops@trackon.in"

        rb1, rb2 = st.columns(2)
        rb1.download_button(
            f"1️⃣ Download {sel_ro_hub} Complete Excel Report 📊",
            data=ro_excel_buf.getvalue(),
            file_name=f"{sel_ro_hub}_Master_Performance_Report_{get_ist_now():%d_%b_%Y}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary"
        )
        rb2.markdown(
            f'<a href="{ro_gmail_url}" target="_blank"><button style="background-color: #EF4444; color: white; padding: 10px; border: none; border-radius: 8px; width: 100%; cursor: pointer; font-weight: 600;">2️⃣ Send {sel_ro_hub} Mail in 1-Click (Gmail) ✉️</button></a>',
            unsafe_allow_html=True
        )

        st.markdown(f"#### Preview: `{sel_ro_hub}` Vendor Performance Summary")
        ro_ven_prev = clean_dataframe_for_excel(ro_ven_sum, sheet_type="ven_sum")
        render_summary_with_raw_drilldown(
            ro_ven_prev, ro_ven_raw, f'{sel_ro_hub} vendor performance', 'ven_raw', 'comm_ro_vendor_drilldown'
        )

        st.markdown(f"#### Preview: `{sel_ro_hub}` Operations Exception Summary")
        ro_ops_prev = clean_dataframe_for_excel(ro_ops_sum, sheet_type="ops_sum")
        render_summary_with_raw_drilldown(
            ro_ops_prev, ro_ops_raw, f'{sel_ro_hub} operations summary', 'ops_raw', 'comm_ro_ops_drilldown'
        )
        if not ro_cpk_tables.get('CPK_National_Zonal_UpDown', pd.DataFrame()).empty:
            st.markdown(f"#### Preview: `{sel_ro_hub}` National and Zonal Utilization")
            comm_util_summary = ro_cpk_tables['CPK_National_Zonal_UpDown'].copy()
            if 'Overall Util %' in comm_util_summary.columns:
                util_values = pd.to_numeric(comm_util_summary['Overall Util %'], errors='coerce')
                if util_values.dropna().le(1).all():
                    util_values = util_values * 100
                comm_util_summary['Overall Util %'] = util_values.map(lambda value: f'{value:.1f}%' if pd.notna(value) else '')
            render_summary_with_raw_drilldown(
                comm_util_summary, ro_cpk_raw,
                f'{sel_ro_hub} national-zonal utilization', 'cpk_raw', 'comm_ro_utilization_drilldown',
                match_columns=[('VendorRO', 'RO_Clean'), ('Route (UP/DOWN)', 'Final_Route'), ('Type', 'Final_Type')]
            )

# -------------------------------------------------------------
# E. CPK & UTILIZATION (100% Original Logic + Duration Filter)
# -------------------------------------------------------------
elif choice == "💰 Network Utilization":
    st.markdown("<h2>Network Utilization & CPK Dashboard</h2>", unsafe_allow_html=True)
    if 'CPK_National_Zonal_Master' in data and 'CPK_Raw_Data' in data:
        df_cpk_raw_full = data['CPK_Raw_Data'].copy()
        if not st.session_state.get('all_vendors', True):
            df_cpk_raw_full = filter_df_by_user_vendors(df_cpk_raw_full, 'VendorName')
            
        df_cpk_raw, is_cpk_date_filtered, dur_str_cpk = render_duration_selector(df_cpk_raw_full, 'Date', 'cpk_main')
        
        if is_cpk_date_filtered or not st.session_state.get('all_vendors', True):
            dynamic_cpk = build_cpk_tables_from_raw(df_cpk_raw)
            df_nz_master = dynamic_cpk['CPK_National_Zonal_Master']
            df_nz_updown = dynamic_cpk['CPK_National_Zonal_UpDown']
            df_fr_master = dynamic_cpk['CPK_Feeder_Regional']
            df_col_master = dynamic_cpk['CPK_Coloader']
        else:
            df_nz_master = data.get('CPK_National_Zonal_Master', pd.DataFrame()).copy()
            df_nz_updown = data.get('CPK_National_Zonal_UpDown', pd.DataFrame()).copy()
            df_fr_master = data.get('CPK_Feeder_Regional', pd.DataFrame()).copy()
            df_col_master = data.get('CPK_Coloader', pd.DataFrame()).copy()

        def render_cpk_view(df_master, view_type="Route", df_updown=None):
            if df_master is None or df_master.empty:
                st.info("No data available for this category.")
                return
            
            if PLOTLY_AVAILABLE:
                st.markdown(f"### 📊 Overview: {view_type}")
                col_chart1, col_chart2 = st.columns(2)
                
                with col_chart1:
                    if 'Zone' in df_master.columns:
                        fig1 = px.pie(
                            df_master, values='Total Trip Cost', names='Zone', 
                            title='Total Cost by Zone', hole=0.4, 
                            color_discrete_sequence=[selected_theme['accent'], selected_theme['blue']]
                        )
                        fig1.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color=selected_theme["text"], margin=dict(t=30, b=0, l=0, r=0))
                        st.plotly_chart(fig1, use_container_width=True)

                with col_chart2:
                    vendor_col = 'Vendor(s)' if 'Vendor(s)' in df_master.columns else ('VendorName' if 'VendorName' in df_master.columns else None)
                    if vendor_col:
                        top_vendors = df_master.groupby(vendor_col)['Total Trips'].sum().nlargest(5).reset_index()
                        fig2 = px.bar(
                            top_vendors, x=vendor_col, y='Total Trips', 
                            title='Top 5 Vendors by Volume', text_auto=True,
                            color_discrete_sequence=[selected_theme['blue']]
                        )
                        fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color=selected_theme["text"], margin=dict(t=30, b=0, l=0, r=0))
                        st.plotly_chart(fig2, use_container_width=True)
                st.markdown("---")

            col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
            all_zones = sorted(df_master['Zone'].dropna().unique().tolist()) if 'Zone' in df_master.columns else []
            zone_filter = col1.selectbox(f"Filter Zone ({view_type}):", ["ALL"] + all_zones, key=f"z_{view_type}")
            if zone_filter != "ALL":
                df_master = df_master[df_master['Zone'] == zone_filter]
                
            all_ros = sorted(df_master['VendorRO'].dropna().unique().tolist())
            ro_filter = col2.selectbox(f"Filter RO ({view_type}):", ["ALL"] + all_ros, key=f"r_{view_type}")
            if ro_filter != "ALL":
                df_master = df_master[df_master['VendorRO'] == ro_filter]

            if 'Type' in df_master.columns:
                all_types = sorted(df_master['Type'].dropna().unique().tolist())
                type_filter = col3.selectbox(f"Filter Type ({view_type}):", ["ALL"] + all_types, key=f"t_{view_type}")
                if type_filter != "ALL":
                    df_master = df_master[df_master['Type'] == type_filter]
                
            search_q = col4.text_input(f"🔍 Quick Search ({view_type}):", placeholder="Search...", key=f"s_{view_type}")
            if search_q:
                mask = df_master.astype(str).apply(lambda x: x.str.contains(search_q, case=False, regex=False, na=False)).any(axis=1)
                df_master = df_master[mask]

            m1, m2, m3 = st.columns(3)
            m1.metric("Total Trips", f"{int(df_master['Total Trips'].sum()):,}")
            avg_util = (df_master['Total Carried Wt'].sum() / df_master['Total Capacity'].sum() * 100) if df_master['Total Capacity'].sum() > 0 else 0
            m2.metric("Overall Utilization", f"{avg_util:.1f}%")
            avg_cpk = (df_master['Total Trip Cost'].sum() / df_master['Total Carried Wt'].sum()) if df_master['Total Carried Wt'].sum() > 0 else 0
            m3.metric("Overall CPK", f"₹ {avg_cpk:.2f}")

            util_values = pd.to_numeric(df_master.get('Overall Util %', pd.Series(dtype=float)), errors='coerce')
            low_util_count = int(util_values.lt(0.50).sum()) if not util_values.empty else 0
            high_util_count = int(util_values.ge(0.80).sum()) if not util_values.empty else 0
            utilization_insights = []
            if not util_values.empty:
                utilization_insights.append(
                    f"{low_util_count:,} of {len(util_values):,} visible records are below 50% utilization."
                )
                utilization_insights.append(
                    f"{high_util_count:,} visible records are at or above 80% utilization."
                )
            volume_col = get_col(df_master, ['Total Trips'])
            entity_candidates = {
                'Route': ['Route Pair', 'Route Path'],
                'Vehicle': ['Vehicle No'],
                'Coloader': ['Vendor(s)', 'VendorName']
            }.get(view_type, ['Route Pair', 'Vehicle No', 'Vendor(s)'])
            entity_col = get_col(df_master, entity_candidates)
            if volume_col and entity_col and not df_master.empty:
                volume_frame = df_master[[entity_col, volume_col]].copy()
                volume_frame[volume_col] = pd.to_numeric(volume_frame[volume_col], errors='coerce').fillna(0)
                volume_frame = volume_frame.groupby(entity_col, dropna=True)[volume_col].sum().sort_values(ascending=False)
                if not volume_frame.empty:
                    utilization_insights.append(
                        f"Highest volume: `{str(volume_frame.index[0]).replace('`', '')}` with {int(volume_frame.iloc[0]):,} trips."
                    )
            render_powerbi_insights(
                f'{view_type} Utilization Signals',
                [('Records in view', f'{len(df_master):,}'), ('Trips', f"{int(pd.to_numeric(df_master.get('Total Trips', pd.Series(0, index=df_master.index)), errors='coerce').fillna(0).sum()):,}"),
                 ('Below 50% utilization', f'{low_util_count:,}'), ('At least 80% utilization', f'{high_util_count:,}')],
                utilization_insights,
                period_note=f'Signals follow the selected {view_type.lower()} zone, RO, type, and search.'
            )

            df_cpk_view = df_master.sort_values(by='Overall Util %', ascending=True)
            disp_df = df_cpk_view.copy()
            
            if view_type == "Route":
                disp_df['RowKey'] = disp_df['VendorRO'].astype(str) + " || " + disp_df['Route Pair'].astype(str) + " | " + disp_df['Type'].astype(str)
            elif view_type == "Vehicle":
                disp_df['RowKey'] = disp_df['VendorRO'].astype(str) + " || " + disp_df['Vehicle No'].astype(str)
            else:
                disp_df['RowKey'] = disp_df['VendorRO'].astype(str) + " || " + disp_df['Vendor(s)'].astype(str) + " | " + disp_df['Vehicle No'].astype(str) + " | " + disp_df['Route'].astype(str)

            disp_df = add_total_row_cpk_df(disp_df)
            disp_df.insert(0, 'Select 👁️', False)
            
            ap_data = load_action_plans()
            mod_ap = ap_data.get(f"Network Utilization - {view_type}", {})
            disp_df['Action Plan ✍️'] = disp_df['RowKey'].map(mod_ap).fillna("")
            
            view_df = disp_df.drop(columns=['SortKey', 'Super_SortKey', 'RowKey', 'Zone'], errors='ignore')
            
            def highlight_cpk_util(val, col):
                if pd.isna(val) or val == '-': return ''
                if col == 'Overall Util %':
                    try:
                        pct = float(str(val).replace('%', '').strip())
                        if pct < 50: return 'color: #ff8a80; font-weight: bold;' 
                        elif pct < 80: return 'color: #ffe57f; font-weight: bold;'
                        else: return 'color: #b9f6ca; font-weight: bold;'
                    except: return ''
                elif col == 'Overall CPK':
                    return 'color: #60A5FA; font-weight: bold;'
                return ''

            styled_view = view_df.style
            for col in ['Overall Util %', 'Overall CPK']:
                if col in view_df.columns:
                    style_func = lambda x, c=col: highlight_cpk_util(x, c)
                    if hasattr(styled_view, 'map'):
                        styled_view = styled_view.map(style_func, subset=[col])
                    else:
                        styled_view = styled_view.applymap(style_func, subset=[col])

            disabled_cols = [c for c in view_df.columns if c not in ['Action Plan ✍️', 'Select 👁️']]
            editor_k = f"cpk_editor_{view_type}"
            
            edited_cpk = st.data_editor(
                styled_view,
                column_config={"Action Plan ✍️": st.column_config.TextColumn("Action Plan ✍️", width="large")},
                disabled=disabled_cols,
                use_container_width=True, 
                height=350, 
                key=editor_k
            )
            
            changes = False
            for idx, row in edited_cpk.iterrows():
                r_key = str(disp_df.loc[idx, 'RowKey'])
                if r_key == 'nan' or r_key == '-':
                    continue 
                new_val = str(row['Action Plan ✍️']).strip()
                old_val = str(mod_ap.get(r_key, "")).strip()
                if new_val != old_val:
                    if new_val: mod_ap[r_key] = new_val
                    else: mod_ap.pop(r_key, None)
                    changes = True
            if changes:
                ap_data[f"Network Utilization - {view_type}"] = mod_ap
                save_action_plans(ap_data)

            selected_rows = edited_cpk[edited_cpk['Select 👁️'] == True].index.tolist()

            if selected_rows:
                selected_idx = selected_rows[0]
                if selected_idx >= len(df_cpk_view):
                    st.warning("Please click a valid row, not the TOTAL row.")
                else:
                    if view_type == "Route":
                        selected_sortkey = df_cpk_view.iloc[selected_idx]['Route Pair']
                        st.markdown("---")
                        st.markdown(f"### 🔄 Up/Down Route Summary for `{selected_sortkey}`")
                        
                        if df_updown is not None and not df_updown.empty:
                            updown_filtered = df_updown[(df_updown['SortKey'] == selected_sortkey)].drop(columns=['SortKey', 'Zone'], errors='ignore').copy()
                            if 'Overall Util %' in updown_filtered.columns:
                                updown_filtered['Overall Util %'] = updown_filtered['Overall Util %'].apply(lambda x: f"{x*100:.2f}%" if isinstance(x, (int, float)) else x)
                            if 'Overall CPK' in updown_filtered.columns:
                                updown_filtered['Overall CPK'] = updown_filtered['Overall CPK'].apply(lambda x: f"₹{x:.2f}" if isinstance(x, (int, float)) else x)
                            render_centered_html_table(updown_filtered, height=340)
                            
                        st.markdown(f"### 📄 Raw Data for Route Pair `{selected_sortkey}`")
                        raw_trips = df_cpk_raw[(df_cpk_raw['SortKey'] == selected_sortkey)]

                    elif view_type == "Vehicle":
                        selected_ro_val = df_cpk_view.iloc[selected_idx]['VendorRO']
                        selected_vno = df_cpk_view.iloc[selected_idx]['Vehicle No']
                        raw_trips = df_cpk_raw[
                            (df_cpk_raw['RO_Clean'].astype(str).str.strip().str.upper() == str(selected_ro_val).strip().upper()) & 
                            (df_cpk_raw['Vehicle No'] == selected_vno)
                        ]
                        st.markdown("---")
                        st.markdown(f"### 📄 Raw Data for Vehicle `{selected_vno}`")
                    else:
                        selected_ro_val = df_cpk_view.iloc[selected_idx]['VendorRO']
                        selected_vno = df_cpk_view.iloc[selected_idx]['Vehicle No']
                        selected_vend = df_cpk_view.iloc[selected_idx]['Vendor(s)']
                        selected_rte = df_cpk_view.iloc[selected_idx]['Route']
                        raw_trips = df_cpk_raw[
                            (df_cpk_raw['RO_Clean'].astype(str).str.strip().str.upper() == str(selected_ro_val).strip().upper()) &
                            (df_cpk_raw['VendorName'] == selected_vend) &
                            (df_cpk_raw['Final_Route'] == selected_rte) &
                            (df_cpk_raw['Vehicle No'] == selected_vno)
                        ]
                        st.markdown("---")
                        st.markdown(f"### 📄 Raw Data for `{selected_vend}` (Vehicle: `{selected_vno}`) on `{selected_rte}`")

                    raw_cols = ['RO_Clean', 'Final_Route', 'Final_Type', 'VendorName', 'Vehicle No', 'Date', 'Cap', 'Wt', 'Trips', 'Cost']
                    raw_cols = [c for c in raw_cols if c in raw_trips.columns]
                    raw_trips = raw_trips[raw_cols]
                    
                    raw_trips_disp = raw_trips.copy()
                    if 'Cost' in raw_trips_disp.columns:
                        raw_trips_disp['Cost'] = raw_trips_disp['Cost'].apply(lambda v: f"₹{float(v):.2f}" if pd.notna(v) and str(v).replace('.', '', 1).replace('-', '', 1).isdigit() else v)
                    render_centered_html_table(raw_trips_disp, height=400)
            else:
                st.info("👆 Check the 'Select 👁️' box in the table above to view detailed split & raw data.")

        tab1, tab2, tab3 = st.tabs(["🛣️ National & Zonal (Routewise)", "🚚 Feeder & Regional (Vehiclewise)", "📦 Co-Loader (Vehiclewise)"])
        with tab1:
            render_cpk_view(df_nz_master, view_type="Route", df_updown=df_nz_updown)
        with tab2:
            render_cpk_view(df_fr_master, view_type="Vehicle")
        with tab3:
            render_cpk_view(df_col_master, view_type="Coloader")
    else:
        st.info("Please process CPK data first.")

# -------------------------------------------------------------
# F. TODAY'S CALL ACTION PLAN (MOM) (100% Legacy Lookup Restored)
# -------------------------------------------------------------
elif choice == "📝 Today's Call Action Plan":
    st.markdown("<h2>Today's Call Action Plan (MOM)</h2>", unsafe_allow_html=True)
    st.caption("Here you can view, export, and email all the action plans you saved across modules.")
    
    ap_data = load_action_plans()
    records = []
    
    sr_no = 1
    for mod, plans in ap_data.items():
        for ref, plan in plans.items():
            if " || " in ref:
                ro_part, ref_part = ref.split(" || ", 1)
            else:
                ro_part = "UNKNOWN"
                ref_part = ref
                
                try:
                    if mod == "Operations Summary" and 'Legwise_Route_Summary' in data:
                        pts = ref_part.split(" | ")
                        if len(pts) >= 2:
                            m = data['Legwise_Route_Summary'][(data['Legwise_Route_Summary']['Route Path'] == pts[0].strip()) & (data['Legwise_Route_Summary']['Legwise'] == pts[1].strip())]
                            if not m.empty: ro_part = str(m['Origin RO'].iloc[0])
                    elif mod == "Vendor Performance" and 'Vendor_Perf_Summary' in data:
                        pts = ref_part.split(" | ")
                        if len(pts) >= 3:
                            m = data['Vendor_Perf_Summary'][(data['Vendor_Perf_Summary']['VendorName'] == pts[0].strip()) & (data['Vendor_Perf_Summary']['Route Path'] == pts[1].strip()) & (data['Vendor_Perf_Summary']['Legwise'] == pts[2].strip())]
                            if not m.empty: ro_part = str(m['Origin RO'].iloc[0])
                    elif mod == "Payment Dashboard":
                        ro_part = ref_part.split(" | ")[0].strip()
                    elif mod == "Network Utilization - Route" and 'CPK_National_Zonal_Master' in data:
                        pts = ref_part.split(" | ")
                        if len(pts) >= 2:
                            m = data['CPK_National_Zonal_Master'][(data['CPK_National_Zonal_Master']['Route Pair'] == pts[0].strip()) & (data['CPK_National_Zonal_Master']['Type'] == pts[1].strip())]
                            if not m.empty: ro_part = str(m['VendorRO'].iloc[0])
                    elif mod == "Network Utilization - Vehicle" and 'CPK_Feeder_Regional' in data:
                        pts = ref_part.split(" | ")
                        if len(pts) >= 1:
                            m = data['CPK_Feeder_Regional'][data['CPK_Feeder_Regional']['Vehicle No'] == pts[0].strip()]
                            if not m.empty: ro_part = str(m['VendorRO'].iloc[0])
                    elif mod == "Network Utilization - Coloader" and 'CPK_Coloader' in data:
                        pts = ref_part.split(" | ")
                        if len(pts) >= 3:
                            m = data['CPK_Coloader'][(data['CPK_Coloader']['Vendor(s)'] == pts[0].strip()) & (data['CPK_Coloader']['Vehicle No'] == pts[1].strip()) & (data['CPK_Coloader']['Route'] == pts[2].strip())]
                            if not m.empty: ro_part = str(m['VendorRO'].iloc[0])
                except Exception:
                    pass
                
            records.append({
                "S.No.": sr_no,
                "Origin RO": ro_part,
                "Module Name": mod, 
                "Reference (Route/Vendor/Invoice)": ref_part, 
                "Action Plan Details": plan
            })
            sr_no += 1
            
    if not records:
        render_powerbi_insights(
            'Action Plan Coverage',
            [('Saved action plans', '0'), ('Regional offices', '0'), ('Modules represented', '0')],
            ['No saved plans are available yet; action plans entered in module tables will appear here.']
        )
        st.info("ℹ️ No action plans are saved yet. Add an Action Plan in another module to see it here.")
    else:
        df_ap = pd.DataFrame(records)
        
        all_ros_ap = sorted(df_ap['Origin RO'].unique().tolist())
        filter_ro_ap = st.selectbox("Filter Action Plans by Origin RO:", ["ALL"] + all_ros_ap)
        
        if filter_ro_ap != "ALL":
            df_ap = df_ap[df_ap['Origin RO'] == filter_ro_ap]
            df_ap['S.No.'] = range(1, len(df_ap) + 1)

        action_module_counts = df_ap['Module Name'].value_counts() if 'Module Name' in df_ap.columns else pd.Series(dtype=int)
        action_insights = []
        if not action_module_counts.empty:
            action_insights.append(
                f"Most represented module: `{str(action_module_counts.index[0]).replace('`', '')}` "
                f"with {int(action_module_counts.iloc[0]):,} action plans."
            )
        if filter_ro_ap != 'ALL':
            action_insights.append(f"The current view is scoped to `{filter_ro_ap}`.")
        render_powerbi_insights(
            'Action Plan Portfolio',
            [('Plans in view', f'{len(df_ap):,}'),
             ('Regional offices', f"{df_ap['Origin RO'].nunique():,}" if 'Origin RO' in df_ap.columns else '—'),
             ('Modules represented', f"{df_ap['Module Name'].nunique():,}" if 'Module Name' in df_ap.columns else '—')],
            action_insights,
            period_note='Counts reflect the selected RO filter and saved action plans.'
        )
        
        render_centered_html_table(df_ap, height=460)
        
        output_ap = io.BytesIO()
        with pd.ExcelWriter(output_ap, engine='xlsxwriter') as writer:
            write_styled_sheet_to_excel(writer, df_ap, 'Action_Plans', sheet_type="mom")
                
        email_body = "Namaste Team,\n\nPlease find the Action Plans discussed in today's call below:\n\n"
        current_mod = ""
        for _, r in df_ap.iterrows():
            if r['Module Name'] != current_mod:
                email_body += f"\n=== {r['Module Name'].upper()} ===\n"
                current_mod = r['Module Name']
            email_body += f"{r['S.No.']}. [{r['Origin RO']}] Ref: {r['Reference (Route/Vendor/Invoice)']}\n"
            email_body += f"   👉 Action: {r['Action Plan Details']}\n\n"
            
        email_body += "Thanks,\nAjay Singh Rawat\nFleet Operation Executive"
        
        st.markdown("---")
        st.markdown("### 📤 Export & Share")
        
        c1, c2 = st.columns(2)
        c1.download_button(
            "1️⃣ Download Action Plan (Excel) 📥", 
            data=output_ap.getvalue(), 
            file_name=f"Action_Plan_MOM_{datetime.datetime.now().strftime('%d%b%Y')}.xlsx", 
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
            use_container_width=True,
            type="primary"
        )
        
        encoded_msg = urllib.parse.quote(email_body)
        subject = urllib.parse.quote(f"Today's Call Action Plan (MOM) - {datetime.datetime.now().strftime('%d %b %Y')}")
        gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&su={subject}&body={encoded_msg}&authuser=lh.fleetops@trackon.in"
        
        c2.markdown(f'<a href="{gmail_url}" target="_blank"><button style="background-color: #EF4444; color: white; padding: 10px; border: none; border-radius: 8px; width: 100%; cursor: pointer; font-weight: 600;">2️⃣ Compose Email (Gmail) ✉️</button></a>', unsafe_allow_html=True)
        st.caption("Tip: Download ki hui Action Plan ki Excel sheet ko compose hote waqt attach kar dena.")

# -------------------------------------------------------------
# G. USER & ACCESS CONTROL MODULE (Admin IAM Management)
# -------------------------------------------------------------
elif choice == "🔐 User & Access Control":
    if st.session_state.get('username') != 'admin':
        st.error("🚫 Access Denied. Only Master Administrator can manage User IDs & Permissions.")
        st.stop()

    st.markdown("<h2>🔐 User ID & Access Control Center</h2>", unsafe_allow_html=True)
    st.caption("Create new User IDs, update passwords, assign specific modules, map selected vendors, or disable/remove access anytime.")

    users_db_live = load_users_db()

    # Gather all unique normalized vendor names from the dataset + existing user mappings
    known_vendors_set = set(data.get('Vendor_Options', []))
    for u_d in users_db_live.values():
        for v_item in u_d.get("vendors", []):
            known_vendors_set.add(normalize_vendor_name(v_item))
    known_vendors_list = sorted([v for v in known_vendors_set if v])
    active_user_count = sum(1 for info in users_db_live.values() if info.get('active', True))
    disabled_user_count = len(users_db_live) - active_user_count
    admin_user_count = sum(1 for info in users_db_live.values() if str(info.get('role', 'User')).casefold() == 'admin')
    restricted_user_count = sum(1 for info in users_db_live.values() if not info.get('all_vendors', True))
    user_insights = []
    if disabled_user_count:
        user_insights.append(f"{disabled_user_count:,} accounts are disabled and cannot sign in.")
    if restricted_user_count:
        user_insights.append(f"{restricted_user_count:,} accounts have vendor-restricted access.")
    active_non_admin = [
        info for info in users_db_live.values()
        if info.get('active', True) and str(info.get('role', 'User')).casefold() != 'admin'
    ]
    module_coverage = pd.Series(
        [module for info in active_non_admin for module in info.get('modules', []) if module in ALL_PORTAL_MODULES]
    ).value_counts()
    if not module_coverage.empty:
        user_insights.append(
            f"Most assigned module among active non-admin users: `{str(module_coverage.index[0]).replace('`', '')}` "
            f"({int(module_coverage.iloc[0]):,} assignments)."
        )
    render_powerbi_insights(
        'Access & Adoption Snapshot',
        [('Registered users', f'{len(users_db_live):,}'), ('Active users', f'{active_user_count:,}'),
         ('Disabled users', f'{disabled_user_count:,}'), ('Admin accounts', f'{admin_user_count:,}'),
         ('Vendor-restricted users', f'{restricted_user_count:,}'), ('Known vendors', f'{len(known_vendors_list):,}')],
        user_insights,
        period_note='Counts summarize account status, assigned modules, and vendor access settings.'
    )

    # --- 1. LIVE USERS OVERVIEW TABLE ---
    st.markdown("### 📋 Registered Users & Current Permissions")
    user_rows = []
    for u_id, u_info in users_db_live.items():
        v_disp = "🌍 ALL VENDORS" if u_info.get("all_vendors", True) else (", ".join(u_info.get("vendors", [])) or "None")
        m_disp = ", ".join(u_info.get("modules", []))
        user_rows.append({
            "User ID": u_id,
            "Display Name": u_info.get("label", u_id),
            "Password": "•••••• (Protected)" if u_id == "admin" and st.session_state.get("username") != "admin" else u_info.get("pass", ""),
            "Role": u_info.get("role", "User"),
            "Status": "🟢 Active" if u_info.get("active", True) else "🔴 Disabled",
            "Vendor Access": v_disp,
            "Allowed Modules": m_disp
        })
    df_users_overview = pd.DataFrame(user_rows)
    render_centered_html_table(df_users_overview, height=400)

    st.markdown("---")

    # --- 2. ADD NEW USER OR EDIT EXISTING USER ---
    col_u1, col_u2 = st.columns([1.4, 1])

    with col_u1:
        st.markdown("### ➕ Create New User / ✏️ Edit Existing User")
        existing_user_ids = [u for u in users_db_live.keys() if u != "admin"] if st.session_state.get("username") != "admin" else list(users_db_live.keys())
        mode_sel = st.selectbox(
            "Select Action / Target User:",
            ["➕ CREATE NEW USER"] + [f"✏️ Edit User: {uid} ({users_db_live[uid].get('label', uid)})" for uid in existing_user_ids],
            key="iam_mode_sel"
        )

        is_create_mode = mode_sel == "➕ CREATE NEW USER"
        if not is_create_mode:
            target_uid = mode_sel.split("✏️ Edit User: ")[1].split(" (")[0].strip()
            cur_u_obj = users_db_live.get(target_uid, {})
        else:
            target_uid = ""
            cur_u_obj = {
                "pass": "1234",
                "role": "Vendor",
                "label": "",
                "active": True,
                "all_vendors": False,
                "vendors": [],
                "modules": ["🚚 Vendor Performance"]
            }

        with st.form("user_iam_form"):
            fc1, fc2 = st.columns(2)
            if is_create_mode:
                form_uid = fc1.text_input("New User ID (Login Username)*", placeholder="e.g. FASTLANE or rahul_ops").strip()
            else:
                fc1.text_input("User ID (Login Username)", value=target_uid, disabled=True)
                form_uid = target_uid

            form_label = fc2.text_input("Display Name / Organization Label*", value=cur_u_obj.get("label", ""), placeholder="e.g. Fastlane Logistics / Rahul")

            fc3, fc4, fc5 = st.columns([1.2, 1, 0.8])
            form_pass = fc3.text_input("Login Password*", value=str(cur_u_obj.get("pass", "1234"))).strip()
            role_options = ["Vendor", "User", "Admin"]
            cur_role_idx = role_options.index(cur_u_obj.get("role", "Vendor")) if cur_u_obj.get("role", "Vendor") in role_options else 0
            form_role = fc4.selectbox("System Role*", role_options, index=cur_role_idx, disabled=(target_uid == "admin"))
            form_active = fc5.checkbox("Account Active 🟢", value=cur_u_obj.get("active", True), disabled=(target_uid == "admin"))

            st.markdown("#### 🧭 Module Access Permissions")
            default_mods = [m for m in cur_u_obj.get("modules", ["🚚 Vendor Performance"]) if m in ALL_PORTAL_MODULES]
            form_modules = st.multiselect(
                "Select Modules this User can see & open:",
                options=ALL_PORTAL_MODULES,
                default=ALL_PORTAL_MODULES if target_uid == "admin" else default_mods,
                disabled=(target_uid == "admin")
            )

            st.markdown("#### 🚚 Vendor Data Access Permissions")
            form_all_vendors = st.checkbox(
                "🌍 Grant ALL VENDORS Access (Uncheck to restrict user to selected vendors only)",
                value=cur_u_obj.get("all_vendors", False),
                disabled=(target_uid == "admin")
            )

            cur_mapped_vendors = [normalize_vendor_name(v) for v in cur_u_obj.get("vendors", []) if v]
            cur_mapped_vendors = list(dict.fromkeys([v for v in cur_mapped_vendors if v in known_vendors_list]))

            form_selected_vendors = st.multiselect(
                "Select Allowed Vendor(s) from Dataset:",
                options=known_vendors_list,
                default=cur_mapped_vendors
            )
            form_custom_vendors = st.text_input(
                "Or Add Custom Vendor Name(s) (comma separated, optional):",
                placeholder="e.g. FASTLANE LOGISTICS LLP, SHRI GANPATI"
            )

            save_iam_btn = st.form_submit_button("💾 Save / Update User Access", use_container_width=True, type="primary")

            if save_iam_btn:
                if not form_uid:
                    st.error("❌ Please enter a valid User ID.")
                elif not form_pass:
                    st.error("❌ Password cannot be empty.")
                elif not form_modules and target_uid != "admin":
                    st.error("❌ Please select at least one Module for this user.")
                else:
                    combined_vendors = list(form_selected_vendors)
                    if form_custom_vendors.strip():
                        for cv in form_custom_vendors.split(","):
                            norm_cv = normalize_vendor_name(cv)
                            if norm_cv and norm_cv not in combined_vendors:
                                combined_vendors.append(norm_cv)

                    if not form_all_vendors and not combined_vendors and target_uid != "admin":
                        st.warning("⚠️ You unchecked 'All Vendors Access' but did not select any vendor. Please select at least 1 vendor or enable All Vendors Access.")
                    else:
                        users_db_live[form_uid] = {
                            "pass": form_pass,
                            "role": "Admin" if form_uid == "admin" else form_role,
                            "label": form_label.strip() or form_uid,
                            "active": True if form_uid == "admin" else form_active,
                            "all_vendors": True if form_uid == "admin" else form_all_vendors,
                            "vendors": [] if (form_all_vendors or form_uid == "admin") else combined_vendors,
                            "modules": ALL_PORTAL_MODULES if form_uid == "admin" else form_modules
                        }
                        save_users_db(users_db_live)
                        st.success(f"✅ User `{form_uid}` permissions saved & activated immediately!")
                        st.rerun()

    with col_u2:
        st.markdown("### 🗑️ Quick Disable / Delete User")
        st.caption("Instantly block or permanently remove any user account (Master `admin` is protected).")
        removable_users = [u for u in users_db_live.keys() if u != "admin"]
        if not removable_users:
            st.info("No removable user accounts found.")
        else:
            del_uid = st.selectbox(
                "Select User ID to Manage:",
                removable_users,
                format_func=lambda u: f"{u} ({users_db_live[u].get('label', u)}) - {'Active 🟢' if users_db_live[u].get('active', True) else 'Disabled 🔴'}"
            )
            cur_status = users_db_live[del_uid].get("active", True)

            b_col1, b_col2 = st.columns(2)
            if cur_status:
                if b_col1.button(f"⏸️ Disable `{del_uid}`", use_container_width=True):
                    users_db_live[del_uid]["active"] = False
                    save_users_db(users_db_live)
                    st.warning(f"User `{del_uid}` has been disabled.")
                    st.rerun()
            else:
                if b_col1.button(f"▶️ Activate `{del_uid}`", use_container_width=True):
                    users_db_live[del_uid]["active"] = True
                    save_users_db(users_db_live)
                    st.success(f"User `{del_uid}` is now active!")
                    st.rerun()

            if b_col2.button(f"🗑️ Delete `{del_uid}`", use_container_width=True, type="secondary"):
                users_db_live.pop(del_uid, None)
                save_users_db(users_db_live)
                st.success(f"User `{del_uid}` deleted permanently.")
                st.rerun()

        st.markdown("---")
        st.markdown("#### 💡 Quick Guide:")
        st.markdown(
            "- **Vendor Access:** Jab tu kisi vendor ke liye ID banaye, toh `Grant ALL VENDORS Access` ko **Uncheck** rakhna aur niche dropdown se uska naam select kar lena.\n"
            "- **Team Member Access:** Agar kisi RO ya Ops executive ko 2-3 modules aur kuch specific vendors dene hain, toh `Select Modules` mein wo modules chunn le aur `Select Allowed Vendor(s)` mein unke vendors chunn le!"
        )
