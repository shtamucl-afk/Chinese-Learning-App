# sheets.py

import streamlit as st
from datetime import datetime
import pytz
import gspread
from google.oauth2.service_account import Credentials
from Modules.text_utils import canon_title_for_compare

def get_hong_kong_time():
    return datetime.now(pytz.timezone('Asia/Hong_Kong'))

@st.cache_resource
def get_gs_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_json = st.secrets.get("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        raise RuntimeError("GOOGLE_CREDENTIALS_JSON is not set in secrets.")
    import json
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    return client.open("Chinese Learning Records").sheet1

def init_google_sheets():
    try:
        return get_gs_sheet()
    except Exception as e:
        st.error(f"Error initializing Google Sheets: {e}")
        return None

@st.cache_data(ttl=30, show_spinner=False)
def load_gs_data_cached():
    sheet = init_google_sheets()
    if sheet is None:
        return []
    return sheet.get_all_records()

def check_record_exists(book_title: str, article_title: str, model_used: str) -> bool:
    records = load_gs_data_cached()
    bt_key = canon_title_for_compare(book_title)
    at_key = canon_title_for_compare(article_title)
    mu_key = (model_used or "").strip().lower()
    for r in records:
        if (canon_title_for_compare(r.get("book_title","")) == bt_key and
            canon_title_for_compare(r.get("article_title","")) == at_key and
            r.get("model_used","").strip().lower() == mu_key):
            return True
    return False

def save_to_gs(text_data, keywords, dictionary_data, model_used, book_title="", article_title="", page_number=""):
    try:
        sheet = init_google_sheets()
        if sheet is None:
            return 0

        records = load_gs_data_cached()
        new_record = {
            "export_date": get_hong_kong_time().strftime("%Y-%m-%d %H:%M:%S"),
            "book_title": book_title.strip(),
            "article_title": article_title.strip(),
            "page_number": page_number.strip(),
            "original_text_trad": text_data,
            "keywords": keywords,
            "dictionary_data": dictionary_data,
            "model_used": model_used.strip()
        }

        record_index = None
        for i, r in enumerate(records):
            if (r["book_title"].strip().lower() == book_title.strip().lower() and
                r["article_title"].strip().lower() == article_title.strip().lower() and
                r["model_used"].strip().lower() == model_used.strip().lower()):
                record_index = i + 2  # header + 1-based
                break

        values = list(new_record.values())
        if record_index:
            sheet.update(f"A{record_index}:H{record_index}", [values])
            load_gs_data_cached.clear()
        else:
            sheet.append_row(values)
            load_gs_data_cached.clear()
        return len(records) + (0 if record_index else 1)
    except Exception as e:
        st.error(f"Error saving to Google Sheets: {e}")
        return 0
