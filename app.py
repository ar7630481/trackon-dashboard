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

warnings.filterwarnings('ignore')

# ==========================================
# 1. PAGE SETUP (Professional Dark Theme)
# ==========================================
st.set_page_config(page_title="Trackon Command Center", page_icon="🚀", layout="wide")

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
    "ACTION_PLANS": os.path.join(DATA_DIR, "action_plans.json") # NEW ACTION PLAN DB
}

def get_ist_now():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)

# ==========================================
# 2. AUTHENTICATION
# ==========================================
USERS = {
    "user": "5272",
    "admin": "9211213"
}

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'role' not in st.session_state:
    st.session_state['role'] = None

if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align: center; color: #4facfe;'>🚀 Trackon Command Center</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #a8b2d1;'>Secure Login Portal</h3>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", use_container_width=True)
            
            if submit:
                if username in USERS and USERS[username] == password:
                    st.session_state['logged_in'] = True
                    st.session_state['role'] = 'Admin' if username == 'admin' else 'User'
                    st.rerun()
                else:
                    st.error("❌ Invalid Username or Password!")
    st.stop()

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
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

# NEW: ACTION PLAN HELPER FUNCTIONS
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
        
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#1E3A8A', 
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True
        })
        
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
            for c in pct_cols:
                df_ops[c] = df_ops[c].apply(format_val)

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
            pvt = pvt.reindex(columns=existing_cols)
            pvt = pvt.reset_index() # Adjusted for excel output
            
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

        if 'CPK_National_Zonal_Master' in data_dict and not data_dict['CPK_National_Zonal_Master'].empty:
            df_cpk1 = data_dict['CPK_National_Zonal_Master'].copy()
            df_cpk1 = df_cpk1.sort_values(by='Overall Util %', ascending=True)
            df_cpk1 = add_total_row_cpk(df_cpk1)
            for col in ['Overall CPK', 'Total Trip Cost']: 
                if col in df_cpk1.columns: df_cpk1[col] = df_cpk1[col].apply(lambda x: f"₹{x:.2f}" if isinstance(x, (int, float)) else x)
            if 'Overall Util %' in df_cpk1.columns: df_cpk1['Overall Util %'] = df_cpk1['Overall Util %'].apply(lambda x: f"{x * 100:.2f}%" if isinstance(x, (int, float)) else x)
            df_cpk1.to_excel(writer, sheet_name='CPK_Nat_Zon', index=False)
            apply_manager_formatting('CPK_Nat_Zon', df_cpk1)

        if 'CPK_Feeder_Regional' in data_dict and not data_dict['CPK_Feeder_Regional'].empty:
            df_cpk2 = data_dict['CPK_Feeder_Regional'].copy()
            df_cpk2 = df_cpk2.sort_values(by='Overall Util %', ascending=True)
            df_cpk2 = add_total_row_cpk(df_cpk2)
            for col in ['Overall CPK', 'Total Trip Cost']: 
                if col in df_cpk2.columns: df_cpk2[col] = df_cpk2[col].apply(lambda x: f"₹{x:.2f}" if isinstance(x, (int, float)) else x)
            if 'Overall Util %' in df_cpk2.columns: df_cpk2['Overall Util %'] = df_cpk2['Overall Util %'].apply(lambda x: f"{x * 100:.2f}%" if isinstance(x, (int, float)) else x)
            df_cpk2.to_excel(writer, sheet_name='CPK_Feed_Reg', index=False)
            apply_manager_formatting('CPK_Feed_Reg', df_cpk2)
            
        if 'CPK_Coloader' in data_dict and not data_dict['CPK_Coloader'].empty:
            df_cpk3 = data_dict['CPK_Coloader'].copy()
            df_cpk3 = df_cpk3.sort_values(by='Overall Util %', ascending=True)
            df_cpk3 = add_total_row_cpk(df_cpk3)
            for col in ['Overall CPK', 'Total Trip Cost']: 
                if col in df_cpk3.columns: df_cpk3[col] = df_cpk3[col].apply(lambda x: f"₹{x:.2f}" if isinstance(x, (int, float)) else x)
            if 'Overall Util %' in df_cpk3.columns: df_cpk3['Overall Util %'] = df_cpk3['Overall Util %'].apply(lambda x: f"{x * 100:.2f}%" if isinstance(x, (int, float)) else x)
            df_cpk3.to_excel(writer, sheet_name='CPK_Coloader', index=False)
            apply_manager_formatting('CPK_Coloader', df_cpk3)

        if 'CPK_Raw_Data' in data_dict:
            df_cpk_raw = data_dict['CPK_Raw_Data'].copy()
            df_cpk_raw.to_excel(writer, sheet_name='Network_Raw', index=False)
            apply_manager_formatting('Network_Raw', df_cpk_raw)

# ==========================================
# 5. MAIN DATA PROCESSING
# ==========================================
def process_all_data():
    progress = st.progress(0)
    status_text = st.empty()
    data_for_export = {}
    temp_output = None
    
    try:
        # --- EXTRACT ZONE MAPPING FROM BRANCH MASTER ---
        ro_zone_map = {}
        if os.path.exists(FILE_MAP["BRANCH_MASTER"]):
            df_brn_master = pd.read_excel(FILE_MAP["BRANCH_MASTER"], sheet_name="Sheet1")
            df_brn_master.columns = df_brn_master.columns.astype(str).str.strip()
            ro_col_m = next((c for c in df_brn_master.columns if 'rptro' in c.lower().replace(' ', '')), 'RPTRO')
            zone_col_m = next((c for c in df_brn_master.columns if 'zone' in c.lower().replace(' ', '')), 'Zone')
            df_brn_master[ro_col_m] = df_brn_master[ro_col_m].astype(str).str.strip().str.upper()
            ro_zone_map = df_brn_master.drop_duplicates(subset=[ro_col_m]).set_index(ro_col_m)[zone_col_m].to_dict()

        # --- MODULE 0: PAYMENT DATA ---
        status_text.text("⚙️ Processing Payment Data...")
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
            df_pay['Department Bucket'] =
