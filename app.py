import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Fish Database",
    page_icon="🐠",
    layout="wide"
)

# Database file path
DB_FILE = "fish.db"

@st.cache_resource
def get_connection():
    """Create and cache database connection"""
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        return conn
    except sqlite3.Error as e:
        st.error(f"Error connecting to database: {e}")
        return None

def get_tables(conn):
    """Get list of tables in the database"""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        return tables
    except sqlite3.Error as e:
        st.error(f"Error listing tables: {e}")
        return []

def get_table_data(conn, table_name):
    """Get data from a table"""
    try:
        query = f"SELECT * FROM {table_name}"
        df = pd.read_sql_query(query, conn)
        return df
    except sqlite3.Error as e:
        st.error(f"Error reading table: {e}")
        return None

def get_table_schema(conn, table_name):
    """Get schema information for a table"""
    try:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        schema = cursor.fetchall()
        schema_df = pd.DataFrame(
            schema,
            columns=['cid', 'name', 'type', 'notnull', 'dflt_value', 'pk']
        )
        return schema_df
    except sqlite3.Error as e:
        st.error(f"Error getting schema: {e}")
        return None

def get_people_names(conn):
    """Get list of names from People table"""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT Name FROM People ORDER BY Name")
        names = [row[0] for row in cursor.fetchall()]
        return names
    except sqlite3.Error as e:
        st.error(f"Error getting people names: {e}")
        return []

def get_fish_ids(conn):
    """Get list of IDs from Fish table"""
    try:
        cursor = conn.cursor()
        cursor.execute("""SELECT ID FROM Fish  
                            ORDER BY ID""")
                            # Status IS NOT NULL 
                            # AND LOWER(Status) != 'dead'
        ids = [row[0] for row in cursor.fetchall()]
        return ids
    except sqlite3.Error as e:
        st.error(f"Error getting fish IDs: {e}")
        return []

def get_fish_with_details(conn):
    """Get fish with their tank and level information"""
    try:
        query = """
        SELECT 
            f.ID,
            f.Tank,
            t.Level
        FROM Fish f
        LEFT JOIN Tanks t ON f.Tank = t.Name
        ORDER BY f.ID
        """
        cursor = conn.cursor()
        cursor.execute(query)
        fish_data = cursor.fetchall()
        return fish_data
    except sqlite3.Error as e:
        st.error(f"Error getting fish details: {e}")
        return []

def log_check(conn, date_time, person, fish_id, fed, ate, notes):
    """Log a fish check to the database"""
    try:
        cursor = conn.cursor()
        # Assuming a FishChecks table exists 
        
        fed = 1 if fed else 0
        ate = 1 if ate else 0

        cursor.execute("""
            INSERT INTO FishChecks (Date, By, Fish, Fed, Ate, Notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (date_time, person, fish_id, fed, ate, notes))
        
        conn.commit()
        return True
    except sqlite3.Error as e:
        st.error(f"Error logging check: {e}")
        return False

def main():
    st.title("🐠 Fish Database Browser")
    st.markdown(f"**Database:** `{DB_FILE}`")
    
    # Check if database exists
    if not Path(DB_FILE).exists():
        st.error(f"Database file '{DB_FILE}' not found!")
        st.info(f"Please make sure the '{DB_FILE}' file is in the same directory as this script.")
        return
    
    # Get database connection
    conn = get_connection()
    if conn is None:
        return
    
    # Sidebar
    with st.sidebar:
        st.header("Tables")
        
        # Refresh button
        if st.button("🔄 Refresh Tables", width='stretch'):
            st.cache_resource.clear()
            st.rerun()
        
        st.divider()
        
        # Get and display tables
        tables = get_tables(conn)
        
        if not tables:
            st.warning("No tables found in database")
            return
                
        st.divider()
            
    # Main content area
    # Create tabs
    fishtab, checktab, logtab = st.tabs(["🐟 Fish View", "✅ Check Fish", "📒 Daily logs"])
    
    # Tab 1: Fish table View
    with fishtab:
        df = get_table_data(conn, "Fish")
        if df is not None:
            st.subheader("Fish")
            
            # Display dataframe with configuration
            st.dataframe(
                df,
                width='stretch',
                height=600
            )
            
            # Download button
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name="Fish.csv",
                mime="text/csv"
            )
    
    # Tab 1: Fish table View
    with logtab:
        df = get_table_data(conn, "FishChecks")
        if df is not None:
            st.subheader("Daily log")
            
            # Display dataframe with configuration
            st.dataframe(
                df,
                width='stretch',
                height=600
            )
            
            # Download button
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name="DailyLog.csv",
                mime="text/csv"
            )

    # Tab 4: Check Fish
    with checktab:
        st.subheader("✅ Check Fish")
        
        # Initialize session state for submitted fish
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
            people_names = get_people_names(conn)
            if people_names:
                selected_person = st.selectbox("Person", people_names)
            else:
                st.warning("No people found in People table")
                selected_person = None
        
        with col3:
            sort_by = st.selectbox("Sort by", ["Fish ID", "Tank", "Level"])
        
        st.divider()
        
        # Get fish with details
        fish_data = get_fish_with_details(conn)
        
        if not fish_data:
            st.warning("No fish found in Fish table")
        else:
            # Sort fish based on user selection
            if sort_by == "Tank":
                fish_data_sorted = sorted(fish_data, key=lambda x: (x[1] or "", x[0]))
            elif sort_by == "Level":
                fish_data_sorted = sorted(fish_data, key=lambda x: (x[2] or "", x[0]))
            else:  # Fish ID
                fish_data_sorted = sorted(fish_data, key=lambda x: x[0])
            
            st.write("**Fish Checks:**")
            
            for fish_id, tank, level in fish_data_sorted:
                is_submitted = fish_id in st.session_state.submitted_fish
                
                # Display fish info with tank and level
                info_text = f"**Fish ID: {fish_id}**"
                if tank:
                    info_text += f" | Tank: {tank}"
                if level:
                    info_text += f" | Level: {level}"
                st.write(info_text)
                
                col1, col2, col3 = st.columns([1, 3, 1])
                
                with col1:
                    fed = st.checkbox("Fed", key=f"fed_{fish_id}", disabled=is_submitted)
                
                with col2:
                    notes = st.text_input(
                        "Notes", 
                        key=f"notes_{fish_id}", 
                        label_visibility="collapsed", 
                        placeholder="Notes..." if not is_submitted else "Submitted",
                        disabled=is_submitted
                    )
                
                with col3:
                    if is_submitted:
                        st.button("✓ Logged", key=f"btn_{fish_id}", disabled=True, use_container_width=True)
                    else:
                        if st.button("Log", key=f"btn_{fish_id}", type="primary", use_container_width=True):
                            if selected_person:
                                if log_check(conn, check_date, selected_person, fish_id, fed, notes):
                                    st.session_state.submitted_fish.add(fish_id)
                                    st.success(f"✅ Logged check for Fish {fish_id}")
                                else:
                                    st.error(f"Failed to log check for Fish {fish_id}")
                            else:
                                st.error("Please select a person")
                
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

if __name__ == "__main__":
    main()