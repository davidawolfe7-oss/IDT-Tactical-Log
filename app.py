import streamlit as st
import pandas as pd
from database import init_db, get_connection
from datetime import datetime

# Initialize Database & State
init_db()

# --- HIGH-CONTRAST NIGHT OPS UI ---
st.set_page_config(page_title="Mil-Pro Command", layout="wide", page_icon="🇺🇸")

st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(rgba(14, 17, 23, 0.85), rgba(14, 17, 23, 0.85)),
                    url('https://upload.wikimedia.org/wikipedia/en/a/a4/Flag_of_the_United_States.svg');
        background-size: cover; background-position: center; background-attachment: fixed;
    }
    [data-testid="stSidebar"] { background-color: #111 !important; border-right: 1px solid #333; }
    .stButton>button { background-color: #cc0000; color: white; border: 1px solid #ff0000; font-weight: bold; width: 100%; }
    .success-banner { padding: 20px; background: rgba(0, 50, 0, 0.8); border: 2px solid #00ff00; border-radius: 10px; color: #00ff00; text-align: center; font-weight: bold; }
    .metric-card { background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px; border-left: 4px solid #0052a5; }
    </style>
    """, unsafe_allow_html=True)

conn = get_connection()

# --- DATA HELPERS ---
def get_last_odo(unit_name):
    query = "SELECT end_odo FROM logs WHERE vehicle_name = ? ORDER BY id DESC LIMIT 1"
    res = conn.execute(query, (unit_name,)).fetchone()
    return res[0] if res else 0.0

# --- SIDEBAR: UNIT PERSISTENCE ---
st.sidebar.title("🇺🇸 MIL-PRO COMMAND")
vehicles = pd.read_sql("SELECT name FROM vehicles", conn)
active_unit = st.sidebar.selectbox("PRIMARY VEHICLE", vehicles['name'] if not vehicles.empty else ["No Vehicles Registered"])

with st.sidebar.expander("➕ REGISTER NEW VEHICLE"):
    v_name = st.text_input("Unit ID (e.g., Black Tahoe)")
    v_mpg = st.number_input("Est. MPG", value=18.0)
    if st.button("SAVE UNIT"):
        if v_name:
            try:
                conn.execute("INSERT INTO vehicles (name, mpg) VALUES (?, ?)", (v_name, v_mpg))
                conn.commit()
                st.rerun()
            except: st.sidebar.error("Unit ID already exists.")

# --- MAIN INTERFACE ---
st.title("TACTICAL MOVEMENT & EXPENSE LOG")

# LOGIC: UNIVERSAL TRIP LOGGING
trip_cat = st.selectbox("TRIP CATEGORY", ["Business / Military", "Medical", "Charity", "Personal"])
t_mode = st.radio("TRAVEL MODE", ["POV (Personal Vehicle)", "Commercial Flight", "Rental Fleet"], horizontal=True)

# 2026 IRS RATES
rates = {"Business / Military": 0.725, "Medical": 0.22, "Charity": 0.14, "Personal": 0.0}
current_rate = rates[trip_cat]

st.divider()
col1, col2 = st.columns(2)

with col1:
    m_date = st.date_input("MISSION DATE", datetime.now())
    
    if t_mode == "POV (Personal Vehicle)":
        last_odo = get_last_odo(active_unit)
        st.caption(f"Last Odometer for {active_unit}: {last_odo}")
        # SEQUENTIAL AUTO-FILL
        start_odo = st.number_input("START ODOMETER", value=last_odo, step=0.1)
        end_odo = st.number_input("END ODOMETER", value=start_odo + 1.0, step=0.1)
        miles = max(0.0, end_odo - start_odo)
    
    elif t_mode == "Commercial Flight":
        airfare = st.number_input("AIRFARE TICKET ($)", min_value=0.0, step=0.01)
        airport_parking = st.number_input("AIRPORT PARKING ($)", min_value=0.0, step=0.01)
        miles = st.number_input("DRIVE TO/FROM AIRPORT (MILES)", min_value=0.0, step=0.1)
        
    else: # Rental Fleet
        rental_cost = st.number_input("RENTAL CONTRACT ($)", min_value=0.0, step=0.01)
        rental_fuel = st.number_input("RENTAL FUEL RECEIPTS ($)", min_value=0.0, step=0.01)
        miles = 0.0 # Rental uses actual fuel costs

with col2:
    st.subheader("ADDITIONAL EXPENSES")
    lodging = st.number_input("LODGING (UNREIMBURSED)", min_value=0.0, step=0.01)
    meals = st.number_input("TOTAL MEAL COSTS ($)", min_value=0.0, step=0.01)
    reimbursement = st.number_input("REIMBURSEMENT / STIPEND", min_value=0.0, step=0.01)

# --- THE CALCULATION ENGINE ---
mileage_val = miles * current_rate
meal_val = meals * 0.50 # IRS 50% Rule

if t_mode == "POV (Personal Vehicle)":
    subtotal = mileage_val + lodging + meal_val
elif t_mode == "Commercial Flight":
    subtotal = airfare + airport_parking + mileage_val + lodging + meal_val
else: # Rental
    subtotal = rental_cost + rental_fuel + lodging + meal_val

final_deduction = max(0.0, subtotal - reimbursement)

st.divider()

# --- DISPLAY & SAVE ---
st.markdown(f"""
    <div class="metric-card">
        <h3>Calculated Net Deduction: ${final_deduction:,.2f}</h3>
        <p>Purpose: {trip_cat} | Rate: ${current_rate}/mile</p>
    </div>
    """, unsafe_allow_html=True)

if st.button("💾 SAVE LOG ENTRY", use_container_width=True):
    # Save Odometer Chain: Use end_odo for POV, otherwise keep previous chain
    save_odo = end_odo if t_mode == "POV (Personal Vehicle)" else last_odo
    
    conn.execute('''INSERT INTO logs (date, vehicle_name, start_odo, end_odo, total_deduction, reimbursement) 
                    VALUES (?, ?, ?, ?, ?, ?)''', 
                 (str(m_date), active_unit, start_odo if t_mode == "POV (Personal Vehicle)" else 0, save_odo, final_deduction, reimbursement))
    conn.commit()
    st.markdown(f"<div class='success-banner'>SUCCESS: ${final_deduction:,.2f} LOGGED. ODOMETER CHAIN UPDATED.</div>", unsafe_allow_html=True)

# --- ACCOUNTANT-READY EXPORT ---
st.divider()
st.subheader("📊 EXECUTIVE REPORT (ACCOUNTANT HAND-OFF)")

export_query = """
SELECT 
    date as 'Date',
    vehicle_name as 'Unit',
    CASE 
        WHEN start_odo > 0 THEN (end_odo - start_odo)
        ELSE end_odo 
    END as 'Qty/Miles',
    total_deduction as 'Net Deduction ($)'
FROM logs
"""
report_df = pd.read_sql(export_query, conn)
st.dataframe(report_df, use_container_width=True)

csv = report_df.to_csv(index=False).encode('utf-8')
col_dl, col_refresh = st.columns([2,1])

with col_dl:
    st.download_button("📥 DOWNLOAD CSV FOR TAX PREP", data=csv, file_name="2026_Tax_Export.csv", mime="text/csv")

with col_refresh:
    if st.button("🟥 EMERGENCY REFRESH", type="primary"):
        st.rerun()
