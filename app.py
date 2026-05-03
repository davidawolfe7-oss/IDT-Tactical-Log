import streamlit as st

# --- 1. BOOTSTRAP (LINE 1-10) ---
# We use zero external imports here to guarantee the app starts.
st.set_page_config(page_title="Mil-Pro Command", layout="wide")

# --- 2. NIGHT OPS UI (FLAGS & HIGH-CONTRAST) ---
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.85), rgba(0, 0, 0, 0.85)), 
                    url('https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?auto=format&fit=crop&q=80&w=2000');
        background-size: cover; background-attachment: fixed; color: #FFFFFF;
    }
    .stMetric { background-color: rgba(255, 255, 255, 0.1); padding: 15px; border-radius: 8px; border-left: 5px solid #CC0000; }
    h1, h2, h3 { color: #FFFFFF !important; text-shadow: 2px 2px #000000; font-weight: 800; }
    .stButton>button { background-color: #3C3B6E; color: white; border: 2px solid #FFFFFF; font-weight: bold; }
    .stButton>button:hover { background-color: #B22234; }
    div[data-testid="stForm"] { background-color: rgba(0,0,0,0.6); padding: 20px; border-radius: 10px; border: 1px solid #444; }
    </style>
    """, unsafe_allow_name=True)

# --- 3. SESSION STATE ---
if 'user' not in st.session_state:
    st.session_state.user = None

# --- 4. AUTHENTICATION GATE ---
if not st.session_state.user:
    st.title("🪖 Mil-Pro Command: Secure Login")
    with st.form("login_gate"):
        email = st.text_input("Email")
        pw = st.text_input("Password", type="password")
        if st.form_submit_button("AUTHENTICATE"):
            # DYNAMIC IMPORT: Prevents startup crashes
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
# Only import these once we are safely past the login gate
import datetime
import pandas as pd
from supabase import create_client

# Secure DB Instance
db = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
uid = st.session_state.user.id

# Fleet Database Engine
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

# --- 6. SECTOR: MISSION LOG (Fuel Engine) ---
if nav == "Mission Log":
    st.header(f"📍 Daily Sortie: {selected_v}")
    
    last_odo = 0.0
    try:
        odo_res = db.table("logs").select("end_odo").eq("user_id", uid).order("created_at", desc=True).limit(1).execute()
        if odo_res.data:
            last_odo = float(odo_res.data[0]['end_odo'])
    except:
        pass

    with st.form("mission_log", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            date = st.date_input("Date", datetime.date.today())
            cat = st.selectbox("Category", ["IDT/Business", "Medical", "Charity", "Personal"])
            start = st.number_input("Start Odometer", value=last_odo)
        with c2:
            end = st.number_input("End Odometer", min_value=start)
            dest = st.text_input("Destination")
        
        purpose = st.text_input("Purpose")

        if st.form_submit_button("SUBMIT LOG"):
            # 2026 Mileage Rates
            rates = {"IDT/Business": 0.725, "Medical": 0.205, "Charity": 0.14, "Personal": 0.00}
            miles = end - start
            deduction = round(miles * rates[cat], 2)
            # FUEL COST ENGINE: (Miles / MPG) * Price
            fuel_cost = round((miles / current_mpg) * gas_price, 2)
            
            db.table("logs").insert({
                "user_id": uid, "date": str(date), "miles": miles, "destination": dest,
                "purpose": f"[{cat}] {purpose}", "total_deduction": deduction,
                "vehicle_name": selected_v, "fuel_gas": fuel_cost,
                "start_odo": start, "end_odo": end
            }).execute()
            st.success(f"✅ Mission Logged! Deduction: ${deduction} | Est. Fuel Cost: ${fuel_cost}")

# --- 7. SECTOR: IDT TACTICAL (Detailed) ---
elif nav == "IDT Tactical":
    st.header("✈️ IDT Unreimbursed Logistics")
    st.info("IRS Form 2106 Above-the-Line Tracking ($750 Cap Check)")
    
    with st.form("idt_detail"):
        col1, col2 = st.columns(2)
        with col1:
            m_airport = st.number_input("POV Miles to/from Airport", value=0.0)
            lodging = st.number_input("Hotel/Lodging (Actual Spend)", value=0.0)
            tolls_park = st.number_input("Tolls & Airport Parking", value=0.0)
        with col2:
            transit = st.number_input("Uber/Taxi/Transit", value=0.0)
            meals = st.number_input("Total Meals Cost (App applies 50% rule)", value=0.0)
            reimb = st.number_input("Gov Reimbursement (Voucher)", value=750.0)
        
        incid = st.number_input("Laundry/Incidentals", value=0.0)
        
        if st.form_submit_button("CALCULATE NET TAX DEDUCTION"):
            # IRS Form 2106 Calculation Logic
            total_eligible = (m_airport * 0.725) + lodging + tolls_park + transit + incid + (meals * 0.5)
            net_deduct = max(0.0, total_eligible - reimb)
            st.metric("Net Schedule 1 Deduction", f"${net_deduct:,.2f}")

# --- 8. SECTOR: THE GARAGE ---
elif nav == "The Garage":
    st.header("🚘 Vehicle Fleet Registration")
    with st.form("add_vehicle", clear_on_submit=True):
        v_name = st.text_input("Vehicle Name/Model")
        v_mpg = st.number_input("Average MPG (for fuel tracking)", min_value=1.0, value=20.0)
        if st.form_submit_button("REGISTER TO COMMAND"):
            db.table("vehicles").insert({"user_id": uid, "name": v_name, "mpg": v_mpg}).execute()
            st.success(f"{v_name} added to fleet.")
            st.rerun()

# --- 9. SECTOR: REPORTS ---
elif nav == "Reports":
    st.header("📊 Tactical Tax Reports")
    try:
        report_res = db.table("logs").select("*").eq("user_id", uid).execute()
        if report_res.data:
            df = pd.DataFrame(report_res.data)
            st.dataframe(df[["date", "vehicle_name", "purpose", "miles", "total_deduction", "fuel_gas"]])
            st.download_button("📥 Download Excel/CSV Report", df.to_csv(index=False), "MilPro_2026_Tax.csv")
    except Exception as e:
        st.error(f"Report Error: {e}")
