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
    .metric-card { background: rgba(255,255,255,0.05); padding: 20px; border-radius: 10px; border-left: 5px solid #0052a5; margin-bottom: 20px; }
    .logistics-header { color: #0052a5; font-weight: bold; border-bottom: 1px solid #333; margin-bottom: 15px; }
    .guidance-note { font-style: italic; color: #aaa; font-size: 0.85rem; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

conn = get_connection()

# --- DATA HELPERS ---
def get_last_odo(unit_name):
    query = "SELECT end_odo FROM logs WHERE vehicle_name = ? ORDER BY id DESC LIMIT 1"
    res = conn.execute(query, (unit_name,)).fetchone()
    return res[0] if res else 0.0

# --- SIDEBAR ---
st.sidebar.title("🇺🇸 MIL-PRO COMMAND")
vehicles = pd.read_sql("SELECT name FROM vehicles", conn)
active_unit = st.sidebar.selectbox("PRIMARY VEHICLE", vehicles['name'] if not vehicles.empty else ["No Vehicles Registered"])
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

# --- INITIALIZE GLOBAL VARIABLES ---
last_odo = get_last_odo(active_unit)
start_odo, end_odo = last_odo, last_odo
miles_pov, airfare, parking, rental_cost, rental_fuel, lodging, meals, reimbursement = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 750.0
current_rate = 0.725

# --- SCREEN 1: DAILY LOG ---
if screen == "DAILY LOG (Standard)":
    st.title("🦅 DAILY MOVEMENT LOG")
    st.markdown("<p class='guidance-note'>Best for single-day local trips (Business, Medical, Charity).</p>", unsafe_allow_html=True)
    trip_cat = st.selectbox("PURPOSE", ["Business", "Medical", "Charity", "Personal"])
    rates = {"Business": 0.725, "Medical": 0.22, "Charity": 0.14, "Personal": 0.0}
    current_rate = rates[trip_cat]
    
    col1, col2 = st.columns(2)
    with col1:
        m_date = st.date_input("DATE", datetime.now())
        start_odo = st.number_input("START ODOMETER", value=last_odo, step=0.1)
        end_odo = st.number_input("END ODOMETER", value=start_odo + 1.0, step=0.1)
        miles_pov = max(0.0, end_odo - start_odo)
    
    with col2:
        st.subheader("EXPENSES")
        lodging = st.number_input("LODGING", value=0.0, step=0.01)
        meals = st.number_input("MEALS", value=0.0, step=0.01)
        reimbursement = st.number_input("REIMBURSEMENT", value=0.0, step=0.01)

# --- SCREEN 2: TACTICAL SORTIE ---
else:
    st.title("⚔️ TACTICAL SORTIE LOG (MILITARY)")
    st.markdown("<p class='guidance-note'>Best for multi-day Drill/AT. Check all boxes that apply to your travel to see all entry fields.</p>", unsafe_allow_html=True)
    
    col_dates = st.columns(2)
    with col_dates[0]: start_date = st.date_input("MISSION START", datetime.now())
    with col_dates[1]: end_date = st.date_input("MISSION END", datetime.now() + timedelta(days=2))
    m_date = f"{start_date} to {end_date}"

    st.subheader("🛠️ MISSION LOGISTICS")
    col_check1, col_check2, col_check3 = st.columns(3)
    with col_check1: use_pov = st.checkbox("POV Driven", value=True, help="Check this if you drove your own vehicle at any point (to drill or to airport).")
    with col_check2: use_flight = st.checkbox("Commercial Flight", help="Check this to enter ticket costs and airport parking.")
    with col_check3: use_rental = st.checkbox("Rental Car", help="Check this to enter rental contract costs and fuel receipts.")

    st.divider()
    col_left, col_right = st.columns(2)

    with col_left:
        if use_pov:
            st.markdown("<div class='logistics-header'>🚗 POV MILEAGE</div>", unsafe_allow_html=True)
            st.markdown("<p class='guidance-note'>Automatically fills with your last known odometer reading.</p>", unsafe_allow_html=True)
            st.caption(f"Last Odometer: {last_odo}")
            start_odo = st.number_input("START ODOMETER", value=last_odo, key="mil_start", step=0.1)
            end_odo = st.number_input("END ODOMETER", value=start_odo + 1.0, key="mil_end", step=0.1)
            miles_pov = max(0.0, end_odo - start_odo)
        
        if use_flight:
            st.markdown("<div class='logistics-header'>✈️ FLIGHT DETAILS</div>", unsafe_allow_html=True)
            st.markdown("<p class='guidance-note'>Enter costs for airfare and airport long-term parking.</p>", unsafe_allow_html=True)
            airfare = st.number_input("AIRFARE TICKET ($)", min_value=0.0, step=0.01)
            parking = st.number_input("AIRPORT PARKING ($)", min_value=0.0, step=0.01)

    with col_right:
        if use_rental:
            st.markdown("<div class='logistics-header'>🚘 RENTAL FLEET</div>", unsafe_allow_html=True)
            st.markdown("<p class='guidance-note'>Note: IRS rules allow actual fuel costs for rentals instead of mileage.</p>", unsafe_allow_html=True)
            rental_cost = st.number_input("RENTAL CONTRACT ($)", min_value=0.0, step=0.01)
            rental_fuel = st.number_input("RENTAL FUEL RECEIPTS ($)", min_value=0.0, step=0.01)

        st.markdown("<div class='logistics-header'>💰 PER DIEM & REIMBURSEMENT</div>", unsafe_allow_html=True)
        st.markdown("<p class='guidance-note'>Defaults to $750 (current IDT cap). Total deduction is calculated after this is subtracted.</p>", unsafe_allow_html=True)
        lodging = st.number_input("TOTAL LODGING (UNREIMBURSED)", value=0.0, step=0.01)
        meals = st.number_input("TOTAL MEAL COSTS", value=0.0, step=0.01)
        reimbursement = st.number_input("GOV REIMBURSEMENT", value=750.0, step=0.01)

# --- CALC ENGINE ---
subtotal = (miles_pov * current_rate) + (meals * 0.50) + lodging + airfare + parking + rental_cost + rental_fuel
final_deduction = max(0.0, subtotal - reimbursement)

st.divider()

# --- DISPLAY ---
st.markdown(f"""
    <div class="metric-card">
        <h3 style='color:white;'>Projected Net Deduction: ${final_deduction:,.2f}</h3>
        <p style='color:#ccc;'>Summary: ${miles_pov*current_rate:.2f} Mileage | ${(meals*0.50)+lodging+airfare+parking+rental_cost+rental_fuel:.2f} Other Costs | -${reimbursement} Offset</p>
    </div>
    """, unsafe_allow_html=True)

if st.button("💾 LOCK MISSION LOG", use_container_width=True):
    save_start = start_odo if (screen == "DAILY LOG (Standard)" or use_pov) else 0.0
    save_end = end_odo if (screen == "DAILY LOG (Standard)" or use_pov) else last_odo
    
    conn.execute('''INSERT INTO logs (date, vehicle_name, start_odo, end_odo, total_deduction, reimbursement) 
                    VALUES (?, ?, ?, ?, ?, ?)''', 
                 (str(m_date), active_unit, save_start, save_end, final_deduction, reimbursement))
    conn.commit()
    st.markdown("<div class='success-banner'>MISSION SECURED. Odometer chain updated for next sortie.</div>", unsafe_allow_html=True)

# --- EXPORT ---
st.divider()
st.subheader("📊 EXECUTIVE TAX ARCHIVE (2026)")
report_df = pd.read_sql("SELECT date as 'Mission Window', vehicle_name as 'Unit', CASE WHEN start_odo > 0 THEN (end_odo - start_odo) ELSE end_odo END as 'Qty/Miles', total_deduction as 'Net Deduction ($)' FROM logs", conn)
st.dataframe(report_df, use_container_width=True)
st.download_button("📥 DOWNLOAD ACCOUNTANT HAND-OFF (.CSV)", data=report_df.to_csv(index=False).encode('utf-8'), file_name="2026_Tax_Export.csv", mime="text/csv")

if st.button("🟥 EMERGENCY REFRESH", type="primary"):
    st.rerun()
