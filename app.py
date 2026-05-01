import streamlit as st
import pandas as pd
from database import init_db, get_connection
from datetime import datetime

# Initialize DB on Startup
init_db()

# --- THEME & STYLING ---
st.set_page_config(page_title="IDT Tactical Log", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0E1117; color: white; }
    .stButton>button { background-color: #cc0000; color: white; width: 100%; border-radius: 5px; }
    .success-box { padding: 20px; background-color: #004d00; border-radius: 10px; border: 1px solid #00ff00; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: FLEET MANAGEMENT ---
st.sidebar.title("🇺🇸 Fleet Command")
conn = get_connection()

with st.sidebar.expander("Add New Vehicle"):
    new_name = st.text_input("Unit Name/ID")
    new_mpg = st.number_input("MPG", min_value=1.0, value=20.0)
    if st.button("Register Vehicle"):
        try:
            conn.execute("INSERT INTO vehicles (name, mpg) VALUES (?, ?)", (new_name, new_mpg))
            conn.commit()
            st.success(f"{new_name} added!")
        except:
            st.error("Duplicate Unit Name Detected. Use a unique ID.")

# Persistent Vehicle Selection
vehicles_df = pd.read_sql("SELECT name FROM vehicles", conn)
active_unit = st.sidebar.selectbox("Set Primary Unit", vehicles_df['name'] if not vehicles_df.empty else ["None"])

# --- MISSION LOG ---
st.title("Mission Sortie Entry")
col1, col2 = st.columns(2)

with col1:
    mission_date = st.date_input("Mission Date", datetime.now())
    start_odo = st.number_input("Start Odometer", step=0.1)
    
    # GAP DETECTION LOGIC
    last_entry = pd.read_sql(f"SELECT end_odo FROM logs WHERE vehicle_name='{active_unit}' ORDER BY id DESC LIMIT 1", conn)
    if not last_entry.empty:
        prev_end = last_entry['end_odo'].iloc[0]
        if start_odo > prev_end:
            gap = start_odo - prev_end
            st.warning(f"⚠️ {gap} mile gap detected since last mission.")
            gap_cat = st.selectbox("Assign Gap To:", ["Personal", "Business", "Medical", "Charity"])
        else:
            gap_cat = "None"

with col2:
    end_odo = st.number_input("End Odometer", step=0.1)
    travel_mode = st.selectbox("Travel Mode", ["POV", "Flight", "Rental"])
    reimbursement = st.number_input("Gov Reimbursement ($)", value=750.0)

# --- IRS CALCULATION ---
irs_rate = 0.725 # 2026 Business Rate
net_miles = end_odo - start_odo
gross_deduction = net_miles * irs_rate
final_deduction = max(0, gross_deduction - reimbursement)

if st.button("🚀 LOG MISSION"):
    conn.execute('''INSERT INTO logs (date, vehicle_name, start_odo, end_odo, gap_category, total_deduction, reimbursement) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                 (mission_date, active_unit, start_odo, end_odo, "Business", final_deduction, reimbursement))
    conn.commit()
    st.markdown(f"""<div class='success-box'>MISSION SECURED: You just earned <b>${final_deduction:,.2f}</b> in net deductions.</div>""", unsafe_allow_html=True)

# --- EXPORT & THE NAV TRAP FIX ---
st.divider()
st.subheader("Executive Export")
if st.button("🟥 RETURN TO DASHBOARD (Emergency Bypass)", type="primary"):
    st.rerun()

all_logs = pd.read_sql("SELECT date, vehicle_name, (end_odo - start_odo) as miles, total_deduction FROM logs", conn)
st.table(all_logs)

# CSV Export for Accountant
csv = all_logs.to_csv(index=False).encode('utf-8')
st.download_button("📥 Download Excel/Numbers File", data=csv, file_name="2026_Tax_Export.csv", mime="text/csv")