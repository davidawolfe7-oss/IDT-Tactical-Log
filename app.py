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
    st.error("Missing Secrets: Check SUPABASE_URL and SUPABASE_KEY in Streamlit Settings.")
    st.stop()

# --- AUTHENTICATION MODULE ---
def login_signup():
    st.title("🪖 Mil-Pro Command")
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.rerun()
            except Exception as e:
                st.error(f"Login Failed: {e}")

    with tab2:
        new_email = st.text_input("New Email", key="sig_email")
        new_password = st.text_input("New Password", type="password", key="sig_pass")
        if st.button("Create Account"):
            try:
                supabase.auth.sign_up({"email": new_email, "password": new_password})
                st.success("Account created! Check your email for a confirmation link.")
            except Exception as e:
                st.error(f"Signup Failed: {e}")

# Check session state
if 'user' not in st.session_state:
    login_signup()
    st.stop()

# --- MAIN APP INTERFACE ---
user_id = st.session_state.user.id

# Sidebar Navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to:", ["Mission Log", "Dashboard & History", "Settings"])
if st.sidebar.button("Logout"):
    supabase.auth.sign_out()
    del st.session_state.user
    st.rerun()

# PAGE 1: MISSION LOG
if page == "Mission Log":
    st.header("📋 Log New Mission")
    with st.form("log_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date_input = st.date_input("Mission Date", datetime.date.today())
            destination = st.text_input("Destination (Unit/City)")
        with col2:
            miles = st.number_input("Total Round Trip Miles", min_value=0.0, step=0.1)
            purpose = st.selectbox("Purpose", ["IDT Drill", "Annual Training", "RMP", "Other"])
        
        vehicle = st.text_input("Vehicle", value="Primary Vehicle")
        
        if st.form_submit_button("SAVE TO TACTICAL LOG"):
            try:
                # Tax Rate for 2024-2026 is approx $0.67
                deduction = round(miles * 0.67, 2)
                
                new_entry = {
                    "user_id": user_id,
                    "date": str(date_input),
                    "destination": destination,
                    "purpose": purpose,
                    "miles": miles,
                    "vehicle_name": vehicle,
                    "total_deduction": deduction
                }
                supabase.table("logs").insert(new_entry).execute()
                st.success("✅ Mission Saved to Database!")
                st.balloons()
            except Exception as e:
                st.error(f"Error saving mission: {e}")

# PAGE 2: DASHBOARD & HISTORY
elif page == "Dashboard & History":
    st.header("📊 Tactical Overview")
    
    try:
        # Fetch data for current user
        res = supabase.table("logs").select("*").eq("user_id", user_id).execute()
        df = pd.DataFrame(res.data)
        
        if not df.empty:
            # Dashboard Metrics
            total_miles = df['miles'].sum()
            total_deduct = df['total_deduction'].sum()
            
            c1, c2 = st.columns(2)
            c1.metric("Total Mileage", f"{total_miles} mi")
            c2.metric("Total Tax Deduction", f"${total_deduct:,.2f}")
            
            st.divider()
            st.subheader("Mission History")
            st.dataframe(df[["date", "destination", "purpose", "miles", "total_deduction"]], use_container_width=True)
        else:
            st.info("No missions logged yet. Head over to the 'Mission Log' tab to start.")
            
    except Exception as e:
        st.error(f"Could not load history: {e}")

# PAGE 3: SETTINGS
elif page == "Settings":
    st.header("⚙️ Profile & Settings")
    st.write(f"Logged in as: **{st.session_state.user.email}**")
    st.info("Additional vehicle profiles and IDT reimbursement tracking settings coming soon.")
