import streamlit as st
from core.logging_config import configure_logging
from config.theme import CUSTOM_CSS
from ui.header import render_top_bar
from views.overview import render_global_overview
from views.macro import render_global_macro
from views.shipping import render_shipping
from views.regime import render_market_regime
from views.security import render_security_report
from views.methodology import render_methodology
from views.strategy_lab import render_strategy_lab
from views.screener import render_market_screener

configure_logging()

st.set_page_config(page_title="Cyclical Global Macro Terminal", page_icon="📊", layout="wide", initial_sidebar_state="expanded")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
render_top_bar()

with st.sidebar:
    st.markdown("<div class='terminal-header'>NAVIGATION</div>", unsafe_allow_html=True)
    page = st.radio("Page", ["GLOBAL OVERVIEW", "GLOBAL MACRO", "MARITIME INTELLIGENCE", "MARKET REGIME", "MARKET SCREENER", "SECURITY REPORT", "STRATEGY LAB", "METHODOLOGY"], label_visibility="collapsed")
    st.divider()
    if st.button("CLEAR DATA CACHE", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

PAGES = {
    "GLOBAL OVERVIEW": render_global_overview,
    "GLOBAL MACRO": render_global_macro,
    "MARITIME INTELLIGENCE": render_shipping,
    "MARKET REGIME": render_market_regime,
    "MARKET SCREENER": render_market_screener,
    "SECURITY REPORT": render_security_report,
    "STRATEGY LAB": render_strategy_lab,
    "METHODOLOGY": render_methodology,
}
PAGES[page]()
