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

# --- 3. PERSISTENT MEMORY (The Stabilized Fix) ---
def get_manager():
    if "cookie_manager" not in st.session_state:
        st.session_state.cookie_manager = stx.CookieManager(key="mil_pro_stable_mgr")
    return st.session_state.cookie_manager

def handle_persistent_login():
    manager = get_manager()
    saved_user = manager.get('mil_pro_user_id')
    if saved_user and st.session_state.get('user') is None:
        st.session_state.user = saved_user
        return True
    return False

def save_login_permanently(user_id):
    manager = get_manager()
    manager.set('mil_pro_user_id', user_id, expires_at=datetime.datetime.now() + datetime.timedelta(days=30))

# --- 4. SESSION STATE ---
if 'user' not in st.session_state:
    st.session_state.user = None

# --- 5. MAIN APPLICATION ---
def main():
    handle_persistent_login()

    # --- NIGHT OPS THEME (LOCKED) ---
    st.markdown("""
        <style>
        .stApp {
            background: linear-gradient(rgba(0, 0, 0, 0.85), rgba(0, 0, 0, 0.85)), 
                        url('https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?auto=format&fit=crop&q=80&w=2000');
            background-size: cover !important;
            background-attachment: fixed !important;
            color: #FFFFFF !important;
        }
        [data-testid="stMetric"] {
            background-color: rgba(255, 255, 255, 0.05);
            border-left: 5px solid #B22234;
            padding: 15px;
        }
        .stButton>button {
            background-color: #3C3B6E;
            color: white;
            border: 1px solid #FFFFFF;
            font-weight: bold;
            width: 100%;
        }
        .stButton>button:hover { background-color: #B22234; }
        div[data-testid="stForm"] {
            background-color: rgba(0,0,0,0.7);
            border-radius: 10px;
            padding: 20px;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- AUTHENTICATION GATE ---
    if st.session_state.user is None:
        st.title("🪖 MIL-PRO COMMAND")
        with st.form("login_form"):
            email = st.text_input("Email")
            pw = st.text_input("Access Key", type="password")
            if st.form_submit_button("AUTHENTICATE"):
                try:
                    db = get_db()
                    res = db.auth.sign_in_with_password({"email": email, "password": pw})
                    st.session_state.user = res.user.id
                    save_login_permanently(res.user.id)
                    st.rerun()
                except Exception as e:
                    st.error(f"Login Failure: {e}")
        return

    # --- LOGGED IN: COMMAND CENTER ---
    db = get_db()
    uid = st.session_state.user

    st.sidebar.title("⚓ COMMAND CENTER")
    # Simplified Nav: Focus on Logistics and Intelligence (Reports)
    nav = st.sidebar.radio("Sectors", ["Mission Logistics", "Intelligence (Reports)"])

    if st.sidebar.button("LOGOUT"):
        manager = get_manager()
        manager.delete('mil_pro_user_id')
        st.session_state.user = None
        st.rerun()

    if nav == "Mission Logistics":
        st.header("✈️ Comprehensive Military Logistics")
        
        tab1, tab2, tab3, tab4 = st.tabs([
            "Duty Travel (IDT/AT/PCS)", 
            "Professional Gear", 
            "Medical & VA",
            "Nontaxable Income"
        ])

        with tab1:
            st.subheader("Duty Travel & Mileage Gap")
            with st.form("travel_detailed", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    date = st.date_input("Travel Date")
                    total_miles = st.number_input("Total Miles Driven", min_value=0.0)
                    reimb_miles = st.number_input("Miles Reimbursed by Gov", min_value=0.0)
                    flights_rail = st.number_input("Flights/Rail/Rental/Airport Fees", min_value=0.0)
                
                with col2:
                    lodging = st.number_input("Out-of-Pocket Lodging", min_value=0.0)
                    meals_days = st.number_input("Days Away (Overnight)", step=1)
                    reimb_total = st.number_input("Total Travel Reimbursement Received", value=0.0)

                if st.form_submit_button("LOG TRAVEL DATA"):
                    # IRS 2026 Rate: 72.5c | Mil Rate: 22.5c
                    mileage_gap = (total_miles * 0.725) - (reimb_miles * 0.225)
                    meal_deduction = (meals_days * 60.00) * 0.50 
                    total_deductible = max(0.0, (mileage_gap + flights_rail + lodging + meal_deduction) - reimb_total)
                    
                    db.table("logs").insert({
                        "user_id": uid, "date": str(date), "category": "Travel",
                        "miles": total_miles, "deduction": total_deductible
                    }).execute()
                    st.success(f"Logged ${total_deductible:,.2f} in Potential Deductions.")

        with tab2:
            st.subheader("Uniforms, Gear & Professional Dues")
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

        with tab4:
            st.subheader("Nontaxable Pay Tracking")
            st.caption("Tracking BAH, BAS, and Combat Pay to calculate actual taxable footprint.")
            with st.form("income_form"):
                bah_bas = st.number_input("Monthly BAH + BAS", min_value=0.0)
                combat_pay = st.number_input("Combat Zone Tax-Exempt Pay", min_value=0.0)
                fsa = st.number_input("Family Separation Allowance", min_value=0.0)
                if st.form_submit_button("LOG INCOME DATA"):
                    st.info("This data will be used to reduce AGI in your final report.")

    elif nav == "Intelligence (Reports)":
        st.header("📊 Tactical Financial Intelligence")
        res = db.table("logs").select("*").eq("user_id", uid).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            st.dataframe(df)
            st.download_button("📥 Export CSV", df.to_csv(index=False), "MilPro_Final_Tax_Report.csv")
        else:
            st.warning("No data logs found.")

if __name__ == "__main__":
    main()
