import streamlit as st
from supabase import create_client, Client
import logging

import utils.dbfunctions as db

logger = logging.getLogger('FishDB')

# Initialize Supabase client
@st.cache_resource
def init_supabase():
    """Initialize Supabase client with credentials from secrets"""
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

def get_supabase_client():
    """Get Supabase client with current session"""
    client = init_supabase()
    
    # If we have a session, set the auth header
    if st.session_state.get('session'):
        client.postgrest.auth(st.session_state.session.access_token)
    
    return client
    
def sign_up(email: str, password: str, full_name: str):
    """Sign up a new user"""
    try:
        supabase = get_supabase_client()
        response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        if response.user:
            response = (
                supabase.table("People")
                .insert({
                    'id': st.session_state.user['id'],
                    'full_name': full_name,
                    'email': email,
                    'active': True
                })
                .execute()
            )

            st.success("✅ Sign up successful! Please check your email to verify your account.")
            return True
        else:
            st.error("Sign up failed. Please try again.")
            return False
    except Exception as e:
        st.error(f"Error during sign up: {str(e)}")
        return False

def sign_in(email: str, password: str):
    """Sign in an existing user"""
    try:
        supabase = get_supabase_client()

        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        if response.user:
            logger.debug("sign_in")
            st.session_state.user = response.user
            st.session_state.session = response.session
            st.session_state.full_name = get_full_name()

            st.success("✅ Signed in successfully!")
            st.rerun()
            return True
        else:
            st.error("Sign in failed. Please check your credentials.")
            return False
    except Exception as e:
        st.error(f"Error during sign in: {str(e)}")
        return False

def get_full_name():
    try:
        supabase = get_supabase_client()

        response = (
            supabase.table('People')
            .select(
                'full_name, id'
            )
            .eq('id', st.session_state.user.id)
            .execute()
        )

        logger.debug(f"full_name: {response=}")
        if response.data:
            return response.data[0]['full_name']
        else:
            st.error("No person found matching id {id}")
    except Exception as e:
        logger.debug(f"Error: {str(e)}")
        st.error(f"Error during sign in: {str(e)}")
        return None    

def sign_out():
    """Sign out the current user"""
    try:
        supabase = get_supabase_client()
        st.session_state.user = None
        st.session_state.session = None
        st.success("✅ Signed out successfully!")
        st.rerun()
    except Exception as e:
        st.error(f"Error during sign out: {str(e)}")

def reset_password(email: str):
    """Send password reset email"""
    try:
        supabase = get_supabase_client()
        supabase.auth.reset_password_email(email)
        st.success("✅ Password reset email sent! Please check your inbox.")
        return True
    except Exception as e:
        st.error(f"Error sending reset email: {str(e)}")
        return False

def update_password(new_password: str):
    """Update user password"""
    try:
        supabase = get_supabase_client()
        supabase.auth.update_user({"password": new_password})
        st.success("✅ Password updated successfully!")
        return True
    except Exception as e:
        st.error(f"Error updating password: {str(e)}")
        return False

def logout():
    """Logout user"""
    st.session_state.user = None
    st.session_state.session = None

