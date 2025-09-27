# ai.py

import streamlit as st

@st.cache_resource
def _init_gemini_model():
    import google.generativeai as genai
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-2.5-flash")

def call_gemini(prompt: str) -> str:
    model = _init_gemini_model()
    if not model:
        return "❌ Gemini API key not configured. Please set GEMINI_API_KEY in secrets."
    try:
        resp = model.generate_content(prompt)
        return resp.text
    except Exception as e:
        msg = str(e)
        if "quota" in msg.lower() or "429" in msg:
            return "⚠️ Gemini API quota used up for today. Please try again tomorrow or upgrade your plan."
        return f"❌ Gemini API Error: {e}"

def call_deepseek(prompt: str, model: str = "deepseek-chat") -> str:
    api_key = st.secrets.get("DEEPSEEK_API_KEY")
    if not api_key:
        return "❌ DeepSeek API key not configured. Please set DEEPSEEK_API_KEY in secrets."
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role":"system","content":"You are a helpful assistant."},
                      {"role":"user","content":prompt}],
            stream=False
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"❌ API Error: {e}"

def call_ai_model(prompt: str) -> str:
    if st.session_state.get("selected_model") == "Gemini":
        return call_gemini(prompt)
    return call_deepseek(prompt)
