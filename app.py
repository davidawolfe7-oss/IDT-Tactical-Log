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
    # --- UI: NIGHT OPS HIGH-CONTRAST THEME ---
    st.markdown("""
        <style>
        .stApp {
            background: linear-gradient(rgba(0, 0, 0, 0.85), rgba(0, 0, 0, 0.85)), 
                        url('https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?auto=format&fit=crop&q=80&w=2000');
            background-size: cover;
            background-attachment: fixed;
            color: #FFFFFF;
        }
        /* Metric Cards - High Contrast */
        div[data-testid="stMetricValue"] { color: #FFFFFF !important; font-weight: 800; }
        div[data-testid="stMetricLabel"] { color: #CCCCCC !important; }
        [data-testid="stMetric"] { 
            background-color: rgba(255, 255, 255, 0.05); 
            padding: 15px; 
            border-radius: 8px; 
            border-left: 5px solid #B22234; 
        }
        /* Headers and Text Shadow */
        h1, h2, h3 { color: #FFFFFF !important; text-shadow: 2px 2px #000000; font-weight: 800; }
        /* Buttons - Tactical Blue/Red */
        .stButton>button { 
            background-color: #3C3B6E; 
            color: white; 
            border: 2px solid #FFFFFF; 
            font-weight: bold;
            width: 100%;
        }
        .stButton>button:hover { background-color: #B22234; border-color: #FFFFFF; }
        /* Form Styling */
        div[data-testid="stForm"] { 
            background-color: rgba(0,0,0,0.7); 
            padding: 20px; 
            border-radius: 10px; 
            border: 1px solid #444; 
        }
        /* Sidebar Styling */
        section[data-testid="stSidebar"] {
            background-color: rgba(20, 20, 20, 0.95);
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("🪖 MIL-PRO COMMAND")
    st.caption("Tactical Logistics & Tax Tracking | 2026 Edition")

    # --- 5. AUTHENTICATION GATE ---
    if not st.session_state.user:
        with st.form("login_form"):
            st.subheader("Secure Access Required")
            email = st.text_input("Email")
            pw = st.text_input("Password", type="password")
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

    # SIDEBAR SETUP
    st.sidebar.title("⚓ COMMAND CENTER")
    
    # Vehicle Engine
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
                date = st.date_input("Date", datetime.date.today())
                cat = st.selectbox("Category", ["IDT/Business", "Medical", "Charity", "Personal"])
                start = st.number_input("Start Odometer", min_value=0.0)
            with c2:
                end = st.number_input("End Odometer", min_value=0.0)
                dest = st.text_input("Destination")
            
            purpose = st.text_input("Purpose")

            if st.form_submit_button("LOG MISSION"):
                # 2026 Mileage Rates
                rates = {"IDT/Business": 0.725, "Medical": 0.205, "Charity": 0.14, "Personal": 0.00}
                miles = end - start
                if miles < 0:
                    st.error("End odometer cannot be less than start.")
                else:
                    deduct = round(miles * rates[cat], 2)
                    fuel = round((miles / current_mpg) * gas_price, 2)
                    
                    db.table("logs").insert({
                        "user_id": uid, "date": str(date), "miles": miles, "destination": dest,
                        "purpose": f"[{cat}] {purpose}", "total_deduction": deduct,
                        "vehicle_name": selected_v, "fuel_gas": fuel,
                        "start_odo": start, "end_odo": end
                    }).execute()
                    st.success(f"✅ Mission Logged. Deduction: ${deduct} | Est. Fuel Cost: ${fuel}")

    # --- 8. SECTOR: IDT TACTICAL ---
    elif nav == "IDT Tactical":
        st.header("✈️ IDT Logistics")
        st.info("IRS Form 2106 / Schedule 1 Above-the-Line Calculations")
        with st.form("idt_form"):
            c1, c2 = st.columns(2)
            with c1:
                m_airport = st.number_input("POV Miles to/from Airport", value=0.0)
                lodging = st.number_input("Lodging (Out-of-Pocket)", value=0.0)
                tolls = st.number_input("Tolls & Parking", value=0.0)
            with c2:
                transit = st.number_input("Uber/Taxi/Transit", value=0.0)
                meals = st.number_input("Total Meals Cost", value=0.0)
                reimb = st.number_input("Gov Reimbursement Received", value=750.0)
            
            incid = st.number_input("Laundry/Incidentals", value=0.0)
            
            if st.form_submit_button("CALCULATE NET IMPACT"):
                # 2026 Calculation with 50% meal limitation and $750 cap check
                total_exp = (m_airport * 0.725) + lodging + tolls + transit + incid + (meals * 0.5)
                net = max(0.0, total_exp - reimb)
                st.metric("Net Schedule 1 Deduction", f"${net:,.2f}")

    # --- 9. SECTOR: THE GARAGE ---
    elif nav == "The Garage":
        st.header("🚘 Fleet Management")
        with st.form("garage_form", clear_on_submit=True):
            vn = st.text_input("Vehicle Name (e.g., '2026 SUV')")
            vm = st.number_input("Average MPG", min_value=1.0, value=20.0)
            if st.form_submit_button("REGISTER VEHICLE"):
                db.table("vehicles").insert({"user_id": uid, "name": vn, "mpg": vm}).execute()
                st.success(f"{vn} successfully added to the fleet.")

    # --- 10. SECTOR: REPORTS ---
    elif nav == "Reports":
        st.header("📊 Tax Export")
        try:
            res = db.table("logs").select("*").eq("user_id", uid).execute()
            if res.data:
                df = pd.DataFrame(res.data)
                st.dataframe(df)
                st.download_button("📥 Download 2026 Tax CSV", df.to_csv(index=False), "MilPro_2026_Export.csv")
            else:
                st.warning("No mission logs found for this user.")
        except Exception as e:
            st.error(f"Report Generation Error: {e}")

if __name__ == "__main__":
    main()
