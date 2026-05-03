import streamlit as st

# --- 1. CORE UI BOOTSTRAP (MUST BE FIRST) ---
st.set_page_config(page_title="Mil-Pro Command", layout="wide")

# --- 2. NIGHT OPS HIGH-CONTRAST UI ---
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.85), rgba(0, 0, 0, 0.85)), 
                    url('https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?auto=format&fit=crop&q=80&w=2000');
        background-size: cover; background-attachment: fixed; color: #FFFFFF;
    }
    .stMetric { background-color: rgba(255, 255, 255, 0.1); padding: 15px; border-radius: 8px; border-left: 5px solid #CC0000; }
    h1, h2, h3 { color: #FFFFFF !important; text-shadow: 2px 2px #000000; font-weight: 800; }
    .stButton>button { background-color: #3C3B6E; color: white; border: 2px solid #FFFFFF; font-weight: bold; width: 100%; }
    .stButton>button:hover { background-color: #B22234; }
    div[data-testid="stForm"] { background-color: rgba(0,0,0,0.6); padding: 20px; border-radius: 10px; border: 1px solid #444; }
    </style>
    """, unsafe_allow_name=True)

# --- 3. THE ENGINE ROOM (LOCALIZED IMPORTS) ---
# We move these inside to ensure they don't trigger Line 18 errors on boot.
if 'user' not in st.session_state:
    st.session_state.user = None

# --- 4. AUTHENTICATION GATE ---
if not st.session_state.user:
    st.title("🪖 Mil-Pro Command: Secure Login")
    with st.form("auth_gate"):
        email = st.text_input("Email")
        pw = st.text_input("Password", type="password")
        if st.form_submit_button("AUTHENTICATE"):
            from supabase import create_client
            try:
                db = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
                res = db.auth.sign_in_with_password({"email": email, "password": pw})
                st.session_state.user = res.user
                st.rerun()
            except Exception as e:
                st.error(f"Login Failed: {e}")
    st.stop()

# --- 5. MISSION CONTROL (LOGGED IN) ---
import datetime
import pandas as pd
from supabase import create_client

# Secure Connection Establishment
db = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
uid = st.session_state.user.id

# Fleet Engine
v_options = ["Standard Unit"]
v_mpg_map = {"Standard Unit": 20.0}
try:
    v_query = db.table("vehicles").select("name, mpg").eq("user_id", uid).execute()
    if v_query.data:
        v_options = [v['name'] for v in v_query.data]
        v_mpg_map = {v['name']: float(v['mpg']) for v in v_query.data}
except:
    pass

st.sidebar.title("⚓ COMMAND CENTER")
selected_v = st.sidebar.selectbox("Active Vehicle", v_options)
current_mpg = v_mpg_map.get(selected_v, 20.0)
gas_price = st.sidebar.number_input("Gas Price ($/Gal)", value=3.50)

nav = st.sidebar.radio("Sectors", ["Mission Log", "IDT Tactical", "The Garage", "Reports"])

if st.sidebar.button("LOGOUT"):
    db.auth.sign_out()
    st.session_state.user = None
    st.rerun()

# --- 6. SECTOR: MISSION LOG (Fuel Cost Engine) ---
if nav == "Mission Log":
    st.header(f"📍 Daily Sortie: {selected_v}")
    
    last_odo = 0.0
    try:
        odo_res = db.table("logs").select("end_odo").eq("user_id", uid).order("created_at", desc=True).limit(1).execute()
        if odo_res.data:
            last_odo = float(odo_res.data[0]['end_odo'])
    except:
        pass

    with st.form("mission_entry", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            date = st.date_input("Date", datetime.date.today())
            cat = st.selectbox("Category", ["IDT/Business", "Medical", "Charity", "Personal"])
            start = st.number_input("Start Odometer", value=last_odo)
        with c2:
            end = st.number_input("End Odometer", min_value=start)
            dest = st.text_input("Destination")
        
        purpose = st.text_input("Mission Purpose")

        if st.form_submit_button("LOG MISSION"):
            # 2026 Rates
            rates = {"IDT/Business": 0.725, "Medical": 0.205, "Charity": 0.14, "Personal": 0.00}
            miles = end - start
            deduct = round(miles * rates[cat], 2)
            # Fuel Math: (Miles / MPG) * Price
            fuel = round((miles / current_mpg) * gas_price, 2)
            
            db.table("logs").insert({
                "user_id": uid, "date": str(date), "miles": miles, "destination": dest,
                "purpose": f"[{cat}] {purpose}", "total_deduction": deduct,
                "vehicle_name": selected_v, "fuel_gas": fuel,
                "start_odo": start, "end_odo": end
            }).execute()
            st.success(f"✅ Logged! Deduction: ${deduct} | Fuel Spend: ${fuel}")

# --- 7. SECTOR: IDT TACTICAL (High Detail) ---
elif nav == "IDT Tactical":
    st.header("✈️ IDT Unreimbursed Logistics")
    st.info("IRS Form 2106 / Schedule 1 Logic")
    
    with st.form("idt_form"):
        col1, col2 = st.columns(2)
        with col1:
            m_airport = st.number_input("POV Miles to/from Airport", value=0.0)
            lodging = st.number_input("Lodging (Out-of-Pocket)", value=0.0)
            tolls = st.number_input("Tolls & Parking", value=0.0)
        with col2:
            transit = st.number_input("Uber/Taxi/Transit", value=0.0)
            meals = st.number_input("Total Meals Cost (App applies 50% rule)", value=0.0)
            reimb = st.number_input("Gov Travel Reimbursement Received", value=750.0)
        
        incid = st.number_input("Laundry/Incidentals", value=0.0)
        
        if st.form_submit_button("CALCULATE NET DEDUCTION"):
            # IRS Calculation
            total_eligible = (m_airport * 0.725) + lodging + tolls + transit + incid + (meals * 0.5)
            net_impact = max(0.0, total_eligible - reimb)
            st.metric("Net Schedule 1 Deduction", f"${net_impact:,.2f}")

# --- 8. SECTOR: THE GARAGE ---
elif nav == "The Garage":
    st.header("🚘 Fleet Management")
    with st.form("garage_form", clear_on_submit=True):
        vn = st.text_input("Vehicle Name")
        vm = st.number_input("Vehicle MPG (for Fuel Tracking)", min_value=1.0, value=20.0)
        if st.form_submit_button("REGISTER VEHICLE"):
            db.table("vehicles").insert({"user_id": uid, "name": vn, "mpg": vm}).execute()
            st.success(f"{vn} Registered.")
            st.rerun()

# --- 9. SECTOR: REPORTS ---
elif nav == "Reports":
    st.header("📊 Tax Export")
    try:
        res = db.table("logs").select("*").eq("user_id", uid).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            st.dataframe(df[["date", "vehicle_name", "purpose", "miles", "total_deduction", "fuel_gas"]])
            st.download_button("📥 Download 2026 CSV", df.to_csv(index=False), "MilPro_2026.csv")
    except Exception as e:
        st.error(f"Error: {e}")
