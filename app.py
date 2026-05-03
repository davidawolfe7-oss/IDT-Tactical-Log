import streamlit as st
from supabase import create_client
import datetime
import pandas as pd

# --- 1. SETTINGS ---
st.set_page_config(page_title="Mil-Pro Command", layout="wide")

# --- 2. DATABASE UTILITY ---
def get_db():
    # Defensive check for secrets
    if "SUPABASE_URL" not in st.secrets:
        st.error("Missing SUPABASE_URL in Streamlit Secrets")
        st.stop()
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# --- 3. SESSION STATE ---
if 'user' not in st.session_state:
    st.session_state.user = None

# --- 4. APP LOGIC ---
def main():
    # Simple UI Header (Replacing complex CSS to prevent Line 8 errors)
    st.title("🪖 MIL-PRO COMMAND")
    st.caption("Tactical Logistics & Tax Tracking | 2026 Edition")

    # AUTHENTICATION GATE
    if not st.session_state.user:
        with st.form("login_form"):
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

    # LOGGED IN CONTEXT
    db = get_db()
    uid = st.session_state.user.id

    # SIDEBAR
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

    # SECTOR: MISSION LOG
    if nav == "Mission Log":
        st.header(f"📍 Mission Log: {selected_v}")
        
        with st.form("mission_entry", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                date = st.date_input("Date", datetime.date.today())
                cat = st.selectbox("Category", ["IDT/Business", "Medical", "Charity", "Personal"])
                start = st.number_input("Start Odometer")
            with c2:
                end = st.number_input("End Odometer")
                dest = st.text_input("Destination")
            
            purpose = st.text_input("Purpose")

            if st.form_submit_button("LOG MISSION"):
                # 2026 Rates
                rates = {"IDT/Business": 0.725, "Medical": 0.205, "Charity": 0.14, "Personal": 0.00}
                miles = end - start
                deduct = round(miles * rates[cat], 2)
                fuel = round((miles / current_mpg) * gas_price, 2)
                
                db.table("logs").insert({
                    "user_id": uid, "date": str(date), "miles": miles, "destination": dest,
                    "purpose": f"[{cat}] {purpose}", "total_deduction": deduct,
                    "vehicle_name": selected_v, "fuel_gas": fuel,
                    "start_odo": start, "end_odo": end
                }).execute()
                st.success(f"Mission Logged. Deduction: ${deduct} | Fuel: ${fuel}")

    # SECTOR: IDT TACTICAL
    elif nav == "IDT Tactical":
        st.header("✈️ IDT Logistics")
        with st.form("idt_form"):
            c1, c2 = st.columns(2)
            with c1:
                m_airport = st.number_input("Airport Miles", value=0.0)
                lodging = st.number_input("Lodging", value=0.0)
                tolls = st.number_input("Tolls/Parking", value=0.0)
            with c2:
                transit = st.number_input("Uber/Taxi", value=0.0)
                meals = st.number_input("Total Meals", value=0.0)
                reimb = st.number_input("Gov Reimbursement", value=750.0)
            
            incid = st.number_input("Incidentals", value=0.0)
            
            if st.form_submit_button("CALCULATE"):
                total = (m_airport * 0.725) + lodging + tolls + transit + incid + (meals * 0.5)
                net = max(0.0, total - reimb)
                st.metric("Net Schedule 1 Deduction", f"${net:,.2f}")

    # SECTOR: THE GARAGE
    elif nav == "The Garage":
        st.header("🚘 Fleet Management")
        with st.form("garage_form"):
            vn = st.text_input("Vehicle Name")
            vm = st.number_input("MPG", min_value=1.0, value=20.0)
            if st.form_submit_button("REGISTER"):
                db.table("vehicles").insert({"user_id": uid, "name": vn, "mpg": vm}).execute()
                st.success(f"{vn} registered.")

    # SECTOR: REPORTS
    elif nav == "Reports":
        st.header("📊 Tax Export")
        try:
            res = db.table("logs").select("*").eq("user_id", uid).execute()
            if res.data:
                df = pd.DataFrame(res.data)
                st.dataframe(df)
                st.download_button("Export CSV", df.to_csv(index=False), "MilPro_2026.csv")
        except Exception as e:
            st.error(f"Error: {e}")

if __name__ == "__main__":
    main()
