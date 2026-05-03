import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd

# --- 1. SYSTEM CONFIG (MUST BE FIRST) ---
st.set_page_config(page_title="Mil-Pro Command", layout="wide")

# --- 2. HIGH-CONTRAST NIGHT OPS THEME ---
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
    h1, h2, h3 { color: #FFFFFF !important; text-transform: uppercase; letter-spacing: 2px; }
    .stButton>button { background-color: #3c3b6e; color: white; border: 1px solid #ffffff; font-weight: bold; }
    .stButton>button:hover { background-color: #b22234; }
    </style>
    """, unsafe_allow_name=True)

# --- 3. DEFENSIVE DATABASE INITIALIZATION ---
def get_db():
    """Lazy-loads the database connection only when called."""
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception as e:
        st.error("CRITICAL: Supabase Secrets not found. Check your Streamlit Dashboard Secrets.")
        st.stop()

# --- 4. TACTICAL RATES (2026) ---
# IDT and Business share the $0.725/mile rate.
RATES = {"IDT/Business": 0.725, "Medical": 0.205, "Charity": 0.14, "Personal": 0.00}

# --- 5. SESSION STATE ---
if 'user' not in st.session_state: st.session_state.user = None

# --- 6. AUTHENTICATION ---
if not st.session_state.user:
    st.title("🪖 Mil-Pro Command: Authentication")
    db = get_db() # Called only when needed
    with st.form("login_form"):
        e = st.text_input("Email")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("LOGIN"):
            try:
                res = db.auth.sign_in_with_password({"email": e, "password": p})
                st.session_state.user = res.user
                st.rerun()
            except: st.error("Login Failed. Verify credentials.")
    st.stop()

# --- 7. LOGGED-IN VARIABLES ---
db = get_db()
uid = st.session_state.user.id

# --- 8. SIDEBAR: FLEET & NAV ---
st.sidebar.title("⚓ COMMAND CENTER")

# Fetch Vehicles with Fallback
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
gas_price = st.sidebar.number_input("Gas Price ($/Gal)", value=3.50, step=0.01)

nav = st.sidebar.radio("Sectors", ["Mission Log", "IDT Tactical", "The Garage", "Reports"])

if st.sidebar.button("LOGOUT"):
    db.auth.sign_out()
    st.session_state.user = None
    st.rerun()

# --- 9. SECTOR: MISSION LOG ---
if nav == "Mission Log":
    st.header(f"📍 Daily Sortie: {selected_v}")
    
    last_odo = 0.0
    try:
        odo_res = db.table("logs").select("end_odo").eq("user_id", uid).order("created_at", desc=True).limit(1).execute()
        if odo_res.data: last_odo = float(odo_res.data[0]['end_odo'])
    except: pass

    with st.form("mission_log", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            date = st.date_input("Date", datetime.date.today())
            cat = st.selectbox("Category", list(RATES.keys()))
            start = st.number_input("Start Odometer", value=last_odo)
        with c2:
            end = st.number_input("End Odometer", min_value=start)
            dest = st.text_input("Destination")
        
        purpose = st.text_input("Purpose")

        if st.form_submit_button("SAVE MISSION"):
            miles = end - start
            deduct = round(miles * RATES[cat], 2)
            # FUEL MATH: (Miles / MPG) * Price
            fuel_cost = round((miles / current_mpg) * gas_price, 2)

            db.table("logs").insert({
                "user_id": uid, "date": str(date), "miles": miles, "destination": dest,
                "purpose": f"[{cat}] {purpose}", "total_deduction": deduct,
                "vehicle_name": selected_v, "fuel_gas": fuel_cost,
                "start_odo": start, "end_odo": end
            }).execute()
            st.success(f"✅ Mission Recorded. Deduction: ${deduct} | Fuel Cost: ${fuel_cost}")

# --- 10. SECTOR: IDT TACTICAL ---
elif nav == "IDT Tactical":
    st.header("✈️ IDT Unreimbursed Logistics")
    st.info("IRS Form 2106 / Schedule 1 Tracking")
    
    with st.form("idt_form"):
        col1, col2 = st.columns(2)
        with col1:
            m_airport = st.number_input("Miles to Airport (Home Leg)", value=0.0)
            lodging = st.number_input("Lodging/Hotel (Total Out-of-Pocket)", value=0.0)
            tolls = st.number_input("Tolls & Parking", value=0.0)
        with col2:
            transit = st.number_input("Mass Transit (Uber/Taxi)", value=0.0)
            meals = st.number_input("Total Meals Cost (50% rule applied)", value=0.0)
            reimb = st.number_input("Gov Reimbursement ($750 cap usually)", value=750.0)
        
        incidentals = st.number_input("Laundry/Incidentals", value=0.0)
        
        if st.form_submit_button("CALCULATE NET DEDUCTION"):
            total_eligible = (m_airport * 0.725) + lodging + tolls + transit + incidentals + (meals * 0.5)
            net = max(0.0, total_eligible - reimb)
            st.metric("Net Schedule 1 Deduction", f"${net:,.2f}")

# --- 11. SECTOR: THE GARAGE ---
elif nav == "The Garage":
    st.header("🚘 Fleet Registration")
    with st.form("garage_form", clear_on_submit=True):
        v_name = st.text_input("Vehicle Description")
        v_mpg = st.number_input("Average MPG", min_value=1.0, value=20.0)
        if st.form_submit_button("REGISTER VEHICLE"):
            db.table("vehicles").insert({"user_id": uid, "name": v_name, "mpg": v_mpg}).execute()
            st.success(f"{v_name} registered.")
            st.rerun()

# --- 12. SECTOR: REPORTS ---
elif nav == "Reports":
    st.header("📊 Tax Export")
    data = db.table("logs").select("*").eq("user_id", uid).execute()
    if data.data:
        df = pd.DataFrame(data.data)
        st.dataframe(df[["date", "vehicle_name", "purpose", "miles", "total_deduction", "fuel_gas"]])
        st.download_button("📥 Download CSV", df.to_csv(index=False), "MilPro_2026.csv")
