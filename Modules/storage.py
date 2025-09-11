# storage.py

import os, json, tempfile, atexit
import streamlit as st

def get_temp_dir() -> str:
    temp_dir = os.path.join(tempfile.gettempdir(), f"chinese_app_{st.session_state.session_id}")
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir

def save_to_temp_file(data, filename: str) -> str:
    path = os.path.join(get_temp_dir(), filename)
    with open(path, 'w', encoding='utf-8') as f:
        if isinstance(data, (list, dict)):
            json.dump(data, f, ensure_ascii=False)
        else:
            f.write(str(data))
    return path
def load_from_temp_file(filename: str, default=None):
    path = os.path.join(get_temp_dir(), filename)
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                if filename.endswith('.json'):
                    return json.load(f)
                return f.read()
        except Exception:
            return default
    return default

def clear_temp_data():
    try:
        temp_dir = get_temp_dir()
        for name in os.listdir(temp_dir):
            try:
                os.remove(os.path.join(temp_dir, name))
            except Exception:
                pass
    except Exception:
        pass

# register clean-up once per session
if 'session_initialized' not in st.session_state:
    st.session_state.session_initialized = True
    atexit.register(clear_temp_data)
