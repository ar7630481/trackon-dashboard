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
    "VENDOR_MASTER": os.path.join(DATA_DIR, "vendor_master.json") 
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

        # --- 1. OPERATIONS SUMMARY ---
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

        # --- VENDOR PERFORMANCE ---
        if 'Vendor_Perf_Summary' in data_dict:
            df_vperf = data_dict['Vendor_Perf_Summary'].copy()
            df_vperf.to_excel(writer, sheet_name='Vendor_Perf_Summary', index=False)
            apply_manager_formatting('Vendor_Perf_Summary', df_vperf)
            
        if 'Vendor_Perf_Raw' in data_dict:
            df_vperf_raw = data_dict['Vendor_Perf_Raw'].copy()
            df_vperf_raw.to_excel(writer, sheet_name='Vendor_Perf_Raw', index=False)
            apply_manager_formatting('Vendor_Perf_Raw', df_vperf_raw)

        # --- 2. PAYMENT DASHBOARD ---
        if 'Master_Database' in data_dict:
            df_pay = data_dict['Master_Database'].copy()
            pvt = pd.pivot_table(df_pay, values='Invoice Id', index='RO Name', columns='Department Bucket', aggfunc='count', fill_value=0, margins=True, margins_name='Grand Total')
            cols_order = ["1. USER / DRAFT PENDING", "2. COST CONTROL PENDING", "3. FINANCE PENDING", "4. PAYMENT PENDING", "5. OTHER PENDING", "Grand Total"]
            existing_cols = [c for c in cols_order if c in pvt.columns]
            pvt = pvt.reindex(columns=existing_cols)
            
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
            
            styled_pay.to_excel(writer, sheet_name='Payment_Summary')
            worksheet = writer.sheets['Payment_Summary']
            worksheet.write(0, 0, "RO Name", header_format)
            for col_num, value in enumerate(pvt.columns.values):
                worksheet.write(0, col_num + 1, value, header_format)
            worksheet.set_column(0, len(pvt.columns), 20)
            
            df_pay.to_excel(writer, sheet_name='Payment_Raw', index=False)
            apply_manager_formatting('Payment_Raw', df_pay)

        # --- 3. CPK & UTILIZATION ---
        if 'Up_Down_Route_Summary' in data_dict:
            df_cpk = data_dict['Up_Down_Route_Summary'].copy()
            df_cpk = df_cpk.sort_values(by='Overall Util %', ascending=True)
            
            def add_total_row_cpk(df):
                if df.empty: return df
                tot_trips = df['Total Trips'].sum() if 'Total Trips' in df.columns else 0
                tot_cap = df['Total Capacity'].sum() if 'Total Capacity' in df.columns else 0
                tot_wt = df['Total Carried Wt'].sum() if 'Total Carried Wt' in df.columns else 0
                tot_cost = df['Total Trip Cost'].sum() if 'Total Trip Cost' in df.columns else 0
                
                tot_cpk = tot_cost / tot_wt if tot_wt > 0 else 0
                tot_util = tot_wt / tot_cap if tot_cap > 0 else 0
                tot_avg_cost = tot_cost / tot_trips if tot_trips > 0 else 0
                
                tot_dict = {c: '-' for c in df.columns}
                tot_dict['Zone'] = 'TOTAL'
                tot_dict['VendorRO'] = 'TOTAL'
                if 'Total Trips' in df.columns: tot_dict['Total Trips'] = tot_trips
                if 'Total Capacity' in df.columns: tot_dict['Total Capacity'] = tot_cap
                if 'Total Carried Wt' in df.columns: tot_dict['Total Carried Wt'] = tot_wt
                if 'Total Trip Cost' in df.columns: tot_dict['Total Trip Cost'] = tot_cost
                if 'Overall CPK' in df.columns: tot_dict['Overall CPK'] = tot_cpk
                if 'Overall Util %' in df.columns: tot_dict['Overall Util %'] = tot_util
                if 'Avg Trip Cost' in df.columns: tot_dict['Avg Trip Cost'] = f"₹{tot_avg_cost:.2f}"
                return pd.concat([df, pd.DataFrame([tot_dict])], ignore_index=True)
                
            df_cpk = add_total_row_cpk(df_cpk)
            
            for col in ['Overall CPK', 'Total Trip Cost']: 
                if col in df_cpk.columns: 
                    df_cpk[col] = df_cpk[col].apply(lambda x: f"₹{x:.2f}" if isinstance(x, (int, float)) else x)
            if 'Overall Util %' in df_cpk.columns:
                df_cpk['Overall Util %'] = df_cpk['Overall Util %'].apply(lambda x: f"{x * 100:.2f}%" if isinstance(x, (int, float)) else x)
                
            df_cpk = df_cpk.drop(columns=['SortKey', 'Super_SortKey'], errors='ignore')
            
            def cpk_excel_color(val, col):
                if pd.isna(val) or val == '-': return ''
                if col == 'Overall Util %':
                    try:
                        pct = float(str(val).replace('%', '').strip())
                        if pct < 50: return 'color: #D32F2F; font-weight: bold' 
                        elif pct < 80: return 'color: #FBC02D; font-weight: bold' 
                        else: return 'color: #388E3C; font-weight: bold' 
                    except: return ''
                elif col == 'Overall CPK':
                    return 'color: #0288D1; font-weight: bold' 
                return ''
                
            styled_cpk = df_cpk.style
            if hasattr(styled_cpk, 'map'):
                styled_cpk = styled_cpk.map(lambda x: cpk_excel_color(x, 'Overall Util %'), subset=['Overall Util %'])
                styled_cpk = styled_cpk.map(lambda x: cpk_excel_color(x, 'Overall CPK'), subset=['Overall CPK'])
            else:
                styled_cpk = styled_cpk.applymap(lambda x: cpk_excel_color(x, 'Overall Util %'), subset=['Overall Util %'])
                styled_cpk = styled_cpk.applymap(lambda x: cpk_excel_color(x, 'Overall CPK'), subset=['Overall CPK'])
                
            styled_cpk.to_excel(writer, sheet_name='Network_Utilization', index=False)
            apply_manager_formatting('Network_Utilization', df_cpk)

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
        else:
            st.warning("⚠️ Payment file missing.")

        progress.progress(20)

        # --- MODULE 1: LEGWISE OPERATIONS & VENDOR PERFORMANCE ---
        status_text.text("⚙️ Processing Legwise Operations Data...")
        if os.path.exists(FILE_MAP["LEGWISE"]) and os.path.exists(FILE_MAP["ROUTE_MASTER"]) and os.path.exists(FILE_MAP["BRANCH_MASTER"]):
            df_leg_all = pd.read_excel(FILE_MAP["LEGWISE"], sheet_name="Sheet1")
            df_rte = pd.read_excel(FILE_MAP["ROUTE_MASTER"], sheet_name="RoutePathReportModel")
            df_brn = pd.read_excel(FILE_MAP["BRANCH_MASTER"], sheet_name="Sheet1")
            
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
            
            # Base Cleaning
            df_leg_all = df_leg_all.sort_values(by=['RouteCode', 'MCD_StartDate_DT', 'Min_CD_StartDatetime'])
            dedup = df_leg_all.groupby(['RouteCode', 'MCD_StartDate_DT'])['MasterCDNo'].first().reset_index()
            df_leg_all = df_leg_all.merge(dedup, on=['RouteCode', 'MCD_StartDate_DT', 'MasterCDNo'])
            df_leg_all['Legs'] = df_leg_all['CD_FromBranch'].astype(str) + " to " + df_leg_all['CD_ToBranch'].astype(str)
            df_leg_all.rename(columns={'Min_CD_StartDatetime': 'Actual Departure Time', 'Max_CD_EndDatetime': 'Actual Arrival Time', 'Route': 'Route Path'}, inplace=True)
            
            df_leg_all['CD_FromBranch_Clean'] = df_leg_all['CD_FromBranch'].astype(str).str.strip().str.upper()
            df_brn.columns = df_brn.columns.astype(str).str.strip()
            brn_col = next((c for c in df_brn.columns if 'branchcode' in c.lower().replace(' ', '')), 'RPTBranchcode')
            ro_col = next((c for c in df_brn.columns if 'rptro' in c.lower().replace(' ', '')), 'RPTRO')
            zone_col = next((c for c in df_brn.columns if 'zone' in c.lower().replace(' ', '')), 'Zone')

            df_brn['RPTBranchcode_Clean'] = df_brn[brn_col].astype(str).str.strip().str.upper()
            df_brn_clean = df_brn[['RPTBranchcode_Clean', ro_col, zone_col]].drop_duplicates('RPTBranchcode_Clean')
            df_leg_all = df_leg_all.merge(df_brn_clean, left_on='CD_FromBranch_Clean', right_on='RPTBranchcode_Clean', how='left')
            df_leg_all.rename(columns={ro_col: 'Origin RO', zone_col: 'Zone'}, inplace=True)
            df_leg_all['Origin RO'] = df_leg_all['Origin RO'].fillna('Missing RO')
            df_leg_all['Zone'] = df_leg_all['Zone'].fillna('UNKNOWN ZONE')
            
            df_leg_all[['Origin', 'Destination']] = df_leg_all['Route Path'].apply(lambda x: pd.Series(extract_orig_dest(x)))
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
            
            # -------------------------------------------------------------
            # NEW LOGIC: VENDOR PERFORMANCE (Uses Unfiltered Data)
            # -------------------------------------------------------------
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
            
            # Format Datetime variables for proper Excel export
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
            
            # -------------------------------------------------------------
            # ORIGINAL LOGIC: OPERATIONS EXCEPTION (Filtered)
            # -------------------------------------------------------------
            df_leg = df_leg_all[(df_leg_all['MCD_Created_By'] == 'SCHEDULED') & (df_leg_all['LH Type'].isin(['National LH', 'Zonal LH']))].copy()
            
            def calc_status(act, sch, mode):
                if pd.isna(act): return f"No {mode}" if mode == 'Dep' else "In-Transit"
                if pd.isna(sch): return "Missing Sch"
                if (act - sch).total_seconds() / 60 <= 15: return f"Ontime {mode}"
                return f"Late {mode}"
                
            df_leg['Dep_Status'] = df_leg.apply(lambda r: calc_status(r['Actual Departure Time'], r['Scheduled Departure Time'], 'Dep'), axis=1)
            df_leg['Arr_Status'] = df_leg.apply(lambda r: calc_status(r['Actual Arrival Time'], r['Scheduled Arrival Time'], 'Arr'), axis=1)
            df_leg['Remark'] = df_leg['Dep_Status'] + ", " + df_leg['Arr_Status']

            df_leg['Late Dep'] = df_leg['Remark'].str.contains('Late Dep', case=False, na=False).astype(int)
            df_leg['Late Arr'] = df_leg['Remark'].str.contains('Late Arr', case=False, na=False).astype(int)
            df_leg['Missing'] = df_leg['Remark'].str.contains('No Dep|Missing', case=False, na=False, regex=True).astype(int)

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
            
            del df_leg, df_leg_all, df_rte, df_brn, route_tat_master
        else:
            st.warning("⚠️ Operations files missing. Skipping Operations module.")

        progress.progress(60)
        
        # --- MODULE 2: CPK AND UTILIZATION ---
        status_text.text("⚙️ Calculating CPK & Utilization...")
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
            
            # Map Zone to CPK Data
            df_raw['Zone'] = df_raw['RO_Clean'].map(ro_zone_map).fillna('UNKNOWN ZONE')
            
            target_ros = ['PATRO', 'CCURO', 'BBSRO', 'GAURO', 'MUMRO', 'DELRO', 'LKORO']
            
            # --- APPLY RATE CORRECTIONS IF ANY ---
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
                except Exception as e:
                    pass 
            
            df_updn = df_raw[~df_raw['Final_Type'].str.upper().str.contains('OFD|PICKUP', na=False)].copy()
            target_keys = df_updn[df_updn['RO_Clean'].isin(target_ros)]['SortKey'].unique()
            df_updn = df_updn[df_updn['SortKey'].isin(target_keys)]
            
            data_for_export['CPK_Raw_Data'] = df_updn

            if not df_updn.empty:
                # Calculate Trip Rate for each raw entry before grouping
                df_updn['Trip_Rate'] = np.where(df_updn['Trips'] > 0, df_updn['Cost'] / df_updn['Trips'], 0).round(2)
                df_updn['Trip_Rate_Str'] = "₹" + df_updn['Trip_Rate'].astype(str)
                
                # Group strictly by Route, Type, Capacity, AND Trip Rate for Vendor Merging
                agg_updn = df_updn.groupby(['RO_Clean', 'Zone', 'Final_Route', 'Final_Type', 'Cap', 'SortKey', 'Trip_Rate']).agg(
                    Total_Trips=('Trips', 'sum'),
                    Total_Carried_Wt=('Wt', 'sum'),
                    Total_Trip_Cost=('Cost', 'sum'),
                    VendorName=('VendorName', lambda x: ', '.join(sorted(set(x.dropna().astype(str))))),
                    Avg_Trip_Cost=('Trip_Rate_Str', lambda x: ', '.join(sorted(set(x.dropna().astype(str)))))
                ).reset_index()

                agg_updn['Total Capacity'] = agg_updn['Cap'] * agg_updn['Total_Trips']
                agg_updn['Overall CPK'] = np.where(agg_updn['Total_Carried_Wt'] > 0, agg_updn['Total_Trip_Cost'] / agg_updn['Total_Carried_Wt'], 0)
                agg_updn['Overall Util %'] = np.where(agg_updn['Total Capacity'] > 0, agg_updn['Total_Carried_Wt'] / agg_updn['Total Capacity'], 0)
                
                # Column selection matching the requested output format exactly
                updn_final = agg_updn[['Zone', 'RO_Clean', 'Final_Route', 'Final_Type', 'Overall CPK', 'Overall Util %', 'Cap', 'Total Capacity', 'Total_Carried_Wt', 'Avg_Trip_Cost', 'Total_Trip_Cost', 'Total_Trips', 'VendorName', 'SortKey']]
                updn_final.columns = ["Zone", "VendorRO", "Route (UP/DOWN)", "Type", "Overall CPK", "Overall Util %", "VehCap (Base)", "Total Capacity", "Total Carried Wt", "Avg Trip Cost", "Total Trip Cost", "Total Trips", "Vendor(s)", "SortKey"]

                type_order = {"MCD-National LH":1, "MCD-Zonal LH":2, "MCD-Regional LH":3, "MCD-Feeder":4, "CO-LOADER":5}
                updn_final['TypeSort'] = updn_final['Type'].map(lambda x: type_order.get(x, 99))
                updn_final = updn_final.sort_values(by=['TypeSort', 'SortKey', 'Route (UP/DOWN)'], ascending=[True, True, True]).drop(columns=['TypeSort'])

                data_for_export['Up_Down_Route_Summary'] = updn_final

            del df_raw, df_lookup
        else:
            st.warning("⚠️ CPK files missing. Skipping CPK module.")
            
        progress.progress(80)
        
        if not data_for_export:
            status_text.warning("No datasets were processed. Check the uploaded files.")
            return False
            
        # --- 1. SAVE RAW DB FILE ---
        status_text.text("⚙️ Saving Raw Database...")
        with tempfile.NamedTemporaryFile(dir=DATA_DIR, suffix='.xlsx', delete=False) as tmp:
            temp_output = tmp.name
        with pd.ExcelWriter(temp_output, engine='xlsxwriter') as writer:
            for k, v in data_for_export.items():
                v.to_excel(writer, sheet_name=k, index=False)
        os.replace(temp_output, FILE_MAP["FINAL_OUTPUT"])
        
        progress.progress(90)
        
        # --- 2. GENERATE VIP EXECUTIVE EXCEL DIRECTLY TO DISK ---
        status_text.text("⚙️ Generating VIP Executive Report directly to disk...")
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
        data_for_export.clear()
        if temp_output and os.path.exists(temp_output):
            os.remove(temp_output)
        gc.collect()

# ==========================================
# 6. SIDEBAR: ADMIN PANEL & RATE CORRECTIONS
# ==========================================
st.sidebar.title(f"Welcome, {st.session_state['role']}")
if st.sidebar.button("Logout", key="logout_btn"):
    st.session_state['logged_in'] = False
    st.session_state['role'] = None
    st.rerun()

st.sidebar.markdown("---")

if st.session_state['role'] == 'Admin':
    st.sidebar.header("🛠 Data Management")
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

    # NEW RATE CORRECTION MASTER
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
                    except: pass
                
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
    if st.sidebar.button("🚀 PROCESS & REFRESH DATA", use_container_width=True):
        st.session_state.pop('_dashboard_cache', None)
        gc.collect()
        if process_all_data():
            st.session_state['_processing_success'] = True
            st.rerun()
        st.stop()

# ==========================================
# 7. DASHBOARD UI & DOWNLOAD BUTTON
# ==========================================
MENU_SHEETS = {
    "📊 Operations Summary": ('Legwise_Route_Summary', 'Legwise_Processed_Data'),
    "🚚 Vendor Performance": ('Vendor_Perf_Summary', 'Vendor_Perf_Raw'),
    "💳 Payment Dashboard": ('Master_Database',),
    "📱 Vendor Communication Hub": ('Vendor_Perf_Summary', 'Vendor_Perf_Raw'),
    "💰 Network Utilization": ('Up_Down_Route_Summary', 'CPK_Raw_Data'),
}
menu = list(MENU_SHEETS)
choice = st.sidebar.radio("Navigation:", menu)

def file_version(path):
    stat = os.stat(path)
    return (stat.st_mtime_ns, stat.st_size)

def load_dashboard_data(page):
    path = FILE_MAP["FINAL_OUTPUT"]
    if not os.path.exists(path):
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
                data = {name: workbook.parse(name) for name in MENU_SHEETS[page]
                        if name in workbook.sheet_names}
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

# 📥 EXPORT REPORT - DIRECT FILE STREAM FROM DISK
if os.path.exists(FILE_MAP["FINAL_OUTPUT"]) and os.path.exists(FILE_MAP["EXECUTIVE_REPORT"]):
    st.sidebar.markdown("---")
    st.sidebar.header("📥 Export Reports")
    try:
        with open(FILE_MAP["EXECUTIVE_REPORT"], "rb") as report_file:
            st.sidebar.download_button(
                "📄 Download VIP Executive Report", data=report_file,
                file_name=f"Trackon_Executive_Master_Report_{get_ist_now():%d_%b_%Y}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True, on_click="ignore")
    except Exception as exc:
        st.sidebar.error(f"Could not load download: {exc}")
        
    ts = os.path.getmtime(FILE_MAP["FINAL_OUTPUT"])
    ist = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    dt = datetime.datetime.fromtimestamp(ts, tz=ist).strftime('%d %b %Y, %I:%M %p')
    st.sidebar.info(f"📊 Dashboard Refreshed: {dt} (IST)")

data = load_dashboard_data(choice)
if not data:
    st.warning("No processed data for this page. Admin must upload the relevant files and process data.")
    st.stop()

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

        display_cols = ['Route Path', 'Legwise', 'Legs', 'Total_Trips', 
                        'Ontime Dep, Ontime Arr %', 'Ontime Dep, Late Arr %', 
                        'Late Dep, Late Arr %', 'Late Dep, Ontime Arr %']
        
        df_display = df_leg_sum[display_cols].copy()
        
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
            
        pct_cols = [c for c in df_display.columns if '%' in c]
        for c in pct_cols:
            df_display[c] = df_display[c].apply(format_val)

        def highlight_cells(val, col):
            if not isinstance(val, str) or '%' not in val: return ''
            try: pct = float(val.split('%')[0].strip())
            except: return ''
            
            if pct == 0: return 'color: #78909C;' 
            if 'Late Dep, Late Arr' in col: return 'background-color: rgba(211, 47, 47, 0.15); color: #ff5252; font-weight: bold;'
            elif 'Ontime Dep, Ontime Arr' in col: return 'background-color: rgba(56, 142, 60, 0.15); color: #69f0ae; font-weight: bold;'
            elif 'Ontime Dep, Late Arr' in col: return 'background-color: rgba(245, 127, 23, 0.15); color: #ffd740; font-weight: bold;'
            elif 'Late Dep, Ontime Arr' in col: return 'background-color: rgba(123, 31, 162, 0.15); color: #e040fb; font-weight: bold;'
            return ''

        styled_df = df_display.style
        for col in pct_cols:
            if hasattr(styled_df, 'map'): styled_df = styled_df.map(lambda x, c=col: highlight_cells(x, c), subset=[col])
            else: styled_df = styled_df.applymap(lambda x, c=col: highlight_cells(x, c), subset=[col])

        st.markdown("### Top Priority Routes Summary")
        
        selection = st.dataframe(
            styled_df, 
            use_container_width=True, 
            height=300, 
            on_select="rerun", 
            selection_mode="single-row"
        )
        
        if selection and selection.get('selection', {}).get('rows'):
            selected_idx = selection['selection']['rows'][0]
            selected_route = df_display.iloc[selected_idx]['Route Path']
            selected_leg = df_display.iloc[selected_idx]['Legwise']
            
            st.markdown("---")
            st.markdown(f"### 📄 Details for `{selected_route}` - `{selected_leg}`")
            
            filtered_raw = df_raw_leg[(df_raw_leg['Route Path'] == selected_route) & (df_raw_leg['Legwise'] == selected_leg)].copy()
            
            cols_to_drop = ['Scheduled TAT Till Destination', 'Actual TAT Till Destination', 
                            'Overall Remark', 'MCD_EndDate', 'LH Type', 'Origin', 'Destination', 'Region', 'Origin RO', 'Zone']
            filtered_raw = filtered_raw.drop(columns=[c for c in cols_to_drop if c in filtered_raw.columns], errors='ignore')
            
            logical_order = ['Route Path', 'MCD_StartDate', 'Legwise', 'Legs', 'Remark', 
                             'Scheduled Departure Time', 'Actual Departure Time', 'Scheduled Arrival Time', 
                             'Actual Arrival Time', 'Scheduled Halting', 'Actual Halting', 
                             'MasterCDNo', 'VendorName', 'RouteCode', 'VehicleNo']
            
            final_cols = [c for c in logical_order if c in filtered_raw.columns]
            leftovers = [c for c in filtered_raw.columns if c not in final_cols]
            filtered_raw = filtered_raw[final_cols + leftovers]
            
            def highlight_remarks(val):
                if isinstance(val, str):
                    if 'Late Dep, Late Arr' in val: return 'color: #ff5252; font-weight: bold;'
                    elif 'Ontime Dep, Ontime Arr' in val: return 'color: #69f0ae;'
                return ''
                
            styled_raw = filtered_raw.style
            if 'Remark' in filtered_raw.columns:
                if hasattr(styled_raw, 'map'): styled_raw = styled_raw.map(highlight_remarks, subset=['Remark'])
                else: styled_raw = styled_raw.applymap(highlight_remarks, subset=['Remark'])
                    
            st.dataframe(styled_raw, use_container_width=True)
        else:
            st.info("👆 Click any row in the table above to view detailed trip records.")

# -------------------------------------------------------------
# B. VENDOR PERFORMANCE 
# -------------------------------------------------------------
elif choice == "🚚 Vendor Performance":
    st.markdown("<h2>Vendor Performance (Routewise/Legwise)</h2>", unsafe_allow_html=True)
    
    if 'Vendor_Perf_Summary' in data and 'Vendor_Perf_Raw' in data:
        df_vperf_sum = data['Vendor_Perf_Summary'].copy()
        df_vperf_raw = data['Vendor_Perf_Raw'].copy()
        
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

        display_cols = ['Route Path', 'Legwise', 'Legs', 'VendorName', 'Total_Trips', 
                        'Ontime Arrival', 'Late Arrival', 'In-Transit']
        
        df_display = df_vperf_sum[display_cols].copy()
        
        if search_q:
            mask = df_display.astype(str).apply(lambda x: x.str.contains(search_q, case=False, regex=False, na=False)).any(axis=1)
            df_display = df_display[mask]
            
        def highlight_perf(val, col):
            if not isinstance(val, str) or '%' not in val: return ''
            try: pct = float(val.split('%')[0].strip())
            except: return ''
            
            if pct == 0: return 'color: #78909C;' 
            if col == 'Late Arrival': return 'background-color: rgba(211, 47, 47, 0.15); color: #ff5252; font-weight: bold;'
            elif col == 'Ontime Arrival': return 'background-color: rgba(56, 142, 60, 0.15); color: #69f0ae; font-weight: bold;'
            elif col == 'In-Transit': return 'background-color: rgba(245, 127, 23, 0.15); color: #ffd740; font-weight: bold;'
            return ''

        styled_df = df_display.style
        pct_cols = ['Ontime Arrival', 'Late Arrival', 'In-Transit']
        for col in pct_cols:
            if hasattr(styled_df, 'map'): styled_df = styled_df.map(lambda x, c=col: highlight_perf(x, c), subset=[col])
            else: styled_df = styled_df.applymap(lambda x, c=col: highlight_perf(x, c), subset=[col])

        st.markdown("### Vendor Arrival Performance Summary")
        
        selection = st.dataframe(
            styled_df, 
            use_container_width=True, 
            height=300, 
            on_select="rerun", 
            selection_mode="single-row"
        )
        
        if selection and selection.get('selection', {}).get('rows'):
            selected_idx = selection['selection']['rows'][0]
            selected_route = df_display.iloc[selected_idx]['Route Path']
            selected_leg = df_display.iloc[selected_idx]['Legwise']
            selected_vendor = df_display.iloc[selected_idx]['VendorName']
            
            st.markdown("---")
            st.markdown(f"### 📄 Raw Data for `{selected_vendor}` on `{selected_route}` - `{selected_leg}`")
            
            filtered_raw = df_vperf_raw[
                (df_vperf_raw['Route Path'] == selected_route) & 
                (df_vperf_raw['Legwise'] == selected_leg) &
                (df_vperf_raw['VendorName'] == selected_vendor)
            ].copy()
            
            cols_to_drop = ['Zone', 'Origin RO']
            filtered_raw = filtered_raw.drop(columns=[c for c in cols_to_drop if c in filtered_raw.columns], errors='ignore')
            
            def highlight_raw_remark(val):
                if isinstance(val, str):
                    if 'Late Arrival' in val: return 'color: #ff5252; font-weight: bold;'
                    elif 'Ontime Arrival' in val: return 'color: #69f0ae;'
                    elif 'In-Transit' in val: return 'color: #ffd740;'
                return ''
                
            styled_raw = filtered_raw.style
            if 'Remark with 15 min waiver' in filtered_raw.columns:
                if hasattr(styled_raw, 'map'): styled_raw = styled_raw.map(highlight_raw_remark, subset=['Remark with 15 min waiver'])
                else: styled_raw = styled_raw.applymap(highlight_raw_remark, subset=['Remark with 15 min waiver'])
                    
            st.dataframe(styled_raw, use_container_width=True)
        else:
            st.info("👆 Click any row in the table above to view detailed trip records.")

# -------------------------------------------------------------
# C. VENDOR PAYMENT DASHBOARD 
# -------------------------------------------------------------
elif choice == "💳 Payment Dashboard":
    st.markdown("<h2>Pending Payments Tracker</h2>", unsafe_allow_html=True)
    
    if 'Master_Database' in data:
        df_pay = data['Master_Database'].copy()
        
        col1, col2 = st.columns([1, 2])
        
        all_zones = sorted(df_pay['Zone'].dropna().unique().tolist())
        selected_zone = col1.selectbox("Filter by Zone:", ["ALL"] + all_zones)
        
        if selected_zone != "ALL":
            df_pay = df_pay[df_pay['Zone'] == selected_zone]
            
        search_q = col2.text_input("🔍 Quick Search (Invoice, Vendor, RO...):")
            
        pvt = pd.pivot_table(df_pay, values='Invoice Id', index='RO Name', columns='Department Bucket', aggfunc='count', fill_value=0, margins=True, margins_name='Grand Total')
        
        cols_order = ["1. USER / DRAFT PENDING", "2. COST CONTROL PENDING", "3. FINANCE PENDING", "4. PAYMENT PENDING", "5. OTHER PENDING", "Grand Total"]
        existing_cols = [c for c in cols_order if c in pvt.columns]
        pvt = pvt.reindex(columns=existing_cols)
        
        def color_payment_columns(val, col_name):
            if pd.isna(val) or val == 0: return ''
            if col_name == '1. USER / DRAFT PENDING': return 'background-color: rgba(211, 47, 47, 0.3); color: #ff5252; font-weight: bold;' 
            elif col_name == '2. COST CONTROL PENDING': return 'background-color: rgba(245, 127, 23, 0.3); color: #ffd740; font-weight: bold;'
            elif col_name == '3. FINANCE PENDING': return 'background-color: rgba(245, 127, 23, 0.1); color: #ffe57f; font-weight: bold;'
            return ''

        styled_pvt = pvt.style
        for col in existing_cols:
            if hasattr(styled_pvt, 'map'): styled_pvt = styled_pvt.map(lambda x, c=col: color_payment_columns(x, c), subset=[col])
            else: styled_pvt = styled_pvt.applymap(lambda x, c=col: color_payment_columns(x, c), subset=[col])

        st.markdown("### RO-Wise Summary")
        pay_selection = st.dataframe(
            styled_pvt, 
            use_container_width=True, 
            on_select="rerun", 
            selection_mode="single-row"
        )
        
        if pay_selection and pay_selection.get('selection', {}).get('rows'):
            selected_idx = pay_selection['selection']['rows'][0]
            sel_pay_ro = pvt.index[selected_idx]
            
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
                
            pay_order = ['Invoice Id', 'Zone', 'RO Name', 'Vendor Name', 'Amount', 'Status', 'Pending With', 'Days Pending', 'Aging Bucket', 'Revert Remarks']
            final_pay_cols = [c for c in pay_order if c in filtered_pay.columns]
            
            leftovers_pay = [c for c in filtered_pay.columns if c not in final_pay_cols and c != 'Bill Uploader']
            if 'Bill Uploader' in filtered_pay.columns: leftovers_pay.append('Bill Uploader') 
                
            filtered_pay = filtered_pay[final_pay_cols + leftovers_pay]
            if 'Amount' in filtered_pay.columns: filtered_pay = filtered_pay.sort_values(by='Amount', ascending=False)
                
            st.data_editor(
                filtered_pay,
                use_container_width=True,
                disabled=True,
                column_config={
                    "Revert Remarks": st.column_config.TextColumn("Revert Remarks", width="large"),
                    "Vendor Name": st.column_config.TextColumn("Vendor Name", width="medium")
                }
            )
        else:
             st.info("👆 Click any RO row in the table above to view specific invoices.")

# -------------------------------------------------------------
# D. VENDOR COMMUNICATION HUB (CRASH-PROOF & CRM STYLE)
# -------------------------------------------------------------
elif choice == "📱 Vendor Communication Hub":
    st.markdown("<h2>Vendor Alerts & Messaging CRM</h2>", unsafe_allow_html=True)
    
    if 'Vendor_Perf_Summary' in data and 'Vendor_Perf_Raw' in data:
        df_vperf_sum = data['Vendor_Perf_Summary'].copy()
        df_vperf_raw = data['Vendor_Perf_Raw'].copy()
        
        # --- 1. VENDOR MASTER PANEL (ADMIN ONLY) ---
        if st.session_state.get('role') == 'Admin':
            with st.expander("🛠️ Manage Vendor Master Contacts", expanded=False):
                st.caption("Save Vendor WhatsApp and Email IDs for quick communication.")
                
                # Load existing master
                vendor_master_file = FILE_MAP.get("VENDOR_MASTER", os.path.join(DATA_DIR, "vendor_master.json"))
                v_master_data = {}
                if os.path.exists(vendor_master_file):
                    try:
                        with open(vendor_master_file, 'r') as f:
                            v_master_data = json.load(f)
                    except: pass
                
                with st.form("vendor_master_form"):
                    col_m1, col_m2, col_m3 = st.columns(3)
                    all_vendors_list = sorted(df_vperf_sum['VendorName'].dropna().unique().tolist())
                    vm_name = col_m1.selectbox("Select Vendor Name", all_vendors_list)
                    
                    # Pre-fill if exists
                    pre_wp = v_master_data.get(vm_name, {}).get("whatsapp", "")
                    pre_em = v_master_data.get(vm_name, {}).get("email", "")
                    
                    vm_wp = col_m2.text_input("WhatsApp No (with country code e.g. 9198...)", value=pre_wp)
                    vm_email = col_m3.text_input("Email ID", value=pre_em)
                    
                    if st.form_submit_button("💾 Save to Master"):
                        v_master_data[vm_name] = {"whatsapp": vm_wp.strip(), "email": vm_email.strip()}
                        with open(vendor_master_file, 'w') as f:
                            json.dump(v_master_data, f)
                        st.success(f"Contact details for {vm_name} saved successfully!")
            st.markdown("---")
        
        # --- 2. FILTERS & INDIVIDUAL VENDOR SEARCH ---
        st.markdown("### 🔍 Individual Vendor Messaging")
        col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
        
        all_zones = sorted(df_vperf_sum['Zone'].dropna().unique().tolist())
        selected_zone = col1.selectbox("Filter Zone:", ["ALL"] + all_zones)
        if selected_zone != "ALL":
            df_vperf_sum = df_vperf_sum[df_vperf_sum['Zone'] == selected_zone]
            df_vperf_raw = df_vperf_raw[df_vperf_raw['Zone'] == selected_zone]
            
        all_ros = sorted(df_vperf_sum['Origin RO'].dropna().unique().tolist())
        selected_ro = col2.selectbox("Filter RO:", ["ALL"] + all_ros)
        if selected_ro != "ALL":
            df_vperf_sum = df_vperf_sum[df_vperf_sum['Origin RO'] == selected_ro]
            df_vperf_raw = df_vperf_raw[df_vperf_raw['Origin RO'] == selected_ro]

        all_routes = sorted(df_vperf_sum['Route Path'].dropna().unique().tolist())
        selected_route = col3.selectbox("Filter Route:", ["ALL"] + all_routes)
        if selected_route != "ALL":
            df_vperf_sum = df_vperf_sum[df_vperf_sum['Route Path'] == selected_route]
            df_vperf_raw = df_vperf_raw[df_vperf_raw['Route Path'] == selected_route]
            
        all_vendors_filtered = sorted(df_vperf_sum['VendorName'].dropna().unique().tolist())
        selected_vendor = col4.selectbox("Select Vendor for Detailed View:", ["ALL"] + all_vendors_filtered)
        
        # Display Table for the selected individual vendor
        if selected_vendor != "ALL":
            df_display_ind = df_vperf_sum[df_vperf_sum['VendorName'] == selected_vendor]
            target_vendor = selected_vendor
            
            st.markdown(f"#### Performance View: `{target_vendor}`")
            st.dataframe(df_display_ind[['Route Path', 'Legwise', 'Legs', 'Total_Trips', 'Ontime Arrival', 'Late Arrival']], use_container_width=True, hide_index=True)

            if st.session_state.get('role') == 'Admin':
                # Re-read master file directly
                v_master_data_live = {}
                if os.path.exists(FILE_MAP.get("VENDOR_MASTER")):
                    try:
                        with open(FILE_MAP.get("VENDOR_MASTER"), 'r') as f:
                            v_master_data_live = json.load(f)
                    except: pass
                    
                ven_contact = v_master_data_live.get(target_vendor, {})
                wp_num = ven_contact.get("whatsapp", "")
                email_id = ven_contact.get("email", "")
                
                if not wp_num and not email_id:
                    st.warning(f"⚠️ Contact details for '{target_vendor}' are not saved in the Vendor Master.")
                
                ven_sum = df_vperf_sum[df_vperf_sum['VendorName'] == target_vendor].copy()
                ven_raw = df_vperf_raw[df_vperf_raw['VendorName'] == target_vendor].copy()
                
                total_trips = ven_sum['Total_Trips'].sum() if not ven_sum.empty else 0
                
                # --- Fixed Width Padded Table for Email/WhatsApp ---
                summary_text_breakdown = "ROUTE & LEG".ljust(35) + "| TRIPS | ONTIME | LATE\n"
                summary_text_breakdown += "-"*65 + "\n"
                for _, row in ven_sum.iterrows():
                    route_leg = f"{row['Route Path']} ({row['Legwise']})"
                    route_leg = route_leg[:33].ljust(35)
                    trips = str(row['Total_Trips']).center(5)
                    ontime = str(row['Ontime Arrival']).ljust(8)
                    late = str(row['Late Arrival']).ljust(8)
                    summary_text_breakdown += f"{route_leg}| {trips} | 🟢 {ontime} | 🔴 {late}\n"
                summary_text_breakdown += "-"*65 + "\n"

                msg = f"Dear {target_vendor},\n\n"
                msg += f"Please find attached the arrival performance report for your vehicles.\n"
                msg += f"Total Trips Assigned: {total_trips}\n\n"
                msg += f"Performance Summary:\n{summary_text_breakdown}\n"
                msg += f"Kindly review the attached Excel sheet for raw details and ensure on-time arrivals.\n\n"
                msg += "Thanks,\nAjay Singh Rawat\nFleet operation Executive"
                
                # Generate Excel with BORDERS, AUTOFIT & ACTUAL DATETIME COLUMNS
                output_ven = io.BytesIO()
                with pd.ExcelWriter(output_ven, engine='xlsxwriter') as writer:
                    ven_sum.to_excel(writer, sheet_name='Performance_Summary', index=False)
                    ven_raw.to_excel(writer, sheet_name='Raw_Trip_Details', index=False)
                    
                    workbook = writer.book
                    format_hdr = workbook.add_format({'bold': True, 'bg_color': '#1E3A8A', 'font_color': 'white', 'border': 1, 'text_wrap': True})
                    format_data = workbook.add_format({'border': 1})
                    
                    for sheet in ['Performance_Summary', 'Raw_Trip_Details']:
                        worksheet = writer.sheets[sheet]
                        df_temp = ven_sum if sheet == 'Performance_Summary' else ven_raw
                        for col_num, value in enumerate(df_temp.columns.values):
                            worksheet.write(0, col_num, value, format_hdr)
                        for i, col in enumerate(df_temp.columns):
                            col_width = max(df_temp[col].astype(str).map(len).max(), len(str(col))) + 2
                            worksheet.set_column(i, i, min(col_width, 40), format_data)

                ven_file_name = f"{target_vendor}_Performance_Report.xlsx"
                
                c1, c2, c3 = st.columns(3)
                c1.download_button("1️⃣ Download Excel 📊", data=output_ven.getvalue(), file_name=ven_file_name, mime="application/vnd.ms-excel", use_container_width=True)
                
                encoded_msg = urllib.parse.quote(msg)
                wp_url = f"https://api.whatsapp.com/send?phone={wp_num}&text={encoded_msg}"
                c2.markdown(f'<a href="{wp_url}" target="_blank"><button style="background-color: #25D366; color: white; padding: 10px; border: none; border-radius: 5px; width: 100%; cursor: pointer;">2️⃣ Open WhatsApp 💬</button></a>', unsafe_allow_html=True)
                
                subject = urllib.parse.quote(f"Trackon Performance Report: {target_vendor}")
                gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&to={urllib.parse.quote(email_id)}&su={subject}&body={encoded_msg}&authuser=lh.fleetops@trackon.in"
                c3.markdown(f'<a href="{gmail_url}" target="_blank"><button style="background-color: #DB4437; color: white; padding: 10px; border: none; border-radius: 5px; width: 100%; cursor: pointer;">3️⃣ Open in Gmail 🌐</button></a>', unsafe_allow_html=True)
            else:
                st.info("🔒 Message Sending & Downloading features are restricted to Admin access.")

        st.markdown("---")
        
        # --- 3. BULK MESSAGING HUB (ADMIN ONLY) ---
        if st.session_state.get('role') == 'Admin':
            st.markdown("### 🚀 Bulk Messaging Hub (All Saved Vendors)")
            st.caption("Fatafat sabhi saved vendors ko mail bhejne ke liye yahan se click karein.")
            
            v_master_data_live = {}
            if os.path.exists(FILE_MAP.get("VENDOR_MASTER")):
                try:
                    with open(FILE_MAP.get("VENDOR_MASTER"), 'r') as f:
                        v_master_data_live = json.load(f)
                except: pass
                
            saved_vendors_in_data = [v for v in v_master_data_live.keys() if v in all_vendors_filtered]
            
            if not saved_vendors_in_data:
                st.info("Koi bhi saved vendor current filtered data mein nahi mila. Vendor Master mein details save karein.")
            else:
                for v_name in saved_vendors_in_data:
                    v_email = v_master_data_live[v_name].get("email", "")
                    
                    v_sum = df_vperf_sum[df_vperf_sum['VendorName'] == v_name].copy()
                    if v_sum.empty: continue
                        
                    v_total_trips = v_sum['Total_Trips'].sum()
                    
                    v_summary_table = "ROUTE & LEG".ljust(35) + "| TRIPS | ONTIME | LATE\n"
                    v_summary_table += "-"*65 + "\n"
                    for _, row in v_sum.iterrows():
                        route_leg = f"{row['Route Path']} ({row['Legwise']})"
                        route_leg = route_leg[:33].ljust(35)
                        trips = str(row['Total_Trips']).center(5)
                        ontime = str(row['Ontime Arrival']).ljust(8)
                        late = str(row['Late Arrival']).ljust(8)
                        v_summary_table += f"{route_leg}| {trips} | 🟢 {ontime} | 🔴 {late}\n"
                    v_summary_table += "-"*65 + "\n"

                    v_msg = f"Dear {v_name},\n\nPlease find attached the arrival performance report for your vehicles.\nTotal Trips Assigned: {v_total_trips}\n\nPerformance Summary:\n{v_summary_table}\nKindly review the attached Excel sheet for raw details and ensure on-time arrivals.\n\nThanks,\nAjay Singh Rawat\nFleet operation Executive"
                    
                    v_subject = urllib.parse.quote(f"Trackon Performance Report: {v_name}")
                    v_encoded_msg = urllib.parse.quote(v_msg)
                    v_gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&to={urllib.parse.quote(v_email)}&su={v_subject}&body={v_encoded_msg}&authuser=lh.fleetops@trackon.in"
                    
                    b1, b2 = st.columns([3, 1])
                    b1.markdown(f"**{v_name}** (Trips: {v_total_trips} | Email: {v_email})")
                    b2.markdown(f'<a href="{v_gmail_url}" target="_blank"><button style="background-color: #DB4437; color: white; padding: 5px 15px; border: none; border-radius: 4px; width: 100%; cursor: pointer; font-size: 14px;">✉️ Compose Gmail</button></a>', unsafe_allow_html=True)
                    st.divider()

    else:
        st.info("No data available. Please process the dashboard first.")

# -------------------------------------------------------------
# E. CPK & UTILIZATION 
# -------------------------------------------------------------
elif choice == "💰 Network Utilization":
    st.markdown("<h2>Network Utilization & CPK</h2>", unsafe_allow_html=True)
    if 'Up_Down_Route_Summary' in data and 'CPK_Raw_Data' in data:
        df_cpk_master = data['Up_Down_Route_Summary'].copy()
        df_cpk_raw = data['CPK_Raw_Data']
        
        col1, col2, col3 = st.columns([1, 1, 2])
        
        all_zones = sorted(df_cpk_master['Zone'].dropna().unique().tolist())
        zone_filter = col1.selectbox("Filter Zone:", ["ALL"] + all_zones)
        
        if zone_filter != "ALL":
            df_cpk_master = df_cpk_master[df_cpk_master['Zone'] == zone_filter]
            
        all_ros = sorted(df_cpk_master['VendorRO'].dropna().unique().tolist())
        ro_filter = col2.selectbox("Filter RO:", ["ALL"] + all_ros)
        
        if ro_filter != "ALL": 
            df_cpk_view = df_cpk_master[df_cpk_master['VendorRO'] == ro_filter].copy()
        else:
            df_cpk_view = df_cpk_master.copy()
            
        search_q = col3.text_input("🔍 Quick Search:", placeholder="Search Route, Vendor...")
        
        if search_q:
            mask = df_cpk_view.astype(str).apply(lambda x: x.str.contains(search_q, case=False, regex=False, na=False)).any(axis=1)
            df_cpk_view = df_cpk_view[mask]

        m1, m2, m3 = st.columns(3)
        m1.metric("Total Trips", int(df_cpk_view['Total Trips'].sum()))
        avg_util = (df_cpk_view['Total Carried Wt'].sum() / df_cpk_view['Total Capacity'].sum() * 100) if df_cpk_view['Total Capacity'].sum() > 0 else 0
        m2.metric("Overall Utilization", f"{avg_util:.1f}%")
        avg_cpk = (df_cpk_view['Total Trip Cost'].sum() / df_cpk_view['Total Carried Wt'].sum()) if df_cpk_view['Total Carried Wt'].sum() > 0 else 0
        m3.metric("Overall CPK", f"₹ {avg_cpk:.2f}")
        
        st.markdown("### Top Priority Utilization List")
        
        df_cpk_view = df_cpk_view.sort_values(by='Overall Util %', ascending=True)
        disp_df = df_cpk_view.copy()
        
        def add_total_row(df):
            if df.empty: return df
            tot_trips = df['Total Trips'].sum() if 'Total Trips' in df.columns else 0
            tot_cap = df['Total Capacity'].sum() if 'Total Capacity' in df.columns else 0
            tot_wt = df['Total Carried Wt'].sum() if 'Total Carried Wt' in df.columns else 0
            tot_cost = df['Total Trip Cost'].sum() if 'Total Trip Cost' in df.columns else 0
            
            tot_cpk = tot_cost / tot_wt if tot_wt > 0 else 0
            tot_util = tot_wt / tot_cap if tot_cap > 0 else 0
            tot_avg_cost = tot_cost / tot_trips if tot_trips > 0 else 0
            
            tot_dict = {c: '-' for c in df.columns}
            tot_dict['Zone'] = 'TOTAL'
            tot_dict['VendorRO'] = 'TOTAL'
            if 'Total Trips' in df.columns: tot_dict['Total Trips'] = tot_trips
            if 'Total Capacity' in df.columns: tot_dict['Total Capacity'] = tot_cap
            if 'Total Carried Wt' in df.columns: tot_dict['Total Carried Wt'] = tot_wt
            if 'Total Trip Cost' in df.columns: tot_dict['Total Trip Cost'] = tot_cost
            if 'Overall CPK' in df.columns: tot_dict['Overall CPK'] = tot_cpk
            if 'Overall Util %' in df.columns: tot_dict['Overall Util %'] = tot_util
            if 'Avg Trip Cost' in df.columns: tot_dict['Avg Trip Cost'] = f"₹{tot_avg_cost:.2f}"
            
            return pd.concat([df, pd.DataFrame([tot_dict])], ignore_index=True)

        disp_df = add_total_row(disp_df)
        
        for col in ['Overall CPK', 'Total Trip Cost']: 
            if col in disp_df.columns: 
                disp_df[col] = disp_df[col].apply(lambda x: f"₹{x:.2f}" if isinstance(x, (int, float)) else x)
        if 'Overall Util %' in disp_df.columns:
            disp_df['Overall Util %'] = disp_df['Overall Util %'].apply(lambda x: f"{x * 100:.2f}%" if isinstance(x, (int, float)) else x)
            
        view_df = disp_df.drop(columns=['SortKey', 'Super_SortKey'], errors='ignore')
        
        def highlight_cpk_util(val, col):
            if pd.isna(val) or val == '-': return ''
            if col == 'Overall Util %':
                try:
                    pct = float(str(val).replace('%', '').strip())
                    if pct < 50: return 'color: #ff5252; font-weight: bold;' 
                    elif pct < 80: return 'color: #ffd740; font-weight: bold;'
                    else: return 'color: #69f0ae; font-weight: bold;'
                except: return ''
            elif col == 'Overall CPK':
                return 'color: #40c4ff; font-weight: bold;'
            return ''

        styled_view = view_df.style
        if hasattr(styled_view, 'map'):
            styled_view = styled_view.map(lambda x: highlight_cpk_util(x, 'Overall Util %'), subset=['Overall Util %'])
            styled_view = styled_view.map(lambda x: highlight_cpk_util(x, 'Overall CPK'), subset=['Overall CPK'])
        else:
            styled_view = styled_view.applymap(lambda x: highlight_cpk_util(x, 'Overall Util %'), subset=['Overall Util %'])
            styled_view = styled_view.applymap(lambda x: highlight_cpk_util(x, 'Overall CPK'), subset=['Overall CPK'])

        selection_cpk = st.dataframe(
            styled_view, 
            use_container_width=True, 
            height=300, 
            on_select="rerun", 
            selection_mode="single-row"
        )
        
        if selection_cpk and selection_cpk.get('selection', {}).get('rows'):
            selected_idx = selection_cpk['selection']['rows'][0]
            
            if selected_idx >= len(df_cpk_view):
                st.warning("Please click a valid route row, not the TOTAL row.")
            else:
                selected_super_sortkey = df_cpk_view.iloc[selected_idx]['SortKey']
                selected_route_name = df_cpk_view.iloc[selected_idx]['Route (UP/DOWN)']
                selected_vendor = df_cpk_view.iloc[selected_idx]['Vendor(s)']
                selected_ro_val = df_cpk_view.iloc[selected_idx]['VendorRO']
                
                st.markdown("---")
                st.markdown(f"### 📄 Details for `{selected_vendor}` on `{selected_route_name}`")
                
                vendors_list = [v.strip().upper() for v in str(selected_vendor).split(',')]
                
                raw_trips = df_cpk_raw[
                    (df_cpk_raw['SortKey'] == selected_super_sortkey) & 
                    (df_cpk_raw['VendorName'].astype(str).str.strip().str.upper().isin(vendors_list)) &
                    (df_cpk_raw['RO_Clean'].astype(str).str.strip().str.upper() == str(selected_ro_val).strip().upper())
                ].copy()

                raw_cols = ['Zone', 'RO_Clean', 'Final_Route', 'Final_Type', 'VendorName', 'Vehicle No', 'Date', 'Cap', 'Wt', 'Trips', 'Cost']
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
            st.info("👆 Click any row above to view raw trip details.")
    else:
        st.info("Please process CPK data first.")
