import streamlit as st
from datetime import datetime
import logging

from utils.settings import health_statuses, health_status_colors
import utils.dbfunctions as db
from utils.formatting import apply_custom_css
from utils.date_person import date_person_input
import utils.auth as auth

logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(page_title="Monthly Tasks", page_icon="🗓️", layout="wide")

db.stop_if_not_logged_in()

apply_custom_css()

st.title("🗓️ Monthly Tasks")
st.subheader(f"Logged in as: {st.session_state.full_name}")

tasks = ['Change carbon',
         'Change mechanical filter',
         'Calibrate pH probe',
         'Calibrate conductivity probe',
         'Check alarm thresholds']

systems = db.get_all_systems()
system_names = [s1['name'] for s1 in systems]

if 'completed_tasks' not in st.session_state:
    st.session_state.completed_tasks = set()

# Top row with Date and Person
check_date, selected_person = date_person_input()

st.divider()

st.write("**Tasks:**")

for task in tasks:
    is_done = task in st.session_state.completed_tasks

    taskcol, notescol, systemcol, logcol = st.columns([2, 5, 1, 1], gap='small')
    
    with taskcol:
        st.markdown(f"**{task}**")

    with notescol:
        notes = st.text_input(
            "Notes", 
            key=f"notes_{task}", 
            label_visibility="collapsed", 
            placeholder="Notes..." if not is_done else "Done",
            disabled=is_done
        )
    
    with systemcol:
        system = st.selectbox(
            "System", 
            options=[""] + system_names, 
            key=f"system_{task}", 
            label_visibility="collapsed",
            disabled=is_done
        )

    with logcol:
        if is_done:
            st.button("✓ Done", key=f"btn_{task}", disabled=True, use_container_width=True)
        else:
            if st.button("Done", key=f"btn_{task}", type="primary", use_container_width=True):
                if selected_person:
                    do_log = True
                    
                    if db.log_maintenance(check_date, selected_person, task, system, notes):
                        st.session_state.completed_tasks.add(task)
                        st.success(f"✅ Done")
                    else:
                        st.error(f"Failed")
                else:
                    st.error("Select a person")
    
    # Apply gray styling for completed tasks
    if is_done:
        st.markdown(
            """
            <style>
            div[data-testid="stVerticalBlock"] > div:has(button[kind="primary"][disabled]) {
                opacity: 0.5;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
    
    st.divider()

if st.button("Done and Logout"):
    auth.sign_out()
    st.rerun()

# Previous maintenance logs
st.subheader("📋 Previous Maintenance Logs")

# Date range selector
date_range_options = {
    "Last 7 days": 7,
    "Last 14 days (default)": 14,
    "Last 30 days": 30,
    "Last 60 days": 60,
    "Last 90 days": 90
}

selected_range = st.selectbox(
    "Select date range",
    list(date_range_options.keys()),
    index=1  # Default to 14 days
)

days_back = date_range_options[selected_range]

# Fetch and display health notes
maintenance_logs_df = db.get_maintenance_logs(days_back=days_back)

if not maintenance_logs_df.empty:
    st.success(f"Found {len(maintenance_logs_df)} health record(s)")
    
    # Display each health note as a card
    for _, maint in maintenance_logs_df.iterrows():
        with st.container():
            maint_date = datetime.fromisoformat(maint['date'].replace('Z', '+00:00'))
            
            # Create columns for the note header
            maint_cols = st.columns([3, 2, 2], gap="small")
            
            with maint_cols[0]:
                st.markdown(f"**📅 {maint_date.strftime('%Y-%m-%d %H:%M')}**")
            with maint_cols[1]:
                event_type = maint['task']
                st.markdown(f"**{event_type}**")

            with maint_cols[2]:
                st.markdown(f"*By: {maint.get('by', 'Unknown')}*")
            
            st.markdown(f"**System:** {maint.get('system', 'N/A')}")
            st.markdown(f"**Notes:** {maint.get('notes', 'N/A')}")

            st.markdown("---")
else:
    st.info(f"No maintenance records found for the selected date range ({selected_range})")

