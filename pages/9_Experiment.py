import streamlit as st
from datetime import datetime
import logging

from utils.settings import health_statuses, health_status_colors
import utils.dbfunctions as db
from utils.formatting import apply_custom_css
from utils.date_person import date_person_input

logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(page_title="Record Experiment", page_icon="🔬", layout="wide")

db.stop_if_not_logged_in()

apply_custom_css()

st.title("🔬 Record Experiment")
st.subheader(f"Logged in as: {st.session_state.full_name}")

# Load fish data
fish_data = db.get_all_fish(include_dead=False,
                            return_df=True)
exp_data = db.get_all_experiments(return_df=True)

project_description = ""
if exp_data.empty:
    project_names = []
    project_options = ["New Project"]
else:
    project_names = exp_data['project'].unique().tolist()
    project_options = project_names + ["New Project"]

selected_project = st.selectbox("Select Project", options=project_options)
if selected_project == "New Project":
    new_project_name = st.text_input("Enter New Project Name")
    if new_project_name:
        selected_project = new_project_name
else:
    project_description = exp_data[exp_data['project'] == selected_project]['project_description'].iloc[0]

project_description = st.text_area("Project Description",
                                   value=project_description)

# Top row with Date and Person
exp_date, selected_person = date_person_input()

exp_fish = st.selectbox("Select Fish for Experiment",
                        options=fish_data['id'].tolist())
exp_notes = st.text_area("Experiment Description")

is_terminal = st.checkbox("Terminal Experiment")

selected_fish_data = fish_data[fish_data['id'] == exp_fish].iloc[0]

if selected_fish_data['number_in_group'] > 1:
    n_fish = st.number_input("Number of fish from this group used",
                             min_value=1,
                             max_value=selected_fish_data['number_in_group'],
                             value=selected_fish_data['number_in_group'])
else:
    n_fish = 1

if st.button("Record Experiment"):
    if not selected_project:
        st.error("Please select or enter a project name.")
    elif not exp_fish:
        st.error("Please select a fish for the experiment.")
    else:
        db.record_experiment(fish_id=exp_fish,
                             project=selected_project,
                             project_description=project_description,
                             experiment_description=exp_notes,
                             date=exp_date,
                             person=selected_person,
                             is_terminal=is_terminal,
                             n_fish=n_fish)
        st.success("Experiment recorded successfully.")

st.divider()

st.subheader(f"Previous experiments on {exp_fish}")

if not exp_data.empty:
    exp_on_fish = exp_data[exp_data['fish'] == exp_fish]

    if exp_on_fish.empty:
        st.info("No previous experiments recorded for this fish.")
    else:
        # Display each health note as a card
        for _, exp1 in exp_on_fish.iterrows():
            with st.container():
                exp_date = datetime.fromisoformat(exp1['date'].replace('Z', '+00:00'))
                
                st.markdown(f"*By: {exp1['by']}*")
                
                st.markdown(f"**Project:** {exp1['project']}")
                st.markdown(exp1['project_description'])

                st.markdown("**Experiment Description:**")
                st.markdown(exp1['experiment_description'])

                st.markdown("---")

else:
    st.info("No experiments recorded for this fish.")