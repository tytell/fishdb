import streamlit as st
from datetime import datetime
import logging

from utils.settings import health_statuses, health_status_colors
import utils.dbfunctions as db
from utils.formatting import apply_custom_css

logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(page_title="Check Fish", page_icon="🐠", layout="wide")

db.stop_if_not_logged_in()

apply_custom_css()

st.title("🐠 Check Fish")
st.subheader(f"Logged in as: {st.session_state.full_name}")

# Load fish data
fish_data = db.get_all_fish(include_dead=False)
tanks = db.get_all_tanks()

if not fish_data:
    st.warning("No fish found in the database.")
    st.stop()

if 'submitted_fish' not in st.session_state:
    st.session_state.submitted_fish = set()

# Top row with Date and Person
col1, col2, col3 = st.columns(3, gap='small')

with col1:
    check_date = st.text_input(
        "Date",
        value=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

with col2:
    people = db.get_all_people()
    if st.session_state.full_name in people:
        default_name_ind = list(people).index(st.session_state.full_name)
    else:
        default_name_ind = 0
        logger.warning(f'Username {st.session_state.full_name} not found in database')

    if people:
        selected_person = st.selectbox("Person", people,
                                    index = default_name_ind)
    else:
        st.warning("No people found in People table")
        selected_person = None

with col3:
    sort_by = st.selectbox("Sort by", ["Fish ID", "Tank", "Shelf"])

st.divider()

# Sort fish based on user selection
if sort_by == "Tank":
    fish_data_sorted = sorted(fish_data, key=lambda x: (x['tank'] or "", x['id']))
elif sort_by == "Shelf":
    fish_data_sorted = sorted(fish_data, key=lambda x: (x['shelf'] or "", x['id']))
else:  # Fish ID
    fish_data_sorted = sorted(fish_data, key=lambda x: x['id'])

st.write("**Fish Checks:**")

for fish_data1 in fish_data_sorted:
    fish_id = fish_data1['id']
    is_submitted = fish_id in st.session_state.submitted_fish
    
    # Display fish info with tank and shelf
    info_text = f"**Fish ID: {fish_id}**"
    if fish_data1['tank']:
        info_text += f" | Tank: {fish_data1['tank']}"
    if fish_data1['shelf']:
        info_text += f" | Shelf: {fish_data1['shelf']}"
    st.write(info_text)
    
    fedcol, atecol, healthcol, notescol, logcol = st.columns([1, 1, 2, 3, 1],
                                                             gap='small')
    
    with fedcol:
        fed = st.checkbox("Fed", key=f"fed_{fish_id}", disabled=is_submitted)
    
    with atecol:
        ate = st.checkbox("Ate", key=f"ate_{fish_id}", disabled=is_submitted)

    with healthcol:
        # Health status dropdown
        current_status = fish_data1['status'] or 'Healthy'
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
