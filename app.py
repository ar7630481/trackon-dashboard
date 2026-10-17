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
import tempfile
import logging
import io
import re

# Disable SettingWithCopyWarning for Pandas
warnings.filterwarnings('ignore')
pd.options.mode.chained_assignment = None

# ==========================================
# 1. PAGE SETUP (Professional VIP Dark Theme)
# ==========================================
st.set_page_config(
    page_title="Trackon Command Center",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# VIP Custom CSS for Enterprise Look
st.markdown("""
    <style>
    /* Global App Background */
    .stApp {
        background-color: #0B1120; /* Deep rich navy blue */
    }
    
    /* Sleek metric cards */
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        border: 1px solid #334155;
        padding: 5% 5% 5% 10%;
        border-radius: 12px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5), 0 4px 6px -2px rgba(0, 0, 0, 0.25);
    }
    
    /* DataFrame Headers */
    th {
        background-color: #1D4ED8 !important; /* Rich blue for table headers */
        color: white !important;
        font-weight: 600 !important;
        font-size: 14px !important;
    }
    
    /* Main Titles */
    h1, h2, h3 {
        color: #F8FAFC !important;
        font-weight: 700 !important;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #111827;
        border-right: 1px solid #1F2937;
    }
    
    /* Button Styling */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }
    </style>
""", unsafe_allow_html=True)


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
    "USERS_DB": os.path.join(DATA_DIR, "users_master.json")
}

ALL_PORTAL_MODULES = [
    "📊 Operations Summary",
    "🚚 Vendor Performance",
    "💳 Payment Dashboard",
    "📱 Communication Hub",
    "💰 Network Utilization",
    "📝 Today's Call Action Plan",
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
    mask = df[vendor_col].astype(str).apply(normalize_vendor_name).apply(
        lambda vn: any(av in vn or vn in av for av in allowed_norm if vn)
    )
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
        return float(val.split('%')[0].replace('₹', '').strip())
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

# ==========================================
# 3B. DYNAMIC SUMMARY CALCULATORS (With Vendor Grouping)
# ==========================================
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
    df_valid['OO_Cnt'] = df_valid['Remark'].apply(lambda x: 1 if 'Ontime Dep, Ontime Arr' in str(x) else 0)
    df_valid['LL_Cnt'] = df_valid['Remark'].apply(lambda x: 1 if 'Late Dep, Late Arr' in str(x) else 0)
    df_valid['LO_Cnt'] = df_valid['Remark'].apply(lambda x: 1 if 'Late Dep, Ontime Arr' in str(x) else 0)
    df_valid['OL_Cnt'] = df_valid['Remark'].apply(lambda x: 1 if 'Ontime Dep, Late Arr' in str(x) else 0)
    df_valid['Ontime_Dep_IT_Cnt'] = df_valid['Remark'].apply(lambda x: 1 if 'Ontime Dep, In-Transit' in str(x) else 0)
    df_valid['Late_Dep_IT_Cnt'] = df_valid['Remark'].apply(lambda x: 1 if 'Late Dep, In-Transit' in str(x) else 0)
    
    group_cols = ['Zone', 'LH Type', 'E2E_Pair', 'Origin RO', 'Route Path', 'Origin', 'Destination', 'Leg_Num', 'Legwise', 'Legs']
    existing_gcols = [c for c in group_cols if c in df_valid.columns]
    
    agg_dict = {
        'MasterCDNo': 'count',
        'OO_Cnt': 'sum',
        'LO_Cnt': 'sum',
        'OL_Cnt': 'sum',
        'LL_Cnt': 'sum',
        'Ontime_Dep_IT_Cnt': 'sum',
        'Late_Dep_IT_Cnt': 'sum'
    }
    summary = df_valid.groupby(existing_gcols).agg(agg_dict).reset_index()
    summary.rename(columns={'MasterCDNo': trip_col}, inplace=True)
    
    summary['Ontime Dep, Ontime Arr %'] = summary.apply(lambda r: format_pct_cnt(r['OO_Cnt'], r[trip_col]), axis=1)
    summary['Late Dep, Late Arr %'] = summary.apply(lambda r: format_pct_cnt(r['LL_Cnt'], r[trip_col]), axis=1)
    summary['Late Dep, Ontime Arr %'] = summary.apply(lambda r: format_pct_cnt(r['LO_Cnt'], r[trip_col]), axis=1)
    summary['Ontime Dep, Late Arr %'] = summary.apply(lambda r: format_pct_cnt(r['OL_Cnt'], r[trip_col]), axis=1)
    summary['Ontime Dep, In-Transit'] = summary.apply(lambda r: format_pct_cnt(r['Ontime_Dep_IT_Cnt'], r[trip_col]), axis=1)
    summary['Late Dep, In-Transit'] = summary.apply(lambda r: format_pct_cnt(r['Late_Dep_IT_Cnt'], r[trip_col]), axis=1)
    
    return sort_by_route_and_leg(summary)

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
        Transit_Cnt=('Remark with 15 min waiver', lambda x: (x == 'In-Transit').sum())
    ).reset_index()
    
    perf_sum['Ontime Arrival'] = perf_sum.apply(lambda r: format_pct_cnt(r['Ontime_Cnt'], r['Total_Trips']), axis=1)
    perf_sum['Late Arrival'] = perf_sum.apply(lambda r: format_pct_cnt(r['Late_Cnt'], r['Total_Trips']), axis=1)
    perf_sum['In-Transit'] = perf_sum.apply(lambda r: format_pct_cnt(r['Transit_Cnt'], r['Total_Trips']), axis=1)
    
    perf_sum = perf_sum.drop(columns=['Ontime_Cnt', 'Late_Cnt', 'Transit_Cnt'], errors='ignore')
    return sort_by_route_and_leg(perf_sum)

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
        lines.append(f"📌 PENDING INVOICES SUMMARY (Total Bills: {len(pay_df)})")
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
def clean_dataframe_for_excel(df_in, sheet_type="generic"):
    if df_in is None or df_in.empty:
        return pd.DataFrame()
    df = df_in.copy()
    
    if 'VendorName' in df.columns:
        df['VendorName'] = df['VendorName'].apply(normalize_vendor_name)
        
    df = sort_by_route_and_leg(df)
    
    cols_to_remove = [c for c in JUNK_EXCEL_COLS if c in df.columns]
    df.drop(columns=cols_to_remove, inplace=True, errors='ignore')
    
    if sheet_type == "ops_sum":
        preferred = [
            'Origin RO', 'Route Path', 'Legwise', 'Legs', 'Total_Trips',
            'Ontime Dep, Ontime Arr %', 'Late Dep, Late Arr %',
            'Ontime Dep, Late Arr %', 'Late Dep, Ontime Arr %',
            'Ontime Dep, In-Transit', 'Late Dep, In-Transit'
        ]
        pct_cols = [c for c in df.columns if '%' in c or 'In-Transit' in c]
        for c in pct_cols:
            df[c] = df[c].apply(format_ops_badge)
    elif sheet_type == "ops_raw":
        preferred = [
            'Origin RO', 'Route Path', 'MCD_StartDate', 'Legwise', 'Legs',
            'Remark', 'Scheduled Departure Time', 'Actual Departure Time',
            'Scheduled Arrival Time', 'Actual Arrival Time',
            'Scheduled Halting', 'Actual Halting', 'VendorName',
            'VehicleNo', 'MasterCDNo', 'RouteCode'
        ]
    elif sheet_type == "ven_sum":
        preferred = [
            'Origin RO', 'Route Path', 'Legwise', 'Legs', 'VendorName',
            'Total_Trips', 'Ontime Arrival', 'Late Arrival', 'In-Transit'
        ]
    elif sheet_type == "ven_raw":
        preferred = [
            'Origin RO', 'Route Path', 'Date', 'Legwise', 'Legs',
            'VendorName', 'VehicleNo', 'Actual Departure Time',
            'Actual Arrival Time', 'Given Driving Hours',
            'Actual Driving Hours', 'Delay Hours',
            'Remark with 15 min waiver', 'MasterCDNo', 'RouteCode'
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

    def ui_cell_color(val, col_name):
        if pd.isna(val):
            return ''
        s_val = str(val).strip()
        s_lower = s_val.lower()
        c_lower = str(col_name).lower()

        pct = parse_pct_from_str(s_val)
        if pct is not None and pct == 0:
            return 'color: #78909C;'

        if any(k in c_lower for k in ['ontime dep, ontime arr', 'ontime arrival']):
            if pct is not None and pct > 0:
                return 'background-color: rgba(56, 142, 60, 0.25); color: #b9f6ca; font-weight: bold;'
        elif any(k in c_lower for k in ['late dep, late arr', 'late arrival', 'late dep, in-transit']):
            if pct is not None and pct > 0:
                return 'background-color: rgba(211, 47, 47, 0.25); color: #ff8a80; font-weight: bold;'
        elif 'ontime dep, late arr' in c_lower or 'in-transit' in c_lower:
            if pct is not None and pct > 0:
                return 'background-color: rgba(245, 127, 23, 0.25); color: #ffe57f; font-weight: bold;'
        elif 'late dep, ontime arr' in c_lower:
            if pct is not None and pct > 0:
                return 'background-color: rgba(123, 31, 162, 0.25); color: #ea80fc; font-weight: bold;'

        elif 'remark' in c_lower:
            if 'ontime dep, ontime arr' in s_lower or 'ontime arrival' in s_lower:
                return 'background-color: rgba(56, 142, 60, 0.25); color: #b9f6ca; font-weight: bold;'
            elif any(k in s_lower for k in ['late dep, late arr', 'late arrival', 'no dep', 'missing']):
                return 'background-color: rgba(211, 47, 47, 0.25); color: #ff8a80; font-weight: bold;'
            elif 'ontime dep, late arr' in s_lower or 'in-transit' in s_lower:
                return 'background-color: rgba(245, 127, 23, 0.25); color: #ffe57f; font-weight: bold;'
            elif 'late dep, ontime arr' in s_lower:
                return 'background-color: rgba(123, 31, 162, 0.25); color: #ea80fc; font-weight: bold;'

        elif c_lower == 'delay hours' and s_val not in ['', '-', '0:00']:
            if not s_val.startswith('-'):
                try:
                    parts = s_val.split(':')
                    if (int(parts[0]) + int(parts[1]) / 60.0) > 0.25:
                        return 'background-color: rgba(211, 47, 47, 0.25); color: #ff8a80; font-weight: bold;'
                except:
                    pass
            return 'background-color: rgba(56, 142, 60, 0.2); color: #b9f6ca;'

        return ''

    styled = df_in.style
    for col in df_in.columns:
        if hasattr(styled, 'map'):
            styled = styled.map(lambda x, c=col: ui_cell_color(x, c), subset=[col])
        else:
            styled = styled.applymap(lambda x, c=col: ui_cell_color(x, c), subset=[col])
    return styled

def write_styled_sheet_to_excel(writer, df_in, sheet_name, sheet_type="generic"):
    df = clean_dataframe_for_excel(df_in, sheet_type=sheet_type)
    workbook = writer.book
    worksheet = workbook.add_worksheet(sheet_name)
    writer.sheets[sheet_name] = worksheet
    
    header_fmt = workbook.add_format({
        'bold': True, 'bg_color': '#1E3A8A', 'font_color': 'white',
        'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True
    })
    cell_fmt = workbook.add_format({'border': 1, 'valign': 'vcenter'})
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

    if df.empty:
        worksheet.write(0, 0, "No Data Available", header_fmt)
        return

    worksheet.set_row(0, 26)
    for col_idx, col_name in enumerate(df.columns):
        worksheet.write(0, col_idx, str(col_name), header_fmt)

    for row_idx, (_, row) in enumerate(df.iterrows(), start=1):
        is_total_row = any(str(row.get(k, '')).upper() in ['TOTAL', 'GRAND TOTAL'] for k in ['VendorRO', 'RO Name', 'Route Path', 'Origin RO'])
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
            
            chosen_fmt = total_row_fmt if is_total_row else cell_fmt
            
            if not is_total_row:
                if any(k in c_lower for k in ['ontime dep, ontime arr', 'ontime arrival']):
                    pct = parse_pct_from_str(s_val)
                    if pct is not None:
                        chosen_fmt = green_fmt if pct > 0 else muted_fmt
                elif any(k in c_lower for k in ['late dep, late arr', 'late arrival', 'late dep, in-transit']):
                    pct = parse_pct_from_str(s_val)
                    if pct is not None:
                        chosen_fmt = red_fmt if pct > 0 else muted_fmt
                elif 'ontime dep, late arr' in c_lower:
                    pct = parse_pct_from_str(s_val)
                    if pct is not None:
                        chosen_fmt = yellow_fmt if pct > 0 else muted_fmt
                elif 'late dep, ontime arr' in c_lower:
                    pct = parse_pct_from_str(s_val)
                    if pct is not None:
                        chosen_fmt = purple_fmt if pct > 0 else muted_fmt
                elif 'in-transit' in c_lower:
                    pct = parse_pct_from_str(s_val)
                    if pct is not None:
                        chosen_fmt = yellow_fmt if pct > 0 else muted_fmt
                elif 'remark' in c_lower:
                    if 'ontime dep, ontime arr' in s_lower or 'ontime arrival' in s_lower:
                        chosen_fmt = green_fmt
                    elif 'late dep, late arr' in s_lower or 'late arrival' in s_lower or 'no dep' in s_lower or 'missing' in s_lower:
                        chosen_fmt = red_fmt
                    elif 'ontime dep, late arr' in s_lower or 'in-transit' in s_lower:
                        chosen_fmt = yellow_fmt
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
                    if pct is not None:
                        chosen_fmt = red_fmt if pct < 50 else (yellow_fmt if pct < 80 else green_fmt)
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
        max_val_len = df[col].astype(str).map(len).max() if not df.empty else 10
        col_len = max(max_val_len, len(str(col))) + 3
        worksheet.set_column(i, i, min(col_len, 42))

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
@st.cache_data(show_spinner=False)
def get_processed_data_cached(file_timestamps):
    data_for_export = {}
    
    ro_zone_map = {}
    branch_to_ro_map = {
        "MUMH": "MUMRO", "BWNDLH": "MUMRO", "BWNDH": "MUMRO", "BKLH": "MUMRO",
        "DELAP": "DELRO", "PATH": "PATRO", "CCUH": "CCURO", "HOWDG": "CCURO",
        "BLRSH": "BLRRO", "HYDH": "HYDRO", "PNQHWH": "MAHRO", "PNQH": "MAHRO",
        "AMDH": "AMDRO", "BDQH": "AMDRO", "SRTKDH": "AMDRO", "ANKH": "AMDRO",
        "INDH": "INDRO", "BHOH": "INDRO", "JPRH": "JPRRO", "LKOH": "LKORO",
        "VNS1": "LKORO", "GAUH": "GAURO", "BBSH": "BBSRO", "CHIH": "CHIRO"
    }
    branch_to_zone_map = {}
    
    if os.path.exists(FILE_MAP["BRANCH_MASTER"]):
        try:
            xl_brn = pd.ExcelFile(FILE_MAP["BRANCH_MASTER"])
            sheet_to_read = "Sheet1" if "Sheet1" in xl_brn.sheet_names else xl_brn.sheet_names[0]
            df_brn_master = xl_brn.parse(sheet_to_read)
            df_brn_master.columns = df_brn_master.columns.astype(str).str.strip()
            
            brn_col_m = next((c for c in df_brn_master.columns if 'branchcode' in c.lower().replace(' ', '')), 'RPTBranchcode')
            ro_col_m = next((c for c in df_brn_master.columns if 'rptro' in c.lower().replace(' ', '')), 'RPTRO')
            zone_col_m = next((c for c in df_brn_master.columns if 'zone' in c.lower().replace(' ', '')), 'Zone')
            
            df_brn_master['BRN_CLEAN'] = df_brn_master[brn_col_m].astype(str).str.strip().str.upper()
            df_brn_master['RO_CLEAN'] = df_brn_master[ro_col_m].astype(str).str.strip().str.upper()
            df_brn_master['ZONE_CLEAN'] = df_brn_master[zone_col_m].astype(str).str.strip().str.upper()
            
            valid_brn = df_brn_master[df_brn_master['RO_CLEAN'].notna() & (~df_brn_master['RO_CLEAN'].isin(['', 'NAN', 'NONE']))]
            ro_zone_map = valid_brn.drop_duplicates(subset=['RO_CLEAN']).set_index('RO_CLEAN')['ZONE_CLEAN'].to_dict()
            
            for _, r_b in valid_brn.drop_duplicates(subset=['BRN_CLEAN']).iterrows():
                branch_to_ro_map[r_b['BRN_CLEAN']] = r_b['RO_CLEAN']
                branch_to_zone_map[r_b['BRN_CLEAN']] = r_b['ZONE_CLEAN']
        except Exception as e:
            logging.warning(f"Branch master read warning: {e}")

    # --- MODULE 0: PAYMENT DATA ---
    if os.path.exists(FILE_MAP["PAYMENT"]):
        df_pay = pd.read_excel(FILE_MAP["PAYMENT"])
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

    # --- MODULE 1: LEGWISE OPERATIONS & VENDOR PERFORMANCE ---
    if os.path.exists(FILE_MAP["LEGWISE"]) and os.path.exists(FILE_MAP["ROUTE_MASTER"]) and os.path.exists(FILE_MAP["BRANCH_MASTER"]):
        df_leg_all = pd.read_excel(FILE_MAP["LEGWISE"], sheet_name="Sheet1")
        df_rte = pd.read_excel(FILE_MAP["ROUTE_MASTER"], sheet_name="RoutePathReportModel")
        
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

        def resolve_origin_ro(row):
            for code in [row['Origin_Clean'], row['CD_FromBranch_Clean'], row['CD_ToBranch_Clean']]:
                if code in branch_to_ro_map and branch_to_ro_map[code]:
                    return branch_to_ro_map[code]
            return "DELRO"

        def resolve_zone(row):
            ro_val = row['Origin RO']
            if ro_val in ro_zone_map and ro_zone_map[ro_val]:
                return ro_zone_map[ro_val]
            for code in [row['Origin_Clean'], row['CD_FromBranch_Clean'], row['CD_ToBranch_Clean']]:
                if code in branch_to_zone_map and branch_to_zone_map[code]:
                    return branch_to_zone_map[code]
            return "NORTH"

        df_leg_all['Origin RO'] = df_leg_all.apply(resolve_origin_ro, axis=1)
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
        
        def assign_vendor_remark(row):
            if pd.isna(row['Actual Arrival Time']):
                return "In-Transit"
            if pd.isna(row['Delay Hours_Raw']):
                return "Missing Schedule"
            if row['Delay Hours_Raw'] <= 0.25:
                return "Ontime Arrival"
            return "Late Arrival"
            
        df_vperf['Remark with 15 min waiver'] = df_vperf.apply(assign_vendor_remark, axis=1)
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
        
        def calc_status(act, sch, mode):
            if pd.isna(act):
                return f"No {mode}" if mode == 'Dep' else "In-Transit"
            if pd.isna(sch):
                return "Missing Sch"
            if (act - sch).total_seconds() / 60 <= 15:
                return f"Ontime {mode}"
            return f"Late {mode}"
            
        df_leg['Dep_Status'] = df_leg.apply(lambda r: calc_status(r['Actual Departure Time'], r['Scheduled Departure Time'], 'Dep'), axis=1)
        df_leg['Arr_Status'] = df_leg.apply(lambda r: calc_status(r['Actual Arrival Time'], r['Scheduled Arrival Time'], 'Arr'), axis=1)
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

    # --- MODULE 2: CPK AND UTILIZATION ---
    if os.path.exists(FILE_MAP["CPK_UTIL"]) and os.path.exists(FILE_MAP["ROUTE_LOOKUP"]):
        try:
            df_raw = pd.read_excel(FILE_MAP["CPK_UTIL"], sheet_name='ContractVehicle_DetailReport')
        except:
            df_raw = pd.read_excel(FILE_MAP["CPK_UTIL"])
            
        df_lookup = pd.read_excel(FILE_MAP["ROUTE_LOOKUP"])
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

    return data_for_export

def process_all_data():
    progress = st.progress(0)
    status_text = st.empty()
    temp_output = None
    try:
        status_text.text("⚙️ Aggregating & Processing all files...")
        file_timestamps = {}
        for k, v in FILE_MAP.items():
            if os.path.exists(v):
                file_timestamps[k] = os.path.getmtime(v)
            
        data_for_export = get_processed_data_cached(file_timestamps)
        progress.progress(80)
        
        if not data_for_export:
            status_text.warning("No datasets were processed. Check the uploaded files.")
            return False
            
        status_text.text("⚙️ Saving Master Database...")
        with tempfile.NamedTemporaryFile(dir=DATA_DIR, suffix='.xlsx', delete=False) as tmp:
            temp_output = tmp.name
        with pd.ExcelWriter(temp_output, engine='xlsxwriter') as writer:
            for k, v in data_for_export.items():
                v.to_excel(writer, sheet_name=k, index=False)
        os.replace(temp_output, FILE_MAP["FINAL_OUTPUT"])
        
        progress.progress(90)
        status_text.text("⚙️ Generating Styled VIP Executive Report directly to disk...")
        generate_vip_executive_report_to_disk(data_for_export)

        st.session_state.pop('_dashboard_cache', None)
        st.session_state.pop('_download_version', None)
        progress.progress(100)
        status_text.success("✅ Data Processed & VIP Report Generated Successfully!")
        return True
    except Exception as e:
        logging.exception("Dashboard processing failed")
        status_text.error(f"Error during processing: {e}")
        st.exception(e)
        return False
    finally:
        if temp_output and os.path.exists(temp_output):
            os.remove(temp_output)
        gc.collect()

# ==========================================
# 6. SIDEBAR: ADMIN PANEL & RATE CORRECTIONS
# ==========================================
st.sidebar.markdown(f"### Welcome, **{st.session_state.get('user_label', st.session_state['role'])}**")
st.sidebar.caption(f"ID: `{st.session_state.get('username')}` | Role: `{st.session_state.get('role')}`")
if st.sidebar.button("Logout", key="logout_btn", use_container_width=True):
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
                
        get_processed_data_cached.clear()
        st.session_state.pop('_dashboard_cache', None)
        st.sidebar.success("Old Data Removed! You can paste new data now.")
        st.rerun()
        
    with st.sidebar.expander("📂 Upload Raw Files", expanded=False):
        f1 = st.file_uploader("1. Payment Data", type=['xlsx'])
        if save_file(f1, "PAYMENT"): st.success("Saved!")
        st.caption(f"Last updated: {get_file_time('PAYMENT')}")
        
        f2 = st.file_uploader("2. Legwise Report", type=['xlsx'])
        if save_file(f2, "LEGWISE"): st.success("Saved!")
        st.caption(f"Last updated: {get_file_time('LEGWISE')}")
        
        f3 = st.file_uploader("3. Scheduled Route Master", type=['xlsx'])
        if save_file(f3, "ROUTE_MASTER"): st.success("Saved!")
        st.caption(f"Last updated: {get_file_time('ROUTE_MASTER')}")
        
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
        get_processed_data_cached.clear()
        gc.collect()
        if process_all_data():
            st.session_state['_processing_success'] = True
            st.rerun()
        st.stop()

# ==========================================
# 7. DASHBOARD NAVIGATION & DATA LOADER
# ==========================================
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
    "📝 Today's Call Action Plan": (
        'Legwise_Route_Summary', 'Vendor_Perf_Summary',
        'CPK_National_Zonal_Master', 'CPK_Feeder_Regional', 'CPK_Coloader'
    ),
    "🔐 User & Access Control": ('Vendor_Perf_Raw', 'CPK_Raw_Data')
}

# Dynamically filter Navigation menu based on user's allowed_modules
user_allowed_mods = st.session_state.get('allowed_modules', [])
menu = [m for m in MENU_SHEETS.keys() if m in user_allowed_mods]

# LOCK "User & Access Control" explicitly to 'admin' username only
if st.session_state.get('username') == 'admin' and "🔐 User & Access Control" not in menu:
    menu.append("🔐 User & Access Control")
if not menu:
    menu = ["🚚 Vendor Performance"]

choice = st.sidebar.radio("Navigation:", menu)

def file_version(path):
    stat = os.stat(path)
    return (stat.st_mtime_ns, stat.st_size)

def load_dashboard_data(page):
    path = FILE_MAP["FINAL_OUTPUT"]
    if not os.path.exists(path):
        if page in ["📝 Today's Call Action Plan", "🔐 User & Access Control"]:
            return {"dummy": pd.DataFrame()}
        return {}
    cache_key = (file_version(path), page)
    cached = st.session_state.get('_dashboard_cache')
    if cached and cached[0] == cache_key:
        return cached[1]
    st.session_state.pop('_dashboard_cache', None)
    del cached
    gc.collect()
    try:
        with st.spinner("Loading selected dashboard..."):
            with pd.ExcelFile(path, engine='openpyxl') as workbook:
                data = {
                    name: workbook.parse(name)
                    for name in MENU_SHEETS[page]
                    if name in workbook.sheet_names
                }
        if 'Vendor_Perf_Raw' in data and not data['Vendor_Perf_Raw'].empty:
            data['Vendor_Perf_Raw']['VendorName'] = data['Vendor_Perf_Raw']['VendorName'].apply(normalize_vendor_name)
            data['Vendor_Perf_Summary'] = build_vendor_summary_from_raw(data['Vendor_Perf_Raw'])
        elif 'Vendor_Perf_Summary' in data and not data['Vendor_Perf_Summary'].empty:
            data['Vendor_Perf_Summary']['VendorName'] = data['Vendor_Perf_Summary']['VendorName'].apply(normalize_vendor_name)
        if 'Legwise_Processed_Data' in data and not data['Legwise_Processed_Data'].empty and 'VendorName' in data['Legwise_Processed_Data'].columns:
            data['Legwise_Processed_Data']['VendorName'] = data['Legwise_Processed_Data']['VendorName'].apply(normalize_vendor_name)

        if page in ["📝 Today's Call Action Plan", "🔐 User & Access Control"] and not data:
            data = {"dummy": pd.DataFrame()}
        st.session_state['_dashboard_cache'] = (cache_key, data)
        return data
    except Exception as exc:
        logging.exception("Cannot read dashboard workbook")
        st.error(f"Cannot read the processed Excel file: {exc}")
        if st.session_state['role'] == 'Admin':
            st.exception(exc)
        st.stop()

if st.session_state.pop('_processing_success', False):
    st.success("Data refreshed successfully. Your Executive Report is ready to download!")

# 📥 EXPORT REPORT - DIRECT FILE STREAM FROM DISK (Only for users with All Vendors Access)
if st.session_state.get('all_vendors', True) and os.path.exists(FILE_MAP["FINAL_OUTPUT"]) and os.path.exists(FILE_MAP["EXECUTIVE_REPORT"]):
    st.sidebar.markdown("---")
    st.sidebar.header("📥 Export Reports")
    try:
        with open(FILE_MAP["EXECUTIVE_REPORT"], "rb") as report_file:
            st.sidebar.download_button(
                "📄 Download VIP Executive Report",
                data=report_file,
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
if not data and choice != "🔐 User & Access Control":
    st.warning("No processed data for this page. Admin must upload the relevant files and process data.")
    st.stop()

try:
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# ==========================================
# 7B. DURATION (DATE RANGE) FILTER HELPER
# ==========================================
def render_duration_selector(df_raw, date_col_name, key_prefix):
    if df_raw is None or df_raw.empty or date_col_name not in df_raw.columns:
        return df_raw, False, "All Available Days"
    
    parsed_dates = pd.to_datetime(df_raw[date_col_name], dayfirst=True, errors='coerce')
    valid_dates = parsed_dates.dropna()
    if valid_dates.empty:
        return df_raw, False, "All Available Days"
        
    min_d = valid_dates.min().date()
    max_d = valid_dates.max().date()
    
    with st.container():
        dc1, dc2, dc3 = st.columns([1, 1, 2])
        start_d = dc1.date_input("📅 Start Date (MCD_StartDate):", value=min_d, min_value=min_d, max_value=max_d, key=f"{key_prefix}_sd")
        end_d = dc2.date_input("📅 End Date (MCD_StartDate):", value=max_d, min_value=min_d, max_value=max_d, key=f"{key_prefix}_ed")
        if start_d > end_d:
            start_d, end_d = end_d, start_d
        days_cnt = (end_d - start_d).days + 1
        dc3.info(f"⏱️ **Selected Duration:** `{start_d.strftime('%d %b %Y')}` to `{end_d.strftime('%d %b %Y')}` (**{days_cnt} Days**)")
        
    is_custom = (start_d != min_d) or (end_d != max_d)
    mask = (parsed_dates.dt.date >= start_d) & (parsed_dates.dt.date <= end_d)
    filtered_df = df_raw[mask].copy()
    dur_label = f"{start_d.strftime('%d %b %Y')} to {end_d.strftime('%d %b %Y')} ({days_cnt} Days)"
    return filtered_df, is_custom, dur_label


# -------------------------------------------------------------
# A. DAILY STANDUP (Operations Summary)
# -------------------------------------------------------------
if choice == "📊 Operations Summary":
    st.markdown("<h2>Operations Exception Summary</h2>", unsafe_allow_html=True)
    
    if 'Legwise_Route_Summary' in data and 'Legwise_Processed_Data' in data:
        df_raw_leg_full = data['Legwise_Processed_Data'].copy()
        if not st.session_state.get('all_vendors', True):
            df_raw_leg_full = filter_df_by_user_vendors(df_raw_leg_full, 'VendorName')
            
        df_raw_leg, is_date_filtered, dur_str_ops = render_duration_selector(df_raw_leg_full, 'MCD_StartDate', 'ops_main')
        
        if is_date_filtered or not st.session_state.get('all_vendors', True):
            df_leg_sum = build_ops_summary_from_raw(df_raw_leg)
        else:
            df_leg_sum = data['Legwise_Route_Summary'].copy()
            
        if df_leg_sum.empty:
            st.warning("No Operations trips found for your assigned access / selected date range.")
            st.stop()
            
        col1, col2, col3 = st.columns([1, 1, 2])
        
        all_zones = sorted(df_leg_sum['Zone'].dropna().unique().tolist()) if 'Zone' in df_leg_sum.columns else []
        selected_zone = col1.selectbox("Filter by Zone:", ["ALL"] + all_zones)
        if selected_zone != "ALL":
            df_leg_sum = df_leg_sum[df_leg_sum['Zone'] == selected_zone]
            df_raw_leg = df_raw_leg[df_raw_leg['Zone'] == selected_zone]
            
        all_ros = sorted(df_leg_sum['Origin RO'].dropna().unique().tolist())
        selected_ro = col2.selectbox("Filter by RO:", ["ALL"] + all_ros)
        if selected_ro != "ALL":
            df_leg_sum = df_leg_sum[df_leg_sum['Origin RO'] == selected_ro]
            df_raw_leg = df_raw_leg[df_raw_leg['Origin RO'] == selected_ro]

        search_q = col3.text_input("🔍 Quick Search:", placeholder="Search Route, Leg...")

        display_cols = [
            'Origin RO', 'Route Path', 'Legwise', 'Legs', 'Total_Trips', 
            'Ontime Dep, Ontime Arr %', 'Ontime Dep, Late Arr %', 
            'Late Dep, Late Arr %', 'Late Dep, Ontime Arr %'
        ]
        
        df_display = df_leg_sum[[c for c in display_cols if c in df_leg_sum.columns]].copy()
        df_display['RowKey'] = df_display['Origin RO'].astype(str) + " || " + df_display['Route Path'].astype(str) + " | " + df_display['Legwise'].astype(str)
        
        if search_q:
            mask = df_display.astype(str).apply(lambda x: x.str.contains(search_q, case=False, regex=False, na=False)).any(axis=1)
            df_display = df_display[mask]
            
        def extract_pct(x):
            if isinstance(x, str) and '%' in x:
                try: return float(x.split('%')[0].strip())
                except: return 0.0
            return 0.0
            
        if 'Late Dep, Late Arr %' in df_display.columns:
            df_display['SortKey_Temp'] = df_display['Late Dep, Late Arr %'].apply(extract_pct)
            df_display['Is_Single_Trip'] = df_display['Total_Trips'] <= 1
            df_display = df_display.sort_values(by=['Is_Single_Trip', 'SortKey_Temp', 'Route Path', 'Legwise'], ascending=[True, False, True, True]).drop(columns=['SortKey_Temp', 'Is_Single_Trip'])

        pct_cols = [c for c in df_display.columns if '%' in c and c != 'RowKey']
        for c in pct_cols:
            df_display[c] = df_display[c].apply(format_ops_badge)

        st.markdown("### Top Priority Routes Summary")
        
        df_display.insert(0, 'Select 👁️', False)
        ap_data = load_action_plans()
        mod_ap = ap_data.get("Operations Summary", {})
        df_display['Action Plan ✍️'] = df_display['RowKey'].map(mod_ap).fillna("")
        
        disp_cols = ['Select 👁️'] + [c for c in df_display.columns if c not in ['RowKey', 'Select 👁️']]
        styled_df = style_ui_dataframe(df_display[disp_cols])
            
        disabled_cols = [c for c in disp_cols if c not in ['Action Plan ✍️', 'Select 👁️']]
        
        edited_df = st.data_editor(
            styled_df,
            column_config={"Action Plan ✍️": st.column_config.TextColumn("Action Plan ✍️", width="large")},
            disabled=disabled_cols,
            use_container_width=True,
            height=350,
            key="ops_editor"
        )
        
        changes = False
        for idx, row in edited_df.iterrows():
            r_key = str(df_display.loc[idx, 'RowKey'])
            new_val = str(row['Action Plan ✍️']).strip()
            old_val = str(mod_ap.get(r_key, "")).strip()
            if new_val != old_val:
                if new_val: mod_ap[r_key] = new_val
                else: mod_ap.pop(r_key, None)
                changes = True
        if changes:
            ap_data["Operations Summary"] = mod_ap
            save_action_plans(ap_data)
        
        selected_rows = edited_df[edited_df['Select 👁️'] == True].index.tolist()

        if selected_rows:
            selected_idx = selected_rows[0]
            selected_route = df_display.loc[selected_idx, 'Route Path']
            selected_leg = df_display.loc[selected_idx, 'Legwise']
            
            st.markdown("---")
            st.markdown(f"### 📄 Details for `{selected_route}` - `{selected_leg}`")
            
            filtered_raw = df_raw_leg[(df_raw_leg['Route Path'] == selected_route) & (df_raw_leg['Legwise'] == selected_leg)].copy()
            filtered_raw = clean_dataframe_for_excel(filtered_raw, sheet_type="ops_raw")
            st.dataframe(style_ui_dataframe(filtered_raw), use_container_width=True)
        else:
            st.info("👆 Check the 'Select 👁️' box in the table above to view detailed trip records.")

# -------------------------------------------------------------
# B. VENDOR PERFORMANCE (With Dynamic User/Vendor Restriction)
# -------------------------------------------------------------
elif choice == "🚚 Vendor Performance":
    st.markdown("<h2>Vendor Performance (Routewise/Legwise)</h2>", unsafe_allow_html=True)
    
    if 'Vendor_Perf_Summary' in data and 'Vendor_Perf_Raw' in data:
        df_vperf_raw_full = data['Vendor_Perf_Raw'].copy()
        df_vperf_raw_full['VendorName'] = df_vperf_raw_full['VendorName'].apply(normalize_vendor_name)
        
        if not st.session_state.get('all_vendors', True):
            allowed_v = [normalize_vendor_name(v) for v in st.session_state.get('allowed_vendors', []) if v]
            allowed_v = list(dict.fromkeys([v for v in allowed_v if v]))
            st.info(f"🔒 **Restricted Vendor View:** Showing exclusive performance records for **{', '.join(allowed_v) if allowed_v else 'No Assigned Vendors'}**")
            df_vperf_raw_full = filter_df_by_user_vendors(df_vperf_raw_full, 'VendorName')

        df_vperf_raw, is_vdate_filtered, dur_str_ven = render_duration_selector(df_vperf_raw_full, 'Date', 'ven_main')
        df_vperf_sum = build_vendor_summary_from_raw(df_vperf_raw)
            
        if df_vperf_sum.empty:
            st.warning("No Vendor trips found for the selected criteria/duration.")
            st.stop()

        col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
        
        all_zones = sorted(df_vperf_sum['Zone'].dropna().unique().tolist()) if 'Zone' in df_vperf_sum.columns else []
        selected_zone = col1.selectbox("Filter by Zone:", ["ALL"] + all_zones)
        if selected_zone != "ALL":
            df_vperf_sum = df_vperf_sum[df_vperf_sum['Zone'] == selected_zone]
            df_vperf_raw = df_vperf_raw[df_vperf_raw['Zone'] == selected_zone]
            
        all_ros = sorted(df_vperf_sum['Origin RO'].dropna().unique().tolist())
        selected_ro = col2.selectbox("Filter by RO:", ["ALL"] + all_ros)
        if selected_ro != "ALL":
            df_vperf_sum = df_vperf_sum[df_vperf_sum['Origin RO'] == selected_ro]
            df_vperf_raw = df_vperf_raw[df_vperf_raw['Origin RO'] == selected_ro]
            
        all_vendors = sorted(df_vperf_sum['VendorName'].dropna().unique().tolist())
        selected_vendor_b = col3.selectbox("Filter by Vendor:", ["ALL"] + all_vendors)
        if selected_vendor_b != "ALL":
            df_vperf_sum = df_vperf_sum[df_vperf_sum['VendorName'] == selected_vendor_b]
            df_vperf_raw = df_vperf_raw[df_vperf_raw['VendorName'] == selected_vendor_b]

        search_q = col4.text_input("🔍 Quick Search:", placeholder="Search Route, Leg...")

        display_cols = ['Origin RO', 'Route Path', 'Legwise', 'Legs', 'VendorName', 'Total_Trips', 'Ontime Arrival', 'Late Arrival', 'In-Transit']
        df_display = df_vperf_sum[[c for c in display_cols if c in df_vperf_sum.columns]].copy()
        df_display = sort_by_route_and_leg(df_display)
        df_display['RowKey'] = df_display['Origin RO'].astype(str) + " || " + df_display['VendorName'].astype(str) + " | " + df_display['Route Path'].astype(str) + " | " + df_display['Legwise'].astype(str)
        
        if search_q:
            mask = df_display.astype(str).apply(lambda x: x.str.contains(search_q, case=False, regex=False, na=False)).any(axis=1)
            df_display = df_display[mask]

        dl_buf_v = io.BytesIO()
        with pd.ExcelWriter(dl_buf_v, engine='xlsxwriter') as writer:
            write_styled_sheet_to_excel(writer, df_vperf_sum, 'Vendor_Performance', sheet_type="ven_sum")
            write_styled_sheet_to_excel(writer, df_vperf_raw, 'Vendor_Raw_Data', sheet_type="ven_raw")
        st.download_button(
            "📥 Download Filtered Vendor Performance Report (Styled Excel)",
            data=dl_buf_v.getvalue(),
            file_name=f"Vendor_Performance_Report_{get_ist_now():%d_%b_%Y}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )

        st.markdown("### Vendor Arrival Performance Summary")
        
        df_display.insert(0, 'Select 👁️', False)
        ap_data = load_action_plans()
        mod_ap = ap_data.get("Vendor Performance", {})
        
        if st.session_state['role'] != 'Vendor':
            df_display['Action Plan ✍️'] = df_display['RowKey'].map(mod_ap).fillna("")
            disp_cols = ['Select 👁️'] + [c for c in df_display.columns if c not in ['RowKey', 'Select 👁️']]
            disabled_cols = [c for c in disp_cols if c not in ['Action Plan ✍️', 'Select 👁️']]
        else:
            disp_cols = ['Select 👁️'] + [c for c in df_display.columns if c not in ['RowKey', 'Select 👁️', 'Action Plan ✍️']]
            disabled_cols = [c for c in disp_cols if c != 'Select 👁️']
            
        styled_df = style_ui_dataframe(df_display[disp_cols])
        
        edited_df = st.data_editor(
            styled_df,
            column_config={"Action Plan ✍️": st.column_config.TextColumn("Action Plan ✍️", width="large")},
            disabled=disabled_cols,
            use_container_width=True,
            height=350,
            key="vend_editor"
        )
        
        if st.session_state['role'] != 'Vendor':
            changes = False
            for idx, row in edited_df.iterrows():
                r_key = str(df_display.loc[idx, 'RowKey'])
                new_val = str(row['Action Plan ✍️']).strip()
                old_val = str(mod_ap.get(r_key, "")).strip()
                if new_val != old_val:
                    if new_val: mod_ap[r_key] = new_val
                    else: mod_ap.pop(r_key, None)
                    changes = True
            if changes:
                ap_data["Vendor Performance"] = mod_ap
                save_action_plans(ap_data)

        selected_rows = edited_df[edited_df['Select 👁️'] == True].index.tolist()
        
        if selected_rows:
            selected_idx = selected_rows[0]
            selected_route = df_display.loc[selected_idx, 'Route Path']
            selected_leg = df_display.loc[selected_idx, 'Legwise']
            selected_vendor = df_display.loc[selected_idx, 'VendorName']
            
            st.markdown("---")
            st.markdown(f"### 📄 Raw Data for `{selected_vendor}` on `{selected_route}` - `{selected_leg}`")
            
            filtered_raw = df_vperf_raw[
                (df_vperf_raw['Route Path'] == selected_route) & 
                (df_vperf_raw['Legwise'] == selected_leg) &
                (df_vperf_raw['VendorName'] == selected_vendor)
            ].copy()
            filtered_raw_clean = clean_dataframe_for_excel(filtered_raw, sheet_type="ven_raw")
            
            output_raw = io.BytesIO()
            with pd.ExcelWriter(output_raw, engine='xlsxwriter') as writer:
                write_styled_sheet_to_excel(writer, filtered_raw, 'Raw_Data', sheet_type="ven_raw")
            st.download_button(
                "⬇️ Download This Leg Raw Data (Excel)",
                data=output_raw.getvalue(),
                file_name=f"Raw_Data_{selected_vendor}_{selected_leg}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            st.dataframe(style_ui_dataframe(filtered_raw_clean), use_container_width=True)
        else:
            st.info("👆 Check the 'Select 👁️' box in the table above to view detailed trip records.")

# -------------------------------------------------------------
# C. VENDOR PAYMENT DASHBOARD 
# -------------------------------------------------------------
elif choice == "💳 Payment Dashboard":
    st.markdown("<h2>Pending Payments Tracker</h2>", unsafe_allow_html=True)
    
    if 'Master_Database' in data:
        df_pay = data['Master_Database'].copy()
        if not st.session_state.get('all_vendors', True):
            df_pay = filter_df_by_user_vendors(df_pay, 'Vendor Name')
        
        if df_pay.empty:
            st.warning("No pending invoices found for your assigned vendor access.")
            st.stop()

        if PLOTLY_AVAILABLE and not df_pay.empty:
            st.markdown("### 📊 Payment Buckets Overview")
            pvt_chart = pd.pivot_table(df_pay, values='Invoice Id', index='Department Bucket', aggfunc='count').reset_index()
            fig_pay = px.pie(
                pvt_chart, values='Invoice Id', names='Department Bucket', hole=0.4,
                color_discrete_sequence=['#F87171', '#FBBF24', '#34D399', '#60A5FA', '#A78BFA']
            )
            fig_pay.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="white", height=350)
            st.plotly_chart(fig_pay, use_container_width=True)
            st.markdown("---")

        col1, col2 = st.columns([1, 2])
        all_zones = sorted(df_pay['Zone'].dropna().unique().tolist()) if 'Zone' in df_pay.columns else []
        selected_zone = col1.selectbox("Filter by Zone:", ["ALL"] + all_zones)
        if selected_zone != "ALL":
            df_pay = df_pay[df_pay['Zone'] == selected_zone]
        search_q = col2.text_input("🔍 Quick Search (Invoice, Vendor, RO...):")
            
        pvt = pd.pivot_table(df_pay, values='Invoice Id', index='RO Name', columns='Department Bucket', aggfunc='count', fill_value=0, margins=True, margins_name='Grand Total')
        cols_order = ["1. USER / DRAFT PENDING", "2. COST CONTROL PENDING", "3. FINANCE PENDING", "4. PAYMENT PENDING", "5. OTHER PENDING", "Grand Total"]
        existing_cols = [c for c in cols_order if c in pvt.columns]
        pvt = pvt.reindex(columns=existing_cols).reset_index()
        pvt['RowKey'] = pvt['RO Name'].astype(str) + " || " + pvt['RO Name'].astype(str)
        
        def color_payment_columns(val, col_name):
            if pd.isna(val) or val == 0: return ''
            if col_name == '1. USER / DRAFT PENDING': return 'background-color: rgba(211, 47, 47, 0.3); color: #ff8a80; font-weight: bold;' 
            elif col_name == '2. COST CONTROL PENDING': return 'background-color: rgba(245, 127, 23, 0.3); color: #ffe57f; font-weight: bold;'
            elif col_name == '3. FINANCE PENDING': return 'background-color: rgba(245, 127, 23, 0.1); color: #ffb74d; font-weight: bold;'
            return ''

        st.markdown("### RO-Wise Summary")
        
        pvt.insert(0, 'Select 👁️', False)
        ap_data = load_action_plans()
        mod_ap = ap_data.get("Payment Dashboard", {})
        pvt['Action Plan ✍️'] = pvt['RowKey'].map(mod_ap).fillna("")
        
        disp_cols = ['Select 👁️'] + [c for c in pvt.columns if c not in ['RowKey', 'Select 👁️']]
        styled_pvt = pvt[disp_cols].style
        for col in existing_cols:
            styled_pvt = styled_pvt.map(lambda x, c=col: color_payment_columns(x, c), subset=[col])
            
        disabled_cols = [c for c in disp_cols if c not in ['Action Plan ✍️', 'Select 👁️']]
        
        edited_pvt = st.data_editor(
            styled_pvt,
            column_config={"Action Plan ✍️": st.column_config.TextColumn("Action Plan ✍️", width="large")},
            disabled=disabled_cols,
            use_container_width=True,
            key="pay_editor"
        )
        
        changes = False
        for idx, row in edited_pvt.iterrows():
            r_key = str(pvt.loc[idx, 'RowKey'])
            new_val = str(row['Action Plan ✍️']).strip()
            old_val = str(mod_ap.get(r_key, "")).strip()
            if new_val != old_val:
                if new_val: mod_ap[r_key] = new_val
                else: mod_ap.pop(r_key, None)
                changes = True
        if changes:
            ap_data["Payment Dashboard"] = mod_ap
            save_action_plans(ap_data)
        
        selected_rows = edited_pvt[edited_pvt['Select 👁️'] == True].index.tolist()

        if selected_rows:
            selected_idx = selected_rows[0]
            sel_pay_ro = pvt.loc[selected_idx, 'RO Name']
            
            st.markdown("---")
            st.markdown(f"### 📄 Detailed Invoices for `{sel_pay_ro}`")
            
            sel_bucket = st.selectbox("Filter Pending Status:", existing_cols[:-1])
            
            if sel_pay_ro == 'Grand Total':
                filtered_pay = df_pay[df_pay['Department Bucket'] == sel_bucket].copy()
            else:
                filtered_pay = df_pay[(df_pay['RO Name'] == sel_pay_ro) & (df_pay['Department Bucket'] == sel_bucket)].copy()
                
            if search_q:
                mask = filtered_pay.astype(str).apply(lambda x: x.str.contains(search_q, case=False, regex=False, na=False)).any(axis=1)
                filtered_pay = filtered_pay[mask]
                
            pay_order = ['Invoice Id', 'RO Name', 'Vendor Name', 'Amount', 'Status', 'Pending With', 'Days Pending', 'Aging Bucket', 'Revert Remarks']
            final_pay_cols = [c for c in pay_order if c in filtered_pay.columns]
            leftovers_pay = [c for c in filtered_pay.columns if c not in final_pay_cols and c not in ['Bill Uploader', 'Zone']]
            if 'Bill Uploader' in filtered_pay.columns:
                leftovers_pay.append('Bill Uploader') 
            filtered_pay = filtered_pay[final_pay_cols + leftovers_pay]
            if 'Amount' in filtered_pay.columns:
                filtered_pay = filtered_pay.sort_values(by='Amount', ascending=False)
                
            st.dataframe(filtered_pay, use_container_width=True)
        else:
            st.info("👆 Check the 'Select 👁️' box in the table above to view specific invoices.")

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
        
    df_pay_base = data.get('Master_Database', pd.DataFrame()).copy()
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
        st.dataframe(style_ui_dataframe(ven_prev_df), use_container_width=True, hide_index=True)
        
        st.markdown("#### Preview: Current Ops Performance (Full Route)")
        ops_prev_df = clean_dataframe_for_excel(nat_ops_sum, sheet_type="ops_sum")
        st.dataframe(style_ui_dataframe(ops_prev_df), use_container_width=True, hide_index=True)

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
                st.dataframe(style_ui_dataframe(ind_ven_prev), use_container_width=True, hide_index=True)

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
        k4.metric(f"{sel_ro_hub} Pending Bills", len(ro_pay_raw))

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
                    write_styled_sheet_to_excel(writer, ro_pay_raw, 'Payment_Pending_Raw', sheet_type="pay_raw")

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
        st.dataframe(style_ui_dataframe(ro_ven_prev), use_container_width=True, hide_index=True)

        st.markdown(f"#### Preview: `{sel_ro_hub}` Operations Exception Summary")
        ro_ops_prev = clean_dataframe_for_excel(ro_ops_sum, sheet_type="ops_sum")
        st.dataframe(style_ui_dataframe(ro_ops_prev), use_container_width=True, hide_index=True)

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
                            color_discrete_sequence=px.colors.sequential.Teal
                        )
                        fig1.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="white", margin=dict(t=30, b=0, l=0, r=0))
                        st.plotly_chart(fig1, use_container_width=True)

                with col_chart2:
                    vendor_col = 'Vendor(s)' if 'Vendor(s)' in df_master.columns else ('VendorName' if 'VendorName' in df_master.columns else None)
                    if vendor_col:
                        top_vendors = df_master.groupby(vendor_col)['Total Trips'].sum().nlargest(5).reset_index()
                        fig2 = px.bar(
                            top_vendors, x=vendor_col, y='Total Trips', 
                            title='Top 5 Vendors by Volume', text_auto=True,
                            color_discrete_sequence=['#3B82F6']
                        )
                        fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="white", margin=dict(t=30, b=0, l=0, r=0))
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
                    styled_view = styled_view.map(lambda x, c=col: highlight_cpk_util(x, c), subset=[col])

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
                            updown_filtered = df_updown[(df_updown['SortKey'] == selected_sortkey)].copy()
                            updown_styled = updown_filtered.drop(columns=['SortKey', 'Zone'], errors='ignore').style
                            if 'Overall Util %' in updown_filtered.columns:
                                updown_styled = updown_styled.format({'Overall Util %': lambda x: f"{x*100:.2f}%" if isinstance(x, (int, float)) else x})
                            if 'Overall CPK' in updown_filtered.columns:
                                updown_styled = updown_styled.format({'Overall CPK': lambda x: f"₹{x:.2f}" if isinstance(x, (int, float)) else x})
                            st.dataframe(updown_styled, use_container_width=True)
                            
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
                    
                    styled_raw_trips = raw_trips.style
                    if 'Cost' in raw_trips.columns:
                        def format_cost(val):
                            try: return f"₹{float(val):.2f}"
                            except: return val
                        if hasattr(styled_raw_trips, 'format'):
                            styled_raw_trips = styled_raw_trips.format({'Cost': format_cost})
                    
                    st.dataframe(styled_raw_trips, use_container_width=True)
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
        st.info("❌ Koi Action Plan save nahi hua hai. Dusre modules mein jakar tables mein apna 'Action Plan' type karein!")
    else:
        df_ap = pd.DataFrame(records)
        
        all_ros_ap = sorted(df_ap['Origin RO'].unique().tolist())
        filter_ro_ap = st.selectbox("Filter Action Plans by Origin RO:", ["ALL"] + all_ros_ap)
        
        if filter_ro_ap != "ALL":
            df_ap = df_ap[df_ap['Origin RO'] == filter_ro_ap]
            df_ap['S.No.'] = range(1, len(df_ap) + 1)
        
        st.dataframe(df_ap, use_container_width=True, hide_index=True)
        
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
    known_vendors_set = set()
    if 'Vendor_Perf_Raw' in data and not data['Vendor_Perf_Raw'].empty and 'VendorName' in data['Vendor_Perf_Raw'].columns:
        known_vendors_set.update(data['Vendor_Perf_Raw']['VendorName'].dropna().apply(normalize_vendor_name).unique().tolist())
    if 'CPK_Raw_Data' in data and not data['CPK_Raw_Data'].empty and 'VendorName' in data['CPK_Raw_Data'].columns:
        known_vendors_set.update(data['CPK_Raw_Data']['VendorName'].dropna().apply(normalize_vendor_name).unique().tolist())
    for u_d in users_db_live.values():
        for v_item in u_d.get("vendors", []):
            known_vendors_set.add(normalize_vendor_name(v_item))
    known_vendors_list = sorted([v for v in known_vendors_set if v])

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
    st.dataframe(df_users_overview, use_container_width=True, hide_index=True)

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
