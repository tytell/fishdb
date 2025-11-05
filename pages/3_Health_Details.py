import streamlit as st
from datetime import datetime
import logging
from copy import copy

from utils.settings import health_statuses, health_status_colors
import utils.dbfunctions as db
from utils.formatting import apply_custom_css

logger = logging.getLogger('FishDB')

# Page configuration
st.set_page_config(page_title="Fish Health", page_icon="💊", layout="wide")

db.stop_if_not_logged_in()

apply_custom_css()

st.title("💊 Fish Health Details")
st.subheader(f"Logged in as: {st.session_state.full_name}")

# Load fish data
fish_df = db.get_fish_with_health()

if fish_df.empty:
    st.warning("No fish found in the database.")
    st.stop()

# Create fish selection dropdown
fish_options = fish_df.apply(
    lambda row: f"{row['id']} ({row['species']}): {row['status']}", 
    axis=1
).tolist()

fish_ids = fish_df['id'].tolist()

# Top row with Date and Person
col1, col2 = st.columns(2, gap='small')

with col1:
    check_date = st.text_input(
        "Date",
        value=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

with col2:
    people = db.get_all_people()
    if st.session_state.full_name in people:
        default_name_ind = list(people).index(st.session_state.full_name)
    else:
        default_name_ind = 0
        logger.warning(f'Username {st.session_state.full_name} not found in database')

    if people:
        selected_person = st.selectbox("Person", people,
                                    index = default_name_ind)
    else:
        st.warning("No people found in People table")
        selected_person = None

st.divider()

# Fish selection
st.subheader("Select Fish")
selected_fish_idx = st.selectbox(
    "Fish (ordered by health status)",
    range(len(fish_options)),
    format_func=lambda x: fish_options[x],
    key="fish_selector"
)

if selected_fish_idx is not None:
    selected_fish_id = fish_ids[selected_fish_idx]
    selected_fish = fish_df.iloc[selected_fish_idx]
    
    # Display fish details
    st.divider()
    
    col1, col2, col3 = st.columns(3, gap="small")
    
    with col1:
        st.metric("Fish ID", selected_fish['id'])
    with col2:
        st.metric("Species", selected_fish['species'])
    with col3:
        status_color = {
            'Diseased': '🔴',
            'Monitor': '🟡',
            'Healthy': '🟢'
        }.get(selected_fish['status'], '⚪')
        st.metric("Status", f"{status_color} {selected_fish['status']}")
    
    st.divider()
    
    # Health notes section
    st.subheader("📝 Recent Health Notes")
    
    # Date range selector
    date_range_options = {
        "Last 7 days": 7,
        "Last 14 days (default)": 14,
        "Last 30 days": 30,
        "Last 60 days": 60,
        "Last 90 days": 90
    }
    
    selected_range = st.selectbox(
        "Select date range",
        list(date_range_options.keys()),
        index=1  # Default to 14 days
    )
    
    days_back = date_range_options[selected_range]
    
    # Fetch and display health notes
    health_notes_df = db.get_fish_health_notes(selected_fish_id, days_back)
    
    if not health_notes_df.empty:
        st.success(f"Found {len(health_notes_df)} health record(s)")
        
        # Display each health note as a card
        for _, note in health_notes_df.iterrows():
            with st.container():
                note_date = datetime.fromisoformat(note['date'].replace('Z', '+00:00'))
                
                # Create columns for the note header
                note_cols = st.columns([3, 2, 2], gap="small")
                
                with note_cols[0]:
                    st.markdown(f"**📅 {note_date.strftime('%Y-%m-%d %H:%M')}**")
                with note_cols[1]:
                    event_type = note['event_type']

                    event_emoji = {
                        'Tank Move': '🏠',
                        'Treatment Start': '💊',
                        'Treatment End': '✅',
                        'Observation': '👁️',
                        'Other': '📌'
                    }.get(event_type, '📌')

                    st.markdown(f"{event_emoji} **{event_type}**")
                with note_cols[2]:
                    st.markdown(f"*By: {note.get('by', 'Unknown')}*")
                
                # Display event-specific details
                if note['from_tank'] and note['to_tank']:
                    st.markdown(f"🏠 Moved from {note['tank_name']} to {note['to_tank']}")
                
                if note['treatment']:
                    st.markdown(f"💊 **Treatment:** {note['treatment']}")
                
                if note['change_status']:
                    st.markdown(f"👁️ **New status:** {note['change_status']}")
                    
                if note['notes']:
                    st.markdown(f"**Notes:** {note['notes']}")
                
                st.markdown("---")
    else:
        st.info(f"No health records found for the selected date range ({selected_range})")
    
    st.divider()
    
    # Log new health event section
    st.subheader("➕ Log New Health Event")

    # Event type selection
    event_type = st.selectbox(
        "Event Type *",
        ["Observation", "Change Status", "Tank Move", "Treatment Start", "Treatment End", "Other"],
        help="Select the type of health event"
    )  
    
    with st.form("health_event_form", clear_on_submit=True):
        # Conditional fields based on event type
        tank_name = None
        treatment_details = None
        cur_tank = None
        new_tank = None
        new_status = None

        if event_type == "Tank Move":
            all_tanks = db.get_all_tanks()
            cur_tank = selected_fish["tank"]
            other_tanks = copy(all_tanks)
            other_tanks.remove(cur_tank)
            other_tanks.append("New tank")

            new_tank = st.selectbox(
                "New Tank *",
                other_tanks,
                help="Choose the new tank"
            )

            if new_tank == "New tank":
                systems = db.get_all_systems()

                new_tank = st.text_input("Tank name")
                tank_vol = st.number_input("Volume",
                                           help="Tank volume in L")
                is_hospital = st.checkbox("Hospital tank", value=True)
                if is_hospital:
                    system = new_tank
                    shelf = None
                else:
                    system = st.selectbox("Tank system",
                                          systems)
                    shelf = st.number_input("Shelf")
                
                db.add_tank(new_tank, tank_vol, is_hospital, system, shelf)
                
        if event_type in ["Treatment Start", "Treatment End"]:
            treatment_details = st.text_area(
                "Treatment Details *",
                placeholder="e.g., Melafix, Pimafix, Antibiotic: Doxycyclin 200mg/L, Duration: 5 days",
                help="Describe the treatment, medication, dosage, and duration",
                height=100
            )
        
        if event_type == "Change Status":
            new_status = st.selectbox("Health status", 
                                      health_statuses.keys())
            
        # Notes field (always visible)
        notes = st.text_area(
            "Observations and Notes *",
            placeholder="Enter detailed observations about the fish's condition, behavior, appearance, etc.",
            help="Be as detailed as possible - include symptoms, behavior changes, feeding patterns, etc.",
            height=150,
            key="health_notes_input"
        )
        
        # Submit button
        col1, col2, col3 = st.columns([2, 1, 1], gap="small")
        
        with col1:
            submit_button = st.form_submit_button(
                "📊 Log Health Event",
                use_container_width=True,
                type="primary"
            )
        
        with col2:
            clear_button = st.form_submit_button(
                "🗑️ Clear",
                use_container_width=True
            )
        
        if submit_button:
            # Validation
            errors = []
            
            if not notes.strip():
                errors.append("Notes are required")
            
            if event_type == "New Status" and not new_status:
                errors.append("Please select a status")

            if event_type == "Tank Move" and not tank_name:
                errors.append("Tank name is required for tank moves")
            
            if event_type in ["Treatment Start", "Treatment End"] and not treatment_details:
                errors.append("Treatment details are required for treatment events")
            
            if errors:
                for error in errors:
                    st.error(f"❌ {error}")
            else:
                # Log the event
                success = db.log_health_event(date=check_date,
                                              person=selected_person,
                    fish_id=selected_fish_id,
                    event_type=event_type,
                    to_tank=new_tank,
                    from_tank=cur_tank,
                    treatment=treatment_details,
                    notes=notes,
                )
                
                if success:
                    st.balloons()
                    st.rerun()
        
        if clear_button:
            st.rerun()