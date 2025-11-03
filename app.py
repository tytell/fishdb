import streamlit as st
import os
import sys
import logging
import argparse

from utils.settings import DB_FILE
from utils.dbfunctions import verify_login

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

logger.debug('Starting!')

# Page configuration
st.set_page_config(page_title="Login System", page_icon="🔐")

# Initialize session state for login
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'conn' not in st.session_state:
    st.session_state.conn = None


def logout():
    """Logout user"""
    st.session_state.logged_in = False
    st.session_state.username = None

# Get database

parser = argparse.ArgumentParser(
    description='FishDB Streamlit app')
parser.add_argument('--bypass_login', help='Bypass login screen for testing')

args = parser.parse_args()

# Check if database exists
if not os.path.exists(DB_FILE):
    st.error(f"Database file '{DB_FILE}' not found!")
    st.info(f"Please make sure the '{DB_FILE}' file is in the same directory as this script.")
    st.stop()

# Get database connection
if args.bypass_login:
    st.session_state.logged_in = True
    st.session_state.username = args.bypass_login

# Main login page
st.title("🔐 Login System")

if not st.session_state.logged_in:
    st.subheader("Please login to continue")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            if username and password:
                if verify_login(username, password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
            else:
                st.warning("Please enter both username and password")
else:
    st.success(f"Welcome, {st.session_state.username}!")
    
    if st.button("Check fish"):
        st.switch_page('pages/1_Check_Fish.py')
        
    if st.button("Logout"):
        logout()
        st.rerun()
