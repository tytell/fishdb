import streamlit as st
from datetime import datetime
import logging
from copy import copy

from utils.settings import health_statuses, health_status_colors
import utils.dbfunctions as db
from utils.formatting import apply_custom_css
from utils.date_person import date_person_input

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Page configuration
st.set_page_config(page_title="Fish Health", page_icon="💊", layout="wide")

db.stop_if_not_logged_in()

logger.debug('In Health Details page')

apply_custom_css()

def submit_health_event(log_text,
                        date, person, selected_fish_id, event_type, notes,
                        treatment_details=None, 
                        from_tank=None, to_tank=None,
                        death_status=None):    

    col1, col2 = st.columns([3, 1], gap="small")
    
    with col1:
        submit = st.form_submit_button(
            log_text,
            use_container_width=True,
            type="primary"
        )
    
    with col2:
        clear = st.form_submit_button("🗑️ Clear", use_container_width=True)

    if submit:
        errors = []

        if not notes.strip():
            errors.append("Notes are required")

        if event_type == "Treatment Start" or \
            event_type == "Treatment End":
            if not treatment_details.strip():
                errors.append("Treatment details are required")

        if event_type == "Death":
            if not death_status.strip():
                errors.append("Circumstance of death required")

        if errors:
            for error in errors:
                st.error(f"❌ {error}")
        else:
            success = db.log_health_event(
                date=date, person=person,
                fish_id=selected_fish_id,
                event_type=event_type,
                from_tank=from_tank,
                to_tank=to_tank,
                treatment=treatment_details,
                death_status=death_status,
                notes=notes
            )
            
            if success:
                st.balloons()
                st.rerun()

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
check_date, selected_person = date_person_input()

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
                    st.markdown(f"🏠 Moved from {note['from_tank']} to {note['to_tank']}")
                
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

    # Create tabs for each event type
    obs_tab, move_tab, treat_start_tab, treat_end_tab, death_tab, other_tab = st.tabs([
        "👁️ Observation",
        "🏠 Tank Move", 
        "💊 Treatment Start",
        "✅ Treatment End",
        "💀 Death",
        "📌 Other"
    ])
    
    # TAB 1: OBSERVATION
    with obs_tab:
        st.markdown("#### Daily Health Observation")
        st.info("Record routine health checks, behavior changes, and general observations")
        
        with st.form("observation_form", clear_on_submit=True):
            notes = st.text_area(
                "Observations and Notes *",
                placeholder="Describe the fish's appearance, behavior, feeding patterns, activity level, etc.",
                help="Be as detailed as possible - include symptoms, behavior changes, feeding patterns, etc.",
                height=200,
                key="observation_notes"
            )
            
            submit_health_event("👁️ Log Observation",
                                check_date, selected_person,
                                selected_fish_id, 'Observation', notes)

    # TAB 2: TANK MOVE
    with move_tab:
        st.markdown("#### Move Fish to Different Tank")
        st.info("Record tank transfers and automatically update the fish's current location")
        
        # Get list of existing tanks
        tanks = db.get_all_tanks()
        tank_names = [t1['name'] for t1 in tanks]
        cur_tank = selected_fish['tank']
        other_tanks = copy(tank_names)
        other_tanks.remove(cur_tank)

        # Create tank options list with "New Tank" option
        tank_options = other_tanks + ["➕ New Tank"]
                    
        selected_tank = st.selectbox(
            "Select Destination Tank *",
            tank_options,
            help="Select an existing tank or create a new one",
            key="tank_move_selector"
        )
        
        # If "New Tank" is selected, show new tank creation fields
        if selected_tank == "➕ New Tank":
            st.markdown("---")
            st.markdown("##### Create New Tank")

            systems = db.get_all_systems()
            
            col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 2, 1], gap="small")
            
            with col1:
                new_tank_name = st.text_input(
                    "New Tank Name *",
                    placeholder="e.g., M14, H3",
                    help="Enter a unique name for the new tank",
                    key="new_tank_name_input"
                )
            
            with col2:
                new_tank_volume = st.number_input(
                    "Volume (Liters) *",
                    min_value=0.0,
                    max_value=10000.0,
                    value=100.0,
                    step=10.0,
                    help="Tank capacity in liters",
                    key="new_tank_volume_input"
                )
            
            with col3:
                is_hospital = st.checkbox(
                    "🏥 Hospital tank",
                    value=True,
                    help="Check if this tank is used for quarantine or treatment",
                    key="new_tank_hospital_checkbox"
                )
            
            with col4:
                new_tank_system = st.selectbox("System", systems, help="Tank system if not a hospital tank",
                             key="new_tank_system",
                             disabled=is_hospital)
                
            with col5:
                new_tank_shelf = st.number_input("Shelf", min_value=1,
                                                 help="Shelf in system if not a hospital tank",
                                                 key="new_tank_shelf")
        else:
            new_tank_name = None
            new_tank_volume = None
            is_hospital = False
            new_tank_system = None

        st.markdown("---")
        
        with st.form("tank_move_form", clear_on_submit=True):
            notes = st.text_area(
                "Reason for Tank Move *",
                placeholder="Explain why the fish is being moved (e.g., overcrowding, illness, routine maintenance, quarantine)",
                help="Document the reason for this tank transfer",
                height=150,
                key="tank_move_notes"
            )

            # here we don't use the submit function because we also may need to
            # add a tank
            col1, col2 = st.columns([3, 1], gap="small")
            
            with col1:
                submit = st.form_submit_button(
                    "🏠 Move Fish to Tank",
                    use_container_width=True,
                    type="primary"
                )
            
            with col2:
                clear = st.form_submit_button("🗑️ Clear", use_container_width=True)
            
            if submit:
                errors = []

                if selected_tank == "➕ New Tank":
                    is_new_tank = True
                    if not new_tank_name or not new_tank_name.strip():
                        errors.append("New tank name is required")
                    if new_tank_volume is None or new_tank_volume <= 0:
                        errors.append("Tank volume must be greater than 0")

                else:
                     new_tank_name = selected_tank
                     is_new_tank = False
                     new_tank_shelf = None
                     new_tank_volume = None
                
                if errors:
                    for error in errors:
                        st.error(f"❌ {error}")
                else:                    
                    success = db.move_fish_to_tank(check_date, person=selected_person,
                                                   notes=notes,
                                        fish_id=selected_fish_id,
                                        is_new_tank=is_new_tank,
                                        to_tank=new_tank_name,
                                        system=new_tank_system,
                                        shelf=new_tank_shelf,
                                        new_tank_volume=new_tank_volume)
                             
                    if success:
                        st.balloons()
                        st.rerun()

               
    # TAB 3: TREATMENT START
    with treat_start_tab:
        st.markdown("#### Begin New Treatment")
        st.info("Record the start of medication or treatment protocol")
        
        with st.form("treatment_start_form", clear_on_submit=True):
            treatment_details = st.text_area(
                "Treatment Details *",
                placeholder="Example:\n• Medication: Erythromycin\n• Dosage: 200mg/L\n• Duration: 5 days\n• Administration: Water treatment\n• Target condition: Bacterial infection",
                help="Describe the treatment, medication, dosage, duration, and target condition",
                height=150,
                key="treatment_start_details"
            )
            
            notes = st.text_area(
                "Symptoms and Observations *",
                placeholder="Describe the symptoms that led to starting this treatment, current fish condition, etc.",
                help="Document why this treatment is being started",
                height=150,
                key="treatment_start_notes"
            )
            
            submit_health_event("💊 Start Treatment",
                                check_date, selected_person,
                                selected_fish_id, 'Start Treatment',
                                notes=notes, 
                                treatment_details=treatment_details)

    
    # TAB 4: TREATMENT END
    with treat_end_tab:
        st.markdown("#### Complete Treatment")
        st.info("Record the completion of a treatment protocol and document results")
        
        with st.form("treatment_end_form", clear_on_submit=True):
            treatment_details = st.text_area(
                "Treatment Summary *",
                placeholder="Example:\n• Medication: Erythromycin\n• Duration completed: 5 days\n• Total dosage administered: 200mg/L daily\n• Outcome: Successful",
                help="Summarize the treatment that was completed",
                height=150,
                key="treatment_end_details"
            )
            
            notes = st.text_area(
                "Treatment Results and Current Condition *",
                placeholder="Describe the treatment outcome, current fish condition, any remaining symptoms, follow-up actions needed, etc.",
                help="Document the results of this treatment",
                height=150,
                key="treatment_end_notes"
            )
            
            submit_health_event("✅ Complete Treatment", check_date, selected_person,
                                    selected_fish_id, 'End Treatment',
                                    notes=notes, 
                                    treatment_details=treatment_details)
    
    # TAB 5: DEATH
    with death_tab:
        st.markdown("#### Begin New Treatment")
        st.info("Describe the death of a fish")
        
        with st.form("death_form", clear_on_submit=True):
            death_status = st.selectbox('Circumstance',
                                        ["Found Dead", "Missing", "Euthanized"],
                                        key="death_status")
            
            notes = st.text_area(
                "Notes *",
                placeholder="Describe what happened",
                help="Document condition of fish if found dead or reason for euthanasia",
                height=150,
                key="death_notes"
            )


            submit_health_event("💀 Log Death",
                                check_date, selected_person,
                                selected_fish_id, 'Death',
                                notes=notes, 
                                death_status=death_status)

    # TAB 6: OTHER
    with other_tab:
        st.markdown("#### Other Health Event")
        st.info("Record any other health-related events that don't fit the above categories")
        
        with st.form("other_event_form", clear_on_submit=True):
            notes = st.text_area(
                "Detailed Notes *",
                placeholder="Provide detailed information about this event, actions taken, observations, etc.",
                help="Document this health event in detail",
                height=200,
                key="other_event_notes"
            )

            submit_health_event("📌 Log Other Event",
                                check_date, selected_person,
                                selected_fish_id, 'Other',
                                notes=notes)
