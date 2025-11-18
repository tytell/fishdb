import streamlit as st
from datetime import datetime
import logging
from copy import copy
import pandas as pd

from utils.settings import health_statuses, health_status_colors
import utils.dbfunctions as db
from utils.formatting import apply_custom_css
from utils.date_person import date_person_input
import utils.auth as auth

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Page configuration
st.set_page_config(page_title="Recount Fish", page_icon="📊", layout="wide")

db.stop_if_not_logged_in()

apply_custom_css()

st.title("📊 Recount Fish")
st.subheader(f"Logged in as: {st.session_state.full_name}")

# Load fish data
fish_data = db.get_all_fish(include_dead=False, only_groups=True,
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

st.write("**Recount fish:**")

logger.debug(f"{fish_data=}")
for fish_data1 in fish_data.itertuples():
    fish_id = fish_data1.id
    is_submitted = fish_id in st.session_state.submitted_fish
    
    # Display fish info with tank and shelf
    info_text = f"**Fish ID: {fish_id}**"
    if fish_data1.tank:
        info_text += f" | Tank: {fish_data1.tank}"
    
    st.write(info_text)

    numcol, notescol, logcol = st.columns([1, 3, 1], gap='small')
    
    with numcol:
        num = st.number_input("Number", min_value=1, value=fish_data1.number_in_group,
                                disabled=is_submitted, help="Number of fish in group",
                                placeholder='Number',
                                key=f"num_{fish_id}")

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
                is_new_number = num != fish_data1.number_in_group
                if is_new_number and notes == "":
                    st.error(f"There is a different number in group. Add a note to explain why")
                else:
                    if db.log_number_in_group(check_date, selected_person, fish_id, num, notes,
                                              new_number=is_new_number):
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

with st.expander("Split or Merge Groups", expanded=False):
    splittab, mergetab = st.tabs(["Split Group", "Merge Groups"])

    with splittab:
        st.write("**Split a group into two or more groups:**")

        fish_data = db.get_all_fish(include_dead=False, only_groups=True,
                                    return_df=True)
        tanks = db.get_tanks_without_fish()
        tank_names = [t1['name'] for t1 in tanks]

        groupcol, numcol = st.columns([1, 2], gap='small')

        with groupcol:
            group_id = st.selectbox("Select original group to split",
                                        options=[f1.id for f1 in fish_data.itertuples()],
                                        disabled=is_submitted,
                                        help="Original fish group to split",
                                        placeholder='Original Group')
        with numcol:
            original_number = fish_data[fish_data['id'] == group_id]['number_in_group'].values[0]
            st.write(f"**Original number in group:** {original_number}")

        original_fish_data = fish_data[fish_data['id'] == group_id]
        original_fish_data['number_in_group'] = original_fish_data['number_in_group'].astype(int)

        tank_options = copy(tank_names)
        tank_options.append(original_fish_data['tank'].values[0])
        logger.debug(f"{tank_options=}")

        # Configure column settings
        column_config = {
            'id': st.column_config.TextColumn('ID', required=True, max_chars=100,
                                                help='Unique ID for each new group',
                                                pinned=True),
            'tank': st.column_config.SelectboxColumn('Tank', options=tank_options,
                                                        required=True,
                                                        help='Select tank'),
            'status': st.column_config.SelectboxColumn('Status', options=health_statuses, default='Healthy'),
            'number_in_group': st.column_config.NumberColumn('Number', 
                                                                format="%d",
                                                                min_value=int(1),
                                                                step=int(1),
                                                                help='Number of fish in the group',
                                                                default=int(1))
        }

        new_group_df = original_fish_data[['id', 'tank', 'status', 'number_in_group']].copy()
        new_group_df.reset_index(drop=True, inplace=True)

        logger.debug(f"{type(new_group_df)}: {new_group_df=}")

        new_group_df = st.data_editor(new_group_df,
            column_config=column_config,
            num_rows="dynamic",
            width="stretch",
            key="fish_editor",
            hide_index=True
        )        
        split_notes = st.text_area("Split Notes",
                                    key=f"split_notes_{group_id}",
                                    placeholder="Notes about the split...")
        
        if st.button("Split Group", key=f"split_btn_{group_id}", type="primary",
                    use_container_width=True):
            if len(new_group_df) < 2:
                st.error("Must split into at least 2 groups")
                st.stop()
            elif len(new_group_df) > 4:
                st.error("Cannot split into more than 4 groups in one step")
                st.stop()
            elif sum(new_group_df['number_in_group']) != original_fish_data['number_in_group'].astype(int).values[0]:
                st.error("The total number in new groups must equal the original group's number")
                st.stop()
            
            new_group_df['species'] = original_fish_data['species'].values[0]
            new_group_df['collection'] = original_fish_data['collection'].values[0]

            good, errors = db.split_group(group_id, new_group_df, selected_person, check_date, split_notes)
            if good:
                st.session_state.submitted_fish.add(group_id)
                st.success("✅ Group split successfully")
            else:
                st.error("Failed to split group")
                for error in errors:
                    st.error(error)

    with mergetab:
        st.write("**Merge two or more groups into one group:**")

        fish_data = db.get_all_fish(include_dead=False, only_groups=True,
                                    return_df=True)

        selected_groups = st.multiselect(
            "Select groups to merge",
            options=[f1.id for f1 in fish_data.itertuples()],
            help="Select two or more fish groups to merge",
            default=[],
            key="merge_groups_select"
        )

        if len(selected_groups) >= 2:
            merged_species = fish_data[fish_data['id'].isin(selected_groups)]['species'].unique()
            if len(merged_species) > 1:
                st.error("Selected groups must be of the same species to merge")
                st.stop()

            total_number = fish_data[fish_data['id'].isin(selected_groups)]['number_in_group'].sum()
            st.write(f"**Total number in merged group:** {total_number}")

            new_group_id = st.text_input("New Group ID",
                                        key="new_merged_group_id",
                                        placeholder="Enter new group ID for merged group...")
            merge_notes = st.text_area("Merge Notes",
                                        key=f"merge_notes",
                                        placeholder="Notes about the merge...")

            if st.button("Merge Groups", type="primary", use_container_width=True):
                if new_group_id.strip() == "":
                    st.error("New Group ID cannot be empty")
                    st.stop()
                if not db.check_unique_fish_id(new_group_id):
                    st.error("New Group ID must be unique")
                    st.stop()
                if len(selected_groups) < 2:
                    st.error("Select two or more groups to merge")
                    st.stop()
                elif len(selected_groups) > 4:
                    st.error("Cannot merge more than 4 groups in one step")
                    st.stop()

                good, error = db.merge_groups(selected_groups, new_group_id=new_group_id, number_in_group=total_number,
                                              person=selected_person, date_time=check_date, 
                                              notes=merge_notes)
                if good:
                    st.success("✅ Groups merged successfully")
                else:
                    st.error(f"Failed to merge groups: {error}")
        else:
            st.info("Select two or more groups to enable merging.")

if st.button("Next (Organize Tanks)"):
    st.switch_page('pages/6_Organize_Tanks.py')

if st.button("Done and Logout"):
    auth.sign_out()
    st.rerun()
