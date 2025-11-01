import streamlit as st
import sqlite3
import pandas as pd

# Page configuration
st.set_page_config(page_title="Fish Table", page_icon="🐟")

# Check if user is logged in
if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.warning("⚠️ Please login first!")
    st.info("Use the sidebar to navigate back to the Login page.")
    st.stop()

st.title("🐟 Fish Table")
st.subheader(f"Logged in as: {st.session_state.username}")

# Function to load fish data
def load_fish_data():
    """Load fish data from database"""
    try:
        conn = sqlite3.connect('fish.db')
        query = "SELECT * FROM Fish"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except sqlite3.Error as e:
        st.error(f"Database error: {e}")
        return None
    except Exception as e:
        st.error(f"Error: {e}")
        return None

# Load and display fish data
with st.spinner("Loading fish data..."):
    fish_df = load_fish_data()

if fish_df is not None:
    if not fish_df.empty:
        st.success(f"Found {len(fish_df)} records in the Fish table")
        
        # Display dataframe
        st.dataframe(fish_df, use_container_width=True)
        
        # Optional: Add download button
        csv = fish_df.to_csv(index=False)
        st.download_button(
            label="📥 Download as CSV",
            data=csv,
            file_name="fish_data.csv",
            mime="text/csv"
        )
    else:
        st.info("The Fish table is empty.")
else:
    st.error("Could not load fish data. Please check if the database and table exist.")

# Logout button
if st.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.username = None
    st.success("Logged out successfully!")
    st.info("Navigate back to the Login page using the sidebar.")