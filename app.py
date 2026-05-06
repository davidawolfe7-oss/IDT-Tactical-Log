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
        st.session_state.cookie_manager = stx.CookieManager(key="mil_pro_v3_mgr")
    return st.session_state.cookie_manager

# --- 3. MAIN APP ---
def main():
    manager = get_manager()
    
    # --- NIGHT OPS THEME WITH AMERICAN FLAG BACKGROUND ---
    st.markdown("""
        <style>
        .stApp {
            /* This creates a dark overlay on top of the flag so you can still read the text */
            background: linear-gradient(rgba(0, 0, 0, 0.8), rgba(0, 0, 0, 0.85)), 
                        url('https://img.magnific.com/free-photo/american-flag-blowing-wind-background-ai-generative_123827-23752.jpg?w=2000');
            background-size: cover !important;
            background-attachment: fixed !important;
            background-position: center !important;
            color: #FFFFFF !important;
        }
        
        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: rgba(0, 0, 0, 0.9) !important;
        }

        /* Form Styling (Tactical Black) */
        div[data-testid="stForm"] {
            background-color: rgba(0, 0, 0, 0.8) !important;
            border: 1px solid #3C3B6E !important;
            border-radius: 10px;
            padding: 25px;
        }

        /* Tactical Button Colors (Old Glory Blue and Red) */
        .stButton>button {
            background-color: #3C3B6E !important;
            color: white !important;
            border: 1px solid #FFFFFF !important;
            font-weight: bold;
            width: 100%;
        }
        .stButton>button:hover {
            background-color: #B22234 !important;
            border: 1px solid #B22234 !important;
        }

        /* Metric Styling */
        [data-testid="stMetric"] {
            background-color: rgba(255, 255, 255, 0.05);
            border-left: 5px solid #B22234;
            padding: 15px;
        }
        </style>
    """, unsafe_allow_html=True)

    # AUTH GATE
    if "user" not in st.session_state or st.session_state.user is None:
        st.title("🪖 Tactical Asset Tracker")
        with st.form("login_form"):
            email = st.text_input("Email")
            pw = st.text_input("Access Key", type="password")
            if st.form_submit_button("AUTHENTICATE"):
                try:
                    db = get_db()
                    # Perform the login
                    res = db.auth.sign_in_with_password({"email": email, "password": pw})
                    
                    # SAFETY CHECK: Only set the user if 'res.user' actually exists
                    if res.user:
                        st.session_state.user = res.user.id
                        manager.set('mil_pro_user_id', res.user.id)
                        st.rerun()
                    else:
                        st.error("Authentication failed: No user returned.")
                except Exception as e:
                    # This catches things like wrong passwords or connection issues
                    st.error(f"Access Denied: {str(e)}")
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
                    total_reimb = st.number_input("Total Cash Received (Reimbursement)", min_value=0.0, key="cash")

                if st.form_submit_button("LOG COMPLETE MISSION"):
                    m_gap = (miles_act * 0.725) - (miles_paid * 0.225)
                    per_diem_val = meals_days * 59.0 
                    total_exp = lodging + flight + rental + rent_fuel + laundry + airport_etc + per_diem_val
                    final_impact = max(0.0, (m_gap + total_exp) - total_reimb)
                    
                    db.table("logs").insert({
                        "user_id": uid, "date": str(t_date), 
                        "category": "Travel", "deduction": final_impact
                    }).execute()
                    st.success(f"Mission Logged. Calculated Impact: ${final_impact:,.2f}")

        with tab2:
            st.subheader("Professional Gear")
            with st.form("gear_form"):
                u_maint = st.number_input("Uniform Cleaning/Repair", min_value=0.0)
                insignia = st.number_input("Rank/Patches/Medals", min_value=0.0)
                equipment = st.number_input("Duty Gear (Boots, GPS, Tools)", min_value=0.0)
                dues = st.number_input("Professional Dues/Subscriptions", min_value=0.0)
                if st.form_submit_button("LOG GEAR"):
                    total = u_maint + insignia + equipment + dues
                    db.table("logs").insert({
                        "user_id": uid, "date": str(datetime.date.today()), 
                        "category": "Gear", "deduction": total
                    }).execute()
                    st.success(f"Logged ${total} Professional Expense.")

        
        with tab3:
            st.subheader("VA & Medical Transit")
            with st.form("med_form"):
                med_miles = st.number_input("VA/Medical Appointment Miles", min_value=0.0)
                charity_miles = st.number_input("Charitable/Volunteer Miles (14¢)", min_value=0.0)
                if st.form_submit_button("LOG MEDICAL MILES"):
                    med_total = (med_miles * 0.22) + (charity_miles * 0.14)
                    db.table("logs").insert({
                        "user_id": uid, "date": str(datetime.date.today()), 
                        "category": "Medical", "deduction": med_total
                    }).execute()
                    st.success(f"Medical Logged: ${med_total:,.2f}")

    elif nav == "Intelligence":
        st.header("📊 Tactical Report")
        res = db.table("logs").select("*").eq("user_id", uid).execute()
        if res.data:
            st.table(pd.DataFrame(res.data))

if __name__ == "__main__":
    main()
