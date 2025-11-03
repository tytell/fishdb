import hashlib
from supabase import create_client, Client
import streamlit as st
from contextlib import contextmanager
import logging
from datetime import datetime, timedelta

from utils.settings import DB_FILE

logger = logging.getLogger(__name__)

@st.cache_resource
def get_supabase_client():
    """Get Supabase client connection"""
    db_url = st.secrets["DB_URL"]
    db_key = st.secrets["DB_KEY"]
    return create_client(db_url, db_key)

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

def stop_if_not_logged_in():
    # Check if user is logged in
    if 'logged_in' not in st.session_state or not st.session_state.logged_in:
        st.warning("⚠️ Please login first!")
        st.info("Use the sidebar to navigate back to the Login page.")
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

# Fish database functions
def get_all_fish(include_dead = False):
    """Get all fish with their tank and system information"""

    try:
        supabase = get_supabase_client()

        response = (
            supabase.table('Fish')
            .select(
                'id, species, tank, status, Tanks(system, shelf)'
            )
            .neq('status', 'Dead')
            .execute()
        )
        
        fish_list = flatten_dict_list(response.data)
        
        return fish_list
    except Exception as e:
        st.error(f"Database error in get_all_fish: {e}")
        return []

def get_all_tanks():
    """Get all available tanks"""

    try:
        supabase = get_supabase_client()

        response = (
            supabase.table('Tanks')
            .select('name')
            .order('name')
            .execute()
        )

        tanks = [t['name'] for t in response.data]
        return tanks
    except Exception as e:
        st.error(f"Database error in get_all_tanks: {e}")
        return []

def get_all_systems():
    """Get all available systems"""

    try:
        supabase = get_supabase_client()

        response = (
            supabase.table('Systems')
            .select('name')
            .order('name')
            .execute()
        )

        systems = [s['name'] for s in response.data]
    except Exception as e:
        st.error(f"Database erro in get_all_systems: {e}")
        return []

    shortnames = dict()
    for sys1 in systems:
        if len(sys1) > 4:
            nm = sys1[:4]
        else:
            nm = sys1
    
        if nm in shortnames:
            nm = nm + '1'
        shortnames[nm] = sys1
    
    sysnames = {v: k for k,v in shortnames.items()}
    return sysnames

def get_all_people():
    """Get list of names from People table"""
    try:
        supabase = get_supabase_client()

        response = (
            supabase.table('People')
            .select('username', 'full_name')
            .order('full_name')
            .execute()
        )

        people = {p['username']: p['full_name'] for p in response.data}
        return people
    except Exception as e:
        st.error(f"Database error in get_all_people: {e}")
        return []

def log_water(date_time, person, system, conductivity, pH, ammonia, nitrate, nitrite, waterx, notes):
    """Log a water quality check to the database"""
    try:
        supabase = get_supabase_client()

        response = (
            supabase.table("WaterQuality")
            .insert({
                'date': date_time,
                'by': person,
                'system': system,
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

        response = (
            supabase.table("Feeding")
            .insert({
                'date': date_time,
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


def log_new_health_status(date_time, person, fish_id, status, notes):
    """Log a change in fish health to the database"""

    try:
        supabase = get_supabase_client()

        response = (
            supabase.table("Health")
            .insert({
                'date': date_time,
                'by': person,
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


def move_fish_to_tank(date_time, person, fish_id, new_tank, new_status, notes):
    """Move a fish to a different tank"""

    try:
        supabase = get_supabase_client()

        response = (
            supabase.table("Fish")
            .select('tank')
            .eq('id', fish_id)
        )

        ins = {
            'date': date_time,
            'by': person,
            'fish': fish_id,
            'from_tank': response.data['tank'],
            'to_tank': new_tank,
            'notes': notes
        }

        upd = {
            'tank': new_tank
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
