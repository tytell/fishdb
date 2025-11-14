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
        key="tank_editor",
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

locations = db.get_all_locations()
locationnames = [loc['name'] for loc in locations]

location_options = copy(locationnames)
location_options.append("➕ New location")

location = st.selectbox('General location', options=location_options)

is_new_location = False
with st.expander("📋 Add Location", expanded=(location == "➕ New location")):
    is_new_location = True
    collname = st.text_input('Name', placeholder='Name')
        
    addresscol, phonecol, urlcol = st.columns(3, gap='small')
    with addresscol:
        address = st.text_input('Address', placeholder='Nearest street address')
    with phonecol:
        phone = st.text_input('Phone number', placeholder='Phone number',
                            help='Phone number if from a business')
    with urlcol:
        url = st.text_input('URL', placeholder='URL',
                            help='Web link if from a business')

    towncol, waterbodycol = st.columns(2, gap='small')
    with towncol:
        town = st.text_input('Town', placeholder='Town')
    with waterbodycol:
        waterbody = st.text_input('Water body', placeholder='Water body')

is_collection_details = False
with st.expander("📋 Add Collection Details", expanded=True):
    is_collection_details = True
    
    st.info('All the fish listed below will be identified as being collected at this location. If you collected them at multiple locations, add them separately')

    collect_date, collect_person = date_person_input()

    st.markdown("##### Exact location")
    latcol, longcol = st.columns(2, gap='small')
    with latcol:
        latitude = st.number_input('Latitude', placeholder='Latitude')
    with longcol:
        longitude = st.number_input('Longitude', placeholder='Longitude')

    st.markdown("##### Method details")

    gearcol, effortcol = st.columns(2, gap='small')
    with gearcol:
        gear = st.text_input('Gear', placeholder='Seine or rod')
    with effortcol:
        effort = st.number_input('Effort', placeholder='Number of hauls or casts',
                                min_value=1)
    
    st.markdown("##### Water details")
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

if is_collection_details and location != "➕ New location":
    button_name = "🎣 Save New Collection"
else:
    button_name = "💾 Save New Location"

if st.button(button_name, key="save_collection", type="primary", width='stretch'):
    if location == "➕ New location":
        if not collname:
            st.error("Please provide a name for the new location")
        elif collname in locationnames:
            st.error("Location name must be unique. Please choose a different name.")
        else:
            with st.spinner("Saving new location..."):
                if db.add_location(
                    name=collname,
                    street_address=address,
                    phone_number=phone,
                    url=url,
                    town=town,
                    water_body=waterbody
                ):
                    st.success("✅ New location added successfully!")
    
    if is_collection_details:
        with st.spinner("Saving new collection..."):
            if db.add_collection(
                location_name=location,
                date=collect_date,
                collected_by=collect_person,
                water_body=waterbody,
                town=town,
                latitude=latitude,
                longitude=longitude,
                gear=gear,
                effort=effort,
                temperature=temperature,
                conductivity=conductivity,
                pH=pH,
                speed=speed
            ):
                st.success("✅ New collection added successfully!")

# get tanks again if they were updated
cur_tanks = db.get_tanks_without_fish()
cur_tank_names = [t1['name'] for t1 in cur_tanks]

# get locations again if they were updated
locations_df = db.get_all_locations(return_df=True)

species = db.get_all_species()
species_options = []
for s1 in species:
    if s1['common_name']:
        species_options.append(f"{s1['name']} ({s1['common_name']})")
    else:
        species_options.append(s1['name'])

# Configure column settings
column_config = {
    'id': st.column_config.TextColumn('ID', required=True, max_chars=100,
                                        help='Unique ID for each fish or group of fish',
                                        pinned=True),
    'species': st.column_config.SelectboxColumn('Species', options=list(species_options), 
                                                required=True,
                                                help='Select species name'),
    'tank': st.column_config.SelectboxColumn('Tank', options=cur_tank_names,
                                                required=True,
                                                help='Select tank'),
    'status': st.column_config.SelectboxColumn('Status', options=health_statuses, default='Quarantine'),
    'from': st.column_config.SelectboxColumn('From', options=list(locations_df['name']),
                                                help='Select where the fish was acquired or collected'),
    'number_in_group': st.column_config.NumberColumn('Number', 
                                                        format="%d",
                                                        min_value=int(1),
                                                        step=int(1),
                                                        help='Number of fish in the group',
                                                        default=int(1))
}
            
new_fish_df = pd.DataFrame(data = {
    'id': pd.Series(dtype='str'),
    'species': pd.Series(dtype='str'),
    'tank': pd.Series(dtype='str'),
    'status': pd.Series(dtype='str'),
    'from': pd.Series(dtype='str'),
    'number_in_group': pd.Series(dtype='int'),
})

new_fish_df = st.data_editor(new_fish_df,
    column_config=column_config,
    num_rows="dynamic",
    width="stretch",
    key="fish_editor",
    hide_index=True
)
if st.button("💾 Save New Fish", key="save_fish", type="primary", width='stretch'):
    # validate fish
    cur_fish_ids = db.get_all_fish_ids()
    badid = [row.id for row in new_fish_df.itertuples() if row.id in cur_fish_ids]

    if len(badid) > 0:
        st.error(f"Fish IDs have to be unique. Please change {', '.join(badid)}")
    else:
        with st.spinner("Saving changes..."):
            added, errors = db.add_fish(new_fish_df)
            if errors:
                for error in errors:
                    st.error(error)
            elif added:
                st.success("✅ New fish added successfully!")
