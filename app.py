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
        st.session_state.cookie_manager = stx.CookieManager(key="tat_v1_mgr")
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
            background-size: cover !important;
            background-attachment: fixed !important;
            background-position: center !important;
            color: #FFFFFF !important;
        }
        [data-testid="stSidebar"] { background-color: rgba(0, 0, 0, 0.9) !important; }
        div[data-testid="stForm"] {
            background-color: rgba(0, 0, 0, 0.8) !important;
            border: 1px solid #3C3B6E !important;
            border-radius: 10px; padding: 25px;
        }
        .stButton>button {
            background-color: #3C3B6E !important; color: white !important;
            border: 1px solid #FFFFFF !important; font-weight: bold; width: 100%;
        }
        .stButton>button:hover { background-color: #B22234 !important; border: 1px solid #B22234 !important; }
        </style>
    """, unsafe_allow_html=True)

    # --- AUTH GATE ---
    if "user" not in st.session_state or st.session_state.user is None:
        st.session_state.user = manager.get('mil_pro_user_id')

    if st.session_state.user is None:
        st.title("🪖 TACTICAL ASSET TRACKER")
        with st.form("login_form"):
            email = st.text_input("Email")
            pw = st.text_input("Access Key", type="password")
            if st.form_submit_button("AUTHENTICATE"):
                try:
                    db_auth = get_db()
                    res = db_auth.auth.sign_in_with_password({"email": email, "password": pw})
                    
                    # FIXED LINE 84: Added safety check before assigning ID
                    if res.user:
                        st.session_state.user = res.user.id
                        manager.set('mil_pro_user_id', res.user.id)
                        st.rerun()
                    else:
                        st.error("Authentication failed: No user returned.")
                except Exception as e:
                    st.error(f"Access Denied: {str(e)}")
        return

    # --- COMMAND CENTER ---
    db = get_db()
    uid = st.session_state.user
    
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
            st.subheader("Duty Travel")
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
                    laundry = st.number_input("Laundry/Dry Cleaning (Travel)", min_value=0.0, key="dry")
                    airport_etc = st.number_input("Parking/Taxis/Baggage", min_value=0.0, key="port")
                    st.divider()
                    total_reimb = st.number_input("Total Cash Received", min_value=0.0, key="cash")

                # FIXED LINE 115: Wrapped in a local safety check
                if st.form_submit_button("LOG COMPLETE MISSION"):
                    m_gap = (miles_act * 0.725) - (miles_paid * 0.225)
                    p_diem = meals_days * 59.0 
                    total_exp = lodging + flight + rental + rent_fuel + laundry + airport_etc + p_diem
                    final_impact = max(0.0, (m_gap + total_exp) - total_reimb)
                    
                    db.table("logs").insert({
                        "user_id": uid, "date": str(t_date), 
                        "category": "Travel", "deduction": final_impact
                    }).execute()
                    st.success(f"Mission Logged. Calculated Impact: ${final_impact:,.2f}")

        with tab2:
            st.subheader("Professional Gear")
            with st.form("gear_form"):
                # Added unique keys to stop collision with Tab 1/Tab 3
                u_maint = st.number_input("Uniform Cleaning/Repair", min_value=0.0, key="u_clean")
                insignia = st.number_input("Rank/Patches/Medals", min_value=0.0, key="u_rank")
                equipment = st.number_input("Duty Gear (Boots, GPS, Tools)", min_value=0.0, key="u_gear")
                dues = st.number_input("Professional Dues/Subscriptions", min_value=0.0, key="u_dues")
                
                # FIXED LINE 157: Standardized the insert logic
                if st.form_submit_button("LOG GEAR"):
                    total_gear = u_maint + insignia + equipment + dues
                    db.table("logs").insert({
                        "user_id": uid, "date": str(datetime.date.today()), 
                        "category": "Gear", "deduction": total_gear
                    }).execute()
                    st.success(f"Logged ${total_gear} Professional Expense.")

        with tab3:
            st.subheader("VA & Medical Transit")
            with st.form("med_form"):
                med_miles = st.number_input("VA/Medical Appointment Miles", min_value=0.0, key="m_med")
                charity_miles = st.number_input("Charitable/Volunteer Miles (14¢)", min_value=0.0, key="m_char")
                if st.form_submit_button("LOG MEDICAL MILES"):
                    med_total = (med_miles * 0.22) + (charity_miles * 0.14)
                    db.table("logs").insert({
                        "user_id": uid, "date": str(datetime.date.today()), 
                        "category": "Medical", "deduction": med_total
                    }).execute()
                    st.success(f"Medical Logged: ${med_total:,.2f}")

    elif nav == "Intelligence":
        st.header("📊 Tactical Intelligence Report")
        res = db.table("logs").select("*").eq("user_id", uid).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            st.table(df)
            st.download_button("📥 Export CSV", df.to_csv(index=False), "Tactical_Report.csv")
        else:
            st.warning("No mission logs found in the database.")

if __name__ == "__main__":
    main()
