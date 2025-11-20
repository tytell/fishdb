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
logger.setLevel(logging.INFO)

# Page configuration
st.set_page_config(page_title="Organize Tanks", page_icon="🗄️", layout="wide")

db.stop_if_not_logged_in()

apply_custom_css()

st.title("🗄️ Organize Tanks")
st.subheader(f"Logged in as: {st.session_state.full_name}")

cur_tanks_df = db.get_all_tanks(return_df=True)
if 'cur_tanks_df' not in st.session_state:
    st.session_state.cur_tanks_df = cur_tanks_df.copy()

cur_tank_names = set(cur_tanks_df['name'].tolist())
systems = db.get_all_systems()
system_names = [s1['name'] for s1 in systems]

# Configure column settings
tank_column_config = {
    'name': st.column_config.TextColumn('Name', required=True, max_chars=100,
                                        help='Unique name for each tank',
                                        pinned=True, disabled=True),
    'volume': st.column_config.NumberColumn('Volume (L)', required=True,
                                            help='2, 9, or 18 for plastic tanks. 2gal = 8L, 5.5gal = 21L, 10gal=38L'),
    'is_hospital': st.column_config.CheckboxColumn('Hospital', help='Check if it is a hospital or quarantine tank',
                                                    required=True, default=True),
    'system': st.column_config.SelectboxColumn('System', options=system_names,
                                                help='System or None if it is a hospital tank'),
    'active': st.column_config.CheckboxColumn('Active', help='Check if tank is currently in use',
                                                required=True, default=True),
    'shelf': st.column_config.NumberColumn('Shelf', 
                                            min_value=1, step=1,
                                            help='Top shelf is 1, increasing downwards'),
    'position_in_shelf': st.column_config.NumberColumn('Location on shelf', 
                                                        min_value=1, step=1,
                                            help='Left side is 1, increasing to the right'),
}

st.header("Current Tanks")

sortcol, renumbercol, _ = st.columns([1,1,4])
with sortcol:
    sort_by = st.button("Sort by Shelf and Position", key="sort_tanks")
with renumbercol:
    renumber = st.button("Renumber Shelf Positions", key="renumber_tanks",
                        help="Renumber positions on each shelf from left to right starting at 1")

if sort_by:
    sorted_tanks_df = st.session_state.cur_tanks_df.sort_values(by=['system','shelf', 'position_in_shelf'])
else:
    sorted_tanks_df = st.session_state.cur_tanks_df

if renumber:
    sorted_tanks_df = st.session_state.cur_tanks_df.sort_values(by=['system','shelf', 'position_in_shelf'])
    for system in sorted_tanks_df['system'].unique():
        system_mask = sorted_tanks_df['system'] == system

        for shelf in sorted_tanks_df.loc[system_mask, 'shelf'].unique():
            shelf_mask = sorted_tanks_df['shelf'] == shelf
            n_on_shelf = (system_mask & shelf_mask).sum()
            sorted_tanks_df.loc[system_mask & shelf_mask, 'position_in_shelf'] = range(1, n_on_shelf + 1)

updated_tanks_df = st.data_editor(sorted_tanks_df,
    column_config=tank_column_config,
    num_rows="fixed",
    width="stretch",
    key="tank_editor",
    hide_index=True
)

# Update session state
st.session_state.cur_tanks_df = updated_tanks_df

st.header("Add New Tanks")
new_tanks_df = pd.DataFrame(data = {
    'name': pd.Series(dtype='str'),
    'volume': pd.Series(dtype='int'),
    'is_hospital': pd.Series(dtype='bool'),
    'system': pd.Series(dtype='str'),
    'active': pd.Series(dtype='bool'),
    'shelf': pd.Series(dtype='int'),
    'position_in_shelf': pd.Series(dtype='int'),
})

new_tank_column_config = copy(tank_column_config)
new_tank_column_config['name'] = st.column_config.TextColumn('Name', required=True, max_chars=100,
                                        help='Unique name for each tank',
                                        pinned=True, disabled=False)

new_tanks_df = st.data_editor(new_tanks_df,
    column_config=new_tank_column_config,
    num_rows="dynamic",
    width="stretch",
    key="new_tank_editor",
    hide_index=True
)

if st.button("💾 Update Tanks", key="save_tanks", type="primary", width='stretch'):
    # validate tanks
    badname = [row.name for row in new_tanks_df.itertuples() if row.name in cur_tank_names]
    badsys = [row.name for row in new_tanks_df.itertuples() if not row.is_hospital and row.system is None]

    errors = []
    if len(badname) > 0:
        errors.append(f"Tank names have to be unique. Please change {', '.join(badname)}")

    if len(badsys) > 0:
        errors.append(f"Regular tanks must be in a system. Please choose a system for tanks {', '.join(badsys)}")
    
    if errors:
        for err in errors:
            st.error(err)
    else:
        with st.spinner("Saving changes..."):
            # convert blanks to zeros and convert back to int
            updated_tanks_df[['shelf', 'position_in_shelf']] = updated_tanks_df[['shelf', 'position_in_shelf']].fillna(0).astype(int)
            new_tanks_df[['shelf', 'position_in_shelf']] = new_tanks_df[['shelf', 'position_in_shelf']].fillna(0).astype(int)   

            updated, errors = db.update_tanks(updated_tanks_df)

            if not errors:
                added, more_errors = db.add_tanks(new_tanks_df)
                errors.extend(more_errors)

            if errors:
                for error in errors:
                    st.error(error)
            else:
                st.success("✅ Tanks updated successfully!")

                # Clear just the new tank editor
                if 'new_tank_editor' in st.session_state:
                    del st.session_state['new_tank_editor']
                st.rerun()

if st.button("Done and Logout"):
    auth.sign_out()
    st.rerun()
