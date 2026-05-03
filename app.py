import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
import time

# --- ARCHITECT CONFIG ---
st.set_page_config(page_title="Mil-Pro Command", page_icon="🪖", layout="wide")
st.markdown("""<style> .main { background-color: #0e1117; color: #e0e0e0; } </style>""", unsafe_allow_name=True)

# --- 2026 TACTICAL RATES ---
RATES = {"IDT/Business": 0.725, "Medical": 0.22, "Charity": 0.14, "Personal": 0.00}

# --- CONNECTION ---
url, key = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- SESSION STATE INITIALIZATION ---
if 'user' not in st.session_state: st.session_state.user = None
if 'active_vehicle' not in st.session_state: st.session_state.active_vehicle = "None"
if 'gps_active' not in st.session_state: st.session_state.gps_active = False

# --- AUTH MODULE ---
def auth_gate():
    if not st.session_state.user:
        st.title("🪖 Mil-Pro Command: Night Ops")
        t1, t2 = st.tabs(["Inbound", "Registration"])
        with t1:
            e, p = st.text_input("Email"), st.text_input("Password", type="password")
            if st.button("Login"):
                res = supabase.auth.sign_in_with_password({"email":e,"password":p})
                st.session_state.user = res.user
                st.rerun()
        st.stop()

auth_gate()
user_id = st.session_state.user.id

# --- SIDEBAR: FLEET COMMAND ---
st.sidebar.title("🛠️ Fleet Command")
try:
    v_query = supabase.table("vehicles").select("*").eq("user_id", user_id).execute()
    v_list = [v['name'] for v in v_query.data] if v_query.data else []
    
    if v_list:
        st.session_state.active_vehicle = st.sidebar.selectbox("Active Primary Unit", v_list)
    else:
        st.sidebar.warning("No vehicles in Garage.")
except: pass

nav = st.sidebar.radio("Sectors", ["Mission Log", "IDT Tactical", "The Garage", "Executive Reports"])

# --- SECTOR: MISSION LOG ---
if nav == "Mission Log":
    st.header(f"📍 Daily Sortie: {st.session_state.active_vehicle}")
    
    # GAP DETECTION LOGIC
    try:
        last_log = supabase.table("logs").select("end_odo").eq("user_id", user_id).order("created_at", desc=True).limit(1).execute()
        last_odo = last_log.data[0]['end_odo'] if last_log.data else 0
    except: last_odo = 0

    with st.form("sortie_form"):
        c1, c2 = st.columns(2)
        with c1:
            date = st.date_input("Date", datetime.date.today())
            cat = st.selectbox("Category", list(RATES.keys()))
            cur_start = st.number_input("Start Odometer", value=float(last_odo))
        with c2:
            cur_end = st.number_input("End Odometer", min_value=float(cur_start))
            dest = st.text_input("Destination")
        
        if cur_start > last_odo and last_odo != 0:
            st.warning(f"⚠️ {int(cur_start - last_odo)} mile gap detected. Record as {cat}?")

        if st.form_submit_button("LOG MISSION"):
            dist = cur_end - cur_start
            earned = dist * RATES[cat]
            supabase.table("logs").insert({
                "user_id": user_id, "date": str(date), "miles": dist,
                "destination": dest, "purpose": cat, "vehicle_name": st.session_state.active_vehicle,
                "start_odo": cur_start, "end_odo": cur_end, "total_deduction": earned
            }).execute()
            st.success(f"✅ Logged! You earned ${earned:,.2f} in tax deductions.")
            st.balloons()

# --- SECTOR: IDT TACTICAL ---
elif nav == "IDT Tactical":
    st.header("✈️ Unreimbursed Expense Calculator")
    st.info("Form 2106 Logic: (Expenses - $750 Cap) = Net Deduction")
    
    with st.form("idt_form"):
        mode = st.radio("Travel Mode", ["POV (Personal)", "Commercial Flight", "Rental Fleet"])
        miles_to_airport = st.number_input("Miles to/from Airport (Home Leg)", min_value=0.0)
        
        col1, col2 = st.columns(2)
        with col1:
            lodging = st.number_input("Lodging (Unreimbursed)", min_value=0.0)
            tolls = st.number_input("Tolls & Parking", min_value=0.0)
            fuel = st.number_input("Fuel/Gas (Rentals only)", min_value=0.0)
        with col2:
            transit = st.number_input("Mass Transit (Uber/Taxi)", min_value=0.0)
            incidentals = st.number_input("Laundry/Incidental", min_value=0.0)
            reimb = st.number_input("Government Reimbursement", value=750.0)

        if st.form_submit_button("CALCULATE NET DEDUCTION"):
            total_exp = lodging + tolls + transit + fuel + incidentals + (miles_to_airport * 0.725)
            net = max(0.0, total_exp - reimb)
            st.metric("Total Above-the-Line Deduction", f"${net:,.2f}")
            st.success("Data ready for Schedule 1 (Form 1040)")

# --- SECTOR: THE GARAGE ---
elif nav == "The Garage":
    st.header("🚘 Database Garage")
    with st.form("garage_form"):
        vname = st.text_input("Vehicle Name (Unique)")
        vmpg = st.number_input("Est. MPG", min_value=1.0)
        if st.form_submit_button("Register Vehicle"):
            try:
                supabase.table("vehicles").insert({"user_id":user_id, "name":vname, "mpg":vmpg}).execute()
                st.success(f"{vname} registered to fleet.")
            except: st.error("Duplicate Vehicle Detected. Change Name.")

# --- SECTOR: EXECUTIVE REPORTS ---
elif nav == "Executive Reports":
    st.button("🔴 RETURN TO COMMAND", on_click=lambda: setattr(st.session_state, 'page', 'Mission Log'))
    st.header("📊 Accountant-Ready Export")
    res = supabase.table("logs").select("date,purpose,miles,destination,total_deduction").eq("user_id", user_id).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 Export .XLSX", df.to_csv().encode('utf-8'), "2026_Tax_Log.csv")
