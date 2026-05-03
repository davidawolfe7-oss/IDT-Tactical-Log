import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd

# --- SYSTEM CONFIG ---
st.set_page_config(page_title="Mil-Pro Command", layout="wide")

# 2026 IRS TACTICAL RATES
RATES = {"IDT/Business": 0.725, "Medical": 0.205, "Charity": 0.14}

# --- DATABASE INITIALIZATION ---
@st.cache_resource
def init_connection():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception as e:
        st.error(f"FATAL: Secret Key missing or invalid. {e}")
        return None

db = init_connection()

# --- STATE MANAGEMENT ---
if 'user' not in st.session_state: st.session_state.user = None
if 'active_vehicle' not in st.session_state: st.session_state.active_vehicle = "Standard Unit"

# --- AUTH GATE ---
if not st.session_state.user:
    st.title("🪖 Mil-Pro Command: Login")
    with st.form("auth"):
        e, p = st.text_input("Email"), st.text_input("Password", type="password")
        if st.form_submit_button("Authenticate"):
            res = db.auth.sign_in_with_password({"email": e, "password": p})
            st.session_state.user = res.user
            st.rerun()
    st.stop()

uid = st.session_state.user.id

# --- NAVIGATION ---
nav = st.sidebar.radio("Navigation", ["Mission Log", "IDT Tactical", "Fleet Garage", "Reports"])

# --- MISSION LOG SECTOR ---
if nav == "Mission Log":
    st.header(f"📍 Log Mission: {st.session_state.active_vehicle}")
    
    # Logic: Auto-fetch last odometer to prevent gaps
    last_odo = 0.0
    try:
        log_check = db.table("logs").select("end_odo").eq("user_id", uid).order("created_at", desc=True).limit(1).execute()
        if log_check.data: last_odo = float(log_check.data[0]['end_odo'])
    except: pass

    with st.form("log_entry"):
        c1, c2 = st.columns(2)
        with c1:
            date = st.date_input("Mission Date", datetime.date.today())
            start = st.number_input("Start Odometer", value=last_odo)
            cat = st.selectbox("Mission Type", list(RATES.keys()))
        with c2:
            end = st.number_input("End Odometer", min_value=start)
            dest = st.text_input("Destination/Unit")
        
        if st.form_submit_button("Commit to Database"):
            miles = end - start
            deduction = round(miles * RATES[cat], 2)
            db.table("logs").insert({
                "user_id": uid, "date": str(date), "miles": miles,
                "destination": dest, "purpose": cat, "start_odo": start,
                "end_odo": end, "total_deduction": deduction
            }).execute()
            st.success(f"Mission Saved. Deducted: ${deduction}")

# --- IDT TACTICAL SECTOR ---
elif nav == "IDT Tactical":
    st.header("✈️ IDT Unreimbursed Expense Log")
    st.markdown("> **Rule:** Total Expenses - $750 Gov Reimbursement = Net Deduction")
    
    with st.form("idt_calc"):
        air_miles = st.number_input("Miles to/from Airport", value=0.0)
        lodging = st.number_input("Lodging Costs (Out of Pocket)", value=0.0)
        tolls = st.number_input("Tolls & Parking", value=0.0)
        transit = st.number_input("Uber/Taxi/Mass Transit", value=0.0)
        reimb = st.number_input("Gov Travel Reimbursement Received", value=750.0)
        
        if st.form_submit_button("Calculate Final Net"):
            total_raw = lodging + tolls + transit + (air_miles * 0.725)
            final_net = max(0.0, total_raw - reimb)
            st.metric("Net Schedule 1 Deduction", f"${final_net:,.2f}")

# --- FLEET GARAGE SECTOR ---
elif nav == "Fleet Garage":
    st.header("🚘 Fleet Management")
    with st.form("add_v"):
        v_name = st.text_input("Vehicle Name")
        if st.form_submit_button("Add Vehicle"):
            db.table("vehicles").insert({"user_id": uid, "name": v_name}).execute()
            st.success(f"{v_name} added.")

# --- REPORTS SECTOR ---
elif nav == "Reports":
    st.header("📊 Export Data")
    data = db.table("logs").select("*").eq("user_id", uid).execute()
    if data.data:
        df = pd.DataFrame(data.data)
        st.dataframe(df)
        st.download_button("Download .CSV", df.to_csv(index=False), "Tax_Logs_2026.csv")
