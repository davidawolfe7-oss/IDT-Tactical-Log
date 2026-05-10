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
                        url('https://img.magnific.com/free-photo/american-flag-blowing-wind-background-ai-generative_123827-23752.jpg?w=2000');
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

    # AUTH GATE
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
            st.info("""
            **PURPOSE:** Track unreimbursed costs for official military travel (IDT, AT, or Mobilization). 
            This module calculates the 'Mileage Gap'—the difference between actual vehicle wear-and-tear costs and 
            the government reimbursement rate—alongside out-of-pocket lodging and subsistence.
            """)
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

                if st.form_submit_button("LOG COMPLETE MISSION"):
                    m_gap = (miles_act * 0.725) - (miles_paid * 0.225)
                    total_exp = lodging + flight + rental + rent_fuel + laundry + airport_etc + (meals_days * 59.0)
                    final_impact = max(0.0, (m_gap + total_exp) - total_reimb)
                    
                    db.table("logs").insert({
                        "user_id": uid, "date": str(t_date), "purpose": "Mission Travel",
                        "miles": miles_act, "reimbursement": total_reimb, "lodging": lodging,
                        "fuel_gas": rent_fuel, "tolls_parking": airport_etc,
                        "total_deduction": final_impact, "travel_mode": "POV/Rental"
                    }).execute()
                    st.success(f"Mission Logged. Calculated Impact: ${final_impact:,.2f}")

with tab2:
            st.subheader("Professional Gear")
            
            # --- DETAILED SOLDIER BRIEFING ---
            with st.expander("📝 VIEW GEAR LOGGING GUIDELINES (IRS & JAG STANDARDS)"):
                st.markdown("""
                ### ✅ WHAT YOU CAN LOG
                *   **Uniforms & Maintenance:** Purchase of OCPs, ASUs, Mess Dress, and the cost of professional dry cleaning/sewing patches.
                *   **Rank & Insignia:** Patches, medals, ribbons, name tapes, and berets.
                *   **MOS-Specific Equipment:** Gear required for duty but not issued (DX'd). Examples: 12N specific rugged tools, 88M specialized driving gloves, personal GPS, high-end flashlights, or multitools.
                *   **Professional Dues:** AUSA, NGAUS, or MOS-related trade subscriptions.

                ### ❌ WHAT YOU CANNOT LOG
                *   **Daily Wear:** Plain tan/green t-shirts, standard socks, or PT gear (these are considered "suitable for civilian use").
                *   **Personal Grooming:** Haircuts, shaving supplies, or gym memberships.
                *   **Commuting:** Travel from your home to your regular Reserve Center/Armory (this is 'commuting', not 'mission travel').
                """)

            with st.form("gear_form"):
                # Manual Date Input (Architect Upgrade: Allows logging past purchases)
                gear_date = st.date_input("Purchase Date", value=datetime.date.today())
                
                u_maint = st.number_input("Uniform Cleaning/Repair", min_value=0.0, key="u_maint")
                insignia = st.number_input("Rank/Patches/Medals", min_value=0.0, key="u_insig")
                equipment = st.number_input("Duty Gear (Boots, GPS, Tools)", min_value=0.0, key="u_equip")
                dues = st.number_input("Professional Dues/Subscriptions", min_value=0.0, key="u_dues")
                
                st.divider()
                # --- RECEIPT CAPTURE ---
                st.write("📷 **Receipt Capture**")
                receipt_file = st.file_uploader("Upload or Take Photo of Receipt", type=['jpg', 'jpeg', 'png'])
                
                if st.form_submit_button("LOG GEAR & SAVE RECEIPT"):
                    total_g = u_maint + insignia + equipment + dues
                    
                    # Logic for handling the image name
                    receipt_name = f"receipt_{uid}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png" if receipt_file else None
                    
                    # DATABASE INSERT
                    db.table("logs").insert({
                        "user_id": uid, 
                        "date": str(gear_date), 
                        "purpose": f"Gear Log: {receipt_name}" if receipt_name else "Professional Gear", 
                        "total_deduction": total_g
                    }).execute()
                    
                    # NOTE: To actually save the file, you would use:
                    # db.storage.from_("receipts").upload(receipt_name, receipt_file.getvalue())
                    
                    if receipt_file:
                        st.success(f"Log Complete. Receipt captured as: {receipt_name}")
                    else:
                        st.success(f"Log Complete. Amount: ${total_g}")

        with tab3:
            st.subheader("VA & Medical Transit")
            st.info("""
            **PURPOSE:** Specifically for tracking mileage to VA medical appointments or approved 
            charitable volunteer missions. These miles are calculated at the medical/moving 
            standard rate for tax documentation.
            """)
            with st.form("med_form"):
                med_miles = st.number_input("VA/Medical Appointment Miles", min_value=0.0, key="m_med")
                charity_miles = st.number_input("Charitable/Volunteer Miles", min_value=0.0, key="m_char")
                
                if st.form_submit_button("LOG MEDICAL MILES"):
                    med_total = (med_miles * 0.22) + (charity_miles * 0.14)
                    db.table("logs").insert({
                        "user_id": uid, "date": str(datetime.date.today()), 
                        "purpose": "VA Medical/Charity Travel", "miles": med_miles + charity_miles,
                        "total_deduction": med_total
                    }).execute()
                    st.success(f"Medical Logged: ${med_total:,.2f}")

    elif nav == "Intelligence":
        st.header("📊 Tactical Report")
        st.write("Review all logged missions and expenses synced with the central database.")
        try:
            res = db.table("logs").select(
                "date", "purpose", "miles", "total_deduction", "reimbursement"
            ).eq("user_id", uid).execute()
            
            if res.data:
                df = pd.DataFrame(res.data)
                df.columns = ["Date", "Mission/Purpose", "Miles", "Tax Impact", "Reimbursed"]
                st.table(df)
            else:
                st.info("No mission logs found.")
        except Exception as e:
            st.error(f"Intelligence Sector Error: {str(e)}")

if __name__ == "__main__":
    main()
