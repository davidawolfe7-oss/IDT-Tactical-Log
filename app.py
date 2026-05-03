import streamlit as st
import datetime
import pandas as pd

# --- 1. SYSTEM ARCHITECT CONFIG ---
st.set_page_config(page_title="Mil-Pro Command", layout="wide")

# --- 2. NIGHT OPS UI (FLAGS & HIGH CONTRAST) ---
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

# --- 3. DYNAMIC DEPENDENCY HANDLER ---
def get_db_client():
    """Bulletproof library import to prevent startup line-errors."""
    try:
        from supabase import create_client
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except ImportError:
        st.error("Missing dependency: 'supabase'. Ensure it is in your requirements.txt.")
        st.stop()
    except Exception as e:
        st.error(f"Database Config Error: {e}")
        st.stop()

# --- 4. TACTICAL RATES (2026) ---
RATES = {"IDT/Business": 0.725, "Medical": 0.205, "Charity": 0.14}

# --- 5. SESSION STATE INITIALIZATION ---
if 'user' not in st.session_state:
    st.session_state.user = None

# --- 6. AUTHENTICATION ---
if not st.session_state.user:
    st.title("🪖 Mil-Pro Command: Secure Login")
    with st.form("auth_gate"):
        email = st.text_input("Email")
        pw = st.text_input("Password", type="password")
        if st.form_submit_button("AUTHENTICATE"):
            db = get_db_client()
            try:
                res = db.auth.sign_in_with_password({"email": email, "password": pw})
                st.session_state.user = res.user
                st.rerun()
            except Exception as e:
                st.error(f"Login Failed: {e}")
    st.stop()

# --- 7. COMMAND SECTOR (LOGGED IN) ---
uid = st.session_state.user.id
db = get_db_client()

st.sidebar.title("⚓ COMMAND CENTER")

# Fleet Management Engine
v_options = ["Standard Unit"]
v_mpg_map = {"Standard Unit": 20.0}
try:
    v_query = db.table("vehicles").select("name, mpg").eq("user_id", uid).execute()
    if v_query.data:
        v_options = [v['name'] for v in v_query.data]
        v_mpg_map = {v['name']: float(v['mpg']) for v in v_res.data}
except: pass

selected_v = st.sidebar.selectbox("Active Vehicle", v_options)
current_mpg = v_mpg_map.get(selected_v, 20.0)
gas_price = st.sidebar.number_input("Gas Price ($/Gal)", value=3.50)

nav = st.sidebar.radio("Sectors", ["Mission Log", "IDT Tactical", "The Garage", "Reports"])

if st.sidebar.button("LOGOUT"):
    db.auth.sign_out()
    st.session_state.user = None
    st.rerun()

# --- 8. SECTOR: MISSION LOG ---
if nav == "Mission Log":
    st.header(f"📍 Daily Sortie: {selected_v}")
    
    last_odo = 0.0
    try:
        odo_res = db.table("logs").select("end_odo").eq("user_id", uid).order("created_at", desc=True).limit(1).execute()
        if odo_res.data: last_odo = float(odo_res.data[0]['end_odo'])
    except: pass

    with st.form("mission_entry", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("Date", datetime.date.today())
            cat = st.selectbox("Category", list(RATES.keys()))
            start = st.number_input("Start Odometer", value=last_odo)
        with col2:
            end = st.number_input("End Odometer", min_value=start)
            dest = st.text_input("Destination")
        
        purpose = st.text_input("Purpose")

        if st.form_submit_button("LOG MISSION"):
            miles = end - start
            deduct = round(miles * RATES[cat], 2)
            # Fuel Engine: (Miles / MPG) * Price
            fuel = round((miles / current_mpg) * gas_price, 2)
            
            db.table("logs").insert({
                "user_id": uid, "date": str(date), "miles": miles, "destination": dest,
                "purpose": f"[{cat}] {purpose}", "total_deduction": deduct,
                "vehicle_name": selected_v, "fuel_gas": fuel,
                "start_odo": start, "end_odo": end
            }).execute()
            st.success(f"✅ Logged! Deduction: ${deduct} | Fuel: ${fuel}")

# --- 9. SECTOR: IDT TACTICAL ---
elif nav == "IDT Tactical":
    st.header("✈️ IDT Unreimbursed Logistics")
    st.info("IRS Form 2106 Above-the-Line Tracking")
    
    with st.form("idt_form"):
        c1, c2 = st.columns(2)
        with c1:
            m_airport = st.number_input("Airport Miles (POV)", value=0.0)
            lodging = st.number_input("Lodging (Out-of-Pocket)", value=0.0)
            tolls = st.number_input("Tolls & Parking", value=0.0)
        with c2:
            transit = st.number_input("Uber/Taxi/Transit", value=0.0)
            meals = st.number_input("Total Meals (App applies 50% rule)", value=0.0)
            reimb = st.number_input("Gov Reimbursement Received", value=750.0)
        
        incid = st.number_input("Laundry/Incidentals", value=0.0)
        
        if st.form_submit_button("CALCULATE NET IMPACT"):
            total_exp = (m_airport * 0.725) + lodging + tolls + transit + incid + (meals * 0.5)
            net = max(0.0, total_exp - reimb)
            st.metric("Net Schedule 1 Deduction", f"${net:,.2f}")

# --- 10. SECTOR: THE GARAGE ---
elif nav == "The Garage":
    st.header("🚘 Fleet Management")
    with st.form("garage_form", clear_on_submit=True):
        vn = st.text_input("Vehicle Name")
        vm = st.number_input("Avg MPG", min_value=1.0, value=20.0)
        if st.form_submit_button("REGISTER"):
            db.table("vehicles").insert({"user_id": uid, "name": vn, "mpg": vm}).execute()
            st.success(f"{vn} Registered.")
            st.rerun()

# --- 11. REPORTS ---
elif nav == "Reports":
    st.header("📊 Tax Export")
    try:
        data = db.table("logs").select("*").eq("user_id", uid).execute()
        if data.data:
            df = pd.DataFrame(data.data)
            st.dataframe(df[["date", "vehicle_name", "purpose", "miles", "total_deduction", "fuel_gas"]])
            st.download_button("📥 Export CSV", df.to_csv(index=False), "MilPro_2026.csv")
    except Exception as e:
        st.error(f"Error: {e}")
