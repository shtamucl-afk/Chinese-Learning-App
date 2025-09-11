# _Chinese_Learning_App(Main).py
import streamlit as st
from Modules.session import init_session_state
from Modules.sheets import load_gs_data_cached
from Modules import tab1_typo_checker, tab2_study, tab3_tts, tab4_revision, tab5_tools

st.set_page_config(layout="wide")

def inject_css(path: str = "Modules/styles.css"):
    """Load a local CSS file once per session."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"CSS file not found at: {path}")

def render_header():
    col1, col2, col3 = st.columns([4, 2, 2])
    with col1:
        st.title("📚 Chinese Learning App")
    with col2:
        model_option = st.radio(
            "選擇AI模型",
            ["Gemini", "DeepSeek"],
            index=0 if st.session_state.get("selected_model") == "Gemini" else 1,
            key="model_selector",
            horizontal=True
        )
        st.session_state.selected_model = model_option
    with col3:
        if st.button("Clear Google Sheets Cache"):
            load_gs_data_cached.clear()
            st.rerun()

def main():
    init_session_state()

    # Always inject CSS
    inject_css("Modules/styles.css")

    render_header()

    # Initialize active tab from query params or default
    if "tab" in st.query_params:
        st.session_state.active_tab = st.query_params["tab"]
    elif "active_tab" not in st.session_state:
        st.session_state.active_tab = "錯字檢查"
    
    # Create tabs with consistent approach
    tab_titles = ["錯字檢查", "課文學習", "語音朗讀", "複習", "工具"]
    tabs = st.tabs(tab_titles)
    
    # Map tab titles to render functions
    tab_render_functions = {
        "錯字檢查": tab1_typo_checker.render,
        "課文學習": tab2_study.render,
        "語音朗讀": tab3_tts.render,
        "複習": tab4_revision.render,
        "工具": tab5_tools.render
    }
    
    # Render content for all tabs
    for i, tab_title in enumerate(tab_titles):
        with tabs[i]:
            # Always render the tab content
            tab_render_functions[tab_title]()
    
    # Update query params to match active tab
    if st.session_state.active_tab in tab_titles:
        st.query_params["tab"] = st.session_state.active_tab
    
    # JavaScript to handle tab changes
    st.components.v1.html(f"""
    <script>
        // Function to update the tab parameter
        function updateTabParam(tabName) {{
            const url = new URL(window.location);
            url.searchParams.set('tab', tabName);
            window.history.replaceState({{}}, '', url);
        }}
        
        // Wait for Streamlit to load
        var checkInterval = setInterval(function() {{
            const tabButtons = document.querySelectorAll('[data-testid="stTabButton"]');
            if (tabButtons.length > 0) {{
                clearInterval(checkInterval);
                
                // Add click event listeners to each tab button
                tabButtons.forEach((button, index) => {{
                    button.addEventListener('click', function() {{
                        const tabNames = {tab_titles};
                        if (index < tabNames.length) {{
                            updateTabParam(tabNames[index]);
                        }}
                    }});
                }});
            }}
        }}, 100);
    </script>
    """, height=0)

if __name__ == "__main__":
    main()
