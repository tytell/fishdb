import hashlib
from supabase import create_client, Client
import streamlit as st
import pandas as pd
import logging
from datetime import datetime, timedelta
import re
from copy import copy

from utils.auth import get_supabase_client

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_login(username, password):
    """Verify username and password against database"""
    try:
        supabase = get_supabase_client()
        hashed_password = hash_password(password)

        # Query the database
        response = supabase.table('People').select('*').eq('username', username).eq('password', hashed_password).execute()

        return len(response.data) > 0
    except Exception as e:
        st.error(f"Database error: {e}")
        return False

def stop_if_not_logged_in(min_access = 0):
    # Check if user is logged in
    if 'user' not in st.session_state or st.session_state.user is None:
        st.warning("⚠️ Please login first!")
        st.info("Use the sidebar to navigate back to the Login page.")
        st.stop()
    else:
        people = get_all_people()
        access = [p1['access'] for p1 in people if p1['full_name'] == st.session_state.full_name]
        if len(access) != 1:
            st.error("Weirdness")
            st.stop()
        elif access[0] < min_access:
            st.warning("⚠️ You do not have a high enough access level for this page")
            st.stop()

def flatten_dict_list(d):
    F = []
    for f in d:
        f1 = {}
        for k,v in f.items():
            if isinstance(v, dict):
                for k2,v2 in v.items():
                    f1.update({k2: v2})
            else:
                f1.update({k: v})
        F.append(f1)

    return F

# Define status priority for ordering
health_status_order = {
    'Sick': 1,
    'Monitor': 2,
    'Healthy': 3
}

# List all of the tables in the database
def get_all_table_names():
    # it turns out supabase doesn't have an API to list tables...

    table_names = ['Collections',
                   'Experiments',
                   'Fish',
                   'Feeding',
                   'Groups',
                   'Health',
                   'Locations',
                   'Maintenance',
                   'People',
                   'Species',
                   'Systems',
                   'Tanks',
                   'WaterQuality']
    return table_names
    
# Fish database functions
def get_all_fish(include_dead = False,
                 only_groups = False,
                 include_system_details = True,
                 return_df = False):
    """Get all fish with their tank and system information"""

    try:
        supabase = get_supabase_client()

        if include_system_details:
            sel = '*, Tanks(system, shelf, position_in_shelf)'
        else:
            sel = '*'

        query = (
            supabase.table('Fish')
            .select(sel)
        )

        if not include_dead:
            query = query.neq('status', 'Dead')
        
        if only_groups:
            # this doesn't work, and I don't know why
            # query = query.not_('number_in_group', 'is', 'null')
            # but this one is OK, so it doesn't matter
            query = query.gt('number_in_group', 1)
        
        response = query.execute()
        
        fish_list = flatten_dict_list(response.data)

    except Exception as e:
        st.error(f"Database error in get_all_fish: {e}")
        fish_list = []

    if return_df:
        fish_list = pd.DataFrame(fish_list)
        # Add sort key based on status priority
        fish_list['sort_key'] = fish_list['status'].map(health_status_order).fillna(999)
        fish_list = fish_list.sort_values(['sort_key', 'id'])

    return fish_list

def check_fish_in_same_tank():
    """Get any fish that are in the same tank as another fish.
    Fish with distinct IDs should not be in the same tank."""
    
    try:
        supabase = get_supabase_client()

        response = (
            supabase.table('Fish')
            .select('id, tank', count='exact')
            .neq('tank', None)
            .execute()
        )
        logger.debug(f"{response.data=}")

        tank_fish = {}
        for d1 in response.data:
            t1 = d1['tank']
            if t1 in tank_fish:
                tank_fish[t1].append(d1['id'])
            else:
                tank_fish[t1] = [d1['id']]

        logger.debug(f"{tank_fish=}")

        tanks_with_multiple_fish = {}
        for t1, fish_list in tank_fish.items():
            if len(fish_list) > 1:
                tanks_with_multiple_fish[t1] = fish_list
        logger.debug(f"{tanks_with_multiple_fish=}")

        return tanks_with_multiple_fish

    except Exception as e:
        st.error(f"Database error in check_fish_in_same_tank: {e}")
        return dict()


def get_fish_health_notes(fish_id, days_back=14):
    """Get health notes for a specific fish from the last N days"""
    try:
        cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()

        logger.debug('in get_fish_health_notes')

        supabase = get_supabase_client()
        response = (
            supabase.table('Health')
            .select('*')
            .eq('fish', fish_id)
            .gte('date', cutoff_date)
            .order('date', desc=True)
            .execute()
        )

        if response.data:
            return pd.DataFrame(response.data)
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching health notes: {str(e)}")
        return pd.DataFrame()

def get_all_tanks(return_df = False,
                  include_system_details = False,
                  only_active = False):
    """Get all available tanks"""

    try:
        supabase = get_supabase_client()

        if include_system_details:
            sel = '*, Systems(name)'
        else:
            sel = '*'

        query = (
            supabase.table('Tanks')
            .select(sel)
        )

        if only_active:
            query = query.eq('active', True)
        
        query = query.order('name')
        response = query.execute()

        ret = response.data
    except Exception as e:
        st.error(f"Database error in get_all_tanks: {e}")
        ret = []

    if return_df:
        ret = pd.DataFrame(ret)
    return ret

def get_tanks_without_fish(return_df = False):
    """Get all tanks that do not currently have fish assigned to them"""

    try:
        supabase = get_supabase_client()

        # Subquery to get tank names with fish
        tanks = (
            supabase.table('Fish')
            .select('tank', count='exact')
            .neq('tank', None)
            .execute()
        )

        tanks = [t1['tank'] for t1 in tanks.data]

        # tankstr = ','.join(tanks)
        # tankstr = '(' + tankstr + ')'

        response = (
            supabase.table('Tanks')
            .select('*')
            # not clear why we can't filter this way
            # .not_.in_('name', tankstr)
            .order('name')
            .execute()
        )

        tanks_without_fish = [t1 for t1 in response.data if t1['name'] not in tanks]            

        ret = tanks_without_fish
    except Exception as e:
        st.error(f"Database error in get_tanks_without_fish: {e}")
        ret = []

    if return_df:
        ret = pd.DataFrame(ret)
    return ret

def get_all_from_table(table_name, order_by=None,
                       return_df = False):
    try:
        supabase = get_supabase_client()

        response = (
            supabase.table(table_name)
            .select('*')
        )
        if order_by:
            response = response.order(order_by)
        
        ret = response.execute()
        ret = ret.data
        
    except Exception as e:
        st.error(f"Database error in get_all_from_table: {e}")
        ret = []

    if return_df:
        ret = pd.DataFrame(ret)
    return ret    

def get_all_systems(return_df = False):
    """Get all available systems"""

    systems = get_all_from_table('Systems', return_df=False)
    
    # add a shortname that we can use as a key for the check water page
    shortnames = set()
    for sys1 in systems:
        shortname1 = re.sub(r'\W|^(?=\d)', '_', sys1['name'][:5])
        if shortname1 in shortnames:
            shortname1 = shortname1 + '1'
            shortnames.add(shortname1)
        sys1['short_name'] = shortname1
    
    if return_df:
        return pd.DataFrame(systems)
    else:
        return systems
    
def get_all_people(return_df = False):
    """Get list of names from People table"""

    return get_all_from_table('People', order_by='full_name',
                              return_df=return_df)

def get_all_species(return_df = False):
    """Get all available species"""

    return get_all_from_table('Species', order_by='name',
                              return_df=return_df)

def get_all_collections(return_df = False):
    """Get all collections"""

    return get_all_from_table('Collections', order_by='name',
                              return_df=return_df)

def get_all_experiments(return_df = False):
    """Get all experiments"""

    return get_all_from_table('Experiments', order_by='date',
                              return_df=return_df)

def add_tanks(new_tanks_df):
    """Add several new tanks, stored in a Pandas dataframe"""

    supabase = get_supabase_client()

    changes_made = False
    errors = []
    for idx, row in new_tanks_df.iterrows():
        try:
            insert_data = row.to_dict()
            
            # Convert NaN to None
            insert_data = {k: (None if pd.isna(v) else v) for k, v in insert_data.items()}

            response = supabase.table('Tanks').insert(insert_data).execute()
            if response.data:
                changes_made = True
        except Exception as e:
            errors.append(f"Error inserting new row (name = {row['name']}): {str(e)}")
    
    return changes_made, errors

def update_tanks(updated_tanks_df):
    """Update several tanks, stored in a Pandas dataframe"""

    supabase = get_supabase_client()

    cur_tanks_df = get_all_tanks(return_df=True)
    assert cur_tanks_df.shape[0] == updated_tanks_df.shape[0], \
        "Updated tanks should have the same number of rows as current tanks"

    common_cols = [col for col in cur_tanks_df.columns if col in updated_tanks_df.columns]

    errors = []
    changes_made = False
    for idx in updated_tanks_df.index:
        if idx in cur_tanks_df.index:
            row_id = updated_tanks_df.loc[idx, 'name']
            original_row = cur_tanks_df.loc[idx, common_cols]
            edited_row = updated_tanks_df.loc[idx, common_cols]
            
            # Check if row has changed
            if not original_row.equals(edited_row):
                try:
                    # Prepare update data (exclude id and timestamp columns)
                    update_data = edited_row.to_dict()
                    exclude_cols = ['name']
                    update_data = {k: v for k, v in update_data.items() if k not in exclude_cols}
                    
                    # Convert NaN to None
                    update_data = {k: (None if pd.isna(v) else v) for k, v in update_data.items()}
                    
                    response = (
                        supabase.table('Tanks')
                        .update(update_data)
                        .eq('name', row_id)
                        .execute()
                    )
                    if response.data:
                        changes_made = True
                except Exception as e:
                    errors.append(f"Error updating row {row_id}: {str(e)}")

    return changes_made, errors

def add_tank(tank_name, tank_vol, is_hospital, system, shelf=None):
    """Add a new tank"""

    try:
        supabase = get_supabase_client()

        # hospital tanks aren't in a system
        if is_hospital:
            system = None

        response = (
            supabase.table("Tanks")
            .insert({
                'name': tank_name,
                'volume': tank_vol,
                'system': system,
                'shelf': shelf
            })
            .execute()
        )
        return True

    except Exception as e:
        st.error(f"Database error in add_tank: {e}")
        return False

def add_fish(new_fish_df):
    """Add several new fish, stored in a Pandas dataframe"""

    supabase = get_supabase_client()

    changes_made = False
    errors = []
    for idx, row in new_fish_df.iterrows():
        try:
            insert_data = row.to_dict()
            
            insert_data = {k: (None if pd.isna(v) else v) for k, v in insert_data.items()}
            
            response = supabase.table('Fish').insert(insert_data).execute()
            if response.data:
                changes_made = True
        except Exception as e:
            errors.append(f"Error inserting new row (name = {row['id']}): {str(e)}")
    
    return changes_made, errors

def add_collection(date_time, person, name, latitude=None, longitude=None, 
                   street_address=None, town=None, water_body=None,
                   phone_number=None, url=None, is_commercial=None,
                         sampling_gear=None, seine_length=None, number_of_tries=None,
                         water_temp=None, water_conductivity=None, water_pH=None, water_flow_speed=None,
                         notes=None):
    """Log a new collection event to the database"""
    try:
        supabase = get_supabase_client()

        date_time_str = date_time.strftime('%Y-%m-%d %H:%M:%S')
        response = (
            supabase.table("Collections")
            .insert({
                'date': date_time_str,
                'by': person,
                'name': name,
                'street_address': street_address,
                'town': town,
                'water_body': water_body,
                'phone_number': phone_number,
                'url': url,
                'latitude': latitude,
                'longitude': longitude,
                'sampling_gear': sampling_gear,
                'seine_length': seine_length,
                'number_of_tries': number_of_tries,
                'water_temp': water_temp,
                'water_conductivity': water_conductivity,
                'water_ph': water_pH,
                'water_flow_speed': water_flow_speed,
                'notes': notes,
                'is_commercial': is_commercial
            })
            .execute()
        )

        return response.data[0]['id']
    except Exception as e:
        st.error(f"Database error: {e}")
        return None

def log_maintenance(date_time, person, task, system, notes):
    """Log a maintenance task to the database"""
    try:
        supabase = get_supabase_client()

        date_time_str = date_time.strftime('%Y-%m-%d %H:%M:%S')
        if system == "":
            system = None
        response = (
            supabase.table("Maintenance")
            .insert({
                'date': date_time_str,
                'by': person,
                'task': task,
                'system': system,
                'notes': notes
            })
            .execute()
        )

        return True
    except Exception as e:
        st.error(f"Database error: {e}")
        return False

def get_maintenance_logs(days_back=14):
    """Get maintenance logs from the last N days"""
    try:
        cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()

        logger.debug('in get_maintenance_logs')

        supabase = get_supabase_client()
        response = (
            supabase.table('Maintenance')
            .select('*')
            .gte('date', cutoff_date)
            .order('date', desc=True)
            .execute()
        )

        if response.data:
            return pd.DataFrame(response.data)
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching maintenance logs: {str(e)}")
        return pd.DataFrame()
        
def log_water(date_time, person, system, conductivity, pH, ammonia, nitrate, nitrite, waterx, notes, tank=None):
    """Log a water quality check to the database"""
    try:
        supabase = get_supabase_client()

        date_time_str = date_time.strftime('%Y-%m-%d %H:%M:%S')
        response = (
            supabase.table("WaterQuality")
            .insert({
                'date': date_time_str,
                'by': person,
                'system': system,
                'tank': tank,
                'conductivity': conductivity,
                'ph': pH,
                'ammonia': ammonia,
                'nitrate': nitrate,
                'nitrite': nitrite,
                'water_change_pct': waterx,
                'notes': notes
            })
            .execute()
        )

        return True
    except Exception as e:
        st.error(f"Database error: {e}")
        return False

def log_check(date_time, person, fish_id, fed, ate, notes):
    """Log a fish check to the database"""

    try:
        supabase = get_supabase_client()

        date_time_str = date_time.strftime('%Y-%m-%d %H:%M:%S')

        response = (
            supabase.table("Feeding")
            .insert({
                'date': date_time_str,
                'by': person,
                'fish': fish_id,
                'fed': fed,
                'ate': ate,
                'notes': notes
            })
            .execute()
        )
        return True

    except Exception as e:
        st.error(f"Database error: {e}")
        return False

def log_health_event(date_time, person, fish_id, event_type, notes,
                     new_status=None,
                     from_tank=None, to_tank=None,
                     treatment=None,
                     death_status=None):
    """Log a new health event to the database"""

    try:
        supabase = get_supabase_client()

        date_time_str = date_time.strftime('%Y-%m-%d %H:%M:%S')

        response = (
            supabase.table("Health")
            .insert({
                'date': date_time_str,
                'by': person,
                'fish': fish_id,
                'event_type': event_type,
                'notes': notes,
                'change_status': new_status,
                'from_tank': from_tank,
                'to_tank': to_tank,
                'treatment': treatment,
                'death_status': death_status
            })
            .execute()
        )

        upd = {}
        if death_status is not None:
            upd = {'status': 'Dead',
                   'number_in_group': 0,
                    'tank': None}
        elif new_status is not None:
            upd = {'status': new_status}
        
        if upd:
            response = (
                supabase.table("Fish")
                .update({'status': new_status})
                .eq('id', fish_id)
                .execute()
            )

        return True

    except Exception as e:
        st.error(f"Database error: {e}")
        return False

def log_new_health_status(date_time, person, fish_id, status, notes):
    """Log a change in fish health to the database"""

    try:
        supabase = get_supabase_client()

        date_time_str = date_time.strftime('%Y-%m-%d %H:%M:%S')

        response = (
            supabase.table("Health")
            .insert({
                'date': date_time_str,
                'by': person,
                'event_type': 'Change Status',
                'fish': fish_id,
                'change_status': status,
                'notes': notes
            })
            .execute()
        )

        response = (
            supabase.table("Fish")
            .update({'status': status})
            .eq('id', fish_id)
            .execute()
        )
        return True

    except Exception as e:
        st.error(f"Database error: {e}")
        return False


def log_number_in_group(date_time, person, fish_id, num, notes,
                            event_type = "Recount", new_number=True):
    """Log a change in fish health to the database"""

    try:
        supabase = get_supabase_client()

        if not new_number:
            event_type = "Confirm Number"

        date_time_str = date_time.strftime('%Y-%m-%d %H:%M:%S')

        response = (
            supabase.table("Groups")
            .insert({
                'date': date_time_str,
                'by': person,
                'event_type': event_type,
                'original_group': fish_id,
                'number_in_group': num,
                'notes': notes
            })
            .execute()
        )

        response = (
            supabase.table("Fish")
            .update({'number_in_group': num})
            .eq('id', fish_id)
            .execute()
        )
        return True

    except Exception as e:
        st.error(f"Database error: {e}")
        return False

def split_group(group_id, new_group_df, person, date_time, notes=None):
    """Split a fish group into multiple groups"""

    errors = []
    try:
        supabase = get_supabase_client()

        date_time_str = date_time.strftime('%Y-%m-%d %H:%M:%S')
        new_group_df['number_in_group'] = new_group_df['number_in_group'].fillna(1).astype(int)
        new_group_df['collection'] = new_group_df['collection'].astype(int)

        for idx, row in new_group_df.iterrows():
            if row['id'] == group_id:
                response = (
                    supabase.table("Fish")
                    .update({'number_in_group': row['number_in_group']})
                    .eq('id', group_id)
                    .execute()
                )
            else:
                insert_data = row.to_dict()                
                insert_data = {k: (None if pd.isna(v) else v) for k, v in insert_data.items()}

                response = supabase.table('Fish').insert(insert_data).execute()

        date_time_str = date_time.strftime('%Y-%m-%d %H:%M:%S')

        new_group_ids = new_group_df['id'].tolist()
        insert_data = {
            'date': date_time_str,
            'by': person,
            'event_type': 'Split Group',
            'original_group': group_id,
            'notes': notes
        }
        for i, new_id in enumerate(new_group_ids):
            insert_data[f'group_{i+1}'] = new_id

        response = supabase.table('Groups').insert(insert_data).execute()
        if not response.data:
            errors.append(f"Failed to split group {group_id} into groups {', '.join(new_group_ids)}")
        
        if errors:
            return False, errors
        return True, []

    except Exception as e:
        errors.append(f"Database error: {e}")
        return False, errors

def merge_groups(original_group_ids, new_group_id, number_in_group, person, date_time, notes=None):
    """Merge multiple fish groups into a single group"""

    errors = []
    try:
        supabase = get_supabase_client()

        date_time_str = date_time.strftime('%Y-%m-%d %H:%M:%S')

        for group_id in original_group_ids:
            response = (
                supabase.table("Fish")
                .update({'number_in_group': 0})
                .eq('id', group_id)
                .execute()
            )

        insert_data = copy(response.data[0])
        insert_data['id'] = new_group_id
        insert_data['number_in_group'] = int(number_in_group)

        response = (
            supabase.table("Fish")
            .insert(insert_data)
            .execute()
        )

        insert_data = {
            'date': date_time_str,
            'by': person,
            'event_type': 'Merge Groups',
            'new_group': new_group_id,
            'notes': notes
        }
        for i, old_id in enumerate(original_group_ids):
            insert_data[f'group_{i+1}'] = old_id

        response = supabase.table('Groups').insert(insert_data).execute()
        if not response.data:
            errors.append(f"Failed to merge groups {', '.join(original_group_ids)} into group {new_group_id}")
        
        if errors:
            return False, errors
        return True, []

    except Exception as e:
        errors.append(f"Database error: {e}")
        return False, errors
        
def check_unique_fish_id(fish_id):
    """Check if a fish ID is unique in the database"""

    try:
        supabase = get_supabase_client()

        response = (
            supabase.table("Fish")
            .select('id')
            .eq('id', fish_id)
            .execute()
        )

        if response.data:
            return False
        return True

    except Exception as e:
        st.error(f"Database error: {e}")
        return False
    
def move_fish_to_tank(date_time, person, fish_id, to_tank, notes, 
                      new_status=None):
    """Move a fish to a different tank"""

    try:
        supabase = get_supabase_client()

        response = (
            supabase.table("Fish")
            .select('tank')
            .eq('id', fish_id)
            .execute()
        )

        if not response.data:
            st.error(f"Fish {fish_id} not in the database")
            return False
        
        cur_tank = response.data[0]['tank']

        date_time_str = date_time.strftime('%Y-%m-%d %H:%M:%S')

        ins = {
            'date': date_time_str,
            'by': person,
            'event_type': 'Tank Move',
            'fish': fish_id,
            'from_tank': cur_tank,
            'to_tank': to_tank,
            'notes': notes
        }

        upd = {
            'tank': to_tank
        }

        if new_status is not None:
            ins.update({'change_status': new_status})
            upd.update({'status': new_status})

        response = (
            supabase.table("Health")
            .insert(ins)
            .execute()
        )

        response = (
            supabase.table("Fish")
            .update(upd)
            .eq('id', fish_id)
            .execute()
        )
        return True

    except Exception as e:
        st.error(f"Database error: {e}")
        return False

def record_experiment(fish_id, project, project_description, experiment_description,
                      date, person, is_terminal, n_fish=1):
    """Record a new experiment"""

    try:
        supabase = get_supabase_client()

        date_str = date.strftime('%Y-%m-%d %H:%M:%S')

        response = (
            supabase.table("Experiments")
            .insert({
                'fish': fish_id,
                'project': project,
                'project_description': project_description,
                'experiment_description': experiment_description,
                'date': date_str,
                'by': person,
                'is_terminal': is_terminal,
                'n_fish': n_fish
            })
            .execute()
        )

        if is_terminal:
            response = (
                supabase.table("Fish")
                .select("*")
                .eq('id', fish_id)
                .execute()
            )

            if not response.data:
                st.error(f"Fish {fish_id} not found in database")
                return False
            
            fish_data = response.data[0]
            if fish_data['number_in_group'] is not None and fish_data['number_in_group'] > 1:
                new_number = fish_data['number_in_group'] - n_fish
                response = (
                    supabase.table("Fish")
                    .update({'number_in_group': new_number})
                    .eq('id', fish_id)
                    .execute()
                )
            else:
                response = (
                    supabase.table("Fish")
                    .update({'status': 'Dead',
                             'number_in_group': 0,
                            'tank': None})
                    .eq('id', fish_id)
                    .execute()
                )

        return True
    except Exception as e:
        st.error(f"Database error: {e}")
        return False