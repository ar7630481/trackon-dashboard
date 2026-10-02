import streamlit as st
import pandas as pd
import numpy as np
import datetime
import urllib.parse
import os
import plotly.express as px
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. PAGE SETUP & DIRECTORY
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
    st.markdown("<h1 style='text-align: center; color: #2E4053;'>🚀 Trackon Master Command Center</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center;'>Secure Login Portal</h3>", unsafe_allow_html=True)
    
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
# 4. THE CORE PROCESSING ENGINE
# ==========================================
def process_all_data():
    progress = st.progress(0)
    status_text = st.empty()
    
    try:
        writer = pd.ExcelWriter(FILE_MAP["FINAL_OUTPUT"], engine='xlsxwriter')
        
        # --- MODULE 1: LEGWISE OPERATIONS & SUMMARIES ---
        status_text.text("⚙️ Step 1/3: Processing Legwise Operations Data...")
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
            df_leg.rename(columns={ro_col: 'Origin RO', zone_col: 'Region'}, inplace=True)
            df_leg['Origin RO'] = df_leg['Origin RO'].fillna('Missing RO')
            df_leg['Region'] = df_leg['Region'].fillna('Missing Zone')
            
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

            exec_sum = df_leg.groupby(['Region', 'LH Type', 'E2E_Pair', 'Origin RO', 'Route Path', 'Leg_Num', 'Legwise', 'Legs']).agg(
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
                
                def get_insight(row):
                    total = row[trip_col]
                    if total == 0: return "No Data"
                    oo_pct = row['OO_Cnt']/total
                    ll_pct = row['LL_Cnt']/total
                    ol_pct = row['OL_Cnt']/total
                    lo_pct = row['LO_Cnt']/total
                    arr_total = row['OO_Cnt'] + row['LO_Cnt'] + row['OL_Cnt'] + row['LL_Cnt']
                    if arr_total == 0: return "Currently Running / In-Transit"
                    if oo_pct >= 0.80: return "Smooth Operations - Excellent TAT"
                    elif ll_pct >= 0.40: return "Critical Lag - Fails at Route & Origin"
                    elif ol_pct >= 0.30: return "Transit Delay - Route Lag"
                    elif lo_pct >= 0.30: return "Origin Delay - Covered in Transit"
                    elif (ol_pct + ll_pct) >= 0.50: return "High Arrival Failures"
                    else: return "Mixed Performance - Monitor"
                    
                summary['Operations Insight'] = summary.apply(get_insight, axis=1)
                
                # Keep scheduled times
                summary['Scheduled Dep (HH:MM)'] = summary['Sch_Dep_Time_Raw'].apply(lambda x: pd.to_datetime(x).strftime('%H:%M') if pd.notnull(x) else '')
                summary['Scheduled Arr (HH:MM)'] = summary['Sch_Arr_Time_Raw'].apply(lambda x: pd.to_datetime(x).strftime('%H:%M') if pd.notnull(x) else '')
                
                final_cols = ['Region', 'Origin RO', 'Route Path', 'Legwise', 'Legs', trip_col, 'Ontime Dep, Ontime Arr %', 'Ontime Dep, Late Arr %', 'Late Dep, Late Arr %', 'Late Dep, Ontime Arr %', 'Ontime Dep, In-Transit', 'Late Dep, In-Transit', 'LH Type', 'Origin', 'Destination', 'Scheduled Dep (HH:MM)', 'Given Driving Hours', 'Scheduled Arr (HH:MM)', 'Operations Insight']
                return summary.sort_values(by=['LH Type', 'E2E_Pair', 'Origin', 'Route Path', 'Leg_Num'])[final_cols]
                
            leg_sum = generate_summary(df_leg, ['Region', 'LH Type', 'E2E_Pair', 'Origin RO', 'Route Path', 'Origin', 'Destination', 'Leg_Num', 'Legwise', 'Legs', 'Sch_Dep_Time_Raw', 'Sch_Arr_Time_Raw', 'Given Driving Hours'])
            leg_sum.to_excel(writer, sheet_name='Legwise_Route_Summary', index=False)
            
            # Legwise Processed Data
            dt_cols = ['Scheduled Departure Time', 'Actual Departure Time', 'Scheduled Arrival Time', 'Actual Arrival Time']
            for c in dt_cols: df_leg[c] = df_leg[c].dt.strftime('%d-%m-%Y %H:%M').fillna('')
            df_leg['MCD_StartDate'] = pd.to_datetime(df_leg['MCD_StartDate_DT']).dt.strftime('%d-%m-%Y')
            df_leg_final = df_leg.drop(columns=['Leg_Num', 'E2E_Pair'], errors='ignore')
            df_leg_final.to_excel(writer, sheet_name='Legwise_Processed_Data', index=False)

        else:
            st.warning("⚠️ Operations files missing. Skipping Operations module.")

        progress.progress(40)
        
        # --- MODULE 2: CPK AND UTILIZATION WITH STRICT VLOOKUP & MATH ---
        status_text.text("⚙️ Step 2/3: Calculating CPK & Utilization...")
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

            # VLOOKUP by RefNumber -> MasterCDNo
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

            # Math Conversion
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

            # SortKey Logic for grouping A-B and B-A together
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
            target_ros = ['PATRO', 'CCURO', 'BBSRO', 'GAURO', 'MUMRO', 'DELRO', 'LKORO']
            
            # --- UP/DOWN SUMMARY ---
            df_updn = df_raw[~df_raw['Final_Type'].str.upper().str.contains('OFD|PICKUP', na=False)]
            target_keys = df_updn[df_updn['RO_Clean'].isin(target_ros)]['SortKey'].unique()
            df_updn = df_updn[df_updn['SortKey'].isin(target_keys)]

            if not df_updn.empty:
                agg_updn = df_updn.groupby(['RO_Clean', 'Final_Route', 'Final_Type', 'Cap', 'SortKey']).agg(
                    Total_Trips=('Trips', 'sum'),
                    Total_Carried_Wt=('Wt', 'sum'),
                    Total_Trip_Cost=('Cost', 'sum'),
                    Vendors=('VendorName', lambda x: ', '.join(sorted(set([str(v) for v in x if pd.notna(v) and str(v).strip() != '']))))
                ).reset_index()

                agg_updn['Total Capacity'] = agg_updn['Cap'] * agg_updn['Total_Trips']
                agg_updn['Overall CPK'] = np.where(agg_updn['Total_Carried_Wt'] > 0, agg_updn['Total_Trip_Cost'] / agg_updn['Total_Carried_Wt'], 0)
                agg_updn['Overall Util %'] = np.where(agg_updn['Total Capacity'] > 0, agg_updn['Total_Carried_Wt'] / agg_updn['Total Capacity'], 0)
                
                updn_final = agg_updn[['RO_Clean', 'Final_Route', 'Final_Type', 'Overall CPK', 'Overall Util %', 'Cap', 'Total Capacity', 'Total_Carried_Wt', 'Total_Trip_Cost', 'Total_Trips', 'Vendors', 'SortKey']]
                updn_final.columns = ["VendorRO", "Route (UP/DOWN)", "Type", "Overall CPK", "Overall Util %", "VehCap (Base)", "Total Capacity", "Total Carried Wt", "Total Trip Cost", "Total Trips", "Vendor(s)", "SortKey"]

                type_order = {"MCD-National LH":1, "MCD-Zonal LH":2, "MCD-Regional LH":3, "MCD-Feeder":4, "CO-LOADER":5}
                updn_final['TypeSort'] = updn_final['Type'].map(lambda x: type_order.get(x, 99))
                updn_final = updn_final.sort_values(by=['TypeSort', 'SortKey', 'Route (UP/DOWN)'], ascending=[True, True, True]).drop(columns=['TypeSort', 'SortKey'])

                updn_final.to_excel(writer, sheet_name='Up_Down_Route_Summary', index=False)

            # --- FEEDER USAGE ---
            df_fdr = df_raw[df_raw['Final_Type'].str.upper().str.contains('FEEDER|OFD|PICKUP', na=False)]
            df_fdr = df_fdr[df_fdr['RO_Clean'].isin(target_ros)]
            if not df_fdr.empty:
                c_type_col = get_col(df_raw, ['contracttype', 'contracttypedesc']) or 'ContractType'
                df_fdr['ContractType'] = df_fdr.get(c_type_col, pd.Series(['Unlisted']*len(df_fdr))).fillna('Unlisted').astype(str).str.upper()
                vno_col = get_col(df_raw, ['vehicleno', 'vehicle']) or 'VehicleNo'
                df_fdr['VehicleNo'] = df_fdr.get(vno_col, pd.Series(['Unlisted']*len(df_fdr))).fillna('Unlisted')
                
                agg_fdr = df_fdr.groupby(['RO_Clean', 'VehicleNo', 'Cap', 'ContractType']).agg(
                    Final_Type=('Final_Type', lambda x: ', '.join(set([str(v) for v in x if pd.notna(v)]))),
                    Total_Trips=('Trips', 'sum'),
                    Total_Carried_Wt=('Wt', 'sum'),
                    Total_Trip_Cost=('Cost', 'sum'),
                    Vendors=('VendorName', lambda x: ', '.join(sorted(set([str(v) for v in x if pd.notna(v) and str(v).strip() != '']))))
                ).reset_index()

                agg_fdr['Total Capacity'] = agg_fdr['Cap'] * agg_fdr['Total_Trips']
                agg_fdr['Overall CPK'] = np.where(agg_fdr['Total_Carried_Wt'] > 0, agg_fdr['Total_Trip_Cost'] / agg_fdr['Total_Carried_Wt'], 0)
                agg_fdr['Overall Util %'] = np.where(agg_fdr['Total Capacity'] > 0, agg_fdr['Total_Carried_Wt'] / agg_fdr['Total Capacity'], 0)

                fdr_final = agg_fdr[['RO_Clean', 'VehicleNo', 'Final_Type', 'ContractType', 'Overall CPK', 'Overall Util %', 'Cap', 'Total Capacity', 'Total_Carried_Wt', 'Total_Trip_Cost', 'Total_Trips', 'Vendors']]
                fdr_final.columns = ["VendorRO", "Vehicle No", "Type", "Contract Type", "Overall CPK", "Overall Util %", "VehCap (Base)", "Total Capacity", "Total Carried Wt", "Total Trip Cost", "Total Trips", "Vendor Name(s)"]
                fdr_final = fdr_final.sort_values(by=['VendorRO', 'Overall Util %', 'Overall CPK'], ascending=[True, False, False])
                fdr_final.to_excel(writer, sheet_name='Overall_Feeder_Usage', index=False)

            # --- MASTER DATABASE RAW ---
            if 'Master_Database' not in [s.sheet_name for s in writer.sheets.values()]:
                df_raw.to_excel(writer, sheet_name='Master_Database', index=False)

        else:
            st.warning("⚠️ CPK files missing. Skipping CPK & Util module.")
            
        progress.progress(90)
        status_text.text("⚙️ Step 3/3: Finalizing Dashboard Data...")
        writer.close()
        progress.progress(100)
        status_text.success("✅ Master Data Generated Successfully!")
        
        st.cache_data.clear()
    
    except Exception as e:
        status_text.error(f"❌ Error during processing: {e}")

# ==========================================
# 5. SIDEBAR: ADMIN UPLOAD PANEL
# ==========================================
st.sidebar.title(f"Welcome, {st.session_state['role']}")
if st.sidebar.button("Logout", key="logout_btn"):
    st.session_state['logged_in'] = False
    st.session_state['role'] = None
    st.rerun()

st.sidebar.markdown("---")

if st.session_state['role'] == 'Admin':
    st.sidebar.header("🛠️️ Admin Data Management")
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
    dt = datetime.datetime.fromtimestamp(ts).strftime('%d %b %Y, %I:%M %p')
    st.sidebar.info(f"📊 Dashboard Last Refreshed:\n{dt}")
else:
    st.sidebar.warning("⚠️ No dashboard data available. Admin must upload files and hit Process.")

# ==========================================
# 6. DATA LOADING FOR DASHBOARD VIEWS
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

# ==========================================
# 7. DASHBOARD NAVIGATION & UI
# ==========================================
menu = ["📊 Daily Standup (1-Hour Call)", "📱 WhatsApp Automator", "💰 CPK & Utilization Analysis", "📁 One-Click Raw Data Vault"]
choice = st.sidebar.radio("Navigate to:", menu)

# -------------------------------------------------------------
# A. DAILY STANDUP (VISUAL HEATMAP ENGINE)
# -------------------------------------------------------------
if choice == "📊 Daily Standup (1-Hour Call)":
    st.title("🚨 Exception Reporting (Manager's Visual Heatmap)")
    
    if 'Legwise_Route_Summary' in data:
        df_leg_sum = data['Legwise_Route_Summary'].copy()
        
        all_ros = sorted(df_leg_sum['Origin RO'].dropna().unique().tolist())
        selected_ro = st.selectbox("Select Regional Office (RO) to Address:", ["PAN INDIA"] + all_ros)
        
        if selected_ro != "PAN INDIA":
            df_leg_sum = df_leg_sum[df_leg_sum['Origin RO'] == selected_ro]

        # Hide unnecessary column
        if 'Operations Insight' in df_leg_sum.columns:
            df_leg_sum = df_leg_sum.drop(columns=['Operations Insight'])
            
        # Extract percentage to dynamically sort worst routes to the top
        def extract_pct(x):
            if isinstance(x, str) and '%' in x:
                try: return float(x.split('%')[0].strip())
                except: return 0.0
            return 0.0
            
        df_leg_sum['SortKey'] = df_leg_sum['Late Dep, Late Arr %'].apply(extract_pct)
        df_leg_sum = df_leg_sum.sort_values(by='SortKey', ascending=False).drop(columns=['SortKey'])

        # Smart Data Parsing (Convert '12.5% (1)' to '12.5% | 🚚 1')
        def format_val(x):
            if isinstance(x, str) and '%' in x and '(' in x:
                try:
                    pct = x.split('%')[0] + '%'
                    count = x.split('(')[1].replace(')', '')
                    if count == '0': return "0%"
                    return f"{pct} | 🚚 {count}"
                except: return x
            return x
            
        pct_cols = [c for c in df_leg_sum.columns if '%' in c]
        for c in pct_cols:
            df_leg_sum[c] = df_leg_sum[c].apply(format_val)

        # Dynamic Color Heatmap Function
        def highlight_cells(val, col):
            if not isinstance(val, str) or '%' not in val: return ''
            try: pct = float(val.split('%')[0].strip())
            except: return ''
            
            # Fade out 0% values
            if pct == 0: return 'color: #B0BEC5;' 
            
            # Apply exact color codes based on metric
            if 'Late Dep, Late Arr' in col:
                return 'background-color: #ffebee; color: #d32f2f; font-weight: bold;'
            elif 'Ontime Dep, Ontime Arr' in col:
                return 'background-color: #e8f5e9; color: #388e3c; font-weight: bold;'
            elif 'Ontime Dep, Late Arr' in col:
                return 'background-color: #fff8e1; color: #f57f17; font-weight: bold;'
            elif 'Late Dep, Ontime Arr' in col:
                return 'background-color: #f3e5f5; color: #7b1fa2; font-weight: bold;' # Purple (Questionable)
            return ''

        # Apply Pandas Styler with compatibility for all versions
        styled_df = df_leg_sum.style
        for col in pct_cols:
            if hasattr(styled_df, 'map'):
                styled_df = styled_df.map(lambda x, c=col: highlight_cells(x, c), subset=[col])
            else:
                styled_df = styled_df.applymap(lambda x, c=col: highlight_cells(x, c), subset=[col])

        st.markdown("### 🔥 Top Priority Routes (Sorted by Worst 'Late Dep, Late Arr')")
        st.dataframe(styled_df, use_container_width=True, height=600)
    else:
        st.info("Please upload raw files and click 'PROCESS & REFRESH DATA' in the Admin Panel.")

# -------------------------------------------------------------
# B. WHATSAPP AUTOMATOR
# -------------------------------------------------------------
elif choice == "📱 WhatsApp Automator":
    st.title("📱 WhatsApp Automator")
    st.markdown("Select an RO to generate a pre-formatted WhatsApp report for the Vendor Group.")
    
    ro_group_map = {
        "DELRO": "Delhi Vendors Official 🚛",
        "MUMRO": "Mumbai Operations Sync 🚚",
        "CCURO": "Kolkata Master Group 📦",
        "PATRO": "Patna Route Alerts 🚨",
        "AMDRO": "Ahmedabad Logistics 🚛",
    }
    
    if 'Actionable_Notes' in data:
        df_notes = data['Actionable_Notes']
        all_ros = sorted(df_notes['Origin RO'].dropna().unique().tolist())
        sel_ro = st.selectbox("Select RO:", all_ros)
        
        group_name = ro_group_map.get(sel_ro, f"{sel_ro} Operations Group")
        st.info(f"📲 Mapped WhatsApp Group: **{group_name}**")
        
        ro_notes = df_notes[(df_notes['Origin RO'] == sel_ro) & (df_notes['Status'].str.contains("Critical", na=False, case=False))]
        
        if len(ro_notes) > 0:
            msg = f"*🔴 TRACKON DAILY ALERT: {sel_ro}*\n"
            msg += f"Date: {datetime.datetime.now().strftime('%d %b %Y')}\n\n"
            msg += "Following Scheduled Routes are showing Critical Delays. Please address immediately:\n\n"
            
            for idx, row in ro_notes.iterrows():
                msg += f"🛣️ *Route:* {row['Route Path']} ({row['Legs']})\n"
                msg += f"⚠️ *Issue:* {row['Actionable Note']}\n\n"
            msg += "Regards,\n*Central Control Tower*"
            
            st.text_area("Preview WhatsApp Message:", value=msg, height=300)
            
            encoded_msg = urllib.parse.quote(msg)
            whatsapp_url = f"https://api.whatsapp.com/send?text={encoded_msg}"
            
            st.markdown(f"""
            <a href="{whatsapp_url}" target="_blank">
                <button style="background-color: #25D366; color: white; padding: 10px 24px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold;">
                    💬 Send to WhatsApp Web/App
                </button>
            </a>
            """, unsafe_allow_html=True)
        else:
            st.success(f"🎉 No critical delays for {sel_ro} today!")
    else:
        st.info("No data available to generate messages.")

# -------------------------------------------------------------
# C. CPK & UTILIZATION ANALYSIS
# -------------------------------------------------------------
elif choice == "💰 CPK & Utilization Analysis":
    st.title("💰 CPK & Utilization Analysis")
    if 'Up_Down_Route_Summary' in data:
        df_cpk = data['Up_Down_Route_Summary']
        ro_filter = st.selectbox("Filter RO (CPK):", ["ALL"] + sorted(df_cpk['VendorRO'].dropna().unique().tolist()))
        if ro_filter != "ALL":
            df_cpk = df_cpk[df_cpk['VendorRO'] == ro_filter]
            
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Trips", int(df_cpk['Total Trips'].sum()))
        avg_util = (df_cpk['Total Carried Wt'].sum() / df_cpk['Total Capacity'].sum() * 100) if df_cpk['Total Capacity'].sum() > 0 else 0
        c2.metric("Overall Utilization", f"{avg_util:.1f}%")
        avg_cpk = (df_cpk['Total Trip Cost'].sum() / df_cpk['Total Carried Wt'].sum()) if df_cpk['Total Carried Wt'].sum() > 0 else 0
        c3.metric("Overall CPK", f"₹ {avg_cpk:.2f}")
        
        st.markdown("### Top 10 Worst Utilized Routes (< 50%)")
        bad_util = df_cpk[df_cpk['Overall Util %'] < 0.50].sort_values(by='Overall Util %').head(10)
        
        if not bad_util.empty:
            bad_util['Util %'] = bad_util['Overall Util %'] * 100
            fig = px.bar(bad_util, x='Route (UP/DOWN)', y='Util %', color='VendorRO', text_auto='.1f', 
                         title="Routes Bleeding Money (Check Capacity Match)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.success("All routes are > 50% Utilized!")
            
        st.dataframe(df_cpk.style.format({'Overall CPK': '{:.2f}', 'Overall Util %': '{:.2%}'}), use_container_width=True)
    else:
        st.info("Please process CPK data first from the Admin panel.")

# -------------------------------------------------------------
# D. ONE-CLICK RAW DATA VAULT
# -------------------------------------------------------------
elif choice == "📁 One-Click Raw Data Vault":
    st.title("📁 One-Click Raw Data Vault")
    st.markdown("Instantly access and inspect all underlying master data tables generated by the engine.")
    
    if data:
        sheet_names = list(data.keys())
        selected_sheet = st.selectbox("Select Table to View:", sheet_names)
        
        st.dataframe(data[selected_sheet], use_container_width=True, height=600)
    else:
        st.info("No raw data available. Please process files in the Admin panel.")
