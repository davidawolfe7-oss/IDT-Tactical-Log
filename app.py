import streamlit as st
import pandas as pd
from database import init_db, get_connection
from datetime import datetime, timedelta

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
    .stButton>button { background-color: #cc0000; color: white; border: 1px solid #ff0000; font-weight: bold; width: 100%; height: 3em; }
    .success-banner { padding: 20px; background: rgba(0, 50, 0, 0.9); border: 2px solid #00ff00; border-radius: 10px; color: #00ff00; text-align: center; font-weight: bold; }
    .metric-card { background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px; border-left: 4px solid #0052a5; margin-bottom: 10px; }
    .section-header { border-bottom: 2px solid #cc0000; padding-bottom: 5px; margin-bottom: 20px; color: #fff; font-weight: bold; text-transform: uppercase; }
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

# --- NAVIGATION SCREENS ---
screen = st.sidebar.radio("MISSION TYPE", ["DAILY LOG (Standard)", "TACTICAL SORTIE (Military)"])

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

# --- INITIALIZE GLOBAL LOGIC VARIABLES ---
last_odo = get_last_odo(active_unit)
start_odo = last_odo
end_odo = last_odo
miles = 0.0
airfare = 0.0
parking = 0.0
rental_cost = 0.0
rental_fuel = 0.0
lodging = 0.0
meals = 0.0
reimbursement = 0.0
current_rate = 0.725 # Default

# --- SCREEN 1: DAILY LOG (Business, Medical, Charity, Personal) ---
if screen == "DAILY LOG (Standard)":
    st.title("🦅 DAILY MOVEMENT LOG")
    trip_cat = st.selectbox("PURPOSE", ["Business", "Medical", "Charity", "Personal"])
    rates = {"Business": 0.725, "Medical": 0.22, "Charity": 0.14, "Personal": 0.0}
    current_rate = rates[trip_cat]
    
    col1, col2 = st.columns(2)
    with col1:
        m_date = st.date_input("DATE", datetime.now())
        st.caption(f"Last Odometer for {active_unit}: {last_odo}")
        start_odo = st.number_input("START ODOMETER", value=last_odo, step=0.1)
        end_odo = st.number_input("END ODOMETER", value=start_odo + 1.0, step=0.1)
        miles = max(0.0, end_odo - start_odo)
    
    with col2:
        st.subheader("EXPENSES")
        lodging = st.number_input("LODGING", value=0.0, step=0.01)
        meals = st.number_input("MEALS", value=0.0, step=0.01)

# --- SCREEN 2: TACTICAL SORTIE (Military Specific) ---
else:
    st.title("⚔️ TACTICAL SORTIE LOG (MILITARY)")
    st.info("Use this for multi-day Drill, AT, or Active Duty travel.")
    
    col_dates = st.columns(2)
    with col_dates[0]:
        start_date = st.date_input("START DATE", datetime.now())
    with col_dates[1]:
        end_date = st.date_input("END DATE", datetime.now() + timedelta(days=2))
    
    m_date = f"{start_date} to {end_date}"
    current_rate = 0.725 # Standard Military Rate

    t_mode = st.radio("TRAVEL SEGMENT", ["POV (Personal Vehicle)", "Commercial Flight", "Rental Fleet"], horizontal=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if t_mode == "POV (Personal Vehicle)":
            st.caption(f"Last Odometer for {active_unit}: {last_odo}")
            start_odo = st.number_input("START ODOMETER", value=last_odo, step=0.1)
            end_odo = st.number_input("END ODOMETER", value=start_odo + 1.0, step=0.1)
            miles = max(0.0, end_odo - start_odo)
        elif t_mode == "Commercial Flight":
            airfare = st.number_input("AIRFARE TICKET ($)", min_value=0.0, step=0.01)
            parking = st.number_input("AIRPORT PARKING ($)", min_value=0.0, step=0.01)
            miles = st.number_input("DRIVE TO/FROM AIRPORT (MILES)", min_value=0.0, step=0.1)
        else: # Rental
            rental_cost = st.number_input("RENTAL CONTRACT ($)", min_value=0.0, step=0.01)
            rental_fuel = st.number_input("RENTAL FUEL RECEIPTS ($)", min_value=0.0, step=0.01)
            miles = 0.0

    with col2:
        st.subheader("MISSION EXPENSES")
        lodging = st.number_input("LODGING (TOTAL UNREIMBURSED)", value=0.0, step=0.01)
        meals = st.number_input("TOTAL MEALS / PER DIEM", value=0.0, step=0.01)
        reimbursement = st.number_input("GOV REIMBURSEMENT (IDT CAP)", value=750.0, step=0.01)

# --- GLOBAL CALCULATION ENGINE ---
mileage_deduction = miles * current_rate
meal_deduction = meals * 0.50
subtotal = mileage_deduction + meal_deduction + lodging + airfare + parking + rental_cost + rental_fuel
final_deduction = max(0.0, subtotal - reimbursement)

st.divider()

# --- DISPLAY & SAVE ---
st.markdown(f"""
    <div class="metric-card">
        <h3>Projected Net Deduction: ${final_deduction:,.2f}</h3>
        <p>Applied Rate: ${current_rate}/mile | Mission: {screen}</p>
    </div>
    """, unsafe_allow_html=True)

if st.button("💾 LOCK LOG ENTRY", use_container_width=True):
    save_start = start_odo if (screen == "DAILY LOG (Standard)" or t_mode == "POV (Personal Vehicle)") else 0.0
    save_end = end_odo if (screen == "DAILY LOG (Standard)" or t_mode == "POV (Personal Vehicle)") else last_odo
    
    conn.execute('''INSERT INTO logs (date, vehicle_name, start_odo, end_odo, total_deduction, reimbursement) 
                    VALUES (?, ?, ?, ?, ?, ?)''', 
                 (str(m_date), active_unit, save_start, save_end, final_deduction, reimbursement))
    conn.commit()
    st.markdown(f"<div class='success-banner'>MISSION SECURED. Deduction of ${final_deduction:,.2f} added to archive.</div>", unsafe_allow_html=True)

# --- ACCOUNTANT REPORT ---
st.divider()
st.subheader("📊 EXECUTIVE TAX ARCHIVE (2026)")
export_query = """
SELECT 
    date as 'Date/Mission Window',
    vehicle_name as 'Unit',
    CASE WHEN start_odo > 0 THEN (end_odo - start_odo) ELSE end_odo END as 'Qty/Miles',
    total_deduction as 'Net Deduction ($)'
FROM logs
"""
report_df = pd.read_sql(export_query, conn)
st.dataframe(report_df, use_container_width=True)

csv = report_df.to_csv(index=False).encode('utf-8')
st.download_button("📥 DOWNLOAD ACCOUNTANT HAND-OFF (.CSV)", data=csv, file_name="2026_Tax_Export.csv", mime="text/csv")

if st.button("🟥 EMERGENCY REFRESH", type="primary"):
    st.rerun()
