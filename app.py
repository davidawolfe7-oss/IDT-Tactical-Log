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
    # This creates the manager only if it doesn't exist yet
    if "cookie_manager" not in st.session_state:
        st.session_state.cookie_manager = stx.CookieManager(key="mil_pro_stable_mgr")
    return st.session_state.cookie_manager

def handle_persistent_login():
    manager = get_manager()
    # On the first run, the manager might need a second to initialize
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
    # A. Check for badge immediately
    handle_persistent_login()

    # B. Night Ops Theme (LOCKED VERSION)
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

    # C. AUTHENTICATION GATE
    if st.session_state.user is None:
        st.title("🪖 MIL-PRO COMMAND")
        st.caption("Tactical Logistics Management")
        
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

    # D. COMMAND CENTER (Logged In)
    db = get_db()
    uid = st.session_state.user

    st.sidebar.title("⚓ COMMAND CENTER")
    nav = st.sidebar.radio("Sectors", ["Mission Log", "IDT Tactical", "The Garage", "Reports"])

    if st.sidebar.button("LOGOUT"):
        manager = get_manager()
        manager.delete('mil_pro_user_id')
        st.session_state.user = None
        st.rerun()

    # Sector: Mission Log
    if nav == "Mission Log":
        st.header("📍 Mission Log")
        with st.form("mission_entry", clear_on_submit=True):
            date = st.date_input("Date", datetime.date.today())
            start = st.number_input("Start Odometer", step=1)
            end = st.number_input("End Odometer", step=1)
            purpose = st.text_input("Mission Purpose")
            if st.form_submit_button("LOG MISSION"):
                miles = end - start
                if miles < 0:
                    st.error("Error: End odometer lower than start.")
                else:
                    deduction = round(miles * 0.725, 2)
                    db.table("logs").insert({
                        "user_id": uid, "date": str(date), "miles": miles, 
                        "purpose": purpose, "total_deduction": deduction
                    }).execute()
                    st.success(f"Mission Confirmed: {miles} miles. Deduction: ${deduction}")

    # Sector: IDT Tactical
    elif nav == "IDT Tactical":
        st.header("✈️ IDT Logistics")
        st.info("Tracking unreimbursed expenses ($750 Cap)")
        with st.form("idt_form"):
            meals = st.number_input("Total Meals Cost")
            lodging = st.number_input("Lodging Spend")
            reimb = st.number_input("Reimbursement Received", value=750.0)
            if st.form_submit_button("CALCULATE NET DEDUCTION"):
                total_eligible = (meals * 0.5) + lodging
                net = max(0.0, total_eligible - reimb)
                st.metric("Net Schedule 1 Deduction", f"${net}")

    # Sector: The Garage
    elif nav == "The Garage":
        st.header("🚘 Fleet Management")
        st.write("Vehicle tracking system online.")

    # Sector: Reports
    elif nav == "Reports":
        st.header("📊 Tax Export")
        try:
            res = db.table("logs").select("*").eq("user_id", uid).execute()
            if res.data:
                df = pd.DataFrame(res.data)
                st.dataframe(df)
                st.download_button("📥 Export CSV", df.to_csv(index=False), "MilPro_Report.csv")
        except:
            st.warning("No mission logs found for this user.")

if __name__ == "__main__":
    main()
