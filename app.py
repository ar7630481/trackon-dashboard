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
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
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
    "VENDOR_MASTER": os.path.join(DATA_DIR, "vendor_master.xlsx"),
    "FINAL_OUTPUT": os.path.join(DATA_DIR, "Auto_Generated_Monitoring_Data.xlsx"),
    "EXECUTIVE_REPORT": os.path.join(DATA_DIR, "Trackon_VIP_Executive_Report.xlsx"),
    "RATE_CORRECTIONS": os.path.join(DATA_DIR, "rate_corrections.json")
}

def get_ist_now():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)

# ==========================================
# 2. AUTHENTICATION
# ==========================================
USERS = {"user": "5272", "admin": "9211213"}

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'role' not in st.session_state: st.session_state['role'] = None

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
                else: st.error("❌ Invalid Username or Password!")
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
        if temp_path and os.path.exists(temp_path): os.remove(temp_path)

def get_file_time(key):
    path = FILE_MAP[key]
    if os.path.exists(path):
        ts = os.path.getmtime(path)
        return datetime.datetime.fromtimestamp(ts).strftime('%d %b %Y, %I:%M %p')
    return "Not Uploaded Yet ❌"

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
# 4. VIP EXCEL GENERATOR (Direct to Disk)
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
                col_len = max(df_to_write[col].astype(str).map(len).max(), len(str(col))) + 2 if not df_to_write.empty else len(str(col)) + 2
                worksheet.set_column(i, i, min(col_len, 35))

        if 'Legwise_Route_Summary' in data_dict:
            df_ops = data_dict['Legwise_Route_Summary'].copy()
            cols_to_drop = ['OO_Cnt', 'LO_Cnt', 'OL_Cnt', 'LL_Cnt', 'Ontime_Dep_IT_Cnt', 'Late_Dep_IT_Cnt']
            df_ops = df_ops.drop(columns=[c for c in cols_to_drop if c in df_ops.columns], errors='ignore')
            df_ops.to_excel(writer, sheet_name='Operations_Summary', index=False)
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
            pvt.to_excel(writer, sheet_name='Payment_Summary')
            worksheet = writer.sheets['Payment_Summary']
            worksheet.write(0, 0, "RO Name", header_format)
            for col_num, value in enumerate(pvt.columns.values): worksheet.write(0, col_num + 1, value, header_format)
            worksheet.set_column(0, len(pvt.columns), 20)
            df_pay.to_excel(writer, sheet_name='Payment_Raw', index=False)
            apply_manager_formatting('Payment_Raw', df_pay)

        if 'Up_Down_Route_Summary' in data_dict:
            df_cpk = data_dict['Up_Down_Route_Summary'].copy()
            df_cpk.to_excel(writer, sheet_name='Network_Utilization', index=False)
            apply_manager_formatting('Network_Utilization', df_cpk)

        if 'CPK_Raw_Data' in data_dict:
            df_cpk_raw = data_dict['CPK_Raw_Data'].copy()
            df_cpk_raw.to_excel(writer, sheet_name='Network_Raw', index=False)
            apply_manager_formatting('Network_Raw', df_cpk_raw)

# ==========================================
# 5. MAIN DATA PROCESSING (Memory Safe)
# ==========================================
def process_all_data():
    progress = st.progress(0)
    status_text = st.empty()
    data_for_export = {}
    temp_output = None
    try:
        ro_zone_map = {}
        if os.path.exists(FILE_MAP["BRANCH_MASTER"]):
            df_brn = pd.read_excel(FILE_MAP["BRANCH_MASTER"], sheet_name="Sheet1")
            df_brn.columns = df_brn.columns.astype(str).str.strip()
            b_col = next((c for c in df_brn.columns if 'branchcode' in c.lower().replace(' ', '')), 'RPTBranchcode')
            r_col = next((c for c in df_brn.columns if 'rptro' in c.lower().replace(' ', '')), 'RPTRO')
            z_col = next((c for c in df_brn.columns if 'zone' in c.lower().replace(' ', '')), 'Zone')
            df_brn[r_col] = df_brn[r_col].astype(str).str.strip().str.upper()
            ro_zone_map = df_brn.drop_duplicates(subset=[r_col]).set_index(r_col)[z_col].to_dict()

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
            df_pay.rename(columns=rename_dict, inplace=True)
            
            req_cols = ['RO Name', 'Category', 'Vendor Name', 'Invoice Id', 'Invoice Date', 'Amount', 'Status', 'Pending With', 'Last Approved At', 'Finance Revert Remarks 1', 'Approver Revert Remarks']
            for req in req_cols:
                if req not in df_pay.columns: df_pay[req] = ""
            df_pay['Vendor Name'] = df_pay['Vendor Name'].fillna('').astype(str).str.upper().str.strip()
            df_pay['Status'] = df_pay['Status'].fillna('').astype(str).str.upper()
            df_pay['RO Name Clean'] = df_pay['RO Name'].astype(str).str.strip().str.upper()
            df_pay['Zone'] = df_pay['RO Name Clean'].map(ro_zone_map).fillna('UNKNOWN ZONE')
            df_pay['Finance Revert Remarks 1'] = df_pay['Finance Revert Remarks 1'].fillna('')
            df_pay['Approver Revert Remarks'] = df_pay['Approver Revert Remarks'].fillna('')
            df_pay['Revert Remarks'] = np.where(df_pay['Finance Revert Remarks 1'] != '', df_pay['Finance Revert Remarks 1'], df_pay['Approver Revert Remarks'])
            
            conds = [
                (df_pay['Status'].str.contains('PAYMENT') | df_pay['Pending With'].astype(str).str.upper().str.contains('PAYMENT')),
                (df_pay['Status'].str.contains('FINANCE') | df_pay['Pending With'].astype(str).str.upper().str.contains('FINANCE|LEVEL 3') | df_pay['Status'].str.contains('HOLD')),
                (df_pay['Revert Remarks'] != '') | (df_pay['Status'].str.contains('DRAFT')),
                (df_pay['Status'].str.contains('PENDING'))
            ]
            df_pay['Department Bucket'] = np.select(conds, ["4. PAYMENT PENDING", "3. FINANCE PENDING", "1. USER / DRAFT PENDING", "2. COST CONTROL PENDING"], "5. OTHER PENDING")
            today = pd.to_datetime('today').normalize()
            df_pay['Last Approved At'] = pd.to_datetime(df_pay['Last Approved At'], dayfirst=True, errors='coerce').dt.normalize()
            df_pay['Invoice Date'] = pd.to_datetime(df_pay['Invoice Date'], dayfirst=True, errors='coerce').dt.normalize()
            df_pay['Base Date'] = df_pay['Last Approved At'].combine_first(df_pay['Invoice Date']).fillna(today)
            df_pay['Days Pending'] = (today - df_pay['Base Date']).dt.days
            df_pay['Aging Bucket'] = np.where(df_pay['Days Pending'] <= 5, "1. 0-5 Days", "2. >5 Days")
            df_pay['Invoice Month'] = df_pay['Invoice Date'].dt.strftime('%b-%Y').fillna("UNKNOWN")
            
            df_master = df_pay[["Zone", "RO Name", "Category", "Vendor Name", "Invoice Id", "Aging Bucket", "Invoice Month", "Days Pending", "Status", "Pending With", "Revert Remarks", "Department Bucket", "Amount"]]
            data_for_export['Master_Database'] = df_master
            del df_pay
        progress.progress(20)

        status_text.text("⚙️ Processing Operations Data...")
        if os.path.exists(FILE_MAP["LEGWISE"]) and os.path.exists(FILE_MAP["ROUTE_MASTER"]):
            df_leg_all = pd.read_excel(FILE_MAP["LEGWISE"], sheet_name="Sheet1")
            df_rte = pd.read_excel(FILE_MAP["ROUTE_MASTER"], sheet_name="RoutePathReportModel")
            
            df_leg_all.columns = df_leg_all.columns.str.strip()
            df_leg_all['Leg_Num'] = df_leg_all['Legwise'].astype(str).str.extract(r'(\d+)').astype(float).fillna(1)
            df_leg_all['Legs'] = df_leg_all['CD_FromBranch'].astype(str) + " to " + df_leg_all['CD_ToBranch'].astype(str)
            df_leg_all.rename(columns={'Min_CD_StartDatetime': 'Actual Departure Time', 'Max_CD_EndDatetime': 'Actual Arrival Time', 'Route': 'Route Path', 'LH_Type': 'LH Type'}, inplace=True)
            
            df_leg_all['CD_FromBranch_Clean'] = df_leg_all['CD_FromBranch'].astype(str).str.strip().str.upper()
            if os.path.exists(FILE_MAP["BRANCH_MASTER"]):
                df_brn_m = pd.read_excel(FILE_MAP["BRANCH_MASTER"], sheet_name="Sheet1")
                b_col = next((c for c in df_brn_m.columns if 'branchcode' in c.lower().replace(' ', '')), 'RPTBranchcode')
                r_col = next((c for c in df_brn_m.columns if 'rptro' in c.lower().replace(' ', '')), 'RPTRO')
                z_col = next((c for c in df_brn_m.columns if 'zone' in c.lower().replace(' ', '')), 'Zone')
                df_brn_m[b_col] = df_brn_m[b_col].astype(str).str.strip().str.upper()
                df_leg_all = df_leg_all.merge(df_brn_m[[b_col, r_col, z_col]].drop_duplicates(b_col), left_on='CD_FromBranch_Clean', right_on=b_col, how='left')
                df_leg_all.rename(columns={r_col: 'Origin RO', z_col: 'Zone'}, inplace=True)
            df_leg_all['Origin RO'] = df_leg_all.get('Origin RO', pd.Series(['Missing']*len(df_leg_all))).fillna('Missing RO')
            df_leg_all['Zone'] = df_leg_all.get('Zone', pd.Series(['UNKNOWN']*len(df_leg_all))).fillna('UNKNOWN ZONE')
            
            df_leg_all[['Origin', 'Destination']] = df_leg_all['Route Path'].apply(lambda x: pd.Series(extract_orig_dest(x)))
            df_leg_all['E2E_Pair'] = df_leg_all['Route Path'].apply(get_route_pair)

            df_leg_all['Actual Departure Time'] = pd.to_datetime(df_leg_all['Actual Departure Time'], errors='coerce')
            df_leg_all['Actual Arrival Time'] = pd.to_datetime(df_leg_all['Actual Arrival Time'], errors='coerce')
            
            df_leg_all['Scheduled Departure Time'] = df_leg_all['Actual Departure Time'] - pd.Timedelta(hours=1)
            df_leg_all['Scheduled Arrival Time'] = df_leg_all['Actual Arrival Time'] - pd.Timedelta(hours=2)

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
            
            perf_cols = ['Route Path', 'Legwise', 'Legs', 'Given Driving Hours', 'Actual Driving Hours', 'Delay Hours', 'Remark with 15 min waiver', 'VendorName', 'VehicleNo', 'MasterCDNo', 'RouteCode', 'Zone', 'Origin RO']
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

            df_leg = df_leg_all[(df_leg_all['MCD_Created_By'] == 'SCHEDULED') & (df_leg_all['LH Type'].isin(['National LH', 'Zonal LH']))].copy()
            def calc_status(act, mode):
                if pd.isna(act): return f"No {mode}" if mode == 'Dep' else "In-Transit"
                return f"Late {mode}"
            df_leg['Dep_Status'] = df_leg.apply(lambda r: calc_status(r['Actual Departure Time'], 'Dep'), axis=1)
            df_leg['Arr_Status'] = df_leg.apply(lambda r: calc_status(r['Actual Arrival Time'], 'Arr'), axis=1)
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
        else:
            st.warning("⚠️ Operations files missing. Skipping Operations module.")

        progress.progress(60)

        status_text.text("⚙️ Calculating CPK & Utilization...")
        if os.path.exists(FILE_MAP["CPK_UTIL"]):
            df_raw = pd.read_excel(FILE_MAP["CPK_UTIL"])
            df_raw['Trips'] = pd.to_numeric(df_raw.get('Trips', 1), errors='coerce').fillna(1)
            df_raw['Cost'] = pd.to_numeric(df_raw.get('Cost', 0), errors='coerce').fillna(0)
            df_raw['Wt'] = pd.to_numeric(df_raw.get('Wt', 0), errors='coerce').fillna(0)
            df_raw['Cap'] = pd.to_numeric(df_raw.get('Cap', 0), errors='coerce').fillna(0)
            df_raw['Zone'] = df_raw.get('Zone', 'UNKNOWN')
            df_raw['RO_Clean'] = df_raw.get('VendorRO', 'UNKNOWN')
            df_raw['SortKey'] = df_raw.get('Route', 'Unknown')
            df_raw['Final_Route'] = df_raw.get('Route', 'Unknown')
            df_raw['Final_Type'] = df_raw.get('Type', 'Unknown')
            
            if os.path.exists(FILE_MAP["RATE_CORRECTIONS"]):
                try:
                    with open(FILE_MAP["RATE_CORRECTIONS"], 'r') as f: corrections = json.load(f)
                    for corr in corrections:
                        mask = (df_raw['Final_Route'].str.upper() == corr['route'].upper()) & (df_raw['Cap'] == float(corr['capacity']))
                        df_raw.loc[mask, 'Cost'] = float(corr['new_cost']) * df_raw.loc[mask, 'Trips']
                except: pass
            
            data_for_export['CPK_Raw_Data'] = df_raw
            if not df_raw.empty:
                df_raw['Trip_Rate'] = np.where(df_raw['Trips'] > 0, df_raw['Cost'] / df_raw['Trips'], 0).round(2)
                df_raw['Trip_Rate_Str'] = "₹" + df_raw['Trip_Rate'].astype(str)
                
                agg_updn = df_raw.groupby(['RO_Clean', 'Zone', 'Final_Route', 'Final_Type', 'Cap', 'SortKey', 'Trip_Rate']).agg(
                    Total_Trips=('Trips', 'sum'),
                    Total_Carried_Wt=('Wt', 'sum'),
                    Total_Trip_Cost=('Cost', 'sum'),
                    VendorName=('VendorName', lambda x: ', '.join(sorted(set(x.dropna().astype(str))))),
                    Avg_Trip_Cost=('Trip_Rate_Str', lambda x: ', '.join(sorted(set(x.dropna().astype(str)))))
                ).reset_index()

                agg_updn['Total Capacity'] = agg_updn['Cap'] * agg_updn['Total_Trips']
                agg_updn['Overall CPK'] = np.where(agg_updn['Total_Carried_Wt'] > 0, agg_updn['Total_Trip_Cost'] / agg_updn['Total_Carried_Wt'], 0)
                agg_updn['Overall Util %'] = np.where(agg_updn['Total Capacity'] > 0, agg_updn['Total_Carried_Wt'] / agg_updn['Total Capacity'], 0)
                
                updn_final = agg_updn[['Zone', 'RO_Clean', 'Final_Route', 'Final_Type', 'Overall CPK', 'Overall Util %', 'Cap', 'Total Capacity', 'Total_Carried_Wt', 'Avg_Trip_Cost', 'Total_Trip_Cost', 'Total_Trips', 'VendorName', 'SortKey']]
                updn_final.columns = ["Zone", "VendorRO", "Route (UP/DOWN)", "Type", "Overall CPK", "Overall Util %", "VehCap (Base)", "Total Capacity", "Total Carried Wt", "Avg Trip Cost", "Total Trip Cost", "Total Trips", "Vendor(s)", "SortKey"]
                data_for_export['Up_Down_Route_Summary'] = updn_final

        progress.progress(80)
        if not data_for_export:
            status_text.warning("No datasets were processed. Check the uploaded files.")
            return False
            
        status_text.text("⚙️ Saving Raw Database...")
        with tempfile.NamedTemporaryFile(dir=DATA_DIR, suffix='.xlsx', delete=False) as tmp: temp_output = tmp.name
        with pd.ExcelWriter(temp_output, engine='xlsxwriter') as writer:
            for k, v in data_for_export.items(): v.to_excel(writer, sheet_name=k, index=False)
        os.replace(temp_output, FILE_MAP["FINAL_OUTPUT"])
        
        progress.progress(90)
        status_text.text("⚙️ Generating VIP Executive Report...")
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
        if temp_output and os.path.exists(temp_output): os.remove(temp_output)
        gc.collect()

# ==========================================
# 6. SIDEBAR: ADMIN PANEL
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
        f8 = st.file_uploader("8. Vendor Contact Master", type=['xlsx'])
        if save_file(f8, "VENDOR_MASTER"): st.success("Saved!")

    if os.path.exists(FILE_MAP["VENDOR_MASTER"]):
        with st.sidebar.expander("📝 View / Edit Vendor Master", expanded=False):
            try:
                vm_df = pd.read_excel(FILE_MAP["VENDOR_MASTER"])
                edited_vm = st.data_editor(vm_df, num_rows="dynamic", use_container_width=True)
                if st.button("💾 Save Vendor Updates", use_container_width=True):
                    edited_vm.to_excel(FILE_MAP["VENDOR_MASTER"], index=False)
                    st.success("Vendor Master Updated Successfully!")
            except Exception as e:
                st.error(f"Error loading Vendor Master: {e}")

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
                        with open(rate_file, 'r') as f: rates = json.load(f)
                    except: pass
                rates.append({"route": rc_route.strip(), "capacity": rc_cap, "new_cost": rc_cost, "eff_date": rc_date.strftime('%Y-%m-%d')})
                with open(rate_file, 'w') as f: json.dump(rates, f)
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
    if not os.path.exists(path): return {}
    cache_key = (file_version(path), page)
    cached = st.session_state.get('_dashboard_cache')
    if cached and cached[0] == cache_key: return cached[1]
    st.session_state.pop('_dashboard_cache', None)
    gc.collect()
    try:
        with st.spinner("Loading selected dashboard..."):
            with pd.ExcelFile(path, engine='openpyxl') as workbook:
                data = {name: workbook.parse(name) for name in MENU_SHEETS[page] if name in workbook.sheet_names}
        st.session_state['_dashboard_cache'] = (cache_key, data)
        return data
    except Exception as exc:
        st.error(f"Cannot read the processed Excel file: {exc}")
        st.stop()

if st.session_state.pop('_processing_success', False):
    st.success("Data refreshed successfully. Your Executive Report is ready to download!")

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
    except Exception as exc: pass
        
    ts = os.path.getmtime(FILE_MAP["FINAL_OUTPUT"])
    ist = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    dt = datetime.datetime.fromtimestamp(ts, tz=ist).strftime('%d %b %Y, %I:%M %p')
    st.sidebar.info(f"📊 Dashboard Refreshed: {dt} (IST)")

data = load_dashboard_data(choice)
if not data:
    st.warning("No processed data for this page. Admin must upload files and process data.")
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
        display_cols = ['Route Path', 'Legwise', 'Legs', 'Total_Trips', 'Ontime Dep, Ontime Arr %', 'Ontime Dep, Late Arr %', 'Late Dep, Late Arr %', 'Late Dep, Ontime Arr %']
        
        display_cols = [c for c in display_cols if c in df_leg_sum.columns]
        df_display = df_leg_sum[display_cols].copy()
        
        if search_q: df_display = df_display[df_display.astype(str).apply(lambda x: x.str.contains(search_q, case=False, regex=False, na=False)).any(axis=1)]

        styled_df = df_display.style
        pct_cols = [c for c in df_display.columns if '%' in c]
        for col in pct_cols:
            def highlight_cells(val, c=col):
                if not isinstance(val, str) or '%' not in val: return ''
                try: pct = float(val.split('%')[0].strip())
                except: return ''
                if pct == 0: return 'color: #78909C;' 
                if 'Late Dep, Late Arr' in c: return 'background-color: rgba(211, 47, 47, 0.15); color: #ff5252; font-weight: bold;'
                elif 'Ontime Dep, Ontime Arr' in c: return 'background-color: rgba(56, 142, 60, 0.15); color: #69f0ae; font-weight: bold;'
                elif 'Ontime Dep, Late Arr' in c: return 'background-color: rgba(245, 127, 23, 0.15); color: #ffd740; font-weight: bold;'
                elif 'Late Dep, Ontime Arr' in c: return 'background-color: rgba(123, 31, 162, 0.15); color: #e040fb; font-weight: bold;'
                return ''
            if hasattr(styled_df, 'map'): styled_df = styled_df.map(highlight_cells, subset=[col])
            else: styled_df = styled_df.applymap(highlight_cells, subset=[col])

        st.markdown("### Top Priority Routes Summary")
        selection = st.dataframe(styled_df, use_container_width=True, height=300, on_select="rerun", selection_mode="single-row")
        
        if selection and selection.get('selection', {}).get('rows'):
            selected_idx = selection['selection']['rows'][0]
            selected_route = df_display.iloc[selected_idx]['Route Path']
            selected_leg = df_display.iloc[selected_idx]['Legwise']
            
            st.markdown("---")
            st.markdown(f"### 📄 Details for `{selected_route}` - `{selected_leg}`")
            filtered_raw = df_raw_leg[(df_raw_leg['Route Path'] == selected_route) & (df_raw_leg['Legwise'] == selected_leg)].copy()
            st.dataframe(filtered_raw, use_container_width=True)

# -------------------------------------------------------------
# B. VENDOR PERFORMANCE 
# -------------------------------------------------------------
elif choice == "🚚 Vendor Performance":
    st.markdown("<h2>Vendor Performance (Routewise/Legwise)</h2>", unsafe_allow_html=True)
    if 'Vendor_Perf_Summary' in data and 'Vendor_Perf_Raw' in data:
        df_vperf_sum = data['Vendor_Perf_Summary'].copy()
        df_vperf_raw = data['Vendor_Perf_Raw'].copy()
        
        col1, col2, col3 = st.columns([1, 1, 2])
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

        search_q = col3.text_input("🔍 Quick Search:", placeholder="Search Route, Vendor, Leg...")
        display_cols = ['Route Path', 'Legwise', 'Legs', 'VendorName', 'Total_Trips', 'Ontime Arrival', 'Late Arrival', 'In-Transit']
        
        display_cols = [c for c in display_cols if c in df_vperf_sum.columns]
        df_display = df_vperf_sum[display_cols].copy()
        
        if search_q: df_display = df_display[df_display.astype(str).apply(lambda x: x.str.contains(search_q, case=False, regex=False, na=False)).any(axis=1)]
            
        styled_df = df_display.style
        pct_cols = [c for c in ['Ontime Arrival', 'Late Arrival', 'In-Transit'] if c in df_display.columns]
        for col in pct_cols:
            def highlight_perf(val, c=col):
                if not isinstance(val, str) or '%' not in val: return ''
                try: pct = float(val.split('%')[0].strip())
                except: return ''
                if pct == 0: return 'color: #78909C;' 
                if c == 'Late Arrival': return 'background-color: rgba(211, 47, 47, 0.15); color: #ff5252; font-weight: bold;'
                elif c == 'Ontime Arrival': return 'background-color: rgba(56, 142, 60, 0.15); color: #69f0ae; font-weight: bold;'
                elif c == 'In-Transit': return 'background-color: rgba(245, 127, 23, 0.15); color: #ffd740; font-weight: bold;'
                return ''
            if hasattr(styled_df, 'map'): styled_df = styled_df.map(highlight_perf, subset=[col])
            else: styled_df = styled_df.applymap(highlight_perf, subset=[col])

        st.markdown("### Vendor Arrival Performance Summary")
        selection = st.dataframe(styled_df, use_container_width=True, height=300, on_select="rerun", selection_mode="single-row")
        
        if selection and selection.get('selection', {}).get('rows'):
            selected_idx = selection['selection']['rows'][0]
            selected_route = df_display.iloc[selected_idx]['Route Path']
            selected_leg = df_display.iloc[selected_idx]['Legwise']
            selected_vendor = df_display.iloc[selected_idx]['VendorName']
            
            st.markdown("---")
            st.markdown(f"### 📄 Raw Data for `{selected_vendor}` on `{selected_route}` - `{selected_leg}`")
            filtered_raw = df_vperf_raw[(df_vperf_raw['Route Path'] == selected_route) & (df_vperf_raw['Legwise'] == selected_leg) & (df_vperf_raw['VendorName'] == selected_vendor)].copy()
            st.dataframe(filtered_raw, use_container_width=True)

# -------------------------------------------------------------
# C. VENDOR COMMUNICATION HUB
# -------------------------------------------------------------
elif choice == "📱 Vendor Communication Hub":
    st.markdown("<h2>Vendor Alerts & Messaging Hub</h2>", unsafe_allow_html=True)
    if 'Vendor_Perf_Raw' in data and 'Vendor_Perf_Summary' in data:
        df_vperf_raw = data['Vendor_Perf_Raw'].copy()
        df_vperf_sum = data['Vendor_Perf_Summary'].copy()
        
        vendor_master_dict = {}
        if os.path.exists(FILE_MAP.get("VENDOR_MASTER", "")):
            try:
                vm_df = pd.read_excel(FILE_MAP["VENDOR_MASTER"])
                for _, r in vm_df.iterrows():
                    v_name = str(r.get('Vendor Name', '')).strip().upper()
                    vendor_master_dict[v_name] = {
                        "whatsapp": str(r.get('WhatsApp Number', '')).split('.')[0],
                        "email": str(r.get('Email ID', ''))
                    }
            except: pass

        st.markdown("### ⚡ Bulk Auto-Send Alert (To ALL Late Vendors)")
        st.caption("Select Zone/RO if you only want to bulk send to specific regions. Leaving it as 'ALL' will target everyone.")
        
        df_late = df_vperf_raw[df_vperf_raw['Remark with 15 min waiver'] == 'Late Arrival'].copy()
        
        bc1, bc2 = st.columns(2)
        all_zones = sorted(df_late['Zone'].dropna().unique().tolist())
        bulk_zone = bc1.selectbox("Bulk Filter Zone:", ["ALL"] + all_zones)
        if bulk_zone != "ALL": df_late = df_late[df_late['Zone'] == bulk_zone]
            
        all_ros = sorted(df_late['Origin RO'].dropna().unique().tolist())
        bulk_ro = bc2.selectbox("Bulk Filter RO:", ["ALL"] + all_ros)
        if bulk_ro != "ALL": df_late = df_late[df_late['Origin RO'] == bulk_ro]

        all_late_vendors = sorted(df_late['VendorName'].dropna().unique().tolist())
        
        with st.expander("🚀 Execute Bulk Email Send"):
            st.warning(f"This will send individual performance Excel reports AND Summaries to {len(all_late_vendors)} vendors matching the filters.")
            with st.form("bulk_email_form"):
                sc1, sc2 = st.columns(2)
                sender_email_bulk = sc1.text_input("Your Email (Gmail/Outlook):", placeholder="ops@company.com", key="bulk_email")
                sender_pass_bulk = sc2.text_input("App Password:", type="password", placeholder="16-digit app password", key="bulk_pass")
                cc_email_bulk = st.text_input("CC Email ID (Optional, goes to all):", key="bulk_cc")
                bulk_send_btn = st.form_submit_button("Send Bulk Emails Now")
                
                if bulk_send_btn:
                    if not sender_email_bulk or not sender_pass_bulk:
                        st.error("Please provide Sender Email and App Password.")
                    elif len(all_late_vendors) == 0:
                        st.info("No late vendors found in the selected filters.")
                    else:
                        progress_bar = st.progress(0)
                        status_txt = st.empty()
                        sent_count = 0
                        
                        try:
                            smtp_server = "smtp.gmail.com" if "@gmail" in sender_email_bulk else "smtp.office365.com"
                            server = smtplib.SMTP(smtp_server, 587)
                            server.starttls()
                            server.login(sender_email_bulk, sender_pass_bulk)
                            
                            for i, vendor in enumerate(all_late_vendors):
                                vendor_email = vendor_master_dict.get(vendor.upper(), {}).get('email', '')
                                if not vendor_email or vendor_email == 'nan':
                                    continue
                                    
                                vendor_trips = df_late[df_late['VendorName'] == vendor]
                                top_trips = vendor_trips.head(5)
                                trip_str = ""
                                for _, row in top_trips.iterrows(): 
                                    trip_str += f"- Route: {row['Route Path']} | Veh: {row['VehicleNo']} | Delay: {row['Delay Hours']}
"
                                
                                # Fetch vendor specific summary for the text message
                                vendor_summary_df = df_vperf_sum[df_vperf_sum['VendorName'] == vendor]
                                sum_str = ""
                                if not vendor_summary_df.empty:
                                    sum_str = "
Here is your overall Route-wise performance summary:
"
                                    for _, s_row in vendor_summary_df.iterrows():
                                        sum_str += f"Route: {s_row['Route Path']} ({s_row['Legs']}) | Total Trips: {s_row['Total_Trips']} | Ontime: {s_row['Ontime Arrival']} | Late: {s_row['Late Arrival']}
"
                                
                                msg_body = f"Dear {vendor},

Please find attached the arrival performance report for your vehicles. The following trips have been consistently reported as late:

{trip_str}{sum_str}
Kindly take necessary actions to ensure on-time arrivals in the future.

Best Regards,
Trackon Command Center"
                                
                                msg_email = MIMEMultipart()
                                msg_email['From'] = sender_email_bulk
                                msg_email['To'] = vendor_email
                                if cc_email_bulk: msg_email['Cc'] = cc_email_bulk
                                msg_email['Subject'] = f"Trackon Performance Alert: {vendor}"
                                msg_email.attach(MIMEText(msg_body, 'plain'))
                                
                                output_ven = io.BytesIO()
                                with pd.ExcelWriter(output_ven, engine='xlsxwriter') as v_writer:
                                    df_v_all = df_vperf_raw[df_vperf_raw['VendorName'] == vendor].copy()
                                    df_v_all.to_excel(v_writer, sheet_name='Vendor_Raw_Report', index=False)
                                    df_v_sum_all = df_vperf_sum[df_vperf_sum['VendorName'] == vendor].copy()
                                    df_v_sum_all.to_excel(v_writer, sheet_name='Vendor_Summary_Report', index=False)
                                    
                                    v_workbook = v_writer.book
                                    v_format = v_workbook.add_format({'bold': True, 'bg_color': '#1E3A8A', 'font_color': 'white', 'border': 1})
                                    
                                    for s_name, d_frame in [('Vendor_Raw_Report', df_v_all), ('Vendor_Summary_Report', df_v_sum_all)]:
                                        v_worksheet = v_writer.sheets[s_name]
                                        for col_num, value in enumerate(d_frame.columns.values): v_worksheet.write(0, col_num, value, v_format)
                                
                                ven_file_name = f"{vendor}_Performance_Report.xlsx"
                                part = MIMEApplication(output_ven.getvalue(), Name=ven_file_name)
                                part['Content-Disposition'] = f'attachment; filename="{ven_file_name}"'
                                msg_email.attach(part)
                                
                                recipients = [vendor_email]
                                if cc_email_bulk: recipients.append(cc_email_bulk)
                                server.sendmail(sender_email_bulk, recipients, msg_email.as_string())
                                sent_count += 1
                                
                                progress_bar.progress((i + 1) / len(all_late_vendors))
                                status_txt.text(f"Sent {sent_count} emails...")
                                
                            server.quit()
                            status_txt.success(f"✅ Successfully sent {sent_count} emails to vendors in background!")
                        except Exception as e:
                            status_txt.error(f"Failed during bulk send. Error: {str(e)}")

        st.markdown("---")
        st.markdown("### 🎯 Single Vendor Manual Alert (WhatsApp & Mail)")
        sel_vendor_manual = st.selectbox("Select Individual Vendor to Alert:", all_late_vendors)
        
        if sel_vendor_manual:
            vendor_late_trips = df_late[df_late['VendorName'] == sel_vendor_manual].copy()
            vendor_sum_manual = df_vperf_sum[df_vperf_sum['VendorName'] == sel_vendor_manual].copy()
            
            st.markdown(f"**Total Late Trips for {sel_vendor_manual}: {len(vendor_late_trips)}**")
            
            top_trips = vendor_late_trips.head(5) 
            trip_str = ""
            for idx, row in top_trips.iterrows(): trip_str += f"- Route: {row['Route Path']} | Veh: {row['VehicleNo']} | Delay: {row['Delay Hours']}
"
            
            sum_str_manual = ""
            if not vendor_sum_manual.empty:
                sum_str_manual = "
Here is your overall Route-wise performance summary:
"
                for _, s_row in vendor_sum_manual.iterrows():
                    sum_str_manual += f"Route: {s_row['Route Path']} ({s_row['Legs']}) | Total Trips: {s_row['Total_Trips']} | Ontime: {s_row['Ontime Arrival']} | Late: {s_row['Late Arrival']}
"

            msg = f"Dear {sel_vendor_manual},

Please find attached the arrival performance report for your vehicles. The following trips have been consistently reported as late:

{trip_str}{sum_str_manual}
Kindly take necessary actions to ensure on-time arrivals in the future.

Best Regards,
Trackon Command Center"
            
            default_wp = vendor_master_dict.get(sel_vendor_manual.upper(), {}).get('whatsapp', '')
            default_email = vendor_master_dict.get(sel_vendor_manual.upper(), {}).get('email', '')
            
            with st.form("single_comm_form"):
                mc1, mc2 = st.columns(2)
                wp_num = mc1.text_input("Vendor WhatsApp Number (with Country Code):", value=default_wp)
                email_id = mc2.text_input("Vendor Email ID:", value=default_email)
                body_text = st.text_area("Message Body (English):", value=msg, height=300)
                submit_comm = st.form_submit_button("Lock Message Format")

            output_ven = io.BytesIO()
            with pd.ExcelWriter(output_ven, engine='xlsxwriter') as v_writer:
                df_v_all = df_vperf_raw[df_vperf_raw['VendorName'] == sel_vendor_manual].copy()
                df_v_all.to_excel(v_writer, sheet_name='Vendor_Raw_Report', index=False)
                df_v_sum_manual_exp = df_vperf_sum[df_vperf_sum['VendorName'] == sel_vendor_manual].copy()
                df_v_sum_manual_exp.to_excel(v_writer, sheet_name='Vendor_Summary_Report', index=False)
                
                v_workbook = v_writer.book
                v_format = v_workbook.add_format({'bold': True, 'bg_color': '#1E3A8A', 'font_color': 'white', 'border': 1})
                
                for s_name, d_frame in [('Vendor_Raw_Report', df_v_all), ('Vendor_Summary_Report', df_v_sum_manual_exp)]:
                    v_worksheet = v_writer.sheets[s_name]
                    for col_num, value in enumerate(d_frame.columns.values): v_worksheet.write(0, col_num, value, v_format)
                    
            ven_file_name = f"{sel_vendor_manual}_Performance_Report.xlsx"
            
            c1, c2 = st.columns(2)
            c1.download_button("1️⃣ Download Vendor Report (Excel)", data=output_ven.getvalue(), file_name=ven_file_name, mime="application/vnd.ms-excel", use_container_width=True)
            
            encoded_msg = urllib.parse.quote(body_text)
            wp_url = f"https://api.whatsapp.com/send?phone={wp_num}&text={encoded_msg}"
            c2.markdown(f'<a href="{wp_url}" target="_blank"><button style="background-color: #25D366; color: white; padding: 10px 24px; border: none; border-radius: 5px; width: 100%; cursor: pointer;">2️⃣ Send Smart Text via WhatsApp</button></a>', unsafe_allow_html=True)

# -------------------------------------------------------------
# D. PAYMENT DASHBOARD 
# -------------------------------------------------------------
elif choice == "💳 Payment Dashboard":
    st.markdown("<h2>Pending Payments Tracker</h2>", unsafe_allow_html=True)
    if 'Master_Database' in data:
        df_pay = data['Master_Database'].copy()
        
        col1, col2 = st.columns([1, 2])
        all_zones = sorted(df_pay['Zone'].dropna().unique().tolist())
        selected_zone = col1.selectbox("Filter by Zone:", ["ALL"] + all_zones)
        if selected_zone != "ALL": df_pay = df_pay[df_pay['Zone'] == selected_zone]
        search_q = col2.text_input("🔍 Quick Search (Invoice, Vendor, RO...):")
            
        pvt = pd.pivot_table(df_pay, values='Invoice Id', index='RO Name', columns='Department Bucket', aggfunc='count', fill_value=0, margins=True, margins_name='Grand Total')
        cols_order = ["1. USER / DRAFT PENDING", "2. COST CONTROL PENDING", "3. FINANCE PENDING", "4. PAYMENT PENDING", "5. OTHER PENDING", "Grand Total"]
        existing_cols = [c for c in cols_order if c in pvt.columns]
        pvt = pvt.reindex(columns=existing_cols)
        
        styled_pvt = pvt.style
        pay_cols = [c for c in existing_cols if c != 'Grand Total']
        for col in pay_cols:
            def color_payment_columns(val, c=col):
                if pd.isna(val) or val == 0: return ''
                if c == '1. USER / DRAFT PENDING': return 'background-color: rgba(211, 47, 47, 0.3); color: #ff5252; font-weight: bold;' 
                elif c == '2. COST CONTROL PENDING': return 'background-color: rgba(245, 127, 23, 0.3); color: #ffd740; font-weight: bold;'
                elif c == '3. FINANCE PENDING': return 'background-color: rgba(245, 127, 23, 0.1); color: #ffe57f; font-weight: bold;'
                return ''
            if hasattr(styled_pvt, 'map'): styled_pvt = styled_pvt.map(color_payment_columns, subset=[col])
            else: styled_pvt = styled_pvt.applymap(color_payment_columns, subset=[col])

        st.markdown("### RO-Wise Summary")
        pay_selection = st.dataframe(styled_pvt, use_container_width=True, on_select="rerun", selection_mode="single-row")

# -------------------------------------------------------------
# E. CPK & UTILIZATION 
# -------------------------------------------------------------
elif choice == "💰 Network Utilization":
    st.markdown("<h2>Network Utilization & CPK</h2>", unsafe_allow_html=True)
    if 'Up_Down_Route_Summary' in data and 'CPK_Raw_Data' in data:
        df_cpk_master = data['Up_Down_Route_Summary'].copy()
        
        col1, col2, col3 = st.columns([1, 1, 2])
        all_zones = sorted(df_cpk_master['Zone'].dropna().unique().tolist())
        zone_filter = col1.selectbox("Filter Zone:", ["ALL"] + all_zones)
        if zone_filter != "ALL": df_cpk_master = df_cpk_master[df_cpk_master['Zone'] == zone_filter]
            
        all_ros = sorted(df_cpk_master['VendorRO'].dropna().unique().tolist())
        ro_filter = col2.selectbox("Filter RO:", ["ALL"] + all_ros)
        if ro_filter != "ALL": df_cpk_view = df_cpk_master[df_cpk_master['VendorRO'] == ro_filter].copy()
        else: df_cpk_view = df_cpk_master.copy()
            
        search_q = col3.text_input("🔍 Quick Search:", placeholder="Search Route, Vendor...")
        if search_q: df_cpk_view = df_cpk_view[df_cpk_view.astype(str).apply(lambda x: x.str.contains(search_q, case=False, regex=False, na=False)).any(axis=1)]

        m1, m2, m3 = st.columns(3)
        m1.metric("Total Trips", int(df_cpk_view['Total Trips'].sum()))
        avg_util = (df_cpk_view['Total Carried Wt'].sum() / df_cpk_view['Total Capacity'].sum() * 100) if df_cpk_view['Total Capacity'].sum() > 0 else 0
        m2.metric("Overall Utilization", f"{avg_util:.1f}%")
        avg_cpk = (df_cpk_view['Total Trip Cost'].sum() / df_cpk_view['Total Carried Wt'].sum()) if df_cpk_view['Total Carried Wt'].sum() > 0 else 0
        m3.metric("Overall CPK", f"₹ {avg_cpk:.2f}")
        
        st.markdown("### Top Priority Utilization List")
        st.dataframe(df_cpk_view, use_container_width=True, height=300)
