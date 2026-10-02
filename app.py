import streamlit as st
import pandas as pd
import numpy as np
import datetime
import urllib.parse
import os
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. PAGE SETUP & THEME
# ==========================================
st.set_page_config(page_title="Trackon Command Center", page_icon="🚀", layout="wide")

st.markdown("""
<style>
    .reportview-container {
        background: #0E1117;
    }
    .dataframe {
        border-radius: 8px !important;
        overflow: hidden !important;
    }
</style>
""", unsafe_allow_html=True)

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
# 3. HELPER FUNCTIONS & ADMIN PANEL
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

st.sidebar.title(f"Welcome, {st.session_state['role']}")
if st.sidebar.button("Logout", key="logout_btn"):
    st.session_state['logged_in'] = False
    st.session_state['role'] = None
    st.rerun()

st.sidebar.markdown("---")

if st.session_state['role'] == 'Admin':
    st.sidebar.header("🛠 Admin Data Management")
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
    
if os.path.exists(FILE_MAP["FINAL_OUTPUT"]):
    ts = os.path.getmtime(FILE_MAP["FINAL_OUTPUT"])
    dt = datetime.datetime.fromtimestamp(ts).strftime('%d %b %Y, %I:%M %p')
    st.sidebar.info(f"📊 Dashboard Last Refreshed:\n{dt}")

# ==========================================
# 4. DATA LOADING
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
# 5. DASHBOARD NAVIGATION
# ==========================================
if not data:
    st.warning("⚠ No dashboard data found! Admin must upload raw files and process data.")
    st.stop()
    
menu = ["📊 Daily Standup (1-Hour Call)", "💳 Vendor Payment Dashboard", "📱 WhatsApp Automator", "💰 CPK & Utilization Analysis"]
choice = st.sidebar.radio("Navigate to:", menu)

# -------------------------------------------------------------
# A. DAILY STANDUP
# -------------------------------------------------------------
if choice == "📊 Daily Standup (1-Hour Call)":
    st.markdown("<h1 style='color: #4facfe;'>🚨 Exception Reporting</h1>", unsafe_allow_html=True)
    
    if 'Legwise_Route_Summary' in data and 'Legwise_Processed_Data' in data:
        df_leg_sum = data['Legwise_Route_Summary'].copy()
        df_raw_leg = data['Legwise_Processed_Data'].copy()
        
        all_ros = sorted(df_leg_sum['Origin RO'].dropna().unique().tolist())
        selected_ro = st.selectbox("Select Regional Office (RO):", ["PAN INDIA"] + all_ros)
        
        if selected_ro != "PAN INDIA":
            df_leg_sum = df_leg_sum[df_leg_sum['Origin RO'] == selected_ro]
            df_raw_leg = df_raw_leg[df_raw_leg['Origin RO'] == selected_ro]

        display_cols = ['Route Path', 'Legwise', 'Legs', 'Total_Trips', 
                        'Ontime Dep, Ontime Arr %', 'Ontime Dep, Late Arr %', 
                        'Late Dep, Late Arr %', 'Late Dep, Ontime Arr %']
        
        display_cols = [c for c in display_cols if c in df_leg_sum.columns]
        df_display = df_leg_sum[display_cols].copy()
            
        def extract_pct(x):
            if isinstance(x, str) and '%' in x:
                try: return float(x.split('%')[0].strip())
                except: return 0.0
            return 0.0
            
        if 'Late Dep, Late Arr %' in df_display.columns:
            df_display['SortKey'] = df_display['Late Dep, Late Arr %'].apply(extract_pct)
            df_display['Is_Single_Trip'] = df_display['Total_Trips'] == 1
            df_display = df_display.sort_values(by=['Is_Single_Trip', 'SortKey'], ascending=[True, False]).drop(columns=['SortKey', 'Is_Single_Trip'])

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
            if 'Late Dep, Late Arr' in col: return 'background-color: rgba(211, 47, 47, 0.2); color: #ff5252; font-weight: bold;'
            elif 'Ontime Dep, Ontime Arr' in col: return 'background-color: rgba(56, 142, 60, 0.2); color: #69f0ae; font-weight: bold;'
            elif 'Ontime Dep, Late Arr' in col: return 'background-color: rgba(245, 127, 23, 0.2); color: #ffd740; font-weight: bold;'
            elif 'Late Dep, Ontime Arr' in col: return 'background-color: rgba(123, 31, 162, 0.2); color: #e040fb; font-weight: bold;'
            return ''

        styled_df = df_display.style
        for col in pct_cols:
            if hasattr(styled_df, 'map'): styled_df = styled_df.map(lambda x, c=col: highlight_cells(x, c), subset=[col])
            else: styled_df = styled_df.applymap(lambda x, c=col: highlight_cells(x, c), subset=[col])

        st.markdown("### 🔥 Top Priority Routes Summary (Click a row to see proof)")
        
        selection = st.dataframe(
            styled_df, 
            use_container_width=True, 
            height=300, 
            on_select="rerun", 
            selection_mode="single-row"
        )
        
        if selection and selection.get('selection', {}).get('rows'):
            selected_idx = selection['selection']['rows'][0]
            # Fetch BOTH Route Path AND Legwise
            selected_route = df_display.iloc[selected_idx]['Route Path']
            selected_leg = df_display.iloc[selected_idx]['Legwise']
            
            st.markdown("---")
            st.markdown(f"### 🔍 1-Click Proof: Raw Data for `{selected_route}` - `{selected_leg}`")
            
            # Filter raw data using BOTH Route Path and Legwise
            filtered_raw = df_raw_leg[(df_raw_leg['Route Path'] == selected_route) & (df_raw_leg['Legwise'] == selected_leg)].copy()
            
            cols_to_drop = ['Scheduled TAT Till Destination', 'Actual TAT Till Destination', 
                            'Overall Remark', 'MCD_EndDate', 'LH Type', 'Origin', 'Destination', 'Region', 'Origin RO']
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
            st.info("👆 Click any row in the table above to view its detailed proof data here.")

    else:
        st.error("Operations Data missing.")

# -------------------------------------------------------------
# B. VENDOR PAYMENT DASHBOARD 
# -------------------------------------------------------------
elif choice == "💳 Vendor Payment Dashboard":
    st.markdown("<h1 style='color: #4facfe;'>💳 Pan-India Department Pending Tracker</h1>", unsafe_allow_html=True)
    
    if 'Master_Database' in data:
        df_pay = data['Master_Database'].copy()
        
        st.markdown("### 📊 Overall RO-Wise Control Center (Click a cell/row to filter)")
        pvt = pd.pivot_table(df_pay, values='Invoice Id', index='RO Name', columns='Department Bucket', aggfunc='count', fill_value=0, margins=True, margins_name='Grand Total')
        
        cols_order = ["1. USER / DRAFT PENDING", "2. COST CONTROL PENDING", "3. FINANCE PENDING", "4. PAYMENT PENDING", "5. OTHER PENDING", "Grand Total"]
        existing_cols = [c for c in cols_order if c in pvt.columns]
        pvt = pvt.reindex(columns=existing_cols)
        
        # Function to color columns in pivot table
        def color_payment_columns(val, col_name):
            if pd.isna(val) or val == 0:
                return ''
            if col_name == '1. USER / DRAFT PENDING':
                return 'background-color: rgba(211, 47, 47, 0.3); color: white;' # Red
            elif col_name == '2. COST CONTROL PENDING':
                return 'background-color: rgba(245, 127, 23, 0.3); color: white;' # Yellow
            elif col_name == '3. FINANCE PENDING':
                return 'background-color: rgba(245, 127, 23, 0.15); color: white;' # Light Yellow
            return ''

        styled_pvt = pvt.style
        for col in existing_cols:
            if hasattr(styled_pvt, 'map'):
                styled_pvt = styled_pvt.map(lambda x, c=col: color_payment_columns(x, c), subset=[col])
            else:
                styled_pvt = styled_pvt.applymap(lambda x, c=col: color_payment_columns(x, c), subset=[col])

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
            st.markdown(f"### 🔍 Payment Proof for `{sel_pay_ro}`")
            
            sel_bucket = st.selectbox("Select Pending Status:", existing_cols[:-1])
            
            if sel_pay_ro == 'Grand Total':
                filtered_pay = df_pay[df_pay['Department Bucket'] == sel_bucket].copy()
            else:
                filtered_pay = df_pay[(df_pay['RO Name'] == sel_pay_ro) & (df_pay['Department Bucket'] == sel_bucket)].copy()
                
            pay_order = ['Invoice Id', 'RO Name', 'Vendor Name', 'Amount', 'Status', 'Pending With', 'Days Pending', 'Aging Bucket', 'Revert Remarks']
            final_pay_cols = [c for c in pay_order if c in filtered_pay.columns]
            
            leftovers_pay = [c for c in filtered_pay.columns if c not in final_pay_cols and c != 'Bill Uploader']
            if 'Bill Uploader' in filtered_pay.columns: leftovers_pay.append('Bill Uploader') 
                
            filtered_pay = filtered_pay[final_pay_cols + leftovers_pay]
            if 'Amount' in filtered_pay.columns: filtered_pay = filtered_pay.sort_values(by='Amount', ascending=False)
                
            st.dataframe(filtered_pay, use_container_width=True)
        else:
             st.info("👆 Click any RO row in the table above to view specific invoices.")
    else:
        st.error("Payment Master Database not found.")

# -------------------------------------------------------------
# C. WHATSAPP AUTOMATOR
# -------------------------------------------------------------
elif choice == "📱 WhatsApp Automator":
    st.markdown("<h1 style='color: #25D366;'>📱 WhatsApp Automator</h1>", unsafe_allow_html=True)
    
    if 'Actionable_Notes' in data:
        df_notes = data['Actionable_Notes']
        all_ros = sorted(df_notes['Origin RO'].dropna().unique().tolist())
        sel_ro = st.selectbox("Select RO:", all_ros)
        
        ro_notes = df_notes[(df_notes['Origin RO'] == sel_ro) & (df_notes['Status'].str.contains("Critical", na=False, case=False))]
        
        if len(ro_notes) > 0:
            msg = f"*🔴 TRACKON DAILY ALERT: {sel_ro}*\nDate: {datetime.datetime.now().strftime('%d %b %Y')}\n\nFollowing Scheduled Routes are showing Critical Delays:\n\n"
            for idx, row in ro_notes.iterrows():
                msg += f"🛣️ *Route:* {row['Route Path']} ({row['Legs']})\n⚠️ *Issue:* {row['Actionable Note']}\n\n"
            msg += "Regards,\n*Central Control Tower*"
            
            st.text_area("Preview WhatsApp Message:", value=msg, height=250)
            encoded_msg = urllib.parse.quote(msg)
            whatsapp_url = f"https://api.whatsapp.com/send?text={encoded_msg}"
            
            st.markdown(f"""
            <a href="{whatsapp_url}" target="_blank">
                <button style="background-color: #25D366; color: black; padding: 10px 24px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold;">
                    💬 Send to WhatsApp Web
                </button>
            </a>
            """, unsafe_allow_html=True)
        else:
            st.success(f"🎉 No critical delays for {sel_ro} today!")
    else:
        st.info("No data available.")

# -------------------------------------------------------------
# D. CPK & UTILIZATION ANALYSIS
# -------------------------------------------------------------
elif choice == "💰 CPK & Utilization Analysis":
    st.markdown("<h1 style='color: #4facfe;'>💰 CPK & Utilization Analysis</h1>", unsafe_allow_html=True)
    if 'Up_Down_Route_Summary' in data:
        df_cpk = data['Up_Down_Route_Summary']
        ro_filter = st.selectbox("Filter RO (CPK):", ["ALL"] + sorted(df_cpk['VendorRO'].dropna().unique().tolist()))
        if ro_filter != "ALL": df_cpk = df_cpk[df_cpk['VendorRO'] == ro_filter]
            
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Trips", int(df_cpk['Total Trips'].sum()))
        avg_util = (df_cpk['Total Carried Wt'].sum() / df_cpk['Total Capacity'].sum() * 100) if df_cpk['Total Capacity'].sum() > 0 else 0
        c2.metric("Overall Utilization", f"{avg_util:.1f}%")
        avg_cpk = (df_cpk['Total Trip Cost'].sum() / df_cpk['Total Carried Wt'].sum()) if df_cpk['Total Carried Wt'].sum() > 0 else 0
        c3.metric("Overall CPK", f"₹ {avg_cpk:.2f}")
        
        st.dataframe(df_cpk.style.format({'Overall CPK': '{:.2f}', 'Overall Util %': '{:.2%}'}), use_container_width=True)
    else:
        st.info("Please process CPK data first.")
