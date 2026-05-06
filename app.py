import streamlit as st
import extra_streamlit_components as stx
from supabase import create_client
import datetime
import pandas as pd

# --- 1. BOOTSTRAP ---
st.set_page_config(page_title="Tactical Asset Tracker", layout="wide")

# --- 2. DATABASE UTILITY ---
def get_db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

def get_manager():
    if "cookie_manager" not in st.session_state:
        st.session_state.cookie_manager = stx.CookieManager(key="tat_v2_stable")
    return st.session_state.cookie_manager

# --- 3. MAIN APP ---
def main():
    manager = get_manager()
    
    # --- NIGHT OPS THEME ---
    st.markdown("""
        <style>
        .stApp {
            background: linear-gradient(rgba(0, 0, 0, 0.8), rgba(0, 0, 0, 0.85)), 
                        url('https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?auto=format&fit=crop&q=80&w=2000');
            background-size: cover !important; background-attachment: fixed !important;
            background-position: center !important; color: #FFFFFF !important;
        }
        [data-testid="stSidebar"] { background-color: rgba(0, 0, 0, 0.9) !important; }
        div[data-testid="stForm"] {
            background-color: rgba(0, 0, 0, 0.8) !important;
            border: 1px solid #3C3B6E !important; border-radius: 10px; padding: 25px;
        }
        .stButton>button {
            background-color: #3C3B6E !important; color: white !important;
            border: 1px solid #FFFFFF !important; font-weight: bold; width: 100%;
        }
        .stButton>button:hover { background-color: #B22234 !important; }
        </style>
    """, unsafe_allow_html=True)

    # --- PERSISTENT AUTH LOGIC ---
    if "user" not in st.session_state:
        st.session_state.user = manager.get('mil_pro_user_id')

    # IF NOT LOGGED IN, SHOW LOGIN FORM
    if st.session_state.user is None:
        st.title("🪖 TACTICAL ASSET TRACKER")
        with st.form("login_form"):
            email = st.text_input("Email")
            pw = st.text_input("Access Key", type="password")
            if st.form_submit_button("AUTHENTICATE"):
                try:
                    db_auth = get_db()
                    res = db_auth.auth.sign_in_with_password({"email": email, "password": pw})
                    if res.user:
                        st.session_state.user = res.user.id
                        manager.set('mil_pro_user_id', res.user.id)
                        st.rerun()
                except Exception as e:
                    st.error(f"Access Denied: {str(e)}")
        return

    # --- COMMAND CENTER (IF LOGGED IN) ---
    db = get_db()
    # Pull current ID directly from session state to avoid "Variable Not Found" errors
    current_uid = st.session_state.user
    
    st.sidebar.title("⚓ COMMAND CENTER")
    nav = st.sidebar.radio("Sectors", ["Mission Logistics", "Intelligence"])
    if st.sidebar.button("LOGOUT"):
        manager.delete('mil_pro_user_id')
        st.session_state.user = None
        st.rerun()

    if nav == "Mission Logistics":
        st.header("🪖 Comprehensive Military Logistics")
        tab1, tab2, tab3 = st.tabs(["Duty Travel", "Professional Gear", "VA & Medical Transit"])

        with tab1:
            with st.form("travel_form_v5", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    t_date = st.date_input("Travel Date", key="date_id")
                    miles_act = st.number_input("Actual Round-Trip Miles", min_value=0.0, key="m_act")
                    miles_paid = st.number_input("Miles Reimbursed", min_value=0.0, key="m_paid")
                    lodging = st.number_input("Lodging Expenses", min_value=0.0, key="lodg")
                    meals_days = st.number_input("Days on Per Diem", min_value=0, key="m_days")
                with c2:
                    flight = st.number_input("Flight/Rail", min_value=0.0, key="air")
                    rental = st.number_input("Rental + Fuel", min_value=0.0, key="rent")
                    laundry = st.number_input("Laundry/Dry Cleaning", min_value=0.0, key="dry")
                    airport_fees = st.number_input("Parking/Taxis", min_value=0.0, key="port")
                    total_reimb = st.number_input("Total Cash Received", min_value=0.0, key="cash")

                if st.form_submit_button("LOG MISSION LOGISTICS"):
                    m_gap = (miles_act * 0.725) - (miles_paid * 0.225)
                    total_exp = lodging + flight + rental + laundry + airport_fees + (meals_days * 59.0)
                    final_val = max(0.0, (m_gap + total_exp) - total_reimb)
                    
                    # DIRECT CALL TO PREVENT SCOPE ERROR
                    db.table("logs").insert({
                        "user_id": current_uid, "date": str(t_date), 
                        "category": "Travel", "deduction": final_val
                    }).execute()
                    st.success(f"Asset Logged: ${final_val:,.2f}")

        with tab2:
            with st.form("gear_form_v5"):
                u_maint = st.number_input("Uniform Maintenance", min_value=0.0, key="g1")
                insignia = st.number_input("Rank/Medals", min_value=0.0, key="g2")
                equipment = st.number_input("Duty Gear", min_value=0.0, key="g3")
                if st.form_submit_button("LOG GEAR ASSET"):
                    total_g = u_maint + insignia + equipment
                    db.table("logs").insert({
                        "user_id": current_uid, "date": str(datetime.date.today()), 
                        "category": "Gear", "deduction": total_g
                    }).execute()
                    st.success(f"Gear Logged: ${total_g}")

        with tab3:
            with st.form("med_form_v5"):
                m_miles = st.number_input("VA Travel Miles", min_value=0.0, key="m1")
                if st.form_submit_button("LOG MEDICAL ASSET"):
                    db.table("logs").insert({
                        "user_id": current_uid, "date": str(datetime.date.today()), 
                        "category": "Medical", "deduction": m_miles * 0.22
                    }).execute()
                    st.success("Medical Asset Logged.")

    elif nav == "Intelligence":
        st.header("📊 Tactical Report")
        res = db.table("logs").select("*").eq("user_id", current_uid).execute()
        if res.data:
            st.table(pd.DataFrame(res.data))

if __name__ == "__main__":
    main()
