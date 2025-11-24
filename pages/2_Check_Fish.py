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
st.set_page_config(page_title="Check Fish", page_icon="🐠", layout="wide")

db.stop_if_not_logged_in()

apply_custom_css()

st.title("🐠 Check Fish")
st.subheader(f"Logged in as: {st.session_state.full_name}")

# Load fish data
fish_data = db.get_all_fish(include_dead=False,
                            return_df=True)
tanks = db.get_all_tanks()
tanks = [t1['name'] for t1 in tanks]

if fish_data.empty:
    st.warning("No fish found in the database.")
    st.stop()

if 'submitted_fish' not in st.session_state:
    st.session_state.submitted_fish = set()

# Top row with Date and Person
check_date, selected_person = date_person_input()

st.divider()

# Sort fish based on user selection
sort_by = st.selectbox('Sort by', ['Fish ID', 'Location'])
if sort_by == "Location":
    fish_data.sort_values(by = ['system', 'shelf', 'position_in_shelf'], inplace=True)
else:  # sort by ID
    fish_data.sort_values(by = ['id'], inplace=True)

st.write("**Fish Checks:**")

for fish_data1 in fish_data.itertuples():
    fish_id = fish_data1.id
    is_submitted = fish_id in st.session_state.submitted_fish
    
    # Display fish info with tank and shelf
    info_text = f"**Fish ID: {fish_id}**"
    if fish_data1.tank:
        info_text += f" | Tank: {fish_data1.tank}"
    
    st.write(info_text)

    if fish_data1.number_in_group is not None and \
        fish_data1.number_in_group > 1:
        numcol, fedcol, atecol, healthcol, notescol, logcol = st.columns([1, 1, 1, 2, 3, 1],
                                                             gap='small')
    else:
        numcol = None
        fedcol, atecol, healthcol, notescol, logcol = st.columns([1, 1, 2, 3, 1],
                                                             gap='small')
    
    if numcol:
        with numcol:
            num = st.number_input("Number", min_value=1, value=None,
                                  disabled=is_submitted, help="Number of fish in group",
                                  label_visibility='collapsed', placeholder='Number',
                                  key=f"num_{fish_id}")
    else:
        num = None

    with fedcol:
        fed = st.checkbox("Fed", key=f"fed_{fish_id}", disabled=is_submitted)
    
    with atecol:
        ate = st.checkbox("Ate", key=f"ate_{fish_id}", disabled=is_submitted)

    with healthcol:
        # Health status dropdown
        current_status = fish_data1.status or 'Healthy'
        status_index = health_statuses.index(current_status) if current_status in health_statuses else 0
        new_status = st.selectbox(
            "Health",
            health_status_colors,
            index=status_index,
            key=f"status_{fish_id}",
            disabled=is_submitted,
            label_visibility='collapsed'
        )
        new_status = health_status_colors[new_status]

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
                if selected_person:
                    do_log = True
                    if new_status != current_status:
                        if notes == "":
                            st.error(f"Add a note")
                            do_log = False
                        else:
                            db.log_new_health_status(check_date, selected_person, fish_id, new_status, notes)

                    if num is not None and num != fish_data1.number_in_group:
                        if notes == "":
                            st.error(f"There is a different number in group. Add a note to explain why")
                            do_log = False
                        else:
                            db.log_number_in_group(check_date, selected_person, fish_id, num, notes)

                    if do_log:
                        if db.log_check(check_date, selected_person, fish_id, fed, ate, notes):
                            st.session_state.submitted_fish.add(fish_id)
                            st.success(f"✅ Logged")
                        else:
                            st.error(f"Failed")
                else:
                    st.error("Select a person")
    
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

fish_in_same_tank = db.check_fish_in_same_tank()

if fish_in_same_tank:
    st.warning("⚠️ Some fish are recorded in the same tank. Please verify their locations in the 'Health Details' page.")
    for t1, fish_list in fish_in_same_tank.items():
        st.write(f"**Tank {t1}:** " + ", ".join(fish_list))
        
    if st.button("Go to Health Details"):
        st.switch_page('pages/3_Health_Details.py')

if st.button("Next (Log health details if needed)"):
    st.switch_page('pages/3_Health_Details.py')

if st.button("Done and Logout"):
    auth.sign_out()
    st.rerun()

