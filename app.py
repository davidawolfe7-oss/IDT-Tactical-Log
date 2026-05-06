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

# --- 3. PERSISTENT LOGIN ---
def get_manager():
    if "cookie_manager" not in st.session_state:
        st.session_state.cookie_manager = stx.CookieManager(key="mil_pro_stable_mgr")
    return st.session_state.cookie_manager

# --- 4. MAIN APP LOGIC ---
def main():
    # Handle auto-login
    manager = get_manager()
    saved_user = manager.get('mil_pro_user_id')
    if saved_user and "user" not in st.session_state:
        st.session_state.user = saved_user

    # NIGHT OPS THEME
    st.markdown("""
        <style>
        .stApp {
            background: linear-gradient(rgba(0, 0, 0, 0.85), rgba(0, 0, 0, 0.85)), 
                        url('https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?auto=format&fit=crop&q=80&w=2000');
            background-size: cover; background-attachment: fixed; color: #FFFFFF;
        }
        div[data-testid="stForm"] { background-color: rgba(0,0,0,0.7); border-radius: 10px; padding: 20px; }
        .stButton>button { background-color: #3C3B6E; color: white; border: 1px solid #FFFFFF; }
        .stButton>button:hover { background-color: #B22234; }
        </style>
    """, unsafe_allow_html=True)

    # AUTH GATE
    if "user" not in st.session_state or st.session_state.user is None:
        st.title("🪖 MIL-PRO COMMAND")
        with st.form("login_form"):
            email = st.text_input("Email")
            pw = st.text_input("Access Key", type="password")
            if st.form_submit_button("AUTHENTICATE"):
                try:
                    db = get_db()
                    res = db.auth.sign_in_with_password({"email": email, "password": pw})
                    st.session_state.user = res.user.id
                    manager.set('mil_pro_user_id', res.user.id, expires_at=datetime.datetime.now() + datetime.timedelta(days=30))
                    st.rerun()
                except Exception as e:
                    st.error(f"Login Failure: {e}")
        return

    # --- COMMAND CENTER (LOGGED IN) ---
    # Global variables defined once to avoid Line 142/193 errors
    db = get_db()
    uid = st.session_state.user

    st.sidebar.title("⚓ COMMAND CENTER")
    nav = st.sidebar.radio("Sectors", ["Mission Logistics", "Intelligence (Reports)"])
    
    if st.sidebar.button("LOGOUT"):
        manager.delete('mil_pro_user_id')
        st.session_state.user = None
        st.rerun()

    if nav == "Mission Logistics":
        st.header("✈️ Comprehensive Military Logistics")
        
        tab1, tab2, tab3, tab4 = st.tabs([
            "Duty Travel", "Professional Gear", "Medical & VA", "Nontaxable Pay"
        ])

        with tab1:
            st.subheader("Duty Travel & Mileage Gap")
            with st.form("travel_detailed", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    t_date = st.date_input("Travel Date", key="t_date")
                    total_miles = st.number_input("Total Actual Miles Driven (POV)", min_value=0.0)
                    reimb_miles = st.number_input("Miles Reimbursed by Unit", min_value=0.0)
                    st.divider()
                    flight_cost = st.number_input("Flight Cost", min_value=0.0)
                    rental_cost = st.number_input("Rental Car Cost", min_value=0.0)
                with col2:
                    rental_fuel = st.number_input("Rental Car Fuel", min_value=0.0)
                    airport_fees = st.number_input("Baggage/Taxis/Parking", min_value=0.0)
                    tolls = st.number_input("Tolls & Ferry Fees", min_value=0.0)
                    st.divider()
                    reimb_cash = st.number_input("Total Cash Reimbursement Received", min_value=0.0)

                if st.form_submit_button("LOG MISSION LOGISTICS"):
                    # IRS 2026 Rate: 72.5c | Mil POV: 22.5c
                    m_gap = (total_miles * 0.725) - (reimb_miles * 0.225)
                    o_pocket = flight_cost + rental_cost + rental_fuel + airport_fees + tolls
                    total_deduction = max(0.0, (m_gap + o_pocket) - reimb_cash)
                    
                    db.table("logs").insert({
                        "user_id": uid, "date": str(t_date), 
                        "category": "Travel", "deduction": total_deduction
                    }).execute()
                    st.success(f"Log Successful. Tax Impact: ${total_deduction:,.2f}")

        with tab2:
            st.subheader("Uniforms & Gear")
            with st.form("gear_form"):
                gear_amt = st.number_input("Gear/Uniform/Maintenance Cost", min_value=0.0)
                if st.form_submit_button("LOG GEAR"):
                    db.table("logs").insert({
                        "user_id": uid, "date": str(datetime.date.today()), 
                        "category": "Gear", "deduction": gear_amt
                    }).execute()
                    st.success("Gear Logged.")

        with tab3:
            st.subheader("Medical/VA Travel")
            with st.form("med_form"):
                m_miles = st.number_input("Medical Miles", min_value=0.0)
                if st.form_submit_button("LOG MEDICAL"):
                    m_deduction = m_miles * 0.22
                    db.table("logs").insert({
                        "user_id": uid, "date": str(datetime.date.today()), 
                        "category": "Medical", "deduction": m_deduction
                    }).execute()
                    st.success("Medical Travel Logged.")

        with tab4:
            st.write("Tracking BAH/BAS to adjust your final AGI.")
            # Simplified for now to ensure no errors

    elif nav == "Intelligence (Reports)":
        st.header("📊 Tactical Financial Intelligence")
        res = db.table("logs").select("*").eq("user_id", uid).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            st.dataframe(df)
        else:
            st.warning("No mission logs found.")

if __name__ == "__main__":
    main()
