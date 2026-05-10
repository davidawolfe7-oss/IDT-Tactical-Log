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

    # --- AUTH GATE ---
    if "user" not in st.session_state or st.session_state.user is None:
        st.session_state.user = manager.get('tat_user_id')

    if st.session_state.user is None:
        st.title("🪖 TACTICAL ASSET TRACKER")
        
        auth_mode = st.radio("Select Action", ["Login", "Sign Up"], horizontal=True)
        
        with st.form("auth_form"):
            email = st.text_input("Email")
            pw = st.text_input("Access Key", type="password")
            
            if auth_mode == "Login":
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
            
            else:
                st.info("Creating a new account will establish a unique Tactical Vault for your data.")
                with st.expander("📄 View Beta Terms of Service"):
                    st.markdown("""
                    **1. Purpose & Scope**  
                    Tactical Asset Tracker (TAT) is currently in a Beta testing phase. This tool is designed to assist service members in tracking military logistics; however, it is not an official government or IRS application.
                    
                    **2. Data Security & Privacy**  
                    Your data is stored in a private, encrypted database. While we strive to protect your "Intelligence" and "Vault" uploads, you acknowledge that this is a test environment and sensitive personal data should not be uploaded.
                    
                    **3. No Liability**  
                    The developer is not responsible for any data loss, calculation errors, or issues arising from the use of this data for tax or military reimbursement purposes.
                    """)

                tos_agree = st.checkbox("I have read the Beta Disclaimer and agree to proceed.")
                
                if st.form_submit_button("CREATE ACCOUNT"):
                    if not tos_agree:
                        st.warning("⚠️ High Command requires you to accept the terms before creating an account.")
                    else:
                        try:
                            local_db = get_db()
                            res = local_db.auth.sign_up({"email": email, "password": pw})
                            if res.user:
                                st.success("Account created! You can now switch to Login.")
                                st.balloons()
                        except Exception as e:
                            st.error(f"Registration Error: {str(e)}")
        return # Stop here if not logged in

    # --- COMMAND CENTER (Now inside main() and properly gated) ---
    db = get_db()
    uid = st.session_state.user
    
    # 1. NAVIGATION
    nav = st.sidebar.radio("Sectors", ["Mission Briefing", "Mission Logistics", "Intelligence", "Bug Report"])
    
    if st.sidebar.button("LOGOUT"):
        manager.delete('tat_user_id')
        st.session_state.user = None
        st.rerun()

    # 2. SECTOR: MISSION BRIEFING
    if nav == "Mission Briefing":
        st.title("📂 MISSION BRIEFING: Tactical Tax Intel")
        st.info("Read this section to understand how to maximize your 2026 tax returns using this app.")
        
        st.markdown("""
        ### **Strategic Overview**
        The Tactical Asset Tracker (TAT) is designed to help National Guard and Reserve members recover unreimbursed costs associated with military service. 

        #### **📡 The "Above-the-Line" Travel Win**
        **Crucial Rule:** If you travel **more than 100 miles** from home for military duty (IDT, AT, etc.), the IRS allows you to deduct unreimbursed travel expenses as an **Adjustment to Income**.
        *   **Standard Deduction Friendly:** You claim this *even if you do not itemize*.
        *   **The Mileage Gap:** The gov often pays a lower rate (approx. 0.225) while the IRS allows a much higher business rate (0.725). the app calculates this 'Gap' for you automatically.
        #### **🛡️ The Tactical Vault (Audit Defense)**
        *   **Verification:** The IRS requires proof for lodging and any expense over $75. 
        *   **The Vault:** Snap photos of receipts immediately. Digital copies are audit-ready and won't fade like thermal paper.

        #### **🔧 Professional Gear & Medical**
        *   **Gear:** Uniforms and MOS-specific gear are typically **Itemized Deductions**. Track them here so you are prepared if your total expenses exceed the 2026 Standard Deduction ($16,100 Single / $32,200 Joint).
        *   **VA Transit:** Medical miles contribute to your itemized medical expense totals (deductible once they exceed 7.5% of your AGI).
        """)
        st.success("💡 **Ready to Start?** Switch to 'Mission Logistics' in the sidebar to log your first mission.")

    # 3. SECTOR: MISSION LOGISTICS
    elif nav == "Mission Logistics":
        st.header("🪖 Comprehensive Military Logistics")
        tab1, tab2, tab3, tab4 = st.tabs(["Duty Travel", "Professional Gear", "VA & Medical Transit", "Vault Upload"])
        
        with tab1:
            st.subheader("Duty Travel")
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
                    miles_act = st.number_input("Actual Round-Trip Miles", min_value=0.0)
                    miles_paid = st.number_input("Miles Reimbursed", min_value=0.0)
                    lodging = st.number_input("Out-of-Pocket Lodging", min_value=0.0)
                with c2:
                    per_diem = st.number_input("Per Diem", min_value=0.0)
                    flight = st.number_input("Flight/Rail", min_value=0.0)
                    rental = st.number_input("Rental Car", min_value=0.0)
                    rent_fuel = st.number_input("Rental Fuel", min_value=0.0)
                    airport_etc = st.number_input("Parking/Taxis", min_value=0.0)
                    total_reimb = st.number_input("Total Cash Received", min_value=0.0)

                if st.form_submit_button("LOG COMPLETE MISSION"):
                    m_gap = (miles_act * 0.725) - (miles_paid * 0.225)
                    total_exp = lodging + per_diem + flight + rental + rent_fuel + airport_etc
                    final_impact = max(0.0, (m_gap + total_exp) - total_reimb)
                    db.table("logs").insert({"user_id": uid, "date": str(t_date), "purpose": "Mission Travel", "total_deduction": final_impact}).execute()
                    st.success(f"Mission Logged. Impact: ${final_impact:,.2f}")

        with tab2:
            st.subheader("Professional Gear")
            st.warning("⚠️ **IRS COMPLIANCE:** You MUST upload or maintain a physical receipt for any single purchase **over $75**.")

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
                *   **MOS-Specific Gear:** Equipment required for duty but not issued (e.g., specialized driving gloves, personal GPS/Multitools).
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
                    db.table("logs").insert({"user_id": uid, "date": str(gear_date), "purpose": "Professional Gear", "total_deduction": total_g}).execute()
                    st.success(f"Logged ${total_g}")

        with tab3:
            st.subheader("VA & Medical Transit")
            st.info("""
            **PURPOSE:** Specifically for tracking mileage to VA medical appointments or approved 
            charitable volunteer missions. These miles are calculated at the medical/moving 
            standard rate for tax documentation.
            """)
            with st.form("med_form"):
                med_miles = st.number_input("VA/Medical Miles", min_value=0.0)
                charity_miles = st.number_input("Charitable Miles", min_value=0.0)
                if st.form_submit_button("LOG MEDICAL MILES"):
                    med_total = (med_miles * 0.22) + (charity_miles * 0.14)
                    db.table("logs").insert({"user_id": uid, "date": str(datetime.date.today()), "purpose": "VA Medical/Charity Travel", "total_deduction": med_total}).execute()
                    st.success(f"Medical Logged: ${med_total:,.2f}")

        with tab4:
            st.subheader("📷 Vault Upload")
            with st.expander("📝 Intelligence: Receipt Requirements & Best Practices"):
                st.write("""
                **WHAT TO SECURE:**
                *   **Mandatory:** All Lodging (Hotel/Airbnb) and any single expense **over $75**.
                *   **Recommended:** Rental fuel, tolls, and uniform cleaning (even if under $75).
                
                **WHY SNAP A PHOTO?**
                1.  **Audit Defense:** Digital copies are accepted by the IRS and provide proof of location.
                2.  **Thermal Ink Decay:** Physical receipts fade over time; the Vault keeps them legible.
                3.  **GPS Verification:** A fuel receipt in your duty city acts as a secondary 'boots on the ground' proof.
                """)

            with st.form("vault_form", clear_on_submit=True):
                v_date = st.date_input("Associated Date", value=datetime.date.today())
                v_note = st.text_input("Short Description")
                receipt_file = st.file_uploader("Upload Receipt Image", type=['jpg', 'jpeg', 'png'])
                if st.form_submit_button("SECURE TO VAULT"):
                    if receipt_file:
                        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        file_path = f"{uid}/{timestamp}_{receipt_file.name}"
                        db.storage.from_("receipts").upload(path=file_path, file=receipt_file.getvalue(), file_options={"content-type": receipt_file.type})
                        db.table("logs").insert({"user_id": uid, "date": str(v_date), "purpose": f"Receipt: {v_note}", "total_deduction": 0.0, "receipt_url": file_path}).execute()
                        st.success("File secured.")

    # 4. SECTOR: INTELLIGENCE
    elif nav == "Intelligence":
        st.header("📊 Tactical Report & Intelligence")
        res = db.table("logs").select("*").eq("user_id", uid).order("date", desc=True).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            receipt_logs = df[df['receipt_url'].notna() & (df['receipt_url'] != "") & (df['purpose'].str.contains("Receipt:"))]
            col1, col2 = st.columns([1, 1])
            with col1:
                st.write("### Mission Logs")
                st.dataframe(df[["date", "purpose", "total_deduction"]], use_container_width=True, hide_index=True)
                st.download_button("📥 EXPORT CSV", data=df.to_csv(index=False).encode('utf-8'), file_name="Tactical_Log.csv")
            with col2:
                st.write("### 🖼️ Vault Preview")
                if not receipt_logs.empty:
                    selection = st.selectbox("Select mission to view receipt:", options=receipt_logs.index, format_func=lambda x: f"{receipt_logs.loc[x, 'date']} - {receipt_logs.loc[x, 'purpose']}")
                    path = receipt_logs.loc[selection, 'receipt_url']
                    url_res = db.storage.from_("receipts").create_signed_url(path, 60)
                    st.image(url_res['signedURL'], use_container_width=True)

    # 5. SECTOR: BUG REPORT
    elif nav == "Bug Report":
        st.header("🐞 Bug Reporting")
        with st.form("bug_form", clear_on_submit=True):
            bug_desc = st.text_area("Detailed Description")
            if st.form_submit_button("SUBMIT"):
                db.table("logs").insert({"user_id": uid, "date": str(datetime.date.today()), "purpose": "BUG", "total_deduction": 0.0, "receipt_url": bug_desc}).execute()
                st.success("Intel logged.")

if __name__ == "__main__":
    main()
