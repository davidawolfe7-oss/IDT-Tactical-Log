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
        # Internal key updated to tat
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

    # AUTH GATE - Internal key updated to tat_user_id
    if "user" not in st.session_state or st.session_state.user is None:
        st.session_state.user = manager.get('tat_user_id')

    if st.session_state.user is None:
        st.title("🪖 TACTICAL ASSET TRACKER")
        with st.form("login_form"):
            email = st.text_input("Email")
            pw = st.text_input("Access Key", type="password")
            if st.form_submit_button("AUTHENTICATE"):
                try:
                    local_db = get_db()
                    res = local_db.auth.sign_in_with_password({"email": email, "password": pw})
                    
                    if res.user:
                        st.session_state.user = res.user.id
                        manager.set('tat_user_id', res.user.id)
                        st.rerun()
                except Exception as e:
                    st.error(f"Access Denied: {str(e)}")
        return

    # COMMAND CENTER
    db = get_db()
    uid = st.session_state.user
    
    nav = st.sidebar.radio("Sectors", ["Mission Logistics", "Intelligence"])
    if st.sidebar.button("LOGOUT"):
        manager.delete('tat_user_id')
        st.session_state.user = None
        st.rerun()

if nav == "Mission Logistics":
        st.header("🪖 Comprehensive Military Logistics")
        
        tab1, tab2, tab3 = st.tabs(["Duty Travel", "Professional Gear", "VA & Medical Transit"])

        with tab1:
            st.subheader("Duty Travel")
            with st.form("travel_v3", clear_on_submit=True):
                # ... (Keep your existing columns c1 and c2 here) ...
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

                if st.form_submit_button("LOG COMPLETE MISSION"):
                    # 1. THE CALCULATIONS
                    m_gap = (miles_act * 0.725) - (miles_paid * 0.225)
                    total_exp = lodging + flight + rental + rent_fuel + laundry + airport_etc + (meals_days * 59.0)
                    final_impact = max(0.0, (m_gap + total_exp) - total_reimb)
                    
                    # 2. THE INSERT (Mapped to your DB columns)
                    db.table("logs").insert({
                        "user_id": st.session_state.user,
                        "date": str(t_date),
                        "purpose": "Mission Travel",
                        "miles": miles_act,
                        "reimbursement": total_reimb,
                        "lodging": lodging,
                        "fuel_gas": rent_fuel,
                        "tolls_parking": airport_etc,
                        "total_deduction": final_impact,
                        "travel_mode": "POV/Rental"
                    }).execute()
                    st.success(f"Mission Logged. Calculated Impact: ${final_impact:,.2f}")

        with tab2:
            st.subheader("Professional Gear")
            with st.form("gear_form"):
                # ... (Keep your gear inputs) ...
                u_maint = st.number_input("Uniform Cleaning/Repair", min_value=0.0, key="u_maint")
                insignia = st.number_input("Rank/Patches/Medals", min_value=0.0, key="u_insig")
                equipment = st.number_input("Duty Gear (Boots, GPS, Tools)", min_value=0.0, key="u_equip")
                dues = st.number_input("Professional Dues/Subscriptions", min_value=0.0, key="u_dues")
                
                if st.form_submit_button("LOG GEAR"):
                    total_g = u_maint + insignia + equipment + dues
                    # Mapped to your 'purpose' and 'total_deduction' columns
                    db.table("logs").insert({
                        "user_id": st.session_state.user, 
                        "date": str(datetime.date.today()), 
                        "purpose": "Professional Gear/Maintenance", 
                        "total_deduction": total_g
                    }).execute()
                    st.success(f"Logged ${total_g} Professional Expense.")

        with tab3:
            st.subheader("VA & Medical Transit")
            with st.form("med_form"):
                med_miles = st.number_input("VA/Medical Appointment Miles", min_value=0.0, key="m_med")
                charity_miles = st.number_input("Charitable/Volunteer Miles", min_value=0.0, key="m_char")
                
                if st.form_submit_button("LOG MEDICAL MILES"):
                    med_total = (med_miles * 0.22) + (charity_miles * 0.14)
                    # Mapped to your 'purpose', 'miles', and 'total_deduction' columns
                    db.table("logs").insert({
                        "user_id": st.session_state.user, 
                        "date": str(datetime.date.today()), 
                        "purpose": "VA Medical/Charity Travel",
                        "miles": med_miles + charity_miles,
                        "total_deduction": med_total
                    }).execute()
                    st.success(f"Medical Logged: ${med_total:,.2f}")

   elif nav == "Intelligence":
        st.header("📊 Tactical Report")
        
        # We fetch only the columns that actually exist in your DB
        try:
            res = db.table("logs").select(
                "date", "purpose", "miles", "total_deduction", "reimbursement"
            ).eq("user_id", uid).execute()
            
            if res.data:
                # Convert to a clean DataFrame for display
                df = pd.DataFrame(res.data)
                
                # Rename columns for the user's view (Optional, makes it look cleaner)
                df.columns = ["Date", "Mission/Purpose", "Miles", "Tax Impact", "Reimbursed"]
                
                st.table(df)
            else:
                st.info("No mission logs found in the database.")

        except Exception as e:       
            st.error(f"Intelligence Sector Error: {str(e)}")
            st.info("check if your Supabase column names match: date, purpose, miles, total_deduction, reimbursement")

if __name__ == "__main__":
    main()
