# tab1_typo_checker.py
import os
import unicodedata
import streamlit as st
from Modules.text_utils import normalize_input_cached, highlight_words_dual
from Modules.storage import save_to_temp_file, load_from_temp_file, get_temp_dir
from Modules.ai import call_ai_model


def _parse_markdown_table(response_text: str):
    """
    Parse markdown table rows like:
    | 錯字 | 正確 | 解釋 |
    |  A   |  B   |  ... |
    Returns (typo_list, ai_correct_list).
    """
    typo_list, ai_correct_list = [], []
    if not response_text:
        return typo_list, ai_correct_list

    for line in response_text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]  # drop empty first/last
        if len(cells) < 2:
            continue
        # skip headers / separators
        if cells[0] in ("錯字", "---") or cells[1] in ("正確", "---"):
            continue

        typo, correct = cells[0], cells[1]
        if typo and correct and typo != "此課文沒有錯字":
            typo_list.append(typo)
            ai_correct_list.append(correct)

    return typo_list, ai_correct_list


def render():
    st.header("📖 課文")

    # 1) Text input (persist to temp file)
    text_input = st.text_area(
        "Paste your Chinese text here (Traditional or Simplified):",
        value=load_from_temp_file("tab1_text.txt", ""),
        key="text_input_tab1",
    )
    if text_input != load_from_temp_file("tab1_text.txt", ""):
        save_to_temp_file(text_input, "tab1_text.txt")

    # 2) Always show the button
    check_clicked = st.button("🔍 檢查課文是否有錯字", key="check_typo_tab1")

    # 3) One-time init for this tab
    if "tab1_checked" not in st.session_state:
        st.session_state.tab1_checked = False

    # Ensure persistence file exists
    if not os.path.exists(os.path.join(get_temp_dir(), "last_typo_check_response.txt")):
        save_to_temp_file("", "last_typo_check_response.txt")

    # 4) Handle click → call AI, parse, persist
    if check_clicked:
        if not text_input:
            st.warning("Please enter some text first.")
            st.session_state.tab1_checked = False
            return

        # Normalize only when needed
        text_trad, text_simp = normalize_input_cached(text_input)

        prompt_check = f"""
I just copied the following Chinese text from an image I took using OCR, I will need to study this text for my homework and want to make sure the OCR has not picked up the wrong words. Please carefully review the passage for any incorrect, uncommon, or misused characters:

\"{text_trad}\"

If there are any issues, list the typo in a markdown table format with the following columns:
Column 1 - heading = "錯字", content = problematic character or phrase
Column 2 - heading = "正確", content = correct character or phrase
Column 3 - heading = "解釋", content = Using Chinese, explain why they are incorrect or unusual

Please respond only in Traditional Chinese. If the text is clean, simply respond: "此課文沒有錯字 in column 1"
"""
        try:
            response_check = call_ai_model(prompt_check)
            save_to_temp_file(response_check, "last_typo_check_response.txt")

            # parse rows into lists
            typo_list, ai_correct_list = _parse_markdown_table(response_check)
            user_correct_list = ai_correct_list[:]  # start with AI suggestions

            # persist lists
            save_to_temp_file(typo_list, "typo_list.json")
            save_to_temp_file(ai_correct_list, "ai_correct_list.json")
            save_to_temp_file(user_correct_list, "user_correct_list.json")

            st.session_state.tab1_checked = True
        except Exception as e:
            st.error(f"❌ An unexpected error occurred: {e}")
            st.session_state.tab1_checked = False
            return

    # 5) Show results if a check happened (now or previously)
    last_response = load_from_temp_file("last_typo_check_response.txt", "")
    if not (st.session_state.tab1_checked or (last_response and last_response.strip())):
        return

    # Load current state
    typo_list = load_from_temp_file("typo_list.json", [])
    ai_correct_list = load_from_temp_file("ai_correct_list.json", [])
    user_correct_list = load_from_temp_file("user_correct_list.json", [])

    # Normalize current text for rendering
    text_trad, text_simp = normalize_input_cached(text_input) if text_input else ("", "")

    # 6) Show AI’s table or message
    st.subheader("錯字檢查結果：")
    if last_response:
        st.write(last_response)

    # 7) If no typos → show original Traditional + message
    if not typo_list:
        if text_trad:
            st.subheader("原文(繁體)：")
            st.markdown(text_trad, unsafe_allow_html=True)
        st.caption("此課文沒有錯字")
        return

    # 8) If there are typos → editing controls + highlights
    st.subheader("🛠️ 錯字修正選項")

    # Editable user corrections
    current_user = user_correct_list.copy()
    for i, (typo, ai_correct) in enumerate(zip(typo_list, ai_correct_list)):
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown(f"**錯字:** {typo}")
        with col2:
            user_input = st.text_input(
                f"建議修正: {ai_correct}",
                value=current_user[i] if i < len(current_user) else ai_correct,
                key=f"correction_{i}",
            )
            if i < len(current_user):
                # Keep user corrections normalized to Traditional for consistent comparison
                user_trad, _ = normalize_input_cached(user_input)
                user_correct_list[i] = user_trad
    save_to_temp_file(user_correct_list, "user_correct_list.json")
    st.write("如果你想刪除錯字，就留空。")

    # --- ORIGINAL TEXT with RED highlights (suspected typos) ---
    highlighted_trad, highlighted_simp = text_trad, text_simp
    for typo in typo_list:
        typo_norm = unicodedata.normalize('NFKC', typo)
        highlighted_trad, highlighted_simp = highlight_words_dual(
            highlighted_trad, highlighted_simp, typo_norm,
            highlight_style="background-color:#ffcccc;"   # 🔴 RED
        )

    # --- CORRECTED TEXT (YELLOW = kept AI; GREEN = changed by user) ---
    corrected_trad = text_trad
    for typo, ai_word, user_word in zip(typo_list, ai_correct_list, user_correct_list):
        if user_word.strip():
            # Compare using normalized Traditional forms to decide color
            ai_norm, _ = normalize_input_cached(ai_word)
            user_norm, _ = normalize_input_cached(user_word)
            color = "#ffffcc" if user_norm == ai_norm else "#d0f0c0"  # 🟡 or 🟢
            corrected_trad = corrected_trad.replace(
                typo, f'<span style="background-color:{color};">{user_word}</span>'
            )
        else:
            # If user clears the field, remove the typo from corrected text
            corrected_trad = corrected_trad.replace(typo, "")

    # 9) Render side-by-side
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("原文(繁體)：")
        st.markdown(highlighted_trad, unsafe_allow_html=True)
        st.caption("紅色標記：可能錯誤的字詞")
    with col2:
        st.subheader("修正後課文(繁體)")
        st.markdown(corrected_trad, unsafe_allow_html=True)
        st.caption("黃色標記：AI建議（未修改）｜綠色標記：你手動修改的修正")
