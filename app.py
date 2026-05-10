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
    
    # --- NIGHT OPS THEME UPGRADE ---
    st.markdown("""
        <style>
        .stApp {
            background: linear-gradient(rgba(0, 0, 0, 0.8), rgba(0, 0, 0, 0.85)), 
                        url('https://img.freepik.com/premium-photo/american-flag-blowing-wind-background-ai-generative_123827-23752.jpg');
            background-size: cover !important;
            background-attachment: fixed !important;
            background-position: center !important;
            color: #FFFFFF !important;
        }
        [data-testid="stSidebar"] { background-color: rgba(0, 0, 0, 0.9) !important; }
        div[data-testid="st_form"] {
            background-color: rgba(0, 0, 0, 0.8) !important;
            border: 2px solid #3C3B6E !important;
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
        tab1, tab2, tab3, tab4 = st.tabs(["Duty Travel", "Professional Gear", "VA & Medical Transit", "Vault Upload"])
        with tab1:
            st.subheader("Duty Travel")
            
            # --- MISSION PURPOSE BLOCK ---
            st.info("""
            **PURPOSE:** Track unreimbursed costs for official military travel (IDT, AT, or Mobilization). 
            This module calculates the 'Mileage Gap'—the difference between actual vehicle wear-and-tear costs and 
            the government reimbursement rate.
            """)

            # --- TACTICAL GUIDANCE (Dropdown) ---
            with st.expander("📖 Strategic Overview: The Mileage Gap (Click to Expand)"):
                st.write("""
                **WHAT IS THE MILEAGE GAP?**
                This represents the difference between your actual vehicle operating costs and what the military pays you.
                
                *   **Actual Round-Trip Miles:** This is your true odometer reading (Home → Duty → Home).
                *   **Miles Reimbursed by Gov:** This is the distance the government actually paid for on your travel voucher.
                
                **WHY THEY MIGHT DIFFER:**
                1.  **The $750 Cap:** If your reimbursement was capped, your 'Paid Miles' will be lower than your 'Actual Miles.'
                2.  **Partial Orders:** If you were only authorized one-way travel pay but drove round-trip.
                3.  **Standard Trip:** If the military paid your full distance, enter the **same number** in both boxes.
                """)
            
            with st.form("travel_v3", clear_on_submit=True):
                st.write("### 🛰️ Mission Transit Data")
                c1, c2 = st.columns(2)
                with c1:
                    t_date = st.date_input("Travel Date", key="date_id")
                    miles_act = st.number_input("Actual Round-Trip Miles (Odometer)", min_value=0.0, help="Total physical miles driven.")
                    miles_paid = st.number_input("Miles Reimbursed by Gov", min_value=0.0, help="Miles listed on your paid travel voucher.")
                    st.divider()
                    lodging = st.number_input("Out-of-Pocket Lodging", min_value=0.0)
                with c2:
                    per_diem = st.number_input("Per Diem (Meals/Incidental)", min_value=0.0)
                    flight = st.number_input("Flight/Rail Cost", min_value=0.0)
                    rental = st.number_input("Rental Car Cost", min_value=0.0)
                    rent_fuel = st.number_input("Rental Fuel", min_value=0.0)
                    airport_etc = st.number_input("Parking/Taxis/Baggage", min_value=0.0)
                    st.divider()
                    total_reimb = st.number_input("Total Cash Received (Voucher Total)", min_value=0.0)

                if st.form_submit_button("LOG COMPLETE MISSION"):
                    # Inclusion of per_diem in the total expenditure calculation
                    m_gap = (miles_act * 0.725) - (miles_paid * 0.225)
                    total_exp = lodging + per_diem + flight + rental + rent_fuel + airport_etc
                    final_impact = max(0.0, (m_gap + total_exp) - total_reimb)
                    
                    db.table("logs").insert({
                        "user_id": uid, "date": str(t_date), "purpose": "Mission Travel",
                        "total_deduction": final_impact
                    }).execute()
                    st.success(f"Mission Logged. Calculated Impact: ${final_impact:,.2f}")

        with tab2:
            st.subheader("Professional Gear")
            st.warning("⚠️ **IRS COMPLIANCE:** You MUST upload or maintain a physical receipt for any single purchase **over $75**. Logs without proof for high-value items may be disqualified during an audit.")

            st.info("""
            **PURPOSE:** Records the cost of maintaining professional readiness. 
            Includes uniform procurement, rank insignia, cleaning services, and mission-essential equipment 
            not issued by the unit (e.g., boots, tactical tools, and professional dues).
            """)

            with st.expander("📝 VIEW GEAR LOGGING GUIDELINES (IRS & JAG STANDARDS)"):
                st.markdown("""
                ### ✅ WHAT YOU CAN LOG
                *   **Uniforms & Maintenance:** OCPs, ASUs, Mess Dress, and sewing/cleaning.
                *   **Rank & Insignia:** Patches, medals, ribbons, name tapes.
                *   **MOS-Specific Gear:** Equipment required for duty but not issued (e.g., specialized driving gloves for 88M, rugged tools for 12N, personal GPS/Multitools).
                *   **Dues:** AUSA, NGAUS, or MOS trade subscriptions.

                ### ❌ WHAT YOU CANNOT LOG
                *   **Daily Wear:** Plain t-shirts, standard socks, or PT gear (civilian-suitable).
                *   **Grooming:** Haircuts, shaving supplies, or standard gym memberships.
                """)

            with st.form("gear_form", clear_on_submit=True):
                gear_date = st.date_input("Purchase Date", value=datetime.date.today())
                c1, c2 = st.columns(2)
                with c1:
                    u_maint = st.number_input("Uniform/Cleaning", min_value=0.0)
                    insignia = st.number_input("Rank/Patches", min_value=0.0)
                with c2:
                    equipment = st.number_input("Duty Gear/Tools", min_value=0.0)
                    dues = st.number_input("Prof. Dues", min_value=0.0)
                
                if st.form_submit_button("LOG GEAR EXPENDITURE"):
                    total_g = u_maint + insignia + equipment + dues
                    if total_g > 0:
                        db.table("logs").insert({
                            "user_id": uid, "date": str(gear_date), 
                            "purpose": "Professional Gear", "total_deduction": total_g
                        }).execute()
                        st.success(f"Logged ${total_g}. Use 'Vault Upload' to attach proof.")
                    else:
                        st.warning("No values entered.")

        with tab3:
            st.subheader("VA & Medical Transit")
            with st.form("med_form"):
                med_miles = st.number_input("VA/Medical Appointment Miles", min_value=0.0)
                charity_miles = st.number_input("Charitable/Volunteer Miles", min_value=0.0)
                if st.form_submit_button("LOG MEDICAL MILES"):
                    med_total = (med_miles * 0.22) + (charity_miles * 0.14)
                    db.table("logs").insert({
                        "user_id": uid, "date": str(datetime.date.today()), 
                        "purpose": "VA Medical/Charity Travel", "total_deduction": med_total
                    }).execute()
                    st.success(f"Medical Logged: ${med_total:,.2f}")

        with tab4:
            st.subheader("📷 Vault Upload")
            with st.form("vault_form", clear_on_submit=True):
                v_date = st.date_input("Associated Date", value=datetime.date.today())
                v_note = st.text_input("Short Description (e.g., Boots, OCP Cleaning)")
                receipt_file = st.file_uploader("Upload Receipt Image", type=['jpg', 'jpeg', 'png'])
                
                if st.form_submit_button("SECURE TO VAULT"):
                    if receipt_file:
                        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        file_path = f"{uid}/{timestamp}_{receipt_file.name}"
                        try:
                            db.storage.from_("receipts").upload(path=file_path, file=receipt_file.getvalue(), file_options={"content-type": receipt_file.type})
                            db.table("logs").insert({
                                "user_id": uid, "date": str(v_date), 
                                "purpose": f"Receipt Proof: {v_note}", "total_deduction": 0.0,
                                "receipt_url": file_path
                            }).execute()
                            st.success("File secured in tactical vault.")
                        except Exception as e:
                            st.error(f"Upload Error: {str(e)}")

    elif nav == "Intelligence":
        st.header("📊 Tactical Report & Intelligence")
        res = db.table("logs").select("*").eq("user_id", uid).order("date", desc=True).execute()
        
        if res.data:
            df = pd.DataFrame(res.data)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(label="📥 EXPORT LOGS TO CSV", data=csv, file_name=f"Tactical_Asset_Log_{datetime.date.today()}.csv", mime='text/csv')
            st.divider()
            st.subheader("Active Mission Logs")
            st.dataframe(df[["date", "purpose", "total_deduction", "receipt_url"]], use_container_width=True)

            st.subheader("📷 Evidence Retrieval")
            receipt_logs = df[df["receipt_url"].notna()]
            if not receipt_logs.empty:
                selected_log = st.selectbox("Select log to view receipt:", options=receipt_logs.index, format_func=lambda x: f"{receipt_logs.loc[x, 'date']} - {receipt_logs.loc[x, 'purpose']}")
                if st.button("VIEW RECEIPT"):
                    r_path = receipt_logs.loc[selected_log, 'receipt_url']
                    try:
                        signed_res = db.storage.from_("receipts").create_signed_url(r_path, 60)
                        st.image(signed_res['signedURL'], caption=f"Evidence: {r_path}")
                    except Exception as e:
                        st.error(f"Intelligence Failure: {str(e)}")

if __name__ == "__main__":
    main()
