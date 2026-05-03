import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd

# --- STAGE 1: HARD-CODED PRE-FLIGHT CHECK ---
st.set_page_config(page_title="Mil-Pro Command", layout="wide")

def get_supabase():
    """Diagnostic check to prevent Line 10 crashes."""
    if "SUPABASE_URL" not in st.secrets or "SUPABASE_KEY" not in st.secrets:
        st.error("❌ CRITICAL ERROR: Database credentials missing from Streamlit Secrets.")
        st.info("Please ensure 'SUPABASE_URL' and 'SUPABASE_KEY' are set in your secrets.toml.")
        st.stop()
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# Initialize client safely
db = get_supabase()

# --- STAGE 2: NIGHT OPS HIGH-CONTRAST UI ---
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
    .stButton>button { background-color: #3C3B6E; color: white; border: 2px solid #FFFFFF; font-weight: bold; }
    .stButton>button:hover { background-color: #B22234; }
    </style>
    """, unsafe_allow_name=True)

# --- STAGE 3: LOGIC & RATES ---
RATES = {"IDT/Business": 0.725, "Medical": 0.205, "Charity": 0.14, "Personal": 0.00}

if 'user' not in st.session_state: st.session_state.user = None

# --- STAGE 4: AUTHENTICATION ---
if not st.session_state.user:
    st.title("🪖 Mil-Pro Command: Secure Login")
    with st.form("login_gate"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("AUTHENTICATE"):
            try:
                res = db.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.rerun()
            except Exception as e:
                st.error(f"Login Failed: {e}")
    st.stop()

# --- STAGE 5: LOGGED-IN SESSION ---
uid = st.session_state.user.id

# Sidebar Navigation & Fleet Management
st.sidebar.title("⚓ COMMAND CENTER")

# Fetch Vehicles for MPG Engine
v_options = ["Standard Unit"]
v_mpg_map = {"Standard Unit": 20.0}
try:
    v_query = db.table("vehicles").select("name, mpg").eq("user_id", uid).execute()
    if v_query.data:
        v_options = [v['name'] for v in v_query.data]
        v_mpg_map = {v['name']: float(v['mpg']) for v in v_query.data}
except: pass

selected_vehicle = st.sidebar.selectbox("Active Vehicle", v_options)
current_mpg = v_mpg_map.get(selected_vehicle, 20.0)
gas_price = st.sidebar.number_input("Gas Price ($/Gal)", value=3.50)

nav = st.sidebar.radio("Sectors", ["Mission Log", "IDT Tactical", "The Garage", "Executive Reports"])

if st.sidebar.button("LOGOUT"):
    db.auth.sign_out()
    st.session_state.user = None
    st.rerun()

# --- SECTOR: MISSION LOG (Fuel Cost Integration) ---
if nav == "Mission Log":
    st.header(f"📍 Daily Sortie: {selected_vehicle}")
    
    last_odo = 0.0
    try:
        odo_check = db.table("logs").select("end_odo").eq("user_id", uid).order("created_at", desc=True).limit(1).execute()
        if odo_check.data: last_odo = float(odo_check.data[0]['end_odo'])
    except: pass

    with st.form("mission_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            date = st.date_input("Date", datetime.date.today())
            cat = st.selectbox("Category", list(RATES.keys()))
            start_odo = st.number_input("Start Odometer", value=last_odo)
        with c2:
            end_odo = st.number_input("End Odometer", min_value=start_odo)
            destination = st.text_input("Destination/Unit")
        
        mission_purpose = st.text_input("Mission Purpose")

        if st.form_submit_button("LOG MISSION"):
            miles_driven = end_odo - start_odo
            tax_value = round(miles_driven * RATES[cat], 2)
            # FUEL ENGINE: (Miles / MPG) * Price
            fuel_expense = round((miles_driven / current_mpg) * gas_price, 2)

            db.table("logs").insert({
                "user_id": uid, "date": str(date), "miles": miles_driven,
                "destination": destination, "purpose": f"[{cat}] {mission_purpose}",
                "total_deduction": tax_value, "vehicle_name": selected_vehicle,
                "fuel_gas": fuel_expense, "start_odo": start_odo, "end_odo": end_odo
            }).execute()
            st.success(f"✅ Mission Logged! Deduction: ${tax_value} | Fuel Cost: ${fuel_expense}")

# --- SECTOR: IDT TACTICAL (High-Detail Logistics) ---
elif nav == "IDT Tactical":
    st.header("✈️ IDT Unreimbursed Logistics")
    st.info("IRS Form 2106 Above-the-Line Tracking ($750 Cap Logic Applied)")
    
    with st.form("idt_tactical_form"):
        col1, col2 = st.columns(2)
        with col1:
            m_to_airport = st.number_input("Miles to Airport (Home Leg)", value=0.0)
            lodging_total = st.number_input("Lodging/Hotel (Out-of-Pocket)", value=0.0)
            parking_tolls = st.number_input("Parking & Tolls", value=0.0)
        with col2:
            transit_costs = st.number_input("Uber/Taxi/Transit", value=0.0)
            meals_total = st.number_input("Total Meals Cost (App applies 50% rule)", value=0.0)
            govt_reimb = st.number_input("Gov Reimbursement Received", value=750.0)
        
        incidentals = st.number_input("Laundry/Incidentals", value=0.0)
        
        if st.form_submit_button("CALCULATE SCHEDULE 1 IMPACT"):
            # IRS Calculation Logic
            transport_deduct = (m_to_airport * 0.725) + parking_tolls + transit_costs
            subsistence_deduct = lodging_total + incidentals + (meals_total * 0.5)
            net_deduction = max(0.0, (transport_deduct + subsistence_deduct) - govt_reimb)
            
            st.metric("Net Above-the-Line Deduction", f"${net_deduction:,.2f}")
            st.success("Report this value on Schedule 1 (Form 1040) for unreimbursed Reservist expenses.")

# --- SECTOR: THE GARAGE ---
elif nav == "The Garage":
    st.header("🚘 Vehicle Fleet Registration")
    with st.form("garage_form", clear_on_submit=True):
        v_name = st.text_input("Vehicle Description")
        v_mpg = st.number_input("Average MPG", min_value=1.0, value=20.0)
        if st.form_submit_button("ADD TO FLEET"):
            db.table("vehicles").insert({"user_id": uid, "name": v_name, "mpg": v_mpg}).execute()
            st.success(f"{v_name} registered.")
            st.rerun()

# --- SECTOR: REPORTS ---
elif nav == "Reports":
    st.header("📊 Tax Export Sector")
    try:
        report_data = db.table("logs").select("*").eq("user_id", uid).execute()
        if report_data.data:
            df = pd.DataFrame(report_data.data)
            st.dataframe(df[["date", "vehicle_name", "purpose", "miles", "total_deduction", "fuel_gas"]], use_container_width=True)
            st.download_button("📥 Download Excel-Compatible CSV", df.to_csv(index=False), "MilPro_2026_Report.csv")
        else:
            st.info("No records found in database.")
    except Exception as e:
        st.error(f"Error fetching report: {e}")
