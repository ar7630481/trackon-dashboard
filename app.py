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

# ==========================================
# 4. THE CORE PROCESSING ENGINE (Skipped long backend logic here to save space, assuming it's intact from previous)
# ==========================================
# IMPORTANT: DO NOT DELETE your `def process_all_data():` function. 
# Keep your entire Module 1 to 5 data processing code here exactly as it was.

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
    # if st.sidebar.button("🚀 PROCESS & REFRESH DATA", use_container_width=True):
    #     process_all_data()
    #     st.rerun()

if os.path.exists(FILE_MAP["FINAL_OUTPUT"]):
    ts = os.path.getmtime(FILE_MAP["FINAL_OUTPUT"])
    dt = datetime.datetime.fromtimestamp(ts).strftime('%d %b %Y, %I:%M %p')
    st.sidebar.info(f"📊 Dashboard Last Refreshed:\n{dt}")

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
menu = ["📊 Daily Standup (1-Hour Call)", "💳 Vendor Payment Dashboard", "📱 WhatsApp Automator", "💰 CPK & Utilization Analysis"]
choice = st.sidebar.radio("Navigate to:", menu)

# -------------------------------------------------------------
# A. DAILY STANDUP (VISUAL HEATMAP & DEEP DIVE ENGINE)
# -------------------------------------------------------------
if choice == "📊 Daily Standup (1-Hour Call)":
    st.title("🚨 Exception Reporting (Manager's Visual Heatmap)")
    
    if 'Legwise_Route_Summary' in data and 'Legwise_Processed_Data' in data:
        df_leg_sum = data['Legwise_Route_Summary'].copy()
        df_raw_leg = data['Legwise_Processed_Data'].copy()
        
        all_ros = sorted(df_leg_sum['Origin RO'].dropna().unique().tolist())
        selected_ro = st.selectbox("Select Regional Office (RO) to Address:", ["PAN INDIA"] + all_ros)
        
        if selected_ro != "PAN INDIA":
            df_leg_sum = df_leg_sum[df_leg_sum['Origin RO'] == selected_ro]
            df_raw_leg = df_raw_leg[df_raw_leg['Origin RO'] == selected_ro]

        # 1. CRISP COLUMNS ONLY
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
            df_display = df_display.sort_values(by='SortKey', ascending=False).drop(columns=['SortKey'])

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
            
            if pct == 0: return 'color: #B0BEC5;' 
            if 'Late Dep, Late Arr' in col: return 'background-color: #ffebee; color: #d32f2f; font-weight: bold;'
            elif 'Ontime Dep, Ontime Arr' in col: return 'background-color: #e8f5e9; color: #388e3c; font-weight: bold;'
            elif 'Ontime Dep, Late Arr' in col: return 'background-color: #fff8e1; color: #f57f17; font-weight: bold;'
            elif 'Late Dep, Ontime Arr' in col: return 'background-color: #f3e5f5; color: #7b1fa2; font-weight: bold;'
            return ''

        styled_df = df_display.style
        for col in pct_cols:
            if hasattr(styled_df, 'map'):
                styled_df = styled_df.map(lambda x, c=col: highlight_cells(x, c), subset=[col])
            else:
                styled_df = styled_df.applymap(lambda x, c=col: highlight_cells(x, c), subset=[col])

        st.markdown("### 🔥 Top Priority Routes Summary")
        st.dataframe(styled_df, use_container_width=True, height=350)
        
        # -------------------------------------------------------------
        # 2. DEEP DIVE: RAW DATA EVIDENCE LINKING
        # -------------------------------------------------------------
        st.markdown("---")
        st.markdown("### 🔍 Deep Dive: Raw Data Evidence (Proof)")
        
        selected_route = st.selectbox("🔗 Select Route from Dropdown below to see exact Proof:", df_display['Route Path'].unique())
        
        if selected_route:
            filtered_raw = df_raw_leg[df_raw_leg['Route Path'] == selected_route].copy()
            
            # 🚀 DROP USELESS COLUMNS FOR CLEAN VIEW
            cols_to_drop = ['Scheduled TAT Till Destination', 'Actual TAT Till Destination', 
                            'Overall Remark', 'MCD_EndDate', 'LH Type', 'Origin', 'Destination', 'Region', 'Origin RO']
            filtered_raw = filtered_raw.drop(columns=[c for c in cols_to_drop if c in filtered_raw.columns], errors='ignore')
            
            # 🚀 STRICT LOGICAL ORDER (Proof First)
            logical_order = [
                'Route Path', 'MCD_StartDate', 'Legwise', 'Legs', 'Remark', 
                'Scheduled Departure Time', 'Actual Departure Time', 
                'Scheduled Arrival Time', 'Actual Arrival Time', 
                'Scheduled Halting', 'Actual Halting', 
                'MasterCDNo', 'VendorName', 'RouteCode', 'VehicleNo'
            ]
            
            final_cols = [c for c in logical_order if c in filtered_raw.columns]
            leftovers = [c for c in filtered_raw.columns if c not in final_cols]
            filtered_raw = filtered_raw[final_cols + leftovers]
            
            def highlight_remarks(val):
                if isinstance(val, str):
                    if 'Late Dep, Late Arr' in val: return 'color: #d32f2f; font-weight: bold;'
                    elif 'Ontime Dep, Ontime Arr' in val: return 'color: #388e3c;'
                return ''
                
            styled_raw = filtered_raw.style
            if 'Remark' in filtered_raw.columns:
                if hasattr(styled_raw, 'map'): styled_raw = styled_raw.map(highlight_remarks, subset=['Remark'])
                else: styled_raw = styled_raw.applymap(highlight_remarks, subset=['Remark'])
                    
            st.dataframe(styled_raw, use_container_width=True)

    else:
        st.info("Please upload raw files and click 'PROCESS & REFRESH DATA' in the Admin Panel.")

# -------------------------------------------------------------
# B. VENDOR PAYMENT DASHBOARD (DRILLDOWN ENGINE)
# -------------------------------------------------------------
elif choice == "💳 Vendor Payment Dashboard":
    st.title("💳 Pan-India Department Pending Tracker")
    
    if 'Master_Database' in data:
        df_pay = data['Master_Database'].copy()
        
        st.markdown("### 📊 Overall RO-Wise Control Center")
        pvt = pd.pivot_table(df_pay, values='Invoice Id', index='RO Name', columns='Department Bucket', aggfunc='count', fill_value=0, margins=True, margins_name='Grand Total')
        
        cols_order = ["1. USER / DRAFT PENDING", "2. COST CONTROL PENDING", "3. FINANCE PENDING", "4. PAYMENT PENDING", "5. OTHER PENDING", "Grand Total"]
        existing_cols = [c for c in cols_order if c in pvt.columns]
        pvt = pvt.reindex(columns=existing_cols)
        st.dataframe(pvt, use_container_width=True)
        
        # DEEP DIVE LOGIC
        st.markdown("---")
        st.markdown("### 🔍 Deep Dive: Payment Evidence")
        
        col1, col2 = st.columns(2)
        with col1:
            sel_pay_ro = st.selectbox("Select RO:", sorted(df_pay['RO Name'].dropna().unique().tolist()))
        with col2:
            sel_bucket = st.selectbox("Select Department Bucket:", sorted(df_pay['Department Bucket'].dropna().unique().tolist()))
            
        filtered_pay = df_pay[(df_pay['RO Name'] == sel_pay_ro) & (df_pay['Department Bucket'] == sel_bucket)].copy()
        
        # 🚀 LOGICAL ORDER FOR PAYMENTS (Bill Uploader to the absolute back)
        pay_order = ['Invoice Id', 'Vendor Name', 'Amount', 'Status', 'Pending With', 'Days Pending', 'Aging Bucket', 'Revert Remarks']
        final_pay_cols = [c for c in pay_order if c in filtered_pay.columns]
        
        leftovers_pay = [c for c in filtered_pay.columns if c not in final_pay_cols and c != 'Bill Uploader']
        if 'Bill Uploader' in filtered_pay.columns:
            leftovers_pay.append('Bill Uploader') # Pushed to the extreme end
            
        filtered_pay = filtered_pay[final_pay_cols + leftovers_pay]
        
        st.dataframe(filtered_pay, use_container_width=True)
    else:
        st.info("Payment Master Database not found. Please process data.")

# -------------------------------------------------------------
# C. WHATSAPP AUTOMATOR
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
# D. CPK & UTILIZATION ANALYSIS
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
