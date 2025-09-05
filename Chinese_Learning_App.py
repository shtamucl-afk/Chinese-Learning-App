import streamlit as st
import os
from dotenv import load_dotenv
import google.generativeai as genai
from opencc import OpenCC
import tempfile
import azure.cognitiveservices.speech as speechsdk
from openai import OpenAI
import pandas as pd
from datetime import datetime

# Load environment variables
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")
deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")

# Set full-width layout and reduce top padding
st.set_page_config(layout="wide")

# Custom CSS to reduce the top margin
st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 0rem;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 40px;
            white-space: pre-wrap;
            background-color: #f0f2f6;
            border-radius: 4px 4px 0px 0px;
            gap: 1px;
            padding-top: 10px;
            padding-bottom: 10px;
        }
        .stTabs [aria-selected="true"] {
            background-color: #ffffff;
        }
    </style>
""", unsafe_allow_html=True)

# Initialize session state variables
session_vars = {
    'typo_list': [],
    'ai_correct_list': [],
    'user_correct_list': [],
    'original_text': "",
    'text_input_tab1': "",
    'text_input_tab2': "",
    'words_input_tab2': "",
    'tts_input_tab2': "",
    'available_cantonese_voices': [
        {'name': 'yue-CN-XiaoMinNeural', 'description': '曉敏', 'gender': 'Female'},
        {'name': 'yue-CN-YunSongNeural', 'description': '雲松', 'gender': 'Male'}
    ],
    'selected_cantonese_voice': "yue-CN-XiaoMinNeural",
    'available_mandarin_voices': [
        {'name': 'zh-CN-XiaoxiaoNeural', 'description': '晓晓', 'gender': 'Female'},
        {'name': 'zh-CN-YunyangNeural', 'description': '云扬', 'gender': 'Male'},
        {'name': 'zh-CN-YunxiNeural', 'description': '云希', 'gender': 'Male'},
        {'name': 'zh-CN-XiaoyiNeural', 'description': '晓伊', 'gender': 'Female'}
    ],
    'selected_mandarin_voice': "zh-CN-XiaoxiaoNeural",
    'selected_model': "Gemini",  # Default model
    'dictionary_data': None,
    'exported_texts': [],
    'current_revision_text': None,
    'csv_filename': "chinese_learning_records.csv",
    'overwrite_confirmed': False,
    'filter_book_title': "",
    'filter_article_title': "",
    'filter_page_number': "",
    'filter_model_used': ""
}

for key, default_value in session_vars.items():
    if key not in st.session_state:
        st.session_state[key] = default_value

# Initialize Gemini model
if gemini_api_key:
    genai.configure(api_key=gemini_api_key)
    gemini_model = genai.GenerativeModel("gemini-1.5-flash")
else:
    st.warning("Gemini API key not found. Some features may not work.")

# Create header with title and model selection
col1, col2 = st.columns([3, 1])
with col1:
    st.title("📚 Chinese Learning App")
with col2:
    st.write("")  # Add some vertical space
    st.write("")  # Add some vertical space
    model_option = st.radio(
        "選擇AI模型",
        ["Gemini", "DeepSeek"],
        index=0 if st.session_state.selected_model == "Gemini" else 1,
        key="model_selector",
        horizontal=True
    )
    st.session_state.selected_model = model_option

# API call helper functions
def call_gemini(prompt):
    """Call Gemini API with the given prompt"""
    if not gemini_api_key:
        return "❌ Gemini API key not configured. Please check your .env file."
    
    try:
        response = gemini_model.generate_content(prompt)
        return response.text
    except Exception as e:
        if "quota" in str(e).lower() or "429" in str(e):
            return "⚠️ Gemini API quota used up for today. Please try again tomorrow or upgrade your plan."
        else:
            return f"❌ Gemini API Error: {e}"

# DeepSeek API call helper
def call_deepseek(prompt, model="deepseek-chat"):
    client = OpenAI(api_key=deepseek_api_key, base_url="https://api.deepseek.com")
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            stream=False
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ API Error: {e}"

def call_ai_model(prompt):
    """Call the selected AI model with the given prompt"""
    if st.session_state.selected_model == "Gemini":
        return call_gemini(prompt)
    else:
        return call_deepseek(prompt)

# Utility functions (unchanged from your original code)
def normalize_input(text):
    cc_t2s = OpenCC('t2s')  # Traditional to Simplified
    cc_s2t = OpenCC('s2t')  # Simplified to Traditional
    simplified = cc_t2s.convert(text)
    traditional = cc_s2t.convert(text)
    return traditional, simplified

def highlight_words_dual(text_trad, text_simp, words_string):
    cc_t2s = OpenCC('t2s')
    cc_s2t = OpenCC('s2t')

    unified = words_string.replace("，", ",")
    words_raw = [w.strip() for w in unified.split(",") if w.strip()]

    words_trad = [cc_s2t.convert(w) for w in words_raw]
    words_simp = [cc_t2s.convert(w) for w in words_raw]

    for trad, simp in zip(words_trad, words_simp):
        text_trad = text_trad.replace(trad, f"<mark>{trad}</mark>")
        text_simp = text_simp.replace(simp, f"<mark>{simp}</mark>")
    return text_trad, text_simp

def is_traditional(text_input, text_trad, text_simp):
    trad_matches = sum(1 for a, b in zip(text_input, text_trad) if a == b)
    simp_matches = sum(1 for a, b in zip(text_input, text_simp) if a == b)
    return trad_matches >= simp_matches

# Azure TTS functions (unchanged from your original code)
def speak_text_azure(text, voice_id=None):
    """使用Azure语音服务合成粤语语音并保存到文件"""
    try:
        speech_key = os.getenv("AZURE_SPEECH_KEY")
        speech_region = os.getenv("AZURE_SPEECH_REGION")
        speech_endpoint = os.getenv("AZURE_SPEECH_ENDPOINT")
        
        if not speech_key:
            st.error("Azure语音服务未配置。请在.env文件中设置AZURE_SPEECH_KEY")
            return None
            
        # 配置语音合成
        if speech_endpoint:
            speech_config = speechsdk.SpeechConfig(
                endpoint=speech_endpoint,
                subscription=speech_key
            )
        else:
            speech_config = speechsdk.SpeechConfig(
                subscription=speech_key, 
                region=speech_region
            )
        
        # 设置粤语语音
        if voice_id:
            speech_config.speech_synthesis_voice_name = voice_id
        else:
            if st.session_state.available_cantonese_voices:
                speech_config.speech_synthesis_voice_name = st.session_state.available_cantonese_voices[0]['name']
            else:
                st.warning("未找到可用的粵語語音，使用普通話替代")
                speech_config.speech_synthesis_voice_name = "zh-CN-XiaoxiaoNeural"
        
        # 创建临时文件路径
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as fp:
            temp_file_path = fp.name
        
        # 配置音频输出到文件
        audio_config = speechsdk.audio.AudioOutputConfig(filename=temp_file_path)
        
        # 创建语音合成器
        speech_synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config, 
            audio_config=audio_config
        )
        
        # 合成语音
        result = speech_synthesizer.speak_text_async(text).get()
        
        # 检查结果
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            return temp_file_path
        else:
            cancellation_details = result.cancellation_details
            error_msg = f"语音合成失败: {cancellation_details.reason}"
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                error_msg += f"\n错误详情: {cancellation_details.error_details}"
            
            st.error(error_msg)
            return None
            
    except Exception as e:
        st.error(f"Azure语音服务错误: {e}")
        return None

# New functions for export and revision features
def load_csv_data():
    """Load data from the CSV file"""
    if os.path.exists(st.session_state.csv_filename):
        try:
            df = pd.read_csv(st.session_state.csv_filename, encoding='utf-8-sig')
            return df.to_dict('records')
        except:
            return []
    return []

def check_record_exists(book_title, article_title, model_used):
    """Check if a record with the same book, article and model already exists"""
    records = load_csv_data()
    for record in records:
        # Normalize strings for comparison (strip whitespace, case-insensitive)
        if (record["book_title"].strip().lower() == book_title.strip().lower() and 
            record["article_title"].strip().lower() == article_title.strip().lower() and 
            record["model_used"].strip().lower() == model_used.strip().lower()):
            return True
    return False

def save_to_csv(text_data, keywords, dictionary_data, model_used, book_title="", article_title="", page_number=""):
    """Save text data to the main CSV file"""
    # Normalize the input data
    book_title = book_title.strip()
    article_title = article_title.strip()
    page_number = page_number.strip()
    model_used = model_used.strip()
    
    # Create a dictionary with all the data
    new_record = {
        "export_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "book_title": book_title,
        "article_title": article_title,
        "page_number": page_number,
        "original_text": text_data,
        "keywords": keywords,
        "dictionary_data": dictionary_data,
        "model_used": model_used
    }
    
    # Load existing data
    existing_data = load_csv_data()
    
    # Check if we need to update an existing record
    record_exists = False
    for i, record in enumerate(existing_data):
        # Normalize comparison
        if (record["book_title"].strip().lower() == book_title.lower() and 
            record["article_title"].strip().lower() == article_title.lower() and 
            record["model_used"].strip().lower() == model_used.lower()):
            existing_data[i] = new_record
            record_exists = True
            break
    
    # If it's a new record, append it
    if not record_exists:
        existing_data.append(new_record)
    
    # Save to CSV with UTF-8 encoding
    df = pd.DataFrame(existing_data)
    df.to_csv(st.session_state.csv_filename, index=False, encoding='utf-8-sig')
    
    return len(existing_data)

def parse_dictionary_table(dictionary_text):
    """Parse the dictionary table from the AI response"""
    lines = dictionary_text.split('\n')
    table_data = []
    
    # Find the table rows (skip header and separator lines)
    for line in lines:
        if '|' in line and not line.startswith('| -') and not line.startswith('|  '):
            # Remove leading and trailing pipes and split
            cells = [cell.strip() for cell in line.split('|') if cell.strip()]
            if len(cells) >= 6:  # Ensure we have all columns
                table_data.append({
                    "traditional": cells[0],
                    "simplified": cells[1],
                    "pinyin": cells[2],
                    "definition": cells[3],
                    "example_traditional": cells[4],
                    "example_simplified": cells[5]
                })
    
    return table_data

def initialize_csv():
    """Initialize the CSV file with proper headers and encoding"""
    if not os.path.exists(st.session_state.csv_filename):
        # Create an empty DataFrame with the correct columns
        df = pd.DataFrame(columns=[
            "export_date", 
            "book_title", 
            "article_title", 
            "page_number", 
            "original_text", 
            "keywords", 
            "dictionary_data", 
            "model_used"
        ])
        
        # Save to CSV with UTF-8 encoding and BOM
        df.to_csv(st.session_state.csv_filename, index=False, encoding='utf-8-sig')

# Initialize the CSV file
initialize_csv()

# Create tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["錯字檢查", "課文學習", "語音朗讀", "複習", "工具"])

# First Tab: Typo Checker (OCR Text Correction)
with tab1:
    st.header("📖 課文")
    
    def update_text_input_tab1():
        st.session_state.text_input_tab1 = st.session_state.text_input_widget_tab1
    
    text_input = st.text_area(
        "Paste your Chinese text here (Traditional or Simplified):", 
        value=st.session_state.text_input_tab1,
        key="text_input_widget_tab1",
        on_change=update_text_input_tab1
    )

    if st.session_state.text_input_tab1:
        text_trad, text_simp = normalize_input(st.session_state.text_input_tab1)
        Lookup_text = text_trad

    if st.button("🔍 檢查課文是否有錯字", key="check_typo_tab1"):
        if not st.session_state.text_input_tab1:
            st.warning("Please enter some text first.")
        else:
            prompt_check = f"""
            I just copied the following Chinese text from an image I took using OCR, I will need to study this text for my homework and want to make sure the OCR has not picked up the wrong words.
            Please carefully review the passage for any incorrect, uncommon, or misused characters:
            \"{text_trad}\"
            If there are any issues, list the typo in a markdown table format with the following columns:
            Column 1 - heading = "錯字", content = problematic character or phrase
            Column 2 - heading = "正確", content = correct character or phrase
            Column 3 - heading = "解釋", content = Using Chinese, explain why they are incorrect or unusual

            Please respond only in Traditional Chinese.
            If the text is clean, simply respond: "此課文沒有錯字 in column 1"
            """
            try:
                response_check = call_ai_model(prompt_check)
                st.subheader("錯字檢查結果：")
                st.write(response_check)

                st.session_state.typo_list = []
                st.session_state.ai_correct_list = []
                st.session_state.user_correct_list = []
                
                if is_traditional(st.session_state.text_input_tab1, text_trad, text_simp):
                    st.session_state.original_text = text_trad
                else:
                    st.session_state.original_text = text_simp

                for line in response_check.splitlines():
                    if "|" in line and not line.startswith("| 錯字") and not line.startswith("|錯字"):
                        parts = line.split("|")
                        if len(parts) >= 3:
                            typo = parts[1].strip()
                            correct = parts[2].strip()

                            if typo and correct and typo != "---" and correct != "---" and typo != "此課文沒有錯字":
                                st.session_state.typo_list.append(typo)
                                st.session_state.ai_correct_list.append(correct)
                                st.session_state.user_correct_list.append(correct)

                if not st.session_state.typo_list:
                    st.info("此課文沒有錯字")

            except Exception as e:
                st.error(f"❌ An unexpected error occurred: {e}")

    if st.session_state.typo_list:
        st.subheader("🛠️ 錯字修正選項")
        
        for i, (typo, ai_correct) in enumerate(zip(st.session_state.typo_list, st.session_state.ai_correct_list)):
            col1, col2 = st.columns([1, 2])
            with col1:      
                st.markdown(f"**錯字:** {typo}")
            with col2:
                def update_user_correction(i=i):
                    st.session_state.user_correct_list[i] = st.session_state[f"correction_{i}"]
                
                user_input = st.text_input(
                    f"建議修正: {ai_correct}", 
                    value=st.session_state.user_correct_list[i], 
                    key=f"correction_{i}",
                    on_change=update_user_correction
                )

        st.write("如果你想刪除錯字，就留空。")

        highlighted_original = st.session_state.original_text
        for typo in st.session_state.typo_list:
            highlighted_original = highlighted_original.replace(typo, f"<mark style='background-color: #ffcccc'>{typo}</mark>")

        user_corrected_text = st.session_state.original_text
        
        for i, (typo, user_word, ai_word) in enumerate(zip(st.session_state.typo_list, 
                                                          st.session_state.user_correct_list, 
                                                          st.session_state.ai_correct_list)):
            if user_word:
                if user_word == ai_word:
                    user_corrected_text = user_corrected_text.replace(
                        typo, 
                        f"<mark style='background-color: #ffffcc'>{user_word}</mark>"
                    )
                else:
                    user_corrected_text = user_corrected_text.replace(
                        typo, 
                        f"<mark style='background-color: #ccffcc'>{user_word}</mark>"
                    )
            else:
                user_corrected_text = user_corrected_text.replace(typo, "")

        col1, col2 = st.columns([1, 1])
        with col1:
            st.subheader("原文：")
            st.markdown(highlighted_original, unsafe_allow_html=True)
            st.caption("紅色標記：可能錯誤的字詞")
        with col2:
            st.subheader("修正後課文")
            st.markdown(user_corrected_text, unsafe_allow_html=True)
            st.caption("黃色標記：AI建議的修正 | 綠色標記：您修改的修正")

# Second Tab: Dictionary and Study Tools
with tab2:
    st.header("📘 課文")
    
    def update_text_input_tab2():
        st.session_state.text_input_tab2 = st.session_state.text_input_widget_tab2
    
    def update_words_input_tab2():
        st.session_state.words_input_tab2 = st.session_state.words_input_widget_tab2
        # Clear dictionary data when keywords change
        st.session_state.dictionary_data = None
        
    def update_tts_input_tab2():
        st.session_state.tts_input_tab2 = st.session_state.tts_input_widget_tab2
    
    text_input_tab2 = st.text_area(
        "Paste your Chinese text here (Traditional or Simplified):", 
        value=st.session_state.text_input_tab2,
        key="text_input_widget_tab2",
        on_change=update_text_input_tab2
    )
    
    if st.session_state.text_input_tab2:
        text_trad_tab2, text_simp_tab2 = normalize_input(st.session_state.text_input_tab2)
        Lookup_text_tab2 = text_trad_tab2
    
    if st.session_state.text_input_tab2:
        if st.session_state.words_input_tab2:
            highlighted_trad, highlighted_simp = highlight_words_dual(text_trad_tab2, text_simp_tab2, st.session_state.words_input_tab2)
        else:
            highlighted_trad = text_trad_tab2
            highlighted_simp = text_simp_tab2

        col1, col2 = st.columns([1, 1])
        with col1:
            st.subheader("Traditional Chinese")
            st.markdown(highlighted_trad, unsafe_allow_html=True)
        with col2:
            st.subheader("Simplified Chinese")
            st.markdown(highlighted_simp, unsafe_allow_html=True)
    
    if st.button("辨認關鍵詞語", key="identify_keywords_tab2"):
        if not st.session_state.text_input_tab2:
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
                st.header(f"{st.session_state.selected_model} 辨認關鍵詞:")
                st.write(response_words)
                
                st.session_state.words_input_tab2 = response_words
                # Also update the widget value to keep them in sync
                st.session_state.words_input_widget_tab2 = response_words
                
            except Exception as e:
                st.error(f"❌ An unexpected error occurred: {e}")
    
    st.header("📘 字典解釋 - 關鍵詞語")
    words_input_tab2 = st.text_area(
        "Enter Chinese words to look up (comma-separated):", 
        value=st.session_state.words_input_tab2,
        key="words_input_widget_tab2",
        on_change=update_words_input_tab2  # This now clears dictionary data when changed
    )

    if st.button("字典", key="dictionary_tab2"):
        if not st.session_state.words_input_tab2:
            st.warning("Please enter some words to look up first.")
        else:
            prompt_dict = f"""
            You are a Chinese native speaker, being a language tutor for kids 8-10 years old.

            Please explain the words in "{st.session_state.words_input_tab2}" in Traditional Chinese using Markdown table format with the following columns:

            Column 1: Heading = "繁體", content = the original character in traditional chinese
            Column 2: Heading = "簡體", content = convert the column 1 characters into simplified chinese
            Column 3: Heading = "拼音", content = Mandarin pinyin  
            Column 4: Heading = "解釋", content = A beginner-friendly, simple definition  
            Column 5 & 6: Heading = "例句", content = An example sentence, show in both traditional (column 5) and simplified chinese

            Respond only in Traditional Chinese. Format your response as a Markdown table.
            """
            try:
                response_dict = call_ai_model(prompt_dict)
                st.session_state.dictionary_data = response_dict
                st.session_state.model_used = st.session_state.selected_model
                st.subheader(f"{st.session_state.selected_model} Dictionary:")
                st.write(response_dict)
            except Exception as e:
                st.error(f"❌ An unexpected error occurred: {e}")
    
    # Display dictionary response if it exists
    if st.session_state.dictionary_data:
        st.subheader(f"{st.session_state.selected_model} Dictionary(to be exported):")
        st.markdown(st.session_state.dictionary_data)
        
        # Export section
        st.header("💾 匯出學習資料")
        
        # Create a container for the export form
        export_container = st.container()
        with export_container:
            col1, col2, col3 = st.columns(3)
            with col1:
                book_title = st.text_input("書名", key="book_title")
            with col2:
                article_title = st.text_input("文章標題", key="article_title")
            with col3:
                page_number = st.text_input("頁碼", key="page_number")
            
            # Export button and duplicate handling logic
            
            if st.button("匯出到數據庫(CSV)", key="export_csv"):
                if not book_title or not article_title:
                    st.error("請填寫書名和文章標題。")
                else:
                    # Check if record already exists
                    if check_record_exists(book_title, article_title, st.session_state.model_used):
                        st.warning("已存在相同書名、文章標題和AI模型的記錄。")
                        
                        # Create a confirmation dialog
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if st.button("覆蓋現有記錄", key="overwrite_confirm"):
                                # Remove the old record and add the new one
                                existing_data = load_csv_data()
                                updated_data = [
                                    record for record in existing_data 
                                    if not (record["book_title"].strip().lower() == book_title.strip().lower() and 
                                            record["article_title"].strip().lower() == article_title.strip().lower() and 
                                            record["model_used"].strip().lower() == st.session_state.model_used.strip().lower())
                                ]
                                
                                # Add the new record (convert to Traditional Chinese)
                                cc_s2t = OpenCC('s2t')  # Simplified to Traditional converter
                                trad_original = cc_s2t.convert(st.session_state.text_input_tab2)
                                trad_keywords = cc_s2t.convert(st.session_state.words_input_tab2)
                                
                                updated_data.append({
                                    "export_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "book_title": book_title.strip(),
                                    "article_title": article_title.strip(),
                                    "page_number": page_number.strip(),
                                    "original_text": trad_original,
                                    "keywords": trad_keywords,
                                    "dictionary_data": st.session_state.dictionary_data,
                                    "model_used": st.session_state.model_used
                                })
                                
                                # Save updated data
                                df = pd.DataFrame(updated_data)
                                df.to_csv(st.session_state.csv_filename, index=False, encoding='utf-8-sig')
                                st.success(f"記錄已更新！數據庫中現在有 {len(updated_data)} 條記錄。")
                                st.rerun()
                        
                        with col2:
                            if st.button("使用不同名稱保存", key="save_different"):
                                # This will trigger the new name inputs below
                                st.session_state.show_new_name_inputs = True
                        
                        with col3:
                            if st.button("取消操作", key="cancel_export"):
                                st.session_state.show_new_name_inputs = False
                                st.rerun()
                        
                        # Show new name inputs if requested
                        if st.session_state.get('show_new_name_inputs', False):
                            new_book_title = st.text_input("新書名", value=book_title, key="new_book_title")
                            new_article_title = st.text_input("新文章標題", value=article_title, key="new_article_title")
                            
                            if st.button("確認保存", key="save_with_new_name"):
                                # Convert to Traditional Chinese before saving
                                cc_s2t = OpenCC('s2t')  # Simplified to Traditional converter
                                trad_original = cc_s2t.convert(st.session_state.text_input_tab2)
                                trad_keywords = cc_s2t.convert(st.session_state.words_input_tab2)
                                
                                record_count = save_to_csv(
                                    trad_original,
                                    trad_keywords,
                                    st.session_state.dictionary_data,
                                    st.session_state.model_used,
                                    new_book_title,
                                    new_article_title,
                                    page_number
                                )
                                st.success(f"資料已成功匯出！數據庫中現在有 {record_count} 條記錄。")
                                st.session_state.show_new_name_inputs = False
                                st.rerun()
                    else:
                        # Convert to Traditional Chinese before saving
                        cc_s2t = OpenCC('s2t')  # Simplified to Traditional converter
                        trad_original = cc_s2t.convert(st.session_state.text_input_tab2)
                        trad_keywords = cc_s2t.convert(st.session_state.words_input_tab2)
                        
                        record_count = save_to_csv(
                            trad_original,
                            trad_keywords,
                            st.session_state.dictionary_data,
                            st.session_state.model_used,
                            book_title,
                            article_title,
                            page_number
                        )
                        st.success(f"資料已成功匯出！數據庫中現在有 {record_count} 條記錄。")
                        st.rerun()


# Third Tab: Text-to-Speech
# Third Tab: Text-to-Speech
with tab3:
    # 📢 Text-to-Speech Section
    st.header("🗣️ 語音朗讀")
    
    # Custom CSS to make audio player sticky with taller scrollable text area
    st.markdown("""
    <style>
    .sticky-audio-player {
        position: sticky;
        top: 10px;
        background-color: white;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        z-index: 1000;
        border: 1px solid #e6e6e6;
        margin-bottom: 20px;
    }
    .audio-player-header {
        font-weight: bold;
        margin-bottom: 10px;
        color: #1f77b4;
    }
    .scrollable-text {
        max-height: 300px;  /* Increased from 150px to 250px */
        min-height: 100px;  /* Added minimum height */
        overflow-y: auto;
        margin-bottom: 15px;
        padding: 10px;
        border: 1px solid #e6e6e6;
        border-radius: 4px;
        background-color: #f9f9f9;
        line-height: 1.6;  /* Added for better readability */
    }
    </style>
    """, unsafe_allow_html=True)
        
    # Text area for TTS input
    tts_input_tab2 = st.text_area(
        "輸入你想朗讀的中文句子（可用繁體或簡體）", 
        value=st.session_state.tts_input_tab2,
        key="tts_input_widget_tab2",
        on_change=update_tts_input_tab2,
        height=150,
        help="輸入要朗讀的文字，然後選擇語音類型並點擊朗讀按鈕"
    )

    # Create two columns for voice selection
    col_voice_cantonese, col_voice_mandarin = st.columns([1, 1])

    with col_voice_cantonese:
        if st.session_state.available_cantonese_voices:
            voice_options_cantonese = {v['name']: f"{v['description']} ({v['gender']})" for v in st.session_state.available_cantonese_voices}
            selected_cantonese_voice = st.selectbox(
                "選擇粵語語音",
                options=list(voice_options_cantonese.keys()),
                format_func=lambda x: voice_options_cantonese[x],
                key="cantonese_voice_selector"
            )
            st.session_state.selected_cantonese_voice = selected_cantonese_voice

    with col_voice_mandarin:
        if st.session_state.available_mandarin_voices:
            voice_options_mandarin = {v['name']: f"{v['description']} ({v['gender']})" for v in st.session_state.available_mandarin_voices}
            selected_mandarin_voice = st.selectbox(
                "選擇普通話語音",
                options=list(voice_options_mandarin.keys()),
                format_func=lambda x: voice_options_mandarin[x],
                key="mandarin_voice_selector"
            )
            st.session_state.selected_mandarin_voice = selected_mandarin_voice

    # Initialize session state for audio data if not exists
    if 'cantonese_audio_data' not in st.session_state:
        st.session_state.cantonese_audio_data = None
    if 'mandarin_audio_data' not in st.session_state:
        st.session_state.mandarin_audio_data = None
    if 'audio_text' not in st.session_state:
        st.session_state.audio_text = None

    # Single button to generate both audio types
    if st.button("生成雙語發音", key="generate_both_audio", use_container_width=True):
        if not st.session_state.tts_input_tab2:
            st.warning("請輸入要朗讀的文字")
        else:
            # Generate Cantonese audio
            cantonese_audio_file = speak_text_azure(st.session_state.tts_input_tab2, voice_id=st.session_state.selected_cantonese_voice)
            if cantonese_audio_file:
                with open(cantonese_audio_file, "rb") as f:
                    st.session_state.cantonese_audio_data = f.read()
                try:
                    os.unlink(cantonese_audio_file)
                except:
                    pass

            # Generate Mandarin audio
            mandarin_audio_file = speak_text_azure(st.session_state.tts_input_tab2, voice_id=st.session_state.selected_mandarin_voice)
            if mandarin_audio_file:
                with open(mandarin_audio_file, "rb") as f:
                    st.session_state.mandarin_audio_data = f.read()
                try:
                    os.unlink(mandarin_audio_file)
                except:
                    pass

            # Store text for display
            st.session_state.audio_text = st.session_state.tts_input_tab2
            st.rerun()

    # Display the audio players if audio data exists
    if st.session_state.cantonese_audio_data and st.session_state.mandarin_audio_data:
        # Create a container for the audio player with the original sticky style
        with st.container():
            #st.markdown('<div class="sticky-audio-player">', unsafe_allow_html=True)
            
            # Display audio information
            #st.markdown('<div class="audio-player-header">當前音頻播放</div>', unsafe_allow_html=True)
            
            # Display scrollable text
            st.markdown("**朗讀文本:**")
            st.markdown(f'<div class="scrollable-text">{st.session_state.audio_text}</div>', 
                       unsafe_allow_html=True)
            
            # Display both audio players
            col1, col2 = st.columns(2)
            
            with col1:
                # Get Cantonese voice description
                cantonese_voice_desc = next((f"{v['description']} ({v['gender']})" for v in st.session_state.available_cantonese_voices 
                                          if v['name'] == st.session_state.selected_cantonese_voice), 
                                         st.session_state.selected_cantonese_voice)
                
                st.info(f"粵語發音 - {cantonese_voice_desc}")
                st.audio(st.session_state.cantonese_audio_data, format="audio/wav")
            
            with col2:
                # Get Mandarin voice description
                mandarin_voice_desc = next((f"{v['description']} ({v['gender']})" for v in st.session_state.available_mandarin_voices 
                                          if v['name'] == st.session_state.selected_mandarin_voice), 
                                         st.session_state.selected_mandarin_voice)
                
                st.info(f"普通話發音 - {mandarin_voice_desc}")
                st.audio(st.session_state.mandarin_audio_data, format="audio/wav")
            
            # Add a button to clear the audio
            if st.button("清除音頻", key="clear_audio"):
                st.session_state.cantonese_audio_data = None
                st.session_state.mandarin_audio_data = None
                st.session_state.audio_text = None
                st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)

# Fourth Tab: Revision
with tab4:
    st.header("📚 複習")
    
    # Always show the download full database button at the top
    if os.path.exists(st.session_state.csv_filename):
        with open(st.session_state.csv_filename, "rb") as f:
            csv_data = f.read()
        
        # Add BOM (Byte Order Mark) for Excel compatibility
        bom = b'\xef\xbb\xbf'
        csv_data_with_bom = bom + csv_data
        
        st.download_button(
            label="下載完整數據庫(CSV)",
            data=csv_data_with_bom,
            file_name=st.session_state.csv_filename,
            mime="text/csv; charset=utf-8",
            key="download_full_db_revision"
        )
    
    # Load data from CSV
    records = load_csv_data()
    
    if not records:
        st.info("尚未有任何匯出的課文資料。請先在「課文學習」標籤中匯出資料。")
    else:
        # Create filters
        st.subheader("篩選選項")
        col1, col2, col3, col4 = st.columns([4,8,1.5,2])
        
        # Get unique values for filters
        book_titles = sorted(set(record['book_title'] for record in records if record['book_title']))
        
        # Get available articles based on selected book
        if st.session_state.filter_book_title and st.session_state.filter_book_title != "所有":
            available_articles = sorted(set(
                record['article_title'] for record in records 
                if record['book_title'] == st.session_state.filter_book_title and record['article_title']
            ))
        else:
            available_articles = sorted(set(record['article_title'] for record in records if record['article_title']))
        
        # Get available pages based on selected book and article
        if (st.session_state.filter_book_title and st.session_state.filter_book_title != "所有" and
            st.session_state.filter_article_title and st.session_state.filter_article_title != "所有"):
            available_pages = sorted(set(
                record['page_number'] for record in records 
                if (record['book_title'] == st.session_state.filter_book_title and
                    record['article_title'] == st.session_state.filter_article_title and
                    record['page_number'])
            ))
        else:
            available_pages = sorted(set(record['page_number'] for record in records if record['page_number']))
        
        # Get available models based on selected book, article and page
        if (st.session_state.filter_book_title and st.session_state.filter_book_title != "所有" and
            st.session_state.filter_article_title and st.session_state.filter_article_title != "所有" and
            st.session_state.filter_page_number and st.session_state.filter_page_number != "所有"):
            available_models = sorted(set(
                record['model_used'] for record in records 
                if (record['book_title'] == st.session_state.filter_book_title and
                    record['article_title'] == st.session_state.filter_article_title and
                    record['page_number'] == st.session_state.filter_page_number and
                    record['model_used'])
            ))
        else:
            available_models = sorted(set(record['model_used'] for record in records if record['model_used']))
        
        with col1:
            # Book filter
            new_book_filter = st.selectbox(
                "書名", 
                options=["所有"] + book_titles,
                index=0 if st.session_state.filter_book_title == "所有" else book_titles.index(st.session_state.filter_book_title) + 1,
                key="book_filter"
            )
            
            # If book filter changed, reset dependent filters
            if new_book_filter != st.session_state.filter_book_title:
                st.session_state.filter_book_title = new_book_filter
                st.session_state.filter_article_title = "所有"
                st.session_state.filter_page_number = "所有"
                st.session_state.filter_model_used = "所有"
                st.rerun()
        
        with col2:
            # Article filter
            new_article_filter = st.selectbox(
                "文章標題", 
                options=["所有"] + available_articles,
                index=0 if st.session_state.filter_article_title == "所有" else available_articles.index(st.session_state.filter_article_title) + 1,
                key="article_filter"
            )
            
            # If article filter changed, reset dependent filters
            if new_article_filter != st.session_state.filter_article_title:
                st.session_state.filter_article_title = new_article_filter
                st.session_state.filter_page_number = "所有"
                st.session_state.filter_model_used = "所有"
                st.rerun()
        
        with col3:
            # Page filter
            new_page_filter = st.selectbox(
                "頁碼", 
                options=["所有"] + available_pages,
                index=0 if st.session_state.filter_page_number == "所有" else available_pages.index(st.session_state.filter_page_number) + 1,
                key="page_filter"
            )
            
            # If page filter changed, reset dependent filters
            if new_page_filter != st.session_state.filter_page_number:
                st.session_state.filter_page_number = new_page_filter
                st.session_state.filter_model_used = "所有"
                st.rerun()
        
        with col4:
            # Model filter
            st.session_state.filter_model_used = st.selectbox(
                "AI模型", 
                options=["所有"] + available_models,
                index=0 if st.session_state.filter_model_used == "所有" else available_models.index(st.session_state.filter_model_used) + 1,
                key="model_filter"
            )
        
        # Filter records based on selections
        filtered_records = records
        
        if st.session_state.filter_book_title != "所有":
            filtered_records = [r for r in filtered_records if r['book_title'] == st.session_state.filter_book_title]
        
        if st.session_state.filter_article_title != "所有":
            filtered_records = [r for r in filtered_records if r['article_title'] == st.session_state.filter_article_title]
        
        if st.session_state.filter_page_number != "所有":
            filtered_records = [r for r in filtered_records if r['page_number'] == st.session_state.filter_page_number]
        
        if st.session_state.filter_model_used != "所有":
            filtered_records = [r for r in filtered_records if r['model_used'] == st.session_state.filter_model_used]
        
        if not filtered_records:
            st.warning("沒有符合篩選條件的記錄。")
        else:
            # Create a selection dropdown for filtered texts
            export_options = [f"{record['book_title']} - {record['article_title']} (頁 {record['page_number']}) - {record['model_used']} - {record['export_date']}" 
                             for record in filtered_records]
            
            selected_export = st.selectbox("選擇要複習的課文", options=export_options)
            
            if selected_export:
                # Find the selected export data
                selected_index = export_options.index(selected_export)
                selected_data = filtered_records[selected_index]
                
                # Display the text information
                st.subheader("課文資訊")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.info(f"**書名:** {selected_data['book_title']}")
                with col2:
                    st.info(f"**文章標題:** {selected_data['article_title']}")
                with col3:
                    st.info(f"**頁碼:** {selected_data['page_number']}")
                with col4:
                    st.info(f"**AI模型:** {selected_data['model_used']}")
                
                # Display keywords
                st.subheader("關鍵詞語")
                st.write(selected_data['keywords'])
                
                # Display the original text with highlighted keywords
                st.subheader("課文內容（關鍵詞高亮顯示）")
                text_trad, text_simp = normalize_input(selected_data['original_text'])
                highlighted_trad, highlighted_simp = highlight_words_dual(text_trad, text_simp, selected_data['keywords'])
                
                col1, col2 = st.columns([1, 1])
                with col1:
                    st.markdown("**繁體中文**")
                    st.markdown(highlighted_trad, unsafe_allow_html=True)
                with col2:
                    st.markdown("**簡體中文**")
                    st.markdown(highlighted_simp, unsafe_allow_html=True)
                
                # Display dictionary explanation
                st.subheader("字典解釋")
                st.markdown(f"*由 {selected_data['model_used']} 生成*")
                st.markdown(selected_data['dictionary_data'])
                
                # Only show the PDF note, remove the CSV download button
                st.info("如果你需要下載這個工作紙,您可以將此頁面打印為PDF。")

# Fifth Tab: Helpful Tools
with tab5:
    st.header("🛠️ 工具")
    
    # Create subtabs for the different tools
    tool_tabs = st.tabs(["繁簡轉換", "英文翻譯", "雙語發音"])
    
    # First Tool: Traditional-Simplified Conversion with Pinyin
    with tool_tabs[0]:
        st.subheader("繁簡轉換與拼音")
        
        # Input for conversion
        conversion_input = st.text_area(
            "輸入中文文本（繁體或簡體）:",
            height=100,
            key="conversion_input",
            help="輸入要轉換的文本，系統會顯示繁體、簡體和拼音版本"
        )
        
        if st.button("轉換", key="convert_button"):
            if conversion_input:
                # Use AI to generate the conversion table with tone-marked pinyin
                conversion_prompt = f"""
                Please convert the following Chinese text and provide the results in a Markdown table format with three columns:
                Column 1: 繁體
                Column 2: 簡體  
                Column 3: 拼音
                
                Text to convert: \"{conversion_input}\"
                
                Do not split the text, keep the original sentence structure.
                Please ensure the pinyin uses proper tone marks (e.g., mā, má, mǎ, mà) rather than number notation.
                """
                
                conversion_output = call_ai_model(conversion_prompt)
                
                # Display results
                st.markdown("### 轉換結果")
                st.markdown(conversion_output)
                
                
               
    # Second Tool: English Translation
    with tool_tabs[1]:
        st.subheader("英文翻譯")
        
        # Input for translation
        translation_input = st.text_area(
            "輸入中文文本（繁體或簡體）:",
            height=100,
            key="translation_input",
            help="輸入要翻譯成英文的中文文本"
        )
        
        if st.button("翻譯", key="translate_button"):
            if translation_input:
                # Get English translation using AI
                translation_prompt = f"""
                Please translate the following Chinese text to English:
                \"{translation_input}\"
                
                Provide a clear and accurate translation. If the text contains idioms or cultural references, 
                please provide both a literal translation and an explanation of the meaning in English.
                """
                
                translation_output = call_ai_model(translation_prompt)
                
                # Display translation in a scrollable container
                st.markdown("### 英文翻譯")
                st.markdown(f'<div style="border: 1px solid #e6e6e6; padding: 10px; border-radius: 5px; max-height: 200px; overflow-y: auto; white-space: pre-wrap;">{translation_output}</div>', 
                           unsafe_allow_html=True)
            else:
                st.warning("請輸入要翻譯的文本")
    
    # Third Tool: Dual Language TTS
    with tool_tabs[2]:
        st.subheader("雙語發音")
        
        # Input for TTS
        tts_input = st.text_area(
            "輸入要朗讀的文本:",
            height=60,  # Reduced height to save space
            key="tts_tool_input",
            help="輸入要生成粵語和普通話發音的文本"
        )
        
        # Initialize session state for audio data if not exists
        if 'cantonese_audio' not in st.session_state:
            st.session_state.cantonese_audio = None
        if 'mandarin_audio' not in st.session_state:
            st.session_state.mandarin_audio = None
        if 'tts_text' not in st.session_state:
            st.session_state.tts_text = None

        # In the 雙語發音 section of tab5, add these dropdowns before the buttons
        col_voice_cantonese, col_voice_mandarin = st.columns(2)

        with col_voice_cantonese:
            if st.session_state.available_cantonese_voices:
                voice_options_cantonese = {v['name']: f"{v['description']} ({v['gender']})" for v in st.session_state.available_cantonese_voices}
                selected_cantonese_voice = st.selectbox(
                    "選擇粵語語音",
                    options=list(voice_options_cantonese.keys()),
                    format_func=lambda x: voice_options_cantonese[x],
                    key="cantonese_voice_selector_tab5"
                )
                st.session_state.selected_cantonese_voice = selected_cantonese_voice

        with col_voice_mandarin:
            if st.session_state.available_mandarin_voices:
                voice_options_mandarin = {v['name']: f"{v['description']} ({v['gender']})" for v in st.session_state.available_mandarin_voices}
                selected_mandarin_voice = st.selectbox(
                    "選擇普通話語音",
                    options=list(voice_options_mandarin.keys()),
                    format_func=lambda x: voice_options_mandarin[x],
                    key="mandarin_voice_selector_tab5"
                )
                st.session_state.selected_mandarin_voice = selected_mandarin_voice
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("生成發音", key="generate_tts_button", use_container_width=True):
                if tts_input:
                    # Store the text
                    st.session_state.tts_text = tts_input
                    
                    # Generate Cantonese audio
                    cantonese_audio_file = speak_text_azure(tts_input, voice_id=st.session_state.selected_cantonese_voice)
                    if cantonese_audio_file:
                        with open(cantonese_audio_file, "rb") as f:
                            st.session_state.cantonese_audio = f.read()
                        try:
                            os.unlink(cantonese_audio_file)
                        except:
                            pass
                    
                    # Generate Mandarin audio
                    mandarin_audio_file = speak_text_azure(tts_input, voice_id=st.session_state.selected_mandarin_voice)
                    if mandarin_audio_file:
                        with open(mandarin_audio_file, "rb") as f:
                            st.session_state.mandarin_audio = f.read()
                        try:
                            os.unlink(mandarin_audio_file)
                        except:
                            pass
                    
                    # Don't show success message to save space
                    st.rerun()
                else:
                    st.warning("請輸入要朗讀的文本")
        
        with col2:
            if st.button("清除音頻", key="clear_tts_audio", use_container_width=True):
                st.session_state.cantonese_audio = None
                st.session_state.mandarin_audio = None
                st.session_state.tts_text = None
                st.rerun()
        
        # Display audio players if audio data exists
        if st.session_state.cantonese_audio and st.session_state.mandarin_audio:
            # Display the text being read at the top
            st.markdown(f"**朗讀文本:** {st.session_state.tts_text}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Get Cantonese voice description
                cantonese_voice_desc = next((f"{v['description']} ({v['gender']})" for v in st.session_state.available_cantonese_voices 
                                          if v['name'] == st.session_state.selected_cantonese_voice), 
                                         st.session_state.selected_cantonese_voice)
                
                st.info(f"粵語發音 - {cantonese_voice_desc}")
                st.audio(st.session_state.cantonese_audio, format="audio/wav")
            
            with col2:
                # Get Mandarin voice description
                mandarin_voice_desc = next((f"{v['description']} ({v['gender']})" for v in st.session_state.available_mandarin_voices 
                                          if v['name'] == st.session_state.selected_mandarin_voice), 
                                         st.session_state.selected_mandarin_voice)
                
                st.info(f"普通話發音 - {mandarin_voice_desc}")
                st.audio(st.session_state.mandarin_audio, format="audio/wav")