import streamlit as st
import extra_streamlit_components as stx
from supabase import create_client
import datetime
import pandas as pd

# --- 1. BOOTSTRAP ---
st.set_page_config(page_title="Mil-Pro Command", layout="wide")

# --- 2. DATABASE UTILITY ---
def get_db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

def get_manager():
    if "cookie_manager" not in st.session_state:
        st.session_state.cookie_manager = stx.CookieManager(key="mil_pro_v3_mgr")
    return st.session_state.cookie_manager

# --- 3. MAIN APP ---
def main():
    manager = get_manager()
    
    # NIGHT OPS THEME
    st.markdown("""
        <style>
        .stApp {
            background: linear-gradient(rgba(0,0,0,0.85), rgba(0,0,0,0.85)), 
            url('https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?auto=format&fit=crop&q=80&w=2000');
            background-size: cover; background-attachment: fixed; color: white;
        }
        div[data-testid="stForm"] { background-color: rgba(0,0,0,0.8); border: 1px solid #3C3B6E; padding: 25px; }
        </style>
    """, unsafe_allow_html=True)

    # AUTH GATE
    if "user" not in st.session_state:
        st.session_state.user = manager.get('mil_pro_user_id')

    if st.session_state.user is None:
        st.title("🪖 MIL-PRO COMMAND")
        with st.form("auth_form"):
            email = st.text_input("Email")
            pw = st.text_input("Access Key", type="password")
            if st.form_submit_button("AUTHENTICATE"):
                try:
                    db = get_db()
                    res = db.auth.sign_in_with_password({"email": email, "password": pw})
                    st.session_state.user = res.user.id
                    manager.set('mil_pro_user_id', res.user.id)
                    st.rerun()
                except: st.error("Authentication Failed.")
        return

    # COMMAND CENTER
    db = get_db()
    uid = st.session_state.user
    
    nav = st.sidebar.radio("Sectors", ["Mission Logistics", "Intelligence"])
    if st.sidebar.button("LOGOUT"):
        manager.delete('mil_pro_user_id')
        st.session_state.user = None
        st.rerun()

    if nav == "Mission Logistics":
        st.header("✈️ Comprehensive Logistics & Per Diem")
        
        tab1, tab2, tab3 = st.tabs(["Duty Travel", "Gear & Uniforms", "Medical/VA"])

        with tab1:
            with st.form("travel_v3", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    t_date = st.date_input("Travel Date", key="date_id")
                    miles_act = st.number_input("Actual Round-Trip Miles (POV)", min_value=0.0, key="m_act")
                    miles_paid = st.number_input("Miles Reimbursed by Gov", min_value=0.0, key="m_paid")
                    st.divider()
                    lodging = st.number_input("Out-of-Pocket Lodging", min_value=0.0, key="lodg")
                    meals_days = st.number_input("Days on Per Diem (Meals)", min_value=0, key="m_days")
                
                with c2:
                    flight = st.number_input("Flight/Rail Cost", min_value=0.0, key="air")
                    rental = st.number_input("Rental Car Cost", min_value=0.0, key="rent")
                    rent_fuel = st.number_input("Rental Fuel", min_value=0.0, key="rfuel")
                    laundry = st.number_input("Laundry/Dry Cleaning (Travel Only)", min_value=0.0, key="dry")
                    airport_etc = st.number_input("Parking/Taxis/Baggage", min_value=0.0, key="port")
                    st.divider()
                    total_reimb = st.number_input("Total Cash Received (Reimbursement)", min_value=0.0, key="cash")

                if st.form_submit_button("LOG COMPLETE MISSION"):
                    # MATH: POV Gap + Per Diem ($59/day avg) + Expenses - Reimbursement
                    m_gap = (miles_act * 0.725) - (miles_paid * 0.225)
                    per_diem_val = meals_days * 59.0 # Conservative Standard
                    total_exp = lodging + flight + rental + rent_fuel + laundry + airport_etc + per_diem_val
                    
                    final_impact = max(0.0, (m_gap + total_exp) - total_reimb)
                    
                    db.table("logs").insert({
                        "user_id": uid, "date": str(t_date), 
                        "category": "Travel", "deduction": final_impact
                    }).execute()
                    st.success(f"Mission Logged. Calculated Impact: ${final_impact:,.2f}")

        with tab2:
            with st.form("gear_v3"):
                amt = st.number_input("Gear/Uniform Cost", min_value=0.0, key="g_amt")
                if st.form_submit_button("LOG GEAR"):
                    db.table("logs").insert({"user_id": uid, "category": "Gear", "deduction": amt}).execute()
                    st.success("Gear Logged.")
        
        with tab3:
            with st.form("med_v3"):
                m_miles = st.number_input("VA Travel Miles", min_value=0.0, key="med_m")
                if st.form_submit_button("LOG MEDICAL"):
                    db.table("logs").insert({"user_id": uid, "category": "Medical", "deduction": m_miles*0.22}).execute()
                    st.success("Medical Logged.")

    elif nav == "Intelligence":
        st.header("📊 Tactical Report")
        res = db.table("logs").select("*").eq("user_id", uid).execute()
        if res.data:
            st.table(pd.DataFrame(res.data))

if __name__ == "__main__":
    main()
