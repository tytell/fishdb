import streamlit as st
from datetime import datetime
import logging

import utils.dbfunctions as db

logger = logging.getLogger('__name__')
logger.setLevel(logging.DEBUG)

def date_person_input():
    # Top row with Date and Person
    datecol, timecol, personcol = st.columns(3, gap='small')

    with datecol:
        check_date = st.date_input(
            "Date",
            value="today"
        )

    with timecol:
        check_time = st.time_input("Time", value = "now")
    
    with personcol:
        people = db.get_all_people()
        names = [p1['full_name'] for p1 in people]
        if st.session_state.full_name in names:
            default_name_ind = list(names).index(st.session_state.full_name)
        else:
            default_name_ind = 0
            logger.warning(f'Person {st.session_state.full_name} not found in database')

        if people:
            selected_person = st.selectbox("Person", people,
                                        index = default_name_ind)
        else:
            st.warning("No people found in People table")
            selected_person = None
    
    # make the check_date unique (probably) by adding the current seconds
    check_date = datetime.combine(check_date, check_time)
    current_seconds = datetime.now().second
    check_date = check_date.replace(second=current_seconds)
    
    return check_date, selected_person
