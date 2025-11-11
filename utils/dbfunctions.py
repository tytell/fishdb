import hashlib
from supabase import create_client, Client
import streamlit as st
import pandas as pd
import logging
from datetime import datetime, timedelta
import re

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
    'Diseased': 1,
    'Monitor': 2,
    'Healthy': 3
}

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
                  include_system_details = False):
    """Get all available tanks"""

    try:
        supabase = get_supabase_client()

        if include_system_details:
            sel = '*, Systems(name)'
        else:
            sel = '*'

        response = (
            supabase.table('Tanks')
            .select(sel)
            .order('name')
            .execute()
        )

        ret = response.data
    except Exception as e:
        st.error(f"Database error in get_all_tanks: {e}")
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

def get_all_locations(return_df = False):
    """Get all available species"""

    return get_all_from_table('Locations', order_by='name',
                              return_df=return_df)

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


def move_fish_to_tank(date_time, person, fish_id, to_tank, notes, 
                      is_new_tank=False,
                      new_tank_volume=None,
                      is_hospital=True, 
                      system=None, shelf=None, position_in_shelf=None,
                      new_status=None):
    """Move a fish to a different tank"""

    logger.debug("in move_fish_to_tank")

    try:
        supabase = get_supabase_client()

        response = (
            supabase.table("Fish")
            .select('tank')
            .eq('id', fish_id)
            .execute()
        )

        logger.debug(f"after select tank. {response=}")
        if not response.data:
            st.error(f"Fish {fish_id} not in the database")
            return False
        
        cur_tank = response.data[0]['tank']

        if is_new_tank:
            if is_hospital:
                system=None

            logger.debug('About to insert tank')
            response = (
                supabase.table("Tanks")
                .insert({
                    'name': to_tank,
                    'system': system,
                    'volume': float(new_tank_volume) if new_tank_volume else None,
                    'shelf': int(shelf) if shelf else None,
                    'position_in_shelf': int(position_in_shelf) if position_in_shelf else None
                })
                .execute()
            )
            logger.debug(f"after insert new tank. {response=}")

        logger.debug("Before ins")

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

        logger.debug(f"{ins=}")
        response = (
            supabase.table("Health")
            .insert(ins)
            .execute()
        )
        logger.debug(f"{response=}")

        logger.debug(f"{upd=}")
        response = (
            supabase.table("Fish")
            .update(upd)
            .eq('id', fish_id)
            .execute()
        )
        logger.debug(f"{response=}")
        return True

    except Exception as e:
        st.error(f"Database error: {e}")
        return False
