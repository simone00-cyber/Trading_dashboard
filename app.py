from __future__ import annotations

import html
from importlib import import_module

import streamlit as st

from core.logging_config import configure_logging
from config.theme import CUSTOM_CSS
from ui.header import render_top_bar

configure_logging()

st.set_page_config(
    page_title="Cyclical Global Macro Terminal",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

PAGE_ROUTES = {
    "GLOBAL OVERVIEW": ("views.overview", "render_global_overview"),
    "GLOBAL MACRO": ("views.macro", "render_global_macro"),
    "MARITIME INTELLIGENCE": ("views.shipping", "render_shipping"),
    "MARKET SCREENER": ("views.screener", "render_market_screener"),
    "ASSET WORKSPACE": ("views.workspace", "render_asset_workspace"),
    "STRATEGY LAB": ("views.strategy_lab", "render_strategy_lab"),
    "METHODOLOGY": ("views.methodology", "render_methodology"),
}

st.session_state.setdefault("main_navigation", "GLOBAL OVERVIEW")
st.session_state.setdefault("page_transition_loading", False)


def _start_page_transition() -> None:
    st.session_state.page_transition_loading = True


def _transition_overlay(page_name: str):
    placeholder = st.empty()
    placeholder.markdown(
        f"""
        <div class="terminal-loading-overlay">
          <div class="terminal-loading-panel">
            <div class="terminal-loading-kicker">CYCLICAL GLOBAL MACRO TERMINAL</div>
            <div class="terminal-loading-title">OPENING {html.escape(page_name)}</div>
            <div class="terminal-loading-detail">Loading cached datasets and initializing the active workspace...</div>
            <div class="terminal-loading-track"><div class="terminal-loading-bar"></div></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return placeholder


transition = None
if st.session_state.page_transition_loading:
    transition = _transition_overlay(st.session_state.main_navigation)

render_top_bar()

with st.sidebar:
    st.markdown("<div class='terminal-header'>NAVIGATION</div>", unsafe_allow_html=True)
    page = st.radio(
        "Page",
        list(PAGE_ROUTES),
        key="main_navigation",
        label_visibility="collapsed",
        on_change=_start_page_transition,
    )
    st.divider()
    if st.button("CLEAR DATA CACHE", width="stretch"):
        st.cache_data.clear()
        st.session_state.page_transition_loading = True
        st.rerun()

module_name, function_name = PAGE_ROUTES[page]
try:
    renderer = getattr(import_module(module_name), function_name)
    renderer()
finally:
    if transition is not None:
        transition.empty()
    st.session_state.page_transition_loading = False
