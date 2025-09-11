# tab3_tts.py
# Tab 3: 語音朗讀
# - Uses centralized TTS helpers from tts.py:
#     - voice_selectbox(language, key, label)
#     - synthesize_dual(text, cantonese_id=None, mandarin_id=None)
# - Preserves original file-based temp storage & st.rerun() flow.

import os
import streamlit as st
from Modules.storage import save_to_temp_file, load_from_temp_file
from Modules.tts import voice_selectbox, synthesize_dual, _voice_label




def render():
    st.header("🗣️ 語音朗讀")

    # --- Input text (persist to temp file) ---
    tts_input = st.text_area(
        "輸入你想朗讀的中文句子（可用繁體或簡體）",
        value=load_from_temp_file("tts_input.txt", ""),
        key="tts_input",
        height=150,
        help="輸入要朗讀的文字，選擇語音後點擊「生成雙語發音」"
    )
    if tts_input != load_from_temp_file("tts_input.txt", ""):
        save_to_temp_file(tts_input, "tts_input.txt")

    # --- Voice selection (centralized; no repeated lists) ---
    col_yue, col_mand = st.columns(2)
    with col_yue:
        # Stores selection in st.session_state.selected_cantonese_voice
        voice_selectbox("cantonese", key="cantonese_voice_selector", label="選擇粵語語音")
    with col_mand:
        # Stores selection in st.session_state.selected_mandarin_voice
        voice_selectbox("mandarin", key="mandarin_voice_selector", label="選擇普通話語音")

    # --- Generate both audios in one call ---
    if st.button("生成雙語發音", key="generate_both_audio", use_container_width=True):
        if not (tts_input and tts_input.strip()):
            st.warning("請輸入要朗讀的文字")
        else:
            res = synthesize_dual(tts_input)  # Uses current selections from session (or defaults)
            # Save paths & text to temp files
            if res.get("cantonese_path"):
                save_to_temp_file(res["cantonese_path"], "cantonese_audio_path.txt")
            if res.get("mandarin_path"):
                save_to_temp_file(res["mandarin_path"], "mandarin_audio_path.txt")
            save_to_temp_file(res.get("text", tts_input), "audio_text.txt")
            st.rerun()

    # --- Read back any generated audio ---
    cantonese_path = load_from_temp_file("cantonese_audio_path.txt")
    mandarin_path  = load_from_temp_file("mandarin_audio_path.txt")
    audio_text     = load_from_temp_file("audio_text.txt")

    # --- Show players if both audio files exist ---
    if (
        cantonese_path and mandarin_path
        and os.path.exists(cantonese_path)
        and os.path.exists(mandarin_path)
    ):
        # Display the text being read
        st.markdown("**朗讀文本:**")
        st.markdown(f"<p>{audio_text}</p>", unsafe_allow_html=True)

        # Resolve labels from current session selections (fallback to ids if needed)
        yue_id = st.session_state.get("selected_cantonese_voice", "")
        man_id = st.session_state.get("selected_mandarin_voice", "")
        yue_label = _voice_label(yue_id)
        man_label = _voice_label(man_id)

        c1, c2 = st.columns(2)
        with c1:
            st.info(f"粵語發音 - {yue_label}")
            st.audio(cantonese_path, format="audio/wav")
        with c2:
            st.info(f"普通話發音 - {man_label}")
            st.audio(mandarin_path, format="audio/wav")

        # Clear audio
        if st.button("清除音頻", key="clear_audio"):
            try:
                if os.path.exists(cantonese_path):
                    os.remove(cantonese_path)
                if os.path.exists(mandarin_path):
                    os.remove(mandarin_path)
            except Exception:
                pass
            save_to_temp_file("", "cantonese_audio_path.txt")
            save_to_temp_file("", "mandarin_audio_path.txt")
            save_to_temp_file("", "audio_text.txt")
            st.rerun()
