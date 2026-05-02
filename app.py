import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, timedelta

# --- CLOUD CONNECTION ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- APP CONFIG ---
st.set_page_config(page_title="Mil-Pro Command", layout="wide", page_icon="🇺🇸")

# --- AUTH LOGIC ---
if 'user' not in st.session_state:
    st.session_state.user = None

def login():
    with st.sidebar:
        st.title("🔐 ACCESS CONTROL")
        email = st.text_input("Service Email")
        password = st.text_input("Password", type="password")
        col1, col2 = st.columns(2)
        
        if col1.button("LOGIN"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.rerun()
            except Exception as e:
                st.error("Invalid Credentials")

        if col2.button("SIGN UP"):
            try:
                supabase.auth.sign_up({"email": email, "password": password})
                st.info("Check your email for a confirmation link!")
            except Exception as e:
                st.error(str(e))

def logout():
    supabase.auth.sign_out()
    st.session_state.user = None
    st.rerun()

# --- MAIN ROUTING ---
if st.session_state.user is None:
    login()
    st.title("🇺🇸 MIL-PRO COMMAND")
    st.info("Please login or sign up in the sidebar to access your tactical logs.")
    st.stop() # Stops the rest of the app from loading

# --- IF LOGGED IN, SHOW THE DASHBOARD ---
user_id = st.session_state.user.id
st.sidebar.success(f"Logged in: {st.session_state.user.email}")
if st.sidebar.button("LOGOUT"):
    logout()

# --- NEW DATABASE HELPERS (SUPABASE) ---
def get_vehicles():
    res = supabase.table("vehicles").select("name").execute()
    return pd.DataFrame(res.data)

def get_last_odo(v_name):
    res = supabase.table("logs").select("end_odo").eq("vehicle_name", v_name).order("created_at", desc=True).limit(1).execute()
    return res.data[0]['end_odo'] if res.data else 0.0

# --- START YOUR DASHBOARD CODE HERE ---
st.title("🦅 MISSION DASHBOARD")
# (The rest of your previous UI code for logging miles goes here, 
#  but you'll swap 'conn.execute' for 'supabase.table().insert()')
# --- LOG NEW MISSION ---
# This creates a clickable box to enter your travel
with st.expander("➕ LOG NEW TRAVEL MISSION", expanded=True):
    with st.form("log_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        
        # Capture the travel details
        date = col1.date_input("Date of Travel", datetime.now())
        dest = col2.text_input("Destination (e.g. Armory/Fort McCoy)")
        purpose = col3.selectbox("Purpose", ["IDT Drill", "Battle Assembly", "Annual Training", "Other"])
        
        miles = st.number_input("Total Miles", min_value=0, step=1)
        
        # This button sends the data to your Supabase "logs" table
        if st.form_submit_button("SAVE TO TACTICAL LOG"):
            new_log = {
                "user_id": user_id, 
                "date": str(date),
                "destination": dest,
                "purpose": purpose,
                "miles": miles
            }
            try:
                # This must match your table name in Supabase
                supabase.table("logs").insert(new_log).execute()
                st.success("✅ Mission Logged Successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error saving log: {e}")

# --- VIEW RECENT LOGS ---
st.subheader("📋 Recent Tactical Logs")
try:
    # This fetches ONLY the logs belonging to the person logged in
    res = supabase.table("logs").select("*").eq("user_id", user_id).order("date", desc=True).execute()
    
    if res.data:
        df = pd.DataFrame(res.data)
        # Display the data in a clean table
        st.dataframe(df[["date", "destination", "purpose", "miles"]], use_container_width=True)
    else:
        st.info("No logs found. Start by entering a mission above.")
except Exception as e:
    st.error(f"Could not load logs: {e}")