import streamlit as st
from datetime import datetime
import logging
from copy import copy

from utils.settings import health_statuses, health_status_colors
import utils.dbfunctions as db
from utils.formatting import apply_custom_css
from utils.date_person import date_person_input

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Page configuration
st.set_page_config(page_title="Recount Fish", page_icon="📊", layout="wide")

db.stop_if_not_logged_in()

apply_custom_css()

st.title("📊 Recount Fish")
st.subheader(f"Logged in as: {st.session_state.full_name}")

# Load fish data
# Load fish data
fish_data = db.get_all_fish(include_dead=False, only_groups=True)
tanks = db.get_all_tanks()
tanks = [t1['name'] for t1 in tanks]

if not fish_data:
    st.warning("No fish found in the database.")
    st.stop()

if 'submitted_fish' not in st.session_state:
    st.session_state.submitted_fish = set()

# Top row with Date and Person
check_date, selected_person = date_person_input()

st.divider()

st.write("**Recount fish:**")

for fish_data1 in fish_data:
    fish_id = fish_data1['id']
    is_submitted = fish_id in st.session_state.submitted_fish
    
    # Display fish info with tank and shelf
    info_text = f"**Fish ID: {fish_id}**"
    if fish_data1['tank']:
        info_text += f" | Tank: {fish_data1['tank']}"
    if fish_data1['shelf']:
        info_text += f" | Shelf: {fish_data1['shelf']}"
    
    st.write(info_text)

    numcol, notescol, logcol = st.columns([1, 3, 1],
                                                             gap='small')
    
    with numcol:
        num = st.number_input("Number", min_value=1, value=fish_data1['number_in_group'],
                                disabled=is_submitted, help="Number of fish in group",
                                placeholder='Number')

    with notescol:
        notes = st.text_input(
            "Notes", 
            key=f"notes_{fish_id}", 
            label_visibility="collapsed", 
            placeholder="Notes..." if not is_submitted else "Submitted",
            disabled=is_submitted
        )
    
    with logcol:
        if is_submitted:
            st.button("✓ Logged", key=f"btn_{fish_id}", disabled=True, use_container_width=True)
        else:
            if st.button("Log", key=f"btn_{fish_id}", type="primary", use_container_width=True):
                is_new_number = num != fish_data1['number_in_group']
                if is_new_number and notes == "":
                    st.error(f"There is a different number in group. Add a note to explain why")
                else:
                    if db.log_number_in_group(check_date, selected_person, fish_id, num, notes,
                                              is_new_number=is_new_number):
                        st.session_state.submitted_fish.add(fish_id)
                        st.success(f"✅ Logged")
                    else:
                        st.error(f"Failed")
    
    # Apply gray styling for submitted fish
    if is_submitted:
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