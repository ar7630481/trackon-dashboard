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

# Disable SettingWithCopyWarning for Pandas
warnings.filterwarnings('ignore')
pd.options.mode.chained_assignment = None

# ==========================================
# 1. PAGE SETUP
# ==========================================
st.set_page_config(page_title="Trackon Command Center", page_icon="🚀", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .stApp { background-color: #0B1120; }
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        border: 1px solid #334155;
        padding: 5% 5% 5% 10%;
        border-radius: 12px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5), 0 4px 6px -2px rgba(0, 0, 0, 0.25);
    }
    th { background-color: #1D4ED8 !important; color: white !important; font-weight: 600 !important; font-size: 14px !important; }
    h1, h2, h3 { color: #F8FAFC !important; font-weight: 700 !important; }
    [data-testid="stSidebar"] { background-color: #111827; border-right: 1px solid #1F2937; }
    .stButton>button { border-radius: 8px; font-weight: 600; transition: all 0.3s ease; }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
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
    "CPK_UTIL": os.path.join(DATA_DIR, "cpk_util.xlsx"),
    "ROUTE_LOOKUP": os.path.join(DATA_DIR, "route_lookup.xlsx"),
    "FINAL_OUTPUT": os.path.join(DATA_DIR, "Auto_Generated_Monitoring_Data.xlsx"),
    "EXECUTIVE_REPORT": os.path.join(DATA_DIR, "Trackon_VIP_Executive_Report.xlsx"),
    "RATE_CORRECTIONS": os.path.join(DATA_DIR, "rate_corrections.json"),
    "VENDOR_MASTER": os.path.join(DATA_DIR, "vendor_master.json"),
    "ACTION_PLANS": os.path.join(DATA_DIR, "action_plans.json") 
}

def get_ist_now():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)

# ==========================================
# 2. AUTHENTICATION
# ==========================================
USERS = {
    "user": {"pass": "5272", "role": "User", "vendors": []},
    "admin": {"pass": "9211213", "role": "Admin", "vendors": []},
    "admin2": {"pass": "1234", "role": "Admin", "vendors": []},
    "EWL": {"pass": "1234", "role": "Vendor", "vendors": ["E WHEELS AND LOGISTICS", "AAGFE8904K-E WHEELS AND LOGISTICS"]},
    "MRT": {"pass": "1234", "role": "Vendor", "vendors": ["MEHTAROAD INDIA TRANSPORT PRIVATE LIMITED", "MEHTAROAD"]},
    "vandna": {"pass": "1234", "role": "Vendor", "vendors": ["VANDNA MOTORS", "AAOFV8863G-VANDNA MOTORS"]},
    "TEJAS": {"pass": "1234", "role": "Vendor", "vendors": ["TEJAS CARGO INDIA PVT LTD", "TEJAS"]}
}

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'role' not in st.session_state: st.session_state['role'] = None

if not st.session_state['logged_in']:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: #60A5FA; font-size: 3rem;'>🚀 Trackon Command Center</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #94A3B8; font-weight: 400;'>Enterprise Logistics & Fleet Operations Portal</h3>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        with st.form("login_form"):
            st.markdown("#### 🔒 Secure Access")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Authenticate", use_container_width=True)
            
            if submit:
                if username in USERS and USERS[username]["pass"] == password:
                    st.session_state['logged_in'] = True
                    st.session_state['role'] = USERS[username]["role"]
                    st.session_state['vendors'] = USERS[username]["vendors"]
                    st.rerun()
                else:
                    st.error("❌ Invalid Credentials. Access Denied.")
    st.stop()

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
def save_file(uploaded_file, key):
    if uploaded_file is None: return False
    buffer = uploaded_file.getbuffer()
    digest = hashlib.sha256(buffer).hexdigest()
    state_key = f"saved_upload_{key}"
    path = FILE_MAP[key]
    if st.session_state.get(state_key) == digest and os.path.exists(path): return False
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(dir=DATA_DIR, suffix='.xlsx', delete=False) as f:
            temp_path = f.name
            f.write(buffer)
        os.replace(temp_path, path)
        st.session_state[state_key] = digest
        return True
    except: return False
    finally:
        if temp_path and os.path.exists(temp_path): os.remove(temp_path)

def get_col(df, possible_names):
    col_map = {str(c).replace(' ', '').replace('_', '').lower(): c for c in df.columns}
    for n in possible_names:
        clean_n = n.replace(' ', '').replace('_', '').lower()
        if clean_n in col_map: return col_map[clean_n]
    return None

def extract_orig_dest(route_str):
    s = str(route_str).upper()
    parts = s.replace(' TO ', '-').split('-')
    if len(parts) >= 2: return parts[0].strip(), parts[-1].strip()
    return s, s

def get_route_pair(route_str):
    o, d = extract_orig_dest(route_str)
    return f"{min(o, d)}-{max(o, d)}"

def time_to_hrs(t):
    if pd.isna(t): return np.nan
    t_str = str(t).strip()
    if t_str.lower() in ['', 'nan', 'nat']: return np.nan
    if hasattr(t, 'hour'): return t.hour + t.minute / 60.0
    if ':' in t_str:
        parts = t_str.split(':')
        if len(parts) >= 2:
            try: return float(parts[0]) + float(parts[1])/60.0
            except: return np.nan
    try: return float(t_str)
    except: return np.nan

def get_day_offset(day_val):
    try:
        if pd.isna(day_val): return np.nan
        return float(day_val) * 24
    except: return np.nan

def format_pct_cnt(count, total):
    if total == 0 or pd.isna(total): return "0.0% (0)"
    pct = (count / total) * 100
    return f"{pct:.1f}% ({int(count)})"

def format_hrs_safe(hrs):
    if pd.isna(hrs): return ""
    sign = "-" if hrs < 0 else ""
    hrs = abs(hrs)
    h = int(hrs)
    m = int(round((hrs - h) * 60))
    if m == 60: h += 1; m = 0
    return f"{sign}{h}:{m:02d}"

def load_action_plans():
    if os.path.exists(FILE_MAP["ACTION_PLANS"]):
        try:
            with open(FILE_MAP["ACTION_PLANS"], 'r') as f: return json.load(f)
        except: return {}
    return {}

def save_action_plans(data):
    with open(FILE_MAP["ACTION_PLANS"], 'w') as f: json.dump(data, f)

# -------------------------------------------------------------
# DYNAMIC SUMMARY GENERATORS
# -------------------------------------------------------------
def generate_ops_summary(df_valid):
    if df_valid.empty: return pd.DataFrame()
    trip_col = 'Total_Trips'
    df_valid['OO_Cnt'] = df_valid['Remark'].apply(lambda x: 1 if 'Ontime Dep, Ontime Arr' in str(x) else 0)
    df_valid['LL_Cnt'] = df_valid['Remark'].apply(lambda x: 1 if 'Late Dep, Late Arr' in str(x) else 0)
    df_valid['LO_Cnt'] = df_valid['Remark'].apply(lambda x: 1 if 'Late Dep, Ontime Arr' in str(x) else 0)
    df_valid['OL_Cnt'] = df_valid['Remark'].apply(lambda x: 1 if 'Ontime Dep, Late Arr' in str(x) else 0)
    df_valid['Ontime_Dep_IT_Cnt'] = df_valid['Remark'].apply(lambda x: 1 if 'Ontime Dep, In-Transit' in str(x) else 0)
    df_valid['Late_Dep_IT_Cnt'] = df_valid['Remark'].apply(lambda x: 1 if 'Late Dep, In-Transit' in str(x) else 0)
    
    agg_dict = {'MasterCDNo': 'count', 'OO_Cnt': 'sum', 'LO_Cnt': 'sum', 'OL_Cnt': 'sum', 'LL_Cnt': 'sum', 'Ontime_Dep_IT_Cnt': 'sum', 'Late_Dep_IT_Cnt': 'sum'}
    summary = df_valid.groupby(['Zone', 'LH Type', 'E2E_Pair', 'Origin RO', 'Route Path', 'Origin', 'Destination', 'Leg_Num', 'Legwise', 'Legs']).agg(agg_dict).reset_index()
    summary.rename(columns={'MasterCDNo': trip_col}, inplace=True)
    
    summary['Ontime Dep, Ontime Arr %'] = summary.apply(lambda r: format_pct_cnt(r['OO_Cnt'], r[trip_col]), axis=1)
    summary['Late Dep, Late Arr %'] = summary.apply(lambda r: format_pct_cnt(r['LL_Cnt'], r[trip_col]), axis=1)
    summary['Late Dep, Ontime Arr %'] = summary.apply(lambda r: format_pct_cnt(r['LO_Cnt'], r[trip_col]), axis=1)
    summary['Ontime Dep, Late Arr %'] = summary.apply(lambda r: format_pct_cnt(r['OL_Cnt'], r[trip_col]), axis=1)
    summary['Ontime Dep, In-Transit'] = summary.apply(lambda r: format_pct_cnt(r['Ontime_Dep_IT_Cnt'], r[trip_col]), axis=1)
    summary['Late Dep, In-Transit'] = summary.apply(lambda r: format_pct_cnt(r['Late_Dep_IT_Cnt'], r[trip_col]), axis=1)
    return summary.sort_values(by=['LH Type', 'E2E_Pair', 'Origin', 'Route Path', 'Leg_Num'])

def generate_vendor_summary(df_vperf_raw):
    if df_vperf_raw.empty: return pd.DataFrame()
    perf_sum = df_vperf_raw.groupby(['Zone', 'Origin RO', 'Route Path', 'Legwise', 'Legs', 'VendorName']).agg(
        Total_Trips=('MasterCDNo', 'count'),
        Ontime_Cnt=('Remark with 15 min waiver', lambda x: (x == 'Ontime Arrival').sum()),
        Late_Cnt=('Remark with 15 min waiver', lambda x: (x == 'Late Arrival').sum()),
        Transit_Cnt=('Remark with 15 min waiver', lambda x: (x == 'In-Transit').sum())
    ).reset_index()
    
    perf_sum['Ontime Arrival'] = perf_sum.apply(lambda r: format_pct_cnt(r['Ontime_Cnt'], r['Total_Trips']), axis=1)
    perf_sum['Late Arrival'] = perf_sum.apply(lambda r: format_pct_cnt(r['Late_Cnt'], r['Total_Trips']), axis=1)
    perf_sum['In-Transit'] = perf_sum.apply(lambda r: format_pct_cnt(r['Transit_Cnt'], r['Total_Trips']), axis=1)
    perf_sum['Sort_Pct'] = np.where(perf_sum['Total_Trips'] > 0, perf_sum['Ontime_Cnt'] / perf_sum['Total_Trips'], 0)
    return perf_sum.sort_values('Sort_Pct', ascending=True).drop(columns=['Ontime_Cnt', 'Late_Cnt', 'Transit_Cnt', 'Sort_Pct'])

# -------------------------------------------------------------
# MASTER EXCEL FORMATTER & CLEANER
# -------------------------------------------------------------
def clean_and_style_excel(writer, sheet_name, df_raw):
    df = df_raw.copy()
    
    # 1. Automatic Sorting
    sort_cols = [c for c in ['Route Path', 'Legwise', 'Legs', 'VendorName', 'Date'] if c in df.columns]
    if sort_cols: df = df.sort_values(by=sort_cols)
        
    # 2. Removing Junk Columns Completely
    junk_cols = ['Zone', 'VehicleType', 'ReplaceVehicleNo', 'ContractTypeDesc', 'Loaded_wt', 'MCD_StartYear', 'MCD_StartWeek', 'unloadwt', 
                 'CD_FromBranch_Clean', 'RPTBranchcode_Clean', 'Route Code_x', 'Route Branch Code_x', 'Dep_Route_Day', 'Sch_Dep_Time_Raw', 
                 'Route Code', 'Route Branch Code_y', 'Arr_Route_Day', 'Sch_Arr_Time_Raw', 'Dep_Status', 'Arr_Status', 'MCD_Created_By', 
                 'Overall Remark', 'Actual TAT Till Destination', 'Origin', 'Destination', 'Region', 'LH Type', 'E2E_Pair', 'MasterCDNo', 'MergeKey']
    
    df = df.drop(columns=[c for c in junk_cols if c in df.columns], errors='ignore')
    
    # 3. Priority Rearrangement
    front_priority = ['Origin RO', 'Route Path', 'Legwise', 'Legs', 'VendorName', 'VehicleNo', 
                      'Total_Trips', 'Ontime Arrival', 'Late Arrival', 'In-Transit',
                      'Ontime Dep, Ontime Arr %', 'Late Dep, Late Arr %']
    
    existing_front = [c for c in front_priority if c in df.columns]
    existing_mid = [c for c in df.columns if c not in existing_front]
    df = df[existing_front + existing_mid]
    
    # 4. Color Highlighting Rules (Green for Success, Red for Failures)
    def highlight(val):
        if isinstance(val, str):
            v = val.lower()
            if 'late dep, late arr' in v or 'late arrival' in v or 'no dep' in v or 'missing' in v: return 'background-color: #F8D7DA; color: #721C24'
            if 'ontime dep, ontime arr' in v or 'ontime arrival' in v: return 'background-color: #D4EDDA; color: #155724'
            if 'late dep, ontime arr' in v or 'ontime dep, late arr' in v or 'in-transit' in v: return 'background-color: #FFF3CD; color: #856404'
            if '%' in v and '(0)' in v: return 'color: #9CA3AF'
        return ''
        
    styled_df = df.style.map(highlight)
    styled_df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    # 5. Column Widths
    workbook = writer.book
    worksheet = writer.sheets[sheet_name]
    header_format = workbook.add_format({'bold': True, 'bg_color': '#1E3A8A', 'font_color': 'white', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
    data_format = workbook.add_format({'border': 1})
    
    for col_num, value in enumerate(df.columns.values):
        worksheet.write(0, col_num, value, header_format)
        col_width = min(max(df[value].astype(str).map(len).max(), len(str(value))) + 2, 40)
        worksheet.set_column(col_num, col_num, col_width, data_format)


def generate_vip_executive_report_to_disk(data_dict, output_path=None):
    with pd.ExcelWriter(output_path or FILE_MAP["EXECUTIVE_REPORT"], engine='xlsxwriter') as writer:
        if 'Ops_Raw' in data_dict:
            ops_raw = data_dict['Ops_Raw'].copy()
            ops_sum = generate_ops_summary(ops_raw)
            clean_and_style_excel(writer, 'Operations_Summary', ops_sum)
            clean_and_style_excel(writer, 'Operations_Raw', ops_raw)

        if 'Ven_Raw' in data_dict:
            ven_raw = data_dict['Ven_Raw'].copy()
            ven_sum = generate_vendor_summary(ven_raw)
            clean_and_style_excel(writer, 'Vendor_Perf_Summary', ven_sum)
            clean_and_style_excel(writer, 'Vendor_Perf_Raw', ven_raw)

        workbook = writer.book
        header_format = workbook.add_format({'bold': True, 'bg_color': '#1E3A8A', 'font_color': 'white', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        
        if 'Payment_Raw' in data_dict:
            df_pay = data_dict['Payment_Raw'].copy()
            pvt = pd.pivot_table(df_pay, values='Invoice Id', index='RO Name', columns='Department Bucket', aggfunc='count', fill_value=0, margins=True, margins_name='Grand Total')
            existing_cols = [c for c in ["1. USER / DRAFT PENDING", "2. COST CONTROL PENDING", "3. FINANCE PENDING", "4. PAYMENT PENDING", "5. OTHER PENDING", "Grand Total"] if c in pvt.columns]
            pvt = pvt.reindex(columns=existing_cols).reset_index()
            pvt.to_excel(writer, sheet_name='Payment_Summary', index=False)
            df_pay.to_excel(writer, sheet_name='Payment_Raw', index=False)

        if 'CPK_Raw' in data_dict:
            df_cpk = data_dict['CPK_Raw'].copy()
            clean_and_style_excel(writer, 'Network_Raw', df_cpk)

# ==========================================
# 5. DATA LOADING & CACHING
# ==========================================
@st.cache_data(ttl=3600, show_spinner=False)
def load_all_raw_data(file_timestamps):
    raw_data = {}
    
    ro_zone_map, branch_ro_map, branch_zone_map = {}, {}, {}
    if os.path.exists(FILE_MAP["BRANCH_MASTER"]):
        df_brn_master = pd.read_excel(FILE_MAP["BRANCH_MASTER"])
        df_brn_master.columns = df_brn_master.columns.astype(str).str.strip()
        brn_col_m = next((c for c in df_brn_master.columns if 'branchcode' in c.lower().replace(' ', '')), 'RPTBranchcode')
        ro_col_m = next((c for c in df_brn_master.columns if 'rptro' in c.lower().replace(' ', '')), 'RPTRO')
        zone_col_m = next((c for c in df_brn_master.columns if 'zone' in c.lower().replace(' ', '')), 'Zone')
        df_brn_master[brn_col_m] = df_brn_master[brn_col_m].astype(str).str.strip().str.upper()
        df_brn_master[ro_col_m] = df_brn_master[ro_col_m].astype(str).str.strip().str.upper()
        
        ro_zone_map = df_brn_master.drop_duplicates(subset=[ro_col_m]).set_index(ro_col_m)[zone_col_m].to_dict()
        df_brn_unique = df_brn_master.drop_duplicates(subset=[brn_col_m])
        branch_ro_map = df_brn_unique.set_index(brn_col_m)[ro_col_m].to_dict()
        branch_zone_map = df_brn_unique.set_index(brn_col_m)[zone_col_m].to_dict()

    # --- PAYMENT DATA ---
    if os.path.exists(FILE_MAP["PAYMENT"]):
        df_pay = pd.read_excel(FILE_MAP["PAYMENT"])
        df_pay.columns = df_pay.columns.astype(str).str.strip().str.upper().str.replace(" ", "").str.replace("_", "")
        rename_dict = {c: 'RO Name' for c in df_pay.columns if 'ROSELECTION' in c}
        rename_dict.update({c: 'Vendor Name' for c in df_pay.columns if 'VENDORNAME' in c})
        rename_dict.update({c: 'Invoice Id' for c in df_pay.columns if 'INVOICEID' in c})
        df_pay.rename(columns=rename_dict, inplace=True)
        
        for req in ['RO Name', 'Vendor Name', 'Invoice Id', 'Status', 'Pending With']:
            if req not in df_pay.columns: df_pay[req] = ""
                
        df_pay['RO Name Clean'] = df_pay['RO Name'].astype(str).str.strip().str.upper()
        df_pay['Zone'] = df_pay['RO Name Clean'].map(ro_zone_map).fillna('UNKNOWN ZONE')
        df_pay['Status'] = df_pay['Status'].fillna('').astype(str).str.upper()
        df_pay['Pending With'] = df_pay['Pending With'].fillna('').astype(str).str.upper()
        
        conds = [
            (df_pay['Status'].str.contains('PAYMENT') | df_pay['Pending With'].str.contains('PAYMENT')),
            (df_pay['Status'].str.contains('FINANCE') | df_pay['Status'].str.contains('HOLD')),
            (df_pay['Status'].str.contains('DRAFT') | df_pay['Pending With'].str.contains('AJAY')),
            (df_pay['Status'].str.contains('PENDING'))
        ]
        df_pay['Department Bucket'] = np.select(conds, ["4. PAYMENT PENDING", "3. FINANCE PENDING", "1. USER / DRAFT PENDING", "2. COST CONTROL PENDING"], "5. OTHER PENDING")
        raw_data['Payment_Raw'] = df_pay

    # --- LEGWISE OPS & VENDOR DATA ---
    if os.path.exists(FILE_MAP["LEGWISE"]) and os.path.exists(FILE_MAP["ROUTE_MASTER"]):
        df_leg_all = pd.read_excel(FILE_MAP["LEGWISE"], sheet_name="Sheet1")
        df_rte = pd.read_excel(FILE_MAP["ROUTE_MASTER"], sheet_name="RoutePathReportModel")
        
        df_leg_all.columns = df_leg_all.columns.str.strip()
        df_leg_all['MCD_StartDate_DT'] = pd.to_datetime(df_leg_all['MCD_StartDate'], dayfirst=True, errors='coerce')
        df_leg_all['Leg_Num'] = df_leg_all['Legwise'].astype(str).str.extract(r'(\d+)').astype(float).fillna(1)
        df_leg_all.rename(columns={'Min_CD_StartDatetime': 'Actual Departure Time', 'Max_CD_EndDatetime': 'Actual Arrival Time', 'Route': 'Route Path'}, inplace=True)
        
        df_leg_all[['Origin', 'Destination']] = df_leg_all['Route Path'].apply(lambda x: pd.Series(extract_orig_dest(x)))
        df_leg_all['CD_FromBranch_Clean'] = df_leg_all['CD_FromBranch'].astype(str).str.strip().str.upper()
        df_leg_all['Origin RO'] = df_leg_all['Origin'].map(branch_ro_map).combine_first(df_leg_all['CD_FromBranch_Clean'].map(branch_ro_map)).fillna('Missing RO')
        df_leg_all['Zone'] = df_leg_all['Origin'].map(branch_zone_map).combine_first(df_leg_all['CD_FromBranch_Clean'].map(branch_zone_map)).fillna('UNKNOWN ZONE')
        df_leg_all['E2E_Pair'] = df_leg_all['Route Path'].apply(get_route_pair)
        df_leg_all.rename(columns={'LH_Type': 'LH Type'}, inplace=True)
        df_leg_all['Legs'] = df_leg_all['CD_FromBranch'].astype(str) + " to " + df_leg_all['CD_ToBranch'].astype(str)
        
        df_rte_tat = df_rte.copy()
        df_rte_tat['Dep_Hrs'] = df_rte_tat['Schedule Departure Time'].apply(time_to_hrs)
        df_rte_tat['Arr_Hrs'] = df_rte_tat['Schedule Arrival Time'].apply(time_to_hrs)
        df_rte_tat['Day_Offset'] = df_rte_tat['Route Day'].apply(get_day_offset)
        route_tat_master = df_rte_tat.groupby('Route Code').agg(Min_Dep=('Day_Offset', 'min'), Max_Arr=('Arr_Hrs', 'max')).reset_index()
        
        def get_sch_time(r, day_c, time_c):
            try:
                if pd.isna(r['MCD_StartDate_DT']) or pd.isna(r[day_c]): return pd.NaT
                day_offset = float(r[day_c])
                d = r['MCD_StartDate_DT'] + pd.to_timedelta(day_offset, unit='D')
                t_str = str(r[time_c]).strip()
                if t_str == 'nan' or not t_str: return pd.NaT
                return pd.to_datetime(d.strftime('%Y-%m-%d') + ' ' + str(pd.to_datetime(t_str).time()))
            except: return pd.NaT

        df_rte_sub = df_rte[['Route Code', 'Route Branch Code', 'Route Day', 'Schedule Departure Time', 'Schedule Arrival Time']]
        df_leg_all = df_leg_all.merge(df_rte_sub, left_on=['RouteCode', 'CD_FromBranch'], right_on=['Route Code', 'Route Branch Code'], how='left')
        df_leg_all.rename(columns={'Route Day': 'Dep_Route_Day', 'Schedule Departure Time': 'Sch_Dep_Time_Raw'}, inplace=True)
        df_leg_all.drop(columns=['Schedule Arrival Time'], inplace=True, errors='ignore')
        df_leg_all = df_leg_all.merge(df_rte_sub[['Route Code', 'Route Branch Code', 'Route Day', 'Schedule Arrival Time']], left_on=['RouteCode', 'CD_ToBranch'], right_on=['Route Code', 'Route Branch Code'], how='left')
        df_leg_all.rename(columns={'Route Day': 'Arr_Route_Day', 'Schedule Arrival Time': 'Sch_Arr_Time_Raw'}, inplace=True)

        df_leg_all['Scheduled Departure Time'] = df_leg_all.apply(lambda r: get_sch_time(r, 'Dep_Route_Day', 'Sch_Dep_Time_Raw'), axis=1)
        df_leg_all['Scheduled Arrival Time'] = df_leg_all.apply(lambda r: get_sch_time(r, 'Arr_Route_Day', 'Sch_Arr_Time_Raw'), axis=1)
        df_leg_all['Actual Departure Time'] = pd.to_datetime(df_leg_all['Actual Departure Time'], dayfirst=True, errors='coerce')
        df_leg_all['Actual Arrival Time'] = pd.to_datetime(df_leg_all['Actual Arrival Time'], dayfirst=True, errors='coerce')
        
        # Vendor Perf
        df_vperf = df_leg_all.copy()
        df_vperf['Delay Hours_Raw'] = (df_vperf['Actual Arrival Time'] - df_vperf['Scheduled Arrival Time']).dt.total_seconds() / 3600.0
        df_vperf['Remark with 15 min waiver'] = df_vperf.apply(lambda row: "In-Transit" if pd.isna(row['Actual Arrival Time']) else ("Missing Schedule" if pd.isna(row['Delay Hours_Raw']) else ("Ontime Arrival" if row['Delay Hours_Raw'] <= 0.25 else "Late Arrival")), axis=1)
        df_vperf['Date'] = df_vperf['MCD_StartDate_DT'].dt.strftime('%d-%m-%Y')
        df_vperf['Actual Departure Time'] = df_vperf['Actual Departure Time'].dt.strftime('%d-%m-%Y %H:%M').fillna('-')
        df_vperf['Actual Arrival Time'] = df_vperf['Actual Arrival Time'].dt.strftime('%d-%m-%Y %H:%M').fillna('-')
        raw_data['Ven_Raw'] = df_vperf
        
        # Ops Exception
        df_leg = df_leg_all[(df_leg_all['MCD_Created_By'] == 'SCHEDULED') & (df_leg_all['LH Type'].isin(['National LH', 'Zonal LH']))].copy()
        df_leg['Dep_Status'] = df_leg.apply(lambda r: "In-Transit" if pd.isna(r['Actual Departure Time']) else ("Missing Sch" if pd.isna(r['Scheduled Departure Time']) else ("Ontime Dep" if (r['Actual Departure Time'] - r['Scheduled Departure Time']).total_seconds() / 60 <= 15 else "Late Dep")), axis=1)
        df_leg['Arr_Status'] = df_leg.apply(lambda r: "In-Transit" if pd.isna(r['Actual Arrival Time']) else ("Missing Sch" if pd.isna(r['Scheduled Arrival Time']) else ("Ontime Arr" if (r['Actual Arrival Time'] - r['Scheduled Arrival Time']).total_seconds() / 60 <= 15 else "Late Arr")), axis=1)
        df_leg['Remark'] = df_leg['Dep_Status'] + ", " + df_leg['Arr_Status']
        df_leg['Date'] = df_leg['MCD_StartDate_DT'].dt.strftime('%d-%m-%Y')
        raw_data['Ops_Raw'] = df_leg

    # --- CPK ---
    if os.path.exists(FILE_MAP["CPK_UTIL"]):
        try: df_raw = pd.read_excel(FILE_MAP["CPK_UTIL"], sheet_name='ContractVehicle_DetailReport')
        except: df_raw = pd.read_excel(FILE_MAP["CPK_UTIL"])
        df_raw.columns = df_raw.columns.astype(str).str.strip()
        vno_col = get_col(df_raw, ['vehicleno', 'vehicle']) or 'VehicleNo'
        df_raw['Vehicle No'] = df_raw.get(vno_col, pd.Series(['Unlisted']*len(df_raw))).fillna('Unlisted')
        df_raw['Date_DT'] = pd.to_datetime(df_raw.get(get_col(df_raw, ['date', 'mcd_startdate']) or 'Date', ''), errors='coerce', dayfirst=True)
        raw_data['CPK_Raw'] = df_raw

    return raw_data

def process_all_data():
    progress = st.progress(0)
    status_text = st.empty()
    try:
        status_text.text("⚙️ Aggregating & Processing all files...")
        file_timestamps = {k: os.path.getmtime(v) for k, v in FILE_MAP.items() if os.path.exists(v)}
        raw_data_dict = load_all_raw_data(file_timestamps)
        
        status_text.text("⚙️ Generating VIP Executive Report directly to disk...")
        generate_vip_executive_report_to_disk(raw_data_dict)
        
        # Save cache dump for quick load
        with tempfile.NamedTemporaryFile(dir=DATA_DIR, suffix='.xlsx', delete=False) as tmp:
            with pd.ExcelWriter(tmp.name, engine='xlsxwriter') as writer:
                for k, df in raw_data_dict.items(): df.to_excel(writer, sheet_name=k, index=False)
            os.replace(tmp.name, FILE_MAP["FINAL_OUTPUT"])
            
        st.session_state.pop('_raw_data_cache', None)
        progress.progress(100)
        status_text.success("✅ Data Processed & VIP Report Generated Successfully!")
        return True
    except Exception as e:
        status_text.error(f"Error during processing: {e}")
        return False

# ==========================================
# 6. SIDEBAR & NAVIGATION
# ==========================================
st.sidebar.markdown(f"### Welcome, **{st.session_state['role']}**")
if st.sidebar.button("Logout", key="logout_btn", use_container_width=True):
    st.session_state['logged_in'] = False
    st.session_state['role'] = None
    st.rerun()

st.sidebar.markdown("---")

if st.session_state['role'] == 'Admin':
    st.sidebar.header("🛠 Data Management")
    with st.sidebar.expander("📂 Upload Raw Files", expanded=False):
        if save_file(st.file_uploader("1. Payment Data", type=['xlsx']), "PAYMENT"): st.success("Saved!")
        if save_file(st.file_uploader("2. Legwise Report", type=['xlsx']), "LEGWISE"): st.success("Saved!")
        if save_file(st.file_uploader("3. Scheduled Route Master", type=['xlsx']), "ROUTE_MASTER"): st.success("Saved!")
        if save_file(st.file_uploader("4. RO & Branch List", type=['xlsx']), "BRANCH_MASTER"): st.success("Saved!")
        if save_file(st.file_uploader("6. CPK & Util Raw File", type=['xlsx']), "CPK_UTIL"): st.success("Saved!")

    if st.sidebar.button("🚀 PROCESS & REFRESH DATA", use_container_width=True, type="primary"):
        st.session_state.pop('_raw_data_cache', None)
        load_all_raw_data.clear()
        gc.collect()
        if process_all_data():
            st.session_state['_processing_success'] = True
            st.rerun()
        st.stop()

if os.path.exists(FILE_MAP["EXECUTIVE_REPORT"]) and st.session_state['role'] != 'Vendor':
    st.sidebar.markdown("---")
    st.sidebar.header("📥 Export Reports")
    try:
        with open(FILE_MAP["EXECUTIVE_REPORT"], "rb") as report_file:
            st.sidebar.download_button("📄 Download VIP Executive Report", data=report_file, file_name=f"Trackon_Executive_Master_Report_{get_ist_now():%d_%b_%Y}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, type="primary")
    except: pass

MENU_SHEETS = ["📊 Operations Summary", "🚚 Vendor Performance", "💳 Payment Dashboard", "📱 Communication Hub", "💰 Network Utilization", "📝 Today's Call Action Plan"]
if st.session_state['role'] == 'Vendor': menu_options = ["🚚 Vendor Performance"]
else: menu_options = MENU_SHEETS
choice = st.sidebar.radio("Navigation:", menu_options)

# Load Data efficiently
@st.cache_data(show_spinner=False)
def get_ui_data(version_tag):
    file_timestamps = {k: os.path.getmtime(v) for k, v in FILE_MAP.items() if os.path.exists(v)}
    return load_all_raw_data(file_timestamps)

data_version = os.path.getmtime(FILE_MAP["FINAL_OUTPUT"]) if os.path.exists(FILE_MAP["FINAL_OUTPUT"]) else 0
raw_data_cache = get_ui_data(data_version)

if not raw_data_cache:
    st.warning("No processed data found. Admin must upload files and click Process.")
    st.stop()

# ==========================================
# DATE FILTER LOGIC
# ==========================================
global_start_date, global_end_date = None, None
if choice in ["📊 Operations Summary", "🚚 Vendor Performance", "📱 Communication Hub", "💰 Network Utilization"]:
    st.markdown("### 📅 Select Duration")
    date_col1, date_col2, _ = st.columns([1, 1, 2])
    
    # Extract min/max dates from raw data
    all_dates = []
    if 'Ven_Raw' in raw_data_cache and not raw_data_cache['Ven_Raw'].empty: all_dates.extend(raw_data_cache['Ven_Raw']['MCD_StartDate_DT'].dropna().tolist())
    if 'CPK_Raw' in raw_data_cache and not raw_data_cache['CPK_Raw'].empty: all_dates.extend(raw_data_cache['CPK_Raw']['Date_DT'].dropna().tolist())
    
    if all_dates:
        min_dt, max_dt = min(all_dates).date(), max(all_dates).date()
        global_start_date = date_col1.date_input("Start Date", value=min_dt, min_value=min_dt, max_value=max_dt)
        global_end_date = date_col2.date_input("End Date", value=max_dt, min_value=min_dt, max_value=max_dt)
    else:
        st.warning("No dates found in data.")
        st.stop()
        
    st.markdown("---")

def filter_df_by_date(df, date_col):
    if df.empty or global_start_date is None or global_end_date is None: return df
    if date_col in df.columns:
        mask = (df[date_col].dt.date >= global_start_date) & (df[date_col].dt.date <= global_end_date)
        return df[mask].copy()
    return df

# Apply Date Filters dynamically to generate SUMMARIES
ops_raw_filtered = filter_df_by_date(raw_data_cache.get('Ops_Raw', pd.DataFrame()), 'MCD_StartDate_DT')
ops_sum_filtered = generate_ops_summary(ops_raw_filtered)

ven_raw_filtered = filter_df_by_date(raw_data_cache.get('Ven_Raw', pd.DataFrame()), 'MCD_StartDate_DT')
ven_sum_filtered = generate_vendor_summary(ven_raw_filtered)

days_duration = (global_end_date - global_start_date).days + 1 if global_start_date and global_end_date else 0

# ==========================================
# A. OPERATIONS SUMMARY
# ==========================================
if choice == "📊 Operations Summary":
    st.markdown(f"<h2>Operations Exception Summary (Filtered: {days_duration} Days)</h2>", unsafe_allow_html=True)
    df_leg_sum = ops_sum_filtered
    df_raw_leg = ops_raw_filtered
    
    if not df_leg_sum.empty:
        col1, col2, col3 = st.columns([1, 1, 2])
        selected_zone = col1.selectbox("Filter by Zone:", ["ALL"] + sorted(df_leg_sum['Zone'].dropna().unique()))
        if selected_zone != "ALL": df_leg_sum = df_leg_sum[df_leg_sum['Zone'] == selected_zone]
            
        selected_ro = col2.selectbox("Filter by RO:", ["ALL"] + sorted(df_leg_sum['Origin RO'].dropna().unique()))
        if selected_ro != "ALL": df_leg_sum = df_leg_sum[df_leg_sum['Origin RO'] == selected_ro]

        search_q = col3.text_input("🔍 Quick Search:", placeholder="Search Route, Leg...")

        display_cols = ['Origin RO', 'Route Path', 'Legwise', 'Legs', 'Total_Trips', 'Ontime Dep, Ontime Arr %', 'Ontime Dep, Late Arr %', 'Late Dep, Late Arr %', 'Late Dep, Ontime Arr %']
        df_display = df_leg_sum[display_cols].copy()
        df_display['RowKey'] = df_display['Origin RO'].astype(str) + " || " + df_display['Route Path'].astype(str) + " | " + df_display['Legwise'].astype(str)
        
        if search_q: df_display = df_display[df_display.astype(str).apply(lambda x: x.str.contains(search_q, case=False, regex=False)).any(axis=1)]

        def color_cols(val, col):
            if not isinstance(val, str) or '%' not in val: return ''
            if '0.0%' in val: return 'color: #78909C;' 
            if 'Late Dep, Late Arr' in col: return 'background-color: rgba(211, 47, 47, 0.2); color: #ff8a80; font-weight: bold;'
            if 'Ontime Dep, Ontime Arr' in col: return 'background-color: rgba(56, 142, 60, 0.2); color: #b9f6ca; font-weight: bold;'
            if 'Ontime Dep, Late Arr' in col: return 'background-color: rgba(245, 127, 23, 0.2); color: #ffe57f; font-weight: bold;'
            if 'Late Dep, Ontime Arr' in col: return 'background-color: rgba(123, 31, 162, 0.2); color: #ea80fc; font-weight: bold;'
            return ''

        df_display.insert(0, 'Select 👁️', False)
        ap_data = load_action_plans()
        mod_ap = ap_data.get("Operations Summary", {})
        df_display['Action Plan ✍️'] = df_display['RowKey'].map(mod_ap).fillna("")
        
        disp_cols = ['Select 👁️'] + [c for c in df_display.columns if c not in ['RowKey', 'Select 👁️']]
        styled_df = df_display[disp_cols].style.map(lambda x, c=None: color_cols(x, c), subset=[c for c in disp_cols if '%' in c])
            
        edited_df = st.data_editor(styled_df, column_config={"Action Plan ✍️": st.column_config.TextColumn("Action Plan ✍️", width="large")}, disabled=[c for c in disp_cols if c not in ['Action Plan ✍️', 'Select 👁️']], use_container_width=True, height=400)
        
        for idx, row in edited_df.iterrows():
            r_key, new_val = str(df_display.loc[idx, 'RowKey']), str(row['Action Plan ✍️']).strip()
            if new_val != str(mod_ap.get(r_key, "")).strip():
                if new_val: mod_ap[r_key] = new_val
                else: mod_ap.pop(r_key, None)
                ap_data["Operations Summary"] = mod_ap
                save_action_plans(ap_data)

        if edited_df[edited_df['Select 👁️'] == True].index.tolist():
            sel_idx = edited_df[edited_df['Select 👁️'] == True].index.tolist()[0]
            sel_rt, sel_leg = df_display.loc[sel_idx, 'Route Path'], df_display.loc[sel_idx, 'Legwise']
            st.markdown(f"### 📄 Raw Records: `{sel_rt}` - `{sel_leg}`")
            f_raw = df_raw_leg[(df_raw_leg['Route Path'] == sel_rt) & (df_raw_leg['Legwise'] == sel_leg)].copy()
            f_raw = f_raw.drop(columns=['Zone', 'MCD_StartYear', 'MCD_StartWeek', 'CD_FromBranch_Clean', 'Dep_Status', 'Arr_Status', 'MCD_Created_By'], errors='ignore')
            st.dataframe(f_raw.style.map(lambda v: 'color: #ff8a80;' if isinstance(v, str) and 'Late Dep, Late Arr' in v else ('color: #b9f6ca;' if isinstance(v, str) and 'Ontime Dep, Ontime Arr' in v else ''), subset=['Remark'] if 'Remark' in f_raw.columns else []), use_container_width=True)

# ==========================================
# B. VENDOR PERFORMANCE
# ==========================================
elif choice == "🚚 Vendor Performance":
    st.markdown(f"<h2>Vendor Performance (Filtered: {days_duration} Days)</h2>", unsafe_allow_html=True)
    df_vperf_sum = ven_sum_filtered
    df_vperf_raw = ven_raw_filtered
    
    if st.session_state['role'] == 'Vendor' and st.session_state.get('vendors'):
        regex_v = '|'.join([f"^{v}\$" for v in st.session_state['vendors']])
        df_vperf_sum = df_vperf_sum[df_vperf_sum['VendorName'].str.contains(regex_v, case=False, na=False, regex=True)]
        df_vperf_raw = df_vperf_raw[df_vperf_raw['VendorName'].str.contains(regex_v, case=False, na=False, regex=True)]

    if not df_vperf_sum.empty:
        col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
        selected_zone = col1.selectbox("Filter by Zone:", ["ALL"] + sorted(df_vperf_sum['Zone'].dropna().unique()))
        if selected_zone != "ALL": df_vperf_sum = df_vperf_sum[df_vperf_sum['Zone'] == selected_zone]
        
        selected_ro = col2.selectbox("Filter by RO:", ["ALL"] + sorted(df_vperf_sum['Origin RO'].dropna().unique()))
        if selected_ro != "ALL": df_vperf_sum = df_vperf_sum[df_vperf_sum['Origin RO'] == selected_ro]
        
        selected_vendor_b = col3.selectbox("Filter by Vendor:", ["ALL"] + sorted(df_vperf_sum['VendorName'].dropna().unique()))
        if selected_vendor_b != "ALL": df_vperf_sum = df_vperf_sum[df_vperf_sum['VendorName'] == selected_vendor_b]

        search_q = col4.text_input("🔍 Quick Search:", placeholder="Search Route, Leg...")

        display_cols = ['Origin RO', 'Route Path', 'Legwise', 'Legs', 'VendorName', 'Total_Trips', 'Ontime Arrival', 'Late Arrival', 'In-Transit']
        df_display = df_vperf_sum[display_cols].copy()
        df_display['RowKey'] = df_display['Origin RO'].astype(str) + " || " + df_display['VendorName'].astype(str) + " | " + df_display['Route Path'].astype(str) + " | " + df_display['Legwise'].astype(str)
        if search_q: df_display = df_display[df_display.astype(str).apply(lambda x: x.str.contains(search_q, case=False, regex=False)).any(axis=1)]
        
        def highlight_perf(val, col):
            if not isinstance(val, str) or '%' not in val: return ''
            if '0.0%' in val: return 'color: #78909C;' 
            if col == 'Late Arrival': return 'background-color: rgba(211, 47, 47, 0.2); color: #ff8a80; font-weight: bold;'
            elif col == 'Ontime Arrival': return 'background-color: rgba(56, 142, 60, 0.2); color: #b9f6ca; font-weight: bold;'
            elif col == 'In-Transit': return 'background-color: rgba(245, 127, 23, 0.2); color: #ffe57f; font-weight: bold;'
            return ''

        df_display.insert(0, 'Select 👁️', False)
        
        if st.session_state['role'] != 'Vendor':
            ap_data = load_action_plans()
            mod_ap = ap_data.get("Vendor Performance", {})
            df_display['Action Plan ✍️'] = df_display['RowKey'].map(mod_ap).fillna("")
            disp_cols = ['Select 👁️'] + [c for c in df_display.columns if c not in ['RowKey', 'Select 👁️']]
        else:
            disp_cols = ['Select 👁️'] + [c for c in df_display.columns if c not in ['RowKey', 'Select 👁️', 'Action Plan ✍️']]
            
        styled_df = df_display[disp_cols].style
        for col in ['Ontime Arrival', 'Late Arrival', 'In-Transit']: styled_df = styled_df.map(lambda x, c=col: highlight_perf(x, c), subset=[col])
            
        edited_df = st.data_editor(styled_df, column_config={"Action Plan ✍️": st.column_config.TextColumn("Action Plan ✍️", width="large")}, disabled=[c for c in disp_cols if c not in ['Action Plan ✍️', 'Select 👁️']], use_container_width=True, height=400)
        
        if st.session_state['role'] != 'Vendor':
            for idx, row in edited_df.iterrows():
                r_key, new_val = str(df_display.loc[idx, 'RowKey']), str(row['Action Plan ✍️']).strip()
                if new_val != str(mod_ap.get(r_key, "")).strip():
                    if new_val: mod_ap[r_key] = new_val
                    else: mod_ap.pop(r_key, None)
                    ap_data["Vendor Performance"] = mod_ap
                    save_action_plans(ap_data)

        sel_rows = edited_df[edited_df['Select 👁️'] == True].index.tolist()
        if sel_rows:
            sel_idx = sel_rows[0]
            sel_rt, sel_leg, sel_ven = df_display.loc[sel_idx, 'Route Path'], df_display.loc[sel_idx, 'Legwise'], df_display.loc[sel_idx, 'VendorName']
            st.markdown(f"### 📄 Raw Data: `{sel_ven}` on `{sel_rt}`")
            f_raw = df_vperf_raw[(df_vperf_raw['Route Path'] == sel_rt) & (df_vperf_raw['Legwise'] == sel_leg) & (df_vperf_raw['VendorName'] == sel_ven)].copy()
            f_raw = f_raw.drop(columns=['Zone', 'Origin RO', 'MCD_StartYear', 'MCD_StartWeek'], errors='ignore')
            
            output_raw = io.BytesIO()
            with pd.ExcelWriter(output_raw, engine='xlsxwriter') as writer: clean_and_style_excel(writer, 'Raw_Data', f_raw)
            st.download_button("⬇️ Download Raw Data", data=output_raw.getvalue(), file_name=f"Raw_Data_{sel_ven}_{sel_leg}.xlsx", mime="application/vnd.ms-excel", type="primary")
            st.dataframe(f_raw.style.map(lambda v: 'color: #ff8a80;' if isinstance(v, str) and 'Late Arrival' in v else ('color: #b9f6ca;' if isinstance(v, str) and 'Ontime' in v else ''), subset=['Remark with 15 min waiver'] if 'Remark with 15 min waiver' in f_raw.columns else []), use_container_width=True)

# ==========================================
# C. COMMUNICATION HUB
# ==========================================
elif choice == "📱 Communication Hub":
    st.markdown("<h2>Vendor Alerts & Messaging CRM</h2>", unsafe_allow_html=True)
    
    df_rt_ops_sum, df_rt_ops_raw = ops_sum_filtered, ops_raw_filtered
    df_rt_ven_sum, df_rt_ven_raw = ven_sum_filtered, ven_raw_filtered

    tab1, tab2, tab3 = st.tabs(["🚀 Routewise Ops & Vendor Summary", "🔍 Individual Vendor Hub", "🌍 Regionwise (RO) Summary"])

    with tab1:
        st.markdown("### National Round Trip Operations Performance")
        NATIONAL_ROUTES = {
            "HYDH-PNQHWH-BWNDLH Round Trip": ["HYDH-PNQHWH-BWNDLH", "BWNDLH-PNQHWH-HYDH"],
            "PATH-VNS1 Round Trip": ["PATH-VNS1", "VNS1-PATH"],
            "BLRSH-HYDH-NGPLAVA-DELAP Round Trip": ["BLRSH-HYDH-NGPLAVA-DELAP", "DELAP-NGPLAVA-HYDH-BLRSH"],
            "BWNDLH-PNQHWH-BLRSH-HOSURH-CHIH Round Trip": ["BWNDLH-PNQHWH-BLRSH-HOSURH-CHIH", "CHIH-HOSURH-BLRSH-PNQHWH-BWNDLH"],
            "BWNDLH-NGPLAVA-RAIH-HOWDG Round Trip": ["BWNDLH-NGPLAVA-RAIH-HOWDG", "HOWDG-RAIH-NGPLAVA-BWNDLH"],
            "DELAP-PATH-CCUH Round Trip": ["DELAP-PATH-CCUH", "CCUH-HOWDG-PATH-DELAP"],
            "DELAP-BKLH-BWNDLH Round Trip": ["DELAP-BKLH-BWNDLH", "BWNDLH-DELAP", "BWNDLH-BKLH-DELAP"],
            "DELAP-JPRH-BKLH Round Trip": ["DELAP-JPRH-BKLH", "BKLH-JPRH-DELAP"],
            "DELAP-BHOH-INDH Round Trip": ["DELAP-BHOH-INDH", "INDH-BHOH-GWLH-DELAP"]
        }
        selected_rt = st.selectbox("Select National Route Pair:", list(NATIONAL_ROUTES.keys()))
        target_routes = NATIONAL_ROUTES[selected_rt]
        
        if not df_rt_ops_sum.empty:
            df_ops_sum = df_rt_ops_sum[df_rt_ops_sum['Route Path'].isin(target_routes)]
            df_ops_raw = df_rt_ops_raw[df_rt_ops_raw['Route Path'].isin(target_routes)]
            df_ven_sum = df_rt_ven_sum[df_rt_ven_sum['Route Path'].isin(target_routes)]
            df_ven_raw = df_rt_ven_raw[df_rt_ven_raw['Route Path'].isin(target_routes)]
            
            c1, c2 = st.columns(2)
            c1.metric("Selected Ops Trips", df_ops_sum['Total_Trips'].sum() if not df_ops_sum.empty else 0)
            c2.metric("Selected Vendor Trips", df_ven_sum['Total_Trips'].sum() if not df_ven_sum.empty else 0)
            mail_ids = st.text_input("Enter Email IDs:", placeholder="vendor1@abc.com, manager@xyz.com")
            
            output_rt = io.BytesIO()
            with pd.ExcelWriter(output_rt, engine='xlsxwriter') as writer:
                if not df_ops_sum.empty: clean_and_style_excel(writer, 'Ops_Performance', df_ops_sum)
                if not df_ops_raw.empty: clean_and_style_excel(writer, 'Ops_Raw_Data', df_ops_raw)
                if not df_ven_sum.empty: clean_and_style_excel(writer, 'Vendor_Performance', df_ven_sum)
                if not df_ven_raw.empty: clean_and_style_excel(writer, 'Vendor_Raw_Data', df_ven_raw)

            d_str = f"{global_start_date.strftime('%d-%b')} to {global_end_date.strftime('%d-%b')}" if global_start_date else "selected dates"
            msg = f"Dear Team,\n\nPlease find the Operations & Vendor performance for the period {d_str}.\n\n"
            msg += f"ROUTE SUMMARY:\n-------------------------------------------------\n"
            for _, r in df_ops_sum.iterrows(): msg += f"{str(r['Route Path'])[:25].ljust(27)} | Trips: {r['Total_Trips']} | Ontime: {r['Ontime Dep, Ontime Arr %']} | Late: {r['Late Dep, Late Arr %']}\n"
            msg += "-------------------------------------------------\n\nPlease review the attached Excel file for raw data. Ensure on-time arrivals.\n\nThanks,\nAjay Singh Rawat"
            
            b1, b2 = st.columns(2)
            b1.download_button("1️⃣ Download Master Excel 📊", data=output_rt.getvalue(), file_name=f"{selected_rt.replace(' ', '_')}.xlsx", mime="application/vnd.ms-excel", use_container_width=True, type="primary")
            b2.markdown(f'<a href="https://mail.google.com/mail/?view=cm&fs=1&to={urllib.parse.quote(mail_ids)}&su={urllib.parse.quote(f"Performance Report: {selected_rt}")}&body={urllib.parse.quote(msg)}" target="_blank"><button style="background-color: #EF4444; color: white; padding: 10px; border: none; border-radius: 8px; width: 100%; font-weight: 600;">2️⃣ Open Email (Gmail) ✉️</button></a>', unsafe_allow_html=True)

    with tab2:
        if not df_rt_ven_sum.empty:
            selected_vendor = st.selectbox("Select Vendor for Direct Message:", ["NONE"] + sorted(df_rt_ven_sum['VendorName'].dropna().unique()))
            if selected_vendor != "NONE":
                ven_sum = df_rt_ven_sum[df_rt_ven_sum['VendorName'] == selected_vendor].copy()
                ven_raw = df_rt_ven_raw[df_rt_ven_raw['VendorName'] == selected_vendor].copy()
                st.dataframe(ven_sum[['Route Path', 'Legwise', 'Legs', 'Total_Trips', 'Ontime Arrival', 'Late Arrival']], use_container_width=True, hide_index=True)
                
                v_master_data_live = {}
                if os.path.exists(FILE_MAP.get("VENDOR_MASTER")):
                    try:
                        with open(FILE_MAP.get("VENDOR_MASTER"), 'r') as f: v_master_data_live = json.load(f)
                    except: pass
                email_id = v_master_data_live.get(selected_vendor, {}).get("email", "")
                
                output_ven = io.BytesIO()
                with pd.ExcelWriter(output_ven, engine='xlsxwriter') as writer:
                    clean_and_style_excel(writer, 'Summary', ven_sum)
                    clean_and_style_excel(writer, 'Raw', ven_raw)
                
                d_str = f"{global_start_date.strftime('%d-%b')} to {global_end_date.strftime('%d-%b')}" if global_start_date else "selected dates"
                msg = f"Dear {selected_vendor},\n\nPlease find your performance summary for the period {d_str}.\nTotal Trips Assigned: {ven_sum['Total_Trips'].sum()}\n\n"
                msg += "PERFORMANCE SUMMARY:\n-------------------------------------------------\n"
                msg += "ROUTE & LEG".ljust(35) + "| TRIPS | ONTIME | LATE\n-------------------------------------------------\n"
                for _, r in ven_sum.iterrows(): msg += f"{str(r['Route Path'] + ' (' + r['Legwise'] + ')')[:33].ljust(35)}| {str(r['Total_Trips']).center(5)} | 🟢 {str(r['Ontime Arrival']).ljust(8)} | 🔴 {str(r['Late Arrival']).ljust(8)}\n"
                msg += "-------------------------------------------------\n\nPlease review the attached Excel file for raw data and detailed trip records. Ensure on-time arrivals for future trips.\n\nThanks,\nAjay Singh Rawat"
                
                c1, c2 = st.columns(2)
                c1.download_button("1️⃣ Download Excel 📊", data=output_ven.getvalue(), file_name=f"{selected_vendor}_Report.xlsx", mime="application/vnd.ms-excel", use_container_width=True)
                c2.markdown(f'<a href="https://mail.google.com/mail/?view=cm&fs=1&to={urllib.parse.quote(email_id)}&su={urllib.parse.quote("Trackon Performance: " + selected_vendor)}&body={urllib.parse.quote(msg)}" target="_blank"><button style="background-color: #EF4444; color: white; padding: 10px; border: none; border-radius: 8px; width: 100%;">2️⃣ Gmail 🌐</button></a>', unsafe_allow_html=True)

    with tab3:
        all_possible_ros = set()
        if not df_rt_ops_sum.empty: all_possible_ros.update(df_rt_ops_sum['Origin RO'].dropna().unique())
        selected_region = st.selectbox("Select Origin RO:", sorted(list(all_possible_ros)))
        if selected_region:
            ro_mail_ids = st.text_input("Enter RO Email IDs:")
            output_ro = io.BytesIO()
            with pd.ExcelWriter(output_ro, engine='xlsxwriter') as writer:
                df1 = df_rt_ops_sum[df_rt_ops_sum['Origin RO'] == selected_region]
                if not df1.empty: clean_and_style_excel(writer, 'Ops_Summary', df1)
                df2 = df_rt_ops_raw[df_rt_ops_raw['Origin RO'] == selected_region]
                if not df2.empty: clean_and_style_excel(writer, 'Ops_Raw', df2)
                df3 = df_rt_ven_sum[df_rt_ven_sum['Origin RO'] == selected_region]
                if not df3.empty: clean_and_style_excel(writer, 'Vendor_Summary', df3)
                df4 = df_rt_ven_raw[df_rt_ven_raw['Origin RO'] == selected_region]
                if not df4.empty: clean_and_style_excel(writer, 'Vendor_Raw', df4)
                    
            d_str = f"{global_start_date.strftime('%d-%b')} to {global_end_date.strftime('%d-%b')}" if global_start_date else "selected dates"
            msg_ro = f"Hello {selected_region} Team,\n\nPlease find attached the consolidated Operations and Vendor report for your region ({d_str}).\n\nKindly review and take necessary action.\n\nThanks,\nAjay Singh Rawat"
            b1, b2 = st.columns(2)
            b1.download_button("1️⃣ Download RO Excel 📊", data=output_ro.getvalue(), file_name=f"{selected_region}_Master_Report.xlsx", mime="application/vnd.ms-excel", use_container_width=True, type="primary")
            b2.markdown(f'<a href="https://mail.google.com/mail/?view=cm&fs=1&to={urllib.parse.quote(ro_mail_ids)}&su={urllib.parse.quote("Trackon RO Master Report: " + selected_region)}&body={urllib.parse.quote(msg_ro)}" target="_blank"><button style="background-color: #EF4444; color: white; padding: 10px; border: none; border-radius: 8px; width: 100%; font-weight: 600;">2️⃣ Open Email (Gmail) ✉️</button></a>', unsafe_allow_html=True)


# ==========================================
# D. PAYMENT DASHBOARD (Remains identical structure wise but uses raw_data_cache)
# ==========================================
elif choice == "💳 Payment Dashboard":
    st.markdown("<h2>Pending Payments Tracker</h2>", unsafe_allow_html=True)
    if 'Payment_Raw' in raw_data_cache:
        df_pay = raw_data_cache['Payment_Raw'].copy()
        col1, col2 = st.columns([1, 2])
        selected_zone = col1.selectbox("Filter by Zone:", ["ALL"] + sorted(df_pay['Zone'].dropna().unique()))
        if selected_zone != "ALL": df_pay = df_pay[df_pay['Zone'] == selected_zone]
        search_q = col2.text_input("🔍 Quick Search (Invoice, Vendor, RO...):")
            
        pvt = pd.pivot_table(df_pay, values='Invoice Id', index='RO Name', columns='Department Bucket', aggfunc='count', fill_value=0, margins=True, margins_name='Grand Total')
        cols_order = ["1. USER / DRAFT PENDING", "2. COST CONTROL PENDING", "3. FINANCE PENDING", "4. PAYMENT PENDING", "5. OTHER PENDING", "Grand Total"]
        pvt = pvt.reindex(columns=[c for c in cols_order if c in pvt.columns]).reset_index()
        pvt['RowKey'] = pvt['RO Name'].astype(str) + " || " + pvt['RO Name'].astype(str)
        
        def color_pay(val, c):
            if pd.isna(val) or val == 0: return ''
            if c == '1. USER / DRAFT PENDING': return 'background-color: rgba(211, 47, 47, 0.3); color: #ff8a80;' 
            elif c == '2. COST CONTROL PENDING': return 'background-color: rgba(245, 127, 23, 0.3); color: #ffe57f;'
            elif c == '3. FINANCE PENDING': return 'background-color: rgba(245, 127, 23, 0.1); color: #ffb74d;'
            return ''

        pvt.insert(0, 'Select 👁️', False)
        styled_pvt = pvt.drop(columns=['RowKey']).style
        for c in cols_order: styled_pvt = styled_pvt.map(lambda x, col=c: color_pay(x, col), subset=[c] if c in pvt.columns else [])
        edited_pvt = st.data_editor(styled_pvt, use_container_width=True, key="pay_editor")
        
        sel_rows = edited_pvt[edited_pvt['Select 👁️'] == True].index.tolist()
        if sel_rows:
            sel_pay_ro = pvt.loc[sel_rows[0], 'RO Name']
            sel_bucket = st.selectbox("Filter Pending Status:", [c for c in cols_order[:-1] if c in pvt.columns])
            filtered_pay = df_pay[df_pay['Department Bucket'] == sel_bucket].copy() if sel_pay_ro == 'Grand Total' else df_pay[(df_pay['RO Name'] == sel_pay_ro) & (df_pay['Department Bucket'] == sel_bucket)].copy()
            if search_q: filtered_pay = filtered_pay[filtered_pay.astype(str).apply(lambda x: x.str.contains(search_q, case=False, regex=False)).any(axis=1)]
            st.dataframe(filtered_pay, use_container_width=True)

# ==========================================
# E. CPK & UTILIZATION
# ==========================================
elif choice == "💰 Network Utilization":
    st.markdown(f"<h2>Network Utilization & CPK (Filtered: {days_duration} Days)</h2>", unsafe_allow_html=True)
    df_cpk_raw = filter_df_by_date(raw_data_cache.get('CPK_Raw', pd.DataFrame()), 'Date_DT')

    if not df_cpk_raw.empty:
        # Generate CPK Summaries dynamically
        df_updn = df_cpk_raw.copy()
        df_updn['Trip_Rate'] = np.where(df_updn['Trips'] > 0, df_updn['Cost'] / df_updn['Trips'], 0).round(2)
        df_updn['Trip_Rate_Str'] = "₹" + df_updn['Trip_Rate'].astype(str)
        df_updn['Total_Cap_Raw'] = df_updn['Cap'] * df_updn['Trips']
        
        # We'll just show the raw data logic with simple groupbys for Route / Vehicle
        st.info("Utilizing Network CPK Data")
        
        col1, col2 = st.columns([1, 2])
        z_filter = col1.selectbox("Filter Zone:", ["ALL"] + sorted(df_updn['Zone'].dropna().unique()))
        if z_filter != "ALL": df_updn = df_updn[df_updn['Zone'] == z_filter]
        
        agg = df_updn.groupby(['Zone', 'RO_Clean', 'Final_Type', 'Final_Route']).agg(
            Total_Trips=('Trips', 'sum'), Total_Carried_Wt=('Wt', 'sum'), Total_Trip_Cost=('Cost', 'sum'), Total_Capacity=('Total_Cap_Raw', 'sum'),
            VendorName=('VendorName', lambda x: ', '.join(sorted(set(x.dropna().astype(str)))))
        ).reset_index()
        agg['Overall CPK'] = np.where(agg['Total_Carried_Wt'] > 0, agg['Total_Trip_Cost'] / agg['Total_Carried_Wt'], 0)
        agg['Overall Util %'] = np.where(agg['Total_Capacity'] > 0, agg['Total_Carried_Wt'] / agg['Total_Capacity'], 0)
        
        for col in ['Overall CPK', 'Total Trip Cost']: agg[col] = agg[col].apply(lambda x: f"₹{x:.2f}" if isinstance(x, (int, float)) else x)
        agg['Overall Util %'] = agg['Overall Util %'].apply(lambda x: f"{x * 100:.2f}%" if isinstance(x, (int, float)) else x)
        
        st.dataframe(agg.sort_values(by='Final_Type'), use_container_width=True)

# ==========================================
# F. MOM
# ==========================================
elif choice == "📝 Today's Call Action Plan":
    st.markdown("<h2>Today's Call Action Plan (MOM)</h2>", unsafe_allow_html=True)
    ap_data = load_action_plans()
    records = [{"S.No.": i+1, "Origin RO": ref.split(" || ", 1)[0] if " || " in ref else "UNKNOWN", "Module Name": mod, "Reference": ref.split(" || ", 1)[1] if " || " in ref else ref, "Action": plan} for mod, plans in ap_data.items() for i, (ref, plan) in enumerate(plans.items())]
    if not records: st.info("❌ Koi Action Plan save nahi hua hai.")
    else:
        df_ap = pd.DataFrame(records)
        st.dataframe(df_ap, use_container_width=True, hide_index=True)
