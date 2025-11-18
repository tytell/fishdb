import streamlit as st
import os
import sys
import logging
import argparse

logging.basicConfig(level=logging.WARNING,
                    format='%(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

from utils.dbfunctions import verify_login
import utils.auth as auth
from utils.formatting import apply_custom_css

logger.debug('Starting!')

# Page configuration
st.set_page_config(page_title="Login System", page_icon="🔐")

# Initialize session state for login
if 'user' not in st.session_state:
    st.session_state.user = None
if 'session' not in st.session_state:
    st.session_state.session = None
if 'full_name' not in st.session_state:
    st.session_state.full_name = None

# Get database

# parser = argparse.ArgumentParser(
#     description='FishDB Streamlit app')
# parser.add_argument('--bypass_login', help='Bypass login screen for testing')

# args = parser.parse_args()

# # Get database connection
# if args.bypass_login:
#     st.session_state.logged_in = True
#     st.session_state.user = args.bypass_login

apply_custom_css()

# Main login page
st.title("🔐 Login System")

if st.session_state.user is None:
    st.subheader("Please login to continue")
    
    tab1, tab2, tab3 = st.tabs(["Sign In", "Sign Up", "Reset Password"])
    
    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email", key='login_email')
            password = st.text_input("Password", type="password", key="login_password")
            submit = st.form_submit_button("Login")
            
            if submit:
                if email and password:
                    if auth.sign_in(email, password):
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
                else:
                    st.warning("Please enter both username and password")
    
    with tab2:
        st.subheader("Create New Account")
        with st.form("sign_up_form"):
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_password")
            password_confirm = st.text_input("Confirm Password", type="password", key="signup_password_confirm")

            submit = st.form_submit_button("Sign Up")
            
            if submit:
                if email and password and password_confirm:
                    if password == password_confirm:
                        if len(password) >= 8:
                            auth.sign_up(email, password)
                        else:
                            st.error("Password must be at least 8 characters long")
                    else:
                        st.error("Passwords do not match")
                else:
                    st.error("Please fill in all fields")
    
    with tab3:
        st.subheader("Reset Password")
        st.write("Enter your email address and we'll send you a link to reset your password.")
        with st.form("reset_password_form"):
            email = st.text_input("Email", key="reset_email")
            submit = st.form_submit_button("Send Reset Link")
            
            if submit:
                if email:
                    auth.reset_password(email)
                else:
                    st.error("Please enter your email address")

else:
    if st.session_state.full_name is None:
        # new user
        with st.form("Add your information"):
            full_name = st.text_input("Full Name", key="new_fullname")
            phone = st.text_input("Mobile Phone", key="new_phone")
            level = st.selectbox("Level",
                                 ("Undergraduate", "Graduate", "Postdoc", "Other"))
            non_tufts_email = st.text_input("Non-Tufts email", key="new_nontuftsemail")

            submit = st.form_submit_button("Update")
            if submit:
                if auth.add_update_person(full_name, level, phone, non_tufts_email):
                    st.session_state.full_name = full_name
                    st.rerun()
                else:
                    st.error("Problem adding your information")

    else:
        st.success(f"Welcome, {st.session_state.full_name}!")

        dailycol, weeklycol, othercol = st.columns(3, gap='large')

        with dailycol:
            st.markdown("**Daily Tasks:**")     
            if st.button("Check water"):
                st.switch_page('pages/1_Check_Water.py')
            if st.button("Check fish"):
                st.switch_page('pages/2_Check_Fish.py')
            if st.button("Log health details"):
                st.switch_page('pages/3_Health_Details.py')

        with weeklycol:
            st.markdown("**Weekly Tasks:**")     
            if st.button("Weekly tasks"):
                st.switch_page('pages/4_Weekly_Tasks.py')
            if st.button("Recount Fish"):
                st.switch_page('pages/5_Recount_Fish.py')
        
        with othercol:
            st.markdown("**Other:**")     
            if st.button("Organize tanks"):
                st.switch_page('pages/6_Organize_Tanks.py')
            if st.button("Add fish"):
                st.switch_page('pages/7_Add_Fish.py')
            if st.button("Monthly tasks"):
                st.switch_page('pages/8_Monthly_Tasks.py')

        if st.button("Logout"):
            auth.logout()
            st.rerun()
