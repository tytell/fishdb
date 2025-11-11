import streamlit as st
from datetime import datetime
import logging
from copy import copy
import pandas as pd

from utils.settings import health_statuses, health_status_colors
import utils.dbfunctions as db
from utils.formatting import apply_custom_css
from utils.date_person import date_person_input

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Page configuration
st.set_page_config(page_title="Add Fish", page_icon="➕", layout="wide")

db.stop_if_not_logged_in()

apply_custom_css()

st.title("➕ Add Fish")
st.subheader(f"Logged in as: {st.session_state.full_name}")

cur_tanks = db.get_all_tanks()
cur_tank_names = {t1['name'] for t1 in cur_tanks}
systems = db.get_all_systems()
system_names = [sys1['name'] for sys1 in systems]

with st.expander("📋 Add Tanks", expanded=False):
    # Configure column settings
    tank_column_config = {
        'name': st.column_config.TextColumn('Name', required=True, max_chars=100,
                                          help='Unique name for each tank',
                                          pinned=True),
        'volume': st.column_config.NumberColumn('Volume (L)', required=True,
                                                help='2, 9, or 18 for plastic tanks. 2gal = 8L, 5.5gal = 21L, 10gal=38L'),
        'is_hospital': st.column_config.CheckboxColumn('Hospital', help='Check if it is a hospital or quarantine tank',
                                                       required=True, default=True),
        'system': st.column_config.SelectboxColumn('System', options=system_names,
                                                   help='System or None if it is a hospital tank'),
        'shelf': st.column_config.NumberColumn('Shelf', 
                                                min_value=1, step=1,
                                                help='Top shelf is 1, increasing downwards'),
        'position_in_shelf': st.column_config.NumberColumn('Location on shelf', 
                                                           min_value=1, step=1,
                                                help='Left side is 1, increasing to the right'),
    }

    # empty data frame with the columns
    new_tanks_df = pd.DataFrame(data = {
        'name': pd.Series(dtype='str'),
        'volume': pd.Series(dtype='float'),
        'is_hospital': pd.Series(dtype='bool'),
        'system': pd.Series(dtype='str'),
        'shelf': pd.Series(dtype='int'),
        'position_in_shelf': pd.Series(dtype='int')})
    
    new_tanks_df = st.data_editor(new_tanks_df,
        column_config=tank_column_config,
        num_rows="dynamic",
        width="stretch",
        key="fish_editor",
        hide_index=True
    )

    if st.button("💾 Save New Tanks", key="save_tanks", type="primary", width='stretch'):
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
                new_tanks_df[['shelf', 'position_in_shelf']] = new_tanks_df[['shelf', 'position_in_shelf']].fillna(0).astype(int)

                added, errors = db.add_tanks(new_tanks_df)
                if errors:
                    for error in errors:
                        st.error(error)
                elif added:
                    st.success("✅ New tanks added successfully!")

with st.expander("📋 Add Collection", expanded=False):
    st.info('All the fish listed below will be identified as being collected at this location. If you collected them at multiple locations, add them separately')

    locations = db.get_all_locations()
    locationnames = [loc['name'] for loc in locations]
    locationnames.append('➕ New location')

    st.header('General location')
    oldloccol, namecol, addresscol, phonecol, urlcol = st.columns(5, gap='small')

    with oldloccol:
        oldloc = st.selectbox('Existing location', options = locationnames)

    with namecol:
        collname = st.text_input('Name', placeholder='Name')
    
    with addresscol:
        address = st.text_input('Address', placeholder='Nearest street address')
    
    with phonecol:
        phone = st.text_input('Phone number', placeholder='Phone number',
                              help='Phone number if from a business')
    
    with urlcol:
        url = st.text_input('URL', placeholder='URL',
                            help='Web link if from a business')
    
    st.divider()

    st.header('Specific details')

    collect_date, collect_person = date_person_input()

    watercol, towncol, latcol, longcol = st.columns(4, gap='small')
    with watercol:
        waterbody = st.text_input('Water body', placeholder='Water body')
    with towncol:
        town = st.text_input('Town', placeholder='Town')
    with latcol:
        latitude = st.number_input('Latitude', placeholder='Latitude')
    with longcol:
        longitude = st.number_input('Longitude', placeholder='Longitude')

    gearcol, effortcol = st.columns(2, gap='small')
    with gearcol:
        gear = st.text_input('Gear', placeholder='Seine or rod')
    with effortcol:
        effort = st.number_input('Effort', placeholder='Number of hauls or casts',
                                 min_value=1)
    
    st.header('Water details')
    tempcol, condcol, phcol, speedcol = st.columns(4, gap='small')
    with tempcol:
        temperature = st.number_input('Temperature', placeholder='deg C')
    with condcol:
        conductivity = st.number_input('Conductivity', placeholder='uS')
    with phcol:
        pH = st.number_input('pH', placeholder='pH')
    with speedcol:
        speed = st.text_input('Speed', placeholder='Description (fast, slow, still) or number')
    
    st.text_input('Notes')



# get tanks again if they were updated
cur_tanks = db.get_all_tanks()
cur_tank_names = [t1['name'] for t1 in cur_tanks]

species = db.get_all_species()
species_names = [s1['name'] for s1 in species]

            
