# tab5_tools.py
# Full Tab 5 implementation:
#   - Tool 1: 繁簡轉換 + 字典解釋  (AI)
#   - Tool 2: 雙向翻譯            (AI)
#   - Tool 3: 雙語發音 (TTS)      (Azure Speech via tts.py helpers)
#
# Notes:
# - Uses file-based temp storage exactly like your original approach.
# - TTS voice options & selection UI are centralized in tts.py (VOICE_CATALOG, voice_selectbox, synthesize_dual).
# - If you keep only TTS, remove Tool 1 & 2 blocks and the `call_ai_model` import.

import os
import streamlit as st
from Modules.storage import save_to_temp_file, load_from_temp_file
from Modules.ai import call_ai_model                     # Remove this import if you keep TTS-only
from Modules.tts import voice_selectbox, synthesize_dual, _voice_label # Centralized TTS helpers


def render():
    st.header("🛠️ 工具")
    t1, t2, t3 = st.tabs(["繁簡轉換+字典", "雙向翻譯", "雙語發音"])

    # -------------------------------------------------------------------------
    # Tool 1: 繁簡轉換 + 字典解釋 (AI)
    # -------------------------------------------------------------------------
    with t1:
        st.subheader("繁簡轉換(拼音)+字典解釋")

        # Input text for conversion
        conversion_input = st.text_area(
            "輸入中文文本（繁體或簡體）:",
            height=100,
            key="conversion_input",
            help="輸入要轉換的文本，系統會顯示繁體、簡體、拼音和字典解釋"
        )

        if st.button("轉換", key="convert_button"):
            if conversion_input and conversion_input.strip():
                # Prompt mirrors your original
                prompt = f"""
Please convert the following Chinese text and provide the results in a table format with 6 columns:
Column 1: "繁體" (original sentence or chunk in Traditional Chinese)
Column 2: "簡體" (convert column 1 to Simplified Chinese)
Column 3: "拼音" (Mandarin pinyin with tone marks, e.g., mā, má, mǎ, mà)
Column 4: "解釋" (beginner-friendly definition)
Column 5 & 6: "例句" (example in Traditional and Simplified Chinese)
Text to convert: "{conversion_input}"
Do not split the text arbitrarily; keep the original sentence structure.
"""
                out = call_ai_model(prompt)
                save_to_temp_file(out, "conversion_output.txt")

                st.markdown("### 轉換結果")
                st.markdown(out)
            else:
                st.warning("請輸入文本")
        else:
            # Show previous result if available
            prev = load_from_temp_file("conversion_output.txt")
            if prev:
                st.markdown("### 轉換結果")
                st.markdown(prev)

    # -------------------------------------------------------------------------
    # Tool 2: 雙向翻譯 (AI)
    # -------------------------------------------------------------------------
    with t2:
        st.subheader("雙向翻譯")

        translation_direction = st.radio(
            "選擇翻譯方向:",
            ["中文 to English", "English to 中文"],
            horizontal=True,
            key="translation_direction"
        )

        if translation_direction == "中文 to English":
            input_label = "輸入中文文本（繁體或簡體）:"
            help_text   = "輸入要翻譯成英文的中文文本"
        else:
            input_label = "輸入英文文本:"
            help_text   = "輸入要翻譯成中文的英文文本"

        translation_input = st.text_area(input_label, height=100, key="translation_input", help=help_text)

        if st.button("翻譯", key="translate_button"):
            if translation_input and translation_input.strip():
                if translation_direction == "中文 to English":
                    prompt = f"""
Please translate the following Chinese text to English: "{translation_input}"
Provide a clear and accurate translation.
If the text contains idioms or cultural references, please provide both a literal translation and an explanation of the meaning in English.
The answer should be provided in a plain-text table with 3 columns:
"中文" (original), "英文翻譯" (translation), "解釋" (explanation if needed).
"""
                else:
                    prompt = f"""
Please translate the following English text to Chinese (Traditional and Simplified): "{translation_input}"
Provide a clear and accurate translation.
Return two plain-text tables.
Table 1: "Table 1: Full translation" with columns: "英文", "繁體", "簡體", "拼音"
Table 2: "Table 2: Breakdown of Translation" with columns: "英文", "繁體", "簡體", "拼音", "解釋", "例句"
Use tone-mark pinyin (mā, má, mǎ, mà). Keep original passage format.
"""
                out = call_ai_model(prompt)
                save_to_temp_file(out, "translation_output.txt")

                st.markdown("### 翻譯結果")
                st.markdown(out)
            else:
                st.warning("請輸入要翻譯的文本")
        else:
            prev = load_from_temp_file("translation_output.txt")
            if prev:
                st.markdown("### 翻譯結果")
                st.markdown(prev)

    # -------------------------------------------------------------------------
    # Tool 3: 雙語發音 (TTS)
    # -------------------------------------------------------------------------
    with t3:
        st.subheader("雙語發音")

        tts_input = st.text_area(
            "輸入要朗讀的文本:",
            height=60,
            key="tts_tool_input",
            help="輸入要生成粵語和普通話發音的文本"
        )

        # Centralized voice dropdowns (distinct keys from Tab 3 to avoid collisions)
        c1, c2 = st.columns(2)
        with c1:
            voice_selectbox("cantonese", key="cantonese_voice_selector_tab5", label="選擇粵語語音")
        with c2:
            voice_selectbox("mandarin",  key="mandarin_voice_selector_tab5",  label="選擇普通話語音")

        if st.button("生成發音", key="generate_tts_button"):
            if not (tts_input and tts_input.strip()):
                st.warning("請輸入要朗讀的文本")
            else:
                # One call, both audios
                res = synthesize_dual(tts_input)

                if res["cantonese_path"]:
                    save_to_temp_file(res["cantonese_path"], "cantonese_audio_tool_path.txt")
                if res["mandarin_path"]:
                    save_to_temp_file(res["mandarin_path"], "mandarin_audio_tool_path.txt")
                save_to_temp_file(res["text"], "tts_text.txt")

                st.rerun()

        # Read back any generated audio
        yue_path = load_from_temp_file("cantonese_audio_tool_path.txt")
        man_path = load_from_temp_file("mandarin_audio_tool_path.txt")
        tts_text = load_from_temp_file("tts_text.txt")

        

        if yue_path and man_path and os.path.exists(yue_path) and os.path.exists(man_path):
            st.markdown(f"**朗讀文本:** {tts_text}")

            c1, c2 = st.columns(2)
            with c1:
                st.info(f"粵語發音 - {_voice_label(st.session_state.get('selected_cantonese_voice', ''))}")
                st.audio(yue_path, format="audio/wav")
            with c2:
                st.info(f"普通話發音 - {_voice_label(st.session_state.get('selected_mandarin_voice', ''))}")
                st.audio(man_path, format="audio/wav")

            if st.button("清除音頻", key="clear_tts_audio"):
                try:
                    if os.path.exists(yue_path): os.remove(yue_path)
                    if os.path.exists(man_path): os.remove(man_path)
                except Exception:
                    pass
                save_to_temp_file("", "cantonese_audio_tool_path.txt")
                save_to_temp_file("", "mandarin_audio_tool_path.txt")
                save_to_temp_file("", "tts_text.txt")
                st.rerun()
