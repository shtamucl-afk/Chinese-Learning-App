# tts.py
import tempfile
import streamlit as st
import azure.cognitiveservices.speech as speechsdk

# ---------- Centralized voice catalog (edit here to add/remove voices) ----------
VOICE_CATALOG = {
    "cantonese": [
        {"id": "yue-CN-XiaoMinNeural", "label": "曉敏 (Female)"},
        {"id": "yue-CN-YunSongNeural", "label": "雲松 (Male)"},
    ],
    "mandarin": [
        {"id": "zh-CN-XiaoxiaoNeural", "label": "晓晓 (Female)"},
        {"id": "zh-CN-YunyangNeural",  "label": "云扬 (Male)"},
        {"id": "zh-CN-YunxiNeural",    "label": "云希 (Male)"},
        {"id": "zh-CN-XiaoyiNeural",   "label": "晓伊 (Female)"},
    ],
}

def get_voice_catalog():
    return VOICE_CATALOG

def _voice_label_map(language: str):
    return {v["id"]: v["label"] for v in VOICE_CATALOG.get(language, [])}

def _default_voice(language: str):
    """Prefer last-picked in session; else first in catalog; else None."""
    key = "selected_cantonese_voice" if language == "cantonese" else "selected_mandarin_voice"
    labels = _voice_label_map(language)
    if key in st.session_state and st.session_state[key] in labels:
        return st.session_state[key]
    items = VOICE_CATALOG.get(language, [])
    return items[0]["id"] if items else None

def voice_selectbox(language: str, key: str, label: str):
    """
    Render a selectbox for 'cantonese' | 'mandarin'.
    Stores selection in st.session_state and returns the selected voice id.
    """
    labels = _voice_label_map(language)
    options = list(labels.keys())
    default_id = _default_voice(language)
    default_index = options.index(default_id) if default_id in options else 0

    selected = st.selectbox(
        label,
        options=options,
        index=default_index,
        format_func=lambda vid: labels.get(vid, vid),
        key=key,
    )
    if language == "cantonese":
        st.session_state.selected_cantonese_voice = selected
    else:
        st.session_state.selected_mandarin_voice = selected
    return selected

def _voice_label(voice_id: str) -> str:
    """Map a voice id to a human-friendly label using VOICE_CATALOG."""
    try:
        catalog = get_voice_catalog()
        # Flatten id->label map from both languages
        id_to_label = {v["id"]: v["label"] for lst in catalog.values() for v in lst}
        return id_to_label.get(voice_id, voice_id or "")
    except Exception:
        return voice_id or ""
    
# ---------- Azure TTS (unchanged) ----------
def speak_text_azure(text: str, voice_id: str = None):
    """Synthesize speech via Azure and return a temp .wav path or None."""
    try:
        speech_key = st.secrets.get("AZURE_SPEECH_KEY")
        speech_region = st.secrets.get("AZURE_SPEECH_REGION")
        speech_endpoint = st.secrets.get("AZURE_SPEECH_ENDPOINT", "")

        if not speech_key:
            st.error("Azure語音服務未配置。請在 secrets 設定 AZURE_SPEECH_KEY")
            return None

        if speech_endpoint:
            speech_config = speechsdk.SpeechConfig(endpoint=speech_endpoint, subscription=speech_key)
        else:
            speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)

        speech_config.speech_synthesis_voice_name = voice_id or "zh-CN-XiaoxiaoNeural"

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as fp:
            out_path = fp.name

        audio_config = speechsdk.audio.AudioOutputConfig(filename=out_path)
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
        result = synthesizer.speak_text_async(text).get()

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            return out_path

        cancellation = result.cancellation_details
        msg = f"語音合成失敗: {cancellation.reason}"
        if cancellation.reason == speechsdk.CancellationReason.Error:
            msg += f"\n錯誤詳情: {cancellation.error_details}"
        st.error(msg)
        return None

    except Exception as e:
        st.error(f"Azure語音服務錯誤: {e}")
        return None

# ---------- NEW: one-shot dual synthesis ----------
def _resolve_voice(language: str, provided_id: str | None) -> str | None:
    """
    Use provided_id if given; else selected voice in session; else default voice for the language.
    """
    if provided_id:
        return provided_id
    key = "selected_cantonese_voice" if language == "cantonese" else "selected_mandarin_voice"
    if key in st.session_state and st.session_state[key]:
        return st.session_state[key]
    return _default_voice(language)

def synthesize_dual(text: str, cantonese_id: str | None = None, mandarin_id: str | None = None) -> dict:
    """
    Generate Cantonese + Mandarin audio in one call.
    If voice ids are omitted, use current selections or defaults.

    Returns:
        {
          "text": str,
          "cantonese_id": str,
          "mandarin_id": str,
          "cantonese_path": str | None,
          "mandarin_path": str | None
        }
    """
    text = (text or "").strip()
    if not text:
        return {"text": "", "cantonese_id": None, "mandarin_id": None, "cantonese_path": None, "mandarin_path": None}

    yue_id = _resolve_voice("cantonese", cantonese_id)
    man_id = _resolve_voice("mandarin", mandarin_id)

    yue_path = speak_text_azure(text, voice_id=yue_id) if yue_id else None
    man_path = speak_text_azure(text, voice_id=man_id) if man_id else None

    return {
        "text": text,
        "cantonese_id": yue_id,
        "mandarin_id": man_id,
        "cantonese_path": yue_path,
        "mandarin_path": man_path,
    }
