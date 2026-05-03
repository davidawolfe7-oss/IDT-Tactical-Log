import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd

# --- 1. SYSTEM ARCHITECTURE & THEME ---
st.set_page_config(page_title="Mil-Pro Command", layout="wide")

# High-Contrast Night Ops CSS with Flag Motif
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.85), rgba(0, 0, 0, 0.85)), 
                    url('https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?auto=format&fit=crop&q=80&w=2000');
        background-size: cover;
        color: #FFFFFF;
    }
    .stMetric { background-color: rgba(255, 255, 255, 0.1); padding: 10px; border-radius: 5px; border-left: 5px solid #cc0000; }
    h1, h2, h3 { color: #FFFFFF !important; text-shadow: 2px 2px #000000; }
    .stButton>button { background-color: #cc0000; color: white; width: 100%; border: none; font-weight: bold; }
    </style>
    """, unsafe_allow_name=True)

# --- 2. TACTICAL RATES (2026) ---
RATES = {"IDT/Business": 0.725, "Medical": 0.205, "Charity": 0.14, "Personal": 0.00}

# --- 3. DATABASE CONNECTION ---
@st.cache_resource
def init_db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

db = init_db()

# --- 4. SESSION STATE ---
if 'user' not in st.session_state: st.session_state.user = None

# Auth Gate
if not st.session_state.user:
    st.title("🪖 Mil-Pro Command: Login")
    with st.form("auth"):
        e, p = st.text_input("Email"), st.text_input("Password", type="password")
        if st.form_submit_button("AUTHENTICATE"):
            try:
                res = db.auth.sign_in_with_password({"email": e, "password": p})
                st.session_state.user = res.user
                st.rerun()
            except: st.error("Login Failed.")
    st.stop()

uid = st.session_state.user.id

# --- 5. SIDEBAR FLEET MGMT ---
st.sidebar.title("🛠️ Fleet & Navigation")
v_data = db.table("vehicles").select("*").eq("user_id", uid).execute()
vehicles = {v['name']: v['mpg'] for v in v_data.data} if v_data.data else {"Primary Unit": 20.0}
active_v = st.sidebar.selectbox("Active Primary Unit", list(vehicles.keys()))
active_mpg = vehicles.get(active_v, 20.0)

nav = st.sidebar.radio("Sectors", ["Mission Log", "IDT Tactical", "The Garage", "Reports"])

# --- 6. SECTOR: MISSION LOG (With Fuel Cost Engine) ---
if nav == "Mission Log":
    st.header(f"📍 Daily Sortie: {active_v}")
    gas_price = st.number_input("Current Gas Price ($/Gal)", value=3.50, step=0.10)
    
    with st.form("log_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            date = st.date_input("Date", datetime.date.today())
            cat = st.selectbox("Category", list(RATES.keys()))
            start = st.number_input("Start Odometer", min_value=0.0)
        with c2:
            end = st.number_input("End Odometer", min_value=start)
            dest = st.text_input("Destination/Purpose")
        
        if st.form_submit_button("SAVE MISSION"):
            miles = end - start
            deduct = round(miles * RATES[cat], 2)
            # FUEL COST CALC: (Miles / MPG) * Price
            fuel_cost = round((miles / active_mpg) * gas_price, 2)
            
            db.table("logs").insert({
                "user_id": uid, "date": str(date), "miles": miles, "destination": dest,
                "purpose": cat, "total_deduction": deduct, "vehicle_name": active_v,
                "fuel_gas": fuel_cost, "start_odo": start, "end_odo": end
            }).execute()
            st.success(f"✅ Logged! Deduction: ${deduct} | Est. Fuel Cost: ${fuel_cost}")
            st.balloons()

# --- 7. SECTOR: IDT TACTICAL (High Detail) ---
elif nav == "IDT Tactical":
    st.header("✈️ Comprehensive IDT Logistics")
    st.info("Form 2106 Above-the-Line Tracking")
    
    with st.form("idt_detail"):
        m1, m2 = st.columns(2)
        with m1:
            miles_airport = st.number_input("Miles to/from Home Airport", value=0.0)
            lodging = st.number_input("Hotel/Lodging (Actual Cost)", value=0.0)
            tolls = st.number_input("Tolls & Airport Parking", value=0.0)
        with m2:
            transit = st.number_input("Uber/Taxi/Mass Transit", value=0.0)
            meals = st.number_input("Meals (Deductible at 50%)", value=0.0)
            reimb = st.number_input("Gov Reimbursement Received", value=750.0)
        
        if st.form_submit_button("CALCULATE NET TAX IMPACT"):
            # Math: (Transport + Lodging + Transit + (Meals * 0.5)) - Reimbursement
            total_exp = (miles_airport * 0.725) + lodging + tolls + transit + (meals * 0.5)
            net_impact = max(0.0, total_exp - reimb)
            st.metric("Net Schedule 1 Deduction", f"${net_impact:,.2f}")

# --- 8. SECTOR: THE GARAGE ---
elif nav == "The Garage":
    st.header("🚘 Vehicle Fleet Registration")
    with st.form("add_v", clear_on_submit=True):
        vname = st.text_input("Vehicle Name (Unique)")
        vmpg = st.number_input("Vehicle MPG (Used for Fuel Math)", value=20.0)
        if st.form_submit_button("Register to Fleet"):
            db.table("vehicles").insert({"user_id": uid, "name": vname, "mpg": vmpg}).execute()
            st.success(f"{vname} Added.")
            st.rerun()

# --- 9. SECTOR: REPORTS ---
elif nav == "Reports":
    st.header("📊 Executive Accountant Export")
    res = db.table("logs").select("*").eq("user_id", uid).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df[["date", "vehicle_name", "miles", "purpose", "total_deduction", "fuel_gas"]])
        st.download_button("📥 Download Tax CSV", df.to_csv(index=False), "MilPro_Tax_2026.csv")
