import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd

# --- 1. ARCHITECTURAL UI CONFIG ---
st.set_page_config(page_title="Mil-Pro Command", layout="wide")

# Night Ops Aesthetic: High-contrast, Dark Theme, American Flag Background
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.85), rgba(0, 0, 0, 0.85)), 
                    url('https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?auto=format&fit=crop&q=80&w=2000');
        background-size: cover;
        background-attachment: fixed;
        color: #FFFFFF;
    }
    .stMetric { background-color: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 10px; border-left: 5px solid #b22234; }
    div[data-testid="stForm"] { background-color: rgba(0, 0, 0, 0.7); border: 1px solid #444; border-radius: 10px; }
    h1, h2, h3 { color: #FFFFFF !important; text-transform: uppercase; letter-spacing: 2px; }
    .stButton>button { background-color: #3c3b6e; color: white; border: 1px solid #ffffff; }
    .stButton>button:hover { background-color: #b22234; border: 1px solid #ffffff; }
    </style>
    """, unsafe_allow_name=True)

# --- 2. TACTICAL RATES & SYSTEM CONSTANTS ---
# 2026 IRS Rates: Business/IDT share the same 72.5 cent rate.
RATES = {"IDT/Business": 0.725, "Medical": 0.205, "Charity": 0.14, "Personal": 0.00}
IDT_REIMB_CAP = 750.00

# --- 3. FAIL-SAFE DATABASE INITIALIZATION ---
@st.cache_resource
def get_db_connection():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception as e:
        st.error("DATABASE CONNECTION FAILED: Check Streamlit Secrets.")
        return None

db = get_db_connection()

# --- 4. SESSION STATE MANAGEMENT ---
if 'user' not in st.session_state: st.session_state.user = None
if 'active_vehicle' not in st.session_state: st.session_state.active_vehicle = "Standard Unit"

# --- 5. AUTHENTICATION GATE ---
def auth_gate():
    if not st.session_state.user:
        st.title("🪖 Mil-Pro Command: Authentication")
        tab1, tab2 = st.tabs(["INBOUND (Login)", "REGISTRATION (Sign-Up)"])
        with tab1:
            with st.form("login"):
                e, p = st.text_input("Email"), st.text_input("Password", type="password")
                if st.form_submit_button("LOGIN"):
                    try:
                        res = db.auth.sign_in_with_password({"email": e, "password": p})
                        st.session_state.user = res.user
                        st.rerun()
                    except: st.error("Access Denied: Invalid Credentials.")
        with tab2:
            with st.form("register"):
                ne, np = st.text_input("New Email"), st.text_input("New Password", type="password")
                if st.form_submit_button("CREATE ACCOUNT"):
                    try:
                        db.auth.sign_up({"email": ne, "password": np})
                        st.success("Registration Sent. Check Email.")
                    except: st.error("Registration Failed.")
        st.stop()

auth_gate()
uid = st.session_state.user.id

# --- 6. SIDEBAR: FLEET COMMAND & NAVIGATION ---
st.sidebar.title("⚓ COMMAND CENTER")

# Defensive Vehicle Fetching
v_options = ["Standard Unit"]
v_mpg_map = {"Standard Unit": 20.0}

try:
    v_res = db.table("vehicles").select("name, mpg").eq("user_id", uid).execute()
    if v_res.data:
        v_options = [v['name'] for v in v_res.data]
        v_mpg_map = {v['name']: float(v['mpg']) for v in v_res.data}
except: pass

selected_v = st.sidebar.selectbox("Active Vehicle", v_options)
current_mpg = v_mpg_map.get(selected_v, 20.0)

nav = st.sidebar.radio("Sectors", ["Mission Log", "IDT Tactical", "The Garage", "Reports"])

if st.sidebar.button("LOGOUT"):
    db.auth.sign_out()
    st.session_state.user = None
    st.rerun()

# --- 7. SECTOR: MISSION LOG (Fuel Engine Integrated) ---
if nav == "Mission Log":
    st.header(f"📍 Daily Sortie: {selected_v}")
    gas_price = st.sidebar.number_input("Gas Price ($/Gal)", value=3.50, step=0.01)

    # Fetch last Odometer to prevent manual entry errors
    last_odo = 0.0
    try:
        odo_res = db.table("logs").select("end_odo").eq("user_id", uid).order("created_at", desc=True).limit(1).execute()
        if odo_res.data: last_odo = float(odo_res.data[0]['end_odo'])
    except: pass

    with st.form("mission_entry", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            date = st.date_input("Date", datetime.date.today())
            cat = st.selectbox("Category", list(RATES.keys()))
            start = st.number_input("Start Odometer", value=last_odo)
        with c2:
            end = st.number_input("End Odometer", min_value=start)
            dest = st.text_input("Destination/Unit")
        
        purpose = st.text_input("Purpose of Travel")

        if st.form_submit_button("SUBMIT MISSION LOG"):
            miles = end - start
            deduction = round(miles * RATES[cat], 2)
            # Automatic Fuel Cost Calculation
            fuel_cost = round((miles / current_mpg) * gas_price, 2)

            db.table("logs").insert({
                "user_id": uid, "date": str(date), "miles": miles, "destination": dest,
                "purpose": f"[{cat}] {purpose}", "total_deduction": deduction,
                "vehicle_name": selected_v, "fuel_gas": fuel_cost, 
                "start_odo": start, "end_odo": end
            }).execute()
            
            st.success(f"✅ Mission Recorded. Deduction: ${deduction} | Est. Fuel Cost: ${fuel_cost}")
            st.balloons()

# --- 8. SECTOR: IDT TACTICAL (Deep Detail) ---
elif nav == "IDT Tactical":
    st.header("✈️ IDT Unreimbursed Logistics")
    st.info("Reservist Above-the-Line Deduction (Form 2106 / Schedule 1)")
    
    with st.form("idt_detail"):
        st.subheader("Transport & Lodging")
        col1, col2 = st.columns(2)
        with col1:
            air_miles = st.number_input("Miles to/from Airport (Home Leg)", min_value=0.0)
            lodging = st.number_input("Lodging/Hotel (Actual Out-of-Pocket)", min_value=0.0)
            tolls_park = st.number_input("Tolls & Airport Parking", min_value=0.0)
        with col2:
            transit = st.number_input("Mass Transit (Uber/Taxi/Lyft)", min_value=0.0)
            meals = st.number_input("Meals (Total Spent - 50% will be applied)", min_value=0.0)
            reimb = st.number_input("Gov Travel Reimbursement (Voucher Pay)", value=IDT_REIMB_CAP)
        
        st.subheader("Miscellaneous Expenses")
        incidentals = st.number_input("Laundry & Incidentals (Overnight Only)", min_value=0.0)
        
        if st.form_submit_button("GENERATE NET DEDUCTION"):
            # Math for Schedule 1: (Transport + Lodging + Transit + Incid + (Meals*0.5)) - Reimb
            total_eligible = (air_miles * 0.725) + lodging + tolls_park + transit + incidentals + (meals * 0.5)
            net_deduct = max(0.0, total_eligible - reimb)
            
            st.metric("Net Tax Deduction (Above-the-Line)", f"${net_deduct:,.2f}")
            st.success("This value reduces your AGI directly on Schedule 1.")

# --- 9. SECTOR: THE GARAGE ---
elif nav == "The Garage":
    st.header("🚘 Fleet Registration")
    with st.form("garage_reg", clear_on_submit=True):
        v_name = st.text_input("Vehicle Description (e.g., 2026 SUV)")
        v_mpg = st.number_input("Average MPG", min_value=1.0, value=20.0)
        if st.form_submit_button("REGISTER TO FLEET"):
            try:
                db.table("vehicles").insert({"user_id": uid, "name": v_name, "mpg": v_mpg}).execute()
                st.success(f"{v_name} added to command.")
                st.rerun()
            except: st.error("Error: This vehicle name may already be registered.")

# --- 10. SECTOR: REPORTS ---
elif nav == "Reports":
    st.header("📊 Executive Accountant Report")
    try:
        report_res = db.table("logs").select("*").eq("user_id", uid).execute()
        if report_res.data:
            df = pd.DataFrame(report_res.data)
            # Display Clean View
            st.dataframe(df[["date", "vehicle_name", "purpose", "miles", "total_deduction", "fuel_gas"]], use_container_width=True)
            # Export
            st.download_button("📥 Export .CSV for Tax Preparer", df.to_csv(index=False).encode('utf-8'), "MilPro_2026_Tax.csv")
        else:
            st.info("No data currently available for export.")
    except Exception as e:
        st.error(f"Report Generation Error: {e}")
