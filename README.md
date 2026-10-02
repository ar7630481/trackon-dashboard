import streamlit as st
import pandas as pd
import numpy as np
import datetime
import urllib.parse
import os
import plotly.express as px

# ==========================================
# 1. PAGE SETUP & AUTHENTICATION
# ==========================================
st.set_page_config(page_title="Trackon Command Center", page_icon="🚀", layout="wide")

# Passwords
USER_PASS = "5272"
ADMIN_PASS = "9211213"

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'role' not in st.session_state:
    st.session_state['role'] = None

# Login Page
if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align: center; color: #2E4053;'>🚀 Trackon Master Command Center</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center;'>Please Log In</h3>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        password = st.text_input("Enter Password", type="password")
        if st.button("Login", use_container_width=True):
            if password == USER_PASS:
                st.session_state['logged_in'] = True
                st.session_state['role'] = 'User'
                st.rerun()
            elif password == ADMIN_PASS:
                st.session_state['logged_in'] = True
                st.session_state['role'] = 'Admin'
                st.rerun()
            else:
                st.error("❌ Incorrect Password!")
    st.stop()

# ==========================================
# 2. FILE HANDLING & SIDEBAR
# ==========================================
DATA_FILE = "master_dashboard_data.xlsx"

st.sidebar.title(f"Welcome, {st.session_state['role']}")
if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.session_state['role'] = None
    st.rerun()

st.sidebar.markdown("---")

# Admin Upload Section
if st.session_state['role'] == 'Admin':
    st.sidebar.subheader("🛠️ Admin Panel")
    uploaded_file = st.sidebar.file_uploader("Upload New Master Data File", type=['xlsx'])
    if uploaded_file is not None:
        with open(DATA_FILE, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.sidebar.success("✅ File Successfully Updated!")

# Last Updated Timestamp
if os.path.exists(DATA_FILE):
    timestamp = os.path.getmtime(DATA_FILE)
    dt = datetime.datetime.fromtimestamp(timestamp).strftime('%d %b %Y, %I:%M %p')
    st.sidebar.info(f"🕒 Last Updated:\n{dt}")
else:
    st.warning("⚠️ No data file found. Please ask Admin to upload the Master Excel File.")
    st.stop()

# ==========================================
# 3. DATA LOADING (CACHED FOR SPEED)
# ==========================================
@st.cache_data
def load_data():
    xls = pd.ExcelFile(DATA_FILE)
    sheets = xls.sheet_names
    data = {}
    if 'Legwise_Route_Summary' in sheets:
        data['leg_sum'] = pd.read_excel(xls, sheet_name='Legwise_Route_Summary')
    if 'Actionable_Notes' in sheets:
        data['notes'] = pd.read_excel(xls, sheet_name='Actionable_Notes')
    if 'Up_Down_Route_Summary' in sheets:
        data['cpk_updn'] = pd.read_excel(xls, sheet_name='Up_Down_Route_Summary')
    if 'Overall_Feeder_Usage' in sheets:
        data['cpk_fdr'] = pd.read_excel(xls, sheet_name='Overall_Feeder_Usage')
    return data

data = load_data()

# ==========================================
# 4. DASHBOARD NAVIGATION
# ==========================================
menu = ["📊 Daily Standup (1-Hour Call)", "📱 WhatsApp Automator", "💰 CPK & Utilization Analysis"]
choice = st.sidebar.radio("Navigate to:", menu)

st.title(choice)

# ---------------------------------------------------------
# A. DAILY STANDUP (Focus on Worst Performers)
# ---------------------------------------------------------
if choice == "📊 Daily Standup (1-Hour Call)":
    st.markdown("### 🚨 Exception Reporting (Focus on what's failing)")
    
    if 'notes' in data:
        df_notes = data['notes']
        all_ros = sorted(df_notes['Origin RO'].unique().tolist())
        selected_ro = st.selectbox("Select Regional Office (RO) to Address:", ["PAN INDIA"] + all_ros)
        
        if selected_ro != "PAN INDIA":
            df_notes = df_notes[df_notes['Origin RO'] == selected_ro]
            
        critical = df_notes[df_notes['Status'].str.contains("Critical", na=False, case=False)]
        warning = df_notes[df_notes['Status'].str.contains("Warning", na=False, case=False)]
        
        col1, col2, col3 = st.columns(3)
        col1.metric("🔴 Critical Failures", len(critical))
        col2.metric("🟠 Warnings", len(warning))
        col3.metric("🟢 Smooth Legs", len(df_notes) - len(critical) - len(warning))
        
        st.subheader("🔥 Top Priority Routes (Late Dep & Late Arr)")
        st.dataframe(critical[['Route Path', 'Legs', 'Actionable Note']], use_container_width=True)
        
    else:
        st.error("Actionable_Notes sheet not found in uploaded data.")

# ---------------------------------------------------------
# B. WHATSAPP AUTOMATOR
# ---------------------------------------------------------
elif choice == "📱 WhatsApp Automator":
    st.markdown("Select an RO to generate a pre-formatted WhatsApp report for the Vendor Group.")
    
    # Mapping RO to WhatsApp Group Names
    ro_group_map = {
        "DELRO": "Delhi Vendors Official 🚛",
        "MUMRO": "Mumbai Operations Sync 🚚",
        "CCURO": "Kolkata Master Group 📦",
        "PATRO": "Patna Route Alerts 🚨",
        "AMDRO": "Ahmedabad Logistics 🚛",
        # Add more as needed...
    }
    
    if 'notes' in data:
        df_notes = data['notes']
        all_ros = sorted(df_notes['Origin RO'].dropna().unique().tolist())
        sel_ro = st.selectbox("Select RO:", all_ros)
        
        group_name = ro_group_map.get(sel_ro, f"{sel_ro} Operations Group")
        st.info(f"📲 Mapped WhatsApp Group: **{group_name}**")
        
        # Generate Text
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
            
            # URL Encoding for Deep Link
            encoded_msg = urllib.parse.quote(msg)
            whatsapp_url = f"https://api.whatsapp.com/send?text={encoded_msg}"
            
            st.markdown(f"""
            <a href="{whatsapp_url}" target="_blank">
                <button style="background-color: #25D366; color: white; padding: 10px 24px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold;">
                    💬 Send to WhatsApp Web/App
                </button>
            </a>
            """, unsafe_allow_html=True)
            
            st.caption("Note: Streamlit cloud cannot automatically open your WhatsApp while you are sleeping. Click this button at 11 AM to instantly open the pre-filled message!")
        else:
            st.success(f"🎉 No critical delays for {sel_ro} today!")
    else:
        st.error("Data missing.")

# ---------------------------------------------------------
# C. CPK & UTILIZATION ANALYSIS
# ---------------------------------------------------------
elif choice == "💰 CPK & Utilization Analysis":
    if 'cpk_updn' in data:
        st.subheader("Linehaul Up/Down Performance")
        df_cpk = data['cpk_updn']
        
        # Filters
        ro_filter = st.selectbox("Filter RO (CPK):", ["ALL"] + sorted(df_cpk['VendorRO'].unique().tolist()))
        if ro_filter != "ALL":
            df_cpk = df_cpk[df_cpk['VendorRO'] == ro_filter]
            
        # KPIs
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Trips", int(df_cpk['Total Trips'].sum()))
        
        avg_util = (df_cpk['Total Carried Wt'].sum() / df_cpk['Total Capacity'].sum() * 100) if df_cpk['Total Capacity'].sum() > 0 else 0
        c2.metric("Overall Pan-India Utilization", f"{avg_util:.1f}%")
        
        avg_cpk = (df_cpk['Total Trip Cost'].sum() / df_cpk['Total Carried Wt'].sum()) if df_cpk['Total Carried Wt'].sum() > 0 else 0
        c3.metric("Overall Pan-India CPK", f"₹ {avg_cpk:.2f}")
        
        # Charts
        st.markdown("**Top 10 Worst Utilized Routes (< 50%)**")
        bad_util = df_cpk[df_cpk['Overall Util %'] < 0.50].sort_values(by='Overall Util %').head(10)
        
        if not bad_util.empty:
            bad_util['Util %'] = bad_util['Overall Util %'] * 100
            fig = px.bar(bad_util, x='Route (UP/DOWN)', y='Util %', color='VendorRO', text_auto='.1f', 
                         title="Routes Bleeding Money (Check Capacity Match)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.success("All routes are > 50% Utilized!")
            
        st.dataframe(df_cpk, use_container_width=True)
    else:
        st.error("CPK Data (Up_Down_Route_Summary) not found in the uploaded file.")
