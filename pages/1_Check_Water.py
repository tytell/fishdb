import streamlit as st
from datetime import datetime
import logging

from utils.settings import health_statuses, health_status_colors
import utils.dbfunctions as db
from utils.formatting import apply_custom_css
from utils.date_person import date_person_input

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Page configuration
st.set_page_config(page_title="Check Water", page_icon="💧", layout="wide")

db.stop_if_not_logged_in()

apply_custom_css()

st.title("💧 Check Water")
st.subheader(f"Logged in as: {st.session_state.full_name}")

# Top row
check_date, selected_person = date_person_input()

# Load fish data
systems = db.get_all_systems()
tanks = db.get_all_tanks()
individual_tank_names = {t1['name']: t1['name'] for t1 in tanks if t1['system'] is None}

# add individual tanks to the list of systems
systems.update(individual_tank_names)

if not systems:
    st.warning("No tank systems found in the database.")
    st.stop()

if 'submitted_system' not in st.session_state:
    st.session_state.submitted_system = set()

st.divider()

st.write("**Water Checks:**")

for system, sysname in systems.items():
    is_submitted = sysname in st.session_state.submitted_system
    
    # Display fish info with tank and shelf
    info_text = f"**{system}**"
    st.write(info_text)
    
    condcol, pHcol, ammcol, nitritecol, nitratecol, waterxcol, notescol, logcol = \
        st.columns([1]*6 + [3, 1], gap='small')

    def number_col(name, key):
        return st.number_input(name, key=key,
                                      value=None,
                                      placeholder=name,
                                 label_visibility="collapsed",
                                 disabled=is_submitted)
    
    with condcol:
        coductivity = number_col("Conductivity", f"cond_{sysname}")
    
    with pHcol:
        pH = number_col("pH", f"pH_{sysname}")
    
    with ammcol:
        amm = number_col("Ammonia", f"amm_{sysname}")

    with nitratecol:
        nitrate = number_col("Nitrate", f"nitrate_{sysname}")

    with nitritecol:
        nitrite = number_col("Nitrite", f"nitrite_{sysname}")

    with waterxcol:
        waterx = number_col("Water Ex", f"waterx_{sysname}")
        
    with notescol:
        notes = st.text_input(
            "Notes", 
            key=f"notes_{sysname}", 
            label_visibility="collapsed", 
            placeholder="Notes..." if not is_submitted else "Submitted",
            disabled=is_submitted
        )
    
    with logcol:
        if is_submitted:
            st.button("✓ Logged", key=f"btn_{sysname}", disabled=True, use_container_width=True)
        else:
            if st.button("Log", key=f"btn_{sysname}", type="primary", use_container_width=True):
                if selected_person:
                    if system in individual_tank_names:
                        tank = system
                        system = None
                    else:
                        tank = None
                    
                    logger.debug(f'{check_date=}')

                    if db.log_water(check_date, selected_person, system, coductivity, pH,
                                    amm, nitrate, nitrite, waterx, notes, tank=tank):
                        st.session_state.submitted_system.add(sysname)
                        st.success(f"✅ Logged")
                    else:
                        st.error(f"Failed")
                else:
                    st.error("Select a person")
    
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

if st.button("Next (Check fish)"):
    st.switch_page('pages/2_Check_Fish.py')
