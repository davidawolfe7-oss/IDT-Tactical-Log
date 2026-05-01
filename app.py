import streamlit as st
import pandas as pd
from database import init_db, get_connection
from datetime import datetime

# Initialize Database
init_db()

# --- NIGHT OPS UI WITH AMERICAN FLAG BACKGROUND ---
st.set_page_config(page_title="Mil-Pro Command", layout="wide", page_icon="🇺🇸")

st.markdown("""
    <style>
    .stApp {
        background: 
            linear-gradient(rgba(14, 17, 23, 0.85), rgba(14, 17, 23, 0.85)),
            url('https://upload.wikimedia.org/wikipedia/en/a/a4/Flag_of_the_United_States.svg');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        color: #FFFFFF;
    }
    [data-testid="stHeader"] { background: rgba(0,0,0,0); }
    .stButton>button { 
        background-color: #cc0000; 
        color: white; 
        border: 1px solid #ff0000;
        font-weight: bold;
    }
    .metric-container {
        background: rgba(255, 255, 255, 0.1);
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #0052a5;
        margin-bottom: 20px;
    }
    h1, h2, h3 { color: #FFFFFF !important; text-shadow: 2px 2px 4px #000; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: FLEET & PERSISTENT GARAGE ---
st.sidebar.title("🇺🇸 MIL-PRO COMMAND")
conn = get_connection()

vehicles = pd.read_sql("SELECT name, mpg FROM vehicles", conn)
active_unit = st.sidebar.selectbox("PRIMARY VEHICLE", vehicles['name'] if not vehicles.empty else ["No Vehicles Found"])

with st.sidebar.expander("➕ REGISTER NEW VEHICLE"):
    new_v = st.text_input("Vehicle Name (e.g., F-150)")
    new_mpg = st.number_input("MPG", value=18.0)
    if st.button("ADD TO GARAGE"):
        if new_v:
            try:
                conn.execute("INSERT INTO vehicles (name, mpg) VALUES (?, ?)", (new_v, new_mpg))
                conn.commit()
                st.rerun()
            except: st.error("Name already exists.")

# --- MAIN INTERFACE ---
st.title("TACTICAL MOVEMENT & EXPENSE LOG")

# LOGIC: TRIP CATEGORY & RATES
col_cat, col_mode = st.columns(2)
with col_cat:
    trip_cat = st.selectbox("TRIP CATEGORY", ["Business / Military", "Medical", "Charity", "Personal / Commute"])
with col_mode:
    t_mode = st.radio("TRAVEL MODE", ["POV (Personal)", "Commercial Flight", "Rental Fleet"], horizontal=True)

# IRS 2026 RATES ENGINE
rates = {"Business / Military": 0.725, "Medical": 0.22, "Charity": 0.14, "Personal / Commute": 0.0}
current_rate = rates[trip_cat]

st.divider()

col1, col2 = st.columns(2)

with col1:
    m_date = st.date_input("DATE", datetime.now())
    if t_mode == "POV (Personal)":
        start_odo = st.number_input("START ODOMETER", step=0.1)
        end_odo = st.number_input("END ODOMETER", step=0.1)
        miles = max(0.0, end_odo - start_odo)
        
        # INTERACTIVE GAP DETECTION
        last_log = pd.read_sql(f"SELECT end_odo FROM logs WHERE vehicle_name='{active_unit}' ORDER BY id DESC LIMIT 1", conn)
        if not last_log.empty and start_odo > last_log['end_odo'].iloc[0]:
            gap = start_odo - last_log['end_odo'].iloc[0]
            st.warning(f"⚠️ {gap} MILE GAP DETECTED. Miles will be flagged as Personal.")
    else:
        miles = st.number_input("TOTAL MILES (TO/FROM HUB)", step=0.1)
        flight_cost = st.number_input("TICKET / RENTAL COST ($)", value=0.0)

with col2:
    st.subheader("EXPENSES")
    lodging = st.number_input("LODGING", value=0.0)
    meals = st.number_input("MEALS (TOTAL)", value=0.0)
    reimbursement = st.number_input("REIMBURSEMENT / STIPEND", value=0.0)

# --- THE CALCULATION ENGINE ---
mileage_deduction = miles * current_rate
meal_deduction = meals * 0.50 # IRS 50% Limit
subtotal = mileage_deduction + meal_deduction + lodging
if t_mode != "POV (Personal)":
    subtotal += flight_cost

final_deduction = max(0.0, subtotal - reimbursement)

# --- SUCCESS BOX & SAVE ---
st.markdown(f"""
    <div class="metric-container">
        <h3>Estimated Deduction: ${final_deduction:,.2f}</h3>
        <p>Rate Applied: ${current_rate}/mile | Category: {trip_cat}</p>
    </div>
    """, unsafe_allow_html=True)

if st.button("💾 SAVE LOG ENTRY", use_container_width=True):
    conn.execute('''INSERT INTO logs (date, vehicle_name, start_odo, end_odo, total_deduction, reimbursement) 
                    VALUES (?, ?, ?, ?, ?, ?)''', 
                 (str(m_date), active_unit, 0 if t_mode != "POV (Personal)" else start_odo, miles, final_deduction, reimbursement))
    conn.commit()
    st.success("Entry logged successfully.")

# --- EXECUTIVE EXPORT ---
st.divider()
st.subheader("ACCOUNTANT-READY DATA")
all_data = pd.read_sql("SELECT date, vehicle_name, end_odo as miles, total_deduction as deduction FROM logs", conn)
st.dataframe(all_data, use_container_width=True)

if st.button("🟥 EMERGENCY REFRESH (BYPASS NAV TRAP)", type="primary"):
    st.rerun()
