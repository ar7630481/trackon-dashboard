import streamlit as st
import pandas as pd
import numpy as np
import datetime
import urllib.parse
import os
import time
import shutil
import warnings
from playwright.sync_api import sync_playwright
import pdfplumber

warnings.filterwarnings('ignore')

# ... (Apna baaki ka shuruwati code yahan rakh, imports se lekar FILE_MAP aur login tak) ...

# ==========================================
# 4. FLEET SCRAPER LOGIC (Cloud Crash & Download Fixes Added)
# ==========================================
FLEET_ACCOUNTS = [
    {"email": "anand.joshi@trackon.in", "password": "Trackon@123"},
    {"email": "lh.fleetops@trackon.in", "password": "i7F0TYVh@"},
    {"email": "amar.vandanamotors@gmail.com", "password": "Amar@123"},
    {"email": "9712339060", "password": "Boss@9918"}
]

def clear_pre_modal_popups(page):
    try:
        close_btn = page.locator('span.ant-tour-close-icon')
        if close_btn.is_visible(timeout=1000): close_btn.click()
    except: pass
    try:
        next_btn = page.locator("span", has_text="Next")
        if next_btn.is_visible(timeout=1000): next_btn.click()
    except: pass
    try:
        svg_close = page.locator('svg[data-icon="close"]')
        if svg_close.is_visible(timeout=1000): svg_close.click()
    except: pass

@st.cache_data(ttl=900, show_spinner="⏳ Tracking Active: Sabhi accounts se live data fetch ho raha hai...")
def fetch_fleet_data():
    os.system("playwright install chromium")
    
    # Use current working directory for reliable paths in cloud
    base_dir = os.getcwd() 
    all_raw_data = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox', 
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',           
                '--single-process'         
            ]
        ) 
        
        for acc in FLEET_ACCOUNTS:
            context = None
            try:
                context = browser.new_context(accept_downloads=True)
                page = context.new_page()
                
                safe_email = acc['email'].replace('@', '_').replace('.', '_')
                pdf_path = os.path.join(base_dir, f"temp_{safe_email}.pdf")
                
                page.goto("https://app.fleetx.io/users/login", timeout=90000, wait_until="domcontentloaded")
                page.fill('input[data-testid="email"]', acc['email'])
                page.fill('input[data-testid="password"]', acc['password'])
                page.click('button[type="submit"]')

                page.wait_for_selector('img[title="Realtime Vehicle Report"]', timeout=90000)
                page.wait_for_timeout(2000)

                clear_pre_modal_popups(page)

                page.evaluate("document.querySelector('img[title=\"Realtime Vehicle Report\"]').click()")
                page.wait_for_timeout(2000) 
                
                if os.path.exists(pdf_path): 
                    try: os.remove(pdf_path)
                    except: pass

                # --- NEW MORE RELIABLE DOWNLOAD LOGIC ---
                try:
                    # Tell playwright to expect a download when we click the button
                    with page.expect_download(timeout=60000) as download_info:
                        # Find and click the download button using a more robust selector
                        download_buttons = page.locator("span", has_text="Download")
                        # Click the last one or the one containing 'PDF' if possible
                        if download_buttons.count() > 0:
                             download_buttons.last.click()
                        else:
                             page.evaluate("Array.from(document.querySelectorAll('span')).find(el => el.textContent.includes('Download'))?.click()")
                             
                    download = download_info.value
                    
                    # Wait for download to complete and save it to our specific path
                    download.save_as(pdf_path)
                    print(f"✅ Downloaded successfully for {acc['email']}")

                except Exception as e:
                     print(f"⚠️ Native download failed for {acc['email']}: {e}")
                     # Fallback to older logic if native expect_download fails
                     page.evaluate("Array.from(document.querySelectorAll('span')).find(el => el.textContent.includes('Download'))?.click()")
                     page.wait_for_timeout(15000) # Wait 15 seconds as a fallback

                # ==========================================
                # EXTRACTION & READ
                # ==========================================
                if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
                    with pdfplumber.open(pdf_path) as pdf:
                        for page_obj in pdf.pages:
                            table = page_obj.extract_table()
                            if table:
                                for row in table:
                                    if any(cell and str(cell).strip() for cell in row):
                                        all_raw_data.append(row)
                    try: os.remove(pdf_path)
                    except: pass
                else:
                    print(f"❌ Final check: File nahi mili ya khali hai for {acc['email']}")

            except Exception as e:
                print(f"Error fetching {acc['email']}: {e}")
            finally:
                if context:
                    try: context.close()
                    except: pass
                
        browser.close()

    if all_raw_data:
        max_cols = max(len(row) for row in all_raw_data)
        normalized_data = [row + [""] * (max_cols - len(row)) for row in all_raw_data]
        df = pd.DataFrame(normalized_data[1:], columns=normalized_data[0])
        df.columns = [str(c).replace('\n', ' ').strip() if c else f"Col_{i}" for i, c in enumerate(df.columns)]
        
        veh_col = next((c for c in df.columns if 'Vehicle' in str(c) or 'Name' in str(c)), None)
        if veh_col:
            raw_str = df[veh_col].astype(str).str.replace(r'\n', ' ', regex=True)
            df['Vehicle_Code'] = raw_str.str.extract(r'(?i)(?:Name:)?\s*(\d{4})', expand=False).fillna("-")
            df['Full_Number'] = raw_str.str.extract(r'(?i)No:\s*([A-Z0-9]+)', expand=False).fillna("-")
        else:
            df['Vehicle_Code'] = "-"
            df['Full_Number'] = "-"
            
        status_col = next((c for c in df.columns if 'Status' in str(c) and 'Job' not in str(c)), None)
        df['Status'] = df[status_col].astype(str).str.replace(r'\n', ' ', regex=True).str.strip() if status_col else "-"
            
        speed_col = next((c for c in df.columns if 'Spee' in str(c) or 'Speed' in str(c)), None)
        df['Speed'] = df[speed_col].astype(str).str.replace(r'\n', ' ', regex=True).str.strip() if speed_col else "-"
            
        nearest_col = next((c for c in df.columns if 'Nearest' in str(c)), None)
        df['Remaining_KMS'] = df[nearest_col].astype(str).str.replace(r'\n', ' ', regex=True).str.strip() if nearest_col else "-"
            
        loc_col = next((c for c in df.columns if 'Location' in str(c)), None)
        df['Location'] = df[loc_col].astype(str).str.replace(r'\n', ' ', regex=True).str.strip() if loc_col else "-"
            
        time_col = next((c for c in df.columns if 'Last' in str(c) or 'dated' in str(c)), None)
        df['Last_Updated'] = df[time_col].astype(str).str.replace(r'\n', ' ', regex=True).str.strip() if time_col else "-"

        final_cols = ['Vehicle_Code', 'Full_Number', 'Status', 'Speed', 'Remaining_KMS', 'Location', 'Last_Updated']
        for col in final_cols:
            if col not in df.columns:
                df[col] = "-"
                
        df_clean = df[final_cols]
        df_clean = df_clean.drop_duplicates(subset=['Full_Number'], keep='first')
        return df_clean
    else:
        return pd.DataFrame()


# ... (Apna bacha hua code yahan daal de: def process_all_data() aur saare streamlit UI components) ...
