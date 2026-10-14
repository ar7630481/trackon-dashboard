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
# 1. PAGE SETUP (Professional VIP Dark Theme)
# ==========================================
st.set_page_config(page_title="Trackon Command Center", page_icon="🚀", layout="wide", initial_sidebar_state="expanded")

# VIP Custom CSS for Enterprise Look
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
    "MCD_VENDOR": os.path.join(DATA_DIR, "mcd_vendor.xlsx"),
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
# 2. AUTHENTICATION (Roles & Vendor Logic)
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

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'role' not in st.session_state:
    st.session_state['role'] = None

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
        if clean_n in col_map: return col_map[clean_n]
    return None

def format_hrs_safe(hrs):
    if pd.isna(hrs): return ""
    sign = "-" if hrs < 0 else ""
    hrs = abs(hrs)
    h = int(hrs)
    m = int(round((hrs - h) * 60))
    if m == 60: h += 1; m = 0
    return f"{sign}{h}:{m:02d}"

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

def load_action_plans():
    path = FILE_MAP["ACTION_PLANS"]
    if os.path.exists(path):
        try:
            with open(path, 'r') as f: return json.load(f)
        except: return {}
    return {}

def save_action_plans(data):
    with open(FILE_MAP["ACTION_PLANS"], 'w') as f:
        json.dump(data, f)

# ==========================================
# 4. VIP EXCEL GENERATOR
# ==========================================
def generate_vip_executive_report_to_disk(data_dict, output_path=None):
    with pd.ExcelWriter(output_path or FILE_MAP["EXECUTIVE_REPORT"], engine='xlsxwriter') as writer:
        workbook = writer.book
        header_format = workbook.add_format({'bold': True, 'bg_color': '#1E3A8A', 'font_color': 'white', 'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True})
        
        def apply_manager_formatting(sheet_name, df_to_write):
            worksheet = writer.sheets[sheet_name]
            for col_num, value in enumerate(df_to_write.columns.values):
                worksheet.write(0, col_num, value, header_format)
            for i, col in enumerate(df_to_write.columns):
                if not df_to_write.empty:
                    col_len = max(df_to_write[col].astype(str).map(len).max(), len(str(col))) + 2
                else:
                    col_len = len(str(col)) + 2
                worksheet.set_column(i, i, min(col_len, 35))

        if 'Legwise_Route_Summary' in data_dict:
            df_ops = data_dict['Legwise_Route_Summary'].copy()
            cols_to_drop = ['OO_Cnt', 'LO_Cnt', 'OL_Cnt', 'LL_Cnt', 'Ontime_Dep_IT_Cnt', 'Late_Dep_IT_Cnt']
            df_ops = df_ops.drop(columns=[c for c in cols_to_drop if c in df_ops.columns], errors='ignore')
            
            def extract_pct(x):
                if isinstance(x, str) and '%' in x:
                    try: return float(x.split('%')[0].strip())
                    except: return 0.0
                return 0.0
                
            if 'Late Dep, Late Arr %' in df_ops.columns:
                df_ops['SortKey_Temp'] = df_ops['Late Dep, Late Arr %'].apply(extract_pct)
                df_ops['Is_Single_Trip'] = df_ops['Total_Trips'] <= 1
                df_ops = df_ops.sort_values(by=['Is_Single_Trip', 'SortKey_Temp'], ascending=[True, False]).drop(columns=['SortKey_Temp', 'Is_Single_Trip'])

            def format_val(x):
                if isinstance(x, str) and '%' in x and '(' in x:
                    try:
                        pct = x.split('%')[0] + '%'
                        count = x.split('(')[1].replace(')', '')
                        if count == '0': return "0%"
                        return f"{pct} | 🚚 {count}"
                    except: return x
                return x
                
            pct_cols = [c for c in df_ops.columns if '%' in c]
            for c in pct_cols: df_ops[c] = df_ops[c].apply(format_val)

            def ops_excel_color(val, col):
                if not isinstance(val, str) or '%' not in val: return ''
                try: pct = float(val.split('%')[0].strip())
                except: return ''
                if pct == 0: return 'color: #6C757D' 
                if 'Late Dep, Late Arr' in col: return 'background-color: #F8D7DA; color: #721C24' 
                elif 'Ontime Dep, Ontime Arr' in col: return 'background-color: #D4EDDA; color: #155724' 
                elif 'Ontime Dep, Late Arr' in col: return 'background-color: #FFF3CD; color: #856404' 
                elif 'Late Dep, Ontime Arr' in col: return 'background-color: #E2D9F3; color: #4A148C' 
                return ''

            styled_ops = df_ops.style
            for col in pct_cols:
                if hasattr(styled_ops, 'map'): styled_ops = styled_ops.map(lambda x, c=col: ops_excel_color(x, c), subset=[col])
                else: styled_ops = styled_ops.applymap(lambda x, c=col: ops_excel_color(x, c), subset=[col])
            
            styled_ops.to_excel(writer, sheet_name='Operations_Summary', index=False)
            apply_manager_formatting('Operations_Summary', df_ops)
            
        if 'Legwise_Processed_Data' in data_dict:
            df_ops_raw = data_dict['Legwise_Processed_Data'].copy()
            df_ops_raw.to_excel(writer, sheet_name='Operations_Raw', index=False)
            apply_manager_formatting('Operations_Raw', df_ops_raw)

        if 'Vendor_Perf_Summary' in data_dict:
            df_vperf = data_dict['Vendor_Perf_Summary'].copy()
            df_vperf.to_excel(writer, sheet_name='Vendor_Perf_Summary', index=False)
            apply_manager_formatting('Vendor_Perf_Summary', df_vperf)
            
        if 'Vendor_Perf_Raw' in data_dict:
            df_vperf_raw = data_dict['Vendor_Perf_Raw'].copy()
            df_vperf_raw.to_excel(writer, sheet_name='Vendor_Perf_Raw', index=False)
            apply_manager_formatting('Vendor_Perf_Raw', df_vperf_raw)

        if 'Master_Database' in data_dict:
            df_pay = data_dict['Master_Database'].copy()
            pvt = pd.pivot_table(df_pay, values='Invoice Id', index='RO Name', columns='Department Bucket', aggfunc='count', fill_value=0, margins=True, margins_name='Grand Total')
            cols_order = ["1. USER / DRAFT PENDING", "2. COST CONTROL PENDING", "3. FINANCE PENDING", "4. PAYMENT PENDING", "5. OTHER PENDING", "Grand Total"]
            existing_cols = [c for c in cols_order if c in pvt.columns]
            pvt = pvt.reindex(columns=existing_cols).reset_index()
            
            def pay_excel_color(val, col_name):
                if pd.isna(val) or val == 0: return ''
                if col_name == '1. USER / DRAFT PENDING': return 'background-color: #F8D7DA; color: #721C24; font-weight: bold' 
                elif col_name == '2. COST CONTROL PENDING': return 'background-color: #FFF3CD; color: #856404; font-weight: bold'
                elif col_name == '3. FINANCE PENDING': return 'background-color: #FFF8E1; color: #856404; font-weight: bold'
                return ''
                
            styled_pay = pvt.style
            for col in existing_cols:
                if hasattr(styled_pay, 'map'): styled_pay = styled_pay.map(lambda x, c=col: pay_excel_color(x, c), subset=[col])
                else: styled_pay = styled_pay.applymap(lambda x, c=col: pay_excel_color(x, c), subset=[col])
            
            styled_pay.to_excel(writer, sheet_name='Payment_Summary', index=False)
            apply_manager_formatting('Payment_Summary', pvt)
            df_pay.to_excel(writer, sheet_name='Payment_Raw', index=False)
            apply_manager_formatting('Payment_Raw', df_pay)

        def add_total_row_cpk(df):
            if df.empty: return df
            tot_trips = df['Total Trips'].sum() if 'Total Trips' in df.columns else 0
            tot_cap = df['Total Capacity'].sum() if 'Total Capacity' in df.columns else 0
            tot_wt = df['Total Carried Wt'].sum() if 'Total Carried Wt' in df.columns else 0
            tot_cost = df['Total Trip Cost'].sum() if 'Total Trip Cost' in df.columns else 0
            tot_cpk = tot_cost / tot_wt if tot_wt > 0 else 0
            tot_util = tot_wt / tot_cap if tot_cap > 0 else 0
            
            tot_dict = {c: '-' for c in df.columns}
            if 'Zone' in df.columns: tot_dict['Zone'] = 'TOTAL'
            if 'VendorRO' in df.columns: tot_dict['VendorRO'] = 'TOTAL'
            if 'Total Trips' in df.columns: tot_dict['Total Trips'] = tot_trips
            if 'Total Capacity' in df.columns: tot_dict['Total Capacity'] = tot_cap
            if 'Total Carried Wt' in df.columns: tot_dict['Total Carried Wt'] = tot_wt
            if 'Total Trip Cost' in df.columns: tot_dict['Total Trip Cost'] = tot_cost
            if 'Overall CPK' in df.columns: tot_dict['Overall CPK'] = tot_cpk
            if 'Overall Util %' in df.columns: tot_dict['Overall Util %'] = tot_util
            return pd.concat([df, pd.DataFrame([tot_dict])], ignore_index=True)

        for sheet, df_key in [('CPK_Nat_Zon', 'CPK_National_Zonal_Master'), ('CPK_Feed_Reg', 'CPK_Feeder_Regional'), ('CPK_Coloader', 'CPK_Coloader')]:
            if df_key in data_dict and not data_dict[df_key].empty:
                df_cpk = data_dict[df_key].copy().sort_values(by='Overall Util %', ascending=True)
                df_cpk = add_total_row_cpk(df_cpk)
                for col in ['Overall CPK', 'Total Trip Cost']: 
                    if col in df_cpk.columns: df_cpk[col] = df_cpk[col].apply(lambda x: f"₹{x:.2f}" if isinstance(x, (int, float)) else x)
                if 'Overall Util %' in df_cpk.columns: df_cpk['Overall Util %'] = df_cpk['Overall Util %'].apply(lambda x: f"{x * 100:.2f}%" if isinstance(x, (int, float)) else x)
                df_cpk.to_excel(writer, sheet_name=sheet, index=False)
                apply_manager_formatting(sheet, df_cpk)

        if 'CPK_Raw_Data' in data_dict:
            df_cpk_raw = data_dict['CPK_Raw_Data'].copy()
            df_cpk_raw.to_excel(writer, sheet_name='Network_Raw', index=False)
            apply_manager_formatting('Network_Raw', df_cpk_raw)

# ==========================================
# 5. MAIN DATA PROCESSING
# ==========================================
@st.cache_data(ttl=3600, show_spinner=False)
def get_processed_data_cached(file_timestamps):
    data_for_export = {}
    
    # --- EXTRACT ZONE MAPPING FROM BRANCH MASTER ---
    ro_zone_map = {}
    branch_ro_map = {}
    branch_zone_map = {}
    
    if os.path.exists(FILE_MAP["BRANCH_MASTER"]):
        df_brn_master = pd.read_excel(FILE_MAP["BRANCH_MASTER"], sheet_name="Sheet1")
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
            if req not in df_pay.columns: df_pay[req] = ""
                
        df_pay['Vendor Name'] = df_pay['Vendor Name'].fillna('').astype(str).str.upper().str.strip()
        df_pay['Category'] = df_pay['Category'].fillna('').astype(str).str.strip()
        df_pay['Status'] = df_pay['Status'].fillna('').astype(str).str.upper()
        df_pay['Pending With'] = df_pay['Pending With'].fillna('').astype(str).str.upper()
        
        df_pay['RO Name Clean'] = df_pay['RO Name'].astype(str).str.strip().str.upper()
        df_pay['Zone'] = df_pay['RO Name Clean'].map(ro_zone_map).fillna('UNKNOWN ZONE')
        
        valid_cats = ["Contract - Feeder Connection vehicle charges", "Market - Feeder Connection vehicle charges", 
                      "Market Vehicle Hired -Linehaul", "Contract Network Vehicle Hired - Regional", 
                      "Contract Network Vehicle Hired - Zonal", "Contract Network Vehicle Hired - National"]
        df_pay = df_pay[df_pay['Category'].isin(valid_cats)]
        
        vip_vends = ["SHRI GANPATI", "MOHD ASLAM", "MEHTAROAD", "E WHEELS", "TEJAS", "T T TRANSPORT", 
                     "APL EXPRESS", "GOTRUCKS", "RADHA RANI", "FASTLANE", "MMM LOGISTICS", "ATA ROADWAYS", "ZAST", "FLEETX"]
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
        df_pay['Department Bucket'] = np.select(conds, ["4. PAYMENT PENDING", "3. FINANCE PENDING", "1. USER / DRAFT PENDING", "2. COST CONTROL PENDING"], "5. OTHER PENDING")
        
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
        df_leg_all['MCD_StartDate_DT'] = pd.to_datetime(df_leg_all['MCD_StartDate'], dayfirst=True, errors='coerce')
        df_leg_all['Leg_Num'] = df_leg_all['Legwise'].astype(str).str.extract(r'(\d+)').astype(float).fillna(1)
        
        df_leg_all = df_leg_all.sort_values(by=['RouteCode', 'MCD_StartDate_DT', 'Min_CD_StartDatetime'])
        dedup = df_leg_all.groupby(['RouteCode', 'MCD_StartDate_DT'])['MasterCDNo'].first().reset_index()
        df_leg_all = df_leg_all.merge(dedup, on=['RouteCode', 'MCD_StartDate_DT', 'MasterCDNo'])
        df_leg_all['Legs'] = df_leg_all['CD_FromBranch'].astype(str) + " to " + df_leg_all['CD_ToBranch'].astype(str)
        df_leg_all.rename(columns={'Min_CD_StartDatetime': 'Actual Departure Time', 'Max_CD_EndDatetime': 'Actual Arrival Time', 'Route': 'Route Path'}, inplace=True)
        
        df_leg_all[['Origin', 'Destination']] = df_leg_all['Route Path'].apply(lambda x: pd.Series(extract_orig_dest(x)))
        df_leg_all['CD_FromBranch_Clean'] = df_leg_all['CD_FromBranch'].astype(str).str.strip().str.upper()
        
        # 🟢 CRITICAL FIX: MAP RO USING ROUTE ORIGIN FIRST (Fixes MUMH Missing RO issue)
        df_leg_all['Origin RO'] = df_leg_all['Origin'].map(branch_ro_map).combine_first(df_leg_all['CD_FromBranch_Clean'].map(branch_ro_map)).fillna('Missing RO')
        df_leg_all['Zone'] = df_leg_all['Origin'].map(branch_zone_map).combine_first(df_leg_all['CD_FromBranch_Clean'].map(branch_zone_map)).fillna('UNKNOWN ZONE')
        
        df_leg_all['E2E_Pair'] = df_leg_all['Route Path'].apply(get_route_pair)
        df_leg_all.rename(columns={'LH_Type': 'LH Type'}, inplace=True)
        df_leg_all = df_leg_all.merge(route_tat_master[['Route Code', 'Scheduled TAT Till Destination']], left_on='RouteCode', right_on='Route Code', how='left')
        
        def get_sch_time(r, day_c, time_c):
            try:
                if pd.isna(r['MCD_StartDate_DT']) or pd.isna(r[day_c]): return pd.NaT
                day_offset = float(r[day_c])
                d = r['MCD_StartDate_DT'] + pd.to_timedelta(day_offset, unit='D')
                t_str = str(r[time_c]).strip()
                if t_str == 'nan' or not t_str: return pd.NaT
                return pd.to_datetime(d.strftime('%Y-%m-%d') + ' ' + str(pd.to_datetime(t_str).time()))
            except: return pd.NaT

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
        
        df_vperf = df_leg_all.copy()
        df_vperf['Given_Secs'] = (df_vperf['Scheduled Arrival Time'] - df_vperf['Scheduled Departure Time']).dt.total_seconds()
        df_vperf['Actual_Secs'] = (df_vperf['Actual Arrival Time'] - df_vperf['Actual Departure Time']).dt.total_seconds()
        
        df_vperf['Given Driving Hours_Raw'] = df_vperf['Given_Secs'] / 3600.0
        df_vperf['Actual Driving Hours_Raw'] = df_vperf['Actual_Secs'] / 3600.0
        df_vperf['Delay Hours_Raw'] = df_vperf['Actual Driving Hours_Raw'] - df_vperf['Given Driving Hours_Raw']
        
        def assign_vendor_remark(row):
            if pd.isna(row['Actual Arrival Time']): return "In-Transit"
            if pd.isna(row['Delay Hours_Raw']): return "Missing Schedule"
            if row['Delay Hours_Raw'] <= 0.25: return "Ontime Arrival"
            return "Late Arrival"
            
        df_vperf['Remark with 15 min waiver'] = df_vperf.apply(assign_vendor_remark, axis=1)
        df_vperf['Given Driving Hours'] = df_vperf['Given Driving Hours_Raw'].apply(format_hrs_safe)
        df_vperf['Actual Driving Hours'] = df_vperf['Actual Driving Hours_Raw'].apply(format_hrs_safe)
        df_vperf['Delay Hours'] = df_vperf['Delay Hours_Raw'].apply(format_hrs_safe)
        
        df_vperf['Actual Departure Time'] = df_vperf['Actual Departure Time'].dt.strftime('%d-%m-%Y %H:%M').fillna('-')
        df_vperf['Actual Arrival Time'] = df_vperf['Actual Arrival Time'].dt.strftime('%d-%m-%Y %H:%M').fillna('-')
        
        perf_cols = ['Route Path', 'Legwise', 'Legs', 'Actual Departure Time', 'Actual Arrival Time', 'Given Driving Hours', 'Actual Driving Hours', 'Delay Hours', 'Remark with 15 min waiver', 'VendorName', 'VehicleNo', 'MasterCDNo', 'RouteCode', 'Zone', 'Origin RO']
        df_vperf_raw = df_vperf[perf_cols + ['MCD_StartDate_DT']].copy()
        df_vperf_raw['Date'] = df_vperf_raw['MCD_StartDate_DT'].dt.strftime('%d-%m-%Y')
        df_vperf_raw = df_vperf_raw.drop(columns=['MCD_StartDate_DT'])
        
        sum_cols = ['Zone', 'Origin RO', 'Route Path', 'Legwise', 'Legs', 'VendorName']
        perf_sum = df_vperf_raw.groupby(sum_cols).agg(
            Total_Trips=('MasterCDNo', 'count'),
            Ontime_Cnt=('Remark with 15 min waiver', lambda x: (x == 'Ontime Arrival').sum()),
            Late_Cnt=('Remark with 15 min waiver', lambda x: (x == 'Late Arrival').sum()),
            Transit_Cnt=('Remark with 15 min waiver', lambda x: (x == 'In-Transit').sum())
        ).reset_index()
        
        perf_sum['Ontime Arrival'] = perf_sum.apply(lambda r: format_pct_cnt(r['Ontime_Cnt'], r['Total_Trips']), axis=1)
        perf_sum['Late Arrival'] = perf_sum.apply(lambda r: format_pct_cnt(r['Late_Cnt'], r['Total_Trips']), axis=1)
        perf_sum['In-Transit'] = perf_sum.apply(lambda r: format_pct_cnt(r['Transit_Cnt'], r['Total_Trips']), axis=1)
        
        perf_sum['Sort_Pct'] = np.where(perf_sum['Total_Trips'] > 0, perf_sum['Ontime_Cnt'] / perf_sum['Total_Trips'], 0)
        perf_sum = perf_sum.sort_values('Sort_Pct', ascending=True).drop(columns=['Ontime_Cnt', 'Late_Cnt', 'Transit_Cnt', 'Sort_Pct'])
        
        data_for_export['Vendor_Perf_Summary'] = perf_sum
        data_for_export['Vendor_Perf_Raw'] = df_vperf_raw
        del df_vperf, df_vperf_raw, perf_sum
        
        df_leg = df_leg_all[(df_leg_all['MCD_Created_By'] == 'SCHEDULED') & (df_leg_all['LH Type'].isin(['National LH', 'Zonal LH']))].copy()
        
        def calc_status(act, sch, mode):
            if pd.isna(act): return f"No {mode}" if mode == 'Dep' else "In-Transit"
            if pd.isna(sch): return "Missing Sch"
            if (act - sch).total_seconds() / 60 <= 15: return f"Ontime {mode}"
            return f"Late {mode}"
            
        df_leg['Dep_Status'] = df_leg.apply(lambda r: calc_status(r['Actual Departure Time'], r['Scheduled Departure Time'], 'Dep'), axis=1)
        df_leg['Arr_Status'] = df_leg.apply(lambda r: calc_status(r['Actual Arrival Time'], r['Scheduled Arrival Time'], 'Arr'), axis=1)
        df_leg['Remark'] = df_leg['Dep_Status'] + ", " + df_leg['Arr_Status']

        def generate_summary(df_group, group_cols):
            df_valid = df_group.copy()
            trip_col = 'Total_Trips'
            df_valid['OO_Cnt'] = df_valid['Remark'].apply(lambda x: 1 if 'Ontime Dep, Ontime Arr' in str(x) else 0)
            df_valid['LL_Cnt'] = df_valid['Remark'].apply(lambda x: 1 if 'Late Dep, Late Arr' in str(x) else 0)
            df_valid['LO_Cnt'] = df_valid['Remark'].apply(lambda x: 1 if 'Late Dep, Ontime Arr' in str(x) else 0)
            df_valid['OL_Cnt'] = df_valid['Remark'].apply(lambda x: 1 if 'Ontime Dep, Late Arr' in str(x) else 0)
            df_valid['Ontime_Dep_IT_Cnt'] = df_valid['Remark'].apply(lambda x: 1 if 'Ontime Dep, In-Transit' in str(x) else 0)
            df_valid['Late_Dep_IT_Cnt'] = df_valid['Remark'].apply(lambda x: 1 if 'Late Dep, In-Transit' in str(x) else 0)
            
            agg_dict = {'MasterCDNo': 'count', 'OO_Cnt': 'sum', 'LO_Cnt': 'sum', 'OL_Cnt': 'sum', 'LL_Cnt': 'sum', 'Ontime_Dep_IT_Cnt': 'sum', 'Late_Dep_IT_Cnt': 'sum'}
            summary = df_valid.groupby(group_cols).agg(agg_dict).reset_index()
            summary.rename(columns={'MasterCDNo': trip_col}, inplace=True)
            
            summary['Ontime Dep, Ontime Arr %'] = summary.apply(lambda r: format_pct_cnt(r['OO_Cnt'], r[trip_col]), axis=1)
            summary['Late Dep, Late Arr %'] = summary.apply(lambda r: format_pct_cnt(r['LL_Cnt'], r[trip_col]), axis=1)
            summary['Late Dep, Ontime Arr %'] = summary.apply(lambda r: format_pct_cnt(r['LO_Cnt'], r[trip_col]), axis=1)
            summary['Ontime Dep, Late Arr %'] = summary.apply(lambda r: format_pct_cnt(r['OL_Cnt'], r[trip_col]), axis=1)
            summary['Ontime Dep, In-Transit'] = summary.apply(lambda r: format_pct_cnt(r['Ontime_Dep_IT_Cnt'], r[trip_col]), axis=1)
            summary['Late Dep, In-Transit'] = summary.apply(lambda r: format_pct_cnt(r['Late_Dep_IT_Cnt'], r[trip_col]), axis=1)
            
            return summary.sort_values(by=['LH Type', 'E2E_Pair', 'Origin', 'Route Path', 'Leg_Num'])
            
        leg_sum = generate_summary(df_leg, ['Zone', 'LH Type', 'E2E_Pair', 'Origin RO', 'Route Path', 'Origin', 'Destination', 'Leg_Num', 'Legwise', 'Legs'])
        data_for_export['Legwise_Route_Summary'] = leg_sum
        
        dt_cols = ['Scheduled Departure Time', 'Actual Departure Time', 'Scheduled Arrival Time', 'Actual Arrival Time']
        for c in dt_cols: df_leg[c] = df_leg[c].dt.strftime('%d-%m-%Y %H:%M').fillna('')
        df_leg['MCD_StartDate'] = pd.to_datetime(df_leg['MCD_StartDate_DT']).dt.strftime('%d-%m-%Y')
        df_leg_final = df_leg.drop(columns=['Leg_Num', 'E2E_Pair'], errors='ignore')
        data_for_export['Legwise_Processed_Data'] = df_leg_final
        del df_leg, df_leg_all, df_rte, route_tat_master

    # --- MODULE 2: CPK AND UTILIZATION ---
    if os.path.exists(FILE_MAP["CPK_UTIL"]) and os.path.exists(FILE_MAP["ROUTE_LOOKUP"]):
        try: df_raw = pd.read_excel(FILE_MAP["CPK_UTIL"], sheet_name='ContractVehicle_DetailReport')
        except: df_raw = pd.read_excel(FILE_MAP["CPK_UTIL"])
            
        df_lookup = pd.read_excel(FILE_MAP["ROUTE_LOOKUP"])
        df_raw.columns = df_raw.columns.astype(str).str.strip()
        df_lookup.columns = df_lookup.columns.astype(str).str.strip()
        if 'VehicleUsageType' in df_raw.columns: df_raw = df_raw[df_raw['VehicleUsageType'] != 'VehicleUsageType']

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
            if raw_route_col: df_raw['Final_Route'] = df_raw['Final_Route'].combine_first(df_raw[raw_route_col])
                
            df_raw['Final_Type'] = df_raw.get('LKP_TYPE', pd.Series([np.nan]*len(df_raw)))
            raw_type_col = get_col(df_raw, ['type', 'vehicletype', 'category'])
            if raw_type_col: df_raw['Final_Type'] = df_raw['Final_Type'].combine_first(df_raw[raw_type_col])
                
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
        df_raw['Final_Type'] = df_raw['Final_Type'].apply(lambda x: f"MCD-{x}" if isinstance(x, str) and "LH" in x.upper() and "MCD" not in x.upper() else x).fillna('Unlisted Type')

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
            if fb and tb and fb != 'NAN' and tb != 'NAN': return f"{min(fb, tb)}-{max(fb, tb)}"
            r = str(row.get('Final_Route', '')).strip().upper()
            pts = r.replace(' TO ', '-').split('-')
            if len(pts) >= 2: return f"{min(pts[0].strip(), pts[-1].strip())}-{max(pts[0].strip(), pts[-1].strip())}"
            return r
            
        df_raw['SortKey'] = df_raw.apply(create_sort_key, axis=1)
        ro_col = get_col(df_raw, ['vendorro', 'ro']) or 'VendorRO'
        df_raw['RO_Clean'] = df_raw.get(ro_col, pd.Series(['UNKNOWN']*len(df_raw))).astype(str).str.upper().str.strip()
        df_raw['Zone'] = df_raw['RO_Clean'].map(ro_zone_map).fillna('UNKNOWN ZONE')
        
        target_ros = ['PATRO', 'CCURO', 'BBSRO', 'GAURO', 'MUMRO', 'DELRO', 'LKORO']
        
        df_raw['Date_DT'] = pd.to_datetime(df_raw['Date'], errors='coerce', dayfirst=True)
        if os.path.exists(FILE_MAP["RATE_CORRECTIONS"]):
            try:
                with open(FILE_MAP["RATE_CORRECTIONS"], 'r') as f: corrections = json.load(f)
                for corr in corrections:
                    route_mask = df_raw['Final_Route'].astype(str).str.upper() == str(corr['route']).strip().upper()
                    cap_mask = pd.to_numeric(df_raw['Cap'], errors='coerce') == float(corr['capacity'])
                    date_mask = df_raw['Date_DT'] >= pd.to_datetime(corr['eff_date'])
                    mask = route_mask & cap_mask & date_mask
                    df_raw.loc[mask, 'Cost'] = float(corr['new_cost']) * df_raw.loc[mask, 'Trips']
            except: pass 
        
        df_updn = df_raw[~df_raw['Final_Type'].str.upper().str.contains('OFD|PICKUP', na=False)].copy()
        target_keys = df_updn[df_updn['RO_Clean'].isin(target_ros)]['SortKey'].unique()
        df_updn = df_updn[df_updn['SortKey'].isin(target_keys)]
        
        df_updn['Final_Type'] = df_updn['Final_Type'].replace({
            'MCD-National LH': 'National LH', 'MCD-Zonal LH': 'Zonal LH',
            'MCD-Regional LH': 'Regional LH', 'MCD-Feeder': 'Feeder'
        })
        data_for_export['CPK_Raw_Data'] = df_updn

        if not df_updn.empty:
            df_updn['Trip_Rate'] = np.where(df_updn['Trips'] > 0, df_updn['Cost'] / df_updn['Trips'], 0).round(2)
            df_updn['Trip_Rate_Str'] = "₹" + df_updn['Trip_Rate'].astype(str)
            df_updn['Total_Cap_Raw'] = df_updn['Cap'] * df_updn['Trips']
            
            nz_mask = df_updn['Final_Type'].isin(['National LH', 'Zonal LH'])
            if nz_mask.any():
                agg_nz_updown = df_updn[nz_mask].groupby(['RO_Clean', 'Zone', 'Final_Route', 'Final_Type', 'Cap', 'SortKey', 'Trip_Rate']).agg(
                    Total_Trips=('Trips', 'sum'), Total_Carried_Wt=('Wt', 'sum'), Total_Trip_Cost=('Cost', 'sum'),
                    VendorName=('VendorName', lambda x: ', '.join(sorted(set(x.dropna().astype(str))))),
                    Per_Trip_Cost=('Trip_Rate_Str', lambda x: ', '.join(sorted(set(x.dropna().astype(str)))))
                ).reset_index()
                agg_nz_updown['Total Capacity'] = agg_nz_updown['Cap'] * agg_nz_updown['Total_Trips']
                agg_nz_updown['Overall CPK'] = np.where(agg_nz_updown['Total_Carried_Wt'] > 0, agg_nz_updown['Total_Trip_Cost'] / agg_nz_updown['Total_Carried_Wt'], 0)
                agg_nz_updown['Overall Util %'] = np.where(agg_nz_updown['Total Capacity'] > 0, agg_nz_updown['Total_Carried_Wt'] / agg_nz_updown['Total Capacity'], 0)
                nz_updown_final = agg_nz_updown[['Zone', 'RO_Clean', 'Final_Route', 'Final_Type', 'Overall CPK', 'Overall Util %', 'Cap', 'Total Capacity', 'Total_Carried_Wt', 'Per_Trip_Cost', 'Total_Trip_Cost', 'Total_Trips', 'VendorName', 'SortKey']]
                nz_updown_final.columns = ["Zone", "VendorRO", "Route (UP/DOWN)", "Type", "Overall CPK", "Overall Util %", "VehCap (Base)", "Total Capacity", "Total Carried Wt", "Per Trip Cost", "Total Trip Cost", "Total Trips", "Vendor(s)", "SortKey"]
                data_for_export['CPK_National_Zonal_UpDown'] = nz_updown_final.sort_values(by=['Type', 'SortKey'])
                
                agg_nz_master = df_updn[nz_mask].groupby(['RO_Clean', 'Zone', 'SortKey', 'Final_Type']).agg(
                    Total_Trips=('Trips', 'sum'), Total_Carried_Wt=('Wt', 'sum'), Total_Trip_Cost=('Cost', 'sum'), Total_Capacity=('Total_Cap_Raw', 'sum'),
                    Unique_Vendors=('VendorName', lambda x: x.nunique()), VendorName=('VendorName', lambda x: ', '.join(sorted(set(x.dropna().astype(str))))),
                    Route_Path=('Final_Route', lambda x: ', '.join(sorted(set(x.dropna().astype(str))))),
                    Per_Trip_Cost=('Trip_Rate_Str', lambda x: ', '.join(sorted(set(x.dropna().astype(str)))))
                ).reset_index()
                agg_nz_master['Overall CPK'] = np.where(agg_nz_master['Total_Carried_Wt'] > 0, agg_nz_master['Total_Trip_Cost'] / agg_nz_master['Total_Carried_Wt'], 0)
                agg_nz_master['Overall Util %'] = np.where(agg_nz_master['Total_Capacity'] > 0, agg_nz_master['Total_Carried_Wt'] / agg_nz_master['Total_Capacity'], 0)
                nz_master_final = agg_nz_master[['Zone', 'RO_Clean', 'Route_Path', 'Final_Type', 'Overall CPK', 'Overall Util %', 'Total_Capacity', 'Total_Carried_Wt', 'Per_Trip_Cost', 'Total_Trip_Cost', 'Total_Trips', 'Unique_Vendors', 'VendorName', 'SortKey']]
                nz_master_final.columns = ["Zone", "VendorRO", "Route Path", "Type", "Overall CPK", "Overall Util %", "Total Capacity", "Total Carried Wt", "Per Trip Cost", "Total Trip Cost", "Total Trips", "Unique Vendors", "Vendor(s)", "Route Pair"]
                data_for_export['CPK_National_Zonal_Master'] = nz_master_final.sort_values(by=['Type', 'Overall Util %'])

            fr_mask = df_updn['Final_Type'].isin(['Regional LH', 'Feeder'])
            if fr_mask.any():
                agg_fr = df_updn[fr_mask].groupby(['RO_Clean', 'Zone', 'Vehicle No', 'Final_Type', 'Cap', 'Trip_Rate']).agg(
                    Total_Trips=('Trips', 'sum'), Total_Carried_Wt=('Wt', 'sum'), Total_Trip_Cost=('Cost', 'sum'),
                    VendorName=('VendorName', lambda x: ', '.join(sorted(set(x.dropna().astype(str))))),
                    Per_Trip_Cost=('Trip_Rate_Str', lambda x: ', '.join(sorted(set(x.dropna().astype(str))))),
                    Routes_Covered=('Final_Route', lambda x: ', '.join(sorted(set(x.dropna().astype(str)))))
                ).reset_index()
                agg_fr['Total Capacity'] = agg_fr['Cap'] * agg_fr['Total_Trips']
                agg_fr['Overall CPK'] = np.where(agg_fr['Total_Carried_Wt'] > 0, agg_fr['Total_Trip_Cost'] / agg_fr['Total_Carried_Wt'], 0)
                agg_fr['Overall Util %'] = np.where(agg_fr['Total Capacity'] > 0, agg_fr['Total_Carried_Wt'] / agg_fr['Total Capacity'], 0)
                fr_final = agg_fr[['Zone', 'RO_Clean', 'Vehicle No', 'Final_Type', 'Overall CPK', 'Overall Util %', 'Cap', 'Total Capacity', 'Total_Carried_Wt', 'Per_Trip_Cost', 'Total_Trip_Cost', 'Total_Trips', 'VendorName', 'Routes_Covered']]
                fr_final.columns = ["Zone", "VendorRO", "Vehicle No", "Type", "Overall CPK", "Overall Util %", "VehCap (Base)", "Total Capacity", "Total Carried Wt", "Per Trip Cost", "Total Trip Cost", "Total Trips", "Vendor(s)", "Routes Covered"]
                data_for_export['CPK_Feeder_Regional'] = fr_final.sort_values(by=['Type', 'VendorRO', 'Overall Util %'])
            
            col_mask = df_updn['Final_Type'] == 'CO-LOADER'
            if col_mask.any():
                agg_col = df_updn[col_mask].groupby(['RO_Clean', 'Zone', 'VendorName', 'Final_Route', 'Vehicle No', 'Trip_Rate']).agg(
                    Total_Trips=('Trips', 'sum'), Total_Carried_Wt=('Wt', 'sum'), Total_Trip_Cost=('Cost', 'sum'),
                    Per_Trip_Cost=('Trip_Rate_Str', lambda x: ', '.join(sorted(set(x.dropna().astype(str)))))
                ).reset_index()
                agg_col['Cap'] = df_updn[col_mask].groupby(['RO_Clean', 'Zone', 'VendorName', 'Final_Route', 'Vehicle No', 'Trip_Rate'])['Cap'].max().values
                agg_col['Total Capacity'] = agg_col['Cap'] * agg_col['Total_Trips']
                agg_col['Overall CPK'] = np.where(agg_col['Total_Carried_Wt'] > 0, agg_col['Total_Trip_Cost'] / agg_col['Total_Carried_Wt'], 0)
                agg_col['Overall Util %'] = np.where(agg_col['Total Capacity'] > 0, agg_col['Total_Carried_Wt'] / agg_col['Total Capacity'], 0)
                col_final = agg_col[['Zone', 'RO_Clean', 'VendorName', 'Final_Route', 'Vehicle No', 'Overall CPK', 'Overall Util %', 'Cap', 'Total Capacity', 'Total_Carried_Wt', 'Per_Trip_Cost', 'Total_Trip_Cost', 'Total_Trips']]
                col_final.columns = ["Zone", "VendorRO", "Vendor(s)", "Route", "Vehicle No", "Overall CPK", "Overall Util %", "VehCap (Base)", "Total Capacity", "Total Carried Wt", "Per Trip Cost", "Total Trip Cost", "Total Trips"]
                data_for_export['CPK_Coloader'] = col_final.sort_values(by=['VendorRO', 'Overall Util %'])

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
            if os.path.exists(v): file_timestamps[k] = os.path.getmtime(v)
            
        data_for_export = get_processed_data_cached(file_timestamps)
        progress.progress(80)
        
        if not data_for_export:
            status_text.warning("No datasets were processed. Check the uploaded files.")
            return False
            
        status_text.text("⚙️ Saving Raw Database...")
        with tempfile.NamedTemporaryFile(dir=DATA_DIR, suffix='.xlsx', delete=False) as tmp:
            temp_output = tmp.name
        with pd.ExcelWriter(temp_output, engine='xlsxwriter') as writer:
            for k, v in data_for_export.items(): v.to_excel(writer, sheet_name=k, index=False)
        os.replace(temp_output, FILE_MAP["FINAL_OUTPUT"])
        progress.progress(90)
        
        status_text.text("⚙️ Generating VIP Executive Report directly to disk...")
        generate_vip_executive_report_to_disk(data_for_export)

        st.session_state.pop('_dashboard_cache', None)
        progress.progress(100)
        status_text.success("✅ Data Processed & VIP Report Generated Successfully!")
        return True
    except Exception as e:
        status_text.error(f"Error during processing: {e}")
        return False
    finally:
        if temp_output and os.path.exists(temp_output): os.remove(temp_output)
        gc.collect()

# ==========================================
# 6. SIDEBAR: ADMIN PANEL & NAVIGATION
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
        f1 = st.file_uploader("1. Payment Data", type=['xlsx'])
        if save_file(f1, "PAYMENT"): st.success("Saved!")
        f2 = st.file_uploader("2. Legwise Report", type=['xlsx'])
        if save_file(f2, "LEGWISE"): st.success("Saved!")
        f3 = st.file_uploader("3. Scheduled Route Master", type=['xlsx'])
        if save_file(f3, "ROUTE_MASTER"): st.success("Saved!")
        f4 = st.file_uploader("4. RO & Branch List", type=['xlsx'])
        if save_file(f4, "BRANCH_MASTER"): st.success("Saved!")
        f5 = st.file_uploader("5. MCD Vendor Monitoring", type=['xlsx'])
        if save_file(f5, "MCD_VENDOR"): st.success("Saved!")
        f6 = st.file_uploader("6. CPK & Util Raw File", type=['xlsx'])
        if save_file(f6, "CPK_UTIL"): st.success("Saved!")
        f7 = st.file_uploader("7. Route Lookup File", type=['xlsx'])
        if save_file(f7, "ROUTE_LOOKUP"): st.success("Saved!")

    with st.sidebar.expander("💸 Rate Correction Master"):
        with st.form("rate_form"):
            rc_route = st.text_input("Route")
            rc_cap = st.number_input("Vehicle Capacity", min_value=0)
            rc_cost = st.number_input("Corrected Trip Cost (₹)", min_value=0.0)
            rc_date = st.date_input("Effective From Date")
            submitted = st.form_submit_button("Save Rate Correction")
            if submitted:
                rate_file = FILE_MAP["RATE_CORRECTIONS"]
                rates = []
                if os.path.exists(rate_file):
                    try:
                        with open(rate_file, 'r') as f: rates = json.load(f)
                    except: pass
                rates.append({"route": rc_route.strip(), "capacity": rc_cap, "new_cost": rc_cost, "eff_date": rc_date.strftime('%Y-%m-%d')})
                with open(rate_file, 'w') as f: json.dump(rates, f)
                st.success("✅ Saved!")

    if st.sidebar.button("🚀 PROCESS & REFRESH DATA", use_container_width=True, type="primary"):
        st.session_state.pop('_dashboard_cache', None)
        get_processed_data_cached.clear() 
        gc.collect()
        if process_all_data():
            st.session_state['_processing_success'] = True
            st.rerun()
        st.stop()

# Role-Based Navigation
MENU_SHEETS = {
    "📊 Operations Summary": ('Legwise_Route_Summary', 'Legwise_Processed_Data'),
    "🚚 Vendor Performance": ('Vendor_Perf_Summary', 'Vendor_Perf_Raw'),
    "💳 Payment Dashboard": ('Master_Database',),
    "📱 Vendor Communication Hub": ('Vendor_Perf_Summary', 'Vendor_Perf_Raw', 'Legwise_Route_Summary', 'Legwise_Processed_Data', 'CPK_National_Zonal_Master', 'CPK_Raw_Data', 'Master_Database'),
    "💰 Network Utilization": ('CPK_National_Zonal_Master', 'CPK_National_Zonal_UpDown', 'CPK_Feeder_Regional', 'CPK_Coloader', 'CPK_Raw_Data'),
    "📝 Today's Call Action Plan": ()
}

if st.session_state['role'] == 'Vendor':
    menu_options = ["🚚 Vendor Performance"]
else:
    menu_options = list(MENU_SHEETS.keys())

choice = st.sidebar.radio("Navigation:", menu_options)

def file_version(path):
    stat = os.stat(path)
    return (stat.st_mtime_ns, stat.st_size)

def load_dashboard_data(page):
    if page == "📝 Today's Call Action Plan": return {"dummy": pd.DataFrame()}
    path = FILE_MAP["FINAL_OUTPUT"]
    if not os.path.exists(path): return {}
    cache_key = (file_version(path), page)
    cached = st.session_state.get('_dashboard_cache')
    if cached and cached[0] == cache_key: return cached[1]
    st.session_state.pop('_dashboard_cache', None)
    try:
        with st.spinner("Loading dashboard..."):
            with pd.ExcelFile(path, engine='openpyxl') as workbook:
                data = {name: workbook.parse(name) for name in MENU_SHEETS[page] if name in workbook.sheet_names}
        st.session_state['_dashboard_cache'] = (cache_key, data)
        return data
    except Exception as exc:
        st.error(f"Cannot read the processed Excel file: {exc}")
        st.stop()

if st.session_state.pop('_processing_success', False):
    st.success("Data refreshed successfully. Your Executive Report is ready to download!")

if os.path.exists(FILE_MAP["FINAL_OUTPUT"]) and os.path.exists(FILE_MAP["EXECUTIVE_REPORT"]) and st.session_state['role'] != 'Vendor':
    st.sidebar.markdown("---")
    st.sidebar.header("📥 Export Reports")
    try:
        with open(FILE_MAP["EXECUTIVE_REPORT"], "rb") as report_file:
            st.sidebar.download_button(
                "📄 Download VIP Executive Report", data=report_file,
                file_name=f"Trackon_Executive_Master_Report_{get_ist_now():%d_%b_%Y}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True, type="primary")
    except: pass
        
    ts = os.path.getmtime(FILE_MAP["FINAL_OUTPUT"])
    ist = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    dt = datetime.datetime.fromtimestamp(ts, tz=ist).strftime('%d %b %Y, %I:%M %p')
    st.sidebar.caption(f"📊 Dashboard Refreshed: {dt} (IST)")

data = load_dashboard_data(choice)
if not data:
    st.warning("No processed data for this page. Admin must upload the relevant files and process data.")
    st.stop()

try:
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


# -------------------------------------------------------------
# A. DAILY STANDUP (Operations Summary)
# -------------------------------------------------------------
if choice == "📊 Operations Summary":
    st.markdown("<h2>Operations Exception Summary</h2>", unsafe_allow_html=True)
    if 'Legwise_Route_Summary' in data and 'Legwise_Processed_Data' in data:
        df_leg_sum = data['Legwise_Route_Summary'].copy()
        df_raw_leg = data['Legwise_Processed_Data']
        
        col1, col2, col3 = st.columns([1, 1, 2])
        all_zones = sorted(df_leg_sum['Zone'].dropna().unique().tolist())
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

        display_cols = ['Origin RO', 'Route Path', 'Legwise', 'Legs', 'Total_Trips', 'Ontime Dep, Ontime Arr %', 'Ontime Dep, Late Arr %', 'Late Dep, Late Arr %', 'Late Dep, Ontime Arr %']
        df_display = df_leg_sum[display_cols].copy()
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
            df_display = df_display.sort_values(by=['Is_Single_Trip', 'SortKey_Temp'], ascending=[True, False]).drop(columns=['SortKey_Temp', 'Is_Single_Trip'])

        def format_val(x):
            if isinstance(x, str) and '%' in x and '(' in x:
                try:
                    pct = x.split('%')[0] + '%'
                    count = x.split('(')[1].replace(')', '')
                    if count == '0': return "0%"
                    return f"{pct} | 🚚 {count}"
                except: return x
            return x
            
        pct_cols = [c for c in df_display.columns if '%' in c and c != 'RowKey']
        for c in pct_cols: df_display[c] = df_display[c].apply(format_val)

        def color_cols(val, col):
            if not isinstance(val, str) or '%' not in val: return ''
            try: pct = float(val.split('%')[0].strip())
            except: return ''
            if pct == 0: return 'color: #78909C;' 
            if 'Late Dep, Late Arr' in col: return 'background-color: rgba(211, 47, 47, 0.2); color: #ff8a80; font-weight: bold;'
            elif 'Ontime Dep, Ontime Arr' in col: return 'background-color: rgba(56, 142, 60, 0.2); color: #b9f6ca; font-weight: bold;'
            elif 'Ontime Dep, Late Arr' in col: return 'background-color: rgba(245, 127, 23, 0.2); color: #ffe57f; font-weight: bold;'
            elif 'Late Dep, Ontime Arr' in col: return 'background-color: rgba(123, 31, 162, 0.2); color: #ea80fc; font-weight: bold;'
            return ''

        st.markdown("### Top Priority Routes Summary")
        df_display.insert(0, 'Select 👁️', False)
        ap_data = load_action_plans()
        mod_ap = ap_data.get("Operations Summary", {})
        df_display['Action Plan ✍️'] = df_display['RowKey'].map(mod_ap).fillna("")
        
        disp_cols = ['Select 👁️'] + [c for c in df_display.columns if c not in ['RowKey', 'Select 👁️']]
        styled_df = df_display[disp_cols].style
        for col in pct_cols: styled_df = styled_df.map(lambda x, c=col: color_cols(x, c), subset=[col])
            
        disabled_cols = [c for c in disp_cols if c not in ['Action Plan ✍️', 'Select 👁️']]
        edited_df = st.data_editor(styled_df, column_config={"Action Plan ✍️": st.column_config.TextColumn("Action Plan ✍️", width="large")}, disabled=disabled_cols, use_container_width=True, height=300)
        
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
            cols_to_drop = ['Scheduled TAT Till Destination', 'Actual TAT Till Destination', 'Overall Remark', 'MCD_EndDate', 'LH Type', 'Origin', 'Destination', 'Region', 'Origin RO', 'Zone']
            filtered_raw = filtered_raw.drop(columns=[c for c in cols_to_drop if c in filtered_raw.columns], errors='ignore')
            
            logical_order = ['Route Path', 'MCD_StartDate', 'Legwise', 'Legs', 'Remark', 'Scheduled Departure Time', 'Actual Departure Time', 'Scheduled Arrival Time', 'Actual Arrival Time', 'Scheduled Halting', 'Actual Halting', 'MasterCDNo', 'VendorName', 'RouteCode', 'VehicleNo']
            final_cols = [c for c in logical_order if c in filtered_raw.columns]
            leftovers = [c for c in filtered_raw.columns if c not in final_cols]
            filtered_raw = filtered_raw[final_cols + leftovers]
            
            def highlight_remarks(val):
                if isinstance(val, str):
                    if 'Late Dep, Late Arr' in val: return 'color: #ff8a80; font-weight: bold;'
                    elif 'Ontime Dep, Ontime Arr' in val: return 'color: #b9f6ca;'
                return ''
                
            styled_raw = filtered_raw.style
            if 'Remark' in filtered_raw.columns: styled_raw = styled_raw.map(highlight_remarks, subset=['Remark'])
            st.dataframe(styled_raw, use_container_width=True)

# -------------------------------------------------------------
# B. VENDOR PERFORMANCE 
# -------------------------------------------------------------
elif choice == "🚚 Vendor Performance":
    st.markdown("<h2>Vendor Performance (Routewise/Legwise)</h2>", unsafe_allow_html=True)
    if 'Vendor_Perf_Summary' in data and 'Vendor_Perf_Raw' in data:
        df_vperf_sum = data['Vendor_Perf_Summary'].copy()
        df_vperf_raw = data['Vendor_Perf_Raw'].copy()
        
        # APPLY VENDOR SPECIFIC FILTERS
        if st.session_state['role'] == 'Vendor':
            vendor_list = st.session_state.get('vendors', [])
            if vendor_list:
                regex_v = '|'.join([f"^{v}$" for v in vendor_list])
                df_vperf_sum = df_vperf_sum[df_vperf_sum['VendorName'].str.contains(regex_v, case=False, na=False, regex=True)]
                df_vperf_raw = df_vperf_raw[df_vperf_raw['VendorName'].str.contains(regex_v, case=False, na=False, regex=True)]
        
        col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
        all_zones = sorted(df_vperf_sum['Zone'].dropna().unique().tolist())
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
        df_display = df_vperf_sum[display_cols].copy()
        df_display['RowKey'] = df_display['Origin RO'].astype(str) + " || " + df_display['VendorName'].astype(str) + " | " + df_display['Route Path'].astype(str) + " | " + df_display['Legwise'].astype(str)
        
        if search_q:
            mask = df_display.astype(str).apply(lambda x: x.str.contains(search_q, case=False, regex=False, na=False)).any(axis=1)
            df_display = df_display[mask]
            
        def highlight_perf(val, col):
            if not isinstance(val, str) or '%' not in val: return ''
            try: pct = float(val.split('%')[0].strip())
            except: return ''
            if pct == 0: return 'color: #78909C;' 
            if col == 'Late Arrival': return 'background-color: rgba(211, 47, 47, 0.2); color: #ff8a80; font-weight: bold;'
            elif col == 'Ontime Arrival': return 'background-color: rgba(56, 142, 60, 0.2); color: #b9f6ca; font-weight: bold;'
            elif col == 'In-Transit': return 'background-color: rgba(245, 127, 23, 0.2); color: #ffe57f; font-weight: bold;'
            return ''

        st.markdown("### Vendor Arrival Performance Summary")
        df_display.insert(0, 'Select 👁️', False)
        
        # Vendor Roles cannot view/edit Admin action plans
        if st.session_state['role'] != 'Vendor':
            ap_data = load_action_plans()
            mod_ap = ap_data.get("Vendor Performance", {})
            df_display['Action Plan ✍️'] = df_display['RowKey'].map(mod_ap).fillna("")
            disp_cols = ['Select 👁️'] + [c for c in df_display.columns if c not in ['RowKey', 'Select 👁️']]
        else:
            disp_cols = ['Select 👁️'] + [c for c in df_display.columns if c not in ['RowKey', 'Select 👁️', 'Action Plan ✍️']]
            
        styled_df = df_display[disp_cols].style
        for col in ['Ontime Arrival', 'Late Arrival', 'In-Transit']:
            styled_df = styled_df.map(lambda x, c=col: highlight_perf(x, c), subset=[col])
            
        disabled_cols = [c for c in disp_cols if c not in ['Action Plan ✍️', 'Select 👁️']]
        
        edited_df = st.data_editor(styled_df, column_config={"Action Plan ✍️": st.column_config.TextColumn("Action Plan ✍️", width="large")}, disabled=disabled_cols, use_container_width=True, height=300)
        
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
            filtered_raw = df_vperf_raw[(df_vperf_raw['Route Path'] == selected_route) & (df_vperf_raw['Legwise'] == selected_leg) & (df_vperf_raw['VendorName'] == selected_vendor)].copy()
            filtered_raw = filtered_raw.drop(columns=['Zone', 'Origin RO'], errors='ignore')
            
            output_raw = io.BytesIO()
            with pd.ExcelWriter(output_raw, engine='xlsxwriter') as writer:
                filtered_raw.to_excel(writer, index=False, sheet_name='Raw_Data')
                workbook = writer.book
                worksheet = writer.sheets['Raw_Data']
                format_hdr = workbook.add_format({'bold': True, 'bg_color': '#1E3A8A', 'font_color': 'white', 'border': 1})
                for col_num, value in enumerate(filtered_raw.columns.values):
                    worksheet.write(0, col_num, value, format_hdr)
                    worksheet.set_column(col_num, col_num, max(len(str(value)), 15))
            st.download_button("⬇️ Download This Raw Data", data=output_raw.getvalue(), file_name=f"Raw_Data_{selected_vendor}_{selected_leg}.xlsx", mime="application/vnd.ms-excel", type="primary")
            
            def highlight_raw_remark(val):
                if isinstance(val, str):
                    if 'Late Arrival' in val: return 'color: #ff8a80; font-weight: bold;'
                    elif 'Ontime Arrival' in val: return 'color: #b9f6ca;'
                    elif 'In-Transit' in val: return 'color: #ffe57f;'
                return ''
                
            styled_raw = filtered_raw.style
            if 'Remark with 15 min waiver' in filtered_raw.columns:
                styled_raw = styled_raw.map(highlight_raw_remark, subset=['Remark with 15 min waiver'])
            st.dataframe(styled_raw, use_container_width=True)

# -------------------------------------------------------------
# C. VENDOR COMMUNICATION HUB 
# -------------------------------------------------------------
elif choice == "📱 Vendor Communication Hub":
    st.markdown("<h2>Vendor Alerts & Messaging CRM</h2>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["🚀 Routewise Ops & Vendor Summary", "🔍 Individual Vendor Hub", "🌍 Regionwise (RO) Summary"])

    # --- TAB 1: ROUTEWISE OPS & VENDOR SUMMARY ---
    with tab1:
        st.markdown("### National Round Trip Operations Performance")
        st.caption("Generate complete Ops & Vendor reports for top national pairs and email them in one click.")
        
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
        
        if 'Legwise_Route_Summary' in data and 'Vendor_Perf_Summary' in data:
            df_rt_ops_sum = data['Legwise_Route_Summary'][data['Legwise_Route_Summary']['Route Path'].isin(target_routes)]
            df_rt_ops_raw = data['Legwise_Processed_Data'][data['Legwise_Processed_Data']['Route Path'].isin(target_routes)]
            df_rt_ven_sum = data['Vendor_Perf_Summary'][data['Vendor_Perf_Summary']['Route Path'].isin(target_routes)]
            df_rt_ven_raw = data['Vendor_Perf_Raw'][data['Vendor_Perf_Raw']['Route Path'].isin(target_routes)]
            
            c1, c2 = st.columns(2)
            c1.metric("Selected Ops Trips", df_rt_ops_sum['Total_Trips'].sum() if not df_rt_ops_sum.empty else 0)
            c2.metric("Selected Vendor Trips", df_rt_ven_sum['Total_Trips'].sum() if not df_rt_ven_sum.empty else 0)
            
            mail_ids = st.text_input("Enter Email IDs (Comma separated for multiple):", placeholder="e.g. vendor1@abc.com, manager@xyz.com")
            
            output_rt = io.BytesIO()
            with pd.ExcelWriter(output_rt, engine='xlsxwriter') as writer:
                if not df_rt_ops_sum.empty: df_rt_ops_sum.to_excel(writer, sheet_name='Ops_Performance', index=False)
                if not df_rt_ops_raw.empty: df_rt_ops_raw.to_excel(writer, sheet_name='Ops_Raw_Data', index=False)
                if not df_rt_ven_sum.empty: df_rt_ven_sum.to_excel(writer, sheet_name='Vendor_Performance', index=False)
                if not df_rt_ven_raw.empty: df_rt_ven_raw.to_excel(writer, sheet_name='Vendor_Raw_Data', index=False)
                
                # Format Sheets
                workbook = writer.book
                format_hdr = workbook.add_format({'bold': True, 'bg_color': '#1E3A8A', 'font_color': 'white', 'border': 1})
                for sheet in writer.sheets:
                    worksheet = writer.sheets[sheet]
                    df_ref = locals().get(f"df_rt_{'ops' if 'Ops' in sheet else 'ven'}_{'sum' if 'Performance' in sheet else 'raw'}")
                    if df_ref is not None and not df_ref.empty:
                        for col_num, value in enumerate(df_ref.columns.values):
                            worksheet.write(0, col_num, value, format_hdr)
                            worksheet.set_column(col_num, col_num, min(max(len(str(value)), 15), 35))

            rt_filename = f"{selected_rt.replace(' ', '_')}_Report.xlsx"
            
            msg = f"Hello Team,\n\nPlease find attached the Operations and Vendor performance summary for the {selected_rt}.\n"
            msg += f"Included Routes: {', '.join(target_routes)}\n\nKindly review and take necessary action.\n\nThanks,\nAjay Singh Rawat\nFleet Operation Executive"
            
            st.markdown("---")
            b1, b2 = st.columns(2)
            
            b1.download_button(
                "1️⃣ Download Master Excel 📊", 
                data=output_rt.getvalue(), 
                file_name=rt_filename, 
                mime="application/vnd.ms-excel", 
                use_container_width=True, 
                type="primary"
            )
            
            encoded_msg = urllib.parse.quote(msg)
            subject = urllib.parse.quote(f"Trackon Performance Report: {selected_rt}")
            mail_to = urllib.parse.quote(mail_ids) if mail_ids else ""
            gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&to={mail_to}&su={subject}&body={encoded_msg}&authuser=lh.fleetops@trackon.in"
            
            b2.markdown(f'<a href="{gmail_url}" target="_blank"><button style="background-color: #EF4444; color: white; padding: 10px; border: none; border-radius: 8px; width: 100%; cursor: pointer; font-weight: 600;">2️⃣ Open Email (Gmail) ✉️</button></a>', unsafe_allow_html=True)
            st.caption("💡 Tip: Click 'Download', then click 'Open Email' and attach the downloaded file.")
        else:
            st.warning("Ops and Vendor data not fully processed yet.")

    # --- TAB 2: INDIVIDUAL VENDOR HUB ---
    with tab2:
        if 'Vendor_Perf_Summary' in data and 'Vendor_Perf_Raw' in data:
            df_vperf_sum = data['Vendor_Perf_Summary'].copy()
            df_vperf_raw = data['Vendor_Perf_Raw'].copy()
            
            if st.session_state.get('role') in ['Admin', 'Admin2']:
                with st.expander("🛠 Manage Vendor Master Contacts", expanded=False):
                    vendor_master_file = FILE_MAP.get("VENDOR_MASTER")
                    v_master_data = {}
                    if os.path.exists(vendor_master_file):
                        try:
                            with open(vendor_master_file, 'r') as f: v_master_data = json.load(f)
                        except: pass
                    with st.form("vendor_master_form"):
                        col_m1, col_m2, col_m3 = st.columns(3)
                        all_vendors_list = sorted(df_vperf_sum['VendorName'].dropna().unique().tolist())
                        vm_name = col_m1.selectbox("Select Vendor", all_vendors_list)
                        vm_wp = col_m2.text_input("WhatsApp No", value=v_master_data.get(vm_name, {}).get("whatsapp", ""))
                        vm_email = col_m3.text_input("Email ID", value=v_master_data.get(vm_name, {}).get("email", ""))
                        if st.form_submit_button("💾 Save"):
                            v_master_data[vm_name] = {"whatsapp": vm_wp.strip(), "email": vm_email.strip()}
                            with open(vendor_master_file, 'w') as f: json.dump(v_master_data, f)
                            st.success(f"Saved for {vm_name}")

            all_vendors_filtered = sorted(df_vperf_sum['VendorName'].dropna().unique().tolist())
            selected_vendor = st.selectbox("Select Vendor for Direct Message:", ["NONE"] + all_vendors_filtered)
            
            if selected_vendor != "NONE":
                df_display_ind = df_vperf_sum[df_vperf_sum['VendorName'] == selected_vendor]
                st.dataframe(df_display_ind[['Route Path', 'Legwise', 'Legs', 'Total_Trips', 'Ontime Arrival', 'Late Arrival']], use_container_width=True, hide_index=True)
                
                v_master_data_live = {}
                if os.path.exists(FILE_MAP.get("VENDOR_MASTER")):
                    try:
                        with open(FILE_MAP.get("VENDOR_MASTER"), 'r') as f: v_master_data_live = json.load(f)
                    except: pass
                
                ven_contact = v_master_data_live.get(selected_vendor, {})
                wp_num = ven_contact.get("whatsapp", "")
                email_id = ven_contact.get("email", "")
                
                if not wp_num and not email_id: st.warning("⚠️ Contact not saved in Master.")
                
                ven_sum = df_vperf_sum[df_vperf_sum['VendorName'] == selected_vendor].copy()
                ven_raw = df_vperf_raw[df_vperf_raw['VendorName'] == selected_vendor].copy()
                total_trips = ven_sum['Total_Trips'].sum() if not ven_sum.empty else 0
                
                summary_text = "ROUTE & LEG".ljust(35) + "| TRIPS | ONTIME | LATE\n" + "-"*65 + "\n"
                for _, row in ven_sum.iterrows():
                    summary_text += f"{str(row['Route Path'] + ' (' + row['Legwise'] + ')')[:33].ljust(35)}| {str(row['Total_Trips']).center(5)} | 🟢 {str(row['Ontime Arrival']).ljust(8)} | 🔴 {str(row['Late Arrival']).ljust(8)}\n"
                summary_text += "-"*65 + "\n"

                msg = f"Dear {selected_vendor},\n\nPlease find attached the arrival performance report for your vehicles.\nTotal Trips Assigned: {total_trips}\n\nPerformance Summary:\n{summary_text}\nKindly review and ensure on-time arrivals.\n\nThanks,\nAjay Singh Rawat"
                
                output_ven = io.BytesIO()
                with pd.ExcelWriter(output_ven, engine='xlsxwriter') as writer:
                    ven_sum.to_excel(writer, sheet_name='Summary', index=False)
                    ven_raw.to_excel(writer, sheet_name='Raw', index=False)
                
                c1, c2, c3 = st.columns(3)
                c1.download_button("1️⃣ Download Excel 📊", data=output_ven.getvalue(), file_name=f"{selected_vendor}_Report.xlsx", mime="application/vnd.ms-excel", use_container_width=True)
                
                encoded_msg = urllib.parse.quote(msg)
                c2.markdown(f'<a href="https://api.whatsapp.com/send?phone={wp_num}&text={encoded_msg}" target="_blank"><button style="background-color: #25D366; color: white; padding: 10px; border: none; border-radius: 8px; width: 100%;">2️⃣ WhatsApp 💬</button></a>', unsafe_allow_html=True)
                
                gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&to={urllib.parse.quote(email_id)}&su={urllib.parse.quote('Trackon Performance: ' + selected_vendor)}&body={encoded_msg}&authuser=lh.fleetops@trackon.in"
                c3.markdown(f'<a href="{gmail_url}" target="_blank"><button style="background-color: #EF4444; color: white; padding: 10px; border: none; border-radius: 8px; width: 100%;">3️⃣ Gmail 🌐</button></a>', unsafe_allow_html=True)
        else:
            st.info("Vendor Data not processed.")

    # --- TAB 3: REGIONWISE (RO) SUMMARY ---
    with tab3:
        st.markdown("### Regionwise Complete Output Generation")
        st.caption("Generate a consolidated workbook containing Operations, Vendor Performance, Payments, and CPK filtered specifically for one Regional Office (RO).")
        
        all_possible_ros = set()
        if 'Legwise_Route_Summary' in data: all_possible_ros.update(data['Legwise_Route_Summary']['Origin RO'].dropna().unique())
        if 'Master_Database' in data: all_possible_ros.update(data['Master_Database']['RO Name'].dropna().unique())
        if 'CPK_National_Zonal_Master' in data: all_possible_ros.update(data['CPK_National_Zonal_Master']['VendorRO'].dropna().unique())
        
        selected_region = st.selectbox("Select Origin RO:", sorted(list(all_possible_ros)))
        
        if selected_region:
            ro_mail_ids = st.text_input("Enter RO Email IDs:", placeholder="ro.manager@trackon.in")
            
            output_ro = io.BytesIO()
            with pd.ExcelWriter(output_ro, engine='xlsxwriter') as writer:
                if 'Legwise_Route_Summary' in data:
                    df1 = data['Legwise_Route_Summary'][data['Legwise_Route_Summary']['Origin RO'] == selected_region]
                    if not df1.empty: df1.to_excel(writer, sheet_name='Ops_Summary', index=False)
                if 'Legwise_Processed_Data' in data:
                    df2 = data['Legwise_Processed_Data'][data['Legwise_Processed_Data']['Origin RO'] == selected_region]
                    if not df2.empty: df2.to_excel(writer, sheet_name='Ops_Raw', index=False)
                    
                if 'Vendor_Perf_Summary' in data:
                    df3 = data['Vendor_Perf_Summary'][data['Vendor_Perf_Summary']['Origin RO'] == selected_region]
                    if not df3.empty: df3.to_excel(writer, sheet_name='Vendor_Summary', index=False)
                if 'Vendor_Perf_Raw' in data:
                    df4 = data['Vendor_Perf_Raw'][data['Vendor_Perf_Raw']['Origin RO'] == selected_region]
                    if not df4.empty: df4.to_excel(writer, sheet_name='Vendor_Raw', index=False)
                    
                if 'Master_Database' in data:
                    df5 = data['Master_Database'][data['Master_Database']['RO Name'].astype(str).str.upper() == selected_region.upper()]
                    if not df5.empty: df5.to_excel(writer, sheet_name='Payments', index=False)
                    
                if 'CPK_National_Zonal_Master' in data:
                    df6 = data['CPK_National_Zonal_Master'][data['CPK_National_Zonal_Master']['VendorRO'].astype(str).str.upper() == selected_region.upper()]
                    if not df6.empty: df6.to_excel(writer, sheet_name='CPK_NatZon', index=False)
                    
            msg_ro = f"Hello {selected_region} Team,\n\nPlease find attached the consolidated Operations, Vendor, and Utilization report for your region.\n\nKindly review and take necessary action.\n\nThanks,\nAjay Singh Rawat\nFleet Operation Executive"
            
            st.markdown("---")
            b1, b2 = st.columns(2)
            
            b1.download_button(
                "1️⃣ Download RO Excel 📊", 
                data=output_ro.getvalue(), 
                file_name=f"{selected_region}_Master_Report.xlsx", 
                mime="application/vnd.ms-excel", 
                use_container_width=True, 
                type="primary"
            )
            
            encoded_msg_ro = urllib.parse.quote(msg_ro)
            subject_ro = urllib.parse.quote(f"Trackon RO Master Report: {selected_region}")
            mail_to_ro = urllib.parse.quote(ro_mail_ids) if ro_mail_ids else ""
            gmail_url_ro = f"https://mail.google.com/mail/?view=cm&fs=1&to={mail_to_ro}&su={subject_ro}&body={encoded_msg_ro}&authuser=lh.fleetops@trackon.in"
            
            b2.markdown(f'<a href="{gmail_url_ro}" target="_blank"><button style="background-color: #EF4444; color: white; padding: 10px; border: none; border-radius: 8px; width: 100%; cursor: pointer; font-weight: 600;">2️⃣ Open Email (Gmail) ✉️</button></a>', unsafe_allow_html=True)
            st.caption("💡 Tip: Click 'Download', then click 'Open Email' and attach the downloaded file manually in Gmail.")


# -------------------------------------------------------------
# D. PAYMENT DASHBOARD 
# -------------------------------------------------------------
elif choice == "💳 Payment Dashboard":
    st.markdown("<h2>Pending Payments Tracker</h2>", unsafe_allow_html=True)
    if 'Master_Database' in data:
        df_pay = data['Master_Database'].copy()
        
        if PLOTLY_AVAILABLE:
            st.markdown("### 📊 Payment Buckets Overview")
            pvt_chart = pd.pivot_table(df_pay, values='Invoice Id', index='Department Bucket', aggfunc='count').reset_index()
            fig_pay = px.pie(pvt_chart, values='Invoice Id', names='Department Bucket', hole=0.4, color_discrete_sequence=['#F87171', '#FBBF24', '#34D399', '#60A5FA', '#A78BFA'])
            fig_pay.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="white", height=350)
            st.plotly_chart(fig_pay, use_container_width=True)
            st.markdown("---")

        col1, col2 = st.columns([1, 2])
        all_zones = sorted(df_pay['Zone'].dropna().unique().tolist())
        selected_zone = col1.selectbox("Filter by Zone:", ["ALL"] + all_zones)
        if selected_zone != "ALL": df_pay = df_pay[df_pay['Zone'] == selected_zone]
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
        for col in existing_cols: styled_pvt = styled_pvt.map(lambda x, c=col: color_payment_columns(x, c), subset=[col])
            
        disabled_cols = [c for c in disp_cols if c not in ['Action Plan ✍️', 'Select 👁️']]
        edited_pvt = st.data_editor(styled_pvt, column_config={"Action Plan ✍️": st.column_config.TextColumn("Action Plan ✍️", width="large")}, disabled=disabled_cols, use_container_width=True, key="pay_editor")
        
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
            
            if sel_pay_ro == 'Grand Total': filtered_pay = df_pay[df_pay['Department Bucket'] == sel_bucket].copy()
            else: filtered_pay = df_pay[(df_pay['RO Name'] == sel_pay_ro) & (df_pay['Department Bucket'] == sel_bucket)].copy()
                
            if search_q:
                mask = filtered_pay.astype(str).apply(lambda x: x.str.contains(search_q, case=False, regex=False, na=False)).any(axis=1)
                filtered_pay = filtered_pay[mask]
                
            pay_order = ['Invoice Id', 'Zone', 'RO Name', 'Vendor Name', 'Amount', 'Status', 'Pending With', 'Days Pending', 'Aging Bucket', 'Revert Remarks']
            final_pay_cols = [c for c in pay_order if c in filtered_pay.columns]
            leftovers_pay = [c for c in filtered_pay.columns if c not in final_pay_cols and c != 'Bill Uploader']
            if 'Bill Uploader' in filtered_pay.columns: leftovers_pay.append('Bill Uploader') 
            filtered_pay = filtered_pay[final_pay_cols + leftovers_pay]
            if 'Amount' in filtered_pay.columns: filtered_pay = filtered_pay.sort_values(by='Amount', ascending=False)
                
            st.dataframe(filtered_pay, use_container_width=True)

# -------------------------------------------------------------
# E. CPK & UTILIZATION
# -------------------------------------------------------------
elif choice == "💰 Network Utilization":
    st.markdown("<h2>Network Utilization & CPK Dashboard</h2>", unsafe_allow_html=True)
    if 'CPK_National_Zonal_Master' in data and 'CPK_Raw_Data' in data:
        df_cpk_raw = data['CPK_Raw_Data']

        def render_cpk_view(df_master, view_type="Route", df_updown=None):
            if df_master.empty:
                st.info("No data available for this category.")
                return
            
            if PLOTLY_AVAILABLE:
                st.markdown(f"### 📊 Overview: {view_type}")
                col_chart1, col_chart2 = st.columns(2)
                with col_chart1:
                    if 'Zone' in df_master.columns:
                        fig1 = px.pie(df_master, values='Total Trip Cost', names='Zone', title='Total Cost by Zone', hole=0.4, color_discrete_sequence=px.colors.sequential.Teal)
                        fig1.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="white", margin=dict(t=30, b=0, l=0, r=0))
                        st.plotly_chart(fig1, use_container_width=True)
                with col_chart2:
                    vendor_col = 'Vendor(s)' if 'Vendor(s)' in df_master.columns else ('VendorName' if 'VendorName' in df_master.columns else None)
                    if vendor_col:
                        top_vendors = df_master.groupby(vendor_col)['Total Trips'].sum().nlargest(5).reset_index()
                        fig2 = px.bar(top_vendors, x=vendor_col, y='Total Trips', title='Top 5 Vendors by Volume', text_auto=True, color_discrete_sequence=['#3B82F6'])
                        fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="white", margin=dict(t=30, b=0, l=0, r=0))
                        st.plotly_chart(fig2, use_container_width=True)
                st.markdown("---")

            col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
            all_zones = sorted(df_master['Zone'].dropna().unique().tolist())
            zone_filter = col1.selectbox(f"Filter Zone ({view_type}):", ["ALL"] + all_zones, key=f"z_{view_type}")
            if zone_filter != "ALL": df_master = df_master[df_master['Zone'] == zone_filter]
                
            all_ros = sorted(df_master['VendorRO'].dropna().unique().tolist())
            ro_filter = col2.selectbox(f"Filter RO ({view_type}):", ["ALL"] + all_ros, key=f"r_{view_type}")
            if ro_filter != "ALL": df_master = df_master[df_master['VendorRO'] == ro_filter]

            if 'Type' in df_master.columns:
                all_types = sorted(df_master['Type'].dropna().unique().tolist())
                type_filter = col3.selectbox(f"Filter Type ({view_type}):", ["ALL"] + all_types, key=f"t_{view_type}")
                if type_filter != "ALL": df_master = df_master[df_master['Type'] == type_filter]
                
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
            
            if view_type == "Route": disp_df['RowKey'] = disp_df['VendorRO'].astype(str) + " || " + disp_df['Route Pair'].astype(str) + " | " + disp_df['Type'].astype(str)
            elif view_type == "Vehicle": disp_df['RowKey'] = disp_df['VendorRO'].astype(str) + " || " + disp_df['Vehicle No'].astype(str)
            else: disp_df['RowKey'] = disp_df['VendorRO'].astype(str) + " || " + disp_df['Vendor(s)'].astype(str) + " | " + disp_df['Vehicle No'].astype(str) + " | " + disp_df['Route'].astype(str)

            def add_total_row(df):
                if df.empty: return df
                tot_trips = df['Total Trips'].sum() if 'Total Trips' in df.columns else 0
                tot_cap = df['Total Capacity'].sum() if 'Total Capacity' in df.columns else 0
                tot_wt = df['Total Carried Wt'].sum() if 'Total Carried Wt' in df.columns else 0
                tot_cost = df['Total Trip Cost'].sum() if 'Total Trip Cost' in df.columns else 0
                tot_cpk = tot_cost / tot_wt if tot_wt > 0 else 0
                tot_util = tot_wt / tot_cap if tot_cap > 0 else 0
                
                tot_dict = {c: '-' for c in df.columns}
                if 'Zone' in df.columns: tot_dict['Zone'] = 'TOTAL'
                if 'VendorRO' in df.columns: tot_dict['VendorRO'] = 'TOTAL'
                if 'Route Path' in df.columns: tot_dict['Route Path'] = 'TOTAL'
                if 'Total Trips' in df.columns: tot_dict['Total Trips'] = tot_trips
                if 'Total Capacity' in df.columns: tot_dict['Total Capacity'] = tot_cap
                if 'Total Carried Wt' in df.columns: tot_dict['Total Carried Wt'] = tot_wt
                if 'Total Trip Cost' in df.columns: tot_dict['Total Trip Cost'] = tot_cost
                if 'Overall CPK' in df.columns: tot_dict['Overall CPK'] = tot_cpk
                if 'Overall Util %' in df.columns: tot_dict['Overall Util %'] = tot_util
                if 'Route Pair' in df.columns: tot_dict['Route Pair'] = 'TOTAL'
                return pd.concat([df, pd.DataFrame([tot_dict])], ignore_index=True)

            disp_df = add_total_row(disp_df)
            
            for col in ['Overall CPK', 'Total Trip Cost']: 
                if col in disp_df.columns: disp_df[col] = disp_df[col].apply(lambda x: f"₹{x:.2f}" if isinstance(x, (int, float)) else x)
            if 'Overall Util %' in disp_df.columns:
                disp_df['Overall Util %'] = disp_df['Overall Util %'].apply(lambda x: f"{x * 100:.2f}%" if isinstance(x, (int, float)) else x)
            
            disp_df.insert(0, 'Select 👁️', False)
            ap_data = load_action_plans()
            mod_ap = ap_data.get(f"Network Utilization - {view_type}", {})
            disp_df['Action Plan ✍️'] = disp_df['RowKey'].map(mod_ap).fillna("")
            
            view_df = disp_df.drop(columns=['SortKey', 'Super_SortKey', 'RowKey'], errors='ignore')
            
            def highlight_cpk_util(val, col):
                if pd.isna(val) or val == '-': return ''
                if col == 'Overall Util %':
                    try:
                        pct = float(str(val).replace('%', '').strip())
                        if pct < 50: return 'color: #ff8a80; font-weight: bold;' 
                        elif pct < 80: return 'color: #ffe57f; font-weight: bold;'
                        else: return 'color: #b9f6ca; font-weight: bold;'
                    except: return ''
                elif col == 'Overall CPK': return 'color: #60A5FA; font-weight: bold;'
                return ''

            styled_view = view_df.style
            for col in ['Overall Util %', 'Overall CPK']:
                if col in view_df.columns: styled_view = styled_view.map(lambda x, c=col: highlight_cpk_util(x, c), subset=[col])

            disabled_cols = [c for c in view_df.columns if c not in ['Action Plan ✍️', 'Select 👁️']]
            edited_cpk = st.data_editor(styled_view, column_config={"Action Plan ✍️": st.column_config.TextColumn("Action Plan ✍️", width="large")}, disabled=disabled_cols, use_container_width=True, height=300, key=f"cpk_editor_{view_type}")
            
            changes = False
            for idx, row in edited_cpk.iterrows():
                r_key = str(disp_df.loc[idx, 'RowKey'])
                if r_key == 'nan': continue 
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
                if selected_idx >= len(df_cpk_view): st.warning("Please click a valid row, not the TOTAL row.")
                else:
                    if view_type == "Route":
                        selected_sortkey = df_cpk_view.iloc[selected_idx]['Route Pair']
                        st.markdown("---")
                        st.markdown(f"### 🔄 Up/Down Route Summary for `{selected_sortkey}`")
                        
                        if df_updown is not None and not df_updown.empty:
                            updown_filtered = df_updown[(df_updown['SortKey'] == selected_sortkey)].copy()
                            updown_styled = updown_filtered.drop(columns=['SortKey']).style
                            if 'Overall Util %' in updown_filtered.columns: updown_styled = updown_styled.format({'Overall Util %': lambda x: f"{x*100:.2f}%" if isinstance(x, (int, float)) else x})
                            if 'Overall CPK' in updown_filtered.columns: updown_styled = updown_styled.format({'Overall CPK': lambda x: f"₹{x:.2f}" if isinstance(x, (int, float)) else x})
                            st.dataframe(updown_styled, use_container_width=True)
                            
                        st.markdown(f"### 📄 Raw Data for Route Pair `{selected_sortkey}`")
                        raw_trips = df_cpk_raw[(df_cpk_raw['SortKey'] == selected_sortkey)]
                    elif view_type == "Vehicle":
                        selected_ro_val = df_cpk_view.iloc[selected_idx]['VendorRO']
                        selected_vno = df_cpk_view.iloc[selected_idx]['Vehicle No']
                        raw_trips = df_cpk_raw[(df_cpk_raw['RO_Clean'].astype(str).str.strip().str.upper() == str(selected_ro_val).strip().upper()) & (df_cpk_raw['Vehicle No'] == selected_vno)]
                        st.markdown("---")
                        st.markdown(f"### 📄 Raw Data for Vehicle `{selected_vno}`")
                    else:
                        selected_ro_val = df_cpk_view.iloc[selected_idx]['VendorRO']
                        selected_vno = df_cpk_view.iloc[selected_idx]['Vehicle No']
                        selected_vend = df_cpk_view.iloc[selected_idx]['Vendor(s)']
                        selected_rte = df_cpk_view.iloc[selected_idx]['Route']
                        raw_trips = df_cpk_raw[(df_cpk_raw['RO_Clean'].astype(str).str.strip().str.upper() == str(selected_ro_val).strip().upper()) & (df_cpk_raw['VendorName'] == selected_vend) & (df_cpk_raw['Final_Route'] == selected_rte) & (df_cpk_raw['Vehicle No'] == selected_vno)]
                        st.markdown("---")
                        st.markdown(f"### 📄 Raw Data for `{selected_vend}` (Vehicle: `{selected_vno}`) on `{selected_rte}`")

                    raw_cols = ['Zone', 'RO_Clean', 'Final_Route', 'Final_Type', 'VendorName', 'Vehicle No', 'Date', 'Cap', 'Wt', 'Trips', 'Cost']
                    raw_cols = [c for c in raw_cols if c in raw_trips.columns]
                    raw_trips = raw_trips[raw_cols]
                    
                    styled_raw_trips = raw_trips.style
                    if 'Cost' in raw_trips.columns:
                        def format_cost(val):
                            try: return f"₹{float(val):.2f}"
                            except: return val
                        if hasattr(styled_raw_trips, 'format'): styled_raw_trips = styled_raw_trips.format({'Cost': format_cost})
                    st.dataframe(styled_raw_trips, use_container_width=True)

        tab1, tab2, tab3 = st.tabs(["🛣️ National & Zonal", "🚚 Feeder & Regional", "📦 Co-Loader"])
        with tab1: render_cpk_view(data.get('CPK_National_Zonal_Master', pd.DataFrame()), view_type="Route", df_updown=data.get('CPK_National_Zonal_UpDown', pd.DataFrame()))
        with tab2: render_cpk_view(data.get('CPK_Feeder_Regional', pd.DataFrame()), view_type="Vehicle")
        with tab3: render_cpk_view(data.get('CPK_Coloader', pd.DataFrame()), view_type="Coloader")
    else:
        st.info("Please process CPK data first.")

# -------------------------------------------------------------
# F. TODAY'S CALL ACTION PLAN
# -------------------------------------------------------------
elif choice == "📝 Today's Call Action Plan":
    st.markdown("<h2>Today's Call Action Plan (MOM)</h2>", unsafe_allow_html=True)
    st.caption("View, export, and email all saved action plans.")
    
    ap_data = load_action_plans()
    records = []
    
    sr_no = 1
    for mod, plans in ap_data.items():
        for ref, plan in plans.items():
            ro_part, ref_part = ref.split(" || ", 1) if " || " in ref else ("UNKNOWN", ref)
            records.append({
                "S.No.": sr_no, "Origin RO": ro_part, "Module Name": mod, 
                "Reference (Route/Vendor/Invoice)": ref_part, "Action Plan Details": plan
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
            df_ap.to_excel(writer, index=False, sheet_name='Action_Plans')
            worksheet = writer.sheets['Action_Plans']
            workbook = writer.book
            format_hdr = workbook.add_format({'bold': True, 'bg_color': '#1E3A8A', 'font_color': 'white', 'border': 1})
            format_data = workbook.add_format({'border': 1, 'text_wrap': True})
            for col_num, value in enumerate(df_ap.columns.values): worksheet.write(0, col_num, value, format_hdr)
            for i, col in enumerate(df_ap.columns):
                worksheet.set_column(i, i, min(max(df_ap[col].astype(str).map(len).max(), len(str(col))) + 2, 70), format_data)
                
        email_body = "Namaste Team,\n\nPlease find the Action Plans discussed in today's call below:\n\n"
        current_mod = ""
        for _, r in df_ap.iterrows():
            if r['Module Name'] != current_mod:
                email_body += f"\n--- {r['Module Name'].upper()} ---\n"
                current_mod = r['Module Name']
            email_body += f"{r['S.No.']}. [{r['Origin RO']}] Ref: {r['Reference (Route/Vendor/Invoice)']}\n  👉 Action: {r['Action Plan Details']}\n\n"
            
        email_body += "Thanks,\nAjay Singh Rawat\nFleet Operation Executive"
        
        st.markdown("---")
        st.markdown("### 📤 Export & Share")
        
        c1, c2 = st.columns(2)
        c1.download_button(
            "1️⃣ Download Action Plan (Excel) 📥", data=output_ap.getvalue(), 
            file_name=f"Action_Plan_MOM_{datetime.datetime.now().strftime('%d%b%Y')}.xlsx", 
            mime="application/vnd.ms-excel", use_container_width=True, type="primary"
        )
        
        encoded_msg = urllib.parse.quote(email_body)
        subject = urllib.parse.quote(f"Today's Call Action Plan (MOM) - {datetime.datetime.now().strftime('%d %b %Y')}")
        gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&su={subject}&body={encoded_msg}&authuser=lh.fleetops@trackon.in"
        
        c2.markdown(f'<a href="{gmail_url}" target="_blank"><button style="background-color: #EF4444; color: white; padding: 10px; border: none; border-radius: 8px; width: 100%; cursor: pointer; font-weight: 600;">2️⃣ Compose Email (Gmail) ✉️</button></a>', unsafe_allow_html=True)
        st.caption("Tip: Download ki hui Action Plan ki Excel sheet ko compose hote waqt attach kar dena.")
