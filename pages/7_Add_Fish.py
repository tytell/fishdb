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
                    st.rerun()

collections = db.get_all_collections()
# make it a set to ignore duplicates
order_names = {c['name'] for c in collections if c['is_commercial']}
order_names = list(order_names)
order_names.append('➕ New Commercial Source')
order_names.append('🎣 New Collection')

selected_collection = st.selectbox('Received fish from', options=order_names)

collect_date, collect_person = date_person_input()
notes = st.text_input('Notes')

with st.expander("📋 Add Commercial Source", expanded=selected_collection == '➕ New Commercial Source'):
    source_name = st.text_input('Name', placeholder='Name of business or person',
                                key='source_name')
    
    addresscol, towncol = st.columns(2, gap='small')
    with addresscol:
        address = st.text_input('Address', placeholder='Street address',
                            key='commercial_address')
    with towncol:
        town = st.text_input('Town', placeholder='Town',
                                key='commercial_town')

    phonecol, urlcol = st.columns(2, gap='small')
    with phonecol:
        phone = st.text_input('Phone number', placeholder='Phone number',
                            help='Phone number')
    with urlcol:
        url = st.text_input('URL', placeholder='URL',
                            help='Web link')


with st.expander("📋 Add Collection", expanded=selected_collection == '➕ Add new collection'):
    st.info('All the fish listed below will be identified as being collected at this location. If you collected them at multiple locations, add them separately')

    collname = st.text_input('Name', placeholder='Name')
        
    addresscol, towncol, waterbodycol = st.columns(3, gap='small')
    with addresscol:
        address = st.text_input('Address', placeholder='Nearest street address',
                            key='collection_address')
    with towncol:
        town = st.text_input('Town', placeholder='Town',
                                key='collection_town')
    with waterbodycol:
        waterbody = st.text_input('Water body', placeholder='Water body')

    collect_date, collect_person = date_person_input(key='collection')

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

# get tanks again if they were updated
cur_tanks = db.get_tanks_without_fish()
cur_tank_names = [t1['name'] for t1 in cur_tanks]

species = db.get_all_species()
species_options = {}
for s1 in species:
    if s1['common_name']:
        disp_name = f"{s1['name']} ({s1['common_name']})"
    else:
        disp_name = s1['name']
    species_options[disp_name] = s1['name']

# Configure column settings
column_config = {
    'id': st.column_config.TextColumn('ID', required=True, max_chars=100,
                                        help='Unique ID for each fish or group of fish',
                                        pinned=True),
    'species': st.column_config.SelectboxColumn('Species', options=list(species_options.keys()), 
                                                required=True,
                                                help='Select species name'),
    'tank': st.column_config.SelectboxColumn('Tank', options=cur_tank_names,
                                                required=True,
                                                help='Select tank'),
    'status': st.column_config.SelectboxColumn('Status', options=health_statuses, default='Quarantine'),
    # 'from': st.column_config.SelectboxColumn('From', options=list(locations_df['name']),
    #                                             help='Select where the fish was acquired or collected'),
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
    # 'from': pd.Series(dtype='str'),
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
    with st.spinner("Adding collection..."):
        # save collection / commercial source
        if selected_collection == '➕ New Commercial Source':
            collection_id = db.add_collection(
                date_time=collect_date,
                person=collect_person,
                name=source_name,
                street_address=address,
                town=town,
                phone_number=phone,
                url=url,
                notes=notes,
                is_commercial=True
            )
        elif selected_collection == '🎣 New Collection':
            collection_id = db.add_collection(
                date_time=collect_date,
                person=collect_person,
                name=collname,
                street_address=address,
                town=town,
                water_body=waterbody,
                latitude=latitude,
                longitude=longitude,
                sampling_gear=gear,
                number_of_tries=effort,
                water_temp=temperature,
                water_conductivity=conductivity,
                water_pH=pH,
                water_flow_speed=speed,
                notes=notes,
                is_commercial=False
            )
        else:
            collect_num = [i for i, c in enumerate(collections) if c['name'] == selected_collection][0]

            collection_id = db.add_collection(
                date_time=collect_date,
                person=collect_person,
                name=selected_collection,
                street_address=collections[collect_num]['street_address'],
                town=collections[collect_num]['town'],
                phone_number=collections[collect_num]['phone_number'],
                url=collections[collect_num]['url'],
                notes=notes,
                is_commercial=True
            )

    if collection_id is None:
        st.error("Error adding collection. Fish not added.")
        st.stop()

    new_fish_df['number_in_group'] = new_fish_df['number_in_group'].fillna(1).astype(int)   
    new_fish_df['collection'] = collection_id

    new_fish_df['species'] = new_fish_df['species'].map(species_options)

    # validate fish
    cur_fish = db.get_all_fish()
    cur_fish_ids = {f1['id'] for f1 in cur_fish}
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

if st.button("Done and Logout"):
    auth.sign_out()
    st.rerun()
