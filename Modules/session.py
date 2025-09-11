# session.py

import uuid
import streamlit as st

def init_session_state():
    """Initialize essential session state variables."""
    essential = {
        'selected_model': "Gemini",
        'selected_cantonese_voice': "yue-CN-XiaoMinNeural",
        'selected_mandarin_voice': "zh-CN-XiaoxiaoNeural",
        'filter_book_title': "",
        'filter_article_title': "",
        'filter_page_number': "",
        'filter_model_used': "",
        'current_tab': "錯字檢查",
        'session_id': str(uuid.uuid4()),
    }
    for k, v in essential.items():
        if k not in st.session_state:
            st.session_state[k] = v
