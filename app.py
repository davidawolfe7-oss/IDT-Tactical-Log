import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd

# --- 1. SYSTEM INITIALIZATION ---
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
    .stMetric { background-color: rgba(255, 255, 255, 0.1); padding: 15px; border-radius: 8px; border-left: 5px solid #CC0000; }
    h1, h2, h3 { color: #FFFFFF !important; text-shadow: 2px 2px #000000; font-weight: 800; }
    .stButton>button { background-color: #3C3B6E; color: white; border: 2px solid #FFFFFF; font-weight: bold; width: 100%; }
    .stButton>button:hover { background-color: #B22234; }
    div[data-testid="stForm"] { background-color: rgba(0,0,0,0.5); padding: 20px; border-radius: 10px; border: 1px solid #444; }
    </style>
    """, unsafe_allow_name=True)

# --- 3. JIT DATABASE CONNECTION ---
def get_db():
    """Connects to Supabase only when explicitly called to prevent Line 21 crashes."""
    if "SUPABASE_URL" not in st.secrets or "SUPABASE_KEY" not in st.secrets:
        st.error("Database Secrets Missing. Configure SUPABASE_URL and SUPABASE_KEY in Streamlit.")
        st.stop()
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# --- 4. TACTICAL RATES (2026) ---
RATES = {"IDT/Business": 0.725, "Medical": 0.205, "Charity": 0.14, "Personal": 0.00}

# --- 5. SESSION STATE ---
if 'user' not in st.session_state:
    st.session_state.user = None

# --- 6. AUTHENTICATION GATE ---
if not st.session_state.user:
    st.title("🪖 Mil-Pro Command: Secure Login")
    with st.form("auth_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("AUTHENTICATE"):
            try:
                db = get_db()
                res = db.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.rerun()
            except Exception as e:
                st.error(f"Login Failed: {e}")
    st.stop()

# --- 7. SECURE CONTEXT ---
uid = st.session_state.user.id

# --- 8. SIDEBAR COMMAND ---
st.sidebar.title("⚓ COMMAND CENTER")

# Fleet Data Fetch (Defensive)
v_options = ["Standard Unit"]
v_mpg_map = {"Standard Unit": 20.0}
try:
    db = get_db()
    v_res = db.table("vehicles").select("name, mpg").eq("user_id", uid).execute()
    if v_res.data:
        v_options = [v['name'] for v in v_res.data]
        v_mpg_map = {v['name']: float(v['mpg']) for v in v_res.data}
except:
    pass

selected_v = st.sidebar.selectbox("Active Vehicle", v_options)
current_mpg = v_mpg_map.get(selected_v, 20.0)
gas_price = st.sidebar.number_input("Gas Price ($/Gal)", value=3.50)

nav = st.sidebar.radio("Sectors", ["Mission Log", "IDT Tactical", "The Garage", "Reports"])

if st.sidebar.button("LOGOUT"):
    db = get_db()
    db.auth.sign_out()
    st.session_state.user = None
    st.rerun()

# --- 9. SECTOR: MISSION LOG ---
if nav == "Mission Log":
    st.header(f"📍 Daily Sortie: {selected_v}")
    
    # Auto-fetch last odo
    last_odo = 0.0
    try:
        db = get_db()
        odo_check = db.table("logs").select("end_odo").eq("user_id", uid).order("created_at", desc=True).limit(1).execute()
        if odo_check.data:
            last_odo = float(odo_check.data[0]['end_odo'])
    except:
        pass

    with st.form("mission_entry", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("Date", datetime.date.today())
            cat = st.selectbox("Category", list(RATES.keys()))
            start = st.number_input("Start Odometer", value=last_odo)
        with col2:
            end = st.number_input("End Odometer", min_value=start)
            dest = st.text_input("Destination")
        
        purpose = st.text_input("Mission Purpose")

        if st.form_submit_button("SUBMIT LOG"):
            miles = end - start
            deduction = round(miles * RATES[cat], 2)
            # FUEL ENGINE
            fuel_cost = round((miles / current_mpg) * gas_price, 2)
            
            db = get_db()
            db.table("logs").insert({
                "user_id": uid, "date": str(date), "miles": miles, "destination": dest,
                "purpose": f"[{cat}] {purpose}", "total_deduction": deduction,
                "vehicle_name": selected_v, "fuel_gas": fuel_cost,
                "start_odo": start, "end_odo": end
            }).execute()
            st.success(f"✅ Mission Recorded. Deduction: ${deduction} | Fuel: ${fuel_cost}")

# --- 10. SECTOR: IDT TACTICAL ---
elif nav == "IDT Tactical":
    st.header("✈️ IDT Unreimbursed Logistics")
    st.info("Reservist Above-the-Line Tracking ($750 Cap Logic Applied)")
    
    with st.form("idt_form"):
        c1, c2 = st.columns(2)
        with c1:
            m_airport = st.number_input("Miles to Airport (Home Leg)", value=0.0)
            lodging = st.number_input("Lodging (Out-of-Pocket)", value=0.0)
            tolls = st.number_input("Parking & Tolls", value=0.0)
        with c2:
            transit = st.number_input("Uber/Taxi/Transit", value=0.0)
            meals = st.number_input("Total Meals (App applies 50% rule)", value=0.0)
            reimb = st.number_input("Gov Reimbursement Received", value=750.0)
        
        incid = st.number_input("Laundry/Incidentals", value=0.0)
        
        if st.form_submit_button("CALCULATE NET IMPACT"):
            # IRS Calculation
            total_eligible = (m_airport * 0.725) + lodging + tolls + transit + incid + (meals * 0.5)
            net_impact = max(0.0, total_eligible - reimb)
            st.metric("Net Schedule 1 Deduction", f"${net_impact:,.2f}")

# --- 11. SECTOR: THE GARAGE ---
elif nav == "The Garage":
    st.header("🚘 Fleet Management")
    with st.form("garage_reg", clear_on_submit=True):
        v_name = st.text_input("Vehicle Name")
        v_mpg = st.number_input("Avg MPG", min_value=1.0, value=20.0)
        if st.form_submit_button("REGISTER VEHICLE"):
            db = get_db()
            db.table("vehicles").insert({"user_id": uid, "name": v_name, "mpg": v_mpg}).execute()
            st.success(f"{v_name} Registered.")
            st.rerun()

# --- 12. SECTOR: REPORTS ---
elif nav == "Reports":
    st.header("📊 Tax Export")
    try:
        db = get_db()
        res = db.table("logs").select("*").eq("user_id", uid).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            st.dataframe(df[["date", "vehicle_name", "purpose", "miles", "total_deduction", "fuel_gas"]])
            st.download_button("📥 Export CSV", df.to_csv(index=False), "MilPro_2026.csv")
    except Exception as e:
        st.error(f"Error: {e}")
