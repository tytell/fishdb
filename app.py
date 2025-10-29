import streamlit as st
import sqlite3
import hashlib

# Page configuration
st.set_page_config(page_title="Login System", page_icon="🔐")

# Initialize session state for login
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_login(username, password):
    """Verify username and password against database"""
    try:
        conn = sqlite3.connect('fish.db')
        cursor = conn.cursor()
        
        # Hash the input password
        hashed_password = hash_password(password)
        
        # Query the database
        cursor.execute(
            "SELECT * FROM People WHERE username = ? AND password = ?",
            (username, hashed_password)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        return result is not None
    except sqlite3.Error as e:
        st.error(f"Database error: {e}")
        return False

def logout():
    """Logout user"""
    st.session_state.logged_in = False
    st.session_state.username = None

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
    st.info("Navigate to the 'Fish Data' page using the sidebar to view the fish table.")
    
    if st.button("Logout"):
        logout()
        st.rerun()