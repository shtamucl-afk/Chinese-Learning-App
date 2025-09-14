# tab2_study.py
# Matches your original Tab 2 behavior:
# - file-based temp storage for state/perf
# - st.rerun() to reveal overwrite / save-as UI
# - save_to_gs() used for BOTH create and overwrite
# Changes vs your last version:
# - Adds "課文顯示" (normalized Trad/Simp) immediately when passage is entered
# - Moves the small heading "📘字典解釋 - 關鍵詞語" above the keywords input
# - Adds scrollable containers for text display
# - Reorganizes layout to move buttons below text display

import streamlit as st
from Modules.text_utils import normalize_input_cached, highlight_words_dual
from Modules.storage import load_from_temp_file, save_to_temp_file
from Modules.ai import call_ai_model
from Modules.sheets import check_record_exists, save_to_gs


def render():
    current_tab = "課文學習"
    st.header("📘 課文")

    if st.session_state.get('force_highlight', False):
        st.session_state.force_highlight = False
        # This ensures the highlighting will be processed
        st.session_state.words_input_tab2 = load_from_temp_file("tab2_words.txt", "")
        st.rerun()

 
    # Use file-based storage for text input
    text_input_tab2 = st.text_area(
        "Paste your Chinese text here (Traditional or Simplified):", 
        value=load_from_temp_file("tab2_text.txt", ""),
        key="text_input_tab2",
        height=150
    )
    
    # Save to temp file when text changes
    if text_input_tab2 != load_from_temp_file("tab2_text.txt", ""):
        save_to_temp_file(text_input_tab2, "tab2_text.txt")
        # Clear dictionary data when text changes
        save_to_temp_file("", "dictionary_data.txt")
    
    if text_input_tab2:
        text_trad_tab2, text_simp_tab2 = normalize_input_cached(text_input_tab2)
        Lookup_text_tab2 = text_trad_tab2
    
    if text_input_tab2:
        
        # Replace the column layout with tabs
        trad_tab, simp_tab = st.tabs(["繁體中文", "簡體中文"])
        
        with trad_tab:
            # Display the traditional text
            if 'words_input_tab2' in st.session_state and st.session_state.words_input_tab2:
                # Normalize the words input
                words_trad, words_simp = normalize_input_cached(st.session_state.words_input_tab2)
                # Use the normalized version for processing
                highlighted_trad, highlighted_simp = highlight_words_dual(text_trad_tab2, text_simp_tab2, words_trad)
                
                # Split the text into paragraphs and build the full HTML content
                paragraphs = highlighted_trad.split('\n\n')
                html_content = '<div class="scrollable-text">'
                for paragraph in paragraphs:
                    if paragraph.strip():  # Only include non-empty paragraphs
                        html_content += f'<div class="chinese-text-teaching">{paragraph}</div><br>'
                html_content += '</div>'
                
                # Display the entire content in a single markdown call
                st.markdown(html_content, unsafe_allow_html=True)
            else:
                # Display plain text without highlighting, but with proper formatting
                paragraphs = text_trad_tab2.split('\n\n')
                html_content = '<div class="scrollable-text">'
                for paragraph in paragraphs:
                    if paragraph.strip():  # Only include non-empty paragraphs
                        html_content += f'<div class="chinese-text-teaching">{paragraph}</div><br>'
                html_content += '</div>'
                st.markdown(html_content, unsafe_allow_html=True)

        with simp_tab:
            # Display the simplified text
            if 'words_input_tab2' in st.session_state and st.session_state.words_input_tab2:
                # Normalize the words input
                words_trad, words_simp = normalize_input_cached(st.session_state.words_input_tab2)
                # Use the normalized version for processing
                highlighted_trad, highlighted_simp = highlight_words_dual(text_trad_tab2, text_simp_tab2, words_trad)
                
                # Split the text into paragraphs and build the full HTML content
                paragraphs = highlighted_simp.split('\n\n')
                html_content = '<div class="scrollable-text">'
                for paragraph in paragraphs:
                    if paragraph.strip():  # Only include non-empty paragraphs
                        html_content += f'<div class="chinese-text-teaching">{paragraph}</div><br>'
                html_content += '</div>'
                
                # Display the entire content in a single markdown call
                st.markdown(html_content, unsafe_allow_html=True)
            else:
                # Display plain text without highlighting, but with proper formatting
                paragraphs = text_simp_tab2.split('\n\n')
                html_content = '<div class="scrollable-text">'
                for paragraph in paragraphs:
                    if paragraph.strip():  # Only include non-empty paragraphs
                        html_content += f'<div class="chinese-text-teaching">{paragraph}</div><br>'
                html_content += '</div>'
                st.markdown(html_content, unsafe_allow_html=True)

    
    # Move the "辨認關鍵詞語" button and words input below the text display
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Move the "辨認關鍵詞語" button to below the text
        if st.button("辨認關鍵詞語", key="identify_keywords_tab2"):
            if not text_input_tab2:
                st.warning("Please enter some text first.")
            else:
                prompt_words = f"""
                You are a Chinese native speaker, being a language tutor for a 12 year old student.
                Please identify the key complex vocabulary in the passage in "{Lookup_text_tab2}", 
                and provide your selection of words in a text string in the order that they appear in the passage, no explanation needed
                Respond only in Traditional Chinese, separate the words with commas.
                """
                try:
                    response_words = call_ai_model(prompt_words)
                    # Save the identified keywords to a separate file (not the words input)
                    save_to_temp_file(response_words, "ai_suggested_keywords.txt")
                    st.subheader(f"{st.session_state.selected_model} 辨認關鍵詞:")
                    st.write(response_words)
                                    
                except Exception as e:
                    st.error(f"❌ An unexpected error occurred: {e}")
    
    with col2:
        # Dictionary Section - Positioned below the text areas
        st.markdown(
        """
        <div class="dict-keywords" style="margin-bottom:0;">
            <span style="font-size:14px; font-weight:bold;">📘字典解釋 - 關鍵詞語</span>
            <span style="font-size:12px;"> Enter Chinese words to look up (comma-separated):</span>
        </div>
        """,
        unsafe_allow_html=True
        )

        words_input_tab2 = st.text_area(
            "",
            key="words_input_tab2",  # Remove default value
            height=150,
            label_visibility="collapsed",
            on_change=lambda: save_to_temp_file(st.session_state.words_input_tab2, "tab2_words.txt")
        )

        # Initialize session state if not exists
        if "words_input_tab2" not in st.session_state:
            st.session_state.words_input_tab2 = load_from_temp_file("tab2_words.txt", "")
            
        # Save to temp file when words change
        if words_input_tab2 != load_from_temp_file("tab2_words.txt", ""):
            save_to_temp_file(words_input_tab2, "tab2_words.txt")
            # Clear dictionary data when words change
            save_to_temp_file("", "dictionary_data.txt")
            # Rerun to update the highlighted text
            st.rerun()
    
    
    
    # Load dictionary data from temp file
    dictionary_data = load_from_temp_file("dictionary_data.txt")
    
    if st.button("字典", key="dictionary_tab2"):
        if not words_input_tab2:
            st.warning("Please enter some words to look up first.")
        else:
            # Normalize the words input
            words_trad, words_simp = normalize_input_cached(words_input_tab2)
            
            prompt_dict = f"""
            You are a Chinese native speaker, being a language tutor for kids 8-10 years old.

            Please explain the words in "{words_trad}" in Traditional Chinese using Markdown table format with the following columns:

            Column 1: Heading = "繁體", content = the original character in traditional chinese
            Column 2: Heading = "簡體", content = convert the column 1 characters into simplified chinese
            Column 3: Heading = "拼音", content = Mandarin pinyin  
            Column 4: Heading = "解釋", content = A beginner-friendly, simple definition  
            Column 5 & 6: Heading = "例句", content = An example sentence, show in both traditional (column 5) and simplified chinese

            Respond only in Traditional Chinese. Format your response as a Markdown table.
            """
            try:
                response_dict = call_ai_model(prompt_dict)
                save_to_temp_file(response_dict, "dictionary_data.txt")
                dictionary_data = response_dict
                st.session_state.model_used = st.session_state.selected_model
                st.rerun()  # Rerun to display the updated dictionary
            except Exception as e:
                st.error(f"❌ An unexpected error occurred: {e}")
    
    # Display dictionary response if it exists
    if dictionary_data:
        st.subheader(f"{st.session_state.selected_model} Dictionary:")
        st.markdown(dictionary_data)

    # --- Export section (original save-to-temp + st.rerun flow) ---
    st.header("💾 匯出學習資料")
    export_container = st.container()

    with export_container:
        col1, col2, col3 = st.columns(3)

        _prev_book_title = load_from_temp_file("book_title.txt", "")
        _prev_article_title = load_from_temp_file("article_title.txt", "")
        _prev_page_number = load_from_temp_file("page_number.txt", "")

        with col1:
            book_title = st.text_input("書名", key="book_title", value=_prev_book_title)
            if book_title != _prev_book_title:
                save_to_temp_file(book_title, "book_title.txt")

        with col2:
            article_title = st.text_input("文章標題", key="article_title", value=_prev_article_title)
            if article_title != _prev_article_title:
                save_to_temp_file(article_title, "article_title.txt")

        with col3:
            page_number = st.text_input("頁碼", key="page_number", value=_prev_page_number)
            if page_number != _prev_page_number:
                save_to_temp_file(page_number, "page_number.txt")

        book_title_trad = normalize_input_cached(book_title)[0] if book_title else ""
        article_title_trad = normalize_input_cached(article_title)[0] if article_title else ""

        # Read flags from temp files (original flow)
        show_overwrite_options = load_from_temp_file("show_overwrite_options.txt", "False") == "True"
        show_new_name_inputs = load_from_temp_file("show_new_name_inputs.txt", "False") == "True"

        # Export button
        if st.button("匯出到數據庫(Google Sheet)", key="export"):
            if not text_trad_tab2 or not text_trad_tab2.strip():
                st.warning("請先輸入課文內容（上方文字框）。")
                return
            words_trad = normalize_input_cached(words_input_tab2)[0] if words_input_tab2 else ""
            if not words_trad or not words_trad.strip():
                st.warning("請先輸入關鍵詞語。")
                return
            if not dictionary_data or not str(dictionary_data).strip():
                st.warning("請先生成【字典】（點擊上方「字典」按鈕）。")
                return
            if not book_title or not article_title:
                st.error("請填寫書名和文章標題。")
            else:
                exists = check_record_exists(
                    book_title_trad, article_title_trad, st.session_state.selected_model
                )
                if exists:
                    st.warning("已存在相同書名、文章標題和AI模型的記錄。")
                    save_to_temp_file("True", "show_overwrite_options.txt")
                    save_to_temp_file("False", "show_new_name_inputs.txt")
                    st.rerun()  # force options to appear immediately
                else:
                    trad_original = text_trad_tab2
                    trad_keywords = words_trad
                    record_count = save_to_gs(
                        trad_original, trad_keywords, dictionary_data,
                        st.session_state.selected_model, book_title_trad, article_title_trad, page_number
                    )
                    if record_count > 0:
                        st.success(f"資料已成功匯出！數據庫中現在有 {record_count} 條記錄。")
                        save_to_temp_file("False", "show_overwrite_options.txt")
                        save_to_temp_file("False", "show_new_name_inputs.txt")
                    else:
                        st.error("匯出失敗，請檢查錯誤信息。")

        # Overwrite options (original logic, using save_to_gs for overwrite)
        if show_overwrite_options:
            st.info("請選擇如何處理重複記錄：")
            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("覆蓋現有記錄", key="overwrite_confirm"):
                    trad_original = text_trad_tab2
                    words_trad = normalize_input_cached(words_input_tab2)[0] if words_input_tab2 else ""
                    record_count = save_to_gs(
                        trad_original, words_trad, load_from_temp_file("dictionary_data.txt", ""),
                        st.session_state.selected_model, book_title_trad, article_title_trad, page_number
                    )
                    if record_count > 0:
                        st.success("記錄已更新！")
                    else:
                        st.error("更新失敗！")
                    # Reset flags
                    save_to_temp_file("False", "show_overwrite_options.txt")
                    save_to_temp_file("False", "show_new_name_inputs.txt")

            with col2:
                if st.button("使用不同名稱保存", key="save_different"):
                    save_to_temp_file("True", "show_new_name_inputs.txt")
                    save_to_temp_file("False", "show_overwrite_options.txt")
                    st.rerun()

            with col3:
                if st.button("取消操作", key="cancel_export"):
                    save_to_temp_file("False", "show_overwrite_options.txt")
                    save_to_temp_file("False", "show_new_name_inputs.txt")
                    st.rerun()

        # New-name inputs (original logic)
        if show_new_name_inputs:
            new_book_title = st.text_input("新書名", value=book_title, key="new_book_title")
            new_article_title = st.text_input("新文章標題", value=article_title, key="new_article_title")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("確認保存", key="save_with_new_name"):
                    trad_original = text_trad_tab2
                    words_trad = normalize_input_cached(words_input_tab2)[0] if words_input_tab2 else ""
                    record_count = save_to_gs(
                        trad_original, words_trad, load_from_temp_file("dictionary_data.txt", ""),
                        st.session_state.selected_model, new_book_title, new_article_title, page_number
                    )
                    if record_count > 0:
                        st.success(f"資料已成功匯出！數據庫中現在有 {record_count} 條記錄。")
                        save_to_temp_file("False", "show_overwrite_options.txt")
                        save_to_temp_file("False", "show_new_name_inputs.txt")

            with col2:
                if st.button("取消", key="cancel_new_name"):
                    save_to_temp_file("False", "show_new_name_inputs.txt")
