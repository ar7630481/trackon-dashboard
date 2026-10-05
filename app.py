import streamlit as st
import pandas as pd
import numpy as np
import datetime
import urllib.parse
import os
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. PAGE SETUP (Professional Dark Theme)
# ==========================================
st.set_page_config(page_title="Trackon Command Center", page_icon="🚀", layout="wide")

DATA_DIR = "uploaded_raw_data"
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
    "FINAL_OUTPUT": os.path.join(DATA_DIR, "Auto_Generated_Monitoring_Data.xlsx")
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
    if uploaded_file is not None:
        with open(FILE_MAP[key], "wb") as f:
            f.write(uploaded_file.getbuffer())
        return True
    return False

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
# 4. MAIN PROCESSING ENGINE
# ==========================================
def process_all_data():
    progress = st.progress(0)
    status_text = st.empty()
    
    try:
        writer = pd.ExcelWriter(FILE_MAP["FINAL_OUTPUT"], engine='xlsxwriter')
        
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
            
            # Add Zone mapping to Payment Data
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
            df_master.to_excel(writer, sheet_name='Master_Database', index=False)
        else:
            st.warning("⚠️ Payment file missing.")

        progress.progress(20)

        # --- MODULE 1: LEGWISE OPERATIONS ---
        status_text.text("⚙️ Processing Legwise Operations Data...")
        if os.path.exists(FILE_MAP["LEGWISE"]) and os.path.exists(FILE_MAP["ROUTE_MASTER"]) and os.path.exists(FILE_MAP["BRANCH_MASTER"]):
            df_leg = pd.read_excel(FILE_MAP["LEGWISE"], sheet_name="Sheet1")
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

            df_leg.columns = df_leg.columns.str.strip()
            df_leg = df_leg[(df_leg['MCD_Created_By'] == 'SCHEDULED') & (df_leg['LH_Type'].isin(['National LH', 'Zonal LH']))]
            df_leg['MCD_StartDate_DT'] = pd.to_datetime(df_leg['MCD_StartDate'], dayfirst=True, errors='coerce')
            df_leg['Leg_Num'] = df_leg['Legwise'].astype(str).str.extract(r'(\d+)').astype(float).fillna(1)

            df_leg = df_leg.sort_values(by=['RouteCode', 'MCD_StartDate_DT', 'Min_CD_StartDatetime'])
            dedup = df_leg.groupby(['RouteCode', 'MCD_StartDate_DT'])['MasterCDNo'].first().reset_index()
            df_leg = df_leg.merge(dedup, on=['RouteCode', 'MCD_StartDate_DT', 'MasterCDNo'])
            df_leg['Legs'] = df_leg['CD_FromBranch'].astype(str) + " to " + df_leg['CD_ToBranch'].astype(str)
            df_leg.rename(columns={'Min_CD_StartDatetime': 'Actual Departure Time', 'Max_CD_EndDatetime': 'Actual Arrival Time', 'Route': 'Route Path'}, inplace=True)
            
            df_leg['CD_FromBranch_Clean'] = df_leg['CD_FromBranch'].astype(str).str.strip().str.upper()
            df_brn.columns = df_brn.columns.astype(str).str.strip()
            brn_col = next((c for c in df_brn.columns if 'branchcode' in c.lower().replace(' ', '')), 'RPTBranchcode')
            ro_col = next((c for c in df_brn.columns if 'rptro' in c.lower().replace(' ', '')), 'RPTRO')
            zone_col = next((c for c in df_brn.columns if 'zone' in c.lower().replace(' ', '')), 'Zone')

            df_brn['RPTBranchcode_Clean'] = df_brn[brn_col].astype(str).str.strip().str.upper()
            df_brn_clean = df_brn[['RPTBranchcode_Clean', ro_col, zone_col]].drop_duplicates('RPTBranchcode_Clean')
            df_leg = df_leg.merge(df_brn_clean, left_on='CD_FromBranch_Clean', right_on='RPTBranchcode_Clean', how='left')
            df_leg.rename(columns={ro_col: 'Origin RO', zone_col: 'Zone'}, inplace=True)
            df_leg['Origin RO'] = df_leg['Origin RO'].fillna('Missing RO')
            df_leg['Zone'] = df_leg['Zone'].fillna('UNKNOWN ZONE')
            
            df_leg[['Origin', 'Destination']] = df_leg['Route Path'].apply(lambda x: pd.Series(extract_orig_dest(x)))
            df_leg['E2E_Pair'] = df_leg['Route Path'].apply(get_route_pair)
            df_leg.rename(columns={'LH_Type': 'LH Type'}, inplace=True)
            
            df_leg = df_leg.merge(route_tat_master[['Route Code', 'Scheduled TAT Till Destination']], left_on='RouteCode', right_on='Route Code', how='left')
            
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
            df_leg = df_leg.merge(df_rte, left_on=['RouteCode', 'CD_FromBranch'], right_on=['Route Code', 'Route Branch Code'], how='left')
            df_leg.rename(columns={'Route Day': 'Dep_Route_Day', 'Schedule Departure Time': 'Sch_Dep_Time_Raw'}, inplace=True)
            df_leg.drop(columns=['Schedule Arrival Time'], inplace=True, errors='ignore')
            
            df_leg = df_leg.merge(df_rte[['Route Code', 'Route Branch Code', 'Route Day', 'Schedule Arrival Time']], left_on=['RouteCode', 'CD_ToBranch'], right_on=['Route Code', 'Route Branch Code'], how='left')
            df_leg.rename(columns={'Route Day': 'Arr_Route_Day', 'Schedule Arrival Time': 'Sch_Arr_Time_Raw'}, inplace=True)

            df_leg['Scheduled Departure Time'] = df_leg.apply(lambda r: get_sch_time(r, 'Dep_Route_Day', 'Sch_Dep_Time_Raw'), axis=1)
            df_leg['Scheduled Arrival Time'] = df_leg.apply(lambda r: get_sch_time(r, 'Arr_Route_Day', 'Sch_Arr_Time_Raw'), axis=1)
            df_leg['Actual Departure Time'] = pd.to_datetime(df_leg['Actual Departure Time'], dayfirst=True, errors='coerce')
            df_leg['Actual Arrival Time'] = pd.to_datetime(df_leg['Actual Arrival Time'], dayfirst=True, errors='coerce')
            
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

            exec_sum = df_leg.groupby(['Zone', 'LH Type', 'E2E_Pair', 'Origin RO', 'Route Path', 'Leg_Num', 'Legwise', 'Legs']).agg(
                Trips=('MasterCDNo', 'count'), LDep=('Late Dep', 'sum'), LArr=('Late Arr', 'sum'), Miss=('Missing', 'sum')
            ).reset_index()

            def set_stat(r):
                if r['LDep'] > 0 and r['LArr'] > 0: return "Critical: Late Dep & Arr"
                elif r['LDep'] > 0: return "Critical: Late Departure"
                elif r['LArr'] > 0: return "Warning: Late Arrival"
                elif r['Miss'] > 0: return "Alert: Missing Data / No Dep"
                return "OK"
                
            exec_sum['Status'] = exec_sum.apply(set_stat, axis=1)
            exec_notes = exec_sum[exec_sum['Status'] != "OK"].copy()

            def mk_note(r):
                msg = f"Total {r['Trips']} trips. "
                if r['LDep']>0: msg += f"{r['LDep']} Late Dep. "
                if r['LArr']>0: msg += f"{r['LArr']} Late Arr. "
                if r['Miss']>0: msg += f"{r['Miss']} Missing/No Dep."
                return msg.strip()
                
            exec_notes['Actionable Note'] = exec_notes.apply(mk_note, axis=1)
            exec_notes.sort_values(by=['LH Type', 'E2E_Pair', 'Route Path', 'Leg_Num'], inplace=True)
            exec_notes.to_excel(writer, sheet_name='Actionable_Notes', index=False)
            
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
            leg_sum.to_excel(writer, sheet_name='Legwise_Route_Summary', index=False)
            
            dt_cols = ['Scheduled Departure Time', 'Actual Departure Time', 'Scheduled Arrival Time', 'Actual Arrival Time']
            for c in dt_cols: df_leg[c] = df_leg[c].dt.strftime('%d-%m-%Y %H:%M').fillna('')
            df_leg['MCD_StartDate'] = pd.to_datetime(df_leg['MCD_StartDate_DT']).dt.strftime('%d-%m-%Y')
            df_leg_final = df_leg.drop(columns=['Leg_Num', 'E2E_Pair'], errors='ignore')
            df_leg_final.to_excel(writer, sheet_name='Legwise_Processed_Data', index=False)

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
            
            df_updn = df_raw[~df_raw['Final_Type'].str.upper().str.contains('OFD|PICKUP', na=False)]
            target_keys = df_updn[df_updn['RO_Clean'].isin(target_ros)]['SortKey'].unique()
            df_updn = df_updn[df_updn['SortKey'].isin(target_keys)]
            
            df_updn.to_excel(writer, sheet_name='CPK_Raw_Data', index=False)

            if not df_updn.empty:
                # Calculate Rate per trip to ensure grouping separates differing rates
                df_updn['Trip_Rate'] = np.where(df_updn['Trips'] > 0, df_updn['Cost'] / df_updn['Trips'], 0).round(2)
                
                # Modified Groupby to group Vendors with same capacity AND same Rate
                agg_updn = df_updn.groupby(['RO_Clean', 'Zone', 'Final_Route', 'Final_Type', 'Cap', 'SortKey', 'Trip_Rate']).agg(
                    Total_Trips=('Trips', 'sum'),
                    Total_Carried_Wt=('Wt', 'sum'),
                    Total_Trip_Cost=('Cost', 'sum'),
                    VendorName=('VendorName', lambda x: ', '.join(sorted(set(x.dropna().astype(str)))))
                ).reset_index()

                agg_updn['Total Capacity'] = agg_updn['Cap'] * agg_updn['Total_Trips']
                agg_updn['Overall CPK'] = np.where(agg_updn['Total_Carried_Wt'] > 0, agg_updn['Total_Trip_Cost'] / agg_updn['Total_Carried_Wt'], 0)
                agg_updn['Overall Util %'] = np.where(agg_updn['Total Capacity'] > 0, agg_updn['Total_Carried_Wt'] / agg_updn['Total Capacity'], 0)
                agg_updn['Avg Trip Cost'] = np.where(agg_updn['Total_Trips'] > 0, agg_updn['Total_Trip_Cost'] / agg_updn['Total_Trips'], 0)
                
                updn_final = agg_updn[['Zone', 'RO_Clean', 'Final_Route', 'Final_Type', 'Overall CPK', 'Overall Util %', 'Cap', 'Total Capacity', 'Total_Carried_Wt', 'Avg Trip Cost', 'Total_Trip_Cost', 'Total_Trips', 'VendorName', 'SortKey']]
                updn_final.columns = ["Zone", "VendorRO", "Route (UP/DOWN)", "Type", "Overall CPK", "Overall Util %", "VehCap (Base)", "Total Capacity", "Total Carried Wt", "Avg Trip Cost", "Total Trip Cost", "Total Trips", "Vendor(s)", "SortKey"]

                type_order = {"MCD-National LH":1, "MCD-Zonal LH":2, "MCD-Regional LH":3, "MCD-Feeder":4, "CO-LOADER":5}
                updn_final['TypeSort'] = updn_final['Type'].map(lambda x: type_order.get(x, 99))
                updn_final = updn_final.sort_values(by=['TypeSort', 'SortKey', 'Route (UP/DOWN)'], ascending=[True, True, True]).drop(columns=['TypeSort'])

                updn_final.to_excel(writer, sheet_name='Up_Down_Route_Summary', index=False)

        else:
            st.warning("⚠️ CPK files missing. Skipping CPK module.")
            
        progress.progress(90)
        status_text.text("⚙️ Finalizing Dashboard Data...")
        writer.close()
        progress.progress(100)
        status_text.success("✅ Data Processed Successfully!")
        
        st.cache_data.clear()
    
    except Exception as e:
        status_text.error(f"❌ Error during processing: {e}")

# ==========================================
# 5. SIDEBAR: ADMIN PANEL
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

    st.sidebar.markdown("---")
    if st.sidebar.button("🚀 PROCESS & REFRESH DATA", use_container_width=True):
        process_all_data()
        st.rerun()
    
if os.path.exists(FILE_MAP["FINAL_OUTPUT"]):
    ts = os.path.getmtime(FILE_MAP["FINAL_OUTPUT"])
    dt = (datetime.datetime.fromtimestamp(ts) + datetime.timedelta(hours=5, minutes=30)).strftime('%d %b %Y, %I:%M %p')
    st.sidebar.info(f"📊 Dashboard Refreshed:\n{dt} (IST)")

# ==========================================
# 6. DATA LOADING & UI ROUTING
# ==========================================
@st.cache_data
def load_dashboard_data():
    if not os.path.exists(FILE_MAP["FINAL_OUTPUT"]): return {}
    xls = pd.ExcelFile(FILE_MAP["FINAL_OUTPUT"])
    data = {}
    for sheet in xls.sheet_names:
        data[sheet] = pd.read_excel(xls, sheet_name=sheet)
    return data

data = load_dashboard_data()

if not data:
    st.warning("⚠ No data found! Admin must upload raw files and process data.")
    st.stop()
    
menu = ["📊 Operations Summary", "💳 Payment Dashboard", "📱 Communications", "💰 Network Utilization"]
choice = st.sidebar.radio("Navigation:", menu)

# -------------------------------------------------------------
# A. DAILY STANDUP (Operations Summary)
# -------------------------------------------------------------
if choice == "📊 Operations Summary":
    st.markdown("<h2>Operations Exception Summary</h2>", unsafe_allow_html=True)
    
    if 'Legwise_Route_Summary' in data and 'Legwise_Processed_Data' in data:
        df_leg_sum = data['Legwise_Route_Summary'].copy()
        df_raw_leg = data['Legwise_Processed_Data'].copy()
        
        col1, col2, col3 = st.columns([1, 1, 2])
        
        # Zone Filter
        all_zones = sorted(df_leg_sum['Zone'].dropna().unique().tolist())
        selected_zone = col1.selectbox("Filter by Zone:", ["ALL"] + all_zones)
        
        if selected_zone != "ALL":
            df_leg_sum = df_leg_sum[df_leg_sum['Zone'] == selected_zone]
            df_raw_leg = df_raw_leg[df_raw_leg['Zone'] == selected_zone]
            
        # RO Filter
        all_ros = sorted(df_leg_sum['Origin RO'].dropna().unique().tolist())
        selected_ro = col2.selectbox("Filter by RO:", ["ALL"] + all_ros)
        
        if selected_ro != "ALL":
            df_leg_sum = df_leg_sum[df_leg_sum['Origin RO'] == selected_ro]
            df_raw_leg = df_raw_leg[df_raw_leg['Origin RO'] == selected_ro]

        search_q = col3.text_input("🔍 Quick Search:", placeholder="Search Route, Leg...")

        display_cols = ['Route Path', 'Legwise', 'Legs', 'Total_Trips', 
                        'Ontime Dep, Ontime Arr %', 'Ontime Dep, Late Arr %', 
                        'Late Dep, Late Arr %', 'Late Dep, Ontime Arr %']
        
        display_cols = [c for c in display_cols if c in df_leg_sum.columns]
        df_display = df_leg_sum[display_cols].copy()
        
        if search_q:
            mask = df_display.astype(str).apply(lambda x: x.str.contains(search_q, case=False)).any(axis=1)
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

    else:
        st.error("Operations Data missing.")

# -------------------------------------------------------------
# B. VENDOR PAYMENT DASHBOARD 
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
                mask = filtered_pay.astype(str).apply(lambda x: x.str.contains(search_q, case=False)).any(axis=1)
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
# C. WHATSAPP ALERTS (Communications)
# -------------------------------------------------------------
elif choice == "📱 Communications":
    st.markdown("<h2>Actionable Communications</h2>", unsafe_allow_html=True)
    
    if 'Actionable_Notes' in data:
        df_notes = data['Actionable_Notes']
        all_ros = sorted(df_notes['Origin RO'].dropna().unique().tolist())
        sel_ro = st.selectbox("Select RO for Alert Generation:", all_ros)
        
        ro_notes = df_notes[(df_notes['Origin RO'] == sel_ro) & (df_notes['Status'].str.contains("Critical", na=False, case=False))]
        
        if len(ro_notes) > 0:
            msg = f"*🔴 TRACKON DAILY ALERT: {sel_ro}*\nDate: {datetime.datetime.now().strftime('%d %b %Y')}\n\nFollowing Scheduled Routes are showing Critical Delays:\n\n"
            for idx, row in ro_notes.iterrows():
                msg += f"🛣️ *Route:* {row['Route Path']} ({row['Legs']})\n⚠️ *Issue:* {row['Actionable Note']}\n\n"
            msg += "Regards,\n*Central Control Tower*"
            
            st.text_area("Preview Message:", value=msg, height=250)
            encoded_msg = urllib.parse.quote(msg)
            whatsapp_url = f"https://api.whatsapp.com/send?text={encoded_msg}"
            
            st.markdown(f"""
            <a href="{whatsapp_url}" target="_blank">
                <button style="background-color: #25D366; color: white; padding: 10px 24px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold;">
                    💬 Send via WhatsApp Web
                </button>
            </a>
            """, unsafe_allow_html=True)
        else:
            st.success(f"🎉 No critical delays for {sel_ro} today!")
    else:
        st.info("No data available.")

# -------------------------------------------------------------
# D. CPK & UTILIZATION 
# -------------------------------------------------------------
elif choice == "💰 Network Utilization":
    st.markdown("<h2>Network Utilization & CPK</h2>", unsafe_allow_html=True)
    if 'Up_Down_Route_Summary' in data and 'CPK_Raw_Data' in data:
        df_cpk_master = data['Up_Down_Route_Summary'].copy()
        df_cpk_raw = data['CPK_Raw_Data'].copy()
        
        df_cpk_master = df_cpk_master[df_cpk_master['Type'].isin(['MCD-National LH', 'MCD-Zonal LH', 'National LH', 'Zonal LH'])]
        df_cpk_master['Type'] = df_cpk_master['Type'].replace({'MCD-National LH': 'National', 'MCD-Zonal LH': 'Zonal', 'National LH': 'National', 'Zonal LH': 'Zonal'})
        
        def create_super_key(route):
            parts = str(route).split('-')
            if len(parts) >= 2:
                start = parts[0].strip().upper()
                end = parts[-1].strip().upper()
                return "-".join(sorted([start, end]))
            return str(route).upper()
            
        df_cpk_master['Super_SortKey'] = df_cpk_master['Route (UP/DOWN)'].apply(create_super_key)

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
            mask = df_cpk_view.astype(str).apply(lambda x: x.str.contains(search_q, case=False)).any(axis=1)
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
            if 'Avg Trip Cost' in df.columns: tot_dict['Avg Trip Cost'] = tot_avg_cost
            
            return pd.concat([df, pd.DataFrame([tot_dict])], ignore_index=True)

        disp_df = add_total_row(disp_df)
        
        for col in ['Overall CPK', 'Avg Trip Cost', 'Total Trip Cost']: 
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
                selected_super_sortkey = df_cpk_view.iloc[selected_idx]['Super_SortKey']
                selected_route_name = df_cpk_view.iloc[selected_idx]['Route (UP/DOWN)']
                selected_vendor = df_cpk_view.iloc[selected_idx]['Vendor(s)']
                selected_ro_val = df_cpk_view.iloc[selected_idx]['VendorRO']
                
                st.markdown("---")
                st.markdown(f"### 🔗 Network Connected View (UP & DOWN)")
                
                network_df = df_cpk_master[df_cpk_master['Super_SortKey'] == selected_super_sortkey].copy()
                network_df = network_df.drop(columns=['SortKey', 'Super_SortKey'], errors='ignore')
                
                network_df = add_total_row(network_df)
                
                for col in ['Overall CPK', 'Avg Trip Cost', 'Total Trip Cost']: 
                    if col in network_df.columns: network_df[col] = network_df[col].apply(lambda x: f"₹{x:.2f}" if isinstance(x, (int, float)) else x)
                if 'Overall Util %' in network_df.columns:
                    network_df['Overall Util %'] = network_df['Overall Util %'].apply(lambda x: f"{x * 100:.2f}%" if isinstance(x, (int, float)) else x)
                
                styled_network = network_df.style
                if hasattr(styled_network, 'map'):
                    styled_network = styled_network.map(lambda x: highlight_cpk_util(x, 'Overall Util %'), subset=['Overall Util %'])
                    styled_network = styled_network.map(lambda x: highlight_cpk_util(x, 'Overall CPK'), subset=['Overall CPK'])
                else:
                    styled_network = styled_network.applymap(lambda x: highlight_cpk_util(x, 'Overall Util %'), subset=['Overall Util %'])
                    styled_network = styled_network.applymap(lambda x: highlight_cpk_util(x, 'Overall CPK'), subset=['Overall CPK'])

                st.dataframe(styled_network, use_container_width=True)
                
                st.markdown("---")
                st.markdown(f"### 📄 Details for `{selected_vendor}` on `{selected_route_name}`")
                
                vendors_list = [v.strip().upper() for v in str(selected_vendor).split(',')]
                
                raw_trips = df_cpk_raw[
                    (df_cpk_raw['Final_Route'].astype(str).str.strip().str.upper() == str(selected_route_name).strip().upper()) & 
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
            st.info("👆 Click any row above to view full UP/DOWN network details.")
    else:
        st.info("Please process CPK data first.")
