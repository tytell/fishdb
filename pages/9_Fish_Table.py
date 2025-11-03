import streamlit as st
import pandas as pd
import logging

import utils.dbfunctions as db

logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(page_title="Fish Table", page_icon="🐟")

db.stop_if_not_logged_in()

st.title("🐟 Fish Table")
st.subheader(f"Logged in as: {st.session_state.username}")

# Load and display fish data
with st.spinner("Loading fish data..."):
    fish_df = pd.DataFrame(db.get_all_fish())

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