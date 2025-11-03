import hashlib
import sqlite3
import streamlit as st
from contextlib import contextmanager
import logging
from datetime import datetime, timedelta

from utils.settings import DB_FILE

logger = logging.getLogger(__name__)

@contextmanager
def get_db_connection():
    """Context manager for SQLite database connection."""
    conn = sqlite3.connect(DB_FILE)
    try:
        yield conn
    finally:
        conn.close()

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_login(username, password):
    """Verify username and password against database"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Hash the input password
            hashed_password = hash_password(password)
            
            # Query the database
            cursor.execute(
                "SELECT * FROM People WHERE Username = ? AND Password = ?",
                (username, hashed_password)
            )
            
            result = cursor.fetchone()
            
            return result is not None
    except sqlite3.Error as e:
        st.error(f"Database error: {e}")
        return False

def stop_if_not_logged_in():
    # Check if user is logged in
    if 'logged_in' not in st.session_state or not st.session_state.logged_in:
        st.warning("⚠️ Please login first!")
        st.info("Use the sidebar to navigate back to the Login page.")
        st.stop()

# Fish database functions
def get_all_fish(include_dead = False):
    """Get all fish with their tank and system information"""

    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = '''
            SELECT 
                f.ID,
                f.Species,
                f.Tank,
                f.Status,
                t.System,
                t.Shelf
            FROM Fish f
            LEFT JOIN Tanks t ON f.Tank = t.Name
        '''

        if not include_dead:
            query += '''
                WHERE Status <> 'Dead'
            '''

        query += '''
            ORDER BY f.Tank, f.ID
        '''

        cursor.execute(query)
        
        fish = cursor.fetchall()
        conn.close()
        return fish

def get_all_tanks():
    """Get all available tanks"""

    with get_db_connection() as conn:    
        cursor = conn.cursor()
        cursor.execute('SELECT Name FROM Tanks ORDER BY Name')
        tanks = [row[0] for row in cursor.fetchall()]
        return tanks

def get_all_systems():
    """Get all available systems"""

    with get_db_connection() as conn:    
        cursor = conn.cursor()
        cursor.execute('''
                        SELECT 
                            Name
                        FROM Systems
                        WHERE Active = 1
                        ORDER BY Name
                    ''')
        systems = [row[0] for row in cursor.fetchall()]

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

def get_last_water_quality(system, last=7):
    cutoff_date = datetime.now() - timedelta(days=last)
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            conn.row_factory = sqlite3.Row

            cursor.execute("""
                    SELECT * From WaterQuality
                    WHERE Date >= ? AND System = ?
                    ORDER BY Date DESC
            """, (cutoff_date, system))

            water_quality = cursor.fetchall()

            if len(water_quality) > 0:
                return water_quality[0]
            else:
                return []
    except sqlite3.Error as e:
        st.error(f"Error getting water quality: {e}")
        return []

def log_water(date_time, person, system, conductivity, pH, ammonia, nitrate, nitrite, waterx, notes):
    """Log a water quality check to the database"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('PRAGMA foreign_keys = ON')
            
            cursor.execute("""
                INSERT INTO WaterQuality (
                           Date, 
                           Person, 
                           System, 
                           Conductivity, 
                           pH, 
                           Ammonia,
                           Nitrate, 
                           Nitrite, 
                           WaterChangePct, 
                           Notes
                           )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (date_time, person, system, conductivity, pH, ammonia, nitrate, nitrite, waterx, notes))
            
            conn.commit()
            return True
    except sqlite3.Error as e:
        st.error(f"Error logging check: {e}")
        return False
    
def get_all_people():
    """Get list of names from People table"""
    try:
        with get_db_connection() as conn:    
            cursor = conn.cursor()
            cursor.execute("""
                    SELECT 
                        Username,
                        Name
                    FROM People 
                    WHERE Active = 1
                    ORDER BY Username
            """)
            names = {row[0]: row[1] for row in cursor.fetchall()}
            return names
    except sqlite3.Error as e:
        st.error(f"Error getting people names: {e}")
        return []

def log_check(date_time, person, fish_id, fed, ate, notes):
    """Log a fish check to the database"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('PRAGMA foreign_keys = ON')
            
            fed = 1 if fed else 0
            ate = 1 if ate else 0

            cursor.execute("""
                INSERT INTO Feeding (Date, Person, Fish, Fed, Ate, Notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (date_time, person, fish_id, fed, ate, notes))
            
            conn.commit()
            return True
    except sqlite3.Error as e:
        st.error(f"Error logging check: {e}")
        return False

def log_new_health_status(date_time, person, fish_id, status, notes):
    """Log a change in fish health to the database"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('PRAGMA foreign_keys = ON')
            
            cursor.execute("""
                INSERT INTO Health (Date, Person, Fish, ChangeStatus, Notes)
                VALUES (?, ?, ?, ?, ?)
            """, (date_time, person, fish_id, status, notes))

            cursor.execute('UPDATE Fish SET Status = ? WHERE ID = ?', (status, fish_id))

            conn.commit()
            return True
    except sqlite3.Error as e:
        st.error(f"Error logging check: {e}")
        return False


def move_fish_to_tank(fish_id, new_tank):
    """Move a fish to a different tank"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('PRAGMA foreign_keys = ON')
            cursor.execute('UPDATE Fish SET Tank = ? WHERE ID = ?', (new_tank, fish_id))
            conn.commit()
            conn.close()
            return True
    except sqlite3.Error as e:
        st.error(f"Database error: {e}")
        return False
