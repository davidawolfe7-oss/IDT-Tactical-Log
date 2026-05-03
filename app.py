import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd

# 1. Page Configuration
st.set_page_config(page_title="Mil-Pro Command", page_icon="🪖", layout="wide")

# 2. Setup Connection
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Check Streamlit Secrets for SUPABASE_URL and SUPABASE_KEY.")
    st.stop()

# --- IRS 2026 OFFICIAL RATES ---
RATES = {
    "IDT/Business": 0.725,
    "Medical": 0.205,
    "Charity": 0.14,
    "Personal": 0.00
}

# --- AUTHENTICATION ---
def login_signup():
    st.title("🪖 Mil-Pro Command")
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    with tab1:
        email = st.text_input("Email", key="l_email")
        password = st.text_input("Password", type="password", key="l_pass")
        if st.button("Login"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.rerun()
            except Exception as e:
                st.error(f"Login Failed: {e}")
    with tab2:
        new_email = st.text_input("New Email", key="s_email")
        new_pass = st.text_input("New Password", type="password", key="s_pass")
        if st.button("Create Account"):
            try:
                supabase.auth.sign_up({"email": new_email, "password": new_pass})
                st.success("Account created! Check email for confirmation.")
            except Exception as e:
                st.error(f"Signup Failed: {e}")

if 'user' not in st.session_state:
    login_signup()
    st.stop()

user_id = st.session_state.user.id

# --- HELPER: GET VEHICLES ---
def get_user_vehicles():
    try:
        res = supabase.table("vehicles").select("name").eq("user_id", user_id).execute()
        return [v['name'] for v in res.data] if res.data else ["Primary Vehicle"]
    except:
        return ["Primary Vehicle"]

# --- NAVIGATION ---
page = st.sidebar.radio("Command Center", ["Trip Logger", "The Garage", "Tax Dashboard", "Settings"])
if st.sidebar.button("Logout"):
    supabase.auth.sign_out()
    del st.session_state.user
    st.rerun()

# --- PAGE: TRIP LOGGER ---
if page == "Trip Logger":
    st.header("📍 Log Tactical Travel")
    vehicles = get_user_vehicles()
    
    with st.form("main_log", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date_in = st.date_input("Mission Date", datetime.date.today())
            category = st.selectbox("Travel Category", list(RATES.keys()))
            destination = st.text_input("Destination")
        
        with col2:
            miles = st.number_input("Round Trip Miles", min_value=0.0, step=0.1)
            purpose = st.text_input("Purpose (e.g., Drill, VA Appt)")
            vehicle_used = st.selectbox("Vehicle Used", vehicles)

        st.divider()
        st.write("**Odometer (Optional)**")
        oc1, oc2 = st.columns(2)
        start_odo = oc1.number_input("Start Odometer", min_value=0)
        end_odo = oc2.number_input("End Odometer", min_value=0)

        if st.form_submit_button("SAVE MISSION LOG"):
            try:
                rate = RATES.get(category, 0.00)
                deduction = round(miles * rate, 2)
                reimb = min(750.00, deduction) if category == "IDT/Business" else 0.00

                new_entry = {
                    "user_id": user_id, "date": str(date_in), "destination": destination,
                    "purpose": f"[{category}] {purpose}", "miles": miles,
                    "vehicle_name": vehicle_used, "start_odo": start_odo, "end_odo": end_odo,
                    "total_deduction": deduction, "reimbursement": reimb
                }
                supabase.table("logs").insert(new_entry).execute()
                st.success(f"✅ Logged! Deduction: ${deduction}")
                st.balloons()
            except Exception as e:
                st.error(f"Save Error: {e}")

# --- PAGE: THE GARAGE ---
elif page == "The Garage":
    st.header("🚘 Vehicle Management")
    
    with st.form("add_vehicle", clear_on_submit=True):
        v_name = st.text_input("Vehicle Name (e.g., 2026 Suburban)")
        v_type = st.selectbox("Type", ["Personal", "Work-Only", "Medical Support"])
        if st.form_submit_button("Save to Garage"):
            try:
                supabase.table("vehicles").insert({"user_id": user_id, "name": v_name, "vehicle_type": v_type}).execute()
                st.success(f"Added {v_name} to your fleet!")
            except Exception as e:
                st.error(f"Error: {e}")

    st.subheader("Your Fleet")
    try:
        v_res = supabase.table("vehicles").select("*").eq("user_id", user_id).execute()
        if v_res.data:
            st.table(pd.DataFrame(v_res.data)[["name", "vehicle_type"]])
    except:
        st.write("No vehicles saved yet.")

# --- PAGE: TAX DASHBOARD ---
elif page == "Tax Dashboard":
    st.header("📊 Tax & Reimbursement Overview")
    try:
        res = supabase.table("logs").select("*").eq("user_id", user_id).execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Mileage", f"{df['miles'].sum()} mi")
            m2.metric("Total Deduction", f"${df['total_deduction'].sum():,.2f}")
            m3.metric("IDT Reimbursement", f"${df['reimbursement'].sum():,.2f}")
            st.dataframe(df, use_container_width=True)
            st.download_button("📥 Download Tax Report", df.to_csv(index=False).encode('utf-8'), "tax_report.csv", "text/csv")
    except Exception as e:
        st.error(f"Load Error: {e}")

# --- PAGE: SETTINGS ---
elif page == "Settings":
    st.header("⚙️ Settings")
    st.write(f"Account: {st.session_state.user.email}")
    st.write("### 2026 IRS Rates: Business: 72.5¢ | Medical: 20.5¢ | Charity: 14¢")
