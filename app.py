import streamlit as st
import pandas as pd
from database import init_db, get_connection
from datetime import datetime

# Initialize Database
init_db()

# --- THEME & STYLING (Including American Flag) ---
st.set_page_config(page_title="Mil-Pro Command", layout="wide", page_icon="🇺🇸")
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(rgba(14, 17, 23, 0.8), rgba(14, 17, 23, 0.8)),
                    url('https://upload.wikimedia.org/wikipedia/en/a/a4/Flag_of_the_United_States.svg');
        background-size: cover; background-position: center; background-attachment: fixed;
    }
    .stNumberInput, .stSelectbox, .stDateInput { background: rgba(255,255,255,0.05) !important; }
    .success-banner { padding: 15px; background: #002200; border: 1px solid #00ff00; border-radius: 5px; color: #00ff00; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

conn = get_connection()

# --- SIDEBAR: UNIT PERSISTENCE ---
st.sidebar.title("🇺🇸 MIL-PRO COMMAND")
vehicles = pd.read_sql("SELECT name FROM vehicles", conn)
active_unit = st.sidebar.selectbox("ACTIVE VEHICLE", vehicles['name'] if not vehicles.empty else ["No Vehicles Registered"])

# --- AUTOMATED ODOMETER LOGIC ---
def get_last_odo(unit_name):
    query = "SELECT end_odo FROM logs WHERE vehicle_name = ? ORDER BY id DESC LIMIT 1"
    res = conn.execute(query, (unit_name,)).fetchone()
    return res[0] if res else 0.0

# --- MAIN UI ---
st.title("TACTICAL MOVEMENT & EXPENSE LOG")

trip_cat = st.selectbox("TRIP PURPOSE", ["Business / Military", "Medical", "Charity", "Personal"])
t_mode = st.radio("TRAVEL SEGMENT", ["POV (Personal Vehicle)", "Commercial Flight", "Rental Car / Fleet"], horizontal=True)

# 2026 IRS Rates
rates = {"Business / Military": 0.725, "Medical": 0.22, "Charity": 0.14, "Personal": 0.0}
current_rate = rates[trip_cat]

st.divider()
col1, col2 = st.columns(2)

# --- SEGMENTED ENTRY LOGIC ---
with col1:
    m_date = st.date_input("DATE", datetime.now())
    
    if t_mode == "POV (Personal Vehicle)":
        last_odo = get_last_odo(active_unit)
        st.info(f"Last reported Odometer for {active_unit}: {last_odo}")
        # AUTO-UPDATE START ODO
        start_odo = st.number_input("START ODOMETER", value=last_odo, step=0.1)
        end_odo = st.number_input("END ODOMETER", value=start_odo + 1.0, step=0.1)
        net_miles = max(0.0, end_odo - start_odo)
        st.metric("Segment Miles", f"{net_miles:.1f}")
        
    elif t_mode == "Commercial Flight":
        airfare = st.number_input("AIRFARE COST ($)", min_value=0.0, step=0.01)
        airport_parking = st.number_input("AIRPORT PARKING ($)", min_value=0.0, step=0.01)
        # Separate mileage for driving to the airport
        airport_miles = st.number_input("DRIVE TO/FROM AIRPORT (TOTAL MILES)", min_value=0.0, step=0.1)
        net_miles = airport_miles # Only the miles to the airport get the mileage rate
        
    elif t_mode == "Rental Car / Fleet":
        rental_cost = st.number_input("RENTAL CONTRACT COST ($)", min_value=0.0, step=0.01)
        rental_fuel = st.number_input("RENTAL FUEL RECEIPTS ($)", min_value=0.0, step=0.01)
        net_miles = 0.0 # Renters deduct actual fuel, not mileage

with col2:
    st.subheader("ADDITIONAL EXPENSES")
    lodging = st.number_input("LODGING", min_value=0.0, step=0.01)
    meals = st.number_input("TOTAL MEALS / PER DIEM", min_value=0.0, step=0.01)
    reimbursement = st.number_input("UNIT REIMBURSEMENT (IDT CAP)", value=0.0, step=0.01)

# --- THE CALCULATION ENGINE ---
mileage_cash = net_miles * current_rate
meal_cash = meals * 0.50 # IRS 50% Rule

if t_mode == "POV (Personal Vehicle)":
    subtotal = mileage_cash + lodging + meal_cash
elif t_mode == "Commercial Flight":
    subtotal = airfare + airport_parking + mileage_cash + lodging + meal_cash
else: # Rental
    subtotal = rental_cost + rental_fuel + lodging + meal_cash

final_deduction = max(0.0, subtotal - reimbursement)

st.divider()

# --- DISPLAY & SAVE ---
st.subheader(f"Calculated Deduction: ${final_deduction:,.2f}")

if st.button("💾 SAVE LOG ENTRY", use_container_width=True):
    # Determine what to save as "end_odo" to maintain the chain
    # If POV, we save the end_odo. If others, we keep the odometer where it was.
    save_odo = end_odo if t_mode == "POV (Personal Vehicle)" else last_odo
    
    conn.execute('''INSERT INTO logs (date, vehicle_name, start_odo, end_odo, total_deduction, reimbursement) 
                    VALUES (?, ?, ?, ?, ?, ?)''', 
                 (str(m_date), active_unit, start_odo if t_mode == "POV" else 0, save_odo, final_deduction, reimbursement))
    conn.commit()
    st.markdown(f"<div class='success-banner'>SUCCESS: ${final_deduction:,.2f} logged for {trip_cat}. Start odometer for next trip updated to {save_odo}.</div>", unsafe_allow_html=True)

# --- REFRESHED EXPORT ---
st.subheader("ACCOUNTANT-READY EXPORT")
all_logs = pd.read_sql("SELECT date, vehicle_name, end_odo as 'Current Odo', total_deduction as 'Deduction ($)' FROM logs", conn)
st.dataframe(all_logs, use_container_width=True)

if st.button("🟥 EMERGENCY REFRESH / CLEAR NAV TRAP", type="primary"):
    st.rerun()
