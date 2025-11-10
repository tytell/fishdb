"""
Admin Panel for Fish Database
Requires access level 5 or higher
Allows editing of Fish, Tanks, and Systems tables using data_editor
"""
import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import logging

from utils.formatting import apply_custom_css #, init_session_state
import utils.dbfunctions as db

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Page configuration
st.title("⚙️ Admin Panel")
st.set_page_config(page_title="Admin Panel", page_icon="⚙️", layout="wide")

db.stop_if_not_logged_in(min_access=5)

apply_custom_css()

# Initialize session state for tracking changes
if 'pending_changes' not in st.session_state:
    st.session_state.pending_changes = {}
if 'deleted_rows' not in st.session_state:
    st.session_state.deleted_rows = {}


# ============================================
# HELPER FUNCTIONS
# ============================================

def apply_changes(table_name, original_df, edited_df, id_column='id'):
    """Apply changes from edited dataframe to database"""
    changes_made = False
    errors = []
    
    supabase = db.get_supabase_client()

    # Find updated rows
    if not original_df.empty and not edited_df.empty:
        # Ensure both dataframes have same columns for comparison
        common_cols = [col for col in original_df.columns if col in edited_df.columns]
        
        for idx in edited_df.index:
            if idx in original_df.index:
                row_id = edited_df.loc[idx, id_column]
                original_row = original_df.loc[idx, common_cols]
                edited_row = edited_df.loc[idx, common_cols]
                
                # Check if row has changed
                if not original_row.equals(edited_row):
                    try:
                        # Prepare update data (exclude id and timestamp columns)
                        update_data = edited_row.to_dict()
                        exclude_cols = [id_column, 'created_at', 'updated_at']
                        update_data = {k: v for k, v in update_data.items() if k not in exclude_cols}
                        
                        # Convert NaN to None
                        update_data = {k: (None if pd.isna(v) else v) for k, v in update_data.items()}
                        
                        response = supabase.table(table_name).update(update_data).eq(id_column, row_id).execute()
                        if response.data:
                            changes_made = True
                    except Exception as e:
                        errors.append(f"Error updating row {row_id}: {str(e)}")
    
    # Find new rows (rows in edited_df that weren't in original_df)
    if not edited_df.empty:
        if original_df.empty:
            new_rows = edited_df
        else:
            new_rows = edited_df[~edited_df[id_column].isin(original_df[id_column])]
        
        for idx, row in new_rows.iterrows():
            try:
                # Prepare insert data (exclude timestamp columns for auto-generation)
                insert_data = row.to_dict()
                exclude_cols = ['created_at', 'updated_at']
                insert_data = {k: v for k, v in insert_data.items() if k not in exclude_cols}
                
                # Convert NaN to None and skip empty required fields
                insert_data = {k: (None if pd.isna(v) else v) for k, v in insert_data.items()}

                # Only insert if we have some non-null data
                if any(v is not None for v in insert_data.values()):
                    response = supabase.table(table_name).insert(insert_data).execute()
                    if response.data:
                        changes_made = True
            except Exception as e:
                errors.append(f"Error inserting new row: {str(e)}")
    
    return changes_made, errors

def delete_rows(table_name, row_ids, id_column='id'):
    """Delete rows from database"""
    errors = []
    deleted = 0
    
    supabase = db.get_supabase_client()
    for row_id in row_ids:
        try:
            response = supabase.table(table_name).delete().eq(id_column, row_id).execute()
            if response.data:
                deleted += 1
        except Exception as e:
            errors.append(f"Error deleting row {row_id}: {str(e)}")
    
    return deleted, errors

# ============================================
# MAIN ADMIN INTERFACE
# ============================================

st.markdown("---")
st.markdown("### 📝 Instructions")
st.info("""
**How to use the data editor:**
- **Edit cells** by clicking on them
- **Add rows** by clicking the ➕ button at the bottom of the table
- **Delete rows** by selecting row(s) and clicking 🗑️ Delete Selected button
- **Save changes** by clicking the 💾 Save Changes button
- Changes are highlighted in yellow
""")

# Create tabs for each table
fishtab, tankstab = st.tabs(["🐟 Fish", "🏠 Tanks",])

# # ============================================
# # TAB 1: SYSTEMS MANAGEMENT
# # ============================================
# with tab1:
#     st.header("Systems Management")
    
#     # Get current systems
#     systems_df = get_all_systems()
    
#     if systems_df.empty:
#         # Initialize with empty row for first entry
#         systems_df = pd.DataFrame({
#             'id': [None],
#             'system_name': [''],
#             'description': [''],
#             'location': [''],
#             'created_at': [None],
#             'updated_at': [None]
#         })
    
#     # Show statistics
#     if not systems_df.empty and systems_df['id'].notna().any():
#         col1, col2 = st.columns([3, 1], gap="small")
#         with col2:
#             st.metric("Total Systems", len(systems_df[systems_df['id'].notna()]))
    
#     # Configure column settings
#     column_config = {
#         'id': st.column_config.NumberColumn('ID', disabled=True, help='Auto-generated ID'),
#         'system_name': st.column_config.TextColumn('System Name *', required=True, max_chars=100),
#         'description': st.column_config.TextColumn('Description', max_chars=500),
#         'location': st.column_config.TextColumn('Location', max_chars=255),
#         'created_at': st.column_config.DatetimeColumn('Created', disabled=True),
#         'updated_at': st.column_config.DatetimeColumn('Updated', disabled=True)
#     }
    
#     # Store original for comparison
#     original_systems = systems_df.copy()
    
#     # Display editable dataframe
#     edited_systems = st.data_editor(
#         systems_df,
#         column_config=column_config,
#         num_rows="dynamic",
#         use_container_width=True,
#         key="systems_editor",
#         hide_index=True
#     )
    
#     # Action buttons
#     col1, col2, col3 = st.columns([2, 1, 1], gap="small")
    
#     with col1:
#         if st.button("💾 Save Changes", key="save_systems", type="primary", use_container_width=True):
#             with st.spinner("Saving changes..."):
#                 changes_made, errors = apply_changes('Systems', original_systems, edited_systems, 'id')
                
#                 if errors:
#                     for error in errors:
#                         st.error(error)
#                 elif changes_made:
#                     st.success("✅ Changes saved successfully!")
#                     st.rerun()
#                 else:
#                     st.info("No changes detected")
    
#     with col2:
#         if st.button("🔄 Refresh", key="refresh_systems", use_container_width=True):
#             st.rerun()
    
#     with col3:
#         # Get selected rows for deletion
#         if 'selected_systems' not in st.session_state:
#             st.session_state.selected_systems = []
        
#         selected_ids = st.multiselect(
#             "Select rows to delete",
#             options=systems_df[systems_df['id'].notna()]['id'].tolist(),
#             format_func=lambda x: systems_df[systems_df['id'] == x]['system_name'].values[0] if len(systems_df[systems_df['id'] == x]) > 0 else str(x),
#             key="systems_delete_select",
#             label_visibility="collapsed"
#         )
    
#     if selected_ids:
#         if st.button("🗑️ Delete Selected", key="delete_systems", use_container_width=True):
#             deleted, errors = delete_rows('Systems', selected_ids, 'id')
            
#             if errors:
#                 for error in errors:
#                     st.error(error)
#             if deleted > 0:
#                 st.success(f"✅ Deleted {deleted} system(s)")
#                 st.rerun()


# ============================================
# TAB 1: FISH MANAGEMENT
# ============================================
with fishtab:
    st.header("Fish Management")
    
    # Get current data
    fish_df = db.get_all_fish(return_df = True)

    # make sure the number_in_group column is an integer
    fish_df['number_in_group'] = fish_df['number_in_group'].fillna(1).astype(int)
    fish_df.set_index('id')
    logger.debug(f"{fish_df.dtypes=}")

    tanks_df = db.get_all_tanks(return_df = True, include_system_details = True)
    species_df = db.get_all_species(return_df = True)
    location_df = db.get_all_locations(return_df = True)

    # # Show statistics
    # if not fish_df.empty and fish_df['id'].notna().any():
    #     valid_fish = fish_df[fish_df['id'].notna()]
    #     col1, col2, col3, col4, col5 = st.columns(5, gap="small")
    #     with col1:
    #         st.metric("Total Fish", len(valid_fish))
    #     with col2:
    #         st.metric("Healthy", len(valid_fish[valid_fish['status'] == 'Healthy']))
    #     with col3:
    #         st.metric("Monitor", len(valid_fish[valid_fish['status'] == 'Monitor']))
    #     with col4:
    #         st.metric("Diseased", len(valid_fish[valid_fish['status'] == 'Diseased']))
    #     with col5:
    #         st.metric("Assigned", len(valid_fish[valid_fish['tank_id'].notna()]))
    
    # Create tank name mapping for display
    tank_options = {}
    if not tanks_df.empty and tanks_df['name'].notna().any():
        tank_sys = []
        for row in tanks_df.itertuples():
            if row.system:
                tank_sys.append(f"{row.name} ({row.system})")
            else:
                tank_sys.append(row.name)

        tank_options = dict(zip(tanks_df['name'], tank_sys))

    species_options = {}
    if not species_df.empty and species_df['name'].notna().any():
        spec_common_name = []
        for row in species_df.itertuples():
            if row.common_name:
                spec_common_name = f"{row.name} ({row.common_name})"
            else:
                spec_common_name = row.name
        species_options = dict(zip(species_df['name'], spec_common_name))

    # Configure column settings
    column_config = {
        'id': st.column_config.TextColumn('ID', required=True, max_chars=100,
                                          help='Unique ID for each fish or group of fish',
                                          pinned=True),
        'species': st.column_config.SelectboxColumn('Species', options=list(species_options.keys()), 
                                                    required=True,
                                                    help='Select species name'),
        'tank': st.column_config.SelectboxColumn('Tank', options=list(tanks_df['name']),
                                                 required=True,
                                                 help='Select tank'),
        'status': st.column_config.SelectboxColumn('Status', options=['Healthy', 'Monitor', 'Diseased', 'Dead'], default='Healthy'),
        'from': st.column_config.SelectboxColumn('From', options=list(location_df['name']),
                                                 help='Select where the fish was acquired or collected'),
        'number_in_group': st.column_config.NumberColumn('Number', 
                                                         format="%d",
                                                         min_value=int(1),
                                                         step=int(1),
                                                         help='Number of fish in the group',
                                                         default=int(1)),
        'system': st.column_config.TextColumn('System', disabled=True,
                                              help="To edit the system, edit the Tanks table"),
        'shelf': st.column_config.TextColumn('Shelf', disabled=True,
                                              help="To edit the tank location, edit the Tanks table"),
        'position_in_shelf': st.column_config.TextColumn('Position', disabled=True,
                                              help="To edit the tank location, edit the Tanks table"),
    }

    original_fish = fish_df.copy()
    
    # Display editable dataframe
    edited_fish = st.data_editor(
        fish_df,
        column_config=column_config,
        num_rows="dynamic",
        width="stretch",
        key="fish_editor",
        hide_index=True
    )
    
    # Show tank names below for reference
    if tank_options:
        with st.expander("📋 Tank Reference", expanded=False):
            ref_df = tanks_df[['name', 'system']]
            st.dataframe(ref_df, hide_index=True, width='stretch')
    
    # Action buttons
    col1, col2, col3 = st.columns([2, 1, 1], gap="small")
    
    with col1:
        if st.button("💾 Save Changes", key="save_fish", type="primary", width='stretch'):
            with st.spinner("Saving changes..."):
                logger.debug(f"{edited_fish.dtypes=}")

                edited_fish['number_in_group'] = edited_fish['number_in_group'].fillna(1).astype(int)
                drop_cols = ['system', 'shelf', 'position_in_shelf', 'sort_key']

                changes_made, errors = apply_changes('Fish', 
                                                     original_fish.drop(columns=drop_cols), 
                                                     edited_fish.drop(columns=drop_cols), 
                                                     id_column='id')
                
                if errors:
                    for error in errors:
                        st.error(error)
                elif changes_made:
                    st.success("✅ Changes saved successfully!")
                    st.rerun()
                else:
                    st.info("No changes detected")
    
    with col2:
        if st.button("🔄 Refresh", key="refresh_fish", width='stretch'):
            st.rerun()
    
    with col3:
        selected_fish_ids = st.multiselect(
            "Select rows to delete",
            options=fish_df['id'].tolist(),
            # format_func=lambda x: f"{fish_df[fish_df['id'] == x]['name'].values[0]} ({fish_df[fish_df['id'] == x]['species'].values[0]})" if len(fish_df[fish_df['id'] == x]) > 0 else str(x),
            key="fish_delete_select",
            label_visibility="collapsed"
        )
    
    if selected_fish_ids:
        if st.button("🗑️ Delete Selected", key="delete_fish", width='stretch'):
            deleted, errors = delete_rows('Fish', selected_fish_ids, 'id')
            
            if errors:
                for error in errors:
                    st.error(error)
            if deleted > 0:
                st.success(f"✅ Deleted {deleted} fish")
                st.rerun()

# ============================================
# TAB 2: TANKS MANAGEMENT
# ============================================
with tankstab:
    st.header("Tanks Management")
    
    # Get current data
    tanks_df = db.get_all_tanks(return_df=True)
    systems_df = db.get_all_systems(return_df=True)

    logger.debug(f"{tanks_df.dtypes=}")

    # Configure column settings
    column_config = {
        'name': st.column_config.TextColumn('Name', required=True),
        'volume': st.column_config.NumberColumn('Volume (L) *', required=True, min_value=0, format="%.1f"),
        'is_hospital': st.column_config.CheckboxColumn('Hospital Tank', default=False),
        'system': st.column_config.SelectboxColumn('System', options=list(systems_df['name']), help='Select a system. Hospital tanks do not have a system'),
        'shelf': st.column_config.NumberColumn('Shelf', help="Shelf in rack (1 is top)",
                                               format="%d", min_value=int(1), step=int(1)),
        'position_in_shelf': st.column_config.NumberColumn('Position in shelf', help="Position on the shelf (1 is furthest left)",
                                               format="%d", min_value=int(1), step=int(1)),
    }
    
    original_tanks = tanks_df.copy()
    
    # Display editable dataframe
    edited_tanks = st.data_editor(
        tanks_df,
        column_config=column_config,
        num_rows="dynamic",
        width='stretch',
        key="tanks_editor",
        hide_index=True
    )
    
    # Show system names below for reference
    with st.expander("📋 System Reference", expanded=False):
        ref_df = systems_df[['name']]
        st.dataframe(ref_df, hide_index=True, width='stretch')
    
    # Action buttons
    col1, col2, col3 = st.columns([2, 1, 1], gap="small")
    
    with col1:
        if st.button("💾 Save Changes", key="save_tanks", type="primary", width='stretch'):
            logger.debug(f"{edited_tanks.dtypes=}")

            with st.spinner("Saving changes..."):
                changes_made, errors = apply_changes('Tanks', original_tanks, edited_tanks, 'name')
                
                if errors:
                    for error in errors:
                        st.error(error)
                elif changes_made:
                    st.success("✅ Changes saved successfully!")
                    st.rerun()
                else:
                    st.info("No changes detected")
    
    with col2:
        if st.button("🔄 Refresh", key="refresh_tanks", width='stretch'):
            st.rerun()
    
    with col3:
        selected_tank_ids = st.multiselect(
            "Select rows to delete",
            options=tanks_df['name'].tolist(),
            key="tanks_delete_select",
            label_visibility="collapsed"
        )
    
    if selected_tank_ids:
        if st.button("🗑️ Delete Selected", key="delete_tanks", width='stretch'):
            deleted, errors = delete_rows('Tanks', selected_tank_ids, 'name')
            
            if errors:
                for error in errors:
                    st.error(error)
            if deleted > 0:
                st.success(f"✅ Deleted {deleted} tank(s)")
                st.rerun()

# # Sidebar with admin info
# with st.sidebar:
#     st.subheader("👤 Admin Info")
#     st.write(f"**User:** {user_name or 'Unknown'}")
#     st.write(f"**Email:** {st.session_state.user.email}")
#     st.write(f"**Access Level:** {access_level}")
    
#     st.divider()
    
#     st.subheader("📊 Database Summary")
#     try:
#         systems_count = len(get_all_systems())
#         tanks_count = len(get_all_tanks())
#         fish_count = len(get_all_fish())
        
#         st.metric("Systems", systems_count)
#         st.metric("Tanks", tanks_count)
#         st.metric("Fish", fish_count)
#     except:
#         st.error("Error loading stats")
    
#     st.divider()
    
#     st.subheader("ℹ️ About Access Levels")
#     st.markdown("""
#     **Level 1-4:** Standard users
#     **Level 5-9:** Administrators
#     **Level 10:** Super Admin
    
#     Only Level 5+ can access this panel.
#     """)
    
#     st.divider()
    
#     st.subheader("💡 Tips")
#     st.markdown("""
#     - Click any cell to edit
#     - Use ➕ to add new rows
#     - Changes show in yellow
#     - Save before leaving page
#     - Use FK reference tables
#     """)


