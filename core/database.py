import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def _client() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

def init_db():
    pass  # Tables are managed in Supabase — see supabase_migration.sql

def create_user(username, password, full_name):
    try:
        _client().table('users').insert({
            'username': username,
            'password': password,
            'full_name': full_name
        }).execute()
        return True
    except Exception:
        return False

def get_user(username):
    result = _client().table('users').select('*').eq('username', username).execute()
    return result.data[0] if result.data else None

def get_user_progress(user_id):
    result = _client().table('user_progress').select('*').eq('user_id', user_id).execute()
    return result.data[0] if result.data else None

def create_user_progress(user_id, job_path_id):
    _client().table('user_progress').insert({
        'user_id': user_id,
        'job_path_id': job_path_id
    }).execute()

def get_tasks(user_id, week):
    result = _client().table('tasks').select('*').eq('user_id', user_id).eq('week', week).execute()
    return result.data

def save_task(user_id, week, title, description, deliverable):
    _client().table('tasks').insert({
        'user_id': user_id,
        'week': week,
        'title': title,
        'description': description,
        'deliverable': deliverable
    }).execute()

def submit_task(task_id, submission):
    _client().table('tasks').update({
        'submission': submission,
        'status': 'submitted'
    }).eq('id', task_id).execute()

def save_feedback(task_id, feedback):
    _client().table('tasks').update({
        'feedback': feedback,
        'status': 'reviewed'
    }).eq('id', task_id).execute()

def advance_week(user_id):
    result = _client().table('user_progress').select('current_week').eq('user_id', user_id).execute()
    current_week = result.data[0]['current_week']
    _client().table('user_progress').update({
        'current_week': current_week + 1
    }).eq('user_id', user_id).execute()

def resubmit_task(task_id):
    _client().table('tasks').update({
        'status': 'pending',
        'submission': None,
        'feedback': None
    }).eq('id', task_id).execute()
