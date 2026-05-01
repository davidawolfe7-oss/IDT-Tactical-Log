import streamlit as st
import pandas as pd
from database import init_db, get_connection
from datetime import datetime

# Initialize
init_db()

# --- HIGH-CONTRAST NIGHT OPS STYLING ---
st.set_page_config(page_title="Mil-Pro Command", layout="wide")
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.85), rgba(0, 0, 0, 0.85)), 
                    url('https://www.transparenttextures.com/patterns/dark-matter.png');
        color: #E0E0E0;
    }
    [data-testid="stSidebar"] { background-color: #111 !important; border-right: 1px solid #333; }
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #cc0000;
    }
    .success-box {
        padding: 20px;
        background-color: #002200;
        border: 2px solid #00ff00;
        color: #00ff00;
        text-align: center;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: PERSISTENT GARAGE ---
st.sidebar.title("🦅 MIL-PRO COMMAND")
conn = get_connection()

vehicles = pd.read_sql("SELECT name, mpg FROM vehicles", conn)
active_unit = st.sidebar.selectbox("PRIMARY UNIT", vehicles['name'] if not vehicles.empty else ["No Units Registered"])

# Add Vehicle Section
with st.sidebar.expander("➕ REGISTER NEW VEHICLE"):
    v_name = st.text_input("Unit ID (e.g. Silver Silverado)")
    v_mpg = st.number_input("MPG Estimate", value=18.0)
    if st.button("SAVE UNIT"):
        if v_name and v_name not in vehicles['name'].values:
            conn.execute("INSERT INTO vehicles (name, mpg) VALUES (?, ?)", (v_name, v_mpg))
            conn.commit()
            st.rerun()
        else:
            st.error("Duplicate or Empty Name")

# --- MAIN MISSION DASHBOARD ---
st.header("⚡ MISSION SORTIE LOG")

# Travel Mode Selection - This drives the logic change
t_mode = st.radio("TRAVEL MODE", ["POV (Personal Vehicle)", "COMMERCIAL FLIGHT", "RENTAL FLEET"], horizontal=True)

col1, col2 = st.columns(2)

with col1:
    m_date = st.date_input("MISSION DATE", datetime.now())
    st.subheader("📍 Logistics")
    if t_mode == "POV (Personal Vehicle)":
        start_odo = st.number_input("START ODOMETER", step=0.1)
        end_odo = st.number_input("END ODOMETER", step=0.1)
        miles = max(0.0, end_odo - start_odo)
    elif t_mode == "COMMERCIAL FLIGHT":
        miles = st.number_input("MILES TO/FROM AIRPORT", step=0.1)
        airfare = st.number_input("FLIGHT COST ($)", step=0.01)
        parking = st.number_input("AIRPORT PARKING ($)", step=0.01)
    else: # Rental
        rental_fee = st.number_input("RENTAL COST ($)", step=0.01)
        rental_fuel = st.number_input("RENTAL FUEL/GAS ($)", step=0.01)
        miles = 0 # IRS uses actual costs for rentals, not mileage

with col2:
    st.subheader("💰 Expenses & Per Diem")
    lodging = st.number_input("LODGING (UNREIMBURSED)", step=0.01)
    meals = st.number_input("TOTAL MEAL COSTS ($)", step=0.01)
    misc = st.number_input("TOLLS / TAXIS / LAUNDRY", step=0.01)
    reimbursement = st.number_input("GOV REIMBURSEMENT (IDT CAP)", value=750.0)

# --- REFRESHED CALCULATION ENGINE (IRS 2026) ---
# Logic: POV gets mileage. Flight gets tickets + parking + airport miles. 
# Meals are limited to 50% per IRS rules.
deduction_subtotal = 0

if t_mode == "POV (Personal Vehicle)":
    deduction_subtotal += (miles * 0.725)
elif t_mode == "COMMERCIAL FLIGHT":
    deduction_subtotal += (miles * 0.725) + airfare + parking
else: # Rental
    deduction_subtotal += rental_fee + rental_fuel

# Add shared costs
deduction_subtotal += lodging + (meals * 0.50) + misc
final_net = max(0.0, deduction_subtotal - reimbursement)

st.divider()

if st.button("💾 LOCK MISSION LOG", use_container_width=True):
    # Save to DB
    conn.execute('''INSERT INTO logs (date, vehicle_name, start_odo, end_odo, total_deduction, reimbursement) 
                    VALUES (?, ?, ?, ?, ?, ?)''', 
                 (str(m_date), active_unit, 0, miles, final_net, reimbursement))
    conn.commit()
    st.markdown(f"<div class='success-box'>MISSION SECURED: ${final_net:,.2f} ADDED TO SCHEDULE 1 DEDUCTIONS</div>", unsafe_allow_html=True)

# --- ACCOUNTANT READY VIEW ---
st.subheader("📊 EXECUTIVE REPORT (2026 TAX YEAR)")
raw_logs = pd.read_sql("SELECT date, vehicle_name, end_odo as miles, total_deduction FROM logs", conn)
st.dataframe(raw_logs, use_container_width=True)

if st.button("🟥 EMERGENCY RETURN / REFRESH", type="primary"):
    st.rerun()
