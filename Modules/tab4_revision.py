# tab4_revision.py
import streamlit as st
from Modules.sheets import load_gs_data_cached
from Modules.storage import save_to_temp_file, load_from_temp_file
from Modules.text_utils import normalize_input_cached, highlight_words_dual

def render():
    st.header("📚 複習")

    if 'copy_success' not in st.session_state:
        st.session_state.copy_success = False

    records = load_gs_data_cached()
    if not records:
        st.info("尚未有任何匯出的課文資料。請先在「課文學習」標籤中匯出資料。")
        return

    # Load current filter values
    filter_keys = ["book_title", "article_title", "page_number", "model_used"]
    current_filters = {
        key: load_from_temp_file(f"filter_{key}.txt", "所有") 
        for key in filter_keys
    }

    # 确保所有页面值都是字符串类型，以便比较
    for record in records:
        if 'page_number' in record and record['page_number'] is not None:
            record['page_number'] = str(record['page_number'])

    # 根据当前筛选条件动态计算可用选项
    def get_filtered_records(records, filters):
        filtered = records
        for key, value in filters.items():
            if value != "所有":
                filtered = [r for r in filtered if r[key] == value]
        return filtered

    # 根据当前筛选条件计算每个筛选器的可用选项
    def get_filter_options(records, current_filters, exclude_key=None):
        options = {}
        
        for key in filter_keys:
            if key == exclude_key:
                continue
                
            temp_records = records.copy()
            # 应用其他筛选条件
            for k, v in current_filters.items():
                if k != key and k != exclude_key and v != "所有":
                    temp_records = [r for r in temp_records if r[k] == v]
            
            # 获取当前筛选器的可用选项
            if key == 'page_number':
                options[key] = ["所有"] + sorted(
                    set(r[key] for r in temp_records if r[key]), 
                    key=lambda x: int(x) if x.isdigit() else x
                )
            else:
                options[key] = ["所有"] + sorted(set(r[key] for r in temp_records if r[key]))
        
        return options

    # 获取所有筛选器的可用选项
    filter_options = get_filter_options(records, current_filters)

    # 确保当前值在可用选项中，如果不在则重置为"所有"
    for key in filter_keys:
        if current_filters[key] not in filter_options[key]:
            current_filters[key] = "所有"
            save_to_temp_file("所有", f"filter_{key}.txt")

    st.subheader("篩選選項")
    cols = st.columns(4)
    
    # 使用会话状态来跟踪筛选器的变化
    if 'filter_changed' not in st.session_state:
        st.session_state.filter_changed = False
    
    # 显示筛选器并处理变化
    filter_labels = {
        "book_title": "書名",
        "article_title": "文章標題", 
        "page_number": "頁碼",
        "model_used": "AI模型"
    }
    
    for i, key in enumerate(filter_keys):
        with cols[i]:
            options = filter_options[key]
            idx = options.index(current_filters[key]) if current_filters[key] in options else 0
            new_value = st.selectbox(filter_labels[key], options=options, index=idx, key=f"{key}_filter")
            
            if new_value != current_filters[key]:
                save_to_temp_file(new_value, f"filter_{key}.txt")
                st.session_state.filter_changed = True
    
    # 如果有筛选器变化，重新运行
    if st.session_state.filter_changed:
        st.session_state.filter_changed = False
        st.rerun()

    # 获取筛选后的记录
    filtered_records = get_filtered_records(records, current_filters)

    # Display filtered results
    if not filtered_records:
        st.warning("沒有符合篩選條件的記錄。")
        return

    options = [f"{r['book_title']} - {r['article_title']} (頁 {r['page_number']}) - {r['model_used']} - {r['export_date']}" for r in filtered_records]
    selected = st.selectbox("選擇要複習的課文", options=options)
    if not selected:
        return
    idx = options.index(selected)
    data = filtered_records[idx]

    if st.button("複製到<<課文學習>>和<<語音朗讀>>", key="copy_to_other_tabs"):
    # Save data to temporary files for other tabs
        save_to_temp_file(data['original_text_trad'], "tab2_text.txt")
        save_to_temp_file(data['keywords'], "tab2_words.txt")
        save_to_temp_file(data['original_text_trad'], "tts_input.txt")
        
        # Set success state
        st.session_state.copy_success = True
        
        # Force a rerun to ensure highlighting works
        st.session_state.force_highlight = True
        st.success("複製成功！")
        
        # Set active tab to Tab 2
        st.session_state.active_tab = "課文學習"
        st.rerun()
             

    st.subheader("課文資訊")
    c1, c2 = st.columns(2)
    with c1:
        st.info(f"**書名:** {data['book_title']}")
        st.info(f"**文章標題:** {data['article_title']}")
    with c2:
        st.info(f"**頁碼:** {data['page_number']}")
        st.info(f"**AI模型:** {data['model_used']}")

    
    
    st.subheader("關鍵詞語")
    st.write(data['keywords'])

    st.subheader("課文內容（關鍵詞高亮顯示）")
    text_trad, text_simp = normalize_input_cached(data['original_text_trad'])
    highlighted_trad, highlighted_simp = highlight_words_dual(text_trad, text_simp, data['keywords'])
    t1, t2 = st.tabs(["繁體中文", "簡體中文"])
    with t1:
        st.markdown(highlighted_trad, unsafe_allow_html=True)
    with t2:
        st.markdown(highlighted_simp, unsafe_allow_html=True)

    st.subheader("字典解釋")
    st.markdown(f"*由 {data['model_used']} 生成*")
    st.markdown(data['dictionary_data'])
    st.info("如果你需要下載這個工作紙,您可以將此頁面打印為PDF。")
