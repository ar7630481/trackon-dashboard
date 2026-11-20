import os
import py_compile
import shutil

APP_PATH = "app.py"
BACKUP_PATH = "app_backup_before_bi.py"


def apply_patch(src, name, old, new, already_marker=None):
    if already_marker and already_marker in src:
        print(f"⏭️  Already applied: {name}")
        return src
    if old not in src:
        print(f"⚠️  Anchor not found (skipped): {name}")
        return src
    print(f"✅ Applied: {name}")
    return src.replace(old, new, 1)


def main():
    if not os.path.exists(APP_PATH):
        raise FileNotFoundError("app.py not found in the current folder!")

    if not os.path.exists(BACKUP_PATH):
        shutil.copy2(APP_PATH, BACKUP_PATH)
        print(f"💾 Backup created: {BACKUP_PATH}")

    with open(APP_PATH, "r", encoding="utf-8") as f:
        code = f.read()

    # 1. Import bi_engine & raise pandas styler safe limit
    code = apply_patch(
        code,
        "Import bi_engine + Styler limit",
        "import html as html_module\nimport textwrap",
        "import html as html_module\nimport textwrap\nimport bi_engine\npd.set_option('styler.render.max_elements', 500000)",
        already_marker="import bi_engine",
    )

    # 2. Fix 3 invalid CSS '- { box-sizing:' typos
    if "- { box-sizing:" in code:
        code = code.replace("- { box-sizing:", "* { box-sizing:")
        print("✅ Applied: Fixed 3 CSS box-sizing typos")

    # 3. Seamless signed-token auth for New-Window Raw Data (?raw_view=1)
    code = apply_patch(
        code,
        "New-Window Raw View Auth Token",
        "if not st.session_state['logged_in']:\n    st.markdown(\"<br><br><br>\"",
        """try:
    _rv_params = st.query_params
    _rv_flag = str(_rv_params.get('raw_view', ''))
    _rv_snap = str(_rv_params.get('snap', ''))
    _rv_auth = str(_rv_params.get('raw_auth', ''))
except Exception:
    _rv_flag, _rv_snap, _rv_auth = '', '', ''
if not st.session_state['logged_in'] and _rv_flag == '1':
    _rv_user = bi_engine.verify_raw_view_token(DATA_DIR, _rv_auth, _rv_snap, USERS_DB)
    if _rv_user:
        _rv_ud = USERS_DB[_rv_user]
        st.session_state['logged_in'] = True
        st.session_state['username'] = _rv_user
        st.session_state['role'] = _rv_ud.get('role', 'User')
        st.session_state['all_vendors'] = _rv_ud.get('all_vendors', True)
        st.session_state['allowed_vendors'] = _rv_ud.get('vendors', [])
        st.session_state['allowed_modules'] = _rv_ud.get('modules', STANDARD_MODULES)
        st.session_state['user_label'] = _rv_ud.get('label', _rv_user)

if not st.session_state['logged_in']:
    st.markdown("<br><br><br>\"""",
        already_marker="verify_raw_view_token",
    )

    # 4. Route to Full-Screen Raw Window right before Section 6 (all helpers already defined!)
    code = apply_patch(
        code,
        "Full-Screen New-Window Router",
        "# ==========================================\n# 6. SIDEBAR: ADMIN PANEL & RATE CORRECTIONS",
        """if _rv_flag == '1' and _rv_snap:
    bi_engine.render_fullscreen_raw_window(
        DATA_DIR, _rv_snap, write_styled_sheet_to_excel, style_ui_dataframe, selected_theme
    )

# ==========================================
# 6. SIDEBAR: ADMIN PANEL & RATE CORRECTIONS""",
        already_marker="render_fullscreen_raw_window(",
    )

    # 5. Guard style_ui_dataframe against huge table Styler OOM crash
    code = apply_patch(
        code,
        "Safe Styler Cell-Limit Guard",
        'def style_ui_dataframe(df_in):\n    """Applies Green (Achievement), Red (Failure), Yellow (Warning), Purple highlights to Streamlit UI tables."""\n    if df_in is None or df_in.empty:\n        return df_in',
        'def style_ui_dataframe(df_in):\n    """Applies Green (Achievement), Red (Failure), Yellow (Warning), Purple highlights to Streamlit UI tables."""\n    if df_in is None or df_in.empty or df_in.size > 40000:\n        return df_in',
        already_marker="df_in.size > 40000",
    )

    # 6. Fast Bulk-Write Guard in write_styled_sheet_to_excel (fixes long processing Excel timeout & NaN crashes)
    code = apply_patch(
        code,
        "Fast Large-Sheet Excel Export + NaN/Inf Guard",
        "    worksheet.set_row(0, 26)\n    for col_idx, col_name in enumerate(df.columns):\n        worksheet.write(0, col_idx, str(col_name), header_fmt)",
        """    worksheet.set_row(0, 26)
    for col_idx, col_name in enumerate(df.columns):
        worksheet.write(0, col_idx, str(col_name), header_fmt)

    # Fast vectorized path for huge raw sheets (>12,000 rows) to prevent Streamlit Cloud timeout
    if len(df) > 12000:
        safe_df = df.replace([np.inf, -np.inf], np.nan).fillna("")
        for r_i, row_vals in enumerate(safe_df.itertuples(index=False, name=None), start=1):
            worksheet.write_row(r_i, 0, row_vals, cell_fmt)
        for i, col in enumerate(df.columns):
            sample_len = safe_df[col].head(500).astype(str).map(len).max() if not safe_df.empty else 10
            worksheet.set_column(i, i, min(max(sample_len, len(str(col))) + 3, 38))
        worksheet.autofilter(0, 0, len(df), max(len(df.columns) - 1, 0))
        worksheet.freeze_panes(1, 0)
        return""",
        already_marker="if len(df) > 12000:",
    )

    # 7. Vectorize get_sch_time & guard Cartesian merge explosion in get_processed_data_cached
    code = apply_patch(
        code,
        "Vectorize Schedule Time + Prevent Cartesian Merge OOM",
        """        df_rte['Route Branch Code'] = df_rte['Route Branch Code'].astype(str).str.strip()
        df_rte = df_rte[['Route Code', 'Route Branch Code', 'Route Day', 'Schedule Departure Time', 'Schedule Arrival Time']]
        df_leg_all = df_leg_all.merge(df_rte, left_on=['RouteCode', 'CD_FromBranch'], right_on=['Route Code', 'Route Branch Code'], how='left')
        df_leg_all.rename(columns={'Route Day': 'Dep_Route_Day', 'Schedule Departure Time': 'Sch_Dep_Time_Raw'}, inplace=True)
        df_leg_all.drop(columns=['Schedule Arrival Time'], inplace=True, errors='ignore')
        
        df_leg_all = df_leg_all.merge(df_rte[['Route Code', 'Route Branch Code', 'Route Day', 'Schedule Arrival Time']], left_on=['RouteCode', 'CD_ToBranch'], right_on=['Route Code', 'Route Branch Code'], how='left')
        df_leg_all.rename(columns={'Route Day': 'Arr_Route_Day', 'Schedule Arrival Time': 'Sch_Arr_Time_Raw'}, inplace=True)

        df_leg_all['Scheduled Departure Time'] = df_leg_all.apply(lambda r: get_sch_time(r, 'Dep_Route_Day', 'Sch_Dep_Time_Raw'), axis=1)
        df_leg_all['Scheduled Arrival Time'] = df_leg_all.apply(lambda r: get_sch_time(r, 'Arr_Route_Day', 'Sch_Arr_Time_Raw'), axis=1)""",
        """        df_rte['Route Branch Code'] = df_rte['Route Branch Code'].astype(str).str.strip()
        df_rte = df_rte[['Route Code', 'Route Branch Code', 'Route Day', 'Schedule Departure Time', 'Schedule Arrival Time']].drop_duplicates(subset=['Route Code', 'Route Branch Code'])
        df_leg_all = df_leg_all.merge(df_rte, left_on=['RouteCode', 'CD_FromBranch'], right_on=['Route Code', 'Route Branch Code'], how='left')
        df_leg_all.rename(columns={'Route Day': 'Dep_Route_Day', 'Schedule Departure Time': 'Sch_Dep_Time_Raw'}, inplace=True)
        df_leg_all.drop(columns=['Schedule Arrival Time'], inplace=True, errors='ignore')
        
        df_leg_all = df_leg_all.merge(df_rte[['Route Code', 'Route Branch Code', 'Route Day', 'Schedule Arrival Time']], left_on=['RouteCode', 'CD_ToBranch'], right_on=['Route Code', 'Route Branch Code'], how='left')
        df_leg_all.rename(columns={'Route Day': 'Arr_Route_Day', 'Schedule Arrival Time': 'Sch_Arr_Time_Raw'}, inplace=True)

        def _vec_sch_time(base_dt, day_ser, time_ser):
            days_num = pd.to_numeric(day_ser, errors='coerce')
            uniq_t = {val: time_to_hrs(val) for val in pd.unique(time_ser)}
            hrs_num = time_ser.map(uniq_t)
            valid = base_dt.notna() & days_num.notna() & hrs_num.notna()
            out_dt = pd.Series(pd.NaT, index=base_dt.index, dtype='datetime64[ns]')
            if valid.any():
                out_dt.loc[valid] = (
                    base_dt.loc[valid].dt.normalize()
                    + pd.to_timedelta(days_num.loc[valid], unit='D')
                    + pd.to_timedelta(hrs_num.loc[valid], unit='h')
                )
            return out_dt

        df_leg_all['Scheduled Departure Time'] = _vec_sch_time(df_leg_all['MCD_StartDate_DT'], df_leg_all['Dep_Route_Day'], df_leg_all['Sch_Dep_Time_Raw'])
        df_leg_all['Scheduled Arrival Time'] = _vec_sch_time(df_leg_all['MCD_StartDate_DT'], df_leg_all['Arr_Route_Day'], df_leg_all['Sch_Arr_Time_Raw'])""",
        already_marker="def _vec_sch_time(",
    )

    # 8. Safe nan_inf_to_errors + Fast Pickle Disk Cache in process_all_data & read_dashboard_sheets_cached
    code = apply_patch(
        code,
        "Fast Pickle Cache + NaN-Safe Excel Writer in process_all_data",
        """        status_text.text("⚙️ Saving Master Database...")
        with tempfile.NamedTemporaryFile(dir=DATA_DIR, suffix='.xlsx', delete=False) as tmp:
            temp_output = tmp.name
        with pd.ExcelWriter(temp_output, engine='xlsxwriter') as writer:
            for k, v in data_for_export.items():
                v.to_excel(writer, sheet_name=k, index=False)
        os.replace(temp_output, FILE_MAP["FINAL_OUTPUT"])
        
        progress.progress(90)
        status_text.text("⚙️ Generating Styled VIP Executive Report directly to disk...")
        generate_vip_executive_report_to_disk(data_for_export)""",
        """        status_text.text("⚙️ Saving Fast Binary Cache & Master Database...")
        try:
            pd.to_pickle(data_for_export, os.path.join(DATA_DIR, "processed_fast_cache.pkl"))
        except Exception:
            pass
        with tempfile.NamedTemporaryFile(dir=DATA_DIR, suffix='.xlsx', delete=False) as tmp:
            temp_output = tmp.name
        with pd.ExcelWriter(temp_output, engine='xlsxwriter', engine_kwargs={'options': {'nan_inf_to_errors': True}}) as writer:
            for k, v in data_for_export.items():
                v.replace([np.inf, -np.inf], np.nan).to_excel(writer, sheet_name=k, index=False)
        os.replace(temp_output, FILE_MAP["FINAL_OUTPUT"])
        gc.collect()
        
        progress.progress(90)
        status_text.text("⚙️ Generating Styled VIP Executive Report directly to disk...")
        try:
            generate_vip_executive_report_to_disk(data_for_export)
        except Exception as vip_exc:
            logging.warning(f"VIP report generation warning: {vip_exc}")""",
        already_marker="processed_fast_cache.pkl",
    )

    code = apply_patch(
        code,
        "NaN-Safe VIP Report Writer",
        'with pd.ExcelWriter(output_path or FILE_MAP["EXECUTIVE_REPORT"], engine=\'xlsxwriter\') as writer:',
        'with pd.ExcelWriter(output_path or FILE_MAP["EXECUTIVE_REPORT"], engine=\'xlsxwriter\', engine_kwargs={\'options\': {\'nan_inf_to_errors\': True}}) as writer:',
        already_marker="nan_inf_to_errors': True}}) as writer:",
    )

    code = apply_patch(
        code,
        "Fast Cache Loader in read_dashboard_sheets_cached",
        """@st.cache_data(show_spinner=False, max_entries=12)
def read_dashboard_sheets_cached(path, signature, sheet_names):
    \"\"\"Keep workbook reads warm across navigation; the file signature invalidates stale data.\"\"\"
    with pd.ExcelFile(path, engine='openpyxl') as workbook:
        return {name: workbook.parse(name) for name in sheet_names if name in workbook.sheet_names}""",
        """@st.cache_data(show_spinner=False, max_entries=12)
def read_dashboard_sheets_cached(path, signature, sheet_names):
    \"\"\"Load instantly from binary cache if fresh, else fall back to openpyxl.\"\"\"
    fast_pkl = os.path.join(DATA_DIR, "processed_fast_cache.pkl")
    if os.path.exists(fast_pkl):
        try:
            if os.path.getmtime(fast_pkl) >= os.path.getmtime(path) - 5:
                bundle = pd.read_pickle(fast_pkl)
                if isinstance(bundle, dict):
                    return {name: bundle[name] for name in sheet_names if name in bundle}
        except Exception:
            pass
    with pd.ExcelFile(path, engine='openpyxl') as workbook:
        return {name: workbook.parse(name) for name in sheet_names if name in workbook.sheet_names}""",
        already_marker="fast_pkl = os.path.join(DATA_DIR",
    )

    # 9. Upgrade render_summary_with_raw_drilldown -> Full-Screen New Window Launcher
    code = apply_patch(
        code,
        "Comm Hub & Drilldown -> New-Window Raw Explorer",
        """    st.markdown(f'#### {title} · {selected_col or "selected row"} detail · {len(detail):,} records')
    compact = compact_detail_frame(detail, raw_kind)
    if compact.empty:
        st.info('No matching raw rows were found for the selected summary line.')
        return
    st.dataframe(style_ui_dataframe(compact), use_container_width=True, hide_index=True, height=330)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        write_styled_sheet_to_excel(writer, compact, 'Focused_Raw_Data', sheet_type=raw_kind)
    st.download_button(
        f'📥 Download {title} detail (formatted Excel)', data=buffer.getvalue(),
        file_name=f'{re.sub(r"[^A-Za-z0-9_-]+", "_", title)}_Detail.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        key=f'{key}_download'
    )""",
        """    compact = compact_detail_frame(detail, raw_kind)
    bi_engine.render_new_window_raw_launcher(
        df=compact,
        data_dir=DATA_DIR,
        title=f'{title} · {selected_col or "Selected Row"}',
        subtitle=f'Focused raw records ({len(compact):,} rows)',
        sheet_type=raw_kind,
        excel_writer_fn=write_styled_sheet_to_excel,
        style_fn=style_ui_dataframe,
        theme=selected_theme,
        key_prefix=f'{key}_nw',
        file_prefix=title,
    )""",
        already_marker="key_prefix=f'{key}_nw'",
    )

    # 10. Operations Summary: Fix Duplicate Chart Loop Bug + Plug Power BI Suite + Full-Screen Raw Windows
    code = apply_patch(
        code,
        "Operations Summary: Fix Duplicate Chart Bug + Power BI Suite",
        """        for c in pct_cols:
            df_display[c] = df_display[c].apply(lambda value, col=c: _format_ops_status_badge(value, col))
            st.markdown("### 📈 Visual Analytics: Route Health")
            chart_c1, chart_c2 = st.columns(2)
            
            # 1. E2E Performance Donut Chart
            # 1. E2E Performance Donut Chart (Based on Actual Remarks)
            pie_data = pd.DataFrame(list(ops_outcome_counts.items()), columns=['Status', 'Count'])
            pie_data = pie_data[pie_data['Count'] > 0]
            
            if not pie_data.empty:
                fig_pie = px.pie(
                    pie_data, values='Count', names='Status', hole=0.45,
                    title='Trip Health by Remark Outcome'
                )
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                fig_pie.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", 
                    font_color=selected_theme["text"], margin=dict(t=40, b=10, l=10, r=10),
                    showlegend=False
                )
                chart_c1.plotly_chart(fig_pie, use_container_width=True)

            # 2. Top 5 Problematic Routes Bar Chart
            if 'Late Dep, Late Arr %' in df_leg_sum.columns:
                # Calculate actual late count per route for the bar chart
                df_leg_sum['Late_Count_Temp'] = df_leg_sum['Total_Trips'] * (df_leg_sum['Late Dep, Late Arr %'].apply(extract_pct) / 100)
                top_problem_routes = df_leg_sum.nlargest(5, 'Late_Count_Temp')
                
                if not top_problem_routes.empty and top_problem_routes['Late_Count_Temp'].sum() > 0:
                    fig_bar = px.bar(
                        top_problem_routes, x='Route Path', y='Late_Count_Temp',
                        text_auto='.0f', title='Top 5 Routes by Late Arrivals',
                        color_discrete_sequence=['#ef4444']
                    )
                    fig_bar.update_layout(
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        font_color=selected_theme["text"], margin=dict(t=40, b=10, l=10, r=10),
                        xaxis_title="", yaxis_title="Late Trips"
                    )
                    chart_c2.plotly_chart(fig_bar, use_container_width=True)
                
                df_leg_sum = df_leg_sum.drop(columns=['Late_Count_Temp'], errors='ignore')""",
        """        for c in pct_cols:
            df_display[c] = df_display[c].apply(lambda value, col=c: _format_ops_status_badge(value, col))

        bi_engine.render_ops_powerbi_suite(raw_status, df_leg_sum, ops_outcome_counts, selected_theme, THEME_IS_LIGHT)
        bi_engine.render_new_window_raw_launcher(
            df=clean_dataframe_for_excel(df_raw_leg.drop(columns=['_OpsRemarkOutcome'], errors='ignore'), sheet_type="ops_raw"),
            data_dir=DATA_DIR,
            title="All Filtered Operations Raw Data",
            subtitle=f"Duration: {dur_str_ops} · Zone: {selected_zone} · RO: {selected_ro}",
            sheet_type="ops_raw",
            excel_writer_fn=write_styled_sheet_to_excel,
            style_fn=style_ui_dataframe,
            theme=selected_theme,
            key_prefix="ops_all_nw",
            file_prefix="Operations_All_Filtered",
            compact_mode=True,
        )""",
        already_marker="render_ops_powerbi_suite(",
    )

    code = apply_patch(
        code,
        "Operations Selected Row -> New-Window Raw Explorer",
        """            st.markdown("---")
            st.markdown(f"### 📄 Remark-wise Raw Trip Data · `{selected_route}` · `{selected_leg}`")
            
            filtered_raw = df_raw_leg[(df_raw_leg['Route Path'] == selected_route) & (df_raw_leg['Legwise'] == selected_leg)].copy()
            filtered_raw = filtered_raw.drop(columns=['_OpsRemarkOutcome'], errors='ignore')
            filtered_raw = clean_dataframe_for_excel(filtered_raw, sheet_type="ops_raw")
            st.caption("The Remark column is the trip outcome shown for each raw record.")
            st.dataframe(style_ui_dataframe(filtered_raw), use_container_width=True)""",
        """            st.markdown("---")
            filtered_raw = df_raw_leg[(df_raw_leg['Route Path'] == selected_route) & (df_raw_leg['Legwise'] == selected_leg)].copy()
            filtered_raw = filtered_raw.drop(columns=['_OpsRemarkOutcome'], errors='ignore')
            filtered_raw = clean_dataframe_for_excel(filtered_raw, sheet_type="ops_raw")
            bi_engine.render_new_window_raw_launcher(
                df=filtered_raw,
                data_dir=DATA_DIR,
                title=f"Ops Raw Data · {selected_route} ({selected_leg})",
                subtitle=f"Duration: {dur_str_ops} · Zone: {selected_zone} · RO: {selected_ro}",
                sheet_type="ops_raw",
                excel_writer_fn=write_styled_sheet_to_excel,
                style_fn=style_ui_dataframe,
                theme=selected_theme,
                key_prefix="ops_sel_nw",
                file_prefix=f"Ops_{selected_route}_{selected_leg}",
            )""",
        already_marker='key_prefix="ops_sel_nw"',
    )

    # 11. Vendor Performance: Power BI Suite + Full-Screen New-Window Raw Data
    code = apply_patch(
        code,
        "Vendor Performance -> Power BI Suite",
        """        # ==========================================
        # UPGRADE: POWER BI-STYLE PLOTLY VISUALS (VENDORS)
        # ==========================================
        if PLOTLY_AVAILABLE and not df_display.empty:
            st.markdown("### 📊 Visual Analytics: Vendor Reliability")
            v_chart1, v_chart2 = st.columns(2)
            
            # 1. Vendor Volume vs On-Time Scatter/Bubble
            v_vol = df_display.groupby('VendorName').agg(
                Total_Trips=('Total_Trips', 'sum'),
                Ontime_Count=('Ontime Arrival', lambda x: sum(int(str(v).split('(')[-1].replace(')','')) if '(' in str(v) else 0 for v in x))
            ).reset_index()
            
            v_vol['On-Time %'] = (v_vol['Ontime_Count'] / v_vol['Total_Trips'] * 100).round(1)
            
            fig_v_scatter = px.scatter(
                v_vol, x='Total_Trips', y='On-Time %', size='Total_Trips', color='On-Time %',
                hover_name='VendorName', title='Vendor Volume vs. Reliability',
                color_continuous_scale=[(0, "#ef4444"), (0.8, "#f59e0b"), (1, "#10b981")]
            )
            fig_v_scatter.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color=selected_theme["text"], margin=dict(t=40, b=10, l=10, r=10),
                xaxis_title="Total Trips", yaxis_title="On-Time %"
            )
            v_chart1.plotly_chart(fig_v_scatter, use_container_width=True)

            # 2. Bottom 5 Vendors by Late Count
            v_vol['Late_Count'] = v_vol['Total_Trips'] - v_vol['Ontime_Count']
            bottom_vendors = v_vol.nlargest(5, 'Late_Count')
            
            if bottom_vendors['Late_Count'].sum() > 0:
                fig_v_bar = px.bar(
                    bottom_vendors, x='VendorName', y='Late_Count',
                    text_auto='.0f', title='Vendors with Most Late Arrivals',
                    color_discrete_sequence=['#f97316']
                )
                fig_v_bar.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font_color=selected_theme["text"], margin=dict(t=40, b=10, l=10, r=10),
                    xaxis_title="", yaxis_title="Late Trips"
                )
                v_chart2.plotly_chart(fig_v_bar, use_container_width=True)""",
        """        bi_engine.render_vendor_powerbi_suite(df_vperf_raw, df_vperf_raw_full, df_display, selected_theme, THEME_IS_LIGHT)
        bi_engine.render_new_window_raw_launcher(
            df=clean_dataframe_for_excel(df_vperf_raw, sheet_type="ven_raw"),
            data_dir=DATA_DIR,
            title="All Filtered Vendor Performance Raw Data",
            subtitle=f"Duration: {dur_str_ven} · Zone: {selected_zone} · RO: {selected_ro} · Vendor: {selected_vendor_b}",
            sheet_type="ven_raw",
            excel_writer_fn=write_styled_sheet_to_excel,
            style_fn=style_ui_dataframe,
            theme=selected_theme,
            key_prefix="ven_all_nw",
            file_prefix="Vendor_All_Filtered",
            compact_mode=True,
        )""",
        already_marker="render_vendor_powerbi_suite(",
    )

    code = apply_patch(
        code,
        "Vendor Selected Row -> New-Window Raw Explorer",
        """            st.markdown(f"#### 📄 `{selected_row['VendorName']}` · `{selected_row['Route Path']}` · `{selected_row['Legwise']}` · {selected_vendor_metric or 'All trip metrics'} · {len(filtered_raw_clean):,} trips")
            st.dataframe(style_ui_dataframe(filtered_raw_clean), use_container_width=True, hide_index=True, height=330)
            output_raw = io.BytesIO()
            with pd.ExcelWriter(output_raw, engine='xlsxwriter') as writer:
                write_styled_sheet_to_excel(writer, filtered_raw_clean, 'Focused_Trips', sheet_type='ven_raw')
            st.download_button(
                '📥 Download selected performance records (formatted Excel)', data=output_raw.getvalue(),
                file_name=f"Vendor_Performance_{re.sub(r'[^A-Za-z0-9_-]+', '_', str(selected_row['VendorName']))}_{selected_idx + 1}.xlsx",
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', key='vendor_focused_raw_download'
            )""",
        """            bi_engine.render_new_window_raw_launcher(
                df=filtered_raw_clean,
                data_dir=DATA_DIR,
                title=f"{selected_row['VendorName']} · {selected_row['Route Path']} ({selected_row['Legwise']})",
                subtitle=f"Metric: {selected_vendor_metric or 'All'} · Duration: {dur_str_ven}",
                sheet_type="ven_raw",
                excel_writer_fn=write_styled_sheet_to_excel,
                style_fn=style_ui_dataframe,
                theme=selected_theme,
                key_prefix=f"ven_sel_nw_{selected_idx}",
                file_prefix=f"Vendor_{selected_row['VendorName']}",
            )""",
