import streamlit as st
import pandas as pd
import logging

import utils.dbfunctions as db

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Page configuration
st.set_page_config(page_title="Fish Table", page_icon="🐟")

db.stop_if_not_logged_in()

st.title("🐟 Fish Table")
st.subheader(f"Logged in as: {st.session_state.full_name}")

# Get all tables
all_tables = db.get_all_table_names()

table_name = st.selectbox("Select Table to View", options=all_tables, 
                          index=all_tables.index('Fish'))

# Load and display fish data
table = None
with st.spinner(f"Loading table {table_name}..."):
    table = db.get_all_from_table(table_name, return_df=True)

if table is not None:
    if not table.empty:
        st.success(f"Found {len(table)} records in the {table_name} table")
                
        st.markdown("## Filter")
        filtercol, fishcol, bycol, datecol1, datecol2 = st.columns(5)

        is_fish = pd.Series([True] * len(table))
        is_by = pd.Series([True] * len(table))
        is_date = pd.Series([True] * len(table))

        if 'fish' in table.columns:
            with fishcol:
                fish_filter = st.multiselect("Fish", options=[""] + sorted(table['fish'].astype(str).unique().tolist()))
                if fish_filter:
                    is_fish = table['fish'].isin(fish_filter)

        if 'by' in table.columns:
            with bycol:
                by_filter = st.multiselect("By", options=[""] + sorted(table['by'].astype(str).unique().tolist()))
                if by_filter:
                    is_by = table['by'].isin(by_filter)

        if 'date' in table.columns:
            dates = pd.to_datetime(table['date']).dt.date
            logger.debug(f"{dates=}")
                         
            with datecol1:
                start_date_filter = st.date_input("Start date")
            with datecol2:
                end_date_filter = st.date_input("End date")
            
            logger.debug(f"{start_date_filter=}, {end_date_filter=}")

            if start_date_filter and not end_date_filter:
                is_date = (dates >= start_date_filter)
            elif end_date_filter and not start_date_filter:
                isdate = (dates <= end_date_filter)
            elif start_date_filter and end_date_filter:
                isdate = (dates <= end_date_filter) & \
                         (dates >= start_date_filter)

        with filtercol:
            do_filter = st.button("Filter")

        if do_filter:
            filtered_table = table[is_fish & is_by & is_date]
        else:
            filtered_table = table
        
        # Display dataframe
        st.markdown("## Data")        
        st.dataframe(filtered_table, width='stretch')
        
        # Optional: Add download button
        csv = table.to_csv(index=False)
        st.download_button(
            label="📥 Download as CSV",
            data=csv,
            file_name="fish_data.csv",
            mime="text/csv"
        )
    else:
        st.info(f"The {table_name} table is empty.")
else:
    st.error(f"Could not load {table_name}. Please check if the database and table exist.")

# Logout button
if st.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.user = None
    st.success("Logged out successfully!")
    st.info("Navigate back to the Login page using the sidebar.")