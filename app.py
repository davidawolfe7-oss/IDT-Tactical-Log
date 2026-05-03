import streamlit as st
from supabase import create_client
import datetime
import pandas as pd

# --- 1. SETTINGS & BOOTSTRAP ---
st.set_page_config(page_title="Mil-Pro Command", layout="wide")

# --- 2. DATABASE UTILITY ---
def get_db():
    if "SUPABASE_URL" not in st.secrets:
        st.error("Missing SUPABASE_URL in Streamlit Secrets")
        st.stop()
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# --- 3. SESSION STATE ---
if 'user' not in st.session_state:
    st.session_state.user = None

# --- 4. MAIN APPLICATION ---
def main():
    # --- UI: FORCED NIGHT OPS THEME (V2) ---
    st.markdown("""
        <style>
        /* Force background on the main app container and all parent wrappers */
        .stApp, .main, .block-container {
            background: linear-gradient(rgba(0, 0, 0, 0.85), rgba(0, 0, 0, 0.85)), 
                        url('https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?auto=format&fit=crop&q=80&w=2000') !important;
            background-size: cover !important;
            background-attachment: fixed !important;
            background-position: center !important;
            color: #FFFFFF !important;
        }

        /* Sidebar Styling - Solid Dark */
        [data-testid="stSidebar"] {
            background-color: #0E1117 !important;
            border-right: 1px solid #444;
        }

        /* High-Contrast Typography */
        h1, h2, h3, h4, h5, h6, p, span, label {
            color: #FFFFFF !important;
            text-shadow: 2px 2px 4px #000000 !important;
        }

        /* Metric Cards - Old Glory Red Accent */
        [data-testid="stMetric"] {
            background-color: rgba(255, 255, 255, 0.1) !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            border-left: 6px solid #B22234 !important; /* Old Glory Red */
            padding: 20px !important;
            border-radius: 10px !important;
        }

        /* Tactical Buttons - Old Glory Blue */
        .stButton>button {
            background-color: #3C3B6E !important; /* Old Glory Blue */
            color: #FFFFFF !important;
            border: 1px solid #FFFFFF !important;
            font-weight: bold !important;
            text-transform: uppercase !important;
            letter-spacing: 1px !important;
            width: 100% !important;
            border-radius: 5px !important;
        }
        .stButton>button:hover {
            background-color: #B22234 !important;
            border-color: #FFFFFF !important;
        }

        /* Inputs & Forms - Dark Transparent */
        div[data-testid="stForm"] {
            background-color: rgba(0, 0, 0, 0.6) !important;
            border: 1px solid #444 !important;
            border-radius: 12px !important;
        }
        
        input, select, textarea {
            background-color: #1A1C23 !important;
            color: #FFFFFF !important;
            border: 1px solid #444 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("🪖 MIL-PRO COMMAND")
    st.caption("Tactical Logistics & Tax Tracking | 2026 Edition")

    # --- 5. AUTHENTICATION GATE ---
    if not st.session_state.user:
        with st.form("login_form"):
            st.subheader("SECURE LOGIN REQUIRED")
            email = st.text_input("User Email")
            pw = st.text_input("Access Key", type="password")
            if st.form_submit_button("AUTHENTICATE"):
                try:
                    db = get_db()
                    res = db.auth.sign_in_with_password({"email": email, "password": pw})
                    st.session_state.user = res.user
                    st.rerun()
                except Exception as e:
                    st.error(f"Login Failed: {e}")
        return

    # --- 6. COMMAND SECTOR (LOGGED IN) ---
    db = get_db()
    uid = st.session_state.user.id

    # SIDEBAR
    st.sidebar.title("⚓ COMMAND CENTER")
    
    # Vehicle Database
    v_options = ["Standard Unit"]
    v_mpg_map = {"Standard Unit": 20.0}
    try:
        v_res = db.table("vehicles").select("name", "mpg").eq("user_id", uid).execute()
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
        db.auth.sign_out()
        st.session_state.user = None
        st.rerun()

    # --- 7. SECTOR: MISSION LOG ---
    if nav == "Mission Log":
        st.header(f"📍 Mission Log: {selected_v}")
        
        with st.form("mission_entry", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                date = st.date_input("Mission Date", datetime.date.today())
                cat = st.selectbox("Category", ["IDT/Business", "Medical", "Charity", "Personal"])
                start = st.number_input("Start Odometer")
            with c2:
                end = st.number_input("End Odometer")
                dest = st.text_input("Destination")
            
            purpose = st.text_input("Mission Purpose")

            if st.form_submit_button("LOG MISSION"):
                # 2026 Mileage Rates
                rates = {"IDT/Business": 0.725, "Medical": 0.205, "Charity": 0.14, "Personal": 0.00}
                miles = end - start
                if miles < 0:
                    st.error("Negative mileage detected. Re-check odometers.")
                else:
                    deduct = round(miles * rates[cat], 2)
                    fuel = round((miles / current_mpg) * gas_price, 2)
                    
                    db.table("logs").insert({
                        "user_id": uid, "date": str(date), "miles": miles, "destination": dest,
                        "purpose": f"[{cat}] {purpose}", "total_deduction": deduct,
                        "vehicle_name": selected_v, "fuel_gas": fuel,
                        "start_odo": start, "end_odo": end
                    }).execute()
                    st.success(f"Log Confirmed. Deduction: ${deduct} | Est. Fuel Cost: ${fuel}")

    # --- 8. SECTOR: IDT TACTICAL ---
    elif nav == "IDT Tactical":
        st.header("✈️ IDT Logistics")
        st.info("IRS Form 2106 / Schedule 1 Logic: 2026 Tax Year")
        with st.form("idt_form"):
            c1, c2 = st.columns(2)
            with c1:
                m_airport = st.number_input("POV Miles (Airport)", value=0.0)
                lodging = st.number_input("Lodging Spend", value=0.0)
                tolls = st.number_input("Tolls & Parking", value=0.0)
            with c2:
                transit = st.number_input("Uber/Taxi", value=0.0)
                meals = st.number_input("Total Meals", value=0.0)
                reimb = st.number_input("Reimbursement Received", value=750.0)
            
            incid = st.number_input("Incidentals/Laundry", value=0.0)
            
            if st.form_submit_button("CALCULATE NET TAX DEDUCTION"):
                # IRS Logic: (Transport + 50% Meals) - Reimbursement
                total_exp = (m_airport * 0.725) + lodging + tolls + transit + incid + (meals * 0.5)
                net = max(0.0, total_exp - reimb)
                st.metric("Net Schedule 1 Deduction", f"${net:,.2f}")

    # --- 9. SECTOR: THE GARAGE ---
    elif nav == "The Garage":
        st.header("🚘 Fleet Management")
        with st.form("garage_form", clear_on_submit=True):
            vn = st.text_input("Vehicle Name")
            vm = st.number_input("MPG Rating", min_value=1.0, value=20.0)
            if st.form_submit_button("REGISTER VEHICLE"):
                db.table("vehicles").insert({"user_id": uid, "name": vn, "mpg": vm}).execute()
                st.success(f"{vn} Registered.")

    # --- 10. SECTOR: REPORTS ---
    elif nav == "Reports":
        st.header("📊 Tax Export")
        try:
            res = db.table("logs").select("*").eq("user_id", uid).execute()
            if res.data:
                df = pd.DataFrame(res.data)
                st.dataframe(df)
                st.download_button("📥 Export 2026 CSV", df.to_csv(index=False), "MilPro_2026_Report.csv")
        except Exception as e:
            st.error(f"Data Retrieval Error: {e}")

if __name__ == "__main__":
    main()
