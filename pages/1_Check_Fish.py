import streamlit as st
import sqlite3
from datetime import datetime
import logging

from utils.settings import health_statuses, health_status_colors
import utils.dbfunctions as db

logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(page_title="Check Fish", page_icon="🐠", layout="wide")

db.stop_if_not_logged_in()

st.title("🐠 Check Fish")
st.subheader(f"Logged in as: {st.session_state.username}")

# Load fish data
fish_data = db.get_all_fish(include_dead=False)
tanks = db.get_all_tanks()

if not fish_data:
    st.warning("No fish found in the database.")
    st.stop()

if 'submitted_fish' not in st.session_state:
    st.session_state.submitted_fish = set()

# Top row with Date and Person
col1, col2, col3 = st.columns(3)

with col1:
    check_date = st.text_input(
        "Date",
        value=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

with col2:
    people_data = db.get_all_people()
    usernames = people_data.keys()
    people_names = people_data.values()
    if st.session_state.username in people_data:
        default_name_ind = list(people_names).index(people_data[st.session_state.username])
    else:
        default_name_ind = 0
        logger.warning(f'Username {st.session_state.username} not found in database')

    if people_names:
        selected_person = st.selectbox("Person", people_names,
                                    index = default_name_ind)
    else:
        st.warning("No people found in People table")
        selected_person = None

with col3:
    sort_by = st.selectbox("Sort by", ["Fish ID", "Tank", "Shelf"])

st.divider()

# Sort fish based on user selection
if sort_by == "Tank":
    fish_data_sorted = sorted(fish_data, key=lambda x: (x['Tank'] or "", x['ID']))
elif sort_by == "Shelf":
    fish_data_sorted = sorted(fish_data, key=lambda x: (x['Shelf'] or "", x['ID']))
else:  # Fish ID
    fish_data_sorted = sorted(fish_data, key=lambda x: x['ID'])

st.write("**Fish Checks:**")

for fish_data1 in fish_data_sorted:
    fish_id = fish_data1['ID']
    is_submitted = fish_id in st.session_state.submitted_fish
    
    # Display fish info with tank and shelf
    info_text = f"**Fish ID: {fish_id}**"
    if fish_data1['Tank']:
        info_text += f" | Tank: {fish_data1['Tank']}"
    if fish_data1['Shelf']:
        info_text += f" | Level: {fish_data1['Shelf']}"
    st.write(info_text)
    
    fedcol, atecol, healthcol, notescol, logcol = st.columns([1, 1, 2, 3, 1])
    
    with fedcol:
        fed = st.checkbox("Fed", key=f"fed_{fish_id}", disabled=is_submitted)
    
    with atecol:
        ate = st.checkbox("Ate", key=f"ate_{fish_id}", disabled=is_submitted)

    with healthcol:
        # Health status dropdown
        current_status = fish_data1['Status'] or 'Healthy'
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

# # Group fish by tank
# fish_by_tank = {}
# for fish in fish_list:
#     tank = fish['Tank'] or 'Unassigned'
#     if tank not in fish_by_tank:
#         fish_by_tank[tank] = []
#     fish_by_tank[tank].append(fish)

# # Display fish grouped by tank
# for tank_name, fish_in_tank in fish_by_tank.items():
#     system = fish_in_tank[0]['System'] if fish_in_tank[0]['System'] else 'No System'
    
#     with st.expander(f"**{tank_name}** ({system}) - {len(fish_in_tank)} fish", expanded=True):
#         for fish in fish_in_tank:
#             col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 2])
            
#             with col1:
#                 status_icon = status_colors.get(fish['Status'], "⚪")
#                 st.write(f"**{fish['common_name']}** {status_icon}")
#                 st.caption(f"ID: {fish['id']} | {fish['species']}")
#                 st.caption(f"Size: {fish['length_cm']}cm, {fish['weight_kg']}kg")
            
#             with col2:
#                 # Health status dropdown
#                 current_status = fish['Status'] or 'Healthy'
#                 new_status = st.selectbox(
#                     "Health Status",
#                     health_statuses,
#                     index=health_statuses.index(current_status) if current_status in health_statuses else 0,
#                     key=f"status_{fish['id']}"
#                 )
                
#                 if new_status != current_status:
#                     if update_fish_status(fish['id'], new_status):
#                         st.success("Updated!")
#                         st.rerun()
            
#             with col3:
#                 # Move tanks button and dialog
#                 if st.button("Move Tank", key=f"move_btn_{fish['id']}"):
#                     st.session_state[f'show_move_{fish["id"]}'] = True
                
#                 if st.session_state.get(f'show_move_{fish["id"]}', False):
#                     new_tank = st.selectbox(
#                         "Select new tank:",
#                         tanks,
#                         key=f"tank_select_{fish['id']}"
#                     )
                    
#                     col_a, col_b = st.columns(2)
#                     with col_a:
#                         if st.button("Confirm", key=f"confirm_{fish['id']}"):
#                             if move_fish_to_tank(fish['id'], new_tank):
#                                 st.success(f"Moved to {new_tank}!")
#                                 st.session_state[f'show_move_{fish["id"]}'] = False
#                                 st.rerun()
#                     with col_b:
#                         if st.button("Cancel", key=f"cancel_{fish['id']}"):
#                             st.session_state[f'show_move_{fish["id"]}'] = False
#                             st.rerun()
            
#             with col4:
#                 # Feed button
#                 if st.button("🍽️ Feed", key=f"feed_{fish['id']}"):
#                     st.success(f"Fed {fish['common_name']}!")
#                     # You can add feeding log to database here
            
#             with col5:
#                 # Check button
#                 if st.button("🔍 Check", key=f"check_{fish['id']}"):
#                     st.info(f"Checked {fish['common_name']}!")
#                     # You can add check log to database here
            
#             st.divider()

# # Summary statistics
# st.subheader("Summary")
# col1, col2, col3, col4 = st.columns(4)

# total_fish = len(fish_list)
# healthy_count = sum(1 for f in fish_list if f['Status'] == 'Healthy')
# monitor_count = sum(1 for f in fish_list if f['Status'] == 'Monitor')
# diseased_count = sum(1 for f in fish_list if f['Status'] == 'Diseased')
# dead_count = sum(1 for f in fish_list if f['Status'] == 'Dead')

# with col1:
#     st.metric("Total Fish", total_fish)
# with col2:
#     st.metric("🟢 Healthy", healthy_count)
# with col3:
#     st.metric("🟡 Monitor", monitor_count)
# with col4:
#     st.metric("🟠 Diseased", diseased_count)

# if dead_count > 0:
#     st.error(f"🔴 {dead_count} fish marked as dead")

# # Logout button
# if st.button("Logout"):
#     st.session_state.logged_in = False
#     st.session_state.username = None
#     st.success("Logged out successfully!")
#     st.info("Navigate back to the Login page using the sidebar.")
