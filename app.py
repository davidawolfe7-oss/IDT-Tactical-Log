import streamlit as st
from supabase import create_client, Client
import datetime

# 1. Setup Connection
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.title("🪖 Mil-Pro Command: Tactical Log")
st.subheader("IDT Travel & Tax Tracker")

# 2. Input Fields
with st.form("log_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    
    with col1:
        date_input = st.date_input("Mission Date", datetime.date.today())
        destination = st.text_input("Destination", placeholder="e.g., Fort McCoy")
    
    with col2:
        miles = st.number_input("Round Trip Miles", min_value=0.0, step=0.1)
        purpose = st.selectbox("Purpose", ["IDT Drill", "Annual Training", "Mobilization", "Other"])

    vehicle = st.text_input("Vehicle Name", value="Personal Vehicle")
    
    submit = st.form_submit_button("SAVE TO TACTICAL LOG")

# 3. Save Logic
if submit:
    try:
        # We build the dictionary to match the Supabase columns exactly
        new_entry = {
            "date": str(date_input),
            "destination": destination,
            "purpose": purpose,
            "miles": miles,
            "vehicle_name": vehicle,
            # These calculate the tax logic (approx $0.67/mile for 2024-2026)
            "total_deduction": round(miles * 0.67, 2)
        }

        response = supabase.table("logs").insert(new_entry).execute()
        
        st.success("✅ Mission Logged Successfully!")
        st.balloons()
        
    except Exception as e:
        st.error(f"⚠️ Tactical Failure: {e}")
